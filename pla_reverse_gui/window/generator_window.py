"""Spawner generator window"""

import numpy as np
import numba
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
)
from qtpy.QtGui import QRegularExpressionValidator
from qtpy import QtCore

# pylint: enable=no-name-in-module

from .result_table_widget import ResultTableWidget
from ..util import get_name_en, get_personal_info
from .checkable_combobox_widget import CheckableComboBox
from .range_widget import RangeWidget
from ..generator import generate


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
    ) -> None:
        super().__init__(parent)
        self.spawner = spawner
        self.encounter_table = encounter_table
        self.setWindowTitle(
            "Generator "
            f"{SPAWNER_NAMES_LA.get(np.uint64(spawner.spawner_id), '')} - "
            f"{ENCOUNTER_TABLE_NAMES_LA.get(np.uint64(spawner.encounter_table_id), '')}"
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
        self.settings_layout.addWidget(QLabel("Settings:"))
        self.weather_combobox, weather_widget = labled_widget("Weather:", QComboBox)
        self.weather_combobox: QComboBox
        for weather in LAWeather:
            self.weather_combobox.addItem(weather.name.title(), weather)
        self.time_combobox, time_widget = labled_widget("Time:", QComboBox)
        self.time_combobox: QComboBox
        for time in LATime:
            self.time_combobox.addItem(time.name.title(), time)
        self.settings_layout.addWidget(weather_widget)
        self.settings_layout.addWidget(time_widget)
        self.settings_layout.addWidget(QLabel("Advance Range:"))
        self.advance_range = RangeWidget(
            0, 20 if self.spawner.min_spawn_count > 1 else 9999
        )
        self.advance_range.max_entry.setMaximum(99999999)
        self.settings_layout.addWidget(self.advance_range)
        self.settings_layout.addWidget(QLabel("Shiny Rolls:"))
        self.shiny_roll_entries = []

        self.added_species = []
        self.shiny_rolls_comboboxes = {}
        for slot in self.encounter_table.slots.view(np.recarray):
            if slot.is_alpha:
                continue
            if (slot.species, slot.form) in self.added_species:
                continue
            self.added_species.append((slot.species, slot.form))
            species_name = get_name_en(slot.species, slot.form)

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
                (slot.species, slot.form)
            ] = shiny_rolls_combobox

        self.filter_widget = QWidget()
        self.filter_layout = QVBoxLayout(self.filter_widget)

        self.species_filter, species_widget = labled_widget(
            "Species Filter:", CheckableComboBox
        )
        self.species_filter: CheckableComboBox
        for species_form in self.added_species:
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

        self.filter_layout.addWidget(species_widget)
        self.filter_layout.addWidget(gender_widget)
        self.filter_layout.addWidget(nature_widget)
        self.filter_layout.addWidget(shiny_widget)
        self.filter_layout.addWidget(self.alpha_filter)

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

        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate)

        self.result_table = ResultTableWidget()
        self.main_layout.addWidget(self.top_widget)
        self.main_layout.addWidget(self.generate_button)
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
        advance_range = self.advance_range.get_range()
        species_info = TypedDict.empty(
            key_type=numba.typeof((0, 0)), value_type=numba.typeof((0, 0, False))
        )

        filtered_species = self.species_filter.get_checked_values()
        filtered_genders = self.gender_filter.get_checked_values()
        filtered_natures = self.nature_filter.get_checked_values()
        shiny_filter = self.shiny_filter.currentData() or 15
        alpha_filter = self.alpha_filter.checkState() == QtCore.Qt.Checked
        iv_filters = tuple(
            (iv_range.start, iv_range.stop - 1)
            for iv_range in (iv_filter.get_range() for iv_filter in self.iv_filters)
        )

        for species, form in self.added_species:
            personal_info = get_personal_info(species, form)
            species_info[(species, form)] = (
                personal_info.gender_ratio,
                self.shiny_rolls_comboboxes[(species, form)].currentData(),
                len(filtered_species) == 0 or (species, form) in filtered_species,
            )

        rows = generate(
            seed,
            advance_range.start,
            advance_range.stop,
            self.spawner.max_spawn_count,
            self.encounter_table,
            self.weather_combobox.currentData(),
            self.time_combobox.currentData(),
            species_info,
            filtered_genders,
            filtered_natures,
            shiny_filter,
            alpha_filter,
            iv_filters,
        )
        rows.sort()
        for (
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
        ) in rows:
            personal_info = get_personal_info(species, form)
            row_i = self.result_table.rowCount()
            self.result_table.insertRow(row_i)
            row = (
                str(advance),
                "->".join(str(ko) for ko in path)
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
                str(height),
                str(weight),
            )
            for j, value in enumerate(row):
                item = QTableWidgetItem(value)
                self.result_table.setItem(row_i, j, item)
