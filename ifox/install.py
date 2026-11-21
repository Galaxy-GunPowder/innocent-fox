"""Download the Innocent Fox browser from GitHub Releases and unpack it.

  ifox-install                                       the version matching this package
  ifox-install --version 0.1.0
  ifox-install --zip innocent-fox-0.1.0-win64.zip    install from a file you already have

The browser lands in %LOCALAPPDATA%\\InnocentFox\\browser, where Browser() finds it.
The zip's SHA-256 is checked against the one published next to it.
"""
import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

REPO = "Galaxy-GunPowder/innocent-fox"
HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "InnocentFox"
INSTALLED = HOME / "browser" / "firefox" / "firefox.exe"


def _version():
    try:
        return version("innocent-fox")
    except PackageNotFoundError:
        return "0.1.0"


def _url(ver, name):
    return f"https://github.com/{REPO}/releases/download/v{ver}/{name}"


def _get(url, dest=None):
    req = urllib.request.Request(url, headers={"User-Agent": "ifox-install"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            if dest is None:
                return r.read()
            total = int(r.headers.get("Content-Length", 0))
            done = 0
            with open(dest, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"\r  {done >> 20} / {total >> 20} MB", end="", flush=True)
            print()
            return dest
    except urllib.error.HTTPError as e:
        raise SystemExit(f"download failed: HTTP {e.code} for {url}") from None


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def unpack(zip_path):
    target = HOME / "browser"
    tmp = Path(tempfile.mkdtemp(dir=HOME))
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmp)
    if not (tmp / "firefox" / "firefox.exe").exists():
        shutil.rmtree(tmp)
        raise SystemExit("the zip has no firefox/firefox.exe; is it an Innocent Fox package?")
    if target.exists():
        shutil.rmtree(target)
    tmp.rename(target)
    return INSTALLED


def main():
    ap = argparse.ArgumentParser(description="Install the Innocent Fox browser.")
    ap.add_argument("--version", default=_version())
    ap.add_argument("--zip", help="install from a local zip instead of downloading")
    a = ap.parse_args()
    HOME.mkdir(parents=True, exist_ok=True)

    if a.zip:
        zip_path = Path(a.zip)
    else:
        name = f"innocent-fox-{a.version}-win64.zip"
        print(f"downloading {name}")
        zip_path = Path(_get(_url(a.version, name), HOME / name))
        expected = _get(_url(a.version, name + ".sha256")).decode().split()[0]
        if sha256(zip_path) != expected:
            zip_path.unlink()
            raise SystemExit("checksum mismatch: the download is damaged or not the published file")
    exe = unpack(zip_path)
    if not a.zip:
        zip_path.unlink()
    print(f"installed: {exe}")


if __name__ == "__main__":
    sys.exit(main())
