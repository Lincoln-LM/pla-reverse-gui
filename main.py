"""Main script for pla-reverse-gui"""

import sys
import qdarkstyle
from pla_reverse_gui.window import MapWindow
from qtpy.QtWidgets import QApplication

if __name__ == "__main__":
    # Create the Qt application
    app = QApplication(sys.argv)

    # Create the main window
    window = MapWindow()
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    window.show()
    window.setFocus()

    # Run the Qt event loop
    sys.exit(app.exec())
