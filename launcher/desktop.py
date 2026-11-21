"""Desktop icon entry: same as `ifox-open` (see ifox/desktop.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ifox.desktop import main_safe  # noqa: E402

main_safe()
