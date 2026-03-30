from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mobility_os.runtime.runtime import MobilityRuntime, run_demo

__all__ = ["MobilityRuntime", "run_demo"]
