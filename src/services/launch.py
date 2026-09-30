"""Build a source-port command from explicit launch inputs."""
from dataclasses import dataclass
import platform
from pathlib import Path


@dataclass(frozen=True)
class LaunchRequest:
    title: str
    game_path: str
    runner_name: str
    runner_path: str
    mod_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class LaunchCommand:
    executable: str
    arguments: tuple[str, ...]
    save_directory: Path


def build_launch_command(request: LaunchRequest, *, system=None, home=None) -> LaunchCommand:
    """Preserve port-specific arguments and the existing save directory layout."""
    if not request.game_path or not request.runner_name or not request.runner_path:
        raise ValueError('Choose a game version and source port')
    title = ''.join(char for char in request.title if char not in '\\/:*?<>|"')
    if not title:
        raise ValueError('Game title is empty')
    home = Path.home() if home is None else Path(home)
    system = platform.system() if system is None else system
    if system == 'Windows':
        save_directory = home / 'AppData' / 'Roaming' / 'Boomer Shooter Launcher' / 'Saves'
    else:
        save_directory = home / '.local' / 'share' / 'Boomer Shooter Launcher'
    save_directory = save_directory / request.runner_name / title
    arguments = ['-iwad', request.game_path]
    if request.mod_paths:
        arguments.extend(('-file', *request.mod_paths))
    arguments.extend(('-save' if request.runner_name == 'PrBoom+' else '-savedir',
                      str(save_directory)))
    return LaunchCommand(request.runner_path, tuple(arguments), save_directory)
