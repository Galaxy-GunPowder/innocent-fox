"""Browser, Tab and Frame: drive Innocent Fox from Python over the private pipe.

    from ifox import Browser
    with Browser("alice", proxy="https://user:pass@us.decodo.com:10001") as b:
        tab = b.open("https://example.com/signup")
        tab.type("#email", "a@example.com")
        tab.click("text=Create account")

Selectors: CSS, text=Sign up, text="Exact text", and "a >> b" to step into
an iframe or shadow root. Every call waits for its element; nothing to switch.
"""
import atexit
import base64
import itertools
import json
import os
import random
import shutil
import subprocess
import threading
import time
import weakref
from pathlib import Path

from . import fingerprint as fp
from . import human
from .network import agent_args, proxy_prefs
from .pipe import PipePair
from . import profile as pf
from . import install
from .install import INSTALLED
from .winjob import Job

# Where the browser and the saved profiles live: the env vars if set, else the
# dev build on the build machine, else %LOCALAPPDATA%, downloaded there on first use.
_DEV = Path(r"D:\ifox\obj\dist\bin\firefox.exe")
BROWSER = Path(os.environ.get("IFOX_BROWSER") or (_DEV if _DEV.exists() else INSTALLED))
PROFILES = pf.ROOT

# Profile housekeeping only: none of these change what a page can see.
QUIET = {
    "browser.shell.checkDefaultBrowser": False,
    "browser.aboutwelcome.enabled": False,
    "browser.startup.homepage_override.mstone": "ignore",
    "browser.startup.page": 0,
    "datareporting.policy.dataSubmissionEnabled": False,
    "toolkit.telemetry.reportingpolicy.firstRun": False,
    # Background calls no page can see. Stock Firefox makes 33 on an idle blank
    # tab (ads, weather, region lookup, update checks). Off here.
    # Kept on purpose, because pages can tell: media plug-ins (OpenH264,
    # Widevine), push, Safe Browsing, tracker lists, remote settings.
    "browser.startup.homepage": "about:blank",
    "browser.newtabpage.enabled": False,
    "browser.newtabpage.activity-stream.feeds.topsites": False,
    "browser.newtabpage.activity-stream.showSponsored": False,
    "browser.newtabpage.activity-stream.showSponsoredTopSites": False,
    "browser.newtabpage.activity-stream.feeds.section.topstories": False,
    "browser.newtabpage.activity-stream.discoverystream.enabled": False,
    "browser.newtabpage.activity-stream.showWeather": False,
    "browser.newtabpage.activity-stream.system.showWeather": False,
    "browser.newtabpage.activity-stream.telemetry": False,
    "browser.topsites.contile.enabled": False,
    "browser.urlbar.quicksuggest.enabled": False,
    "browser.urlbar.suggest.quicksuggest.sponsored": False,
    "browser.urlbar.suggest.quicksuggest.nonsponsored": False,
    "browser.search.suggest.enabled": False,
    "browser.urlbar.speculativeConnect.enabled": False,
    "browser.places.speculativeConnect.enabled": False,
    "browser.region.update.enabled": False,         # IP-based region lookup
    "browser.region.network.url": "",
    "network.captive-portal-service.enabled": False,
    "network.connectivity-service.enabled": False,  # example.org, ipv4only.arpa
    "network.trr.mode": 5,                           # no DoH probes; DNS as before
    "app.update.auto": False,
    "extensions.update.enabled": False,
    "extensions.systemAddon.update.enabled": False,
    "extensions.getAddons.cache.enabled": False,
    "extensions.htmlaboutaddons.recommendations.enabled": False,
    "app.normandy.enabled": False,                   # studies can change prefs
    "app.shield.optoutstudies.enabled": False,
    "messaging-system.rsexperimentloader.enabled": False,
    "datareporting.healthreport.uploadEnabled": False,
    "toolkit.telemetry.enabled": False,
    "browser.discovery.enabled": False,
    "browser.tabs.crashReporting.sendReport": False,
}

