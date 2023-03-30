"""Shows window on first run"""
import platform
import sys
import logging
from PySide6 import QtWidgets, QtGui

class FirstRun(QtWidgets.QDialog):
    """Shows window on first run"""
    def __init__(self, parent):
        super().__init__(parent=parent)
        parent = self.parent()
        # self.status = self.statusBar()
        self.logger = logging.getLogger("Main window")
        if "--debug" in sys.argv:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug mode")
        self.platform = platform.system()
        addGameButton = QtWidgets.QPushButton("Add Games")
        addPortButton = QtWidgets.QPushButton("Add Source Port")
        importButton = QtWidgets.QPushButton("Import Modpack")
        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(QtWidgets.QLabel("Right now, this launcher only supports Doom-based games."))
        mainLayout.addWidget(QtWidgets.QLabel("You can start by adding a folder with games (Doom 3 BFG and Doom Eternal work): "))
        mainLayout.addWidget(addGameButton, 0, QtGui.Qt.AlignRight)
        mainLayout.addWidget(QtWidgets.QLabel("Choose a source port to run the game with: "))
        mainLayout.addWidget(addPortButton, 0, QtGui.Qt.AlignRight)
        mainLayout.addWidget(QtWidgets.QLabel("If you have a modpack, you can import it here: "))
        mainLayout.addWidget(importButton, 0, QtGui.Qt.AlignRight)

        addGameButton.clicked.connect(parent.gameScanner)
        addPortButton.clicked.connect(parent.showRunnerList)
        importButton.clicked.connect(parent.importModpack)

        self.setLayout(mainLayout)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Close"""
        self.deleteLater()
        return super().closeEvent(event)

    def showWindow(self):
        """Open window and set size/location"""
        self.resize(400,300)
        mainLocation = self.parent().frameGeometry()
        x = mainLocation.x() + mainLocation.width() / 2 - self.width() / 2
        y = mainLocation.y() + mainLocation.height() / 2 - self.height() / 2
        self.move(x, y)
        self.setWindowTitle("Welcome")
        self.show()
