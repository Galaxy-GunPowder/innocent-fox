"""Put the Innocent Fox icon into the Firefox source before a build.

  python scripts/branding.py           copy branding/fox.ico over the app icons (the build uses branding/unofficial)
  python scripts/branding.py restore   put Mozilla's icons back

Icons are binary, so they live here instead of in patches/. The originals are
kept in the tree's pristine\\_branding folder. The name change is patch 11.
Pages can't see either: the user agent still says Firefox.
"""
import shutil
import sys
from pathlib import Path

from common import PRISTINE, SRC as TREE_SRC

ROOT = Path(__file__).resolve().parents[1]
SRC = TREE_SRC / "browser" / "branding" / "unofficial"
KEEP = PRISTINE / "_branding"
ICON = ROOT / "branding" / "fox.ico"
TARGETS = ["firefox.ico", "firefox64.ico"]   # compiled into firefox.exe: window, taskbar, shortcut


def main():
    KEEP.mkdir(parents=True, exist_ok=True)
    for name in TARGETS:
        if not (KEEP / name).exists():
            shutil.copy2(SRC / name, KEEP / name)
        if sys.argv[1:] == ["restore"]:
            shutil.copy2(KEEP / name, SRC / name)
        else:
            shutil.copy2(ICON, SRC / name)
        print(("restored " if sys.argv[1:] == ["restore"] else "fox icon -> ") + str(SRC / name))


if __name__ == "__main__":
    main()
