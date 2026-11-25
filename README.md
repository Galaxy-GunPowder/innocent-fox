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

</div>

<br>

# Introduction

Innocent Fox is an anti-detect, identity-safe, fully scriptable browser, built by changing Firefox 160's source code directly.
Each profile can be Firefox 158, 159 or 160, identical to the official release in 7 fingerprint layers, from the TLS handshake to WebGL.

**Design goals:** fully scriptable from Python, no automation traces, and every layer of an identity agrees.<br>
**Changes:** 27 major changes for identity safety, in 13 patches. [Features](#features) · [Full list](docs/build-list.md)<br>
**Test results:** 6/6 public bot checkers passed, and Firefox 158, 159 and 160 each show 0 differences from official. [All results](#test-results)

- [Test results](#test-results)
- [How to use](#how-to-use)
- [Scripting](#scripting)
- [Features](#features)
- [Build it yourself](#build-it-yourself)
- [License](#license)
- [Special thanks](#special-thanks)

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
[Scripting](#scripting) shows what to put in your script.

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

# Scripting

A script is a Python file. Each line does one thing a person would do: open a page, click, type, read.
Every example here runs as it is: save it as a `.py` file and run `python yourfile.py`.

### Your first script

Search Wikipedia and print the start of the article.

```python
"""Search Wikipedia and print the first paragraph of the article."""
from ifox import Browser

with Browser() as b:                                   # start the browser (a new identity each run)
    tab = b.open("https://en.wikipedia.org/")          # open a tab at this address

    tab.type("input[name=search]", "Red fox")          # click the search box and type, like a person
    tab.press("Enter")                                 # press the Enter key

    tab.wait("#firstHeading")                          # wait until the article title is on the page
    print(tab.text("#firstHeading"))                   # the title's text
    print(tab.text("#mw-content-text p:not(.mw-empty-elt)"))   # the first paragraph's text
```

It prints:

```
Red fox
The red fox (Vulpes vulpes) is the largest of the true foxes, ...
```

### Point at things on a page

Every call that touches the page takes a selector: words that say which thing on the page you mean.

| Selector | Means | Example |
|---|---|---|
| `#name` | the thing with this id | `tab.text("#firstHeading")` |
| `tag[attr=value]` | a tag with this attribute | `tab.type("input[name=search]", "Red fox")` |
| `text=Words` | the thing that shows these words | `tab.click("text=Submit order")` |
| `a >> b` | b inside a: a frame or a shadow root | `tab.click("iframe#pay >> text=Pay")` |

To find an id or name: right-click the thing in Firefox, choose Inspect, and read its line.

### Waiting

Pages load in pieces. `tab.wait(sel)` pauses until the thing is on the page, up to 10 seconds, then raises an error.
After a click that changes the page, wait for something only the next page has. Text you just typed also counts as on the page.

### Fill in a form

```python
"""Fill in a web form and send it. httpbin.org is a public test site that shows what it received."""
import json
from ifox import Browser

with Browser() as b:
    tab = b.open("https://httpbin.org/forms/post")

    tab.type("input[name=custname]", "Alex Doe")             # a text box
    tab.type("input[name=custtel]", "555-0100")
    tab.type("input[name=custemail]", "alex@example.com")
    tab.click("input[value=medium]")                          # a round option button: Medium
    tab.click("input[value=cheese]")                          # a tick box: Cheese
    tab.type("textarea[name=comments]", "Ring the bell twice.")
    tab.click("text=Submit order")                            # the button, found by its words

    tab.wait("text=Raw Data")              # wait for something only the next page has
    tab.click("text=Raw Data")             # Firefox shows the reply in its JSON viewer; this tab is plain text
    sent = json.loads(tab.text("pre"))
    print(sent["form"])                    # just the form part
```

It prints what the site received:

```
{'comments': 'Ring the bell twice.', 'custemail': 'alex@example.com', 'custname': 'Alex Doe', 'custtel': '555-0100', 'delivery': '', 'size': 'medium', 'topping': 'cheese'}
```

### Save data from a page

```python
"""Save the top 10 Hacker News stories to a spreadsheet file (CSV)."""
import csv
from ifox import Browser

with Browser() as b:
    tab = b.open("https://news.ycombinator.com/")
    tab.wait(".titleline")

    # Read many things at once with JavaScript. It runs out of the page's sight.
    stories = tab.js("""
        return [...document.querySelectorAll(".titleline > a")]
            .slice(0, 10)
            .map(a => [a.textContent, a.href]);
    """)

with open("stories.csv", "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows([["title", "link"], *stories])
print(f"saved {len(stories)} stories to stories.csv")
```

`stories.csv` opens in Excel: one row per story, with its title and link.

### Stay signed in

A saved profile keeps cookies, so you sign in by hand once and every later run is signed in.

```python
"""Sign in to a site by hand once. Every later run starts already signed in."""
from ifox import Browser, profile

p = profile.get("github")                        # first run makes a saved profile, later runs load it

with Browser(p) as b:
    tab = b.open("https://github.com/login")
    if tab.exists("text=Sign in to GitHub"):     # the sign-in page: not signed in yet
        print("Sign in in the browser window, then close the window.")
        b.wait_closed()                           # cookies are saved when the window closes
    else:
        print("Already signed in.")               # the saved cookies did it
```

### Typing like a person

One call types a whole sentence or paragraph with real key presses, about 5 letters a second, never the same rhythm twice.
No JavaScript writes into the field, so the page sees a person typing.

```python
tab.type("textarea", "Hello.
This is a second line.")   # 
 presses Enter
tab.type("input[name=q]", "new words", clear=True)        # empty the field first
tab.type(None, "more")                                     # type where the cursor already is
```

### Every call

| Call | Does |
|---|---|
| `b.open(url)` | opens a tab at the address; gives back the tab |
| `tab.goto(url)`, `tab.back()`, `tab.reload()` | moves the tab like the address bar and buttons |
| `tab.click(sel)` | moves the mouse there like a hand, then clicks |
| `tab.type(sel, text)` | clicks the field, then types the text key by key |
| `tab.press("Enter")` | presses a key or keys together, such as `"Control+a"` |
| `tab.hover(sel)` | moves the mouse over it without clicking |
| `tab.upload(sel, "C:\cv.pdf")` | chooses a file for a file button, as a person picks one (next release) |
| `tab.wait(sel)` | waits until it is on the page |
| `tab.exists(sel)` | True or False, right away |
| `tab.text(sel)` | its words |
| `tab.title`, `tab.url` | the page title and address |
| `tab.js("return ...")` | runs JavaScript out of the page's sight, gives back the result |
| `tab.frame(sel)` | the same calls inside a frame |
| `tab.shot("page.png")` | saves a picture of the page |
| `tab.check()` | what the page sees about this browser, next to the profile |
| `b.wait_closed()` | keeps the script open until you close the window |

Every setting and call in detail: [docs/scripting.md](docs/scripting.md).

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

# Build it yourself

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
- And thank you for reading this. Don't forget to give me a thumbs up and spread the word. Here come the ads: feeling lonely? Try the AI companion at [Stagian.site](https://stagian.site). Need to block bots like this one? Try [Li-edge](https://lientertainment.site/li-edge), a TLS edge and firewall that spots them by their JA3 and JA4 fingerprints.
