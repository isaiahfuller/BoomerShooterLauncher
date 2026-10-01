"""Coordinate launch selection, persistence, and process lifecycle."""
import logging

from PySide6 import QtCore

from services.launcher import GameLauncher
from models.records import Modpack
from services.launch import LaunchRequest


class LaunchController(QtCore.QObject):
    started = QtCore.Signal(str, str, str)
    stopped = QtCore.Signal()
    failed = QtCore.Signal(str)
    runners_needed = QtCore.Signal(str)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.process = None
        self._runner_name = ''
        self._closing = False
        self.logger = logging.getLogger('Launch Controller')

    def launch(self, record, version, runner, *, has_runners):
        """Start the selected version with explicit records from the view."""
        try:
            if self.process is not None and self.process.state() != QtCore.QProcess.NotRunning:
                raise RuntimeError('A game is already running')
            if record is None:
                raise ValueError('Select a game first')
            if version is None or not version.path:
                raise ValueError('Select an installed game version')
            if not has_runners:
                family = record.base if isinstance(record, Modpack) else record.family
                self.runners_needed.emit(family or '')
                return
            if runner is None or not runner.path:
                raise ValueError('Select a source port')
            is_modpack = isinstance(record, Modpack)
            mod_paths = tuple(file.path for file in record.files) if is_modpack else ()
            if any(not path for path in mod_paths):
                raise ValueError('A modpack file has no local path')
            request = LaunchRequest(record.name, version.path, runner.name,
                                    runner.path, mod_paths)
            self.repository.save_selection(record.name, runner.name, version.name,
                                           modpack=is_modpack)
            if self.process is not None:
                self.process.deleteLater()
            process = GameLauncher(self)
            self.process = process
            self._runner_name = runner.name
            process.finished.connect(self._process_finished)
            process.errorOccurred.connect(self._process_error)
            process.runGame(request)
            self.started.emit(record.name, runner.name, version.name)
        except Exception as error:  # pylint: disable=broad-except
            self.logger.exception('Failed to launch game')
            if self.process is not None and self.process.state() == QtCore.QProcess.NotRunning:
                self._release_process(self.process)
            self.failed.emit(f'Failed to launch game ({error})')

    def _release_process(self, process):
        if process is self.process:
            self.process = None
        process.deleteLater()

    def _process_finished(self, exit_code, exit_status):
        self._handle_process_finished(self.sender(), exit_code, exit_status)

    def _handle_process_finished(self, process, exit_code, exit_status):
        if process is not self.process:
            return
        self._release_process(process)
        if self._closing:
            return
        self.stopped.emit()
        if exit_code != 0 or exit_status != QtCore.QProcess.NormalExit:
            self.failed.emit(
                f'{self._runner_name} exited with code {exit_code}. '
                'Check the source port and game version if modded.')

    def _process_error(self, error):
        self._handle_process_error(self.sender(), error)

    def _handle_process_error(self, process, error):
        if process is not self.process or error != QtCore.QProcess.FailedToStart:
            return
        message = process.errorString()
        self._release_process(process)
        if not self._closing:
            self.stopped.emit()
            self.failed.emit(f'Failed to start {self._runner_name}: {message}')

    def stop(self):
        """Stop the owned process before application shutdown."""
        self._closing = True
        process = self.process
        if process is not None and process.state() != QtCore.QProcess.NotRunning:
            process.terminate()
            if not process.waitForFinished(3000):
                process.kill()
                process.waitForFinished(3000)
        if process is not None and process is self.process:
            self._release_process(process)
