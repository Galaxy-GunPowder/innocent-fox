"""Paths and versions shared by every script."""
from pathlib import Path

FIREFOX_VERSION = "160.0.1"

PROJECT = Path(__file__).resolve().parent.parent
PATCHES = PROJECT / "patches"

# Firefox's build system breaks on paths with spaces, so the tree lives outside the project.
WORK = Path(r"D:\ifox")
DOWNLOADS = WORK / "dl"
SRC = WORK / "src"
OBJ = WORK / "obj"

TARBALL = DOWNLOADS / f"firefox-{FIREFOX_VERSION}.source.tar.xz"
SHA256SUMS = DOWNLOADS / "SHA256SUMS"

MOZILLABUILD = Path(r"C:\mozilla-build")
