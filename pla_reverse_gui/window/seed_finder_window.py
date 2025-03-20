"""Seed finder window"""
import numpy as np
from numba_pokemon_prngs.data.encounter import (
    ENCOUNTER_TABLE_NAMES_LA,
    SPAWNER_NAMES_LA,
    EncounterAreaLA,
)
from numba_pokemon_prngs.data.fbs.encounter_la import PlacementSpawner8a

# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QTextEdit,
)

# pylint: enable=no-name-in-module
from qtpy.QtCore import Qt

from .pokemon_info_widget import PokemonInfoWidget
from .eta_progress_bar import ETAProgressBar
from .log_spin_box_widget import LogSpinBox
from ..kernel_interface import (
    ComputeFixedSeedsThread,
    ComputeGeneratorSeedsThread,
    ComputeGroupSeedThread,
)


class ConsoleWindow(QDialog):
    """Console log window"""

    def __init__(self):
        super().__init__()

        self.main_layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.progress_bar = ETAProgressBar()
        self.main_layout.addWidget(self.text_edit)
        self.main_layout.addWidget(self.progress_bar)

        self.setWindowTitle("Console Window")
        self.setGeometry(100, 100, 640, 480)

    def log(self, line):
        """Log a line of text"""
        self.text_edit.append(line)
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )


