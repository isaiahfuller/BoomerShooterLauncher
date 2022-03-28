from PySide6 import QtCore, QtWidgets, QtGui
from pathlib import Path
import os
import db
import data
import webbrowser
import platform
import subprocess

class RunnerView(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
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

        self.runnerDialog = QtWidgets.QFileDialog(self)

        self.setCentralWidget(self.scroll)
        self.setWindowTitle("Source Ports")

    def showWindowFromMenu(self):
        self.openedFromMenu = True
        self.showWindow("all", "all")

    def showWindow(self, game, runner):
        self.resize(400, 300)
        self.builder(game, runner)
        self.show()

    def builder(self, game, runner):
        self.runnerList.clear()
        self.game = game
        self.runner = runner
        if game == "all":
            try:
                c = db.connect()
                query = "SELECT * FROM Runners"
                allRunners = c.execute(query).fetchall()
            finally:
                c.close()
            for i in allRunners:
                self.runnerList.addItem(f"{i[0]} [installed]")
            for i in data.runners:
                for j in data.runners[i]:
                    if not self.runnerList.findItems(j["name"], QtCore.Qt.MatchContains):
                        self.runnerList.addItem(j["name"])
        else:
            for i in data.runners[runner]:
                if game in i["games"]:
                    if not self.runnerList.findItems(i["name"], QtCore.Qt.MatchExactly):
                        self.runnerList.addItem(i["name"])
    
    def setRunner(self):
        runners = []
        if "[installed]" in self.name:
            installed = True
        else:
            installed = False
        self.name = self.name.replace(" [installed]", "")
        for i in data.runners:
            runners.append(i)
        for j in runners:
            for i in data.runners[j]:
                if i["name"] == self.name:
                    self.executable = i["executable"]
                    self.runner = j
                    self.descriptionLabel.setText("Description:\n" + i["description"])
                    self.url = i["link"]
                    self.downloadButton.setEnabled(True)
                    if installed: self.selectInstalledButton.setEnabled(False)
                    else: self.selectInstalledButton.setEnabled(True)
                    break

    def getDownloadLink(self):
        webbrowser.open(self.url)

    def updateText(self):
        name = self.runnerList.currentItem().text()
        self.name = name
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
            if filePath.stem.strip() == self.executable:
                insertQuery = "INSERT INTO Runners values (?, ?, ?, ?)"
                insertData = (self.runnerList.selectedItems()[0].text(), self.runner, str(filePath).strip(), self.executable)
                con.execute(insertQuery, insertData)
                con.commit()
        except Exception as e:
            print(e)
        finally:
            con.close()
            if len(os.fspath(filePath)) > 0:
                self.builder(self.game, self.runner)
                self.selectInstalledButton.setEnabled(False)
                if not self.openedFromMenu: self.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.runnerList.clear()
        self.openedFromMenu = False
        return super().closeEvent(event)