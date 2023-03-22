"""Widget for entering a range"""

# pylint: disable=no-name-in-module
from qtpy.QtWidgets import QWidget, QLabel, QSpinBox, QHBoxLayout

# pylint: enable=no-name-in-module


class RangeWidget(QWidget):
    """Widget for entering a range"""

    def __init__(self, minimum: int, maximum: int, label: str = None) -> None:
        super().__init__()
        self.main_layout = QHBoxLayout(self)
        self.label = None
        if label is not None:
            self.label = QLabel(label)
            self.main_layout.addWidget(self.label)
        self.min_entry = QSpinBox(minimum=minimum, maximum=maximum)
        self.main_layout.addWidget(self.min_entry)
        self.min_entry.setValue(minimum)
        self.max_entry = QSpinBox(minimum=minimum, maximum=maximum)
        self.main_layout.addWidget(self.max_entry)
        self.max_entry.setValue(maximum)

    def get_range(self) -> range:
        """Get entered range"""
        return range(self.min_entry.value(), self.max_entry.value() + 1)
