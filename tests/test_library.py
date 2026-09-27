"""Domain selection checks require neither Qt nor a main window."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from models.library import Library
from models.records import Game, InstalledVersion, ModFile, Modpack, Runner


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.first = InstalledVersion("Original", "1.0", "abc", "/games/original.wad")
        self.second = InstalledVersion("Updated", "1.9", "def", "/games/updated.wad")
        self.library = Library(
            (Game("Doom", "Doom", 1993, (self.first, self.second)),
             Game("Heretic", "Heretic", 1994, (self.first,))),
            (Runner("UZDoom", "/ports/uzdoom", "uzdoom"),
             Runner("Chocolate Heretic", "/ports/heretic", "heretic"),
             Runner("Custom", "/ports/custom", "custom")),
            (Modpack("Pack", "Doom", (ModFile("one", "/mods/one", ""),
                                      ModFile("two", "/mods/two", ""))),)
        )

    def test_compatibility_and_custom_ports(self):
        self.assertEqual(
            [r.name for r in self.library.compatible_runners("Doom", "Custom")],
            ["Custom", "UZDoom"])
        for stale in ("Removed", "Chocolate Heretic"):
            self.assertEqual(
                [r.name for r in self.library.compatible_runners("Doom", stale)],
                ["UZDoom", "Custom"])

    def test_versions_use_base_identity_or_modpack_family(self):
        self.assertEqual(self.library.installed_versions("Doom"), (self.first, self.second))
        self.assertEqual(self.library.installed_versions("Pack", modpack=True,
                                                        preferred="Updated"),
                         (self.second, self.first))
        self.assertEqual(self.library.installed_versions("Doom", preferred="Removed"),
                         (self.first, self.second))
        self.assertEqual(self.library.installed_versions("Missing"), ())
        self.assertEqual(self.library.installed_versions("Missing", modpack=True), ())


if __name__ == "__main__":
    unittest.main()
