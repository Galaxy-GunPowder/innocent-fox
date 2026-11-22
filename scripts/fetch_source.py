"""Download the Firefox source from Mozilla's archive, verify it, unpack it into the tree.

  python scripts/fetch_source.py                       160.0.1 into D:\\ifox\\src
  set IFOX_FIREFOX=159.0.1 && python scripts/fetch_source.py   into D:\\ifox\\v159\\src

The tarball is checked against Mozilla's SHA256SUMS for that release.
No git: indexing 300k files is too slow on Windows. patchtool.py tracks only the files we edit.
"""
import hashlib
import subprocess
import sys
import urllib.request

from common import ARCHIVE, DOWNLOADS, SHA256SUMS, SRC, TARBALL


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def download(url, dest):
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "ifox-build"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total, done, shown = int(r.headers.get("Content-Length", 0)), 0, -1
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            pct = done * 100 // total if total else 0
            if pct // 10 != shown // 10:
                shown = pct
                print(f"  {pct}%  {done >> 20} / {total >> 20} MB", flush=True)
    tmp.replace(dest)


def expected_sha256():
    want = f"source/{TARBALL.name}"
    for line in SHA256SUMS.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if name.strip() == want:
            return digest
    sys.exit(f"{want} not listed in {SHA256SUMS}")


def main():
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    if not SHA256SUMS.exists():
        download(f"{ARCHIVE}/SHA256SUMS", SHA256SUMS)
    if not TARBALL.exists():
        print(f"downloading {TARBALL.name}", flush=True)
        download(f"{ARCHIVE}/source/{TARBALL.name}", TARBALL)
    got, want = sha256(TARBALL), expected_sha256()
    if got != want:
        sys.exit(f"checksum mismatch: got {got}, want {want}")
    print("checksum ok", flush=True)

    if SRC.exists():
        sys.exit(f"{SRC} already exists; delete it first to re-unpack")

    # Unpack straight into SRC: no move afterwards, because a failed rename makes
    # shutil.move copy 300k files and then delete the original.
    # Windows' bundled bsdtar handles .xz and is much faster than Python's tarfile.
    SRC.mkdir(parents=True)
    subprocess.run([r"C:\Windows\System32\tar.exe", "-xf", str(TARBALL), "-C", str(SRC),
                    "--strip-components=1"], check=True)
    if not (SRC / "dom" / "base" / "Navigator.cpp").exists():
        sys.exit(f"unpack incomplete: {SRC}")
    print(f"unpacked to {SRC}", flush=True)


if __name__ == "__main__":
    main()
