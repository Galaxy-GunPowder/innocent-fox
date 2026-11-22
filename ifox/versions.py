"""Show pages an older Firefox than the one running: one build, several versions.

versions.json holds, per version, the prefs that make this build look like it to
a website: the user agent, features switched off, and Innocent Fox's version
switch (ifox.compat.*). It is measured, not guessed: tests/identity/versions.py
compares official Firefox releases and writes it.
"""
import json
from pathlib import Path

DATA = Path(__file__).with_name("versions.json")


def table():
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except OSError:
        return {"base": "160", "versions": {}}


def available():
    """Versions a profile can show, newest first: the build's own, then those the lab verified
    (0 differences from the official release, tests/identity/compare.py --assemble ours)."""
    t = table()
    ok = [v for v, e in t["versions"].items() if (e.get("verified") or {}).get("passed")]
    return [t["base"], *sorted(ok, key=int, reverse=True)]


def major(version):
    return str(version).split(".")[0]


def prefs(version, build_version):
    """Prefs that make a build of build_version show as version; {} for its own version."""
    want, have, t = major(version), major(build_version), table()
    if want == have:
        return {}
    if have != t["base"]:
        raise ValueError(f"the version switch is made for a Firefox {t['base']} build; this one is {have}")
    if want not in available():
        raise ValueError(f"version must be one of {available()}, not {version!r}")
    return dict(t["versions"][want]["prefs"])


def merge(base, extra):
    """Version prefs on top of profile prefs; hidden WebGL extension lists are joined."""
    out = {**base, **extra}
    key = "ifox.webgl.hiddenExtensions"
    if base.get(key) and extra.get(key):
        out[key] = ",".join(dict.fromkeys(base[key].split(",") + extra[key].split(",")))
    return out
