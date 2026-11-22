"""Saved browser profiles: make one, read it, change it, wipe its history.

    from ifox import profile
    p = profile.create("shop1", proxy="https://user:pass@us.decodo.com:10001")
    p.update(langs=["pt-BR", "pt", "en"])
    p.wipe_history()     # cookies, logins, history, cache gone; settings and device kept

A profile is a folder: Firefox's own files plus ifox-profile.json (the settings).
The proxy login is kept in that file in plain text; the browser itself never reads it.
"""
import copy
import json
import os
import random
import re
import shutil
import sqlite3
import tempfile
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from . import fingerprint as fp
from . import versions
from .install import HOME
from .network import Proxy, parse

_DEV = Path(r"D:\ifox\obj\dist\bin\firefox.exe")
ROOT = Path(os.environ.get("IFOX_PROFILES") or
            (_DEV.parents[3] / "profiles" if _DEV.exists() else HOME / "profiles"))
FILE = "ifox-profile.json"
SESSIONS = "ifox-sessions.json"     # history: wipe_history removes it

# Every setting and its default.
DEFAULTS = {
    "proxy": None, "timezone": "auto", "langs": "auto",
    "device": None, "cores": None, "screen": None, "dpr": None, "gpu": None, "touch": None,
    "gpu_mode": "fake", "seed": None, "version": None, "prefs": {},
}
HELP = {
    "proxy": "proxy URL; None = this computer's own connection",
    "timezone": '"auto" = the proxy exit\'s, looked up every start (no proxy: this computer\'s); or "America/Chicago"',
    "langs": '"auto" = the exit country\'s, fixed at the first start; or ["pt-BR", "pt", "en"]',
    "device": "a name from profile.DEVICES; None = random. Sets cores, screen, dpr and gpu from one real machine",
    "cores": "CPU threads pages see (default: the device's)",
    "screen": "(width, height) in device pixels (default: the device's)",
    "dpr": "display scale: 1.0, 1.25, 1.5 (default: the device's)",
    "gpu": "(vendor, renderer) that WebGL reports (default: the device's)",
    "touch": "touch points; 0 = no touch screen",
    "gpu_mode": '"fake" = claim the device\'s GPU, with WebGL noise; "real" = this computer\'s GPU',
    "seed": "canvas noise key; None = random once, then kept",
    "version": "Firefox version pages see, one of profile.VERSIONS (\"160\", \"159\", \"158\"); "
               "None = picked at random when the profile is made, then kept",
    "prefs": "extra Firefox prefs, {name: value}",
}
DEVICES = [d["name"] for d in fp.DEVICES]
VERSIONS = versions.available()       # the build's own and the lab-verified ones, newest first


def _pick_version(s):
    """A version for a new profile that names none: one of VERSIONS at random, kept from then on.
    Profiles saved before versions existed keep None, the build's own, so pages never see one change."""
    if s.get("version") is None:
        s["version"] = random.SystemRandom().choice(VERSIONS)
    return s

# Built in, always there: a new random device, screen, scale and canvas seed every use,
# this computer's real GPU, nothing kept after the browser closes.
DEFAULT = "default"
_DEFAULT_SETTINGS = {"gpu_mode": "real"}
_DEVICE_KEYS = ("device", "cores", "screen", "dpr", "gpu", "touch", "gpu_mode", "seed")


class ProfileError(RuntimeError):
    pass


def _check(settings):
    bad = set(settings) - set(DEFAULTS)
    if bad:
        raise TypeError(f"unknown setting {', '.join(sorted(bad))}; settings are: {', '.join(DEFAULTS)}")
    out = dict(settings)
    if out.get("device") is not None and out["device"] not in DEVICES:
        raise ValueError(f"device must be one of {DEVICES}")
    if out.get("version") is not None:
        out["version"] = versions.major(out["version"])
        if out["version"] not in VERSIONS:
            raise ValueError(f"version must be one of {VERSIONS}")
    if out.get("gpu_mode", "fake") not in ("fake", "real"):
        raise ValueError('gpu_mode must be "fake" or "real"')
    langs = out.get("langs", "auto")
    if langs != "auto" and (isinstance(langs, str) or not all(isinstance(x, str) for x in langs)):
        raise ValueError('langs must be "auto" or a list like ["en-US", "en"]')
    if langs != "auto":
        out["langs"] = list(langs)
    for k in ("screen", "gpu"):
        if out.get(k) is not None:
            out[k] = tuple(out[k])
            if len(out[k]) != 2:
                raise ValueError(f"{k} takes two values")
    if isinstance(out.get("proxy"), Proxy):
        out["proxy"] = out["proxy"].url()
    elif out.get("proxy"):
        parse(out["proxy"])                       # fails early on a bad proxy
    return out


