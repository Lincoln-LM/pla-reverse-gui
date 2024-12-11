"""Pokemon fixed info widget"""

import numpy as np
from numba_pokemon_prngs.data import ABILITIES_EN, NATURES_EN
from numba_pokemon_prngs.data.encounter import EncounterAreaLA
from numba_pokemon_prngs.data.fbs.encounter_la import PlacementSpawner8a

# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QDialog,
)

# pylint: enable=no-name-in-module

from ..util import get_name_en, get_personal_info
from .measurement_widget import MeasurementWidget
from .iv_calculator_window import IVCalculatorWindow


class PokemonInfoWidget(QWidget):
    """Pokemon fixed info widget"""

    def __init__(
        self,
        title: str,
        spawner: PlacementSpawner8a,
        encounter_table: EncounterAreaLA,
    ) -> None:
        super().__init__()
        self.spawner: PlacementSpawner8a = spawner
        self.encounter_table: EncounterAreaLA = encounter_table
        self.main_layout = QVBoxLayout(self)
        self.pokemon_title = QLabel(title)
        self.species_combobox = QComboBox()
        extra_shiny_rolls = 0
        if self.spawner.is_mass_outbreak:
            extra_shiny_rolls = 25
            if self.spawner.encounter_table_id != self.encounter_table.table_id:
                extra_shiny_rolls = 12
        added_species = []
        for slot in self.encounter_table.slots.view(np.recarray):
            if slot.is_alpha:
                continue
            if (slot.species, slot.form) in added_species:
                continue
            added_species.append((slot.species, slot.form))
            self.species_combobox.addItem(
                f"{get_name_en(slot.species, slot.form)}",
                (slot.species, slot.form),
            )
        self.species_combobox.currentIndexChanged.connect(self.species_changed)
        self.shiny_rolls_combobox = QComboBox()
        for item in (
            ("Base Research", 1 + extra_shiny_rolls),
            ("Research Level 10", 2 + extra_shiny_rolls),
            ("Perfect Research", 4 + extra_shiny_rolls),
            ("Shiny Charm + Research Level 10", 5 + extra_shiny_rolls),
            ("Shiny Charm + Perfect Research", 7 + extra_shiny_rolls),
        ):
            self.shiny_rolls_combobox.addItem(*item)
        self.nature_combobox = QComboBox()
        for i, nature in enumerate(NATURES_EN):
            self.nature_combobox.addItem(nature, i)
        self.iv = QWidget()
        self.iv_layout = QHBoxLayout(self.iv)
        self.iv_widgets = [QSpinBox(minimum=0, maximum=31) for _ in range(6)]
        for iv_widget in self.iv_widgets:
            self.iv_layout.addWidget(iv_widget)
        self.iv_calc_button = QPushButton("Calculate IVs")
        self.iv_calc_button.clicked.connect(self.iv_calc_button_clicked)
        self.gender_combobox = QComboBox()
        self.ability_combobox = QComboBox()
        self.measurements = MeasurementWidget()
        self.main_layout.addWidget(self.pokemon_title)
        self.main_layout.addWidget(self.species_combobox)
        self.main_layout.addWidget(self.shiny_rolls_combobox)
        self.main_layout.addWidget(self.nature_combobox)
        self.main_layout.addWidget(self.iv)
        self.main_layout.addWidget(self.iv_calc_button)
        self.main_layout.addWidget(self.gender_combobox)
        self.main_layout.addWidget(self.ability_combobox)
        self.main_layout.addWidget(self.measurements)
        self.species_changed(0)

    def species_changed(self, index: int) -> None:
        """Callback for when the species combobox changes"""
        if index == -1:
            return
        species_form = self.species_combobox.currentData()
        if species_form is None:
            return
        self.measurements.update_base_species_form(species_form)
        personal_info = get_personal_info(*species_form)
        self.gender_combobox.clear()
        self.ability_combobox.clear()
        if personal_info.gender_ratio == 255:
            self.gender_combobox.addItem("Genderless", 2)
        else:
            if personal_info.gender_ratio < 254:
                self.gender_combobox.addItem("Male", 0)
            if personal_info.gender_ratio > 0:
                self.gender_combobox.addItem("Female", 1)
        self.ability_combobox.addItem(ABILITIES_EN[personal_info.ability_1], 0)
        if personal_info.ability_1 != personal_info.ability_2:
            self.ability_combobox.addItem(ABILITIES_EN[personal_info.ability_2], 1)

    def iv_calc_button_clicked(self) -> None:
        """Callback for when the IV calc button is clicked"""
        iv_calc_window = IVCalculatorWindow(
            self,
            self.species_combobox.currentData(),
            self.nature_combobox.currentData(),
        )
        if iv_calc_window.exec_() == QDialog.Accepted:
            ivs = iv_calc_window.get_ivs()
            for iv, iv_widget in zip(ivs, self.iv_widgets):
                iv_widget.setValue(iv)
