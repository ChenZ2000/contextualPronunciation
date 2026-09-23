"""Import pure core modules without importing NVDA's global plugin entry point."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType

PACKAGE_NAME = "_contextualPronunciationCoreUnderTest"
PLUGIN_PATH = Path(__file__).resolve().parents[1] / "addon" / "globalPlugins" / "contextualPronunciation"


def load(module_name: str):
	if PACKAGE_NAME not in sys.modules:
		package = ModuleType(PACKAGE_NAME)
		package.__path__ = [str(PLUGIN_PATH)]
		package.__package__ = PACKAGE_NAME
		sys.modules[PACKAGE_NAME] = package
	return importlib.import_module(f"{PACKAGE_NAME}.{module_name}")