def _build(s, old=None):
    """The fingerprint for settings s; an unset device or seed keeps the old one."""
    device = s["device"] or (old.device if old else None)
    seed = s["seed"] if s["seed"] is not None else (old.seed if old else None)
    f = fp.make(device=device, seed=seed, gpu_mode=s["gpu_mode"])
    for k in ("cores", "dpr", "screen", "gpu"):
        if s[k] is not None:
            setattr(f, k, s[k])
    if s["touch"] is not None:
        f.extra["touch"] = s["touch"]
    if s["langs"] != "auto":
        f.langs = list(s["langs"])
    elif old:
        f.langs = old.langs
    f.tz = "" if s["timezone"] == "auto" else s["timezone"]     # "" = this computer's clock
    return f


class Profile:
    """One profile. Read: p.name, p.folder, p.settings, p.fingerprint."""

    def __init__(self, name, folder, settings, fingerprint, temp=False):
        self.name, self.folder, self.settings, self.fingerprint = name, Path(folder), settings, fingerprint
        self.temp = temp          # throwaway (deleted when its browser closes) or a run-only copy
        self._saves = not temp

    @property
    def is_default(self):
        return self.temp and self.name == DEFAULT

    def _not_default(self, what):
        if self.temp:
            raise ProfileError(f"{self.name} keeps nothing, so there is nothing to {what}; "
                               "it is new every use and deleted when its browser closes")

    def __repr__(self):
        f = self.fingerprint
        return f"<Profile {self.name}: {f.device}, {f.screen[0]}x{f.screen[1]} @{f.dpr}, {self.settings['timezone']}>"

    def details(self):
        """Everything about this profile as a dict: settings, the values pages
        will see, and what is stored. The proxy login is never included."""
        f, s = self.fingerprint, self.settings
        x = parse(s["proxy"]) if s["proxy"] else None
        open_now = self.in_use()          # first: it clears a stale lock file
        files = [q for q in self.folder.rglob("*") if q.is_file() and q.name != FILE] if self.folder.exists() else []
        own = lambda k: "set" if s[k] is not None else "device"          # noqa: E731
        return {
            "name": self.name,
            "folder": str(self.folder),
            "saved": ("no: built in, new random device, seed and version every use, nothing kept"
                      if self.is_default else self._saves and (self.folder / FILE).exists()),
            "proxy": f"{x.scheme}://{x.host}:{x.port}" + ((" (login saved)" if self._saves else " (with login)") if x.user else "") if x else None,
            "timezone": "auto (the proxy exit's, every start)" if s["timezone"] == "auto" else s["timezone"],
            "langs": "auto (the exit country's, at first start)" if s["langs"] == "auto" else f.langs,
            "device": f.device,
            "cores": f"{f.cores} ({own('cores')})",
            "screen": f"{f.screen[0]}x{f.screen[1]} device px, pages see "
                      f"{round(f.screen[0] / f.dpr)}x{round(f.screen[1] / f.dpr)} ({own('screen')})",
            "dpr": f"{f.dpr} ({own('dpr')})",
            "gpu": f"{f.gpu[0]} | {f.gpu[1]} ({own('gpu')})" if f.gpu_mode == "fake" else "this computer's (real)",
            "touch": f.extra.get("touch", 0),
            "gpu_mode": f.gpu_mode,
            "seed": f.seed,
            "version": f"Firefox {s['version'] or versions.table()['base']}"
                       + (" (picked at random)" if self.is_default else ""),
            "user_agent": f.user_agent,
            "prefs": s["prefs"],
            "open_now": open_now,
            **self._history(files),
        }

    def _history(self, files):
        runs = self.sessions()
        countries = Counter(r.get("country") or "no lookup" for r in runs)
        last = runs[-1] if runs else None
        sites, cookies = self.sites(), self.cookie_sites()
        more = lambda xs, n=5: ", ".join(xs[:n]) + (f" (+{len(xs) - n} more)" if len(xs) > n else "")  # noqa: E731
        return {
            "history": f"{len(files)} files, {sum(q.stat().st_size for q in files if q.exists()) / 1e6:.1f} MB"
                       if files else "empty",
            "sessions": len(runs),
            "last_session": (f"{last['start']} to {last['end'] or 'now'}, {last['proxy']}"
                             + (f", exit {last['country']} {last.get('city', '')} {last.get('ip', '')}".rstrip()
                                if last.get("country") else "")
                             if last else None),
            "countries": ", ".join(f"{c} x{n}" for c, n in countries.most_common()) or None,
            "proxies_used": ", ".join(dict.fromkeys(r["proxy"] for r in runs)) or None,
            "sites": f"{len(sites)}: {more(sites)}" if sites else 0,
            "cookie_sites": f"{len(cookies)}: {more(cookies)}" if cookies else 0,
        }

    # Sessions and history (all removed by wipe_history)

    def log_session(self, entry):
        """Called by Browser at start: which proxy and exit this run used. Returns its index."""
        log = self.sessions()
        log.append(entry)
        self._write_sessions(log)
        return len(log) - 1

    def end_session(self, index, when):
        log = self.sessions()
        if 0 <= index < len(log):
            log[index]["end"] = when
            self._write_sessions(log)

    def _write_sessions(self, log):
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / SESSIONS).write_text(json.dumps(log, indent=1), encoding="utf-8")

    def sessions(self):
        """Every browser run: start, end, proxy, exit ip/country/city, clock, langs."""
        try:
            return json.loads((self.folder / SESSIONS).read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return []

    def _query(self, db, sql):
        """Read one of Firefox's databases, from a copy (works while the browser is open)."""
        src = self.folder / db
        if not src.exists():
            return []
        with tempfile.TemporaryDirectory() as tmp:
            for ext in ("", "-wal"):
                if Path(str(src) + ext).exists():
                    shutil.copy2(str(src) + ext, Path(tmp) / (db + ext))
            con = sqlite3.connect(Path(tmp) / db)
            try:
                return con.execute(sql).fetchall()
            except sqlite3.Error:
                return []
            finally:
                con.close()

    def visits(self, limit=50):
        """Pages visited, newest first: (time, url, title)."""
        rows = self._query("places.sqlite", "SELECT last_visit_date, url, title FROM moz_places "
                           f"WHERE visit_count > 0 AND last_visit_date IS NOT NULL ORDER BY last_visit_date DESC LIMIT {int(limit)}")
        return [(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t / 1e6)), u, ti or "") for t, u, ti in rows]

    def sites(self):
        """Sites visited, newest first."""
        rows = self._query("places.sqlite", "SELECT url FROM moz_places WHERE visit_count > 0 "
                                            "AND last_visit_date IS NOT NULL ORDER BY last_visit_date DESC")
        return list(dict.fromkeys(h for (u,) in rows if (h := urlsplit(u).hostname)))

    def cookie_sites(self):
        """Sites holding cookies in this profile."""
        rows = self._query("cookies.sqlite", "SELECT DISTINCT host FROM moz_cookies")
        return sorted({h.lstrip(".") for (h,) in rows})

    def __str__(self):
        return "\n".join(f"  {k:11} {v}" for k, v in self.details().items())

    def save(self):
        if self._saves:
            self.folder.mkdir(parents=True, exist_ok=True)
            data = {"settings": self.settings, "fingerprint": asdict(self.fingerprint)}
            (self.folder / FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def update(self, **changes):
        """Change settings and save them. Device values are rebuilt; cookies stay."""
        changes = _check(changes)
        self.settings = {**self.settings, **changes}
        if any(k in changes for k in _DEVICE_KEYS) or "langs" in changes or "timezone" in changes:
            self.fingerprint = _build(self.settings, self.fingerprint)
        self.save()
        return self

    def for_run(self, **changes):
        """A copy with changes for one run; the saved profile stays as it is."""
        if not changes:
            return self
        p = copy.deepcopy(self)
        p._saves = False
        p.settings = {**p.settings, **_check(changes)}
        p.fingerprint = _build(p.settings, p.fingerprint)
        return p

    def in_use(self):
        """True while a browser has this profile open."""
        lock = self.folder / "parent.lock"
        try:
            lock.unlink()               # a running Firefox holds it; a stale one just goes
            return False
        except FileNotFoundError:
            return False
        except PermissionError:
            return True

    def wipe_history(self):
        """A fresh browser with the same settings and device: cookies, logins,
        history, cache, site storage and Firefox's own prefs all deleted.
        Returns the profile, so print() shows the result."""
        self._not_default("wipe")
        if self.in_use():
            raise ProfileError(f"{self.name} is open in a browser; close it first")
        for item in self.folder.iterdir():
            if item.name != FILE:
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        return self

    def delete(self):
        """The whole folder, settings included. Returns what was deleted."""
        self._not_default("delete")
        if self.in_use():
            raise ProfileError(f"{self.name} is open in a browser; close it first")
        last = self.details()
        shutil.rmtree(self.folder, ignore_errors=True)
        return {"deleted": self.name, "folder": last["folder"], "history": last["history"],
                "exists_now": (self.folder / FILE).exists()}


def _folder(name):
    if not re.fullmatch(r"[\w.-]+", name) or name.startswith((".", "_")):
        raise ValueError(f"profile name {name!r}: letters, digits, _ . - only")
    return ROOT / name


def exists(name):
    return name == DEFAULT or (_folder(name) / FILE).exists()


def names():
    """Saved profiles, after the built-in "default"."""
    saved = sorted(d.name for d in ROOT.iterdir() if (d / FILE).exists()) if ROOT.exists() else []
    return [DEFAULT] + [n for n in saved if n != DEFAULT]


def create(name, *, overwrite=False, **settings):
    """A new saved profile. Settings not given take their defaults (see HELP)."""
    if name == DEFAULT:
        raise ProfileError(f'"{DEFAULT}" is built in and always there; pick another name to save one')
    folder = _folder(name)
    if (folder / FILE).exists():
        if not overwrite:
            raise ProfileError(f"profile {name} exists; profile.load({name!r}), or overwrite=True")
        load(name).delete()
    s = _pick_version({**copy.deepcopy(DEFAULTS), **_check(settings)})
    p = Profile(name, folder, s, _build(s))
    p.save()
    return p


def load(name):
    if name == DEFAULT:
        return default()
    folder = _folder(name)
    try:
        data = json.loads((folder / FILE).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ProfileError(f"no profile {name} in {ROOT}; profile.create({name!r}) makes one") from None
    if "fingerprint" not in data:          # first format: the fingerprint alone
        data = {"fingerprint": data, "settings": {"device": data["device"], "seed": data["seed"],
                                                  "langs": data["langs"], "gpu_mode": data.get("gpu_mode", "fake")}}
    d = data["fingerprint"]
    f = fp.Profile(**{**d, "screen": tuple(d["screen"]), "gpu": tuple(d["gpu"])})
    return Profile(name, folder, {**copy.deepcopy(DEFAULTS), **data["settings"]}, f)


def get(name, **settings):
    """load(name), or create(name, **settings) the first time."""
    if name == DEFAULT:
        return default(**settings)
    return load(name) if exists(name) else create(name, **settings)


def delete(name):
    """Returns what was deleted."""
    return load(name).delete()


def default(**settings):
    """The built-in profile, new every call: a random device (cores, screen, scale),
    a random canvas seed, this computer's real GPU, the clock and languages of the
    proxy exit. Nothing is kept; its folder is deleted when its browser closes.
    Settings given here (proxy, timezone, device, ...) apply to this one use."""
    s = _pick_version({**copy.deepcopy(DEFAULTS), **_DEFAULT_SETTINGS, **_check(settings)})
    folder = ROOT / "_tmp" / os.urandom(6).hex()
    return Profile(DEFAULT, folder, s, _build(s), temp=True)


temporary = default      # older name
