"""Make and apply our patches without putting 300k Firefox files under git.

Only files we touch are tracked: their original copy goes to D:\\ifox\\pristine.

  python scripts/patchtool.py edit dom/base/Navigator.cpp ...   register files BEFORE editing them
  python scripts/patchtool.py status                             files changed since the last saved patch
  python scripts/patchtool.py save 02-navigator                  write those changes as patches/02-navigator.patch
  python scripts/patchtool.py redo 03-screen                     rebuild one patch after fixing its files in the tree
  python scripts/patchtool.py apply                              restore originals, apply every patch in order
  python scripts/patchtool.py init                               fresh tree (another Firefox version): record originals of every patched file
"""
import difflib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from common import MAJOR, PATCHES, PRISTINE, SRC, TREE


def patch_list():
    """patches/*.patch in order; patches/v159/<same name> replaces one for Firefox 159."""
    own = PATCHES / f"v{MAJOR}"
    return [own / p.name if (own / p.name).exists() else p for p in sorted(PATCHES.glob("*.patch"))]


NEW_LIST = PRISTINE / "_new_files.txt"


def read(path):
    return path.read_bytes().decode("utf-8", "surrogateescape") if path.exists() else None


def new_files():
    return set(NEW_LIST.read_text().split()) if NEW_LIST.exists() else set()


def tracked():
    # _branding holds Mozilla's icons for branding.py, not files a patch changes.
    files = {p.relative_to(PRISTINE).as_posix() for p in PRISTINE.rglob("*")
             if p.is_file() and p != NEW_LIST and not p.relative_to(PRISTINE).as_posix().startswith("_branding/")}
    return sorted(files | new_files())


def cmd_edit(paths):
    PRISTINE.mkdir(parents=True, exist_ok=True)
    added = new_files()
    for rel in paths:
        rel = Path(rel).as_posix()
        if rel in tracked():
            continue
        src = SRC / rel
        if src.exists():
            # Untracked files are never touched by a patch, so the tree copy is the original.
            dst = PRISTINE / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"tracking {rel}")
        else:
            added.add(rel)
            print(f"tracking new file {rel}")
    NEW_LIST.write_text("\n".join(sorted(added)) + "\n")


def git_apply(patch, cwd):
    # Git for Windows ships core.autocrlf=true, which would turn every patched file into CRLF.
    subprocess.run(["git", "-c", "core.autocrlf=false", "apply", "--whitespace=nowarn", str(patch)],
                   cwd=cwd, check=True)


def staged_tree():
    """Temp dir holding tracked files with all saved patches applied."""
    tmp = Path(tempfile.mkdtemp(prefix="ifox-stage-", dir=TREE))
    for rel in tracked():
        p = PRISTINE / rel
        if p.exists():
            (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, tmp / rel)
    for patch in patch_list():
        git_apply(patch, tmp)
    return tmp


def file_diff(rel, old, new):
    a = old.splitlines(keepends=True) if old is not None else []
    b = new.splitlines(keepends=True) if new is not None else []
    out = [f"diff --git a/{rel} b/{rel}\n"]
    if old is None:
        out.append("new file mode 100644\n")
    if new is None:
        out.append("deleted file mode 100644\n")
    body = difflib.unified_diff(a, b, "/dev/null" if old is None else f"a/{rel}",
                                "/dev/null" if new is None else f"b/{rel}", n=3)
    for line in body:
        out.append(line)
        if not line.endswith("\n"):
            out.append("\n\\ No newline at end of file\n")
    return "".join(out)


def changes():
    tmp = staged_tree()
    try:
        diffs = []
        for rel in tracked():
            old, new = read(tmp / rel), read(SRC / rel)
            if old != new:
                diffs.append((rel, file_diff(rel, old, new)))
        return diffs
    finally:
        shutil.rmtree(tmp)


def cmd_status():
    for rel, _ in changes():
        print(f"changed {rel}")


def cmd_save(name):
    diffs = changes()
    if not diffs:
        sys.exit("nothing changed since the last saved patch")
    PATCHES.mkdir(exist_ok=True)
    out = PATCHES / f"{name}.patch"
    if out.exists():
        sys.exit(f"{out.name} already exists")
    out.write_bytes("".join(d for _, d in diffs).encode("utf-8", "surrogateescape"))
    print(f"wrote {out.name}: {len(diffs)} files")


def patch_files(patch):
    return [line.split(" b/", 1)[1].strip() for line in patch.read_text(encoding="utf-8").splitlines()
            if line.startswith("diff --git ")]


def cmd_redo(name):
    """Rebuild one patch from the originals, after fixing its files in the tree.

    Only safe when no other patch touches the same files, which is checked.
    """
    target = PATCHES / f"{name}.patch"
    if not target.exists():
        sys.exit(f"{target.name} not found")
    files = patch_files(target)
    for other in PATCHES.glob("*.patch"):
        if other != target and set(patch_files(other)) & set(files):
            sys.exit(f"{other.name} also touches {sorted(set(patch_files(other)) & set(files))}")
    diffs = [file_diff(rel, read(PRISTINE / rel), read(SRC / rel)) for rel in files]
    target.write_bytes("".join(diffs).encode("utf-8", "surrogateescape"))
    print(f"rebuilt {target.name}: {len(files)} files")


def cmd_init():
    """Record the originals of every file the patches touch, for a freshly unpacked tree."""
    if tracked():
        sys.exit(f"{PRISTINE} already holds originals")
    PRISTINE.mkdir(parents=True, exist_ok=True)
    added = set()
    for patch in patch_list():
        lines = patch.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not line.startswith("diff --git "):
                continue
            rel = line.split(" b/", 1)[1].strip()
            if i + 1 < len(lines) and lines[i + 1].startswith("new file mode"):
                added.add(rel)
            elif not (PRISTINE / rel).exists():
                (PRISTINE / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(SRC / rel, PRISTINE / rel)
    NEW_LIST.write_text("\n".join(sorted(added)) + "\n")
    print(f"recorded {len(tracked()) - len(added)} originals, {len(added)} new files")


def cmd_apply():
    added = new_files()
    for rel in tracked():
        dst = SRC / rel
        if rel in added:
            dst.unlink(missing_ok=True)
        else:
            shutil.copy2(PRISTINE / rel, dst)
    patches = patch_list()
    for p in patches:
        print(f"applying {p.relative_to(PATCHES).as_posix()}")
        git_apply(p, SRC)
    print(f"{len(patches)} patches applied")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "edit" and args:
        cmd_edit(args)
    elif cmd == "status":
        cmd_status()
    elif cmd == "save" and len(args) == 1:
        cmd_save(args[0])
    elif cmd == "redo" and len(args) == 1:
        cmd_redo(args[0])
    elif cmd == "init":
        cmd_init()
    elif cmd == "apply":
        cmd_apply()
    else:
        sys.exit(__doc__)
