<h1 align="center">Innocent Fox</h1>

<p align="center">Fully scriptable, identity-secure browser based on Firefox 160.</p>

<p align="center">
  <a href="#major-changes"><img src="https://img.shields.io/badge/Major_changes-1f6feb?style=for-the-badge" alt="Major changes"></a>
  &nbsp;
  <a href="#full-list-of-changes"><img src="https://img.shields.io/badge/Full_list_of_changes-30363d?style=for-the-badge" alt="Full list of changes"></a>
  &nbsp;
  <a href="#download"><img src="https://img.shields.io/badge/Download-2da44e?style=for-the-badge" alt="Download"></a>
</p>

Each profile looks like one real computer: its own screen, cores, GPU, clock, languages and proxy.
The values are set inside Firefox's C++, so pages find no injected scripts to detect.
Python drives it over a private pipe, with mouse and keys that move like a person's.

## Major changes

### Proxy

Each profile has its own proxy, and nothing leaves around it.

| Change | Result |
|---|---|
| HTTPS, HTTP and SOCKS5, with login | 5 text formats accepted |
| Clock and languages follow the exit | Brazil exit gave pt-BR and the São Paulo clock |
| WebRTC through the proxy only | 0 addresses shown, real IP never |
| DNS through the proxy | only the proxy's own name is looked up locally |
| Kill switch | if the proxy drops, pages fail; never your real IP |

### Fingerprint

| Change | Result |
|---|---|
| Set per profile, in C++ | 15 values: screen, scale, cores, GPU, touch, clock and more |
| Devices copied from real machines | 4 devices, each with its own screen, cores and GPU |
| Canvas noise key kept per profile | the same profile looks the same after restarts |

### Scripting

| Change | Result |
|---|---|
| Control over a named pipe, not a port | CreepJS: 0% headless, 0% stealth, no lies |
| Mouse and keys enter like OS input | trusted events, human paths and typing rhythm |
| Selectors reach into iframes and shadow roots | cross-site iframes too |

### Profiles

| Change | Result |
|---|---|
| Saved profiles | same computer, cookies and logins every run |
| Built-in `default` | random device and seed every run, nothing kept |
| Session details | proxies, exit countries and sites visited, from `print(p)` |

### Quiet

Background calls pages can't see are off: 33 hosts on an idle tab, down to 8.

## Full list of changes

Compared with stock Firefox 160. Firefox source: 11 patches, 1,208 added lines in 23 files ([patches/](patches)).

### Fingerprint

| Value | Firefox 160 | Innocent Fox | How |
|---|---|---|---|
| User agent, platform, oscpu | this computer's | the profile's | stock prefs |
| Screen size, CSS device-width | real screen | the profile's | [patch 03](patches/03-screen.patch) |
| Display scale | real, zoomed by Windows "Text size" (101% gives 1.0169) | the profile's, no zoom | stock prefs |
| CPU cores, pages and workers | real | the profile's | [patch 02](patches/02-navigator.patch) |
| Touch points, CSS pointer queries | real | the profile's | [patches 02](patches/02-navigator.patch), [06](patches/06-pointer.patch) |
| `navigator.webdriver` | true when automated | always false | [patch 02](patches/02-navigator.patch) |
| Time zone, pages, workers, sandboxes | this computer's | the proxy exit's | [patches 08](patches/08-timezone.patch), [10](patches/10-sandbox-timezone.patch) |
| Languages | this computer's | the exit country's | stock pref |
| GPU vendor and renderer | real | a claimed GPU, or real | stock prefs |
| WebGL limits and extensions | real GPU's | the claimed GPU's | [patch 05](patches/05-webgl-gpu.patch) |
| WebGL pixel noise | off | on with a claimed GPU | stock pref |
| Canvas noise | new key each session | key kept per profile | [patch 04](patches/04-noise-seed.patch) |
| Audio sample rate | the sound card's | the profile's | stock pref |

All values come from `ifox.*` prefs, registered in [patch 01](patches/01-ifox-prefs.patch). Pages can't read prefs.

### Control

