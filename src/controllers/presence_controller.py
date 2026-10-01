"""Coordinate presence independently of widgets and scan status messages."""
from PySide6 import QtCore


class PresenceController(QtCore.QObject):
    status_changed = QtCore.Signal(str)

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.state = "Idle..."
        self.details = "Looking at games"
        self.running = False
        self.closed = False
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(30_000)
        self.timer.timeout.connect(self.update)

    def start(self):
        self.timer.start()
        self.idle()

    def playing(self, title, runner, version):
        self.details = f"Playing {title} with {runner}"
        self.state = version
        self.running = True
        self.update()
        self.status_changed.emit(f"{self.details} ({version})")

    def idle(self):
        self.state = "Idle..."
        self.details = "Looking at games"
        self.running = False
        self.update()
        self.status_changed.emit("Idle...")

    def update(self):
        if not self.closed:
            self.service.update(self.state, self.details)

    def stop(self):
        self.timer.stop()
        if not self.closed:
            self.closed = True
            self.service.clear()
