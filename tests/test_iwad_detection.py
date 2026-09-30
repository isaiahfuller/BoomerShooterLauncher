"""Offline catalog and WAD identification checks."""
import struct
import tempfile
import unittest
from pathlib import Path

from models.iwadinfo import bundled_catalog, parse_iwadinfo
from services.iwad_detection import detect_wad, wad_entries
from services.game_files import scan_game_file


def make_wad(path, names):
    entries = b''.join(struct.pack('<II8s', 12, 0, name.encode()) for name in names)
    path.write_bytes(struct.pack('<4sII', b'IWAD', len(names), 12) + entries)


class IWadDetectionTests(unittest.TestCase):
    def test_bundled_catalog(self):
        catalog = bundled_catalog()
        self.assertGreater(len(catalog.definitions), 40)
        self.assertEqual(catalog.definitions[0].name, 'Rise Of The Wool Ball')
        self.assertIn('doom2.wad', catalog.names)

    def test_order_and_missing_entries(self):
        catalog = parse_iwadinfo('''
            IWad { Name = "Specific" Game = "Doom" IWADName = "doom.wad"
                   MustContain = "MAP01", "SPECIAL" }
            IWad { Name = "General" MustContain = "MAP01" }
            Names { "doom.wad" } Order { "Specific" "General" }
        ''')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'renamed.wad'
            make_wad(path, ['MAP01', 'SPECIAL'])
            self.assertEqual(detect_wad(path, catalog).name, 'Specific')
            make_wad(path, ['MAP01'])
            self.assertEqual(detect_wad(path, catalog).name, 'General')
            make_wad(path, ['OTHER'])
            self.assertIsNone(detect_wad(path, catalog))

    def test_scan_uses_content_and_retains_filename_fallback(self):
        class Repository:
            def __init__(self):
                self.saved = []

            def save_game(self, *args, **kwargs):
                self.saved.append((args, kwargs))

        with tempfile.TemporaryDirectory() as temp:
            repository = Repository()
            path = Path(temp) / 'doom2.wad'
            make_wad(path, ['MAP01'])
            self.assertTrue(scan_game_file(path, repository))
            self.assertEqual(repository.saved[-1][0][0], 'Doom II: Hell on Earth')
            self.assertEqual(repository.saved[-1][1]['label'], 'DOOM 2: Hell on Earth')
            # A known filename still uses the legacy lookup if the content
            # catalog has no match.
            fallback = Path(temp) / 'doom.wad'
            fallback.write_bytes(b'legacy data')
            self.assertTrue(scan_game_file(fallback, repository))
            self.assertEqual(repository.saved[-1][0][0], 'Doom')
            self.assertIsNone(repository.saved[-1][1]['label'])

    def test_doom_rules_require_their_filenames(self):
        catalog = bundled_catalog()
        cases = (
            ('DOOM 2: Hell on Earth', 'doom2.wad', 'custom_map.wad'),
            ('DOOM Shareware', 'doom1.wad', 'episode.wad'),
            ('The Ultimate DOOM', 'doom.wad', 'renamed.wad'),
        )
        with tempfile.TemporaryDirectory() as temp:
            for rule_name, expected_name, other_name in cases:
                rule = next(rule for rule in catalog.definitions if rule.name == rule_name)
                expected = Path(temp) / expected_name
                other = Path(temp) / other_name
                make_wad(expected, rule.must_contain)
                make_wad(other, rule.must_contain)
                self.assertEqual(detect_wad(expected).name, rule_name)
                self.assertIsNone(detect_wad(other))

    def test_ultimate_doom_rule_matches_before_registered(self):
        catalog = bundled_catalog()
        ultimate = next(rule for rule in catalog.definitions
                        if rule.name == 'The Ultimate DOOM')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'DOOM.WAD'
            make_wad(path, ultimate.must_contain)
            self.assertEqual(detect_wad(path).name, 'The Ultimate DOOM')

    def test_kex_doom_uses_iwadinfo_label_with_legacy_identity(self):
        class Repository:
            def __init__(self):
                self.saved = None

            def save_game(self, *args, **kwargs):
                self.saved = (args, kwargs)

        definition = next(rule for rule in bundled_catalog().definitions
                          if rule.name == 'DOOM: KEX Edition')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'doomkex.wad'
            make_wad(path, definition.must_contain)
            repository = Repository()
            self.assertTrue(scan_game_file(path, repository))
            self.assertEqual(repository.saved[0][0], 'Doom')
            self.assertEqual(repository.saved[1]['label'], 'DOOM: KEX Edition')

    def test_bad_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.wad'
            path.write_bytes(struct.pack('<4sII', b'IWAD', 2, 12))
            with self.assertRaises(ValueError):
                wad_entries(path)


if __name__ == '__main__':
    unittest.main()
