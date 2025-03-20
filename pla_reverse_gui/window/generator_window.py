"""Spawner generator window"""

import time
import numpy as np
import numba
from numba.typed import List as TypedList
from numba_pokemon_prngs.data.encounter import (
    ENCOUNTER_TABLE_NAMES_LA,
    SPAWNER_NAMES_LA,
    EncounterAreaLA,
)
from numba_pokemon_prngs.data import NATURES_EN, ABILITIES_EN
from numba_pokemon_prngs.data.fbs.encounter_la import PlacementSpawner8a
from numba_pokemon_prngs.enums import LAWeather, LATime

# pylint: disable=no-name-in-module
from numba.typed import Dict as TypedDict
from qtpy.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTableWidgetItem,
    QSpinBox,
)
from qtpy.QtGui import QRegularExpressionValidator
from qtpy import QtCore
from qtpy.QtCore import QThread, Signal, Qt

# pylint: enable=no-name-in-module

from .result_table_widget import ResultTableWidget
from ..util import get_name_en, get_personal_info, get_personal_index, path_to_string
from .checkable_combobox_widget import CheckableComboBox
from .range_widget import RangeWidget
from ..generator import generate_standard, generate_mass_outbreak, generate_variable
from ..pla_reverse_main.pla_reverse.size import calc_display_size
from .eta_progress_bar import ETAProgressBar


def compute_result_count(max_spawn_count: int, max_path_length: int) -> int:
    """Calculate the total amount of results to be generated for a given spawner and max path length"""
    if max_spawn_count == 1:
        return max_path_length
    initial_value = 1 if max_spawn_count != 3 else 2
    return initial_value * (1 - max_spawn_count**max_path_length) // (1 - max_spawn_count)

def compute_result_count_variable(spawn_counts: list[int]):
    """Calculate the total amount of results to be generated for a given variable multi spawner"""
    # number of results at each step that have the corresponding num_spawned
    counts = {
        1: 0,
        # variable spawners always start with 2 spawns
        2: 1,
        3: 0
    }
    total_result_count = sum(counts.values())
    for spawn_count in spawn_counts[1:]:
        new_counts = {
            1: 0,
            2: 0,
            3: 0
        }
        for num_spawned in range(1, 4):
            # a num_spawned of N can be advanced N + 1 ways
            # KOing 0,1,2,...,N spawns
            for ko_count in range(num_spawned + 1):
                # KOing M spawns reduces the spawn count to num_spawned - M
                # meaning after this step the num_spawned will be max(num_spawned - M, spawn_count)
                # as num_spawned will either remain the same (if its >= spawn_count)
                # or increase to spawn_count
                # (this loop is the same as just looping over num_spawned - ko_count in reverse)
                new_counts[max(num_spawned - ko_count, spawn_count)] += counts[num_spawned]
        total_result_count += sum(new_counts.values())
        counts = new_counts

    return total_result_count

def labled_widget(
    label: str, widget_constructor: QWidget, *args, **kwargs
) -> tuple[QWidget, QWidget]:
    """Build a labled widget"""
    outer_widget = QWidget()
    layout = QHBoxLayout(outer_widget)
    label_widget = QLabel(label)
    layout.addWidget(label_widget)
    widget = widget_constructor(*args, **kwargs)
    layout.addWidget(widget)
    return widget, outer_widget