# A driven window is often behind other windows. Firefox then reports the page
# hidden and unfocused, and a page that gets typing while hidden and unfocused
# has no real user. These stock prefs make it behave as the front window.
FRONT = {
    "focusmanager.testmode": True,
    "widget.windows.window_occlusion_tracking.enabled": False,
}


class IfoxError(RuntimeError):
    pass


class LoadError(IfoxError):
    """A page that did not load (Firefox showed its error page)."""

    def __init__(self, name, url):
        super().__init__(f"{url}: {name}")
        self.name, self.url = name, url


# Firefox network error codes (xpcom/base/ErrorList.py, module NETWORK).
LOAD_ERRORS = {
    0x804B000D: "connection refused",
    0x804B000E: "timed out",
    0x804B0010: "offline",
    0x804B0014: "connection reset",
    0x804B001E: "host not found",
    0x804B002A: "proxy host not found",
    0x804B0047: "connection interrupted",
    0x804B0048: "proxy refused the connection",
}
ABORTED = 0x804B0002  # replaced by another navigation (a redirect): not an error


def _loaded(reply, url):
    status = (reply or {}).get("status", 0) & 0xFFFFFFFF
    if status and status != ABORTED:
        raise LoadError(LOAD_ERRORS.get(status, f"error 0x{status:08X}"), url)
    return reply


def _user_js(prefs):
    return "".join(f"user_pref({json.dumps(k)}, {json.dumps(v)});\n" for k, v in prefs.items())


_open = weakref.WeakSet()


@atexit.register
def _close_all():
    """A script that never called close() still quits its browsers cleanly."""
    for b in list(_open):
        b.close()


