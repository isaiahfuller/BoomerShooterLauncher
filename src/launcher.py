"""Start source ports with explicit launch inputs and report Qt process events."""
import logging
from pathlib import Path

from PySide6 import QtCore

from services.launch import LaunchRequest, build_launch_command


class GameLauncher(QtCore.QProcess):
    """Own the process; UI error reporting belongs to the caller."""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.logger = logging.getLogger('Launcher')

    def runGame(self, request: LaunchRequest):
        command = build_launch_command(request)
        if not Path(command.executable).is_file():
            raise FileNotFoundError(f'Executable missing: {command.executable}')
        command.save_directory.mkdir(parents=True, exist_ok=True)
        self.setWorkingDirectory(str(command.save_directory))
        self.logger.debug('Starting %s with %s', command.executable, command.arguments)
        self.start(command.executable, list(command.arguments))
