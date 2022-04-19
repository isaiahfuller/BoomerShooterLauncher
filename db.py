import os
import sys
import sqlite3
import platform 
import logging
from pathlib import Path

logger = logging.getLogger("Database")

def init():
    logger.debug("Database init")
    try:
        con = connect()
        test1 = con.execute('CREATE TABLE IF NOT EXISTS Games(base TEXT, name TEXT, version TEXT, year INTEGER, crc TEXT PRIMARY KEY, path TEXT, runners TEXT, game TEXT)')
        test2 = con.execute('CREATE TABLE IF NOT EXISTS Runners(name TEXT PRIMARY KEY, game TEXT, path TEXT NOT NULL, executable TEXT NOT NULL)')
    finally:
        con.close()

def connect():
    if platform.system() == "Windows":
        appData = os.getenv('APPDATA')
        path = Path(appData, "fullerSpectrum/", "Boomer Shooter Launcher/")
    else:
        path = Path(f"{Path.home()}/.config/BoomerShooterLauncher/")
    os.makedirs(Path(path, "Modpacks"), exist_ok=True)
    con = sqlite3.connect(os.fspath(path) + "/games.db")
    return con

def addGame(gameInfo, self):
    c = connect()
    try:
        c.execute("INSERT INTO Games values (?, ?, ?, ?, ?, ?, ?, ?)", gameInfo)
        c.commit()
    except Exception as e:
        print(e)
    finally: 
        c.close()