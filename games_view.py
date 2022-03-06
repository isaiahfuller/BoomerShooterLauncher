import db
import os
import json

from PySide6 import QtCore, QtWidgets
from collections import defaultdict

class GamesView(QtWidgets.QTableWidget):
    def __init__(self, runnerList):
        super().__init__()
        self.runnerList = runnerList
        self.games = []
        self.bases = []
        self.modpacks = []
        self.files = []
        self.game = ""
        self.selected_row = 0
        self.modpack_selected = False
        
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        self.setColumnCount(3)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.refresh()
        self.itemSelectionChanged.connect(self.updateRow)

    def refresh(self):
        self.games.clear()
        self.clearContents()
        dbConnect = db.connect()
        try:
            self.setRowCount(dbConnect.execute('SELECT count(DISTINCT base) from Games').fetchone()[0])
            games = dbConnect.execute('SELECT * FROM Games GROUP BY base ORDER BY game').fetchall()
            allGames = dbConnect.execute('SELECT * FROM Games ORDER BY game').fetchall()
            count = 0
            self.bases = games
            filesArray = defaultdict(list)
            for game in allGames:
                # game = allGames[i] 
                if os.path.exists(game[5]):
                    self.games.append(game)
                    if game in games:
                        self.setItem(count, 0, QtWidgets.QTableWidgetItem(game[7]))
                        # self.setItem(count, 1, QtWidgets.QTableWidgetItem(game[0] + " (" + str(game[3]) + ")"))
                        self.setItem(count, 1, QtWidgets.QTableWidgetItem(game[0]))
                        count = count + 1
                    fileNameSplit = game[5].split("\\")
                    fileName = fileNameSplit[len(fileNameSplit) - 1]
                    filesArray[game[0]].append(f"{fileName} - {game[2]}")
                else:
                    dbConnect.execute('DELETE FROM Games WHERE crc=?', (game[4],))
                    dbConnect.commit()
                    self.refresh()
                    break
            for i in range(len(games)):
                self.setItem(i, 2, QtWidgets.QTableWidgetItem(", ".join(filesArray[games[i][0]])))
            self.loadModpacks()
        except Exception as e:
            print(e)
        finally:
            dbConnect.close()

    def loadModpacks(self):
        appData = os.getenv('APPDATA')
        path = os.path.join(appData, "Boomer Shooter Launcher", "Modpacks")
        os.makedirs(path, exist_ok=True)
        modpacks = [os.path.join(path, f) for f in os.listdir(path)]
        for pack in modpacks:
            with open(pack) as json_file:
                data = json.load(json_file)
                self.modpacks.append(data)
                list = (data["base"] + " (Modded)", data["name"], "modpack", 0, "modpack", [])
                for file in data["files"]:
                    list[5].append(os.path.realpath(file["path"]))
                items = self.findItems(data["base"], QtCore.Qt.MatchExactly)
                if items:
                    pos = items[len(items) - 1].row() + 1
                    self.insertRow(pos)
                    self.setItem(pos, 0, QtWidgets.QTableWidgetItem(list[0]))
                    self.setItem(pos, 1, QtWidgets.QTableWidgetItem(list[1]))
                    self.setItem(pos, 2, QtWidgets.QTableWidgetItem(", ".join(list[5])))

    def updateRow(self):
        if self.selectedItems():
            self.game = self.selectedItems()[1].text()
            for i in range(len(self.bases)):
                if self.selectedItems()[0].text().replace(" (Modded)", "") == self.bases[i][7]:
                    self.selected_row = i
                    self.modpack_selected = True
                    self.files = self.selectedItems()[2].text().split(", ")
                    break
                elif self.selectedItems()[0].text() == self.bases[i][7]:
                    self.selected_row = i
                    self.modpack_selected = False
                    self.files.clear()
                    break