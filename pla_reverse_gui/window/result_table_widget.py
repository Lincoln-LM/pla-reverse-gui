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
from ..util import string_to_path


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
        self.min_spawn_count = 0
        self.max_spawn_count = 0
        self.encounter_table = None
        self.seed = 0
        self.weather = None
        self.time = None
        self.spawn_counts = None

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
        if self.max_spawn_count == 4:
            pre_path = (1, 1)
        elif self.min_spawn_count != self.max_spawn_count:
            pre_path = (2,)
        else:
            pre_path = (self.max_spawn_count,)
        path = string_to_path(path_text)
        path_tracker = PathTrackerWindow(
            self,
            self.encounter_table,
            self.second_wave_encounter_table,
            self.seed,
            pre_path,
            path,
            self.spawn_counts,
            self.max_spawn_count,
            self.weather,
            self.time,
            self.species_info,
        )
        path_tracker.show()
