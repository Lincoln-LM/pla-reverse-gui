"""Height and Weight measurement widget"""
# pylint: disable=no-name-in-module
from qtpy.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QVBoxLayout,
    QWidget,
)

# pylint: enable=no-name-in-module
from ..util import get_name_en, find_evo_line


class MeasurementWidget(QWidget):
    """Height and Weight measurement widget"""

    def __init__(
        self,
    ) -> None:
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.measurement_system_combobox = QComboBox()
        self.measurement_system_combobox.addItem("Metric", False)
        self.measurement_system_combobox.addItem("Imperial", True)
        self.measurement_system_combobox.currentIndexChanged.connect(
            self.measurement_system_changed
        )
        self.add_measurement_button = QPushButton("Add Measurement")
        self.add_measurement_button.clicked.connect(self.new_measurement)
        self.base_species_form: tuple[int, int] = None
        self.evo_line: tuple[tuple[int, int]] = ()
        self.measurements = []
        self.main_layout.addWidget(self.measurement_system_combobox)
        self.main_layout.addWidget(self.add_measurement_button)

    def update_base_species_form(self, species_form: tuple[int, int]) -> None:
        """Update base species and form"""
        self.base_species_form = species_form
        if self.base_species_form is not None:
            self.evo_line = list(find_evo_line(*self.base_species_form))
            # move base species to index 0
            self.evo_line = [
                self.evo_line.pop(self.evo_line.index(self.base_species_form))
            ] + self.evo_line
            for (
                species,
                (
                    height_feet,
                    height_inches,
                    height_imperial,
                    height_metric,
                ),
                weight_measurement,
            ) in self.measurements:
                species.deleteLater()
                height_feet.deleteLater()
                height_inches.deleteLater()
                height_imperial.deleteLater()
                height_metric.deleteLater()
                weight_measurement.deleteLater()
            self.measurements = []
        self.measurement_system_changed(0)

    def new_measurement(self) -> None:
        """Create a new measurement"""
        species = QComboBox()
        for species_form in self.evo_line:
            species.addItem(get_name_en(*species_form), species_form)

        height_imperial = QWidget()
        height_imperial_layout = QHBoxLayout(height_imperial)
        height_feet = QSpinBox(suffix=" ft", maximum=99999)
        height_inches = QSpinBox(suffix=" in", maximum=99999)
        height_imperial_layout.addWidget(height_feet)
        height_imperial_layout.addWidget(height_inches)
        height_metric = QDoubleSpinBox(decimals=2, suffix=" m", maximum=99999)
        weight = QDoubleSpinBox(maximum=99999)
        self.measurements.append(
            (
                species,
                (height_feet, height_inches, height_imperial, height_metric),
                weight,
            )
        )
        self.main_layout.addWidget(species)
        self.main_layout.addWidget(height_imperial)
        self.main_layout.addWidget(height_metric)
        self.main_layout.addWidget(weight)
        imperial = self.measurement_system_combobox.currentData()
        height_imperial.setVisible(imperial)
        height_metric.setVisible(not imperial)
        weight.setSuffix(" lbs" if imperial else " kg")
        weight.setDecimals(1 if imperial else 2)

    def measurement_system_changed(self, index: int) -> None:
        """Callback for when the measurement system changes"""
        if index == -1:
            return
        for (
            _,
            (
                height_feet,
                height_inches,
                height_imperial,
                height_metric,
            ),
            weight_measurement,
        ) in self.measurements:
            height_feet.setValue(0)
            height_inches.setValue(0)
            height_metric.setValue(0)
            weight_measurement.setValue(0)

            imperial = self.measurement_system_combobox.currentData()
            height_imperial.setVisible(imperial)
            height_metric.setVisible(not imperial)
            weight_measurement.setSuffix(" lbs" if imperial else " kg")
            weight_measurement.setDecimals(1 if imperial else 2)

    def get_value(self) -> tuple:
        """Get all size measurement values"""
        heights = []
        weights = []
        measured_species = []
        imperial = self.measurement_system_combobox.currentData()
        for (
            species,
            (
                height_feet,
                height_inches,
                _,
                height_metric,
            ),
            weight_measurement,
        ) in self.measurements:
            measured_species.append(species.currentData())
            if imperial:
                heights.append((height_feet.value(), height_inches.value()))
            else:
                heights.append(height_metric.value())
            weights.append(weight_measurement.value())
        return measured_species, heights, weights, imperial