class GeneratorWindow(QDialog):
    """Spawner generator window"""

    def __init__(
        self,
        parent: QWidget,
        spawner: PlacementSpawner8a,
        encounter_table: EncounterAreaLA,
        second_wave_encounter_table: EncounterAreaLA,
    ) -> None:
        super().__init__(parent)
        self.generator_update_thread = None
        self.spawner = spawner
        self.encounter_table = encounter_table
        self.second_wave_encounter_table = second_wave_encounter_table
        self.has_second_wave = self.second_wave_encounter_table is not None
        self.is_mmo = spawner.encounter_table_id != self.encounter_table.table_id
        is_variable = spawner.min_spawn_count != spawner.max_spawn_count
        self.basculin_gender = {
            0xFD9CA9CA1D5681CB: 0,  # M
            0xFD999DCA1D543790: 1,  # F
        }.get(spawner.encounter_table_id, None)
        self.setWindowTitle(
            "Generator "
            f"{SPAWNER_NAMES_LA.get(np.uint64(spawner.spawner_id), '')} - "
            f"{ENCOUNTER_TABLE_NAMES_LA.get(np.uint64(self.encounter_table.table_id), '')}"
        )
        self.main_layout = QVBoxLayout(self)
        self.top_widget = QWidget()
        self.top_layout = QHBoxLayout(self.top_widget)
        self.settings_widget = QWidget()
        self.settings_layout = QVBoxLayout(self.settings_widget)
        self.settings_layout.addWidget(QLabel("Seed:"))
        self.seed_input = QLineEdit()
        self.seed_input.setValidator(
            QRegularExpressionValidator(QtCore.QRegularExpression("[0-9a-fA-F]{0,16}"))
        )
        self.settings_layout.addWidget(self.seed_input)
        settings_label = QLabel("Settings:")
        self.settings_layout.addWidget(settings_label)
        self.weather_combobox, weather_widget = labled_widget("Weather:", QComboBox)
        self.weather_combobox: QComboBox
        for weather in LAWeather:
            if weather != LAWeather.NONE:
                self.weather_combobox.addItem(weather.name.title(), weather)
        self.time_combobox, time_widget = labled_widget("Time:", QComboBox)
        self.time_combobox: QComboBox
        for time in LATime:
            self.time_combobox.addItem(time.name.title(), time)
        settings_label.setVisible(not self.spawner.is_mass_outbreak)
        weather_widget.setVisible(not self.spawner.is_mass_outbreak)
        time_widget.setVisible(not self.spawner.is_mass_outbreak)
        self.settings_layout.addWidget(weather_widget)
        self.settings_layout.addWidget(time_widget)
        spawn_count_label = QLabel("Spawn Count:")
        spawn_count_label.setVisible(bool(self.spawner.is_mass_outbreak))
        self.settings_layout.addWidget(spawn_count_label)
        self.first_wave_spawn_count, first_wave_spawn_count_widget = labled_widget("First Wave:", QSpinBox, minimum=8, maximum=10)
        first_wave_spawn_count_widget.setVisible(bool(self.spawner.is_mass_outbreak))
        self.second_wave_spawn_count, second_wave_spawn_count_widget = labled_widget("Second Wave:", QSpinBox, minimum=6, maximum=8)
        second_wave_spawn_count_widget.setVisible(self.has_second_wave)
        self.settings_layout.addWidget(first_wave_spawn_count_widget)
        self.settings_layout.addWidget(second_wave_spawn_count_widget)
        advance_range_label = QLabel("Advance Range:")
        self.settings_layout.addWidget(advance_range_label)
        self.advance_range = RangeWidget(
            0, 20 if self.spawner.min_spawn_count > 1 else 9999
        )
        self.advance_range.max_entry.setMaximum(99999999)
        advance_range_label.setVisible(not (self.spawner.is_mass_outbreak or is_variable))
        self.advance_range.setVisible(not (self.spawner.is_mass_outbreak or is_variable))
        self.settings_layout.addWidget(self.advance_range)
        self.settings_layout.addWidget(QLabel("Shiny Rolls:"))
        self.shiny_roll_entries = []

        self.added_species = []
        self.unique_slots = set()
        self.shiny_rolls_comboboxes = {}
        # TODO: does second wave ever include new species?
        for slot in self.encounter_table.slots.view(np.recarray):
            self.unique_slots.add((slot.species, slot.form))
            if slot.is_alpha:
                continue
            if slot.species in self.added_species:
                continue
            self.added_species.append(slot.species)
            species_name = get_name_en(slot.species)

            shiny_rolls_combobox, shiny_rolls_outer = labled_widget(
                species_name, QComboBox
            )
            for item in (
                ("Base Research", 1),
                ("Research Level 10", 2),
                ("Perfect Research", 4),
                ("Shiny Charm + Research Level 10", 5),
                ("Shiny Charm + Perfect Research", 7),
            ):
                shiny_rolls_combobox.addItem(*item)
            self.settings_layout.addWidget(shiny_rolls_outer)
            self.shiny_rolls_comboboxes[
                slot.species
            ] = shiny_rolls_combobox
        starting_path_label = QLabel("Spawn Count Values" if is_variable else "Starting Path:")
        starting_path_label.setVisible(self.spawner.max_spawn_count > 1 and not self.spawner.is_mass_outbreak)
        self.settings_layout.addWidget(starting_path_label)
        self.starting_path_input = QLineEdit()
        # TODO: regex validation
        # self.starting_path_input.setValidator(
        #     QRegularExpressionValidator(QtCore.QRegularExpression(""))
        # )
        self.starting_path_input.setVisible(self.spawner.max_spawn_count > 1 and not self.spawner.is_mass_outbreak)
        self.settings_layout.addWidget(self.starting_path_input)

        self.filter_widget = QWidget()
        self.filter_layout = QVBoxLayout(self.filter_widget)

        self.species_filter, species_widget = labled_widget(
            "Species Filter:", CheckableComboBox
        )
        self.species_filter: CheckableComboBox
        for species_form in self.unique_slots:
            self.species_filter.add_checked_item(
                get_name_en(*species_form), species_form
            )
        self.gender_filter, gender_widget = labled_widget(
            "Gender Filter:", CheckableComboBox
        )
        self.gender_filter: CheckableComboBox
        self.gender_filter.add_checked_item("Male", 0)
        self.gender_filter.add_checked_item("Female", 1)
        self.nature_filter, nature_widget = labled_widget(
            "Nature Filter:", CheckableComboBox
        )
        self.nature_filter: CheckableComboBox
        for i, nature in enumerate(NATURES_EN):
            self.nature_filter.add_checked_item(nature, i)
        self.shiny_filter, shiny_widget = labled_widget("Shiny Filter:", QComboBox)
        self.shiny_filter: QComboBox
        self.shiny_filter.addItem("Any", None)
        self.shiny_filter.addItem("Star", 1)
        self.shiny_filter.addItem("Square", 2)
        self.shiny_filter.addItem("Star/Square", 1 | 2)
        self.alpha_filter = QCheckBox("Alpha Only")
        self.shortest_path_filter = QCheckBox("Only Shortest Path")
        self.shortest_path_filter.setChecked(True)

        self.size_filter, size_widget = labled_widget(
            "Height/Scale Filter:", CheckableComboBox
        )
        self.size_filter: CheckableComboBox
        self.size_filter.add_checked_item("XXXS (0)", 0)
        self.size_filter.add_checked_item("XXXL (255)", 255)

        self.filter_layout.addWidget(species_widget)
        self.filter_layout.addWidget(gender_widget)
        self.filter_layout.addWidget(nature_widget)
        self.filter_layout.addWidget(shiny_widget)
        self.filter_layout.addWidget(size_widget)
        self.filter_layout.addWidget(self.alpha_filter)
        self.filter_layout.addWidget(self.shortest_path_filter)

        self.iv_filter_widget = QWidget()
        self.iv_filter_layout = QVBoxLayout(self.iv_filter_widget)
        self.iv_filters = (
            RangeWidget(0, 31, "HP:"),
            RangeWidget(0, 31, "Atk:"),
            RangeWidget(0, 31, "Def:"),
            RangeWidget(0, 31, "SpA:"),
            RangeWidget(0, 31, "SpD:"),
            RangeWidget(0, 31, "Spe:"),
        )
        for iv_filter in self.iv_filters:
            self.iv_filter_layout.addWidget(iv_filter)

        self.top_layout.addWidget(self.settings_widget)
        self.top_layout.addWidget(self.iv_filter_widget)
        self.top_layout.addWidget(self.filter_widget)

        self.progress_bar = ETAProgressBar()

        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate)

        self.result_table = ResultTableWidget()
        self.main_layout.addWidget(self.top_widget)
        self.main_layout.addWidget(self.generate_button)
        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self.result_table)
        self.resize(
            sum(column[1] for column in self.result_table.COLUMNS),
            self.height(),
        )

    def generate(self) -> None:
        """Generate paths for spawner"""
        self.result_table.setRowCount(0)
        seed = int(seed_str, 16) if (seed_str := self.seed_input.text()) else 0
        seed = np.uint64(seed)
        extra_shiny_rolls = 0
        if self.spawner.is_mass_outbreak:
            extra_shiny_rolls = 25
            if self.is_mmo:
                extra_shiny_rolls = 12
        starting_path = tuple(int(x) for x in self.starting_path_input.text().split("->") if x)
        if len(starting_path) == 0:
            starting_path = (-1,)
        advance_range = self.advance_range.get_range()
        species_info = TypedDict.empty(
            key_type=numba.typeof((0, 0)), value_type=numba.typeof((0, 0, False))
        )

        filtered_species = self.species_filter.get_checked_values()
        filtered_genders = self.gender_filter.get_checked_values()
        filtered_natures = self.nature_filter.get_checked_values()
        filtered_sizes = self.size_filter.get_checked_values()
        shiny_filter = self.shiny_filter.currentData() or 15
        alpha_filter = self.alpha_filter.checkState() == QtCore.Qt.Checked
        shortest_path_filter = self.shortest_path_filter.checkState() == QtCore.Qt.Checked
        iv_filters = tuple(
            (iv_range.start, iv_range.stop - 1)
            for iv_range in (iv_filter.get_range() for iv_filter in self.iv_filters)
        )

        for species, form in self.unique_slots:
            personal_info = get_personal_info(species, form)
            species_info[(species, form)] = (
                self.basculin_gender
                if (species, form) == (550, 2) and self.basculin_gender is not None
                else personal_info.gender_ratio,
                self.shiny_rolls_comboboxes[species].currentData() + extra_shiny_rolls,
                len(filtered_species) == 0 or (species, form) in filtered_species,
            )

        # TODO: calculate variable result count
        if self.spawner.is_mass_outbreak or self.spawner.min_spawn_count != self.spawner.max_spawn_count:
            self.progress_bar.setMaximum(compute_result_count_variable(starting_path))
        else:
            self.progress_bar.setMaximum(compute_result_count(self.spawner.max_spawn_count, advance_range.stop))

        if self.spawner.is_mass_outbreak:
            self.generator_update_thread = GeneratorUpdateThread(
                self,
                True,
                False,
                shortest_path_filter,
                seed,
                self.first_wave_spawn_count.value(),
                self.second_wave_spawn_count.value() if self.has_second_wave else 0,
                self.encounter_table,
                self.second_wave_encounter_table or self.second_wave_encounter_table,
                species_info,
                filtered_genders,
                filtered_natures,
                filtered_sizes,
                shiny_filter,
                alpha_filter,
                iv_filters,
            )
        elif self.spawner.min_spawn_count != self.spawner.max_spawn_count:
            self.generator_update_thread = GeneratorUpdateThread(
                self,
                False,
                True,
                shortest_path_filter,
                seed,
                starting_path,
                self.spawner.max_spawn_count,
                self.encounter_table,
                self.weather_combobox.currentData(),
                self.time_combobox.currentData(),
                species_info,
                filtered_genders,
                filtered_natures,
                filtered_sizes,
                shiny_filter,
                alpha_filter,
                iv_filters,
            )
        else:
            self.generator_update_thread = GeneratorUpdateThread(
                self,
                False,
                False,
                shortest_path_filter,
                seed,
                starting_path,
                advance_range.start,
                advance_range.stop,
                self.spawner.max_spawn_count,
                self.encounter_table,
                self.weather_combobox.currentData(),
                self.time_combobox.currentData(),
                species_info,
                filtered_genders,
                filtered_natures,
                filtered_sizes,
                shiny_filter,
                alpha_filter,
                iv_filters,
            )
        self.generator_update_thread.progress.connect(self.progress_bar.setValue)

        def cleanup_generate():
            # self.generator_update_thread.generator_thread.terminate()
            if self.generator_update_thread is not None:
                self.generator_update_thread.requestInterruption()
            self.generate_button.setText("Generate")
            self.generate_button.clicked.disconnect(cleanup_generate)
            self.generate_button.clicked.connect(self.generate)
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setMaximum(1)
                self.progress_bar.setValue(1)

        self.generate_button.setText("Cancel")
        self.generate_button.clicked.disconnect(self.generate)
        self.generate_button.clicked.connect(cleanup_generate)

        self.generator_update_thread.finished.connect(cleanup_generate)
        self.generator_update_thread.start()

        # TODO: storing encounter info in the table feels hacky
        self.result_table.min_spawn_count = self.spawner.min_spawn_count
        self.result_table.max_spawn_count = self.spawner.max_spawn_count
        self.result_table.encounter_table = self.encounter_table
        self.result_table.second_wave_encounter_table = self.second_wave_encounter_table
        self.result_table.seed = seed
        self.result_table.weather = self.weather_combobox.currentData()
        self.result_table.time = self.time_combobox.currentData()
        self.result_table.species_info = species_info
        self.result_table.spawn_counts = starting_path

    def add_result(self, row: tuple):
        (
            advance,
            path,
            (species, form, is_alpha),
            _encryption_constant,
            _pid,
            ivs,
            ability,
            gender,
            nature,
            shiny,
            height,
            weight,
        ) = row
        personal_info = get_personal_info(species, form)
        personal_index = get_personal_index(species, form)
        display_size_metric = calc_display_size(
            personal_index, height, weight, imperial=False
        )
        display_size_imperial = calc_display_size(
            personal_index, height, weight, imperial=True
        )
        row_i = self.result_table.rowCount()
        self.result_table.insertRow(row_i)
        row = (
            advance,
            path_to_string(path)
            if self.spawner.max_spawn_count != 1
            else "N/A",
            get_name_en(species, form, is_alpha),
            "Square" if shiny == 2 else "Star" if shiny else "No",
            "Yes" if is_alpha else "No",
            NATURES_EN[nature],
            ABILITIES_EN[
                personal_info.ability_2 if ability else personal_info.ability_1
            ],
            *(str(iv) for iv in ivs),
            "♂" if gender == 0 else "♀" if gender == 1 else "○",
            f"{display_size_metric[0]:.02f} m | {display_size_imperial[0][0]:.00f}'{display_size_imperial[0][1]:.00f}\" ({height})",
            f"{display_size_metric[1]:.02f} kg | {display_size_imperial[1]:.01f} lbs ({weight})",
        )
        for j, value in enumerate(row):
            item = QTableWidgetItem()
            item.setData(Qt.EditRole, value)
            self.result_table.setItem(row_i, j, item)
        # sort by paths first
        self.result_table.model().sort(1, Qt.AscendingOrder)
        # then by advances
        self.result_table.model().sort(0, Qt.AscendingOrder)

    def closeEvent(self, event):
        if self.generator_update_thread is not None:
            self.generator_update_thread.requestInterruption()
            self.generator_update_thread.wait()
        event.accept()