class Browser:
    def __init__(self, profile=None, *, stock=False, hidden=False, front=True, headless=False,
                 timeout=60, match_exit=True, binary=BROWSER, args=(), place=None, **settings):
        """profile: a saved profile's name or a profile.Profile; None or "default" =
            the built-in default (random device and seed every use, real GPU, deleted on close).
        settings: any of profile.DEFAULTS (proxy, timezone, langs, device, cores, ...).
            No profile: they set this browser. A name not made yet: the profile is
            created with them. An existing profile: they apply to this run only.

        Run options (never saved):
        stock: no fingerprint changes at all, exactly Firefox 160 on this machine.
        hidden: window on a hidden desktop. headless: no window at all.
        front: act as the front window even when covered (for driving). A browser
            a person uses by hand passes False and keeps stock focus behaviour.
        match_exit: with a proxy, ask where traffic leaves (through the proxy, no
            page opened). b.exit holds the answer (ip, country, city, timezone).
        args: extra command-line flags.

        The browser ends with this Python process, however it ends."""
        if Path(binary) == INSTALLED:
            try:
                binary = install.ensure()          # downloads the browser the first time
            except RuntimeError as e:
                raise IfoxError(str(e)) from None
        elif not Path(binary).exists():
            raise IfoxError(f"Innocent Fox not found at {binary} (set IFOX_BROWSER, or leave binary out)")
        if place:      # older form: languages, and the clock when there is no proxy
            settings.setdefault("langs", fp.PLACES[place]["langs"])
            if not settings.get("proxy"):
                settings.setdefault("timezone", fp.PLACES[place]["tz"])
        if isinstance(profile, pf.Profile) and profile.temp:
            p = pf.default(**{**profile.settings, **settings})     # new random device every use
        elif isinstance(profile, pf.Profile):
            p = profile.for_run(**settings)
        elif profile is None or profile == pf.DEFAULT:
            p = pf.default(**settings)
        elif isinstance(profile, str):
            p = pf.load(profile).for_run(**settings) if pf.exists(profile) else pf.create(profile, **settings)
        else:
            raise TypeError("profile is a name, a profile.Profile, or None")
        self.profile, self.folder, self._closed = p, p.folder, False
        self.stock = stock
        self.folder.mkdir(parents=True, exist_ok=True)
        s = p.settings
        proxy = s["proxy"]
        self.timezone = s["timezone"] if s["timezone"] != "auto" else ""
        self.langs = p.fingerprint.langs
        fingerprint = None if stock else p.fingerprint
        all_prefs = {**QUIET, **(FRONT if front else {}), **(fp.prefs(fingerprint, hidden) if fingerprint else {}),
                     **(proxy_prefs(proxy) if proxy else {}), **s["prefs"]}
        # Rewritten on every start, so a pref changed in the code reaches old profiles too.
        (self.folder / "user.js").write_text(_user_js(all_prefs), encoding="utf-8")

        self._ids = itertools.count(1)
        self._waiting = {}
        self._lock = threading.Lock()
        self._mouse = None
        self.rng = random.Random()
        self.pipe = PipePair()
        self.job = Job()
        # -wait-for-browser: stock flag that keeps firefox.exe running until the
        # browser quits, instead of handing off to a second process and exiting.
        self.binary = Path(binary)
        self.proc = self.job.start([str(binary), "-wait-for-browser", "-no-remote", "-profile", str(self.folder),
                                    "-ifox-pipe", self.pipe.name, *(["-headless"] if headless else []), *args])
        _open.add(self)
        try:
            self._start(proxy, match_exit and not stock, timeout)
        except BaseException:
            self.close()
            raise

    def _start(self, proxy, match_exit, timeout):
        connect = threading.Thread(target=self.pipe.connect, daemon=True)
        connect.start()
        connect.join(timeout)
        if connect.is_alive():
            raise IfoxError(f"the browser never opened the pipe within {timeout} s; is {self.binary} an Innocent Fox build?")
        self._reading = threading.Thread(target=self._reader, daemon=True)
        self._reading.start()
        hello = self.call("hello", _wait=timeout)
        if proxy and agent_args(proxy):
            self.call("proxy", **agent_args(proxy))
        self.exit = None
        p = self.profile
        if proxy and match_exit:
            try:
                self.exit = self.call("exitinfo", _wait=60)
            except IfoxError as e:
                raise IfoxError(f"no internet through the proxy ({e})") from None
            if p.settings["timezone"] == "auto" and self.exit.get("timezone"):
                self.timezone = self.exit["timezone"]
                self.set_prefs(**{"ifox.timezone": self.timezone})
            if p.settings["langs"] == "auto" and self.exit.get("country"):
                self.langs = fp.langs_for(self.exit["country"])
                self.set_prefs(**{"intl.accept_languages": ", ".join(self.langs)})
                p.settings["langs"] = p.fingerprint.langs = self.langs      # fixed from now on
                p.save()
        x = pf.parse(proxy) if isinstance(proxy, str) else proxy
        self._session = p.log_session({
            "start": time.strftime("%Y-%m-%d %H:%M:%S"), "end": None,
            "proxy": f"{x.scheme}://{x.host}:{x.port}" if x else "none (this computer's connection)",
            **({k: self.exit.get(k) for k in ("ip", "country", "region", "city", "timezone", "org")}
               if self.exit else {}),
            "clock": self.timezone or "this computer's", "langs": self.langs,
        })
        self.version = hello["version"]
        self.tab = Tab(self, hello["tab"])
        self._fresh = True  # the start tab is still blank and unused

    # Plumbing

    def _reader(self):
        buf = b""
        while True:
            chunk = self.pipe.read()
            if not chunk:
                break
            buf += chunk
            *lines, buf = buf.split(b"\n")
            for line in lines:
                msg = json.loads(line)
                slot = self._waiting.pop(msg.get("id"), None)
                if slot:
                    slot[1].append(msg)
                    slot[0].set()
        for done, box in list(self._waiting.values()):
            box.append({"ok": False, "error": "browser closed"})
            done.set()

    def call(self, verb, _wait=120, **args):
        msg_id = next(self._ids)
        done, box = threading.Event(), []
        self._waiting[msg_id] = (done, box)
        line = json.dumps({"id": msg_id, "do": verb, "args": args}).encode() + b"\n"
        with self._lock:
            self.pipe.write(line)
        if not done.wait(_wait):
            self._waiting.pop(msg_id, None)
            raise IfoxError(f"{verb}: no answer after {_wait} s")
        reply = box[0]
        if not reply["ok"]:
            raise IfoxError(f"{verb}: {reply['error']}")
        return reply["value"]

    # Tabs

    def open(self, url="about:blank", timeout=30):
        """A page in a new tab (the blank start tab is used first)."""
        if self._fresh:
            self._fresh = False
            if url != "about:blank":
                self.tab.goto(url, timeout)
            return self.tab
        r = self.call("open", _wait=timeout + 5, url=url, timeout=int(timeout * 1000))
        _loaded(r, url)
        return Tab(self, r["tab"])

    def tabs(self):
        return [Tab(self, t["tab"]) for t in self.call("tabs")]

    def set_prefs(self, **prefs):
        """Change prefs live, e.g. set_prefs(**{"ifox.hardwareConcurrency": 8})."""
        self.call("prefs", set=prefs)

    # Input

    def move(self, x, y, tab=None, width=20):
        if self._mouse is None:
            self._mouse = (x + self.rng.uniform(-300, 300), y + self.rng.uniform(-200, 200))
        for px, py, gap in human.path(self._mouse, (x, y), width, self.rng):
            time.sleep(gap)
            self.call("mouse", tab=tab, type="move", x=px, y=py)
        self._mouse = (x, y)

    # Lifetime

    def wait_closed(self):
        """Block until the browser quits (a person closed the last window)."""
        self._reading.join()

    def close(self):
        """Quit cleanly (the profile saves cookies and history), then make sure
        nothing is left: every process the browser started ends with it."""
        if self._closed:
            return
        self._closed = True
        _open.discard(self)
        if getattr(self, "_session", None) is not None and not self.profile.temp:
            self.profile.end_session(self._session, time.strftime("%Y-%m-%d %H:%M:%S"))
        try:
            reading = getattr(self, "_reading", None)
            if reading and reading.is_alive():
                self.call("quit", _wait=5)
            self.proc.wait(15)
        except Exception:
            pass
        self.job.kill()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            pass
        self.job.close()
        self.pipe.close()
        if self.profile.temp:
            shutil.rmtree(self.folder, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class Tab:
    """A tab. Stays valid across navigations; every call names this tab."""

    def __init__(self, browser, tab_id, prefix=None):
        self.b, self.id, self.prefix = browser, tab_id, prefix

    def __repr__(self):
        return f"<Tab {self.id}{' ' + self.prefix if self.prefix else ''}>"

    def _sel(self, sel):
        return f"{self.prefix} >> {sel}" if self.prefix else sel

    def frame(self, sel):
        """The same API inside an iframe, any origin."""
        return Frame(self.b, self.id, self._sel(sel))

    # Pages

    def goto(self, url, timeout=30):
        """Load url; raises LoadError when Firefox can't (host not found, refused, ...)."""
        return _loaded(self.b.call("goto", _wait=timeout + 5, tab=self.id, url=url,
                                   timeout=int(timeout * 1000)), url)

    def back(self, timeout=30):
        return _loaded(self.b.call("back", _wait=timeout + 5, tab=self.id,
                                   timeout=int(timeout * 1000)), "back")

    def reload(self, timeout=30):
        return _loaded(self.b.call("reload", _wait=timeout + 5, tab=self.id,
                                   timeout=int(timeout * 1000)), "reload")

    def select(self):
        self.b.call("select", tab=self.id)

    def close(self):
        self.b.call("close", tab=self.id)

    @property
    def info(self):
        return next(t for t in self.b.call("tabs") if t["tab"] == self.id)

    @property
    def url(self):
        return self.info["url"]

    @property
    def title(self):
        return self.info["title"]

    # Reading

    def find(self, sel, timeout=10, wait=True):
        """Where the element is (window CSS px), whether it is visible, its text."""
        return self.b.call("find", _wait=timeout + 5, tab=self.id, sel=self._sel(sel),
                           timeout=int(timeout * 1000), wait=wait)

    def wait(self, sel, timeout=10):
        return self.find(sel, timeout)

    def exists(self, sel):
        return self.find(sel, wait=False)["found"]

    def text(self, sel, timeout=10):
        return self.find(sel, timeout)["text"]

    def js(self, code, *args):
        """Runs code as a function body in a private scope over the page.
        `return` gives a value back; page variables are on window.wrappedJSObject."""
        return self.b.call("js", tab=self.id, frame=self.prefix, code=code, args=list(args))

    def seen(self):
        """What this page can read about the browser (read from a private sandbox)."""
        return self.js(SEEN_JS)

    def check(self):
        """What the page sees next to what the profile says, value by value.
        print() it for a table; .ok is False when anything differs."""
        b, page = self.b, self.seen()
        f = None if b.stock else b.profile.fingerprint
        want = {"cookies": None}
        if f:
            want.update({
                "timezone": b.timezone or None,       # None: this computer's clock, nothing to compare
                "langs": ", ".join(b.langs),
                "cores": f.cores,
                "screen": f"{round(f.screen[0] / f.dpr)}x{round(f.screen[1] / f.dpr)}",
                "dpr": f.dpr,
                "touch": 0 if not f.extra.get("touch") else None,   # Firefox rounds other counts itself
                "gpu": f.gpu[1] if f.gpu_mode == "fake" else None,
                "user_agent": f.user_agent,
                "webdriver": False,
            })
        rows = {}
        for k, v in page.items():
            exp = want.get(k)
            if exp is None:
                ok = None
            elif k == "dpr":
                ok = abs(v - exp) < 0.001
            elif k == "gpu":
                # Stock Firefox shortens GPU names for every user (dom/canvas/SanitizeRenderer.cpp),
                # e.g. GTX 1660 SUPER -> GTX 980, so only the maker must match.
                ok = bool(v) and v.split(",")[0] == exp.split(",")[0]
            else:
                ok = v == exp
            rows[k] = {"page": v, "profile": exp, "ok": ok}
        return Check(rows)

    def shot(self, path=None):
        data = base64.b64decode(self.b.call("shot", tab=self.id).split(",", 1)[1])
        if path:
            Path(path).write_bytes(data)
        return data

    # Acting

    def _ready(self, sel, timeout):
        """Finds the element and wheels it into view like a person would."""
        el = self.find(sel, timeout)
        for _ in range(80):
            if el["inView"]:
                # Smooth scrolling or a layout shift may still be moving it.
                time.sleep(self.b.rng.uniform(0.08, 0.15))
                again = self.find(sel, timeout)
                if again["inView"] and abs(again["x"] - el["x"]) < 0.5 and abs(again["y"] - el["y"]) < 0.5:
                    return again
                el = again
                continue
            v = el["view"]
            below = el["y"] + el["h"] / 2 > v["y"] + v["h"] / 2
            x = human.clip(el["x"] + el["w"] / 2, v["x"] + 20, v["x"] + v["w"] - 20)
            y = v["y"] + v["h"] * self.b.rng.uniform(0.35, 0.65)
            if self.b._mouse is None or abs(self.b._mouse[0] - x) > 200:
                self.b.move(x, y, self.id)
            mx, my = self.b._mouse
            for _ in range(self.b.rng.randint(1, 3)):
                self.b.call("wheel", tab=self.id, x=mx, y=my, dy=1 if below else -1)
                time.sleep(self.b.rng.uniform(0.04, 0.12))
            time.sleep(self.b.rng.uniform(0.1, 0.3))
            el = self.find(sel, timeout)
        raise IfoxError(f"could not scroll to {sel}")

    def hover(self, sel, timeout=10):
        el = self._ready(sel, timeout)
        x, y = human.point_in(el, self.b.rng)
        self.b.move(x, y, self.id, width=min(el["w"], el["h"]))
        return el

    def click(self, sel, timeout=10, button=0, clicks=1):
        el = self.hover(sel, timeout)
        x, y = self.b._mouse
        for n in range(1, clicks + 1):
            self.b.call("mouse", tab=self.id, type="down", x=x, y=y, button=button, clicks=n)
            time.sleep(human.press_time(self.b.rng))
            self.b.call("mouse", tab=self.id, type="up", x=x, y=y, button=button, clicks=n)
            if n < clicks:
                time.sleep(self.b.rng.uniform(0.06, 0.12))
        return el

    def press(self, combo):
        """A key or chord: "Enter", "Tab", "Control+a", "Shift+Tab"."""
        *mods, key = combo.split("+")
        for m in mods:
            self.b.call("key", tab=self.id, key=m, type="down")
            time.sleep(self.b.rng.uniform(0.03, 0.08))
        self.b.call("key", tab=self.id, key=key, type="down")
        time.sleep(human.press_time(self.b.rng))
        self.b.call("key", tab=self.id, key=key, type="up")
        for m in reversed(mods):
            time.sleep(self.b.rng.uniform(0.02, 0.06))
            self.b.call("key", tab=self.id, key=m, type="up")

    def type(self, sel, text, clear=False, timeout=10):
        """Clicks the field (sel=None: whatever has focus), then types like a person."""
        if sel is not None:
            self.click(sel, timeout)
            time.sleep(self.b.rng.uniform(0.15, 0.4))
        if clear:
            self.press("Control+a")
            time.sleep(self.b.rng.uniform(0.05, 0.15))
            self.press("Backspace")
        for ch in text:
            key, shift = human.keys_for(ch)
            if shift:
                self.b.call("key", tab=self.id, key="Shift", type="down")
                time.sleep(self.b.rng.uniform(0.03, 0.09))
            self.b.call("key", tab=self.id, key=key, type="down")
            time.sleep(human.press_time(self.b.rng))
            self.b.call("key", tab=self.id, key=key, type="up")
            if shift:
                time.sleep(self.b.rng.uniform(0.01, 0.05))
                self.b.call("key", tab=self.id, key="Shift", type="up")
            time.sleep(human.key_gap(self.b.rng))


SEEN_JS = """
const gl = document.createElement("canvas").getContext("webgl");
const dbg = gl && gl.getExtension("WEBGL_debug_renderer_info");
return {
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  langs: navigator.languages.join(", "),
  cores: navigator.hardwareConcurrency,
  screen: screen.width + "x" + screen.height,
  dpr: devicePixelRatio,
  touch: navigator.maxTouchPoints,
  gpu: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : null,
  user_agent: navigator.userAgent,
  webdriver: navigator.webdriver,
  cookies: document.cookie ? document.cookie.split("; ").length : 0,
};"""


class Check(dict):
    """tab.check() result: {value: {"page": ..., "profile": ..., "ok": True/False/None}}."""

    @property
    def ok(self):
        return all(r["ok"] is not False for r in self.values())

    def __str__(self):
        mark = {True: "ok", False: "DIFFERENT", None: ""}
        lines = [f"  {k:11} {str(r['page'])[:60]:60}  {mark[r['ok']]}"
                 + (f"  profile: {r['profile']}" if r["ok"] is False else "") for k, r in self.items()]
        return "\n".join(lines + [f"  {'all match' if self.ok else 'MISMATCH'}"])


class Frame(Tab):
    """A tab seen through one iframe: same methods, selectors start inside it."""

    def __repr__(self):
        return f"<Frame {self.prefix} in tab {self.id}>"
