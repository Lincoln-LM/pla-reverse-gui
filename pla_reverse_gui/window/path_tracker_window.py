"""Path tracker window"""
import numpy as np
from numba_pokemon_prngs.data.encounter import EncounterAreaLA
from numba_pokemon_prngs.data import NATURES_EN
from numba_pokemon_prngs.enums import LATime, LAWeather
from numba_pokemon_prngs.xorshift import Xoroshiro128PlusRejection

# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QSizePolicy,
    QTableWidgetItem,
)

# pylint: enable=no-name-in-module

from ..util import calc_effort_level, get_personal_index, get_name_en
from ..pla_reverse_main.pla_reverse.size import calc_display_size


class PathTableWidget(QTableWidget):
    """QTableWidget for spawner paths"""

    COLUMNS = (
        ("Advances", 100),
        ("Path", 100),
        ("Species", 100),
        ("Shiny", 80),
        ("Alpha", 80),
        ("Nature", 80),
        ("Effort Levels", 120),
        ("Gender", 70),
        ("Height", 80),
        ("Weight", 80),
    )

    def __init__(self):
        super().__init__()

        self.setColumnCount(10)
        self.setHorizontalHeaderLabels([column[0] for column in self.COLUMNS])
        for i, (_, width) in enumerate(self.COLUMNS):
            self.setColumnWidth(i, width)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.verticalHeader().setVisible(False)


class PathTrackerWindow(QDialog):
    """Path tracker window"""

    def __init__(
        self,
        parent: QWidget,
        encounter_table: EncounterAreaLA,
        seed: np.uint64,
        path: tuple[int],
        weather: LAWeather,
        time: LATime,
        species_info: dict[tuple[int, int], tuple[int, int, bool]],
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Path Tracker " + ("->".join(map(str, path[1:]))))
        self.main_layout = QVBoxLayout(self)
        self.path_table = PathTableWidget()
        self.main_layout.addWidget(self.path_table)
        self.resize(
            sum(column[1] for column in self.path_table.COLUMNS),
            self.height(),
        )
        group_rng = Xoroshiro128PlusRejection(seed)
        for advance, spawn_count in enumerate(path, start=-1):
            current_path = path[1 : advance + 2]
            for _ in range(spawn_count):
                generator_seed = np.uint64(group_rng.next())
                generator_rng = Xoroshiro128PlusRejection(generator_seed)
                group_rng.next()
                slot = encounter_table.calc_slot(
                    generator_rng.next() / 2 ** 64, np.int64(time), np.int64(weather)
                )
                gender_ratio, shiny_rolls, _ = species_info[(slot.species, slot.form)]
                fixed_rng = Xoroshiro128PlusRejection(np.uint64(generator_rng.next()))
                fixed_rng.next_rand(0xFFFFFFFF)  # encryption constant
                sidtid = fixed_rng.next_rand(0xFFFFFFFF)
                for _ in range(shiny_rolls):
                    pid = fixed_rng.next_rand(0xFFFFFFFF)
                    xor = (
                        (pid >> 16)
                        ^ (sidtid >> 16)
                        ^ (pid & 0xFFFF)
                        ^ (sidtid & 0xFFFF)
                    )
                    shiny = 2 if xor == 0 else 1 if xor < 16 else 0
                    if shiny:
                        break
                effort_levels = np.zeros(6, np.uint8)
                for _ in range(slot.guaranteed_ivs):
                    index = fixed_rng.next_rand(6)
                    while effort_levels[index] != 0:
                        index = fixed_rng.next_rand(6)
                    effort_levels[index] = 3
                for i in range(6):
                    if effort_levels[i] == 0:
                        effort_levels[i] = calc_effort_level(fixed_rng.next_rand(32))
                fixed_rng.next_rand(2)
                gender = 0 if gender_ratio == 0 else 1 if gender_ratio == 254 else 2
                if 1 <= gender_ratio < 254:
                    gender = (fixed_rng.next_rand(253) + 1) < gender_ratio
                nature = fixed_rng.next_rand(25)
                if slot.is_alpha:
                    height = weight = 255
                else:
                    height = fixed_rng.next_rand(0x81) + fixed_rng.next_rand(0x80)
                    weight = fixed_rng.next_rand(0x81) + fixed_rng.next_rand(0x80)

                personal_index = get_personal_index(slot.species, slot.form)
                display_size_metric = calc_display_size(
                    personal_index, height, weight, imperial=False
                )
                display_size_imperial = calc_display_size(
                    personal_index, height, weight, imperial=True
                )
                row_i = self.path_table.rowCount()
                self.path_table.insertRow(row_i)
                row = (
                    str(advance),
                    "->".join(str(x) for x in current_path),
                    get_name_en(slot.species, slot.form, slot.is_alpha),
                    "Square" if shiny == 2 else "Star" if shiny else "No",
                    "Yes" if slot.is_alpha else "No",
                    NATURES_EN[nature],
                    "/".join(str(x) for x in effort_levels),
                    "♂" if gender == 0 else "♀" if gender == 1 else "○",
                    f"{display_size_metric[0]:.02f} m | {display_size_imperial[0][0]:.00f}'{display_size_imperial[0][1]:.00f}\" ({height})",
                    f"{display_size_metric[1]:.02f} kg | {display_size_imperial[1]:.01f} lbs ({weight})",
                )
                for j, value in enumerate(row):
                    item = QTableWidgetItem(value)
                    self.path_table.setItem(row_i, j, item)
            group_rng.re_init(np.uint64(group_rng.next()))
