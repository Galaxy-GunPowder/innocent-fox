# Control channel

Python drives the browser over a private pipe. No port, no injected page script.

## How Firefox talks to itself

| Part | What it is |
|---|---|
| Parent process | One per browser: window, tabs, network, prefs |
| Content processes | Pages run here; each site gets its own process, iframes from other sites too |
| Window actors | A parent half and a child half for every page and every iframe, talking by messages |

Window actors are how Firefox's own password manager and autofill reach into pages.
Marionette and WebDriver BiDi are a TCP server in the parent process that uses those same actors.
We keep the actors and drop the TCP server.

```
Python ── pipe ──> parent process: agent ── actor messages ──> page / iframe (child half)
```

## The pipe

1. The launcher makes an anonymous pipe pair and starts Firefox with `-ifox-pipe <in>,<out>`.
2. Patch: a small C++ reader thread hands each message to the agent, a privileged JS module.
3. The agent answers on the same pipe.

Only the launcher holds the other end. No other process, and no page, can open it.

## What a page can see

| Marionette leak | Innocent Fox |
|---|---|
| TCP port 2828 open on localhost | No port at all |
| `navigator.webdriver` true | false (patch 02) |
| Dozens of prefs flipped at start | None |
| Remote agent running, `-marionette` flag | Never started |
| Script runs in the page | Child half runs in a privileged scope; no globals, ignores prototypes the page patched |
| Clicks are DOM events with no real pointer | Native OS-level events: hover, focus and `isTrusted` behave like a real mouse |

WebDriver BiDi (build list 1.4) stays off. It opens a port, so it is for debugging only.

## Python API

Plain sync calls. Async version later, same names.

```python
from ifox import Browser

with Browser("alice", place="UK", vpn="wg/uk1.conf") as b:   # launches, pipe ready, no connect step
    tab = b.open("https://example.com/signup")               # waits for load
    tab.type("#email", "a@example.com")                      # moves, clicks, types like a person
    tab.click("text=Create account")
    tab.wait("text=Check your email")

    pay = tab.frame("iframe#payment")                        # same API inside a frame, any origin
    pay.type("#card", "4242 4242 4242 4242")
    tab.click("iframe#captcha >> .checkbox")                 # or reach in with >>

    tab.js("return document.title")                          # private scope, page can't see it
    tab.on_script(r"fp\.js", lambda src: src.replace("x", "y"))   # rewrite before the page runs it
    tab.on_response("*/api/*", print)

    other = b.open("https://mail.example.com")               # second tab; nothing to switch
```

### Why it is simpler than CDP

| CDP pain | Here |
|---|---|
| Connect a WebSocket, one per tab, reconnect after navigation | No connecting; one pipe for the whole browser |
| Switch to a tab or frame before acting | Tabs and frames are objects; each call names its target |
| Node IDs go stale after the page re-renders | Selectors, looked up again on every call |
| Add frame offsets by hand to click inside an iframe | The browser knows where every frame is on screen |
| Write your own waits | Every action waits until its element is visible, enabled and still |
| Shadow DOM needs its own calls | `>>` steps into iframes and shadow roots alike |

### Selectors

| Form | Example |
|---|---|
| CSS | `#email`, `button.primary` |
| Visible text | `text=Create account` |
| Role and name | `role=button[name="Sign up"]` |
| Into a frame or shadow root | `iframe#pay >> #card` |

## Wire format

One message per line, JSON. Python never needs to know process or actor details.

```
-> {"id": 7, "to": "tab:2/frame:5", "do": "click", "args": {"sel": ".checkbox"}}
<- {"id": 7, "ok": true}
<- {"event": "response", "tab": 2, "url": "...", "status": 200}
```

| Verb | Does |
|---|---|
| `open`, `close`, `tabs` | Tabs |
| `goto`, `back`, `reload`, `wait` | Pages |
| `click`, `type`, `press`, `hover`, `scroll`, `drag` | Input, as native events |
| `find`, `text`, `attr`, `html`, `shot` | Read the page |
| `js` | Run code in the private scope |
| `rule` | Script gate and request or response rules |
| `prefs` | Change fingerprint values live |

## Status

| Step | State |
|---|---|
| C++ pipe and `-ifox-pipe` flag | done, patch 07 |
| Agent and per-frame actor: open, goto, find, mouse, wheel, key, js, shot, prefs | done, patch 07 |
| Python `ifox` package, frames and `>>`, shadow DOM | done |
| Pipe test (`tests/pipe/run_pipe.py`), smoke and CreepJS driven over the pipe | done |
| Script gate and response rules (`on_script`, `on_response`) | next |
| Element picker (build list 8.1) | later |

Debugging only: `b.call("chrome", code="return win.gBrowser.tabs.length")` runs code in the parent process.
