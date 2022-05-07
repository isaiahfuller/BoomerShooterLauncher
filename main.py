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
        
        self.runner_list = RunnerView(self)
        self.game_list = GamesView(self)
        self.process = GameLauncher(self)
        self.discord_timer = QtCore.QTimer()
        self.discord_details = ""
        self.discord_state = ""
        self.current_runners = []
        self.current_versions = []
        self.runner_text = ""
        self.game_running = False
        self.original_path = ""

        self.game_list.setHorizontalHeaderLabels(["","Name","Files"])
        
        scroll = QtWidgets.QScrollArea()
        scroll.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.game_list)

        file_toolbar = self.addToolBar("Toolbar")
        self.runner_toolbar = self.addToolBar("Launcher")
        file_toolbar.setMovable(False)

        file_toolbar.addAction("&Add Runners", self.runner_list.showWindowFromMenu)
        file_toolbar.addAction("&Add Games", self.gameScanner)
        file_toolbar.addAction("&Add Modpack", self.showModWindow)
        if self.logger.level == logging.DEBUG:
            file_toolbar.addAction("&Refresh", self.game_list.refresh)
        
        self.runner_combobox = QtWidgets.QComboBox()
        self.runner_combobox.addItem("Select a game first")
        self.version_combobox = QtWidgets.QComboBox()
        self.version_combobox.addItem("Versions")
        self.launch_button = QtWidgets.QPushButton("Launch", self)
        self.runner_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.version_combobox.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.runner_combobox.setEnabled(False)
        self.version_combobox.setEnabled(False)

        self.runner_toolbar.addWidget(self.runner_combobox)
        self.runner_toolbar.addWidget(self.version_combobox)
        self.runner_toolbar.addWidget(self.launch_button)

        self.runner_toolbar.setStyleSheet("QToolBar{spacing: 5px;}")

        self.game_list.itemSelectionChanged.connect(self.getRunners)
        self.game_list.itemSelectionChanged.connect(self.getVersions)

        self.launch_button.clicked.connect(self.launchGame)
        self.game_list.cellActivated.connect(self.launchGame)

        self.discord_timer.start(30 * 1000)
        self.discord_timer.timeout.connect(self.updateDiscordStatus)
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
            scanner.crc(files[0], self.game_list.refresh)
    
    def getRunners(self):
        self.current_runners.clear()
        self.runner_combobox.clear()
        if(self.game_list.selectedIndexes()):
            game = self.game_list.selectedItems()[0].text().replace(" (Modded)","")
            
            self.game = game
            self.settings.beginGroup("Runners")
            res = self.settings.childGroups()
            self.settings.endGroup()
            for x in res:
                for y in data.runners:
                    if game in data.runners[y]["games"] and x in y:
                        self.current_runners.append(x)
                if x not in data.runners:
                    self.current_runners.append(x)
            self.logger.debug(f"Compatible runners for \"{game}\": {self.current_runners}")
            if(len(self.current_runners)) == 0:
                self.runner_combobox.adjustSize()
                self.runner_combobox.setEnabled(False)
                self.runner_combobox.addItem("Add source port")
            else:
                self.runner_combobox.adjustSize()
                self.runner_combobox.addItems(self.current_runners)
                self.runner_combobox.setEnabled(True)
        else:
            self.runner_combobox.adjustSize()
            self.runner_combobox.setEnabled(False)
            self.runner_combobox.addItem("Select a game first")

    def getVersions(self):
        self.current_versions.clear()
        self.version_combobox.clear()
        if(self.game_list.selectedIndexes()):
            self.settings.beginGroup("Games")
            bases = self.settings.childGroups()
            res = []
            if "(Modded)" in self.game_list.selectedItems()[0].text():
                game = self.game_list.selectedItems()[0].text().replace(" (Modded)", "")
                for i in bases:
                    if self.settings.value(f"{i}/game") == game:
                        self.settings.beginGroup(i)
                        res = res + self.settings.childGroups()
                        self.settings.endGroup()
            else:
                game = self.game_list.selectedItems()[1].text()
                self.settings.beginGroup(game)
                res = self.settings.childGroups()
                self.settings.endGroup()
            self.settings.endGroup()
            for x in res:
                self.current_versions.append(x)
            self.version_combobox.adjustSize()
            self.version_combobox.addItems(self.current_versions)
            self.version_combobox.setEnabled(True)
            self.logger.debug(f"\"{game}\" versions: {res}")
        else:
            self.version_combobox.adjustSize()
            self.version_combobox.setEnabled(False)
            self.version_combobox.addItem("Versions")

    def launchGame(self):
        version_text = self.version_combobox.currentText()
        self.runner_text = self.runner_combobox.currentText()
        if "(Modded)" not in self.game_list.selectedItems()[0].text():
            game = self.game_list.selectedItems()[1].text()
        else:
            game = self.game
        self.settings.beginGroup(f"Games/{game}/{version_text}")
        try:
            game = self.settings.value("path")
            if len(self.current_runners) == 0:
                self.runner_list.showWindow(self.game)
            else:
                self.original_path = os.getcwd()
                if "(Modded)" in self.game_list.selectedItems()[0].text():
                    self.process.runGame(self.game, game, self.runner_text, self.game_list.files)
                else:
                    self.process.runGame(self.game, game, self.runner_text, [])
                self.discord_details = f"Playing {self.game_list.game} with {self.runner_text}"
                self.discord_state = version_text
                self.game_running = True
                self.updateDiscordStatus()
        except Exception as e:
            self.logger.exception(e)
            self.logger.error("Failed to launch game")
        finally:
            self.settings.endGroup()
        
    def showModWindow(self):
        self.mod_list = ModsView(self.game_list)  
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
            scanner.directoryCrawl(path, self.game_list.refresh)
        return super().dropEvent(event)

    def clearDiscordStatus(self):
        self.discord_state = "Idle"
        self.discord_details = "Looking at games"
        self.game_running = False
        self.updateDiscordStatus()

    def updateDiscordStatus(self):
        self.discord.update(self.discord_state, self.discord_details, self.game_running)
    
    def gameClosed(self):
        os.chdir(self.original_path)

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
