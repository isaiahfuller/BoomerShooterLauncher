"""Offscreen integration checks with isolated settings and external services mocked."""

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
from repositories.settings_repository import SettingsRepository


class SettingsWorkflowTests(unittest.TestCase):
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
                window = main.MainWindow()
                assert window.gameList.rowCount() == 2
                window.gameList.selectRow(0)
                assert window.runnerCombobox.currentText() == 'UZDoom'
                assert window.runnerCombobox.isEnabled()
                assert window.versionCombobox.currentText() == 'Registered'
                repo.save_selection('The Ultimate Doom', 'Removed port', 'Removed release')
                window.getRunners()
                window.getVersions()
                self.assertEqual(window.currentRunners, ['UZDoom'])
                self.assertEqual(window.currentVersions, ['Registered'])
                self.assertEqual(window.runnerCombobox.currentText(), 'UZDoom')
                self.assertEqual(window.versionCombobox.currentText(), 'Registered')
                with patch.object(GameLauncher, 'runGame') as launch:
                    window.launchGame()
                    launch.assert_called_once_with('Doom', '/games/doom.wad', 'UZDoom', [])
                window.gameList.selectRow(1)
                with patch.object(GameLauncher, 'runGame') as launch:
                    window.launchGame()
                    launch.assert_called_once_with('Doom', '/games/doom.wad', 'UZDoom',
                                                    ['/mods/first.pk3', '/mods/second.wad'])
                assert repo.last_selection('Pack', modpack=True) == ('UZDoom', 'Registered')
                editor = ModsView(window.gameList)
                with patch.object(editor, 'showWindow'):
                    editor.openFile()
                assert editor.mods['files'] == files
                editor.mods['files'] = files[1:]
                editor.saveFile()
                assert repo.modpacks()['Pack']['files'] == files[1:]
                importer = ModsImport(window, {'name': 'Imported', 'base': 'Doom',
                                               'mods': [{'name': 'import.pk3', 'source': ''}]})
                importer.mods['import.pk3']['path'] = '/mods/import.pk3'
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
                    assert not window.steamScanAction.isEnabled()
                    loop = QtCore.QEventLoop()
                    worker.finished.connect(loop.quit)
                    timeout = QtCore.QTimer()
                    timeout.setSingleShot(True)
                    timeout.timeout.connect(loop.quit)
                    timeout.start(5000)
                    loop.exec()
                    timeout.stop()
                    assert window.steamScanner is None
                    assert window.steamScanAction.isEnabled()
                    assert '1 supported game files' in window.status.currentMessage()
                window.writeSettings()
                assert not repo.window_geometry().isEmpty()
                window.close()


if __name__ == "__main__":
    unittest.main()
