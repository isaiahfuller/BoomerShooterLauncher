"""Manages light/dark mode"""
import threading
import qdarktheme
import darkdetect

class Theme:
    """Sets light/dark mode on start and when system setting changes"""
    def __init__(self, setStyleSheet):
        self.t = threading.Thread(target=darkdetect.listener, args=(self.switch,))
        self.t.daemon = True
        self.t.start()
        self.setStyleSheet = setStyleSheet

        self.switch(darkdetect.theme())

    def switch(self, new_setting):
        """Switch light/dark mode"""
        self.setStyleSheet(qdarktheme.load_stylesheet(new_setting.lower()))
