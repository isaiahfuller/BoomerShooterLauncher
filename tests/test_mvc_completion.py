"""Final MVC boundaries: supplied records, explicit intents, presence ownership."""
import unittest
from unittest.mock import Mock, patch

from PySide6 import QtCore, QtGui, QtWidgets

from controllers.library_controller import LibraryController
from controllers.presence_controller import PresenceController
from models.library import Library
from models.records import Game, InstalledVersion, Modpack
from views.games_view import GamesView
from views.mods_view import ModsView


class MVCCompletionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.repo = Mock()
        self.game = Game('Doom', 'Doom', 1993, (
            InstalledVersion('legacy', '1', None, '/doom.wad', label='DOOM: KEX Edition'),))
        self.pack = Modpack('Doom', 'Doom', ())
        self.repo.library.return_value = Library((self.game,), (), (self.pack,))
        self.parent = QtWidgets.QMainWindow()
        self.parent.repository = self.repo
        self.parent.status = self.parent.statusBar()
        self.view = GamesView(self.parent)
        self.controller = LibraryController(self.repo)
        self.view.refresh_requested.connect(self.controller.refresh)
        self.controller.records_changed.connect(self.view.render_records)

    def tearDown(self):
        self.parent.close()
        self.parent.deleteLater()

    def test_refresh_is_controller_owned_and_preserves_typed_identity(self):
        self.repo.library.assert_not_called()
        self.assertIs(self.view.repository, self.repo)
        self.view.refresh()
        self.repo.library.assert_called_once_with()
        self.assertEqual(self.view.item(0, 1).text(), 'DOOM: KEX Edition')
        self.view.selectRow(1)
        self.view.refresh()
        self.assertEqual(self.view.selected_record, self.pack)
        self.repo.library.return_value = Library((self.game,), (), ())
        self.view.refresh()
        self.assertIsNone(self.view.selected_record)

    def test_context_actions_capture_record_not_display_or_later_selection(self):
        self.view.refresh()
        self.view.selectRow(1)
        received = []
        self.view.edit_modpack_requested.connect(received.append)
        point = self.view.visualItemRect(self.view.item(1, 0)).center()
        event = QtGui.QMouseEvent(
            QtCore.QEvent.MouseButtonPress, QtCore.QPointF(point),
            QtCore.QPointF(point), QtCore.Qt.RightButton,
            QtCore.Qt.RightButton, QtCore.Qt.NoModifier)
        self.view.eventFilter(self.view.viewport(), event)
        self.view.selectRow(0)
        self.view.menu.actions()[0].trigger()
        self.assertEqual(received, [self.pack])

    def test_editor_accepts_explicit_record_without_parent_selection(self):
        editor = ModsView(self.parent)
        self.assertIs(editor.controller.repository, self.repo)
        with patch.object(editor, 'showWindow'):
            editor.openFile(self.pack)
        self.assertEqual(editor.mods, self.pack)
        refreshed = []
        editor.refresh_requested.connect(lambda: refreshed.append(True))
        editor.close()
        self.assertEqual(refreshed, [True])

    def test_presence_lifecycle_and_shutdown(self):
        service = Mock()
        controller = PresenceController(service)
        messages = []
        controller.status_changed.connect(messages.append)
        controller.start()
        self.assertTrue(controller.timer.isActive())
        service.update.assert_called_with('Idle...', 'Looking at games')
        controller.playing('Doom', 'UZDoom', 'KEX')
        self.assertTrue(controller.running)
        self.assertEqual(messages[-1], 'Playing Doom with UZDoom (KEX)')
        controller.timer.timeout.emit()
        service.update.assert_called_with('KEX', 'Playing Doom with UZDoom')
        controller.idle()
        self.assertFalse(controller.running)
        controller.stop()
        controller.stop()
        self.assertFalse(controller.timer.isActive())
        service.clear.assert_called_once_with()
        service.update.reset_mock()
        controller.update()
        service.update.assert_not_called()


if __name__ == '__main__':
    unittest.main()
