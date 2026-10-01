"""Entry-point and compatibility checks after the package move."""

import unittest
from unittest.mock import Mock, patch

import main
from models.iwadinfo import bundled_catalog
from scanner import DirectoryScanWorker, GameScanner
from services.scanner import DirectoryScanWorker as ServiceWorker
from views.main_window import MainWindow
from views.scanner import GameScanner as ScannerDialog


class PackageLayoutTests(unittest.TestCase):
    def test_compatibility_entry_points(self):
        self.assertIs(main.MainWindow, MainWindow)
        self.assertIs(DirectoryScanWorker, ServiceWorker)
        self.assertIs(GameScanner, ScannerDialog)

    def test_bootstrap_creates_application_and_shows_window(self):
        with patch.object(main.QtWidgets, "QApplication") as application, \
                patch.object(main, "MainWindow") as window:
            application.instance.return_value = None
            application.return_value.exec.return_value = 7
            self.assertEqual(main.main(), 7)
            application.assert_called_once_with(main.sys.argv)
            window.return_value.setWindowTitle.assert_called_once_with(
                "Boomer Shooter Launcher"
            )
            window.return_value.show.assert_called_once_with()

    def test_bootstrap_reuses_application(self):
        app = Mock()
        app.exec.return_value = 0
        with patch.object(main.QtWidgets, "QApplication") as application, \
                patch.object(main, "MainWindow"):
            application.instance.return_value = app
            self.assertEqual(main.main(), 0)
            application.assert_not_called()
            app.exec.assert_called_once_with()

    def test_bundled_catalog_is_available(self):
        self.assertTrue(bundled_catalog().definitions)
