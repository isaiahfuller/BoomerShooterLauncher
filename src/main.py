"""Application entry point for Boomer Shooter Launcher."""

import logging
import sys

from PySide6 import QtWidgets

from views.main_window import MainWindow


def main():
    """Create the application and show its main window."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    logging.basicConfig()
    if "--debug" in sys.argv:
        logging.root.setLevel(logging.DEBUG)
    window = MainWindow()
    window.setWindowTitle("Boomer Shooter Launcher")
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
