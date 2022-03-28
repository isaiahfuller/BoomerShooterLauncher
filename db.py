import os
import sqlite3
import platform 
from pathlib import Path

def init():
    try:
        con = connect()
        con.execute('CREATE TABLE IF NOT EXISTS Games(base TEXT, name TEXT, version TEXT, year INTEGER, crc TEXT PRIMARY KEY, path TEXT, runners TEXT, game TEXT)')
        con.execute('CREATE TABLE IF NOT EXISTS Runners(name TEXT PRIMARY KEY, game TEXT, path TEXT NOT NULL, executable TEXT NOT NULL)')
    finally:
        con.close()

def connect():
    if platform.system() == "Windows":
        appData = os.getenv('APPDATA')
        path = Path(appData, "fullerSpectrum/", "Boomer Shooter Launcher/")
    else:
        path = Path(f"{Path.home()}/.config/BoomerShooterLauncher/")
    os.makedirs(path, exist_ok=True)
    con = sqlite3.connect(os.fspath(path) + "/games.db")
    return con

def addGame(gameInfo, tableRefresh, self):
    c = connect()
    try:
        c.execute("INSERT INTO Games values (?, ?, ?, ?, ?, ?, ?, ?)", gameInfo)
        c.commit()
    except Exception as e:
        print(e)
    finally: 
        c.close()
    tableRefresh()