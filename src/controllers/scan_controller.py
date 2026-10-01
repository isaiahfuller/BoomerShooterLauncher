"""Own background scans and report results without accessing widgets."""
from PySide6 import QtCore

from scanner import DirectoryScanWorker
from steam_scanner import SteamScanner


class ScanController(QtCore.QObject):
    progress = QtCore.Signal(str)
    library_changed = QtCore.Signal()
    manual_finished = QtCore.Signal()
    steam_completed = QtCore.Signal(int, int, int)
    steam_failed = QtCore.Signal(str)
    steam_busy = QtCore.Signal(bool)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.workers = []
        self.steam_worker = None
        self._closing = False

    def scan_paths(self, paths):
        if self._closing:
            return
        for path in paths:
            if not path:
                continue
            worker = DirectoryScanWorker(path, self, repository=self.repository)
            self.workers.append(worker)
            worker.progress.connect(self.progress)
            worker.finished.connect(self._manual_finished)
            worker.start()

    @QtCore.Slot()
    def _manual_finished(self):
        worker = self.sender()
        self.workers.remove(worker)
        worker.deleteLater()
        if not self._closing:
            self.library_changed.emit()
            if not self.workers:
                self.manual_finished.emit()

    def scan_steam(self):
        if self._closing or self.steam_worker is not None:
            return
        worker = SteamScanner(self, repository=self.repository)
        self.steam_worker = worker
        worker.progress.connect(self.progress)
        worker.completed.connect(self._steam_completed)
        worker.failed.connect(self._steam_failed)
        worker.finished.connect(self._steam_finished)
        self.steam_busy.emit(True)
        self.progress.emit('Finding installed Steam games…')
        worker.start()

    @QtCore.Slot(int, int, int)
    def _steam_completed(self, installed, found, errors):
        if not self._closing:
            self.library_changed.emit()
            self.steam_completed.emit(installed, found, errors)

    @QtCore.Slot(str)
    def _steam_failed(self, error):
        if not self._closing:
            self.library_changed.emit()
            self.steam_failed.emit(error)

    @QtCore.Slot()
    def _steam_finished(self):
        self.steam_worker.deleteLater()
        self.steam_worker = None
        if not self._closing:
            self.steam_busy.emit(False)

    def stop(self):
        """Interrupt and join workers before their QObject owner is destroyed."""
        self._closing = True
        workers = self.workers + ([self.steam_worker] if self.steam_worker else [])
        for worker in workers:
            worker.requestInterruption()
        for worker in workers:
            worker.wait()