| | Firefox 160 | Innocent Fox | How |
|---|---|---|---|
| Automation | Marionette or BiDi on a TCP port | named pipe, no port | [patch 07](patches/07-pipe-agent.patch) |
| Input | synthesized test events | through the top window, like OS input | [patch 07](patches/07-pipe-agent.patch) |
| Driven window covered or behind | pages go hidden | acts as the front window | stock prefs |

### Network

| | Firefox 160 | Innocent Fox | How |
|---|---|---|---|
| HTTP proxy login | a prompt for a person | sent without a prompt | [patch 09](patches/09-http-proxy-login.patch) |
| Proxy down | can fall back to direct | pages fail | stock pref |
| DNS with a SOCKS proxy | local | through the proxy | stock pref |
| WebRTC behind a proxy | own UDP, can show the real IP | proxy only | stock pref |
| Idle background calls | 33 hosts | 8 | stock prefs |

### Python side

| Change | How |
|---|---|
| Profiles: create, load, update, wipe history (settings kept), delete | `ifox/profile.py` |
| `tab.check()`: what the page sees, next to the profile | `ifox/browser.py` |
| Browser closes with your script, even on a crash or kill | Windows job object |
| Browser downloads itself on first use, SHA-256 checked | `ifox/install.py` |

### Branding

Own name and fox icon, on Firefox's unofficial branding ([patch 11](patches/11-branding.patch)).

Not done yet: claiming other Firefox versions, a script gate, a WireGuard tunnel. Plan: [docs/build-list.md](docs/build-list.md).

## Download

Windows 10/11, 64-bit, Python 3.10+.

```
pip install https://github.com/Galaxy-GunPowder/innocent-fox/releases/download/v0.1.1/innocent_fox-0.1.1-py3-none-any.whl
```

The first `Browser()` downloads the built browser (130 MB) once and checks its SHA-256. Nothing to patch or build.
The browser zip is also on the [releases page](https://github.com/Galaxy-GunPowder/innocent-fox/releases); `ifox-install --zip <file>` installs it.

## How to use

```python
from ifox import Browser, profile

with Browser(proxy="https://user:pass@host:port") as b:     # built-in default: random every run
    tab = b.open("https://example.com/login")
    tab.type("#email", "a@example.com")                     # human typing rhythm
    tab.click("text=Sign in")                                # human mouse path, real click
    print(tab.check())                                       # what the page sees, next to the profile

p = profile.create("shop1", proxy="https://user:pass@host:port")   # saved: same computer every run
print(p)                                                           # every setting and session
with Browser("shop1") as b:
    b.open("https://example.com/")
```

| Call | Does |
|---|---|
| `b.open(url)`, `tab.goto(url)` | open a page |
| `tab.click`, `type`, `press`, `hover` | input like a person |
| `tab.wait(sel)`, `text(sel)`, `exists(sel)` | read the page |
| `tab.frame("iframe#pay")` | the same calls inside an iframe |
| `tab.js("return document.title")` | run JS the page can't see |
| `tab.shot("page.png")` | screenshot |

Every setting and call: [docs/scripting.md](docs/scripting.md) and [examples/profiles.py](examples/profiles.py).

## Tests

| Test | Result |
|---|---|
| Smoke | 20/20: `python tests/smoke/run_smoke.py` |
| Pipe | 21/21: `python tests/pipe/run_pipe.py` |
| WebRTC leak | 6/6, WebRTC only, local test proxy |
| CreepJS | 0% headless, 0% stealth, no lies |
| Real proxy (Decodo) | FAIL, 10/11: DNS servers show Singapore next to a US exit (the provider's entry server looks names up) |

## Build from source

Only needed to change the browser. The scripts expect `D:\ifox` (no spaces). First build about 90 minutes.

```
python scripts/fetch_source.py          # Firefox 160.0.1 source into D:\ifox\src
python scripts/patchtool.py apply       # patches/*.patch, in order
python scripts/build.py                 # mach build
python scripts/build.py package         # the release zip
```

## License

MPL 2.0. Not made or endorsed by Mozilla; see [NOTICE.md](NOTICE.md).
Use it only on sites and accounts where you're allowed to.
