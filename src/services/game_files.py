"""Identify supported game files and save them without accessing widgets."""
from pathlib import Path
import zlib
import data
from services.iwad_detection import detect_wad


# IWADINFO distinguishes editions that share a legacy library identity.
# Keep that identity for saved selections and modpack references.
_IWAD_LEGACY_HINTS = {
    'doombfg.wad': 'doom.wad',
    'doomkex.wad': 'doom.wad',
    'doomunity.wad': 'doom.wad',
    'doomxbox.wad': 'doom.wad',
    'doom2bfg.wad': 'doom2.wad',
    'doom2kex.wad': 'doom2.wad',
    'doom2unity.wad': 'doom2.wad',
    'doom2xbox.wad': 'doom2.wad',
    'tntkex.wad': 'tnt.wad',
    'tntunity.wad': 'tnt.wad',
    'plutoniakex.wad': 'plutonia.wad',
    'plutoniaunity.wad': 'plutonia.wad',
}


def _catalog_game(path):
    if path.suffix.lower() != '.wad':
        return None
    try:
        definition = detect_wad(path)
    except ValueError:
        return None
    if definition is None:
        return None
    # Preserve existing settings identities and runner compatibility.
    hint = (definition.filename or '').lower()
    game = data.games.get(_IWAD_LEGACY_HINTS.get(hint, hint))
    return (game, definition.name) if game else None



def scan_game_file(path, repository, cancelled=lambda: False):
    path = Path(path).resolve()
    identified = _catalog_game(path)
    game, label = identified if identified else (data.games.get(path.name.lower()), None)
    if game is None:
        return False
    crc = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            if cancelled():
                return False
            crc = zlib.crc32(chunk, crc)
    checksum = format(crc & 0xffffffff, 'x')
    if checksum in data.gameBlacklist:
        return False
    release = next((item for item in game['releases'] if item['crc'] == checksum), None)
    name = release.get('name', game['name']) if release else f"{game['name']} vUnk-{checksum}"
    repository.save_game(game['name'], name,
                         version=release['version'] if release else checksum,
                         crc=checksum, path=str(path), year=game['year'],
                         game=game['game'], label=label)
    return True
