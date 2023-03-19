import numpy as np
from numba_pokemon_prngs.data import SPECIES_EN
from numba_pokemon_prngs.data.encounter import (
    ENCOUNTER_INFORMATION_LA,
    ENCOUNTER_TABLE_NAMES_LA,
    SPAWNER_INFORMATION_LA,
    SPAWNER_NAMES_LA,
)
from numba_pokemon_prngs.enums import LAArea
from pyqtlet2 import L, MapWidget
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MapWindow(QWidget):
    MAP_NAMES: dict[LAArea, str] = {
        LAArea.OBSIDIAN_FIELDLANDS: "obsidianfieldlands",
        LAArea.CRIMSON_MIRELANDS: "crimsonmirelands",
        LAArea.COBALT_COASTLANDS: "cobaltcoastlands",
        LAArea.CORONET_HIGHLANDS: "coronethighlands",
        LAArea.ALABASTER_ICELANDS: "alabastericelands",
    }

    def __init__(self):
        super().__init__()
        self.tile_layer: L.tileLayer = None
        self.markers_initialized = False
        self.setup_widgets()
        self.setup_resources()
        self.select_map(0)

        self.show()

    def setup_widgets(self) -> None:
        """Draw the widgets and main layout of the window"""
        self.map_widget = MapWidget()

        self.main_layout = QHBoxLayout()

        self.options_widget = QWidget()
        self.options_layout = QVBoxLayout(self.options_widget)

        self.location_combobox = QComboBox()
        self.location_combobox.currentIndexChanged.connect(self.select_map)
        for map_id, name in self.MAP_NAMES.items():
            self.location_combobox.addItem(name, map_id)
        self.spawner_combobox = QComboBox()
        self.spawner_combobox.currentIndexChanged.connect(self.spawner_combobox_changed)
        self.spawner_summary = QLabel("")
        self.seed_finder_button = QPushButton("Seed Finder")

        self.options_layout.addWidget(self.location_combobox)
        self.options_layout.addWidget(self.spawner_combobox)
        self.options_layout.addWidget(self.spawner_summary)
        self.options_layout.addWidget(self.seed_finder_button)

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

        self.deselected_marker_icon = L.icon(
            "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png",
            {
                "shadowUrl": "https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png",
                "iconSize": [25, 41],
                "iconAnchor": [12, 41],
                "popupAnchor": [1, -34],
                "shadowSize": [41, 41],
            },
        )
        self.deselected_marker_icon.addTo(self.map)
        self.all_markers: dict[LAArea, list[L.marker]] = {}
        for map_id in self.MAP_NAMES.keys():
            marker_list = []
            for spawner in SPAWNER_INFORMATION_LA[map_id].spawners:
                if spawner.is_mass_outbreak:
                    continue
                coords = spawner.coordinates.as_tuple()
                marker = L.marker([coords[2] * -0.5, coords[0] * 0.5])
                marker.click.connect(self.marker_onclick)
                marker_list.append(marker)
            self.all_markers[map_id] = marker_list
        self.rendered_markers = []

    def select_map(self, index: int) -> None:
        map_id: LAArea = self.location_combobox.itemData(index)
        self.spawner_information = SPAWNER_INFORMATION_LA[map_id].spawners
        self.encounter_information = ENCOUNTER_INFORMATION_LA[map_id]
        self.map.setView([4096, 4096], 1)
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
            if spawner.is_mass_outbreak:
                continue
            self.spawner_combobox.addItem(
                f"{SPAWNER_NAMES_LA.get(spawner.spawner_id, '')} - 0x{spawner.spawner_id:016X}"
            )

        self.select_marker(self.rendered_markers[0])

    def marker_onclick(self, options: dict) -> None:
        """Callback for when a marker is clicked"""
        marker: L.marker = options["sender"]
        self.select_marker(marker)

    def spawner_combobox_changed(self, index: int) -> None:
        """Callback for when the spawner combobox's selected item changes"""
        if -1 < index < len(self.rendered_markers):
            self.select_marker(self.rendered_markers[index])

    def select_marker(self, marker: L.marker) -> None:
        """Select a marker on the map and update displays"""
        if self.selected_marker is not None:
            # deselect old marker
            self.map.runJavaScriptForMap(
                f"{self.selected_marker.jsName}.setIcon({self.deselected_marker_icon.jsName})"
            )
        if marker in self.rendered_markers:
            self.spawner_combobox.setCurrentIndex(self.rendered_markers.index(marker))
            spawner = self.spawner_information[self.spawner_combobox.currentIndex()]
            self.map.setZoom(2)
            self.map.setView(marker.latLng, 2)
            self.spawner_summary.setText(
                f"Spawn Count: {spawner.min_spawn_count}-{spawner.max_spawn_count}\n"
                f"Table: {ENCOUNTER_TABLE_NAMES_LA.get(np.uint64(spawner.encounter_table_id), '')} - 0x{spawner.encounter_table_id:016X}\n"
                + "\n".join(
                    f" - {'Alpha ' if slot.is_alpha else ''}{SPECIES_EN[slot.species]}{f'-{slot.form}' if slot.form else ''} Lv. {slot.min_level}-{slot.max_level} {f'{slot.guaranteed_ivs} Guaranteed IVs' if slot.guaranteed_ivs else ''}"
                    for slot in self.encounter_information[
                        np.uint64(spawner.encounter_table_id)
                    ].slots.view(np.recarray)
                )
            )
        # select new marker
        self.map.runJavaScriptForMap(
            f"{marker.jsName}.setIcon({self.selected_marker_icon.jsName})"
        )
        self.selected_marker = marker
