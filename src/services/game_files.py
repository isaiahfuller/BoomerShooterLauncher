"""Identify supported game files and save them without accessing widgets."""
from pathlib import Path
import zlib
import data


def scan_game_file(path, repository, cancelled=lambda: False):
    path = Path(path).resolve()
    game = data.games.get(path.name.lower())
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
                         crc=checksum, path=str(path), year=game['year'], game=game['game'])
    return True
