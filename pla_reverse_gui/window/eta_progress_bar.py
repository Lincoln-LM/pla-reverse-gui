"""Progress bar with a time estimation"""

import time

# pylint: disable=no-name-in-module
from qtpy.QtWidgets import QProgressBar

# pylint: enable=no-name-in-module


class ETAProgressBar(QProgressBar):
    """Progress bar with a time estimation"""

    def __init__(self, parent=None) -> None:
        self.start_time: float = None
        super().__init__(parent)

    def setValue(self, value: int) -> None:
        if self.maximum() == 0:
            return
        QProgressBar.setValue(self, value)
        if self.start_time is None or value == 0:
            self.start_time = time.time()
        if value == 0:
            eta_str = "..."
        else:
            elapsed_time = time.time() - self.start_time
            eta = (self.maximum() - value) * elapsed_time / value
            eta_minutes, eta_seconds = divmod(eta, 60)
            eta_hours, eta_minutes = divmod(eta_minutes, 60)
            eta_str = (
                (f"{eta_hours:02.00f}:" if eta_hours > 0 else "")
                + (f"{eta_minutes:02.00f}:" if eta_minutes > 0 else "")
                + f"{eta_seconds:05.02f}"
                + ("s" if eta_hours == 0 and eta_minutes == 0 else "")
            )
        self.setFormat(f"{value/self.maximum()*100:.00f}% Estimated time: {eta_str}")

    def setMaximum(self, maximum: int) -> None:
        if maximum == -1:
            maximum = 0
        QProgressBar.setMaximum(self, maximum)
        self.start_time = None
