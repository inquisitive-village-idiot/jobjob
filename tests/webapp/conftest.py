#!/usr/bin/env python3
"""Webapp backend test setup.

Backend modules import as ``from services import ...`` (see the sys.path shim in
``webapp/backend/main.py``), so the backend directory itself must be importable.
"""

import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "webapp" / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
