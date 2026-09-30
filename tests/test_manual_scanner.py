"""Manual directory scans keep all widget callbacks on the GUI thread."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import struct
import sys
import tempfile
import unittest
from pathlib import Path

from PySide6 import QtCore, QtWidgets

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from scanner import GameScanner
from services.game_files import scan_game_file


class ManualScannerTests(unittest.TestCase):
    def test_unmatched_wad_finishes_without_widget_calls_from_worker(self):
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            wad = Path(directory) / 'SIGIL_SHREDS.wad'
            wad.write_bytes(struct.pack('<4sII', b'PWAD', 1, 12) +
                            struct.pack('<II8s', 12, 0, b'CUSTOM'))

            class RejectSave:
                def save_game(self, *args, **kwargs):
                    raise AssertionError('unmatched WAD should not be saved')

            self.assertFalse(scan_game_file(wad, RejectSave()))

            class Window(QtWidgets.QMainWindow):
                def __init__(self):
                    super().__init__()
                    self.status = self.statusBar()
                    self.directoryScanners = []
                    self.refreshed = 0
                    self.callback_threads = []

                def refresh(self):
                    self.refreshed += 1
                    self.callback_threads.append(QtCore.QThread.currentThread())

                def clearStatus(self):
                    self.callback_threads.append(QtCore.QThread.currentThread())

            window = Window()
            scanner = GameScanner(window)
            scanner.directoryCrawl(directory, window.refresh)
            loop = QtCore.QEventLoop()
            window.directoryScanners[0].finished.connect(loop.quit)
            timer = QtCore.QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            timer.start(5000)
            loop.exec()
            timed_out = not timer.isActive()
            timer.stop()
            app.processEvents()
            self.assertFalse(timed_out)
            self.assertEqual(window.directoryScanners, [])
            self.assertGreaterEqual(window.refreshed, 1)
            self.assertTrue(all(thread == app.thread()
                                for thread in window.callback_threads))
            window.close()


if __name__ == '__main__':
    unittest.main()
