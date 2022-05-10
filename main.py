import sys
import data
import platform
from discord import Discord
from PySide6 import QtCore, QtWidgets, QtGui
from games_view import *
from scanner import *
from runner_view import *
from mods_view import *
from launcher import *

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("Main window")
        if "--debug" in sys.argv:
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Debug mode")
        self.platform = platform.system()

        match self.platform:
            case "Windows":
                self.settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
            case "Linux":
                self.settings = QtCore.QSettings("boomershooterlauncher", "config")

        self.readSettings()
        self.discord = Discord()
        
        self.runnerList = RunnerView(self)
        self.gameList = GamesView(self)
        self.process = GameLauncher(self)
        self.discordTimer = QtCore.QTimer()
        self.discordDetails = ""
        self.discordState = ""
        self.currentRunners = []
        self.currentVersions = []
        self.runnerText = ""
        self.game_running = False
        self.originalPath = ""

        self.gameList.setHorizontalHeaderLabels(["","Name","Files"])
        
        scroll = QtWidgets.QScrollArea()
        scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.gameList)

        fileToolbar = self.addToolBar("Toolbar")
        self.runnerToolbar = self.addToolBar("Launcher")
        fileToolbar.setMovable(False)

        fileToolbar.addAction("&Add Runners", self.runnerList.showWindowFromMenu)
        fileToolbar.addAction("&Add Games", self.gameScanner)
        fileToolbar.addAction("&Add Modpack", self.showModWindow)
        if self.logger.level == logging.DEBUG:
            fileToolbar.addAction("&Refresh", self.gameList.refresh)
        
        self.runnerCombobox = QtWidgets.QComboBox()
        self.runnerCombobox.addItem("Select a game first")
        self.versionCombobox = QtWidgets.QComboBox()
        self.versionCombobox.addItem("Versions")
        self.launchButton = QtWidgets.QPushButton("Launch", self)
        self.runnerCombobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.versionCombobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.runnerCombobox.setEnabled(False)
        self.versionCombobox.setEnabled(False)

        self.runnerToolbar.addWidget(self.runnerCombobox)
        self.runnerToolbar.addWidget(self.versionCombobox)
        self.runnerToolbar.addWidget(self.launchButton)

        self.runnerToolbar.setStyleSheet("QToolBar{spacing: 5px;}")

        self.gameList.itemSelectionChanged.connect(self.getRunners)
        self.gameList.itemSelectionChanged.connect(self.getVersions)

        self.launchButton.clicked.connect(self.launchGame)
        self.gameList.cellActivated.connect(self.launchGame)

        self.discordTimer.start(30 * 1000)
        self.discordTimer.timeout.connect(self.updateDiscordStatus)
        self.process.finished.connect(self.clearDiscordStatus)
        self.process.finished.connect(self.gameClosed)
        self.clearDiscordStatus()
        self.updateDiscordStatus()

        self.setCentralWidget(scroll)
        self.setAcceptDrops(True)

    def writeSettings(self):
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.endGroup()

    def readSettings(self):
        self.settings.beginGroup("MainWindow")
        geometry = self.settings.value("geometry", QtCore.QByteArray())
        if (geometry.isEmpty()):
            self.setGeometry(0, 0, 800, 600)
        else:
            self.restoreGeometry(geometry)
        self.settings.endGroup()

    def gameScanner(self):
        scanner = GameScanner(self)
        if scanner.exec():
            files = scanner.selectedFiles()
            scanner.crc(files[0], self.gameList.refresh)
    
    def getRunners(self):
        self.currentRunners.clear()
        self.runnerCombobox.clear()
        if(self.gameList.selectedIndexes()):
            game = self.gameList.selectedItems()[0].text().replace(" (Modded)","")
            
            self.game = game
            self.settings.beginGroup("Runners")
            res = self.settings.childGroups()
            self.settings.endGroup()
            for x in res:
                for y in data.runners:
                    if game in data.runners[y]["games"] and x in y:
                        self.currentRunners.append(x)
                if x not in data.runners:
                    self.currentRunners.append(x)
            self.logger.debug(f"Compatible runners for \"{game}\": {self.currentRunners}")
            if(len(self.currentRunners)) == 0:
                self.runnerCombobox.adjustSize()
                self.runnerCombobox.setEnabled(False)
                self.runnerCombobox.addItem("Add source port")
            else:
                self.runnerCombobox.adjustSize()
                self.runnerCombobox.addItems(self.currentRunners)
                self.runnerCombobox.setEnabled(True)
        else:
            self.runnerCombobox.adjustSize()
            self.runnerCombobox.setEnabled(False)
            self.runnerCombobox.addItem("Select a game first")

    def getVersions(self):
        self.currentVersions.clear()
        self.versionCombobox.clear()
        if(self.gameList.selectedIndexes()):
            self.settings.beginGroup("Games")
            bases = self.settings.childGroups()
            res = []
            if "(Modded)" in self.gameList.selectedItems()[0].text():
                game = self.gameList.selectedItems()[0].text().replace(" (Modded)", "")
                for i in bases:
                    if self.settings.value(f"{i}/game") == game:
                        self.settings.beginGroup(i)
                        res = res + self.settings.childGroups()
                        self.settings.endGroup()
            else:
                game = self.gameList.selectedItems()[1].text()
                self.settings.beginGroup(game)
                res = self.settings.childGroups()
                self.settings.endGroup()
            self.settings.endGroup()
            for x in res:
                self.currentVersions.append(x)
            self.versionCombobox.adjustSize()
            self.versionCombobox.addItems(self.currentVersions)
            self.versionCombobox.setEnabled(True)
            self.logger.debug(f"\"{game}\" versions: {res}")
        else:
            self.versionCombobox.adjustSize()
            self.versionCombobox.setEnabled(False)
            self.versionCombobox.addItem("Versions")

    def launchGame(self):
        version_text = self.versionCombobox.currentText()
        self.runnerText = self.runnerCombobox.currentText()
        if "(Modded)" not in self.gameList.selectedItems()[0].text():
            game = self.gameList.selectedItems()[1].text()
            self.settings.beginGroup(f"Games/{game}/{version_text}")
        else:
            keys = self.settings.allKeys()
            for i in keys:
                if f"/{version_text}/crc" in i:
                    game = i.replace("/crc","")
                    self.settings.beginGroup(game)
        try:
            game = self.settings.value("path")
            if len(self.currentRunners) == 0:
                self.runnerList.showWindow(self.game)
            else:
                self.originalPath = os.getcwd()
                if "(Modded)" in self.gameList.selectedItems()[0].text():
                    self.process.runGame(self.game, game, self.runnerText, self.gameList.files)
                else:
                    self.process.runGame(self.game, game, self.runnerText, [])
                self.discordDetails = f"Playing {self.gameList.game} with {self.runnerText}"
                self.discordState = version_text
                self.game_running = True
                self.updateDiscordStatus()
        except Exception as e:
            self.logger.exception(e)
            self.logger.error("Failed to launch game")
        finally:
            self.settings.endGroup()
        
    def showModWindow(self):
        self.mod_list = ModsView(self.gameList)  
        self.mod_list.showWindow()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        scanner = GameScanner(self)
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for path in files:
            scanner.directoryCrawl(path, self.gameList.refresh)
        return super().dropEvent(event)

    def clearDiscordStatus(self):
        self.discordState = "Idle"
        self.discordDetails = "Looking at games"
        self.game_running = False
        self.updateDiscordStatus()

    def updateDiscordStatus(self):
        self.discord.update(self.discordState, self.discordDetails, self.game_running)
    
    def gameClosed(self):
        os.chdir(self.originalPath)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.writeSettings()
        return super().closeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    logging.basicConfig()
    if "--debug" in sys.argv:
        logging.root.setLevel(logging.DEBUG)
    widget = MainWindow()
    widget.setWindowTitle("Boomer Shooter Launcher")
    widget.show()

    sys.exit(app.exec())
