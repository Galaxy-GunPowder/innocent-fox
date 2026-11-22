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

<p><a href="#introduction">Introduction</a> &nbsp;·&nbsp; <a href="#features">Features</a> &nbsp;·&nbsp; <a href="#test-results">Test results</a> &nbsp;·&nbsp; <a href="#how-to-use">How to use</a> &nbsp;·&nbsp; <a href="#license">License</a> &nbsp;·&nbsp; <a href="#special-thanks">Special thanks</a></p>

</div>

<br>

# Introduction

Innocent Fox is an anti-detect, identity-safe, fully scriptable browser, built by changing Firefox 160's source code directly.
Each profile can be Firefox 158, 159 or 160, identical to the official release in 7 fingerprint layers, from the TLS handshake to WebGL.

**Design goals:** fully scriptable from Python, no automation traces, and every layer of an identity agrees.<br>
**Changes:** 27 major changes for identity safety, in 13 patches. [Features](#features) · [Full list](docs/build-list.md)<br>
**Test results:** 6/6 public bot checkers passed, and Firefox 158, 159 and 160 each show 0 differences from official. [All results](#test-results)

<br>

# Features

| Category | Feature |
|---|---|
| Versions | One build, shown to websites as Firefox 158, 159 or 160; each shows 0 differences from official in the [identity lab](tests/identity) |
| Scripting | Python drives every page, frame and shadow DOM through a private pipe, not an automation port |
| Scripting | Mouse and keyboard use the normal input path, with human mouse paths and typing rhythm |
| Bot detection | `navigator.webdriver` is false, and your scripts run in a sandbox the page can't see |
| Bot detection | Pages stay focused and visible, and a driven window never takes the foreground from your program |
| Fingerprint | 15 device values set inside the engine, such as screen, display scale, CPU cores and touch |
| Fingerprint | This computer's GPU by default, so WebGL pixels match the GPU name pages see |
| Fingerprint | Canvas noise key kept per profile, so a profile looks the same after restarts |
| Proxy | HTTPS, HTTP and SOCKS5 proxies with login, pasted in any of 5 common formats |
| Proxy | Time zone and languages follow the proxy's country |
| Proxy | WebRTC and DNS go through the proxy; sites see 0 local addresses |
| Proxy | Kill switch: if the proxy drops, pages stop loading instead of using your connection |
| Profiles | Saved profiles keep device, version, cookies and logins every run; the default profile is new every run |
| Background | Idle background connections cut from 33 addresses to 8 |
| Install | The browser downloads itself on first use and closes when your script ends |

Every change, with how it was made: [summary](docs/major-changes.md) · [full list](docs/build-list.md)

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

# How to use

### Download and install

All you need is a Windows 10 or 11 PC (64-bit) and Python. The browser itself installs on its own.

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/). On the installer's first screen, tick "Add python.exe to PATH".
2. Open PowerShell and install Innocent Fox:

   ```
   pip install https://github.com/Galaxy-GunPowder/innocent-fox/releases/download/v0.2.2/innocent_fox-0.2.2-py3-none-any.whl
   ```

3. Save this as `start.py`:

   ```python
   from ifox import Browser

   with Browser() as b:                    # the default profile: a new identity every run
       b.open("https://example.com/")
       b.wait_closed()                     # keeps the window open until you close it
   ```

4. Run it in PowerShell, in the folder where you saved it:

   ```
   python start.py
   ```

The first run downloads the browser (130 MB) and checks it; after that it starts in about 2 seconds.
The sections below show what to put in your script.

### Manage profiles

#### Create a new profile

```python
from ifox import profile

p = profile.create(
    "myprofile",
    overwrite=False,             # True replaces a profile of the same name
    proxy="https://user:pass@host:port",   # None = this computer's own connection
    timezone="auto",             # the proxy exit's clock, every start; or "America/Chicago"
    langs="auto",                # the exit country's languages, fixed at first start; or ["en-US", "en"]
    version=None,                # None = 158, 159 or 160 at random, then kept; or "158"
    device=None,                 # None = a random real machine, then kept; or "i5-1135g7-laptop"
    cores=None,                  # None = the device's; set only to copy another real machine
    screen=None,                 # None = the device's; e.g. (1920, 1080), device pixels
    dpr=None,                    # None = the device's; e.g. 1.25
    gpu=None,                    # None = the device's; e.g. ("Google Inc. (Intel)", "ANGLE (Intel, ...)")
    touch=0,                     # touch points; 0 = no touch screen
    gpu_mode="real",             # "real" = this computer's GPU; "fake" = claim the device's, with WebGL noise
    seed=None,                   # canvas noise key; None = random once, then kept
    prefs={},                    # extra Firefox prefs, {"name": value}
)
print(p)                         # every setting, what pages see, and session history
```

#### Load, change, delete

```python
p = profile.load("myprofile")    # a saved one
p.update(langs=["en-US", "en"])  # change settings; cookies stay
p.wipe_history()                 # cookies, logins, history gone; settings stay
profile.delete("myprofile")      # the whole folder
print(profile.names())           # every profile; "default" is built in
```

#### Default profile

Built in and always there, no `create` needed. Every use is a new random identity: device, Firefox version and canvas seed.
It uses this computer's GPU, and nothing is kept after it closes.

```python
from ifox import Browser, profile

with Browser() as b: ...                                        # the default profile, this computer's connection
with Browser(proxy="https://user:pass@host:port") as b: ...     # clock and languages follow the proxy
with Browser(version="158", device="i5-1135g7-laptop") as b: ...   # fix any setting for this run
print(profile.default())                                        # what one use of it looks like
```

### Browser automation

```python
from ifox import Browser, profile

# Script the browser with the default profile
with Browser(proxy="https://user:pass@host:port") as b:   # the built-in default: new identity, nothing kept
    b.open("https://example.com/").click("text=Sign in")  # human mouse path, real click

# Or with a saved profile
p = profile.get("myprofile", proxy="https://user:pass@host:port")   # first run creates it, later runs load it

with Browser(p) as b:                            # same device, version and cookies every run
    tab = b.open("https://example.com/login")
    tab.type("#email", "a@example.com")          # human typing rhythm
    tab.press("Enter")
    tab.wait("#account")                         # waits until it appears
    print(tab.text("#account"))
    tab.frame("iframe#login").click("text=Continue")   # the same calls inside a frame
    print(tab.js("return document.title"))       # JavaScript the page can't see
    tab.shot("page.png")
    print(tab.check())                           # what the page sees, next to the profile
```

Save any of these as a `.py` file and run it with `python yourfile.py`, as in step 4 above.
Every setting and call: [docs/scripting.md](docs/scripting.md).

### Build it yourself

Only needed to change the browser itself. It takes about 90 minutes, in `D:\ifox`:

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
