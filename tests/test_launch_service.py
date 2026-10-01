"""Launch commands and process setup do not require a main window."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6 import QtCore

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from services.launcher import GameLauncher
from services.launch import LaunchCommand, LaunchRequest, build_launch_command


class LaunchServiceTests(unittest.TestCase):
    def test_command_preserves_paths_mod_order_and_save_flags(self):
        request = LaunchRequest('Pack: One', '/games with spaces/doom.wad',
                                'UZDoom', '/ports/uzdoom',
                                ('/mods/z, first.pk3', '/mods/a second.wad'))
        with tempfile.TemporaryDirectory() as directory:
            linux = build_launch_command(request, system='Linux', home=directory)
            self.assertEqual(linux.arguments[:5],
                             ('-iwad', request.game_path, '-file', *request.mod_paths))
            self.assertEqual(linux.arguments[-2], '-savedir')
            self.assertEqual(linux.save_directory,
                             Path(directory) / '.local/share/Boomer Shooter Launcher/UZDoom/Pack One')
            windows = build_launch_command(request, system='Windows', home=directory)
            self.assertEqual(windows.save_directory,
                             Path(directory) / 'AppData/Roaming/Boomer Shooter Launcher/Saves/UZDoom/Pack One')
            prboom = build_launch_command(LaunchRequest(
                'Doom', request.game_path, 'PrBoom+', '/ports/prboom'),
                system='Linux', home=directory)
            self.assertEqual(prboom.arguments[-2], '-save')
            self.assertNotIn('-file', prboom.arguments)

    def test_process_uses_its_own_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'runner.sh'
            script.write_text('#!/bin/sh\npwd > result.txt\nexit 0\n')
            script.chmod(0o755)
            save_directory = Path(directory) / 'saves'
            command = LaunchCommand(str(script), ('-iwad', '/games/doom.wad',
                                                   '-savedir', str(save_directory)),
                                    save_directory)
            request = LaunchRequest('Doom', '/games/doom.wad', 'Port', str(script))
            original_directory = os.getcwd()
            process = GameLauncher()
            with patch('services.launcher.build_launch_command', return_value=command):
                process.runGame(request)
                self.assertTrue(process.waitForFinished(5000))
            self.assertEqual(process.exitCode(), 0)
            self.assertEqual(process.workingDirectory(), str(save_directory))
            self.assertEqual((save_directory / 'result.txt').read_text().strip(),
                             str(save_directory))
            self.assertEqual(os.getcwd(), original_directory)


if __name__ == '__main__':
    unittest.main()
