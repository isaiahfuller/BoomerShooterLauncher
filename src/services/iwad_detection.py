"""Identify WADs by their directory entries, in IWADINFO order."""
import logging
from pathlib import Path
import struct
from models.iwadinfo import bundled_catalog


def wad_entries(path):
    size = Path(path).stat().st_size
    with open(path, 'rb') as stream:
        header = stream.read(12)
        if len(header) != 12:
            raise ValueError('Truncated WAD header')
        magic, count, offset = struct.unpack('<4sII', header)
        if magic not in (b'IWAD', b'PWAD'):
            raise ValueError('Not a WAD')
        if offset > size or count > (size - offset) // 16:
            raise ValueError('WAD directory exceeds file size')
        stream.seek(offset)
        entries = set()
        for _ in range(count):
            item = stream.read(16)
            if len(item) != 16:
                raise ValueError('Truncated WAD directory')
            start, length, name = struct.unpack('<II8s', item)
            if start > size or length > size - start:
                raise ValueError('WAD entry exceeds file size')
            entries.add(name.rstrip(b'\0').decode('ascii', errors='replace').upper())
        return entries


def detect_wad(path, catalog=None):
    entries = wad_entries(path)
    filename = Path(path).name.lower()
    for definition in (catalog or bundled_catalog()).definitions:
        # The official Doom rules can match ordinary map packs, especially the
        # Doom II rule whose only required lump is MAP01.
        if (definition.name.startswith(('DOOM:', 'DOOM 2:')) or
                definition.name in ('The Ultimate DOOM', 'DOOM Registered', 'DOOM Shareware')):
            expected = definition.filename or 'doom1.wad'  # Shareware has no IWADName.
            if filename != expected.lower():
                continue
        if set(definition.must_contain).issubset(entries):
            logging.getLogger(__name__).debug("Identified %s as %s", path, definition.name)
            return definition
    logging.getLogger(__name__).debug("No IWADINFO match for %s", path)
    return None
