"""Widget-free regression tests for modpack workflows and JSON boundaries."""
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from controllers.modpack_controller import ModpackController
from models.records import ModFile, Modpack
from services.modpack_json import decode_modpack


class ModpackControllerTests(unittest.TestCase):
    def setUp(self):
        self.repo = Mock()
        self.pack = Modpack("Pack", "Doom", (
            ModFile("same.pk3", "/one/same.pk3", "one"),
            ModFile("same.pk3", "/two/same.pk3", "two")))
        self.repo.library.return_value.modpacks = (self.pack,)
        self.controller = ModpackController(self.repo, draft=self.pack)

    def test_order_metadata_and_empty_draft(self):
        c = self.controller
        self.assertFalse(c.add_file("/one/same.pk3"))
        self.assertTrue(c.add_file("/three/same.pk3"))
        self.assertEqual(c.move_file(0, 1), 1)
        c.change_file(1, source="updated")
        self.assertEqual(c.draft.files[1], ModFile("same.pk3", "/one/same.pk3", "updated"))
        self.assertIsNone(c.move_file(0, -1))
        self.assertFalse(c.change_file(-1, source="bad"))
        self.assertIsNone(c.remove_file(-1))
        for _ in range(3):
            c.remove_file(0)
        self.assertEqual(c.draft.files, ())
        self.assertTrue(c.save())
        self.repo.save_modpack_record.assert_called_once_with(c.draft)

    def test_draft_rename_and_remembered_selections(self):
        c = self.controller
        c.open(self.pack)
        c.change(name="Renamed")
        self.repo.save_modpack_record.assert_not_called()
        self.repo.remove_modpack.assert_not_called()
        self.repo.last_selection.return_value = ("Port", "Release")
        self.assertTrue(c.save())
        self.repo.save_selection.assert_called_once_with("Renamed", "Port", "Release", modpack=True)
        self.repo.remove_modpack.assert_called_once_with("Pack")
        self.assertEqual(c.original_name, "Renamed")

    def test_import_resolution_preserves_duplicate_names(self):
        c = self.controller
        c.draft = decode_modpack({"name": "Imported", "base": "Doom", "mods": [
            {"name": "same.pk3", "source": "one", "path": "/ignored"},
            {"name": "same.pk3", "source": "two"}]})
        self.assertFalse(c.save(require_resolved=True))
        self.assertEqual(c.resolve_dropped("/one/same.pk3"), 0)
        self.assertEqual(c.loaded_count, 1)
        self.assertFalse(c.save(require_resolved=True))
        self.assertIsNone(c.resolve_dropped("/other/no-match.pk3"))
        self.assertEqual(c.resolve_dropped("/two/same.pk3"), 1)
        self.assertEqual([f.path for f in c.draft.files], ["/one/same.pk3", "/two/same.pk3"])
        self.assertEqual([f.source for f in c.draft.files], ["one", "two"])
        self.assertTrue(c.save(require_resolved=True))

    def test_json_round_trip_does_not_mutate_export(self):
        c = self.controller
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pack.json"
            self.assertTrue(c.export_json(path))
            self.assertEqual(c.draft, self.pack)
            self.assertNotIn("path", json.loads(path.read_text())["mods"][0])
            imported = c.load_json(path)
            self.assertEqual(imported.files, tuple(ModFile(f.name, None, f.source) for f in self.pack.files))
            self.repo.save_modpack_record.assert_not_called()

    def test_bad_json_and_io_errors_preserve_draft(self):
        c = self.controller
        errors = []
        c.failed.connect(errors.append)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pack.json"
            for content in ("{", "[]", '{"name":"Pack","base":"Doom","mods":[{}]}'):
                path.write_text(content)
                self.assertIsNone(c.load_json(path))
                self.assertEqual(c.draft, self.pack)
            self.assertIsNone(c.load_json(Path(directory) / "missing.json"))
            self.assertFalse(c.export_json(Path(directory) / "missing" / "pack.json"))
        self.assertEqual(len(errors), 5)
        self.repo.save_modpack_record.assert_not_called()

    def test_schema_validation_and_empty_import(self):
        for data in ({}, {"name": "", "base": "Doom", "mods": []},
                     {"name": "Pack", "base": None, "mods": []},
                     {"name": "Pack", "base": "Doom", "mods": {}},
                     {"name": "Pack", "base": "Doom", "mods": [{"name": "mod", "source": None}]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                decode_modpack(data)
        self.controller.draft = decode_modpack({"name": "Empty", "base": "Doom", "mods": []})
        self.assertTrue(self.controller.save(require_resolved=True))

    def test_persistence_errors_are_reported(self):
        errors = []
        self.controller.failed.connect(errors.append)
        self.repo.save_modpack_record.side_effect = OSError("cannot save")
        self.assertFalse(self.controller.save())
        self.repo.remove_modpack.side_effect = OSError("cannot remove")
        self.assertFalse(self.controller.remove(self.pack))
        self.assertEqual(errors, ["cannot save", "cannot remove"])


if __name__ == "__main__":
    unittest.main()
