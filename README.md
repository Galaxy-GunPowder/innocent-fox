<h1 align="center">Innocent Fox</h1>

<p align="center">Fully scriptable, identity-secure browser based on Firefox 160.</p>

<p align="center">
  <a href="#major-changes"><img src="https://img.shields.io/badge/Major_changes-1f6feb?style=for-the-badge" alt="Major changes"></a>
  &nbsp;
  <a href="#full-list-of-changes"><img src="https://img.shields.io/badge/Full_list_of_changes-30363d?style=for-the-badge" alt="Full list of changes"></a>
  &nbsp;
  <a href="#download"><img src="https://img.shields.io/badge/Download-2da44e?style=for-the-badge" alt="Download"></a>
</p>

## Introduction

Innocent Fox is a version of Firefox 160 for running many separate online identities from Python.
Each identity, called a profile, keeps its own settings, cookies, logins and internet connection.
To a website, every profile looks like an ordinary person on an ordinary computer.

What's different from Firefox:

- **Its own proxy for each profile.** Every profile connects through its own proxy, and the time zone and languages follow the proxy's country. The browser never falls back to your real connection, and WebRTC and DNS lookups go through the proxy too.
- **Its own device for each profile.** Screen size, display scale, CPU cores, graphics card, touch support and canvas noise are set per profile. The changes are made inside the browser engine, so every page, frame and worker sees the same values.
- **Scripting that websites can't see.** Python controls the browser through a private channel instead of the usual automation port. Mouse movement and typing follow human timing, and pages find no webdriver flag or injected code.
- **Simple profile management.** Create, load, update, wipe or delete profiles from Python. For quick jobs, the built-in default profile gives you a new random device every time and keeps nothing afterwards.

Install it with one `pip` command; the browser downloads itself the first time you use it.

---

## Contents

1. [Major changes](#major-changes): [Proxy](#proxy) · [Fingerprint](#fingerprint) · [Scripting](#scripting) · [Profiles](#profiles) · [Fewer background connections](#fewer-background-connections)
2. [Full list of changes](#full-list-of-changes): [Fingerprint](#fingerprint-1) · [Control](#control) · [Network](#network) · [Python side](#python-side) · [Branding](#branding)
3. [Download](#download)
4. [How to use](#how-to-use)
5. [Tests](#tests)
6. [Build from source](#build-from-source)
7. [License](#license)

---

## Major changes

### Proxy

Each profile has its own proxy, and the browser makes sure nothing slips past it.

| Change | What you get |
|---|---|
| HTTPS, HTTP and SOCKS5 proxies, with login | Paste a proxy in any of 5 common formats |
| Time zone and languages follow the proxy | A Brazil proxy gave Portuguese (pt-BR) and the São Paulo clock |
| WebRTC goes through the proxy only | Sites see 0 local addresses and never your real IP |
| DNS lookups go through the proxy | Only the proxy's own address is looked up on your computer |
| Kill switch | If the proxy drops, pages stop loading instead of using your real connection |

### Fingerprint

Websites read many small details to recognise a computer. Each profile gives them a consistent set.

| Change | What you get |
|---|---|
| Device values set per profile, inside the engine | 15 values, such as screen, display scale, CPU cores, graphics card and touch |
| Devices copied from real computers | 4 real machine types, each with its own matching screen, cores and graphics card |
| Canvas noise kept per profile | A saved profile looks the same every time you open it |

### Scripting

You drive the browser from Python, and websites can't tell it's being scripted.

| Change | What you get |
|---|---|
| A private channel instead of an automation port | The CreepJS test scores 0% headless and 0% stealth |
| Mouse and keyboard work like a real person's | Natural mouse paths and typing rhythm, reported as real input |
| Works inside frames and shadow DOM | Payment frames from other sites included |

### Profiles

Profiles are folders you manage from Python, and each one shows a full report of itself.

| Change | What you get |
|---|---|
| Saved profiles | The same device, cookies and logins every time |
| A built-in default profile | A new random device every run, with nothing kept afterwards |
| Session history | `print(p)` lists the proxies, countries and websites each profile has used |

### Fewer background connections

Firefox normally contacts many services on its own. Most are turned off: an idle tab now reaches 8 addresses instead of 33.

<p align="right"><a href="#contents">Back to contents</a></p>

---

## Full list of changes

Every change, side by side with standard Firefox 160. The browser changes are 11 patches: 1,208 added lines in 23 Firefox files ([patches/](patches)).

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

<p align="right"><a href="#contents">Back to contents</a></p>

---

## Download

Windows 10/11, 64-bit, Python 3.10+.

```
pip install https://github.com/Galaxy-GunPowder/innocent-fox/releases/download/v0.1.1/innocent_fox-0.1.1-py3-none-any.whl
```

The first `Browser()` downloads the built browser (130 MB) once and checks its SHA-256. Nothing to patch or build.
The browser zip is also on the [releases page](https://github.com/Galaxy-GunPowder/innocent-fox/releases); `ifox-install --zip <file>` installs it.

<p align="right"><a href="#contents">Back to contents</a></p>

---

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

<p align="right"><a href="#contents">Back to contents</a></p>

---

## Tests

| Test | Result |
|---|---|
| Smoke | 20/20: `python tests/smoke/run_smoke.py` |
| Pipe | 21/21: `python tests/pipe/run_pipe.py` |
| WebRTC leak | 6/6, WebRTC only, local test proxy |
| CreepJS | 0% headless, 0% stealth, no lies |
| Real proxy (Decodo) | FAIL, 10/11: DNS servers show Singapore next to a US exit (the provider's entry server looks names up) |

<p align="right"><a href="#contents">Back to contents</a></p>

---

## Build from source

Only needed to change the browser. The scripts expect `D:\ifox` (no spaces). First build about 90 minutes.

```
python scripts/fetch_source.py          # Firefox 160.0.1 source into D:\ifox\src
python scripts/patchtool.py apply       # patches/*.patch, in order
python scripts/build.py                 # mach build
python scripts/build.py package         # the release zip
```

<p align="right"><a href="#contents">Back to contents</a></p>

---

## License

MPL 2.0. Not made or endorsed by Mozilla; see [NOTICE.md](NOTICE.md).
Use it only on sites and accounts where you're allowed to.

<p align="right"><a href="#contents">Back to contents</a></p>
