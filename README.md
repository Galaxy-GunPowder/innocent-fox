<div align="center">

<img src="branding/fox-256.png" width="132" alt="Innocent Fox">

<h1>Innocent Fox</h1>

<p>Scriptable anti-detect browser, built on Firefox.</p>

<p>
  <img src="https://img.shields.io/badge/Firefox-158_%7C_159_%7C_160-2f7f99?logo=firefoxbrowser&logoColor=white" alt="Firefox 158, 159 and 160">
  <img src="https://img.shields.io/badge/Windows-10_%7C_11-2f7f99?logo=windows&logoColor=white" alt="Windows 10 and 11">
  <img src="https://img.shields.io/badge/Python-3.10+-2f7f99?logo=python&logoColor=white" alt="Python 3.10 or newer">
  <img src="https://img.shields.io/github/v/release/Galaxy-GunPowder/innocent-fox?color=1d4e74&label=release" alt="Latest release">
  <img src="https://img.shields.io/badge/license-MPL_2.0-1d4e74" alt="MPL 2.0 license">
</p>

<p><a href="#introduction">Introduction</a> &nbsp;·&nbsp; <a href="#design-goals">Design goals</a> &nbsp;·&nbsp; <a href="#test-results">Test results</a> &nbsp;·&nbsp; <a href="#versions">Versions</a> &nbsp;·&nbsp; <a href="#how-to-use">How to use</a> &nbsp;·&nbsp; <a href="#license">License</a> &nbsp;·&nbsp; <a href="#special-thanks">Special thanks</a></p>

</div>

<br>

# Introduction

Innocent Fox is an anti-detect, identity-safe, fully scriptable browser.
It is Firefox 160 with its source code changed directly: 27 major changes for identity safety, in 13 patches.
Each profile can be Firefox 158, 159 or 160, identical to the official release in 7 fingerprint layers, from the TLS handshake to WebGL.
See the [major changes](docs/major-changes.md) and the [full list of changes](docs/build-list.md).

