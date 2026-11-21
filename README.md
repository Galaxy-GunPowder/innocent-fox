<h1 align="center">Innocent Fox</h1>

<p align="center">Fully scriptable, identity-secure browser based on Firefox 160.</p>

<p align="center">
  <a href="#major-changes"><img src="https://img.shields.io/badge/Major_changes-1f6feb?style=for-the-badge" alt="Major changes"></a>
  &nbsp;
  <a href="#full-list-of-changes"><img src="https://img.shields.io/badge/Full_list_of_changes-30363d?style=for-the-badge" alt="Full list of changes"></a>
  &nbsp;
  <a href="#download"><img src="https://img.shields.io/badge/Download-2da44e?style=for-the-badge" alt="Download"></a>
</p>

# Introduction

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

# Contents

1. [Major changes](#major-changes): [Proxy](#proxy) · [Fingerprint](#fingerprint) · [Scripting](#scripting) · [Profiles](#profiles) · [Fewer background connections](#fewer-background-connections)
2. [Full list of changes](#full-list-of-changes)
3. [How to use](#how-to-use): [Download](#download) · [Your first script](#your-first-script) · [Common calls](#common-calls) · [Build it yourself](#build-it-yourself)
4. [Tests](#tests)
5. [License](#license)

---

# Major changes

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

# Full list of changes

Every change, with how it was made and what is still planned, is listed in the build list:
[docs/build-list.md](https://github.com/Galaxy-GunPowder/innocent-fox/blob/main/docs/build-list.md).

<p align="right"><a href="#contents">Back to contents</a></p>

---

# How to use

The download is the finished, ready-to-use browser: everything above is already built in.
Install it, write a short Python script, and it runs. Building it yourself is only needed if you want to change the browser.

### Download

You need Windows 10 or 11 (64-bit) and Python 3.10 or newer. Install with one command:

```
pip install https://github.com/Galaxy-GunPowder/innocent-fox/releases/download/v0.1.1/innocent_fox-0.1.1-py3-none-any.whl
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

p = profile.create("shop1", proxy="https://user:pass@host:port")   # saved: same computer every run
print(p)                                                           # every setting and session
with Browser("shop1") as b:
    b.open("https://example.com/")
```

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

<p align="right"><a href="#contents">Back to contents</a></p>

---

# Tests

| Test | Result |
|---|---|
| Smoke | 20/20: `python tests/smoke/run_smoke.py` |
| Pipe | 21/21: `python tests/pipe/run_pipe.py` |
| WebRTC leak | 6/6, WebRTC only, local test proxy |
| CreepJS | 0% headless, 0% stealth, no lies |
| Real proxy (Decodo) | FAIL, 10/11: DNS servers show Singapore next to a US exit (the provider's entry server looks names up) |

<p align="right"><a href="#contents">Back to contents</a></p>

---

# License

MPL 2.0. Not made or endorsed by Mozilla; see [NOTICE.md](NOTICE.md).
Use it only on sites and accounts where you're allowed to.

<p align="right"><a href="#contents">Back to contents</a></p>
