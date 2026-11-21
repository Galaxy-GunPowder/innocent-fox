<div align="center">

<img src="branding/fox-256.png" width="132" alt="Innocent Fox">

<h1>Innocent Fox</h1>

<p>Fully scriptable, identity-secure browser based on Firefox 160.</p>

<p>
  <img src="https://img.shields.io/badge/based_on-Firefox_160-2f7f99?logo=firefoxbrowser&logoColor=white" alt="Based on Firefox 160">
  <img src="https://img.shields.io/badge/Windows-10_%7C_11-2f7f99?logo=windows&logoColor=white" alt="Windows 10 and 11">
  <img src="https://img.shields.io/badge/Python-3.10+-2f7f99?logo=python&logoColor=white" alt="Python 3.10 or newer">
  <img src="https://img.shields.io/github/v/release/Galaxy-GunPowder/innocent-fox?color=1d4e74&label=release" alt="Latest release">
  <img src="https://img.shields.io/badge/license-MPL_2.0-1d4e74" alt="MPL 2.0 license">
</p>

<p>
  <a href="#major-changes"><img src="https://img.shields.io/badge/Major_changes-2f7f99?style=for-the-badge" alt="Major changes"></a>
  &nbsp;
  <a href="#how-to-use"><img src="https://img.shields.io/badge/How_to_use-3b82c4?style=for-the-badge" alt="How to use"></a>
  &nbsp;
  <a href="#download"><img src="https://img.shields.io/badge/Download-1d4e74?style=for-the-badge" alt="Download"></a>
</p>

</div>

<br>

# Introduction

Innocent Fox is a version of Firefox 160 for running many separate online identities from Python.
Each identity, called a profile, keeps its own settings, cookies, logins and internet connection.
To a website, every profile looks like an ordinary person on an ordinary computer.

<table>
<tr>
<td width="50%" valign="top">

**Its own proxy for each profile**

Every profile connects through its own proxy, and the time zone and languages follow the proxy's country. The browser never falls back to your real connection; WebRTC and DNS go through the proxy too.

</td>
<td width="50%" valign="top">

**Its own device for each profile**

Screen size, display scale, CPU cores, graphics card, touch support and canvas noise are set per profile, inside the browser engine. Every page, frame and worker sees the same values.

</td>
</tr>
<tr>
<td width="50%" valign="top">

**Scripting that websites can't see**

Python controls the browser through a private channel instead of the usual automation port. Mouse movement and typing follow human timing, with no webdriver flag or injected code.

</td>
<td width="50%" valign="top">

**Simple profile management**

Create, load, update, wipe or delete profiles from Python. For quick jobs, the built-in default profile gives you a new random device every time and keeps nothing.

</td>
</tr>
</table>

<p align="center">Install it with one <code>pip</code> command. The browser downloads itself the first time you use it.</p>

<br>

# Contents

<div align="center">

<a href="#major-changes">Major changes</a> &nbsp;·&nbsp; <a href="#how-to-use">How to use</a> &nbsp;·&nbsp; <a href="#tests">Tests</a> &nbsp;·&nbsp; <a href="#license">License</a>

<sub><a href="#proxy">Proxy</a> &nbsp;·&nbsp; <a href="#fingerprint">Fingerprint</a> &nbsp;·&nbsp; <a href="#scripting">Scripting</a> &nbsp;·&nbsp; <a href="#profiles">Profiles</a> &nbsp;·&nbsp; <a href="#download">Download</a> &nbsp;·&nbsp; <a href="#your-first-script">First script</a> &nbsp;·&nbsp; <a href="#common-calls">Common calls</a> &nbsp;·&nbsp; <a href="#build-it-yourself">Build it yourself</a></sub>

</div>

<br>

# Major changes

These are the main changes; the full list is in [docs/build-list.md](https://github.com/Galaxy-GunPowder/innocent-fox/blob/main/docs/build-list.md).

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

<br>

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

<br>

# Tests

| Test | Result |
|---|---|
| Smoke | 20/20: `python tests/smoke/run_smoke.py` |
| Pipe | 21/21: `python tests/pipe/run_pipe.py` |
| WebRTC leak | 6/6, WebRTC only, local test proxy |
| CreepJS | 0% headless, 0% stealth, no lies |
| Real proxy (Decodo) | FAIL, 10/11: DNS servers show Singapore next to a US exit (the provider's entry server looks names up) |

<br>

# License

<div align="center">

MPL 2.0 &nbsp;·&nbsp; Not made or endorsed by Mozilla &nbsp;·&nbsp; <a href="NOTICE.md">Notice</a>

<sub>Use it only on sites and accounts where you're allowed to.</sub>

</div>
