"""QTableWidget for spawner paths"""

# pylint: disable=no-name-in-module
from PySide6.QtWidgets import (
    QTableWidget,
    QSizePolicy,
)

# pylint: enable=no-name-in-module


class ResultTableWidget(QTableWidget):
    """QTableWidget for spawner paths"""

    COLUMNS = (
        ("Advances", 100),
        ("Path", 100),
        ("Species", 100),
        ("Shiny", 80),
        ("Alpha", 80),
        ("Nature", 80),
        ("Ability", 100),
        ("HP", 50),
        ("Atk", 50),
        ("Def", 50),
        ("SpA", 50),
        ("SpD", 50),
        ("Spe", 50),
        ("Gender", 70),
        ("Height", 80),
        ("Weight", 80),
    )

    def __init__(self):
        super().__init__()

        self.setColumnCount(16)
        self.setHorizontalHeaderLabels([column[0] for column in self.COLUMNS])
        for i, (_, width) in enumerate(self.COLUMNS):
            self.setColumnWidth(i, width)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.verticalHeader().setVisible(False)
