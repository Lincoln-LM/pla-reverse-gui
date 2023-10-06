"""Checkable ComboBox"""
# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QLineEdit,
    QComboBox,
)
from qtpy import QtCore
from qtpy.QtGui import QStandardItemModel

# pylint: enable=no-name-in-module


class CheckableComboBox(QComboBox):
    """Checkable ComboBox"""

    changed = QtCore.Signal(int)

    def __init__(self):
        super().__init__()
        self.setModel(QStandardItemModel(self))
        self.line_edit = QLineEdit(self)
        self.line_edit.setReadOnly(True)
        self.line_edit.installEventFilter(self)
        self.view().installEventFilter(self)
        self.line_edit.selectionChanged.connect(self.line_edit.deselect)
        self.line_edit.textChanged.connect(self.line_edit_changed)
        self.view().pressed.connect(self.handle_item_pressed)
        self.model().dataChanged.connect(self.handle_model_data_changed)
        self.setLineEdit(self.line_edit)
        self.item_count = 0
        self.line_edit_locked = False
        self.locked_text = ""

    def line_edit_changed(self, text: str) -> None:
        """Ensure QComboBox does not automatically change lineedit text"""
        if self.line_edit_locked:
            self.line_edit.setText(self.locked_text)
        else:
            self.locked_text = text

    def add_checked_item(self, text: str, value, checked: bool = False) -> None:
        """Add a checked item to the combobox"""
        self.addItem(text, value)
        item = self.model().item(self.item_count, 0)
        item.setCheckState(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
        self.item_count += 1
        self.setMinimumWidth(self.minimumSizeHint().width() + 50)

    def eventFilter(self, watched, event) -> bool:
        """Event filter for line edit"""
        if watched == self.line_edit and event.type() == QtCore.QEvent.MouseButtonPress:
            self.showPopup()
            return True
        return False

    def handle_item_pressed(self, index):
        """Check an item when clicked"""
        item = self.model().itemFromIndex(index)
        item.setCheckState(
            QtCore.Qt.Unchecked
            if item.checkState() == QtCore.Qt.Checked
            else QtCore.Qt.Checked
        )
        self.changed.emit(index)

    def handle_model_data_changed(self):
        """Check an item when clicked"""
        self.line_edit_locked = False
        check_state = any(
            self.model().item(i).checkState() == QtCore.Qt.Checked
            for i in range(self.model().rowCount())
        )
        if check_state:
            self.line_edit.setText(
                ", ".join(
                    self.model().item(i).text()
                    for i in range(self.model().rowCount())
                    if self.model().item(i).checkState() == QtCore.Qt.Checked
                )
            )
        else:
            self.line_edit.setText("Any")
        self.line_edit_locked = True

    def get_checked_values(self) -> tuple:
        """Get the checked values of the combobox"""
        return tuple(
            self.itemData(i)
            for i in range(self.model().rowCount())
            if self.model().item(i).checkState() == QtCore.Qt.Checked
        )
