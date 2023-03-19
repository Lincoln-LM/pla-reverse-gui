"""IV Calculator Window"""
import numpy as np
from numba_pokemon_prngs.data import NATURES_EN

# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QLabel,
    QComboBox,
    QPushButton,
    QSpinBox,
)

# pylint: enable=no-name-in-module

from ..util import get_name_en, get_personal_info, find_evo_line


class IVCalculatorWindow(QDialog):
    """IV Calculator Window"""

    def __init__(
        self, parent: QWidget, species_form: tuple[int, int], nature: int
    ) -> None:
        super().__init__(parent)
        self.species_form = species_form
        self.nature = nature
        self.setWindowTitle(
            f"IV Calculator - {NATURES_EN[nature]} {get_name_en(*species_form)}"
        )
        self.setModal(True)
        self.main_layout = QVBoxLayout(self)
        self.add_row_button = QPushButton("Add Row")
        self.add_row_button.clicked.connect(self.add_row)
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.accept)
        self.confirm_button.setDisabled(True)
        self.calculate_button = QPushButton("Calculate")
        self.calculate_button.clicked.connect(self.calculate)

        self.data_entry_widget = QWidget()
        self.data_entry_layout = QGridLayout(self.data_entry_widget)
        for i, title in enumerate(
            (
                "Species",
                "Level",
                "HP",
                "Atk",
                "Def",
                "SpA",
                "SpD",
                "Spe",
                "",
            )
        ):
            self.data_entry_layout.addWidget(QLabel(title), 0, i)

        self.data_entries = []
        self.data_entry_row = 1

        self.results_widget = QWidget()
        self.results_layout = QGridLayout(self.results_widget)
        for i, stat in enumerate(("HP", "Atk", "Def", "SpA", "SpD", "Spe")):
            self.results_layout.addWidget(QLabel(stat), i, 0)

        self.main_layout.addWidget(self.add_row_button)
        self.main_layout.addWidget(self.data_entry_widget)
        self.main_layout.addWidget(self.calculate_button)
        self.main_layout.addWidget(self.results_widget)
        self.main_layout.addWidget(self.confirm_button)
        self.add_row()
        self.iv_ranges: list[range] = [
            range(32),
            range(32),
            range(32),
            range(32),
            range(32),
            range(32),
        ]

    def remove_row(self, row: tuple) -> None:
        """Callback for when the remove row button is clicked"""
        if len(self.data_entries) > 1:
            self.data_entries.remove(row)
            species_combobox, level_spinbox, stat_spinboxes, remove_row_button = row
            species_combobox.deleteLater()
            level_spinbox.deleteLater()
            for spinbox in stat_spinboxes:
                spinbox.deleteLater()
            remove_row_button.deleteLater()

    def get_ivs(self) -> tuple[int, int, int, int, int, int]:
        """Function to get the calculated ivs after the window is closed"""
        if all(len(iv_range) == 1 for iv_range in self.iv_ranges):
            return tuple(iv_range[0] for iv_range in self.iv_ranges)
        raise Exception("IVs could not be calculated to precise values")

    def add_row(self) -> None:
        """Callback for when the add row button is clicked"""
        species_combobox = QComboBox()
        for species_form in find_evo_line(*self.species_form):
            species_combobox.addItem(get_name_en(*species_form), species_form)
        level_spinbox = QSpinBox(minimum=0, maximum=100)
        stat_spinboxes = [QSpinBox(minimum=0, maximum=10000) for _ in range(6)]
        remove_row_button = QPushButton("Remove Row")
        self.data_entry_layout.addWidget(species_combobox, self.data_entry_row, 0)
        self.data_entry_layout.addWidget(level_spinbox, self.data_entry_row, 1)
        for i, stat_spinbox in enumerate(stat_spinboxes):
            self.data_entry_layout.addWidget(stat_spinbox, self.data_entry_row, i + 2)
        self.data_entry_layout.addWidget(remove_row_button, self.data_entry_row, 8)
        data_entry = (
            species_combobox,
            level_spinbox,
            stat_spinboxes,
            remove_row_button,
        )
        self.data_entries.append(data_entry)
        remove_row_button.clicked.connect(lambda: self.remove_row(data_entry))
        self.data_entry_row += 1

    @staticmethod
    def calc_stat(
        stat_index: int,
        base_stat: np.uint16,
        iv: np.uint8,
        level: np.uint8,
        nature: np.uint8,
    ):
        """Calcuate a stat value"""
        iv_map = (-1, 0, 1, 3, 4, 2)
        stat = np.uint16(
            np.uint16((np.uint16(2) * base_stat + iv) * level) // np.uint16(100)
        )
        nature_boost = nature // np.uint8(5)
        nature_decrease = nature % np.uint8(5)
        if stat_index == 0:
            stat += np.uint16(level) + np.uint16(10)
        else:
            stat += np.uint16(5)
            if nature_boost != nature_decrease:
                if iv_map[stat_index] == nature_boost:
                    stat = np.uint16(stat * np.float32(1.1))
                elif iv_map[stat_index] == nature_decrease:
                    stat = np.uint16(stat * np.float32(0.9))
        return stat

    @staticmethod
    def calc_ivs(
        base_stats: np.array, stats: np.array, level: np.uint8, nature: np.uint8
    ) -> tuple[range, range, range, range, range, range]:
        """Calculate possible ivs"""
        min_ivs = np.ones(6, np.uint8) * 31
        max_ivs = np.zeros(6, np.uint8)
        for i in range(6):
            for iv in range(32):
                stat = IVCalculatorWindow.calc_stat(
                    i, base_stats[i], np.uint8(iv), np.uint8(level), np.uint8(nature)
                )
                if stat == stats[i]:
                    min_ivs[i] = min(iv, min_ivs[i])
                    max_ivs[i] = max(iv, max_ivs[i])
        return tuple(
            range(min_iv, max_iv + 1) for min_iv, max_iv in zip(min_ivs, max_ivs)
        )

    def calculate(self) -> None:
        """Calculate IVs"""
        self.iv_ranges = [
            range(32),
            range(32),
            range(32),
            range(32),
            range(32),
            range(32),
        ]
        for (
            species_combobox,
            level_spinbox,
            stat_spinboxes,
            _,
        ) in self.data_entries:
            species_form = species_combobox.currentData()
            personal_info = get_personal_info(*species_form)
            base_stats = np.array(
                (
                    personal_info.hp,
                    personal_info.attack,
                    personal_info.defense,
                    personal_info.special_attack,
                    personal_info.special_defense,
                    personal_info.speed,
                ),
                np.uint16,
            )
            level = np.uint8(level_spinbox.value())
            stats = np.array(
                [stat_spinbox.value() for stat_spinbox in stat_spinboxes], np.uint16
            )

            def try_intersect(x, y):
                try:
                    return range(max(x[0], y[0]), min(x[-1], y[-1]) + 1)
                except IndexError:
                    return range(32, 0)

            self.iv_ranges = [
                try_intersect(x, y)
                for x, y in zip(
                    self.iv_ranges,
                    IVCalculatorWindow.calc_ivs(
                        base_stats, stats, level, np.int8(self.nature)
                    ),
                )
            ]
        for i, iv_range in enumerate(self.iv_ranges):
            if len(iv_range) == 0:
                self.results_layout.addWidget(QLabel("Invalid"), i, 1)
            else:
                self.results_layout.addWidget(
                    QLabel(
                        f"{iv_range.start}-{iv_range.stop - 1}"
                        if len(iv_range) > 1
                        else f"{iv_range.start}"
                    ),
                    i,
                    1,
                )
        self.confirm_button.setDisabled(
            any(len(iv_range) != 1 for iv_range in self.iv_ranges)
        )
