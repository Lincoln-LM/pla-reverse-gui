"""QWidget window for main map display"""

import numpy as np
from numba_pokemon_prngs.data.encounter import (
    ENCOUNTER_INFORMATION_LA,
    ENCOUNTER_TABLE_NAMES_LA,
    SPAWNER_INFORMATION_LA,
    SPAWNER_NAMES_LA,
    NHO_LOTTERY_TABLE_LA,
    NHO_GROUP_TABLE_LA,
)
from numba_pokemon_prngs.enums import LAArea
from numba_pokemon_prngs.data.fbs.encounter_la import PlacementSpawner8a
from pyqtlet2 import L, MapWidget

# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=no-name-in-module

from ..util import get_name_en
from .seed_finder_window import SeedFinderWindow
from .generator_window import GeneratorWindow
from .checkable_combobox_widget import CheckableComboBox


class MapWindow(QWidget):
    """QWidget window for main map display"""

    MAP_NAMES: dict[LAArea, str] = {
        LAArea.OBSIDIAN_FIELDLANDS: "obsidianfieldlands",
        LAArea.CRIMSON_MIRELANDS: "crimsonmirelands",
        LAArea.COBALT_COASTLANDS: "cobaltcoastlands",
        LAArea.CORONET_HIGHLANDS: "coronethighlands",
        LAArea.ALABASTER_ICELANDS: "alabastericelands",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PLA Seed Finder")
        self.selected_marker = None
        self.tile_layer: L.tileLayer = None
        self.markers_initialized = False
        self.setup_widgets()
        self.setup_resources()
        self.select_map(0)

        self.show()

    def setup_widgets(self) -> None:
        """Draw the widgets and main layout of the window"""
        self.map_widget = MapWidget()
        settings = self.map_widget.settings()
        settings.setAttribute(
            settings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )

        self.main_layout = QHBoxLayout()

        self.options_widget = QWidget()
        self.options_layout = QVBoxLayout(self.options_widget)

        self.marker_filter = CheckableComboBox()
        self.marker_filter.add_checked_item("Single Spawners", 1, True)
        self.marker_filter.add_checked_item("Multi Spawners", 2, True)
        self.marker_filter.add_checked_item("Mass Outbreak Spawners", 4)
        self.marker_filter.add_checked_item("Massive Mass Outbreak Spawners", 8)
        self.marker_filter.add_checked_item("Variable Multi Spawners", 16, True)
        self.marker_filter.changed.connect(self.update_mark_filter)

        self.location_combobox = QComboBox()
        self.location_combobox.currentIndexChanged.connect(self.select_map)
        for map_id, name in self.MAP_NAMES.items():
            self.location_combobox.addItem(name, map_id)
        self.spawner_combobox = QComboBox()
        self.spawner_combobox.currentIndexChanged.connect(self.spawner_combobox_changed)
        self.first_wave_combobox = QComboBox()
        self.first_wave_combobox.currentIndexChanged.connect(
            self.first_wave_combobox_changed
        )
        self.first_wave_combobox.setHidden(True)
        self.second_wave_combobox = QComboBox()
        self.second_wave_combobox.currentIndexChanged.connect(
            self.second_wave_combobox_changed
        )
        self.second_wave_combobox.setHidden(True)
        self.spawner_summary = QLabel("")
        self.seed_finder_button = QPushButton("Seed Finder")
        self.seed_finder_button.clicked.connect(self.open_seed_finder)
        self.generator_button = QPushButton("Open Generator")
        self.generator_button.clicked.connect(self.open_generator)

        self.options_layout.addWidget(self.marker_filter)
        self.options_layout.addWidget(self.location_combobox)
        self.options_layout.addWidget(self.spawner_combobox)
        self.options_layout.addWidget(self.first_wave_combobox)
        self.options_layout.addWidget(self.second_wave_combobox)
        self.options_layout.addWidget(self.spawner_summary)
        self.options_layout.addWidget(self.seed_finder_button)
        self.options_layout.addWidget(self.generator_button)

        self.main_layout.addWidget(self.options_widget, 0)
        self.main_layout.addWidget(self.map_widget, 1)
        self.setLayout(self.main_layout)

        self.map = L.map(
            self.map_widget,
            options="""{
                minZoom: 0,
                maxZoom: 2,
                crs: L.CRS.Simple,
            }""",
        )

    def setup_resources(self) -> None:
        """Initialize static resources used by the widget"""
        self.selected_marker_icon = L.icon(
            "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
            {
                "shadowUrl": "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
                "iconSize": [25, 41],
                "iconAnchor": [12, 41],
                "popupAnchor": [1, -34],
                "shadowSize": [41, 41],
            },
        )
        self.selected_marker_icon.addTo(self.map)

        self.variable_multi_marker_icon = L.icon(
            "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-black.png",
            {
                "shadowUrl": "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
                "iconSize": [25, 41],
                "iconAnchor": [12, 41],
                "popupAnchor": [1, -34],
                "shadowSize": [41, 41],
            },
        )

        self.variable_multi_marker_icon.addTo(self.map)

        self.single_spawner_icon = L.icon(
            "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png",
            {
                "shadowUrl": "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
                "iconSize": [25, 41],
                "iconAnchor": [12, 41],
                "popupAnchor": [1, -34],
                "shadowSize": [41, 41],
            },
        )
        self.single_spawner_icon.addTo(self.map)

        self.multi_spawner_icon = L.icon(
            "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
            {
                "shadowUrl": "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
                "iconSize": [25, 41],
                "iconAnchor": [12, 41],
                "popupAnchor": [1, -34],
                "shadowSize": [41, 41],
            },
        )
        self.multi_spawner_icon.addTo(self.map)

        self.mass_outbreak_marker_icon = L.icon(
            "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-violet.png",
            {
                "shadowUrl": "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
                "iconSize": [25, 41],
                "iconAnchor": [12, 41],
                "popupAnchor": [1, -34],
                "shadowSize": [41, 41],
            },
        )
        self.mass_outbreak_marker_icon.addTo(self.map)

        self.massive_mass_outbreak_marker_icon = L.icon(
            "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-gold.png",
            {
                "shadowUrl": "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
                "iconSize": [25, 41],
                "iconAnchor": [12, 41],
                "popupAnchor": [1, -34],
                "shadowSize": [41, 41],
            },
        )
        self.massive_mass_outbreak_marker_icon.addTo(self.map)

        self.all_markers: dict[LAArea, list[L.marker]] = {}
        self.marker_icons: dict[L.marker, L.icon] = {}
        for map_id in self.MAP_NAMES.keys():
            marker_list = []
            for spawner in SPAWNER_INFORMATION_LA[map_id].spawners:
                mass_outbreak = spawner.is_mass_outbreak
                massive_mass_outbreak = mass_outbreak and (
                    np.uint64(spawner.encounter_table_id)
                    not in ENCOUNTER_INFORMATION_LA[map_id]
                )
                single_spawner = (
                    spawner.min_spawn_count == spawner.max_spawn_count
                    and spawner.min_spawn_count == 1
                    and not mass_outbreak
                )
                multi_spawner = (
                    spawner.min_spawn_count == spawner.max_spawn_count
                    and spawner.min_spawn_count != 1
                    and not mass_outbreak
                )
                coords = spawner.coordinates.as_tuple()
                marker = L.marker([coords[2] * -0.5, coords[0] * 0.5])
                marker.click.connect(self.marker_onclick)
                marker_list.append(marker)
                self.marker_icons[marker] = (
                    self.massive_mass_outbreak_marker_icon
                    if massive_mass_outbreak
                    else (
                        self.mass_outbreak_marker_icon
                        if mass_outbreak
                        else (
                            self.single_spawner_icon
                            if single_spawner
                            else (
                                self.multi_spawner_icon
                                if multi_spawner
                                else self.variable_multi_marker_icon
                            )
                        )
                    )
                )
            self.all_markers[map_id] = marker_list
        self.rendered_markers = []

    def update_mark_filter(self, _: int = None) -> None:
        """Callback to be run when the mark filter combobox is changed"""
        mark_filter = self.marker_filter.get_checked_values() or (1, 2, 4, 8, 16)
        for rendered_marker in self.rendered_markers:
            # unrender
            self.map.runJavaScriptForMap(
                f"map.removeLayer({rendered_marker.layerName})"
            )
        for i, marker in enumerate(self.rendered_markers):
            spawner = self.spawner_information[i]

            mass_outbreak = spawner.is_mass_outbreak
            massive_mass_outbreak = mass_outbreak and (
                np.uint64(spawner.encounter_table_id)
                not in ENCOUNTER_INFORMATION_LA[self.location_combobox.currentData()]
            )
            single_spawner = (
                spawner.min_spawn_count == spawner.max_spawn_count
                and spawner.min_spawn_count == 1
                and not mass_outbreak
            )
            multi_spawner = (
                spawner.min_spawn_count == spawner.max_spawn_count
                and spawner.min_spawn_count != 1
                and not mass_outbreak
            )

            if single_spawner and 1 not in mark_filter:
                continue
            if multi_spawner and 2 not in mark_filter:
                continue
            if mass_outbreak and not massive_mass_outbreak and 4 not in mark_filter:
                continue
            if massive_mass_outbreak and 8 not in mark_filter:
                continue
            if (
                not (single_spawner or multi_spawner or mass_outbreak)
                and 16 not in mark_filter
            ):
                continue
            # render
            self.map.runJavaScriptForMap(f"map.addLayer({marker.layerName})")

    def select_map(self, index: int) -> None:
        """Callback to be run when the map combobox is changed"""
        map_id: LAArea = self.location_combobox.itemData(index)
        self.spawner_information = SPAWNER_INFORMATION_LA[map_id].spawners
        self.encounter_information = ENCOUNTER_INFORMATION_LA[map_id]
        if not hasattr(self, "map"):
            return
        self.map.setView([4096, 4096], 1)
        if self.tile_layer is not None:
            self.map.removeLayer(self.tile_layer)
        self.tile_layer = L.tileLayer(
            f"https://www.serebii.net/pokearth/hisui/{self.MAP_NAMES[map_id]}/tile_{{z}}-{{x}}-{{y}}.png",
            options="""{
            minZoom: 0,
            maxZoom: 2,
            noWrap: true,
            attribution: "Pok&eacute;mon Legends: Arceus",
        }""",
        )
        self.tile_layer.addTo(self.map)
        self.map.setMaxBounds(
            """new L.LatLngBounds(map.unproject([0, 2048], map.getMaxZoom()), map.unproject([2048, 0], map.getMaxZoom()))"""
        )

        if not self.markers_initialized:
            self.markers_initialized = True
            for markers in self.all_markers.values():
                for marker in markers:
                    # every marker needs to exist before the map is loaded
                    self.map.addLayer(marker)
                    # assign default icon
                    self.map.runJavaScriptForMap(
                        f"{marker.jsName}.setIcon({self.marker_icons[marker].jsName})"
                    )
                    # unrender
                    self.map.runJavaScriptForMap(f"map.removeLayer({marker.layerName})")
        for rendered_marker in self.rendered_markers:
            # unrender
            self.map.runJavaScriptForMap(
                f"map.removeLayer({rendered_marker.layerName})"
            )
        self.rendered_markers = []
        for marker in self.all_markers[map_id]:
            # render
            self.map.runJavaScriptForMap(f"map.addLayer({marker.layerName})")
            self.rendered_markers.append(marker)
        self.selected_marker: L.marker = None
        self.spawner_combobox.clear()

        for spawner in self.spawner_information:
            self.spawner_combobox.addItem(
                f"{SPAWNER_NAMES_LA.get(spawner.spawner_id, '')} - 0x{spawner.spawner_id:016X}",
                spawner,
            )

        self.select_marker(self.rendered_markers[0])
        self.update_mark_filter()

    def marker_onclick(self, options: dict) -> None:
        """Callback for when a marker is clicked"""
        marker: L.marker = options["sender"]
        self.select_marker(marker)

    def spawner_combobox_changed(self, index: int) -> None:
        """Callback for when the spawner combobox's selected item changes"""
        if -1 < index < len(self.rendered_markers):
            self.select_marker(self.rendered_markers[index])

    def first_wave_combobox_changed(self, _: int) -> None:
        """Callback for when the first wave combobox's selected item changes"""
        first_wave = self.first_wave_combobox.currentData()
        if first_wave is None:
            return
        self.second_wave_combobox.clear()
        self.second_wave_combobox.addItem("Second Wave: None", None)
        for second_wave in first_wave.wave_details:
            first_slot = self.encounter_information[
                np.uint64(second_wave.encounter_table_id)
            ].slots.view(np.recarray)[0]
            self.second_wave_combobox.addItem(
                f"Second Wave: {get_name_en(first_slot.species, first_slot.form, first_slot.is_alpha)} - 0x{first_wave.first_wave_encounter_table_id:016X}",
                second_wave,
            )

    def second_wave_combobox_changed(self, _: int) -> None:
        """Callback for when the second wave combobox's selected item changes"""
        first_wave = self.first_wave_combobox.currentData()
        second_wave = self.second_wave_combobox.currentData()
        if first_wave is None:
            return
        spawner_text = (
            "First Wave:\n"
            + "\n".join(
                f" - {get_name_en(slot.species, slot.form, slot.is_alpha)} Lv. {slot.min_level}-{slot.max_level} {f'{slot.guaranteed_ivs} Guaranteed IVs' if slot.guaranteed_ivs else ''}"
                for slot in self.encounter_information[
                    np.uint64(first_wave.first_wave_encounter_table_id)
                ].slots.view(np.recarray)
            )
            + (
                "\nSecond Wave:\n"
                + "\n".join(
                    f" - {get_name_en(slot.species, slot.form, slot.is_alpha)} Lv. {slot.min_level}-{slot.max_level} {f'{slot.guaranteed_ivs} Guaranteed IVs' if slot.guaranteed_ivs else ''}"
                    for slot in self.encounter_information[
                        np.uint64(second_wave.encounter_table_id)
                    ].slots.view(np.recarray)
                )
                if second_wave is not None
                else ""
            )
        )
        # should only apply to unown, truncate spawner summary to 15 lines
        if spawner_text.count("\n") > 15:
            spawner_text = "\n".join(spawner_text.split("\n")[:15]) + "\n..."
        self.spawner_summary.setText(
            spawner_text
        )


    def select_marker(self, marker: L.marker) -> None:
        """Select a marker on the map and update displays"""
        if self.selected_marker is not None:
            # deselect old marker
            self.map.runJavaScriptForMap(
                f"{self.selected_marker.jsName}.setIcon({self.marker_icons[self.selected_marker].jsName})"
            )
        if marker in self.rendered_markers:
            self.spawner_combobox.setCurrentIndex(self.rendered_markers.index(marker))
            spawner: PlacementSpawner8a = self.spawner_combobox.currentData()
            # TODO: disable seed finder for alpha spawners
            # self.seed_finder_button.setDisabled(
            #     spawner.min_spawn_count != spawner.max_spawn_count
            # )
            # self.generator_button.setDisabled(
            #     spawner.min_spawn_count != spawner.max_spawn_count
            # )
            self.map.setZoom(2)
            self.map.setView(marker.latLng, 2)
            # is MMO
            if spawner.is_mass_outbreak and (
                np.uint64(spawner.encounter_table_id)
                not in ENCOUNTER_INFORMATION_LA[self.location_combobox.currentData()]
            ):
                self.first_wave_combobox.setVisible(True)
                self.second_wave_combobox.setVisible(True)
                self.first_wave_combobox.clear()
                for first_wave_lotto in NHO_LOTTERY_TABLE_LA.lottery_group_lookup[
                    np.uint64(spawner.encounter_table_id)
                ].full_table_lookup.values():
                    # fnv1a_64("")
                    if first_wave_lotto.hash == 0xCBF29CE484222645:
                        continue
                    first_wave = NHO_GROUP_TABLE_LA.group_lookup[first_wave_lotto.hash]
                    first_slot = self.encounter_information[
                        np.uint64(first_wave.first_wave_encounter_table_id)
                    ].slots.view(np.recarray)[0]
                    self.first_wave_combobox.addItem(
                        f"First Wave: {get_name_en(first_slot.species, first_slot.form, first_slot.is_alpha)} - 0x{first_wave.first_wave_encounter_table_id:016X}",
                        first_wave,
                    )
            else:
                self.first_wave_combobox.setHidden(True)
                self.second_wave_combobox.setHidden(True)
                spawner_text = (
                    f"Spawn Count: {spawner.min_spawn_count}-{spawner.max_spawn_count}\n"
                    f"Table: {ENCOUNTER_TABLE_NAMES_LA.get(np.uint64(spawner.encounter_table_id), '')} - 0x{spawner.encounter_table_id:016X}\n"
                    + "\n".join(
                        f" - {get_name_en(slot.species, slot.form, slot.is_alpha)} Lv. {slot.min_level}-{slot.max_level} {f'{slot.guaranteed_ivs} Guaranteed IVs' if slot.guaranteed_ivs else ''}"
                        for slot in self.encounter_information[
                            np.uint64(spawner.encounter_table_id)
                        ].slots.view(np.recarray)
                    )
                    if np.uint64(spawner.encounter_table_id)
                    in ENCOUNTER_INFORMATION_LA[self.location_combobox.currentData()]
                    else "Encounter table not found."
                )
                # should only apply to unown, truncate spawner summary to 15 lines
                if spawner_text.count("\n") > 15:
                    spawner_text = "\n".join(spawner_text.split("\n")[:15]) + "\n..."
                self.spawner_summary.setText(
                    spawner_text
                )
        # select new marker
        self.map.runJavaScriptForMap(
            f"{marker.jsName}.setIcon({self.selected_marker_icon.jsName})"
        )
        self.selected_marker = marker

    def open_seed_finder(self) -> None:
        """Open Seed Finder for spawner"""
        spawner = self.spawner_information[self.spawner_combobox.currentIndex()]
        if spawner.is_mass_outbreak and (
            np.uint64(spawner.encounter_table_id)
            not in ENCOUNTER_INFORMATION_LA[self.location_combobox.currentData()]
        ):
            encounter_table = self.encounter_information[
                np.uint64(
                    self.first_wave_combobox.currentData().first_wave_encounter_table_id
                )
            ]
        else:
            encounter_table = self.encounter_information[
                np.uint64(spawner.encounter_table_id)
            ]
        seed_finder_window = SeedFinderWindow(
            self,
            spawner,
            encounter_table,
        )
        seed_finder_window.show()
        seed_finder_window.setFocus()

    def open_generator(self) -> None:
        """Open Generator for spawner"""
        spawner = self.spawner_information[self.spawner_combobox.currentIndex()]
        # is MMO
        if spawner.is_mass_outbreak and (
            np.uint64(spawner.encounter_table_id)
            not in ENCOUNTER_INFORMATION_LA[self.location_combobox.currentData()]
        ):
            first_encounter_table = self.encounter_information[
                np.uint64(
                    self.first_wave_combobox.currentData().first_wave_encounter_table_id
                )
            ]
            second_wave = self.second_wave_combobox.currentData()

            second_wave_encounter_table = (
                self.encounter_information[np.uint64(second_wave.encounter_table_id)]
                if second_wave is not None
                else None
            )
        else:
            first_encounter_table = self.encounter_information[
                np.uint64(spawner.encounter_table_id)
            ]
            second_wave_encounter_table = None
        generator_window = GeneratorWindow(
            self, spawner, first_encounter_table, second_wave_encounter_table
        )
        generator_window.show()
        generator_window.setFocus()