class GeneratorUpdateThread(QThread):
    """Thread for checking progress of GeneratorThread"""

    finished = Signal()
    progress = Signal(int)
    new_result = Signal(tuple)

    def __init__(self, parent_window: GeneratorWindow, is_mass_outbreak: bool, is_variable: bool, shortest_path_only: bool, *args) -> None:
        super().__init__()
        self.parent_window = parent_window
        self.parent_data_hook = np.zeros(2, np.uint64)
        self.generator_thread = GeneratorThread(is_mass_outbreak, is_variable, *args, self.parent_data_hook)
        self.shortest_path_only = shortest_path_only
        self.args = args

    def run(self) -> None:
        """Thread work"""
        self.generator_thread.start()

        if isinstance(self.args[3], EncounterAreaLA):
            total_progress = compute_result_count_variable(self.args[1])
        else:
            total_progress = compute_result_count(self.args[4], self.args[3])

        result_count = 0
        result_ids = set()
        while True:
            # checking here ensures final copied data is from after the thread finishes
            thread_finished = (
                self.isInterruptionRequested()
                or not self.generator_thread.isRunning()
            )
            progress = self.parent_data_hook[0]
            self.parent_data_hook[1] = self.isInterruptionRequested()
            self.progress.emit(progress)
            # copy here to dodge thread issues
            results = list(self.generator_thread.results)
            if len(results) > result_count:
                for row in results[result_count:]:
                    if self.shortest_path_only:
                        result_id = row[3] | (row[4] << 32)
                        if result_id not in result_ids:
                            self.parent_window.add_result(row)
                            result_ids.add(result_id)
                    else:
                        self.parent_window.add_result(row)
                result_count = len(results)
            if (
                progress == total_progress
                or thread_finished
            ):
                break
            time.sleep(1)
        self.generator_thread.wait()


class GeneratorThread(QThread):
    """Thread for handling pokemon generation"""

    finished = Signal()

    def __init__(self, is_outbreak: bool, is_variable: bool, *args) -> None:
        super().__init__()
        self.is_outbreak = is_outbreak
        self.is_variable = is_variable
        self.args = args
        self.results = TypedList.empty_list(
            item_type=numba.typeof(
                (
                    0,
                    [np.uint8(0)],
                    (np.uint16(0), np.uint8(0), np.bool8(0)),
                    np.uint32(0),
                    np.uint32(0),
                    np.zeros(6, np.uint8),
                    np.uint8(0),
                    np.uint8(0),
                    np.uint8(0),
                    np.uint8(0),
                    np.uint8(0),
                    np.uint8(0),
                )
            )
        )

    def run(self) -> None:
        """Thread work"""
        if self.is_outbreak:
            generate_mass_outbreak(*self.args, self.results)
        elif self.is_variable:
            generate_variable(*self.args, self.results)
        else:
            generate_standard(*self.args, self.results)
        self.finished.emit()
