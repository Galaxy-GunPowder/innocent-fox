"""Paths and versions shared by every script.

The Firefox version comes from IFOX_FIREFOX (default 160.0.1):
  set IFOX_FIREFOX=159.0.1 && python scripts/fetch_source.py
160 keeps the original layout (D:\\ifox\\src, obj, pristine); other versions get
their own tree, D:\\ifox\\v159\\src, obj, pristine.
"""
import os
from pathlib import Path

DEFAULT_VERSION = "160.0.1"
FIREFOX_VERSION = os.environ.get("IFOX_FIREFOX") or DEFAULT_VERSION
MAJOR = FIREFOX_VERSION.split(".")[0]

PROJECT = Path(__file__).resolve().parent.parent
PATCHES = PROJECT / "patches"

# Firefox's build system breaks on paths with spaces, so the tree lives outside the project.
WORK = Path(r"D:\ifox")
TREE = WORK if FIREFOX_VERSION == DEFAULT_VERSION else WORK / f"v{MAJOR}"
DOWNLOADS = WORK / "dl"
SRC = TREE / "src"
OBJ = TREE / "obj"
PRISTINE = TREE / "pristine"

TARBALL = DOWNLOADS / f"firefox-{FIREFOX_VERSION}.source.tar.xz"
SHA256SUMS = DOWNLOADS / ("SHA256SUMS" if FIREFOX_VERSION == DEFAULT_VERSION else f"SHA256SUMS-{FIREFOX_VERSION}")
ARCHIVE = f"https://archive.mozilla.org/pub/firefox/releases/{FIREFOX_VERSION}"

MOZILLABUILD = Path(r"C:\mozilla-build")
