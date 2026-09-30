"""Compatibility checks using real QSettings and disposable INI files."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6 import QtCore

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repositories.settings_repository import SettingsRepository, create_settings


class SettingsRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "settings.ini")
        self.repository = SettingsRepository(self.settings)

    def settings(self):
        return QtCore.QSettings(self.path, QtCore.QSettings.IniFormat)

    def test_native_settings_names_are_unchanged(self):
        for system, names in (
            ("Windows", ("Isaiah Fuller", "Boomer Shooter Launcher")),
            ("Linux", ("boomershooterlauncher", "config")),
        ):
            with self.subTest(system=system), \
                    patch("repositories.settings_repository.platform.system", return_value=system), \
                    patch("repositories.settings_repository.QtCore.QSettings") as constructor:
                create_settings()
                constructor.assert_called_once_with(*names)

    def test_reads_legacy_schema_without_rewriting(self):
        settings = self.settings()
        legacy = {
            "MainWindow/geometry": QtCore.QByteArray(b"geometry"),
            "Games/Doom/game": "Doom",
            "Games/Doom/year": 1993,
            "Games/Doom/Ultimate Doom/version": "1.9ud",
            "Games/Doom/Ultimate Doom/crc": "bf0eaac0",
            "Games/Doom/Ultimate Doom/path": "/games with spaces/doom.wad",
            "Games/Doom/Last Runner": "UZDoom",
            "Games/Doom/Last Version": "Ultimate Doom",
            "Runners/UZDoom/path": "/ports/uzdoom",
            "Runners/UZDoom/executable": "uzdoom",
            "Modpacks/My Pack/base": "Doom",
            "Modpacks/My Pack/files/size": 2,
            "Modpacks/My Pack/files/1/name": "first.pk3",
            "Modpacks/My Pack/files/1/path": "/mods/first.pk3",
            "Modpacks/My Pack/files/1/source": "https://example.com/first",
            "Modpacks/My Pack/files/2/name": "second.wad",
            "Modpacks/My Pack/files/2/path": "/mods/second.wad",
            "Modpacks/My Pack/files/2/source": "",
            "Modpacks/My Pack/Last Runner": "UZDoom",
            "Modpacks/My Pack/Last Version": "Ultimate Doom",
            "Unrelated/keep": "untouched",
        }
        for key, value in legacy.items():
            settings.setValue(key, value)
        settings.sync()
        original = Path(self.path).read_bytes()

        self.assertEqual(self.repository.window_geometry(), legacy["MainWindow/geometry"])
        game = self.repository.games()["Doom"]
        self.assertEqual(game["game"], "Doom")
        self.assertEqual(game["releases"]["Ultimate Doom"], {
            "version": "1.9ud", "crc": "bf0eaac0", "path": "/games with spaces/doom.wad"})
        self.assertEqual(self.repository.runners()["UZDoom"]["path"], "/ports/uzdoom")
        files = self.repository.modpacks()["My Pack"]["files"]
        self.assertEqual([file["name"] for file in files], ["first.pk3", "second.wad"])
        self.assertEqual(files[0]["source"], "https://example.com/first")
        self.assertEqual(self.repository.last_selection("Doom"), ("UZDoom", "Ultimate Doom"))
        self.assertEqual(self.repository.last_selection("My Pack", modpack=True),
                         ("UZDoom", "Ultimate Doom"))
        self.assertEqual(Path(self.path).read_bytes(), original)

    def test_writes_survive_reopening_and_use_legacy_keys(self):
        self.repository.save_window_geometry(QtCore.QByteArray(b"saved geometry"))
        self.repository.save_game("Doom", "Registered", version="1.9", crc="1234",
                                  path="/games/doom.wad", year=1993, game="Doom")
        self.repository.save_runner("Custom Port", "/ports/custom port", "*")
        self.repository.save_selection("Doom", "Custom Port", "Registered")
        reopened = SettingsRepository(self.settings)
        self.assertEqual(reopened.window_geometry(), QtCore.QByteArray(b"saved geometry"))
        self.assertEqual(reopened.games()["Doom"]["releases"]["Registered"]["crc"], "1234")
        self.assertEqual(reopened.runners()["Custom Port"]["executable"], "*")
        self.assertEqual(reopened.last_selection("Doom"), ("Custom Port", "Registered"))
        raw = self.settings()
        self.assertEqual(raw.value("Games/Doom/Registered/path"), "/games/doom.wad")
        self.assertEqual(raw.value("Runners/Custom Port/path"), "/ports/custom port")
        self.assertEqual(raw.value("Games/Doom/Last Version"), "Registered")

    def test_iwadinfo_label_is_display_only(self):
        self.repository.save_game("Doom", "The Ultimate Doom", version="1.9ud",
                                  crc="bf0eaac0", path="/games/doom.wad",
                                  year=1993, game="Doom", label="The Ultimate DOOM")
        self.repository.save_selection("Doom", "UZDoom", "The Ultimate Doom")
        record = SettingsRepository(self.settings).library().games[0]
        self.assertEqual(record.name, "Doom")
        self.assertEqual(record.versions[0].name, "The Ultimate Doom")
        self.assertEqual(record.versions[0].display_name, "The Ultimate DOOM")
        self.assertEqual(self.repository.last_selection("Doom"),
                         ("UZDoom", "The Ultimate Doom"))

    def test_modpack_order_shrinking_and_empty_array(self):
        files = [{"name": name, "path": f"/mods/{name}", "source": ""}
                 for name in ("b.pk3", "a.wad")]
        self.repository.save_selection("Pack", "UZDoom", "Ultimate", modpack=True)
        self.repository.save_modpack("Pack", "Doom", files)
        self.assertEqual(self.repository.modpacks()["Pack"]["files"], files)
        self.assertEqual(self.settings().value("Modpacks/Pack/files/1/name"), "b.pk3")
        self.repository.save_modpack("Pack", "Doom", files[1:])
        self.assertEqual(self.repository.modpacks()["Pack"]["files"], files[1:])
        self.assertFalse(self.settings().contains("Modpacks/Pack/files/2/name"))
        self.repository.save_modpack("Pack", "Doom", [])
        self.assertEqual(self.repository.modpacks()["Pack"]["files"], [])
        self.assertEqual(self.settings().value("Modpacks/Pack/files/size"), 0)
        self.assertEqual(self.repository.last_selection("Pack", modpack=True),
                         ("UZDoom", "Ultimate"))

    def test_removal_is_scoped_to_the_selected_record(self):
        for name in ("Keep", "Remove"):
            self.repository.save_runner(name, "/port", "port")
            self.repository.save_modpack(name, "Doom", [])
        self.repository.remove_runner("Remove")
        self.repository.remove_modpack("Remove")
        self.assertEqual(list(self.repository.runners()), ["Keep"])
        self.assertEqual(list(self.repository.modpacks()), ["Keep"])

    def test_empty_settings_defaults(self):
        self.assertTrue(self.repository.window_geometry().isEmpty())
        self.assertEqual(self.repository.games(), {})
        self.assertEqual(self.repository.runners(), {})
        self.assertEqual(self.repository.modpacks(), {})
        self.assertEqual(self.repository.last_selection("Missing"), (None, None))

    def test_scanner_writes_do_not_share_group_state_with_readers(self):
        def save(index):
            self.repository.save_game("Doom", f"Release {index}", version=str(index),
                                      crc=str(index), path=f"/{index}.wad", year=1993, game="Doom")
            self.repository.save_selection("Pack", "UZDoom", str(index), modpack=True)
            self.repository.games()

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(save, range(12)))
        self.assertEqual(len(self.repository.games()["Doom"]["releases"]), 12)
        self.assertEqual(list(self.repository.modpacks()), ["Pack"])
        self.assertFalse(any("Modpacks" in key for key in self.repository.games()))


if __name__ == "__main__":
    unittest.main()
