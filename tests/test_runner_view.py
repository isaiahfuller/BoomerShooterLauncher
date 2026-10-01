"""Runner discovery and overrides with real widgets and isolated settings."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6 import QtCore, QtWidgets
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import data
from runner_view import RunnerView
from repositories.settings_repository import SettingsRepository


class RunnerViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        factory = lambda: QtCore.QSettings(str(self.root / 'config.ini'), QtCore.QSettings.IniFormat)
        self.repo = SettingsRepository(factory)
        self.parent = QtWidgets.QMainWindow()
        self.view = RunnerView(self.parent)
        self.view.repository = self.repo
        self.view.openedFromMenu = True
        self.name = next(iter(data.runners))
        self.executable = data.runners[self.name]['executable']
        self.view.builder('all')
        self.addCleanup(self.parent.deleteLater)

    def program(self, name):
        path = self.root / name
        path.write_text('#!/bin/sh\nexit 0\n')
        path.chmod(0o755)
        return path

    def select(self, name):
        self.view.runnerList.setCurrentItem(
            self.view.runnerList.findItems(name, QtCore.Qt.MatchExactly)[0])

    def test_detects_path_and_saves_selected_runner(self):
        program = self.program(self.executable)
        with patch.dict(os.environ, {'PATH': str(self.root)}):
            self.select(self.name)
            self.assertEqual(self.view.programPath.text(), str(program))
            self.assertEqual(self.repo.runners(), {})
            self.view.addToDb()
        self.assertEqual(self.repo.runners()[self.name]['path'], str(program))

    def test_browse_overrides_detection_and_saved_override_wins(self):
        detected = self.program(self.executable)
        custom = self.program('custom port')
        with patch('controllers.runner_controller.shutil.which', return_value=str(detected)):
            self.select(self.name)
            with patch.object(self.view.runnerDialog, 'getOpenFileName',
                              return_value=(str(custom), '')):
                self.view.browseProgram()
            self.view.addToDb()
            self.assertEqual(self.view.programPath.text(), str(custom))
            self.assertTrue(self.view.selectInstalledButton.isEnabled())
        self.assertEqual(list(self.repo.runners()), [self.name])
        self.assertEqual(self.repo.runners()[self.name]['path'], str(custom))

    def test_missing_path_cancel_and_invalid_file_do_not_save(self):
        with patch('controllers.runner_controller.shutil.which', return_value=None):
            self.select(self.name)
        self.assertEqual(self.view.programPath.text(), '')
        self.assertFalse(self.view.selectInstalledButton.isEnabled())
        with patch.object(self.view.runnerDialog, 'getOpenFileName', return_value=('', '')):
            self.view.browseProgram()
        self.view.programPath.setText(str(self.root / 'missing'))
        with patch.object(QtWidgets.QMessageBox, 'warning') as warning:
            self.view.addToDb()
            warning.assert_called_once()
        self.assertEqual(self.repo.runners(), {})

    def test_runner_identity_does_not_depend_on_display_label(self):
        name = "My port [installed]"
        self.repo.save_runner(name, str(self.program("port")), "*")
        self.view.builder("all")
        item = self.view.runnerList.findItems(name + " [installed]", QtCore.Qt.MatchExactly)[0]
        item.setText("Changed display label")
        self.view.runnerList.setCurrentItem(item)
        self.assertEqual(self.view.name, name)
        self.view.removeRunner()
        self.assertNotIn(name, self.repo.runners())

    def test_existing_custom_runner_can_change_location_without_rename(self):
        original = self.program('original')
        replacement = self.program('replacement')
        self.repo.save_runner('My port', str(original), '*')
        self.view.builder('all')
        self.select('My port [installed]')
        self.view.programPath.setText(str(replacement))
        self.view.addToDb()
        self.assertEqual(list(self.repo.runners()), ['My port'])
        self.assertEqual(self.repo.runners()['My port']['path'], str(replacement))
        self.view.builder('all')  # Clearing selection must be safe.
        self.assertFalse(self.view.selectInstalledButton.isEnabled())


if __name__ == '__main__':
    unittest.main()
