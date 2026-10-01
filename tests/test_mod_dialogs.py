"""Regression checks for record-backed modpack drafts and imports."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6 import QtCore, QtWidgets
from models.records import ModFile, Modpack
from mods_view import ModsView
from import_view import ModsImport
from repositories.settings_repository import SettingsRepository


class ModDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        factory = lambda: QtCore.QSettings(str(self.root / "config.ini"), QtCore.QSettings.IniFormat)
        self.repo = SettingsRepository(factory)
        patcher = patch("repositories.settings_repository.create_settings", factory)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.parent = QtWidgets.QMainWindow()
        self.parent.refresh = Mock()
        self.parent.gameList = self.parent
        self.addCleanup(self.parent.deleteLater)
        self.pack = Modpack("Pack", "Unavailable family", (
            ModFile("first.pk3", "/mods/first.pk3", "first source"),
            ModFile("second.pk3", "/mods/second.pk3", "second source")))
        self.repo.save_modpack_record(self.pack)
        self.parent.selected_record = self.pack

    def editor(self):
        view = ModsView(self.parent)
        with patch.object(view, "showWindow"):
            view.openFile()
        return view

    def test_export_keeps_paths_and_reordering_keeps_metadata(self):
        view = self.editor()
        target = self.root / "pack.json"
        with patch.object(QtWidgets.QFileDialog, "exec", return_value=QtWidgets.QDialog.Accepted), \
                patch.object(QtWidgets.QFileDialog, "selectedFiles", return_value=[str(target)]):
            view.exportJson()
        self.assertEqual(view.mods, self.pack)
        self.assertEqual(json.loads(target.read_text())["mods"], [
            {"name": file.name, "source": file.source} for file in self.pack.files])
        view.modList.setCurrentRow(0)
        view.moveDown()
        view.changeModSource("updated")
        self.assertEqual(view.mods.files[1].name, "first.pk3")
        self.assertEqual(view.mods.files[1].source, "updated")
        view.removeMod()
        view.removeMod()
        view.removeMod()
        self.assertEqual(view.mods.files, ())
        self.assertFalse(view.modSourceEdit.isEnabled())
        view.saveFile()
        self.assertEqual(self.repo.library().modpacks[0].files, ())

    def test_rename_is_only_persisted_on_save(self):
        view = self.editor()
        view.changeName("Cancelled")
        view.close()
        self.assertEqual(self.repo.library().modpacks, (self.pack,))
        self.repo.save_selection("Pack", "Port", "Release", modpack=True)
        view = self.editor()
        view.changeName("Renamed")
        view.saveFile()
        self.assertEqual([p.name for p in self.repo.library().modpacks], ["Renamed"])
        self.assertEqual(self.repo.last_selection("Renamed", modpack=True), ("Port", "Release"))
        self.assertEqual(self.repo.library().modpacks[0].base, "Unavailable family")

    def test_import_duplicate_names_remain_independent_and_ordered(self):
        view = ModsImport(self.parent, {"name": "Imported", "base": "Doom", "mods": [
            {"name": "same.pk3", "source": "one"},
            {"name": "same.pk3", "source": "two"}]})
        view.addDroppedModFile("/one/same.pk3")
        self.assertFalse(view.finishButton.isEnabled())
        view.saveModpack()
        self.assertNotIn("Imported", self.repo.modpacks())
        view.addDroppedModFile("/two/same.pk3")
        self.assertTrue(view.finishButton.isEnabled())
        view.modList.item(0, 0).setText("Changed display")
        view.setModPath(0, "/replacement.pk3")
        view.saveModpack()
        pack = next(p for p in self.repo.library().modpacks if p.name == "Imported")
        self.assertEqual([f.path for f in pack.files], ["/replacement.pk3", "/two/same.pk3"])
        self.assertEqual([f.source for f in pack.files], ["one", "two"])

    def test_record_import_reuses_repository_and_reports_save_failure(self):
        self.parent.repository = self.repo
        view = ModsImport(self.parent, self.pack)
        self.assertIs(view.controller.repository, self.repo)
        self.assertEqual(view.mods, self.pack.files)
        with patch.object(self.repo, "save_modpack_record", side_effect=OSError("cannot save")), \
                patch.object(view, "close") as close:
            view.saveModpack()
            close.assert_not_called()
        self.assertEqual(view.status.currentMessage(), "cannot save")
        self.parent.refresh.assert_not_called()

    def test_export_defaults_to_json_extension(self):
        view = self.editor()
        target = self.root / "pack"

        def accept(chooser):
            self.assertEqual(chooser.acceptMode(), QtWidgets.QFileDialog.AcceptSave)
            self.assertEqual(chooser.defaultSuffix(), "json")
            chooser.selectFile(str(target))
            return QtWidgets.QDialog.Accepted

        with patch.object(QtWidgets.QFileDialog, "exec", new=accept):
            view.exportJson()
        self.assertFalse(target.exists())
        self.assertEqual(json.loads(target.with_suffix(".json").read_text())["name"], "Pack")
        self.assertEqual(view.mods, self.pack)

    def test_cancelled_export_does_not_call_controller(self):
        view = self.editor()
        with patch.object(QtWidgets.QFileDialog, "exec", return_value=QtWidgets.QDialog.Rejected), \
                patch.object(view.controller, "export_json") as export:
            view.exportJson()
            export.assert_not_called()
        self.assertEqual(view.mods, self.pack)