class SeedFinderWindow(QDialog):
    """Seed finder window"""

    def __init__(
        self,
        parent: QWidget,
        spawner: PlacementSpawner8a,
        encounter_table: EncounterAreaLA,
    ) -> None:
        super().__init__(parent)

        self.console_window = None
        self.worker_thread = None
        self.results_1 = None
        self.results_2 = None
        self.results_gen = None
        self.tried_first_order = False

        self.setWindowTitle(
            "Seed Finder "
            f"{SPAWNER_NAMES_LA.get(np.uint64(spawner.spawner_id), '')} - "
            f"{ENCOUNTER_TABLE_NAMES_LA.get(np.uint64(spawner.encounter_table_id), '')}"
        )
        self.fixed_seed_steps = LogSpinBox(2, 0, 10, "Fixed Seed Steps")
        self.generator_seed_steps = LogSpinBox(2, 0, 8, "Generator Seed Steps")
        self.generator_seed_steps.spin_box.setValue(128)
        # TODO: this is a little hacky
        # these two encounter tables are the only two in the game with forced gender encounters
        # the only forced gendered mons in the tables are basculin, and they are always forced
        # this means if the flag is set, and the species selected is a basculin,
        # the gender ratio is effectively 100% M/F
        self.basculin_gender = {
            0xFD9CA9CA1D5681CB: 0,  # M
            0xFD999DCA1D543790: 1,  # F
        }.get(spawner.encounter_table_id, None)
        self.spawner: PlacementSpawner8a = spawner
        self.is_multi_spawner: bool = self.spawner.min_spawn_count > 1 and not self.spawner.is_mass_outbreak
        self.is_variable: bool = self.spawner.min_spawn_count != self.spawner.max_spawn_count
        self.encounter_table: EncounterAreaLA = encounter_table
        self.main_layout = QVBoxLayout(self)
        self.sub_widget = QWidget()
        self.sub_layout = QHBoxLayout(self.sub_widget)
        self.pokemon_1 = PokemonInfoWidget(
            ("Multi-Spawner " if self.is_multi_spawner else "") + "Pokemon 1:",
            spawner,
            encounter_table,
        )
        self.pokemon_2 = PokemonInfoWidget(
            ("Multi-Spawner " if self.is_multi_spawner else "") + "Pokemon 2:",
            spawner,
            encounter_table,
        )
        self.compute_seed_button = QPushButton("Compute Group Seed")
        self.compute_seed_button.clicked.connect(self.compute_seed)

        self.sub_layout.addWidget(self.pokemon_1)
        self.sub_layout.addWidget(self.pokemon_2)
        self.main_layout.addWidget(self.fixed_seed_steps)
        self.main_layout.addWidget(self.generator_seed_steps)
        self.main_layout.addWidget(self.sub_widget)
        self.main_layout.addWidget(self.compute_seed_button)

    def compute_seed(self) -> None:
        """Callback for when the compute group seed button is clicked"""
        self.console_window = ConsoleWindow()
        self.console_window.show()
        self.results_1 = None
        self.results_2 = None
        self.results_gen = None
        self.tried_first_order = False

        def compute_fixed_seeds_1():
            self.worker_thread = ComputeFixedSeedsThread(
                self.fixed_seed_steps.spin_box.value(),
                self.pokemon_1.species_combobox.currentData(),
                self.basculin_gender,
                self.pokemon_1.shiny_rolls_combobox.currentData(),
                tuple(iv_widget.value() for iv_widget in self.pokemon_1.iv_widgets),
                self.pokemon_1.ability_combobox.currentData(),
                self.pokemon_1.nature_combobox.currentData(),
                self.pokemon_1.gender_combobox.currentData(),
                *self.pokemon_1.measurements.get_value(),
            )
            self.worker_thread.log.connect(self.console_window.log)
            self.worker_thread.finished.connect(compute_fixed_seeds_2)

            def save_results(results):
                self.results_1 = results

            self.worker_thread.results.connect(save_results)

            self.worker_thread.init_progress_bar.connect(
                self.console_window.progress_bar.setMaximum
            )
            self.worker_thread.progress.connect(
                self.console_window.progress_bar.setValue
            )
            self.console_window.log("Starting fixed seed search for Pokemon 1.")
            self.worker_thread.start()

        def compute_fixed_seeds_2():
            self.console_window.log("Fixed seed search ended.")
            if self.results_1 is None:
                self.console_window.log("Fixed seed search unsuccessful.")
                return
            self.worker_thread = ComputeFixedSeedsThread(
                self.fixed_seed_steps.spin_box.value(),
                self.pokemon_2.species_combobox.currentData(),
                self.basculin_gender,
                self.pokemon_2.shiny_rolls_combobox.currentData(),
                tuple(iv_widget.value() for iv_widget in self.pokemon_2.iv_widgets),
                self.pokemon_2.ability_combobox.currentData(),
                self.pokemon_2.nature_combobox.currentData(),
                self.pokemon_2.gender_combobox.currentData(),
                *self.pokemon_2.measurements.get_value(),
            )
            self.worker_thread.log.connect(self.console_window.log)
            self.worker_thread.finished.connect(compute_generator_seed)

            def save_results(results):
                self.results_2 = results

            self.worker_thread.results.connect(save_results)

            self.worker_thread.init_progress_bar.connect(
                self.console_window.progress_bar.setMaximum
            )
            self.worker_thread.progress.connect(
                self.console_window.progress_bar.setValue
            )
            self.console_window.log("Starting fixed seed search for Pokemon 2.")
            self.worker_thread.start()

        def compute_generator_seed():
            if not self.tried_first_order:
                self.console_window.log("Fixed seed search ended.")
            if self.results_2 is None:
                self.console_window.log("Fixed seed search unsuccessful.")
                return
            self.tried_first_order = True
            self.worker_thread = ComputeGeneratorSeedsThread(
                self.generator_seed_steps.spin_box.value(),
                self.results_1,
            )
            self.worker_thread.log.connect(self.console_window.log)
            self.worker_thread.finished.connect(compute_group_seed)

            def save_results(results):
                self.results_gen = results

            self.worker_thread.results.connect(save_results)

            self.worker_thread.init_progress_bar.connect(
                self.console_window.progress_bar.setMaximum
            )
            self.worker_thread.progress.connect(
                self.console_window.progress_bar.setValue
            )
            self.console_window.log("Starting generator seed search.")
            self.worker_thread.start()

        def compute_group_seed():
            self.console_window.log("Generator seed search ended.")
            if self.results_gen is None:
                self.console_window.log("Generator seed search unsuccessful")
                return
            self.worker_thread = ComputeGroupSeedThread(
                self.results_2, self.results_gen, self.is_multi_spawner
            )
            self.worker_thread.log.connect(self.console_window.log)
            self.worker_thread.valid_result.connect(on_group_seed_result)
            self.console_window.log("Starting group seed search.")
            self.worker_thread.start()

        def on_group_seed_result(valid: bool):
            if not valid:
                self.console_window.log("Group seed search unsuccessful.")
                if self.is_variable and self.tried_first_order:
                    self.console_window.log("Testing other order.")
                    temp = self.results_1
                    self.results_1 = self.results_2
                    self.results_2 = temp
                    compute_generator_seed()
            self.console_window.log("Group seed search ended.")

        compute_fixed_seeds_1()
