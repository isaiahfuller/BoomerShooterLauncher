from PySide6 import QtCore, QtWidgets, QtGui
import db
import data
import webbrowser

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
            for i in data.runners:
                if game in i["games"]:
                    if not self.runnerList.findItems(i["name"], QtCore.Qt.MatchExactly):
                        self.runnerList.addItem(i["name"])
    
    def setRunner(self, name):
        runners = []
        name = name.replace(" [installed]", "")
        for i in data.runners:
            runners.append(i)
        for j in runners:
            for i in data.runners[j]:
                if i["name"] == name:
                    self.runner = j
                    self.descriptionLabel.setText("Description:\n" + i["description"])
                    self.url = i["link"]
                    self.downloadButton.setEnabled(True)
                    self.selectInstalledButton.setEnabled(True)
                    break

    def getDownloadLink(self):
        webbrowser.open(self.url)

    def updateText(self):
        name = self.runnerList.currentItem().text()
        self.setRunner(name)

    def addToDb(self):
        db.init()
        self.runnerDialog.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        con = db.connect()
        files = self.runnerDialog.getOpenFileUrl()
        try:
            if not files[0].toLocalFile() == "":
                insertQuery = "INSERT INTO Runners values (?, ?, ?)"
                insertData = (self.runnerList.selectedItems()[0].text(), self.runner, files[0].toLocalFile())
                con.execute(insertQuery, insertData)
                con.commit()
        except Exception as e:
            print(e)
        finally:
            con.close()
            if not files[0].toLocalFile() == "":
                if not self.openedFromMenu: self.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.runnerList.clear()
        self.openedFromMenu = False
        return super().closeEvent(event)