**Test results:** 6/6 public bot checkers passed, and Firefox 158, 159 and 160 each show 0 differences from official. [All results](#test-results)

<br>

# Design goals

| Goal | What it means |
|---|---|
| Fully scriptable | Python controls every page, frame, click and keystroke |
| Bot detection countered | Pages find no automation traces: no webdriver flag, no control port, no injected code |
| Consistent identity | Every layer agrees: a Firefox 158 profile has 158's TLS, a US proxy has a US clock |

<br>

# Test results

Public bot and fingerprint checkers, run on 21 November 2026 with the built-in default profile (Firefox 160) through a US residential proxy.

| Checker | What it checks | Passed | |
|---|---|:---:|:---:|
| [BotD](https://fingerprintjs.github.io/BotD/main/) by Fingerprint | Bot detectors | 18/18 | ✅ |
| [Device and Browser Info](https://deviceandbrowserinfo.com/are_you_a_bot) | Automation signals | 22/22 | ✅ |
| [BrowserScan](https://www.browserscan.net/bot-detection) | Bot and automation checks | 17/17 | ✅ |
| [Sannysoft](https://bot.sannysoft.com/) | Classic bot checks | 23/24 ¹ | ✅ |
| [CreepJS](https://abrahamjuliot.github.io/creepjs/) | Headless and stealth score | 0% / 0% | ✅ |
| [Pixelscan](https://pixelscan.net/fingerprint-check) | Fingerprint consistency, proxy | Consistent, no proxy seen | ✅ |
| WebRTC leak test, in this repo | Real IP through WebRTC | 6/6 | ✅ |
| Real proxy test, in this repo | Exit IP, WebRTC, DNS, login | 10/11 ² | ⚠️ |

<sub>¹ The one miss is "Chrome object", a Chrome-only check that every Firefox fails.<br>
² DNS servers show Singapore next to a US exit; the proxy provider's entry server does the lookups.</sub>

<br>

# Versions

Innocent Fox is built once, from Firefox 160. Each profile then shows websites Firefox 158, 159 or 160.

| Term | Meaning |
|---|---|
| Assembled browser | One build that is several Firefox versions to websites |
| Base build | The engine actually built: Firefox 160.0.1 |
| Shown version | The version a website sees: 158, 159 or 160 |
| Version switch | Settings that turn off what is newer than the shown version (`ifox.compat.*`) |
| Verified | 0 differences from the official release in the identity lab |

A new profile picks one of the 3 at random and keeps it. Set one with `version="158"`.

### Lab results

Our build against official Firefox from mozilla.org, 22 November 2026, 2 runs each, on local test servers only.
The lab compares TLS (JA3, JA4), HTTP/2, header order, web APIs, CSS, media codecs and WebGL.

| Shown version | Differences from official | |
|---|:---:|:---:|
| Firefox 160 | 0 | ✅ |
| Firefox 159 | 0 | ✅ |
| Firefox 158 | 0 | ✅ |

The bot lab opens the same page by hand and by script: 0 automation traces, 13/13 input checks.

<br>

# How to use

The download is the finished, ready-to-use browser: everything above is already built in.
Install it, write a short Python script, and it runs. Building it yourself is only needed if you want to change the browser.

### Download

You need Windows 10 or 11 (64-bit) and Python 3.10 or newer. Install with one command:

```
pip install https://github.com/Galaxy-GunPowder/innocent-fox/releases/download/v0.2.1/innocent_fox-0.2.1-py3-none-any.whl
```

The first time your script opens a browser, it downloads the browser itself (130 MB) and checks it. After that it starts in about 2 seconds.
You can also get the browser zip from the [releases page](https://github.com/Galaxy-GunPowder/innocent-fox/releases) and install it with `ifox-install --zip <file>`.

### Your first script

```python
from ifox import Browser, profile

with Browser(proxy="https://user:pass@host:port") as b:     # built-in default: random every run
    tab = b.open("https://example.com/login")
    tab.type("#email", "a@example.com")                     # human typing rhythm
    tab.click("text=Sign in")                                # human mouse path, real click
    print(tab.check())                                       # what the page sees, next to the profile

p = profile.create("shop1", proxy="https://user:pass@host:port")   # saved: same computer and version every run
print(p)                                                           # every setting and session
profile.create("shop2", version="158")                             # always Firefox 158 to websites
with Browser("shop1") as b:
    b.open("https://example.com/")
```

### What a profile holds

| Layer | What websites see | Set by |
|---|---|---|
| Device | CPU cores, screen, display scale, graphics card, canvas | `device`: random, then kept |
| Version | Web APIs and the TLS and HTTP/2 handshake of Firefox 158, 159 or 160 | `version`: random, then kept |
| Network | IP address; WebRTC and DNS go through the proxy too | `proxy` |
| Location | Time zone and languages of the proxy's country | `timezone`, `langs` |
| Storage | Cookies, logins and history | kept per profile |
| Behaviour | Human mouse paths and typing, no automation traces | built in |

The built-in default profile is new every run; saved profiles stay the same person every run.

### Common calls

| Call | What it does |
|---|---|
| `b.open(url)`, `tab.goto(url)` | Open a page |
| `tab.click`, `type`, `press`, `hover` | Use the mouse and keyboard like a person |
| `tab.wait(sel)`, `text(sel)`, `exists(sel)` | Read the page |
| `tab.frame("iframe#pay")` | The same calls inside a frame |
| `tab.js("return document.title")` | Run JavaScript the page can't see |
| `tab.shot("page.png")` | Take a screenshot |

Every setting and call is explained in [docs/scripting.md](docs/scripting.md), with a full example in [examples/profiles.py](examples/profiles.py).

### Build it yourself

Only needed if you want to change the browser. The scripts expect the folder `D:\ifox` (no spaces in the path), and the first build takes about 90 minutes.

```
python scripts/fetch_source.py          # Firefox 160.0.1 source into D:\ifox\src
python scripts/patchtool.py apply       # patches/*.patch, in order
python scripts/build.py                 # build the browser
python scripts/build.py package         # make the release zip
```

<br>

# License

<div align="center">

MPL 2.0 &nbsp;·&nbsp; Not made or endorsed by Mozilla &nbsp;·&nbsp; <a href="NOTICE.md">Notice</a>

<sub>Use it only on sites and accounts where you're allowed to.</sub>

</div>

<br>

# Special thanks

- My $50 and 10 hours of my life.
- Claude Opus 5.5 (High), for its reasonable price and coding that keeps getting better, alongside Jensen Huang's great GPUs and the electricity company that made this happen.
- The Mozilla team, for the bad business strategy of open-sourcing 28 years of work, ever since Netscape released its code on 31 March 1998.
- Everyone who pushed back on Google's Web Environment Integrity, so the web still lets unsigned browsers in, for the past 10 years and the next 0 to 12 months at best.
