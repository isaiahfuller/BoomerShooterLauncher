"""Runner workflows with isolated settings and no window construction."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6 import QtCore
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from controllers.runner_controller import RunnerController
from models.catalog import runners
from models.records import Runner
from repositories.settings_repository import SettingsRepository


class RunnerControllerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.repo = SettingsRepository(lambda: QtCore.QSettings(
            str(self.root / 'config.ini'), QtCore.QSettings.IniFormat))
        self.controller = RunnerController(self.repo)
        self.name = next(iter(runners))
        self.record = Runner(self.name, None, runners[self.name]['executable'])
        self.errors = []
        self.controller.failed.connect(lambda title, message: self.errors.append((title, message)))

    def program(self, name='port'):
        path = self.root / name
        path.write_text('#!/bin/sh\nexit 0\n')
        path.chmod(0o755)
        return str(path)

    def test_choices_filter_and_include_installed_custom_records(self):
        self.repo.save_runner('My port', self.program(), '*')
        choices = self.controller.choices('all')
        self.assertEqual(choices[0], (Runner('My port', self.program(), '*'), True))
        self.assertEqual(sum(record.name == self.name for record, _ in choices), 1)
        game = runners[self.name]['games'][0]
        self.assertEqual({record.name for record, _ in self.controller.choices(game)},
                         {name for name, metadata in runners.items() if game in metadata['games']})

    def test_detection_and_manual_override_save_emit_record(self):
        detected = self.program('detected')
        override = self.program('override')
        with patch('controllers.runner_controller.shutil.which', return_value=detected):
            self.controller.select(self.record)
        self.assertEqual(self.controller.path, detected)
        self.assertEqual(self.repo.runners(), {})
        self.controller.change_path(override)
        saved = []
        self.controller.saved.connect(saved.append)
        record = self.controller.save()
        self.assertEqual(saved, [record])
        self.assertEqual(record, Runner(self.name, override, self.record.executable))
        self.assertEqual(self.repo.runners()[self.name]['path'], override)

    def test_saved_override_wins_and_clear_disables_operations(self):
        override = self.program()
        self.repo.save_runner(self.name, override, self.record.executable)
        with patch('controllers.runner_controller.shutil.which', return_value='other'):
            self.controller.select(self.record)
        self.assertEqual(self.controller.path, override)
        self.assertTrue(self.controller.installed)
        self.controller.select(None)
        self.assertFalse(self.controller.can_save)
        self.assertFalse(self.controller.remove())
        self.assertIsNone(self.controller.save())

    def test_custom_create_and_existing_identity_are_distinct(self):
        path = self.program('Custom...')
        self.controller.select(None, custom=True)
        self.controller.change_path(path)
        record = self.controller.save()
        self.assertEqual(record, Runner('Custom...', path, '*'))
        self.controller.select(record)
        replacement = self.program('replacement')
        self.controller.change_path(replacement)
        self.assertEqual(self.controller.save().name, 'Custom...')
        self.assertEqual(list(self.repo.runners()), ['Custom...'])
        self.assertTrue(self.controller.remove())
        self.assertEqual(self.repo.runners(), {})

    def test_invalid_missing_directory_and_nonexecutable_do_not_save(self):
        self.controller.select(None, custom=True)
        nonexecutable = Path(self.program())
        nonexecutable.chmod(0o644)
        for path in (str(self.root / 'missing'), str(self.root), str(nonexecutable)):
            self.controller.change_path(path)
            self.assertIsNone(self.controller.save())
        self.assertEqual(len(self.errors), 3)
        self.assertEqual(self.repo.runners(), {})

    def test_persistence_errors_do_not_emit_success_or_clear_selection(self):
        self.controller.select(None, custom=True)
        self.controller.change_path(self.program())
        saved = []
        removed = []
        self.controller.saved.connect(saved.append)
        self.controller.removed.connect(lambda: removed.append(True))
        with patch.object(self.repo, 'save_runner', side_effect=OSError('write failed')):
            self.assertIsNone(self.controller.save())
        self.assertEqual(saved, [])
        record = self.controller.save()
        self.controller.select(record)
        with patch.object(self.repo, 'remove_runner', side_effect=OSError('remove failed')):
            self.assertFalse(self.controller.remove())
        self.assertTrue(self.controller.installed)
        self.assertEqual(removed, [])
        self.assertEqual([title for title, _ in self.errors],
                         ['Unable to save runner', 'Unable to remove runner'])


if __name__ == '__main__':
    unittest.main()
