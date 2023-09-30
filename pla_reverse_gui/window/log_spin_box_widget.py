"""Labeled QSpinBox that only allows powers of the provided base"""
# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QHBoxLayout,
    QWidget,
    QSpinBox,
    QLabel
)

class LogSpinBox(QWidget):
    """Labeled QSpinBox that only allows powers of the provided base"""
    def __init__(self, base: int, min_pow: int, max_pow: int, label: str = None) -> None:
        super().__init__()
        self.base = base
        self.main_layout = QHBoxLayout(self)
        self.label = None
        if label is not None:
            self.label = QLabel(label)
            self.main_layout.addWidget(self.label)
        self.spin_box = QSpinBox(minimum=base**min_pow, maximum=base**max_pow)
        self.main_layout.addWidget(self.spin_box)
        self.spin_box.stepBy = self.step_by

    def step_by(self, step_value: int):
        """Logarithmic step"""
        self.spin_box.setValue(self.spin_box.value() * self.base**step_value)