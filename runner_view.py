from PySide6 import QtCore, QtWidgets, QtGui
from pathlib import Path
import logging
import os
import sys
import db
import data
import webbrowser
import platform
import subprocess

class RunnerView(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.logger = logging.getLogger("Modpack Editor")
        # print(parent)

        match platform.system():
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("BoomerShooterLauncher", "Boomer Shooter Launcher")

        self.boxLayout = QtWidgets.QVBoxLayout()
        self.openedFromMenu = False

        self.runnerList = QtWidgets.QListWidget()
        self.runnerList.itemSelectionChanged.connect(self.updateText)

        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setLayout(self.boxLayout)

        self.descriptionLabel = QtWidgets.QLabel()
        self.descriptionLabel.setWordWrap(True)

        self.boxLayout.addWidget(self.runnerList)
        self.boxLayout.addWidget(self.descriptionLabel)

        self.buttonBox = QtWidgets.QHBoxLayout()
        self.downloadButton = QtWidgets.QPushButton("Download", self)

        self.selectInstalledButton = QtWidgets.QPushButton("Select", self)
        
        self.downloadButton.setEnabled(False)
        self.selectInstalledButton.setEnabled(False)
        self.downloadButton.clicked.connect(self.getDownloadLink)
        self.selectInstalledButton.clicked.connect(self.addToDb)

        self.buttonBox.addWidget(self.downloadButton)
        self.buttonBox.addWidget(self.selectInstalledButton)

        self.boxLayout.addLayout(self.buttonBox)

        self.runnerDialog = QtWidgets.QFileDialog(parent=self)

        self.setCentralWidget(self.scroll)
        self.setWindowTitle("Source Ports")

    def showWindowFromMenu(self):
        self.openedFromMenu = True
        self.showWindow("all")

    def showWindow(self, game):
        self.resize(400, 300)
        self.builder(game)
        self.show()

    def builder(self, game):
        self.runnerList.clear()
        self.game = game
        # if game == "all":
        #     try:
        #         c = db.connect()
        #         query = "SELECT * FROM Runners"
        #         allRunners = c.execute(query).fetchall()
        #     finally:
        #         c.close()
        #     for i in allRunners:
        #         self.runnerList.addItem(f"{i[0]} [installed]")
        #     for i in data.runners:
        #         if not self.runnerList.findItems(i, QtCore.Qt.MatchContains):
        #             self.runnerList.addItem(i)
        #     # self.runnerList.addItems(list(data.runners.keys()))
        if game == "all":
            self.settings.beginGroup("Runners")
            allRunners = self.settings.childGroups()
            self.settings.endGroup()
            for i in allRunners:
                self.runnerList.addItem(f"{i} [installed]")
            for i in data.runners:
                if not self.runnerList.findItems(i, QtCore.Qt.MatchContains):
                    self.runnerList.addItem(i)
        else:
            for i in data.runners:
                if game in data.runners[i]["games"]:
                    if not self.runnerList.findItems(i, QtCore.Qt.MatchExactly):
                        self.runnerList.addItem(i)
    
    def setRunner(self):
        if "[installed]" in self.name:
            installed = True
        else:
            installed = False
        self.name = self.name.replace(" [installed]", "")
        for i in data.runners:
            if i == self.name:
                self.executable = data.runners[i]["executable"]
                self.descriptionLabel.setText("Description:\n" + data.runners[i]["description"])
                self.url = data.runners[i]["link"]
                self.downloadButton.setEnabled(True)
                if installed: self.selectInstalledButton.setEnabled(False)
                else: self.selectInstalledButton.setEnabled(True)
                break

    def getDownloadLink(self):
        webbrowser.open(self.url)

    def updateText(self):
        self.name = self.runnerList.currentItem().text()
        self.setRunner()

    def addToDb(self):
        db.init()
        self.runnerDialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        con = db.connect()
        match platform.system():
            case "Windows":
                files = self.runnerDialog.getOpenFileUrl()
                filePath = files[0].toLocalFile()
            case "Linux":
                exe = self.executable
                file = subprocess.run(["which", exe], stdout=subprocess.PIPE)
                filePath = Path(file.stdout.decode("utf-8"))
        try:    
            if Path(filePath).stem.strip() == self.executable:
                insertQuery = "INSERT INTO Runners values (?, ?, ?, ?)"
                insertData = (self.runnerList.selectedItems()[0].text(), "blank", str(filePath).strip(), self.executable)
                con.execute(insertQuery, insertData)
                con.commit()
                self.settings.beginGroup(f"Runners/{self.runnerList.selectedItems()[0].text()}")
                self.settings.setValue("path", str(filePath).strip())
                self.settings.setValue("executable", self.executable)
                self.settings.endGroup()
        except Exception as e:
            logging.exception(e)
            logging.warning(f"[Runner List] Failed to add {self.runnerList.selectedItems()[0].text()} to db")
        finally:
            con.close()
            if len(os.fspath(filePath)) > 0:
                self.builder(self.game)
                self.selectInstalledButton.setEnabled(False)
                if not self.openedFromMenu: self.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.runnerList.clear()
        self.openedFromMenu = False
        self.parent().getRunners()
        return super().closeEvent(event)