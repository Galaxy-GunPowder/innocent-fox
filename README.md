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

# Contents

<div align="center">

<a href="#introduction">Introduction</a> &nbsp;·&nbsp; <a href="#major-changes">Major changes</a> &nbsp;·&nbsp; <a href="#how-to-use">How to use</a> &nbsp;·&nbsp; <a href="#tests">Tests</a> &nbsp;·&nbsp; <a href="#license">License</a>

<sub><a href="#design-goals">Design goals</a> &nbsp;·&nbsp; <a href="#how-it-works">How it works</a> &nbsp;·&nbsp; <a href="#test-results">Test results</a> &nbsp;·&nbsp; <a href="#download">Download</a> &nbsp;·&nbsp; <a href="#your-first-script">First script</a> &nbsp;·&nbsp; <a href="#common-calls">Common calls</a> &nbsp;·&nbsp; <a href="#build-it-yourself">Build it yourself</a></sub>

</div>

<br>

# Introduction

Innocent Fox is a version of Firefox 160 for running many separate online identities from Python.
Each profile keeps its own settings, cookies, logins and internet connection, and to a website it looks like an ordinary person on an ordinary computer.

### Design goals

| Goal | What it means |
|---|---|
| Fully scriptable | Python controls every page, frame, click and keystroke |
| Bot detection countered | Pages find no automation traces: no webdriver flag, no control port, no injected code |
| Identity secured | Proxy, TLS handshake, graphics card and device values all describe the same person; TLS is Firefox 160's own, so it matches |
| Profile-based identities | Each new profile gets a random real device, then keeps it; the built-in default profile is new every run |

### How it works

- **A private channel replaces the automation port.** Python and the browser talk over a Windows named pipe with a new random name each launch. It accepts one local connection, refuses remote ones, and opens no network port; the test checks that the usual automation port, 2828, stays closed.
- **The control code is built into the browser.** The part that carries out your commands is compiled into the browser and runs with browser privileges, outside the page. No extension is installed and nothing is injected into pages.
- **Your scripts run in a sandbox.** JavaScript you run with `tab.js()` sees the page, but the page can't see it.
- **Input takes the real path.** Clicks and key presses enter through the browser window like input from the operating system, so pages receive trusted events. Mouse paths and typing are timed like a person's.
- **Fingerprint values live in the engine.** Patched browser code reads each value from the profile's settings, which pages can't read, and returns it everywhere the value is asked for, workers included. There are no JavaScript overrides to find.
- **The proxy is the only way out.** The proxy login travels over the private channel and is never written into browser settings. DNS goes through the proxy, WebRTC is limited to the proxy, and there is no fallback to your own connection.
- **The clock follows the exit.** At start, the browser asks through the proxy where its traffic leaves, without opening a page, and sets the time zone and languages to match.

### Test results

Public bot and fingerprint checkers, run on 21 November 2026 with the built-in default profile through a US residential proxy:

| Checker | What it looks for | Result |
|---|---|---|
| [CreepJS](https://abrahamjuliot.github.io/creepjs/) | Headless and stealth signs, faked values | 0% headless, 0% stealth, no faked values found |
| [BotD](https://fingerprintjs.github.io/BotD/main/) by Fingerprint | 18 bot detectors | "You are not a bot", 18 of 18 clear |
| [Device and Browser Info](https://deviceandbrowserinfo.com/are_you_a_bot) | 22 automation signals | "You are human", 0 of 22 found |
| [BrowserScan](https://www.browserscan.net/bot-detection) | 17 bot and automation checks | All 17 "Normal" |
| [Pixelscan](https://pixelscan.net/fingerprint-check) | Fingerprint consistency, proxy use | "Fingerprint is consistent", "No proxy detected" |
| [Sannysoft](https://bot.sannysoft.com/) | 24 scored bot checks | 23 of 24 pass; the one miss is a Chrome-only check every Firefox fails |
| WebRTC leak test, in this repo | Your real IP through WebRTC | 6 of 6 pass, no address shown |
| Real proxy test, in this repo | Exit IP, WebRTC, DNS, login | 10 of 11 pass; DNS servers show Singapore next to a US exit, caused by the proxy provider's entry server |

<br>

# Major changes

These are the main changes; the full list is in [docs/build-list.md](https://github.com/Galaxy-GunPowder/innocent-fox/blob/main/docs/build-list.md).

| Category | What we did |
|---|---|
| Scripting | Python controls the browser through a private channel, not an automation port |
| Scripting | Mouse and keyboard use the normal input path, with human mouse paths and typing rhythm |
| Scripting | Selectors reach into frames, including other sites' payment frames, and shadow DOM |
| Bot detection | `navigator.webdriver` is always false, in pages and workers |
| Bot detection | Your scripts run in a sandbox the page can't see |
| Bot detection | Driven windows act as the front window, so pages never switch to hidden |
| Proxy | HTTPS, HTTP and SOCKS5 proxies with login, pasted in any of 5 common formats |
| Proxy | Time zone and languages follow the proxy's country |
| Proxy | WebRTC goes through the proxy only; sites see 0 addresses |
| Proxy | DNS lookups go through the proxy |
| Proxy | Kill switch: if the proxy drops, pages stop loading instead of using your connection |
| Proxy | HTTP proxy login is sent without a prompt |
| Fingerprint | 15 device values set inside the engine, such as screen, display scale, CPU cores and touch |
| Fingerprint | Graphics card name, WebGL limits and extensions match the claimed card |
| Fingerprint | Canvas noise key kept per profile, so a profile looks the same after restarts |
| Fingerprint | Windows "Text size" no longer changes the display scale pages see |
| Profiles | Saved profiles keep the same device, cookies and logins every run |
| Profiles | Built-in default profile: a new random device every run, nothing kept |
| Profiles | `print(p)` shows every setting plus session history: proxies, countries, websites |
| Profiles | Wiping history keeps every setting |
| Background | Idle background connections cut from 33 addresses to 8 |
| Install | The browser downloads itself on first use and closes when your script ends |

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

Run these from the repo folder. The public checkers above are listed under [Test results](#test-results).

| Test | Command | Result |
|---|---|---|
| Smoke | `python tests/smoke/run_smoke.py` | 20 of 20 |
| Control pipe | `python tests/pipe/run_pipe.py` | 21 of 21 |
| WebRTC leak, local test proxy | `python tests/webrtc/run_webrtc.py` | 6 of 6 |
| CreepJS | `python tests/creep/run_creep.py` | 0% headless, 0% stealth |
| Real proxy (needs `IFOX_PROXY_FILE`) | `python tests/real/run_decodo.py` | 10 of 11, DNS server country fails |

<br>

# License

<div align="center">

MPL 2.0 &nbsp;·&nbsp; Not made or endorsed by Mozilla &nbsp;·&nbsp; <a href="NOTICE.md">Notice</a>

<sub>Use it only on sites and accounts where you're allowed to.</sub>

</div>
