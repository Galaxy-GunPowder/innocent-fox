"""Write the mozconfig and run mach inside MozillaBuild's shell.

  python scripts/build.py              full build (about 2 hours the first time)
  python scripts/build.py build binaries   rebuild after editing C++ only (minutes)
  python scripts/build.py package      make a zip in D:\\ifox\\obj\\dist
  python scripts/build.py run          start the built browser
"""
import os
import subprocess
import sys
from pathlib import Path

from common import MOZILLABUILD, OBJ, SRC

# 8 jobs: 12 threads would run 16 GB RAM out while Rust crates and libxul link.
JOBS = 8

# PGO (build, train on real pages, build again) and LTO, like official Firefox. Pages run faster;
# nothing a page reads changes. IFOX_FAST=1 skips both for quick dev rebuilds.
# LTO is C++ only ("thin"): "cross" also feeds Rust in, which needs rustc's LLVM to match
# clang's. Rust 1.100 is LLVM 23 and the bootstrapped clang is 22, so the link failed
# ("Not an int attribute", 2026-11-25).
PGO = "" if os.environ.get("IFOX_FAST") else "ac_add_options MOZ_PGO=1\nac_add_options --enable-lto=thin\n"

MOZCONFIG = f"""\
ac_add_options --enable-application=browser
mk_add_options MOZ_OBJDIR={OBJ.as_posix()}
mk_add_options MOZ_PARALLEL_BUILD={JOBS}

# Match a real release build, so feature detection sees stock Firefox.
ac_add_options --enable-release
ac_add_options --enable-optimize
ac_add_options --disable-debug
{PGO}ac_add_options --enable-update-channel=release

# Download clang, rust, nasm, node, the Windows SDK into ~/.mozbuild.
ac_add_options --enable-bootstrap

# Parts we never ship: they phone home or only slow the build.
ac_add_options --disable-tests
ac_add_options --disable-crashreporter
ac_add_options --disable-updater
ac_add_options --disable-maintenance-service
ac_add_options --disable-default-browser-agent
"""


def mach(*args):
    (SRC / "mozconfig").write_text(MOZCONFIG, newline="\n")
    env = dict(os.environ)
    env.update(
        MOZILLABUILD=str(MOZILLABUILD) + "\\",
        MSYSTEM="MSYS",
        MSYS2_PATH_TYPE="inherit",
        CHERE_INVOKING="1",
        MOZBUILD_STATE_PATH=str(Path.home() / ".mozbuild"),
    )
    for k in ("INCLUDE", "LIB", "CYGWIN", "GITDIR"):
        env.pop(k, None)
    # rustup (installed by `mach bootstrap`) puts rustc here; a running shell won't have it on PATH yet.
    env["PATH"] = str(Path.home() / ".cargo" / "bin") + os.pathsep + env.get("PATH", "")
    bash = MOZILLABUILD / "msys2" / "usr" / "bin" / "bash.exe"
    cmd = "./mach --no-interactive " + " ".join(args)
    return subprocess.run([str(bash), "-l", "-c", cmd], cwd=SRC, env=env).returncode


if __name__ == "__main__":
    sys.exit(mach(*(sys.argv[1:] or ["build"])))
