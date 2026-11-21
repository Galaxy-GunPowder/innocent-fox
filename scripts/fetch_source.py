"""Verify the Firefox source tarball and unpack it to D:\\ifox\\src.

No git: indexing 300k files is too slow on Windows. patchtool.py tracks only the files we edit.
"""
import hashlib
import subprocess
import sys

from common import SHA256SUMS, SRC, TARBALL


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def expected_sha256():
    want = f"source/{TARBALL.name}"
    for line in SHA256SUMS.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if name.strip() == want:
            return digest
    sys.exit(f"{want} not listed in {SHA256SUMS}")


def main():
    got, want = sha256(TARBALL), expected_sha256()
    if got != want:
        sys.exit(f"checksum mismatch: got {got}, want {want}")
    print("checksum ok")

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
    print(f"unpacked to {SRC}")


if __name__ == "__main__":
    main()
