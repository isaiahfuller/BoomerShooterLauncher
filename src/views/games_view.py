"""Generate GamesView"""
import logging

from pathlib import Path
from models.records import Game, Modpack
from PySide6 import QtCore, QtWidgets

class GamesView(QtWidgets.QTableWidget):
    """Displays games in a table"""
    refresh_requested = QtCore.Signal()
    add_modpack_requested = QtCore.Signal(object)
    edit_modpack_requested = QtCore.Signal(object)
    remove_modpack_requested = QtCore.Signal(object)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.status = parent.status
        self.logger = logging.getLogger("Game List")
        self.logger.debug("Building game list")
        self.repository = parent.repository  # Compatibility for legacy dialog callers.

        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.setColumnCount(3)

        header = self.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.setColumnWidth(0, 160)
        self.setColumnWidth(1, 240)
        self.setColumnWidth(2, 400)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.generateMenu)
        self.viewport().installEventFilter(self)

        self.refresh()

    @property
    def selected_record(self):
        """Return the selected domain record, independent of displayed labels."""
        rows = self.selectionModel().selectedRows()
        if not rows:
            return None
        return self.item(rows[0].row(), 0).data(QtCore.Qt.UserRole)

    @property
    def game(self):
        record = self.selected_record
        return record.name if record else ""

    def refresh(self):
        """Compatibility entry point: request a controller-owned refresh."""
        self.refresh_requested.emit()

    def render_records(self, rows):
        """Render supplied records and restore selection by persisted identity."""
        selected = self.selected_record
        identity = (type(selected), selected.name) if selected else None
        blocker = QtCore.QSignalBlocker(self)
        self.clearContents()
        self.setRowCount(len(rows))
        selected_row = None
        for index, record in enumerate(rows):
            if isinstance(record, Game):
                family = record.family or ""
                display_name = ", ".join(dict.fromkeys(
                    version.display_name for version in record.versions)) or record.name
                files = ", ".join(
                    f"{Path(version.path).name if version.path else ''} - {version.version}"
                    for version in record.versions)
            else:
                family = f"{record.base} (Modded)"
                display_name = record.name
                files = ", ".join(file.path or "" for file in record.files)
            for column, label in enumerate((family, display_name, files)):
                item = QtWidgets.QTableWidgetItem(label)
                item.setData(QtCore.Qt.UserRole, record)
                self.setItem(index, column, item)
            if (type(record), record.name) == identity:
                selected_row = index
        self.clearSelection()
        if selected_row is not None:
            self.selectRow(selected_row)
        del blocker
        self.itemSelectionChanged.emit()

    def generateMenu(self, pos):
        """Open menu at current cursor position"""
        if self.itemAt(pos) is not None and hasattr(self, "menu"):
            self.menu.exec_(self.viewport().mapToGlobal(pos))

    def eventFilter(self, qobject: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Create and populate context menu"""
        # pylint: disable=attribute-defined-outside-init
        if(event.type() == QtCore.QEvent.MouseButtonPress and
        event.buttons() == QtCore.Qt.RightButton and qobject is self.viewport()):
            item = self.itemAt(event.pos())
            if item is None:
                return super().eventFilter(qobject, event)
            self.selectRow(item.row())
            record = item.data(QtCore.Qt.UserRole)
            self.menu = QtWidgets.QMenu(self)
            if isinstance(record, Modpack):
                self.menu.addAction("Edit modpack", lambda: self.edit_modpack_requested.emit(record))
                self.menu.addAction("Remove modpack", lambda: self.remove_modpack_requested.emit(record))
            else:
                self.menu.addAction("Add modpack", lambda: self.add_modpack_requested.emit(record))
        return super().eventFilter(qobject, event)
