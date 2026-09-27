"""Discover local Steam libraries and installed game directories."""
import logging
import os
from pathlib import Path
import platform
import re

LOGGER = logging.getLogger(__name__)


def read_vdf(path):
    """Read the quoted KeyValues subset used by Steam library/app manifests."""
    text = Path(path).read_text(encoding='utf-8-sig')
    tokens = re.findall(r'//[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+', text)
    tokens = iter(token for token in tokens if not token.startswith('//'))

    def decode(token):
        if token.startswith('"'):
            return re.sub(r'\\([\\"])', r'\1', token[1:-1])
        return token

    def block(nested=False):
        result = {}
        for token in tokens:
            if token == '}':
                if not nested:
                    raise ValueError('Unexpected closing brace')
                return result
            if token == '{':
                raise ValueError('Missing key')
            value = next(tokens, None)
            if value is None or value == '}':
                raise ValueError('Missing value')
            result[decode(token).lower()] = block(True) if value == '{' else decode(value)
        if nested:
            raise ValueError('Unclosed block')
        return result
    return block()


def steam_roots():
    """Find native Windows/Linux and Flatpak Steam installations."""
    home = Path.home()
    roots = []
    if platform.system() == 'Windows':
        import winreg
        for hive, key, field in (
            (winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam', 'SteamPath'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Valve\Steam', 'InstallPath'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Valve\Steam', 'InstallPath'),
        ):
            try:
                with winreg.OpenKey(hive, key) as handle:
                    roots.append(Path(winreg.QueryValueEx(handle, field)[0]))
            except OSError:
                pass
        for variable in ('ProgramFiles(x86)', 'ProgramFiles'):
            if os.environ.get(variable):
                roots.append(Path(os.environ[variable]) / 'Steam')
    else:
        roots.extend((home / '.steam/steam', home / '.steam/root',
                      home / '.local/share/Steam',
                      Path(os.environ.get('XDG_DATA_HOME', home / '.local/share')) / 'Steam',
                      home / '.var/app/com.valvesoftware.Steam/.local/share/Steam'))
    return list(dict.fromkeys(path.resolve() for path in roots if path.is_dir()))


def installed_game_directories(roots=None):
    """Return deduplicated manifest-backed installs across all Steam libraries."""
    libraries = set()
    for root in steam_roots() if roots is None else roots:
        root = Path(root).resolve()
        libraries.add(root)
        for config in (root / 'steamapps/libraryfolders.vdf', root / 'config/libraryfolders.vdf'):
            if not config.is_file():
                continue
            try:
                folders = read_vdf(config).get('libraryfolders', {})
                if not isinstance(folders, dict):
                    raise ValueError('Invalid library folders')
                for key, value in folders.items():
                    if key.isdigit():
                        path = value.get('path') if isinstance(value, dict) else value
                        if path:
                            libraries.add(Path(path).resolve())
            except (OSError, ValueError, UnicodeError) as error:
                LOGGER.warning('Cannot read %s: %s', config, error)
    installs = set()
    for library in sorted(libraries):
        common = (library / 'steamapps/common').resolve()
        for manifest in sorted((library / 'steamapps').glob('appmanifest_*.acf')):
            try:
                state = read_vdf(manifest).get('appstate', {})
                if not isinstance(state, dict) or not isinstance(state.get('installdir'), str):
                    continue
                install = (common / state['installdir']).resolve()
                if install.is_relative_to(common) and install != common and install.is_dir():
                    installs.add(install)
            except (OSError, ValueError, UnicodeError) as error:
                LOGGER.warning('Cannot read %s: %s', manifest, error)
    return sorted(installs)
