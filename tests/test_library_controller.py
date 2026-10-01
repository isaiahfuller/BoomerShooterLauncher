"""Selection orchestration checks without constructing a main window."""
import unittest
from unittest.mock import Mock

from controllers.library_controller import LibraryController
from models.library import Library
from models.records import Game, InstalledVersion, Modpack, Runner


class LibraryControllerTests(unittest.TestCase):
    def setUp(self):
        self.first = InstalledVersion('Same release', '1', None, '/first.wad')
        self.second = InstalledVersion('Same release', '2', None, '/second.wad')
        self.game = Game('Game', 'Doom', 1993, (self.first,))
        self.pack = Modpack('Game', 'Doom', ())
        self.custom = Runner('Custom', '/custom', 'custom')
        self.uzdoom = Runner('UZDoom', '/uzdoom', 'uzdoom')
        self.repo = Mock()
        self.repo.library.return_value = Library(
            (self.game, Game('Other', 'Doom', 1994, (self.second,))),
            (self.custom, self.uzdoom), (self.pack,))
        self.repo.last_selection.return_value = ('UZDoom', 'Same release')
        self.controller = LibraryController(self.repo)
        self.results = []
        self.controller.choices_changed.connect(
            lambda *choices: self.results.append(choices))

    def test_game_uses_one_snapshot_and_remembered_choices(self):
        self.controller.select(self.game)
        self.assertEqual(self.results[-1],
                         (self.game, (self.uzdoom, self.custom), (self.first,)))
        self.repo.library.assert_called_once_with()
        self.repo.last_selection.assert_called_once_with('Game', modpack=False)
        self.repo.save_selection.assert_not_called()

    def test_modpack_collision_and_duplicate_release_paths(self):
        self.controller.select(self.pack)
        self.repo.last_selection.assert_called_once_with('Game', modpack=True)
        self.assertEqual(self.results[-1][2], (self.first, self.second))

    def test_stale_preferences_and_incompatible_runner(self):
        incompatible = Runner('Chocolate Hexen', '/hexen', 'hexen')
        self.repo.library.return_value = Library(
            (self.game,), (incompatible, self.custom), ())
        self.repo.last_selection.return_value = ('Chocolate Hexen', 'Removed release')
        self.controller.select(self.game)
        self.assertEqual(self.results[-1], (self.game, (self.custom,), (self.first,)))

    def test_no_selection_clears_choices_without_settings_reads(self):
        self.controller.select(None)
        self.assertEqual(self.results[-1], (None, (), ()))
        self.repo.library.assert_not_called()
        self.repo.last_selection.assert_not_called()

    def test_missing_base_and_empty_runners(self):
        self.repo.library.return_value = Library((), (), (self.pack,))
        self.controller.select(self.pack)
        self.assertEqual(self.results[-1], (self.pack, (), ()))


if __name__ == '__main__':
    unittest.main()
