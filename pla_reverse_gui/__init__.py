"""Module for pla-reverse-gui functionality"""
# pylint: disable=wrong-import-position
import os

os.environ["QT_API"] = "pyside6"

from .pla_reverse_main import pla_reverse  # noqa: E402
