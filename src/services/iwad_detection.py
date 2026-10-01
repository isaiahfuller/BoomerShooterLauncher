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
        # Generic Doom rules can match ordinary map packs, especially the
        # Doom II rule whose only required lump is MAP01. Edition-specific
        # rules instead identify content: Steam also ships KEX/Unity/BFG
        # editions as doom.wad or doom2.wad, not their IWADName aliases.
        if definition.name in ('DOOM 2: Hell on Earth', 'The Ultimate DOOM',
                               'DOOM Registered', 'DOOM Shareware'):
            expected = definition.filename or 'doom1.wad'  # Shareware has no IWADName.
            if filename != expected.lower():
                continue
        # MAP33 and its title graphic also occur in community megawads
        # (e.g. Anomaly Report), so the Xbox Doom II rule is not distinctive.
        if (definition.name == 'DOOM 2: XBox Edition' and
                filename not in ('doom2.wad', 'doom2xbox.wad')):
            continue
        if set(definition.must_contain).issubset(entries):
            logging.getLogger(__name__).debug("Identified %s as %s", path, definition.name)
            return definition
    logging.getLogger(__name__).debug("No IWADINFO match for %s", path)
    return None
