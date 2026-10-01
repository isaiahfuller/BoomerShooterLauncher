"""Steam discovery tests use temporary libraries, never a real Steam install."""

import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6 import QtCore

from repositories.settings_repository import SettingsRepository
from services.game_files import scan_game_file
from services.steam import installed_game_directories, read_vdf, steam_roots
from steam_scanner import SteamScanner


class SteamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def install(self, library, appid, name):
        directory = library / "steamapps/common" / name
        directory.mkdir(parents=True)
        (library / f"steamapps/appmanifest_{appid}.acf").write_text(
            f'"AppState" {{ "appid" "{appid}" "installdir" "{name}" }}'
        )
        return directory

    def test_additional_libraries_and_duplicate_roots(self):
        primary = self.root / "Steam"
        extra = self.root / "Other library"
        first = self.install(primary, 1, "Doom")
        second = self.install(extra, 2, "Doom BFG")
        (primary / "steamapps/libraryfolders.vdf").write_text(
            f'"libraryfolders" {{ "0" {{ "path" "{primary}" }} '
            f'"1" {{ "path" "{extra}" "apps" {{ "2" "1000" }} }} }}'
        )
        (primary / "steamapps/common/Unregistered").mkdir()
        self.assertEqual(
            installed_game_directories([primary, primary]), sorted([first, second])
        )

    def test_legacy_libraries_and_bad_manifest_are_tolerated(self):
        primary = self.root / "Steam"
        extra = self.root / "Extra"
        expected = self.install(extra, 1, "Doom")
        (primary / "config").mkdir(parents=True)
        (primary / "config/libraryfolders.vdf").write_text(
            f'"LibraryFolders" {{ "1" "{extra}" }}'
        )
        (extra / "steamapps/appmanifest_bad.acf").write_text('"AppState" {')
        (extra / "steamapps/appmanifest_escape.acf").write_text(
            '"AppState" { "installdir" "../.." }'
        )
        with self.assertLogs("services.steam", level="WARNING"):
            self.assertEqual(installed_game_directories([primary]), [expected])
        self.assertEqual(installed_game_directories([]), [])

    def test_parser_preserves_windows_paths_and_comments(self):
        path = self.root / "libraryfolders.vdf"
        path.write_text(
            '// comment\n"libraryfolders" { "0" { "path" "D:\\\\Steam Library" } }'
        )
        self.assertEqual(
            read_vdf(path)["libraryfolders"]["0"]["path"], "D:\\Steam Library"
        )

    def test_linux_and_flatpak_roots(self):
        native = self.root / ".local/share/Steam"
        flatpak = self.root / ".var/app/com.valvesoftware.Steam/.local/share/Steam"
        native.mkdir(parents=True)
        flatpak.mkdir(parents=True)
        with (
            patch("services.steam.Path.home", return_value=self.root),
            patch("services.steam.platform.system", return_value="Linux"),
            patch.dict(
                "os.environ", {"XDG_DATA_HOME": str(self.root / ".local/share")}
            ),
        ):
            self.assertEqual(set(steam_roots()), {native, flatpak})

    def test_worker_scans_supported_files_and_reports_results(self):
        install = self.install(self.root / "Steam", 1, "Doom")
        wad = install / "DOOM.WAD"
        wad.write_bytes(b"test game data")
        (install / "unsupported.bin").write_bytes(b"not a game")
        factory = lambda: QtCore.QSettings(
            str(self.root / "config.ini"), QtCore.QSettings.IniFormat
        )
        repo = SettingsRepository(factory)
        worker = SteamScanner()
        results = []
        worker.completed.connect(lambda *args: results.append(args))
        with (
            patch("steam_scanner.installed_game_directories", return_value=[install]),
            patch("steam_scanner.SettingsRepository", return_value=repo),
        ):
            worker.run()
        self.assertEqual(results, [(1, 1, 0)])
        releases = repo.games()["Doom"]["releases"]
        self.assertEqual(next(iter(releases.values()))["path"], str(wad))
        checksum = format(zlib.crc32(wad.read_bytes()), "x")
        with patch("services.game_files.data.gameBlacklist", [checksum]):
            self.assertFalse(scan_game_file(wad, repo))


if __name__ == "__main__":
    unittest.main()
