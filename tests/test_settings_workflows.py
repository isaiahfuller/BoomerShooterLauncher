"""Offscreen integration checks with isolated settings and external services mocked."""

from dataclasses import asdict, replace
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6 import QtCore, QtWidgets
import main
from mods_view import ModsView
from import_view import ModsImport
from runner_view import RunnerView
from scanner import GameScanner
from launcher import GameLauncher
from services.launch import LaunchRequest
from repositories.settings_repository import SettingsRepository


class SettingsWorkflowTests(unittest.TestCase):
    def test_record_selection_survives_labels_refresh_and_duplicate_versions(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        main.app = app
        with TemporaryDirectory() as directory:
            factory = lambda: QtCore.QSettings(
                str(Path(directory) / 'config.ini'), QtCore.QSettings.IniFormat)
            repo = SettingsRepository(factory)
            repo.save_window_geometry(QtWidgets.QMainWindow().saveGeometry())
            for name, path in [('First', '/games/first.wad'), ('Second', '/games/second.wad')]:
                repo.save_game(name, 'Registered', version='1.9', crc='1234',
                               path=path, year=1993, game='Doom')
            repo.save_runner('UZDoom', '/ports/uzdoom', 'uzdoom')
            files = [{'name': 'a, b.pk3', 'path': '/mods/a, b.pk3', 'source': ''},
                     {'name': 'last.wad', 'path': '/mods/last.wad', 'source': ''}]
            # The same name can identify records in two different settings groups.
            repo.save_modpack('First', 'Doom', files)
            with patch('repositories.settings_repository.create_settings', factory), \
                 patch.object(main, 'Theme'), patch.object(main, 'Discord'):
                window = main.MainWindow()
                view = window.gameList
                view.selectRow(0)
                self.assertEqual(view.selected_record.name, 'First')
                view.selectRow(2)
                self.assertIsInstance(view.selected_record, main.Modpack)
                view.item(2, 0).setText('Different family label')
                view.item(2, 1).setText('Different name label')
                view.item(2, 2).setText('Different file label')
                window.getRunners()
                window.getVersions()
                window.versionCombobox.setCurrentIndex(1)
                window.versionCombobox.setItemText(1, 'Different version label')
                window.runnerCombobox.setItemText(0, 'Different runner label')
                with patch.object(GameLauncher, 'runGame') as launch:
                    window.launchGame()
                    launch.assert_called_once_with(LaunchRequest(
                        'First', '/games/second.wad', 'UZDoom', '/ports/uzdoom',
                        ('/mods/a, b.pk3', '/mods/last.wad')))
                self.assertEqual(repo.last_selection('First', modpack=True),
                                 ('UZDoom', 'Registered'))
                self.assertEqual(repo.last_selection('First'), (None, None))
                view.refresh()
                self.assertIsInstance(view.selected_record, main.Modpack)
                self.assertEqual(view.selected_record.name, 'First')
                repo.remove_modpack('First')
                view.refresh()
                self.assertIsNone(view.selected_record)
                self.assertFalse(window.versionCombobox.isEnabled())
                self.assertFalse(window.runnerCombobox.isEnabled())
                window.close()

    def test_launch_controller_signals_update_window(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        main.app = app
        with TemporaryDirectory() as directory:
            factory = lambda: QtCore.QSettings(
                str(Path(directory) / 'config.ini'), QtCore.QSettings.IniFormat)
            repo = SettingsRepository(factory)
            repo.save_window_geometry(QtWidgets.QMainWindow().saveGeometry())
            with patch('repositories.settings_repository.create_settings', factory), \
                 patch.object(main, 'Theme'), patch.object(main, 'Discord'), \
                 patch('main.QtWidgets.QErrorMessage') as message:
                window = main.MainWindow()
                window.launchController.started.emit('Doom', 'UZDoom', 'Registered')
                self.assertTrue(window.game_running)
                self.assertIn('Playing Doom with UZDoom', window.status.currentMessage())
                window.launchController.stopped.emit()
                self.assertFalse(window.game_running)
                window.launchController.failed.emit('UZDoom exited with code 3')
                self.assertIn('code 3', message.return_value.showMessage.call_args.args[0])
                window.close()

    def test_settings_backed_workflows(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        main.app = app
        with TemporaryDirectory() as directory:
            settings_path = str(Path(directory) / 'config.ini')
            factory = lambda: QtCore.QSettings(settings_path, QtCore.QSettings.IniFormat)
            repo = SettingsRepository(factory)
            repo.save_window_geometry(QtWidgets.QMainWindow().saveGeometry())
            repo.save_game('The Ultimate Doom', 'Registered', version='1.9', crc='1234',
                           path='/games/doom.wad', year=1993, game='Doom')
            repo.save_runner('UZDoom', '/ports/uzdoom', 'uzdoom')
            repo.save_selection('The Ultimate Doom', 'UZDoom', 'Registered')
            files = [{'name': 'first.pk3', 'path': '/mods/first.pk3', 'source': ''},
                     {'name': 'second.wad', 'path': '/mods/second.wad', 'source': ''}]
            repo.save_modpack('Pack', 'Doom', files)
            library = repo.library()
            self.assertEqual(library.games[0].name, 'The Ultimate Doom')
            self.assertEqual(library.games[0].versions[0].path, '/games/doom.wad')
            self.assertEqual(library.runners[0].name, 'UZDoom')
            self.assertEqual([file.path for file in library.modpacks[0].files],
                             ['/mods/first.pk3', '/mods/second.wad'])
            with patch('repositories.settings_repository.create_settings', factory), \
                 patch.object(main, 'Theme'), patch.object(main, 'Discord'):
                with patch.object(main.ScanController, 'scan_steam') as startup_scan:
                    window = main.MainWindow()
                    startup_scan.assert_called_once_with()
                assert not hasattr(window, 'steamScanAction')
                assert all('Steam Games' not in action.text() for action in window.actions())
                assert window.gameList.rowCount() == 2
                window.gameList.selectRow(0)
                assert window.runnerCombobox.currentText() == 'UZDoom'
                assert window.runnerCombobox.isEnabled()
                assert window.versionCombobox.currentText() == 'Registered — /games/doom.wad'
                repo.save_selection('The Ultimate Doom', 'Removed port', 'Removed release')
                window.getRunners()
                window.getVersions()
                self.assertEqual(window.currentRunners, ['UZDoom'])
                self.assertEqual(window.currentVersions, ['Registered'])
                self.assertEqual(window.runnerCombobox.currentText(), 'UZDoom')
                self.assertEqual(window.versionCombobox.currentText(), 'Registered — /games/doom.wad')
                with patch.object(GameLauncher, 'runGame') as launch:
                    window.launchGame()
                    launch.assert_called_once_with(LaunchRequest(
                        'The Ultimate Doom', '/games/doom.wad', 'UZDoom', '/ports/uzdoom'))
                window.gameList.selectRow(1)
                with patch.object(GameLauncher, 'runGame') as launch:
                    window.launchGame()
                    launch.assert_called_once_with(LaunchRequest(
                        'Pack', '/games/doom.wad', 'UZDoom', '/ports/uzdoom',
                        ('/mods/first.pk3', '/mods/second.wad')))
                assert repo.last_selection('Pack', modpack=True) == ('UZDoom', 'Registered')
                editor = ModsView(window.gameList)
                with patch.object(editor, 'showWindow'):
                    editor.openFile()
                assert [asdict(file) for file in editor.mods.files] == files
                editor.mods = replace(editor.mods, files=editor.mods.files[1:])
                editor.saveFile()
                assert repo.modpacks()['Pack']['files'] == files[1:]
                importer = ModsImport(window, {'name': 'Imported', 'base': 'Doom',
                                               'mods': [{'name': 'import.pk3', 'source': ''}]})
                importer.setModPath(0, '/mods/import.pk3')
                importer.saveModpack()
                assert repo.modpacks()['Imported']['files'][0]['path'] == '/mods/import.pk3'
                runners = RunnerView(window)
                runners.builder('all')
                assert runners.runnerList.item(0).text() == 'UZDoom [installed]'
                wad = Path(directory) / 'doom.wad'
                wad.write_bytes(b'test WAD fixture, unknown CRC')
                scanner = GameScanner(window)
                scanner.individualFile(str(wad))
                assert any(release['path'] == str(wad) for game in repo.games().values()
                           for release in game['releases'].values())
                scanner.deleteLater()
                with patch('steam_scanner.installed_game_directories', return_value=[Path(directory)]):
                    window.scanSteamGames()
                    worker = window.steamScanner
                    window.scanSteamGames()
                    assert window.steamScanner is worker
                    loop = QtCore.QEventLoop()
                    worker.finished.connect(loop.quit)
                    timeout = QtCore.QTimer()
                    timeout.setSingleShot(True)
                    timeout.timeout.connect(loop.quit)
                    timeout.start(5000)
                    loop.exec()
                    timeout.stop()
                    assert window.steamScanner is None
                    assert '1 supported game files' in window.status.currentMessage()
                window.writeSettings()
                assert not repo.window_geometry().isEmpty()
                window.close()


if __name__ == "__main__":
    unittest.main()
