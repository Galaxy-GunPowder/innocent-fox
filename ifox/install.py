"""The Innocent Fox browser: downloaded once from GitHub Releases, then reused.

Browser() calls ensure() itself, so `pip install` is the only step. To fetch it ahead of time:

  ifox-install                                       download now (skipped if already there)
  ifox-install --force                               download again
  ifox-install --zip innocent-fox-0.1.0-win64.zip    install from a file you already have

The browser lands in %LOCALAPPDATA%\\InnocentFox\\browser (or IFOX_HOME\\browser).
The zip's SHA-256 is checked against the one published next to it.
"""
import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO = "Galaxy-GunPowder/innocent-fox"
BROWSER_VERSION = "0.2.0"          # the browser build this package drives; its own release tag
HOME = Path(os.environ.get("IFOX_HOME") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "InnocentFox")
INSTALLED = HOME / "browser" / "firefox" / "firefox.exe"
_STAMP = HOME / "browser" / "ifox-version.txt"
_lock = threading.Lock()


def _url(ver, name):
    return f"https://github.com/{REPO}/releases/download/v{ver}/{name}"


def _get(url, dest=None):
    req = urllib.request.Request(url, headers={"User-Agent": "ifox-install"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            if dest is None:
                return r.read()
            total = int(r.headers.get("Content-Length", 0))
            done, shown = 0, -1
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    pct = done * 100 // total if total else 0
                    if pct // 10 != shown // 10:          # one line per 10%
                        shown = pct
                        print(f"  {pct}%  {done >> 20} / {total >> 20} MB", flush=True)
            return dest
    except (urllib.error.URLError, OSError) as e:
        code = getattr(e, "code", None)
        raise RuntimeError(f"browser download failed ({f'HTTP {code}' if code else e}) from {url}") from None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def unpack(zip_path, ver=BROWSER_VERSION):
    target = HOME / "browser"
    tmp = Path(tempfile.mkdtemp(dir=HOME))
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmp)
    if not (tmp / "firefox" / "firefox.exe").exists():
        shutil.rmtree(tmp)
        raise RuntimeError("the zip has no firefox/firefox.exe; is it an Innocent Fox package?")
    if target.exists():
        shutil.rmtree(target)
    tmp.rename(target)
    _STAMP.write_text(ver, encoding="utf-8")
    return INSTALLED


def installed_version():
    try:
        return _STAMP.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None


def download(ver=BROWSER_VERSION):
    """Download, check and unpack the browser. Returns firefox.exe."""
    HOME.mkdir(parents=True, exist_ok=True)
    name = f"innocent-fox-{ver}-win64.zip"
    print(f"Innocent Fox: downloading the browser, once ({name})", flush=True)
    zip_path = Path(_get(_url(ver, name), HOME / name))
    try:
        expected = _get(_url(ver, name + ".sha256")).decode().split()[0]
        if sha256(zip_path) != expected:
            raise RuntimeError("checksum mismatch: the download is damaged or not the published file")
        exe = unpack(zip_path, ver)
    finally:
        zip_path.unlink(missing_ok=True)
    print(f"Innocent Fox: installed {exe}", flush=True)
    return exe


def ensure():
    """firefox.exe of the right version, downloading it the first time."""
    with _lock:
        if INSTALLED.exists() and installed_version() in (BROWSER_VERSION, "local"):
            return INSTALLED
        return download()


def main():
    ap = argparse.ArgumentParser(description="Download the Innocent Fox browser.")
    ap.add_argument("--version", default=BROWSER_VERSION)
    ap.add_argument("--force", action="store_true", help="download again even if installed")
    ap.add_argument("--zip", help="install from a local zip instead of downloading")
    a = ap.parse_args()
    HOME.mkdir(parents=True, exist_ok=True)
    try:
        if a.zip:
            exe = unpack(Path(a.zip), "local")
        elif a.force or a.version != BROWSER_VERSION:
            exe = download(a.version)
        else:
            exe = ensure()
    except RuntimeError as e:
        raise SystemExit(str(e)) from None
    print(f"ready: {exe}")


if __name__ == "__main__":
    sys.exit(main())
