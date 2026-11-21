# Innocent Fox

Firefox 160 with its fingerprint set per profile, changed in the C++ source.
Python drives it over a private pipe, so pages find no injected scripts or webdriver.

Windows 10/11, 64-bit. Python 3.10+.

## Install

```
pip install https://github.com/Galaxy-GunPowder/innocent-fox/releases/download/v0.1.1/innocent_fox-0.1.1-py3-none-any.whl
```

That's all. The first `Browser()` downloads the built browser (130 MB) once and checks its SHA-256; nothing to patch or build.
To download it ahead of time, run `ifox-install`.

## Use

```python
from ifox import Browser

with Browser(proxy="https://user:pass@host:port") as b:      # the built-in default profile
    tab = b.open("https://example.com/")
    print(tab.check())                                        # what the page sees, next to the profile
```

| Profile | Does |
|---|---|
| `Browser()` | built-in `default`: random device and canvas seed every run, real GPU, nothing kept |
| `Browser("shop1")` | saved profile: same device, cookies and logins every run |
| `profile.create(...)` | a saved profile with your settings; `print(p)` shows its full detail |

Clock and languages follow the proxy's exit country.
The browser closes with your script, however it ends.

Every setting and call: [examples/profiles.py](examples/profiles.py), [docs/scripting.md](docs/scripting.md).

## How it works

| Layer | Language | Job |
|---|---|---|
| `ifox` | Python | profiles, pages, human-like input |
| Agent | privileged Firefox JS | inside the browser, talks to Python over a pipe |
| Patches | C++ | fingerprint values, read from `ifox.*` prefs |

Pages can't read prefs, so one build becomes any fingerprint. Pref names: [docs/prefs.md](docs/prefs.md).

## Status

| Test | Result |
|---|---|
| Smoke | 20/20: `python tests/smoke/run_smoke.py` |
| Pipe | 21/21: `python tests/pipe/run_pipe.py` |
| WebRTC leak | 6/6, WebRTC only, local test proxy: no WebRTC address shown |
| CreepJS | 0% headless, 0% stealth, no lies |
| Real proxy (Decodo) | FAIL, 10/11: DNS servers show Singapore next to a US exit (the provider's entry server looks names up) |

## Build from source

The scripts expect `D:\ifox` (no spaces). First build about 90 minutes.

```
python scripts/fetch_source.py          # Firefox 160.0.1 source into D:\ifox\src
python scripts/patchtool.py apply       # patches/*.patch, in order
python scripts/build.py                 # mach build
python scripts/build.py package         # the release zip
```

## License

MPL 2.0. Not made or endorsed by Mozilla; see [NOTICE.md](NOTICE.md).
Use it only on sites and accounts where you're allowed to.
