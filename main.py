import sys
import db
import data
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
        db.init()
        self.readSettings()
        self.discord = Discord()
        
        self.runner_list = RunnerView()
        self.game_list = GamesView(self.runner_list)
        self.process = QtCore.QProcess()
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

        file_menu = QtWidgets.QMenu("&File")
        file_toolbar.addAction("&Manage Ports", self.runner_list.showWindowFromMenu)
        file_toolbar.addAction("&Add Modpack", self.showModWindow)

        file_menu.addAction("&Add Games", self.gameScanner)
        file_menu.addAction("&Manage Ports", self.runner_list.showWindowFromMenu)

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
        settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
        settings.beginGroup("MainWindow")
        settings.setValue("geometry", self.saveGeometry())
        settings.endGroup()

    def readSettings(self):
        settings = QtCore.QSettings("fullerSpectrum", "Boomer Shooter Launcher")
        settings.beginGroup("MainWindow")
        geometry = settings.value("geometry", QtCore.QByteArray())
        if (geometry.isEmpty()):
            self.setGeometry(800, 800, 600, 600)
        else:
            self.restoreGeometry(geometry)
        settings.endGroup()

    def gameScanner(self):
        scanner = GameScanner()
        if scanner.exec():
            files = scanner.selectedFiles()
            scanner.crc(files[0], self.game_list.refresh)
    
    def getRunners(self):
        c = db.connect()
        self.current_runners.clear()
        self.runner_combobox.clear()
        if(self.game_list.selectedIndexes()):
            # i = self.game_list.selectedIndexes()[0].row()
            i = self.game_list.selected_row
            runner = self.game_list.bases[i][6]
            game = self.game_list.bases[i][7]
            self.runner = runner 
            self.game = game
            try:
                query = "SELECT name FROM Runners WHERE game=?"
                res = c.execute(query, (runner,)).fetchall()
            finally:
                c.close()
            if len(res) == 0:
                self.runner_combobox.addItem("Add source port")
                self.runner_combobox.setEnabled(False)
            else:
                for x in res:
                    for y in data.runners[runner]:
                        if game in y["games"] and y["name"] in x:
                            self.current_runners.append(x[0])
                self.runner_combobox.adjustSize()
                self.runner_combobox.addItems(self.current_runners)
                self.runner_combobox.setEnabled(True)
        else:
            self.runner_combobox.adjustSize()
            self.runner_combobox.setEnabled(False)
            self.runner_combobox.addItem("Select a game first")

    def getVersions(self):
        c = db.connect()
        self.current_versions.clear()
        self.version_combobox.clear()
        if(self.game_list.selectedIndexes()):
            try:
                if "(Modded)" in self.game_list.selectedItems()[0].text():
                    game = self.game_list.selectedItems()[0].text().replace(" (Modded)", "")
                    query = "SELECT version, path, name FROM Games WHERE game = ? ORDER BY name"
                    res = c.execute(query, (game,)).fetchall()
                else:
                    game = self.game_list.selectedItems()[1].text()
                    query = "SELECT version, path, name FROM Games WHERE base = ? ORDER BY name"
                    res = c.execute(query, (game,)).fetchall()
            finally:
                c.close()
            for x in res:
                self.current_versions.append(x[2])
            self.version_combobox.adjustSize()
            self.version_combobox.addItems(self.current_versions)
            self.version_combobox.setEnabled(True)
        else:
            self.version_combobox.adjustSize()
            self.version_combobox.setEnabled(False)
            self.version_combobox.addItem("Versions")

    def launchGame(self):
        version_text = self.version_combobox.currentText()
        self.runner_text = self.runner_combobox.currentText()
        c = db.connect()
        try:
            game_query = "SELECT path, runners from Games WHERE name = ?"
            runner_query = "SELECT * from Runners WHERE name = ?"
            game_data = c.execute(game_query, (version_text,)).fetchone()
            game = game_data[0]
            game_type = game_data[1]
            # print(game_data)

            if self.runner_text == "Add source port":
                self.runner_list.showWindow(self.game, game_type)
            else:
                self.original_path = os.getcwd()
                runner = c.execute(runner_query, (self.runner_text,)).fetchone()
                run = runGame(self.game, game, runner, self.game_list.files)
                run_path = run[1]
                if self.runner_text in ["Chocolate Doom", "Crispy Doom"]:
                    run_path = os.path.join(run[1], self.game_list.game)
                    os.makedirs(run_path, exist_ok=True)
                if self.runner_text == "GZDoom":
                    for retry in range(100):
                        try:
                            os.rename(os.path.join(run[1],"Save"), os.path.join(run[1],".Save"))
                            os.makedirs(os.path.join(run[1], self.game_list.game), exist_ok=True)
                            os.rename(os.path.join(run[1], self.game_list.game), os.path.join(run[1],"Save"))
                            break
                        except:
                            print(f"Folder swap failed {retry}x")
                os.chdir(run_path)
                spArray = run[0]
                self.process.start(spArray[0], spArray[1:])
                self.discord_details = f"Playing {self.game_list.game} with {self.runner_text}"
                self.discord_state = version_text
                self.game_running = True
                self.updateDiscordStatus()
        finally:
            c.close()
        
    def showModWindow(self):
        self.mod_list = ModsView(self.game_list)  
        self.mod_list.showWindow()
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        scanner = GameScanner()
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
        if self.runner_text == "GZDoom":
            for retry in range(100):
                try:
                    os.rename(os.path.join(os.getcwd(),"Save"), os.path.join(os.getcwd(),self.game_list.game))
                    os.rename(os.path.join(os.getcwd(),".Save"), os.path.join(os.getcwd(),"Save"))
                    break
                except:
                    print(f"Folder swap back failed {retry}x")
        os.chdir(self.original_path)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.writeSettings()
        return super().closeEvent(event)

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MainWindow()
    # widget.resize(800, 600)
    widget.setWindowTitle("Boomer Shooter Launcher")
    widget.show()

    sys.exit(app.exec())
