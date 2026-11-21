# Scripting Innocent Fox

Python drives the browser over a private pipe. Pages can't see it.

## Start

The first `Browser()` downloads the built browser (130 MB) once into `%LOCALAPPDATA%\InnocentFox`.
`ifox-install` does the same ahead of time. `IFOX_HOME` moves that folder.

```python
from ifox import Browser, LoadError

PROXY = "https://user:pass@us.decodo.com:10001"   # or socks5h://..., http://..., host:port:user:pass

with Browser("alice", proxy=PROXY) as b:          # "alice": saved profile, same device every run
    tab = b.open("https://example.com/login")
    tab.type("#email", "a@example.com")           # human-like typing
    tab.click("text=Sign in")                      # human-like mouse path, real click
    tab.wait("#dashboard")
    print(tab.title, tab.url)
```

`Browser()` with no name uses the built-in `default` profile, covered below.

## Profiles

A profile is a folder of cookies and logins, plus `ifox-profile.json` with its settings.
Full tour of every setting and call: [examples/profiles.py](../examples/profiles.py).

```python
from ifox import Browser, profile

p = profile.create("shop1", proxy=PROXY, device="i5-1135g7-laptop")   # saved
p.update(langs=["pt-BR", "pt", "en"])        # change saved settings; cookies stay
p.wipe_history()                             # cookies, logins, history, cache gone; settings stay
profile.delete("shop1")                      # the whole folder

with Browser("shop1") as b: ...              # a saved profile
with Browser("shop1", timezone="Asia/Tokyo") as b: ...   # other settings for this run only
with Browser(proxy=PROXY) as b: ...          # the built-in default: random every run, nothing saved
with Browser(proxy=PROXY, device="i7-12700-gtx1660") as b: ...   # the default with one setting fixed
```

The `default` profile is always there and needs no `create`. Every use gets a new random device, screen, scale and canvas seed. It uses this computer's real GPU, and its folder is deleted on close. `Browser()`, `Browser("default")` and `profile.load("default")` all give it; `wipe_history`, `delete` and `create` refuse it.

| Setting | Default | Does |
|---|---|---|
| `proxy` | none | IP and country; also `--proxy-file` style files via `ifox.desktop.proxy_from_file` |
| `timezone` | `"auto"` | the exit's clock, every start (no proxy: this computer's); or `"America/Chicago"` |
| `langs` | `"auto"` | the exit country's languages, fixed at first start; or `["en-US", "en"]` |
| `device` | random | one real machine from `profile.DEVICES`: cores, screen, scale, GPU together |
| `cores`, `screen`, `dpr`, `gpu` | the device's | override one value; only copy another real machine |
| `touch` | 0 | touch points |
| `gpu_mode` | `"fake"` (`default`: `"real"`) | `"real"` = this computer's GPU |
| `seed` | random, kept | canvas noise key |
| `prefs` | `{}` | extra Firefox prefs |

Also: `profile.load(name)`, `profile.get(name)` (load or create), `profile.names()`, `profile.exists(name)`.
Every call returns the profile; `print(p)` shows its full detail (settings, what pages see, history size),
`p.details()` gives the same as a dict. `delete` returns what it deleted.
With history it also shows sessions, countries and proxies used, sites visited and sites with cookies.
Full lists: `p.sessions()` (every run: proxy, exit ip, country, city, clock), `p.visits()`, `p.sites()`, `p.cookie_sites()`.
`wipe_history()` empties all of these and keeps every setting, device and seed included.
The proxy login is never shown. Wipe and delete refuse while the profile is open.
The proxy login is stored in plain text in `ifox-profile.json`; the browser never reads that file.
Folders: `D:\ifox\profiles` on the build machine, else `%LOCALAPPDATA%\InnocentFox\profiles`.

## Closing

The browser ends with your script, however it ends: finished, error, Ctrl+C, window closed, killed.
`with` (or `b.close()`) quits it cleanly so cookies are saved first.

## What you can call

| Call | Does |
|---|---|
| `b.open(url)` | page in a new tab (first call reuses the blank start tab) |
| `tab.goto(url)`, `back()`, `reload()` | navigate; `LoadError` if the page fails (host not found, refused) |
| `tab.find(sel)`, `wait(sel)`, `exists(sel)`, `text(sel)` | elements; `wait` raises after `timeout` seconds if it never appears |
| `tab.click(sel)`, `hover(sel)`, `type(sel, text)`, `press("Control+a")` | input like a person, through the OS input path |
| `tab.frame("iframe#pay")` | the same calls inside an iframe, cross-site too |
| `tab.js("return document.title")` | run JS in a private sandbox the page can't see |
| `tab.check()` | what the page sees next to the profile, value by value; `.ok` is False on any difference |
| `tab.seen()` | what the page sees, as a dict (clock, langs, cores, screen, dpr, touch, gpu, user agent) |
| `tab.shot("page.png")` | screenshot |
| `b.set_prefs(**{"ifox.timezone": "America/Chicago"})` | change a fingerprint value live |
| `b.wait_closed()` | block until a person closes the window |

Selectors: CSS, `text=Sign in`, `text="exact"`, and `a >> b` to step into shadow roots and frames.

## Several at once

Each `Browser` is its own process, profile, fingerprint and proxy:

```python
a = Browser("shop1", proxy="https://user-NAME-country-us:pass@gate.decodo.com:10301")
b = Browser("shop2", proxy="https://user-NAME-country-br:pass@gate.decodo.com:10302")   # Brazil: pt-BR, São Paulo clock
```

## By hand

`ifox-open --name main --proxy-file decodo_proxy.txt` opens profile `main` for a person to use,
clock set to the exit's timezone. A desktop shortcut can run the same command.
