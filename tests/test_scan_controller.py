"""Scan workflow ownership and GUI-thread delivery."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6 import QtCore, QtWidgets
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from controllers.scan_controller import ScanController
from repositories.settings_repository import SettingsRepository


class ScanControllerTests(unittest.TestCase):
    def test_multiple_dropped_files_use_injected_repository_and_gui_callbacks(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / 'doom.wad', root / 'doom2.wad']
            for path in paths:
                path.write_bytes(b'test game data')
            repository = SettingsRepository(lambda: QtCore.QSettings(
                str(root / 'settings.ini'), QtCore.QSettings.IniFormat))
            controller = ScanController(repository)
            threads = []
            loop = QtCore.QEventLoop()
            controller.library_changed.connect(
                lambda: threads.append(QtCore.QThread.currentThread()))
            controller.manual_finished.connect(loop.quit)
            timer = QtCore.QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            controller.scan_paths([str(path) for path in paths])
            timer.start(5000)
            loop.exec()
            controller.stop()
            self.assertTrue(timer.isActive(), 'scan timed out')
            timer.stop()
            self.assertEqual(controller.workers, [])
            self.assertEqual(len(threads), 2)
            self.assertTrue(all(thread == app.thread() for thread in threads))
            self.assertEqual(set(repository.games()), {'Doom', 'Doom II: Hell on Earth'})

    def test_steam_duplicate_request_and_shutdown(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        controller = ScanController(object())
        with patch('controllers.scan_controller.SteamScanner') as factory:
            worker = factory.return_value
            controller.scan_steam()
            controller.scan_steam()
            factory.assert_called_once_with(controller, repository=controller.repository)
            controller.stop()
            worker.requestInterruption.assert_called_once()
            worker.wait.assert_called_once()
            controller.scan_paths(['unused'])
            self.assertEqual(controller.workers, [])
