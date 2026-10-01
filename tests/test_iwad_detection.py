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

    def test_doom_editions_use_content_with_standard_and_alias_filenames(self):
        from unittest.mock import Mock

        catalog = bundled_catalog()
        with tempfile.TemporaryDirectory() as temp:
            for prefix, filename, base in (
                ('DOOM:', 'doom.wad', 'Doom'),
                ('DOOM 2:', 'doom2.wad', 'Doom II: Hell on Earth'),
            ):
                for edition in ('KEX', 'Unity', 'BFG', 'XBox'):
                    label = f'{prefix} {edition} Edition'
                    rule = next(rule for rule in catalog.definitions if rule.name == label)
                    for name in (filename, filename.upper(), rule.filename, 'renamed.wad'):
                        with self.subTest(label=label, filename=name):
                            path = Path(temp) / name
                            make_wad(path, rule.must_contain)
                            if label == 'DOOM 2: XBox Edition' and name == 'renamed.wad':
                                self.assertIsNone(detect_wad(path))
                                continue
                            self.assertEqual(detect_wad(path).name, label)
                            repository = Mock()
                            self.assertTrue(scan_game_file(path, repository))
                            args, kwargs = repository.save_game.call_args
                            self.assertEqual(args[0], base)
                            self.assertEqual(kwargs['label'], label)

    def test_megawad_with_map33_is_not_xbox_doom(self):
        from unittest.mock import Mock

        with tempfile.TemporaryDirectory() as temp:
            for magic in (b'PWAD', b'IWAD'):
                with self.subTest(magic=magic):
                    path = Path(temp) / 'AR.wad'
                    make_wad(path, ['MAP01', 'MAP33', 'CWILV32'])
                    with path.open('r+b') as stream:
                        stream.write(magic)
                    self.assertIsNone(detect_wad(path))
                    repository = Mock()
                    self.assertFalse(scan_game_file(path, repository))
                    repository.save_game.assert_not_called()

    def test_generic_maps_do_not_match_edition_aliases(self):
        with tempfile.TemporaryDirectory() as temp:
            for filename, entries in (
                ('doomkex.wad', ['E1M1']),
                ('doom2kex.wad', ['MAP01']),
                ('custom_map.wad', ['MAP01']),
            ):
                with self.subTest(filename=filename):
                    path = Path(temp) / filename
                    make_wad(path, entries)
                    self.assertIsNone(detect_wad(path))

    def test_editions_without_iwadname_keep_specific_labels(self):
        from unittest.mock import Mock
        import data

        cases = (
            ('DOOM Shareware', 'doom1.wad', 'doom.wad'),
            ('Heretic Shareware', 'heretic1.wad', 'heretic.wad'),
            ('Hexen: Demo Version', 'hexen.wad', 'hexen.wad'),
            ('Strife: Teaser (New Version)', 'strife0.wad', 'strife1.wad'),
            ('Strife: Teaser (Old Version)', 'strife0.wad', 'strife1.wad'),
            ('Freedoom: Demo Version', 'freedoom1.wad', 'freedoom1.wad'),
        )
        with tempfile.TemporaryDirectory() as temp:
            for label, filename, legacy_filename in cases:
                with self.subTest(label=label):
                    rule = next(rule for rule in bundled_catalog().definitions
                                if rule.name == label)
                    self.assertIsNone(rule.filename)
                    path = Path(temp) / filename
                    make_wad(path, rule.must_contain)
                    repository = Mock()
                    self.assertTrue(scan_game_file(path, repository))
                    args, kwargs = repository.save_game.call_args
                    base = data.games[legacy_filename]['name']
                    self.assertEqual(args[0], base)
                    self.assertTrue(args[1].startswith(base + ' vUnk-'))
                    self.assertEqual(kwargs['label'], label)

    def test_unmapped_expansion_is_not_treated_as_base_game(self):
        from unittest.mock import Mock

        rule = next(rule for rule in bundled_catalog().definitions
                    if rule.name == 'Hexen: Deathkings of the Dark Citadel')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'hexdd.wad'
            make_wad(path, rule.must_contain)
            repository = Mock()
            self.assertFalse(scan_game_file(path, repository))
            repository.save_game.assert_not_called()

    def test_bad_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.wad'
            path.write_bytes(struct.pack('<4sII', b'IWAD', 2, 12))
            with self.assertRaises(ValueError):
                wad_entries(path)


if __name__ == '__main__':
    unittest.main()
