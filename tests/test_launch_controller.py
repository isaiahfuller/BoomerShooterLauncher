"""Launch workflow checks without constructing the main window."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6 import QtCore, QtWidgets

_APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from controllers.launch_controller import LaunchController
from launcher import GameLauncher
from models.records import InstalledVersion, ModFile, Modpack, Runner
from services.launch import LaunchCommand, LaunchRequest


class LaunchControllerTests(unittest.TestCase):
    def setUp(self):
        self.repository = Mock()
        self.controller = LaunchController(self.repository)
        self.pack = Modpack('My Pack', 'Doom',
                            (ModFile('one', '/mods/one.pk3', ''),
                             ModFile('two', '/mods/two.wad', '')))
        self.version = InstalledVersion('Registered', '1.9', 'abc', '/games/doom.wad')
        self.runner = Runner('UZDoom', '/ports/uzdoom', 'uzdoom')

    def test_launch_passes_ordered_request_and_reports_nonzero_exit(self):
        events = []
        self.controller.started.connect(lambda *args: events.append(('started', args)))
        self.controller.stopped.connect(lambda: events.append(('stopped',)))
        self.controller.failed.connect(lambda message: events.append(('failed', message)))
        with patch.object(GameLauncher, 'runGame') as run:
            self.controller.launch(self.pack, self.version, self.runner,
                                   has_runners=True)
        run.assert_called_once_with(LaunchRequest(
            'My Pack', '/games/doom.wad', 'UZDoom', '/ports/uzdoom',
            ('/mods/one.pk3', '/mods/two.wad')))
        self.repository.save_selection.assert_called_once_with(
            'My Pack', 'UZDoom', 'Registered', modpack=True)
        self.assertEqual(events[0], ('started', ('My Pack', 'UZDoom', 'Registered')))
        process = self.controller.process
        self.controller._handle_process_finished(process, 5, QtCore.QProcess.CrashExit)
        self.assertIsNone(self.controller.process)
        self.assertEqual(events[1], ('stopped',))
        self.assertIn('code 5', events[2][1])

    def test_real_process_exit_reaches_controller_signals(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'runner.sh'
            script.write_text('#!/bin/sh\nexit 7\n')
            script.chmod(0o755)
            command = LaunchCommand(str(script), ('-iwad', self.version.path),
                                    Path(directory) / 'saves')
            runner = Runner('UZDoom', str(script), 'uzdoom')
            events = []
            self.controller.started.connect(lambda *args: events.append('started'))
            self.controller.stopped.connect(lambda: events.append('stopped'))
            self.controller.failed.connect(events.append)
            loop = QtCore.QEventLoop()
            self.controller.stopped.connect(loop.quit)
            timer = QtCore.QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            with patch('launcher.build_launch_command', return_value=command):
                self.controller.launch(self.pack, self.version, runner,
                                       has_runners=True)
                timer.start(5000)
                loop.exec()
            timed_out = not timer.isActive()
            timer.stop()
            _APP.processEvents()
            self.assertFalse(timed_out)
            self.assertEqual(events[:2], ['started', 'stopped'])
            self.assertIn('code 7', events[2])
            self.assertIsNone(self.controller.process)

    def test_missing_runner_routes_to_setup_without_saving(self):
        families = []
        self.controller.runners_needed.connect(families.append)
        self.controller.launch(self.pack, self.version, None, has_runners=False)
        self.assertEqual(families, ['Doom'])
        self.repository.save_selection.assert_not_called()
        self.assertIsNone(self.controller.process)

    def test_start_error_reports_failure_and_releases_process(self):
        errors = []
        self.controller.failed.connect(errors.append)
        with patch.object(self.controller.logger, 'exception'), \
             patch.object(GameLauncher, 'runGame', side_effect=FileNotFoundError('missing')):
            self.controller.launch(self.pack, self.version, self.runner,
                                   has_runners=True)
        self.assertIsNone(self.controller.process)
        self.assertIn('missing', errors[0])


if __name__ == '__main__':
    unittest.main()
