"""QTableWidget for spawner paths"""

# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QTableWidget,
    QSizePolicy,
    QMenu,
    QAction,
)
from qtpy.QtCore import Qt

# pylint: enable=no-name-in-module
from .path_tracker_window import PathTrackerWindow


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
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu_handler)

        self.action_open_path = QAction("Open Path Tracker", self)
        self.action_open_path.triggered.connect(self.open_path_tracker)
        self.encounter_table = None
        self.seed = 0
        self.weather = None
        self.time = None

    def context_menu_handler(self, pos):
        """Handler for QTableView context manager"""
        menu = QMenu(self)
        menu.addAction(self.action_open_path)
        menu.exec_(self.mapToGlobal(pos))

    def open_path_tracker(self):
        """Handler for opening the path tracker"""
        selected_row = self.item(self.selectedIndexes()[0].row(), 1)
        path_text = selected_row.text()
        if path_text == "N/A":
            return
        path = tuple(int(x) for x in path_text.split("->"))
        path_tracker = PathTrackerWindow(
            self,
            self.encounter_table,
            self.seed,
            path,
            self.weather,
            self.time,
            self.species_info,
        )
        path_tracker.show()
