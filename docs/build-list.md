# Build list

Everything Innocent Fox needs, grouped by goal. We write all of it before the first long build.
How: stock = Firefox already has a pref, patch = our C++/JS change, launcher = Python side, tunnel = Go helper.
The README's [Major changes](../README.md#major-changes) picks the most advanced finished items from this list, one line each.

## 1. Programmable control (Python)

You script in Python. Python talks to an agent inside the browser; the agent talks to C++ hooks.
Design: [control.md](control.md).

| # | Item | How |
|---|---|---|
| 1.1 | `ifox` Python package: launch profiles, open pages, click, type, evaluate | launcher |
| 1.2 | Agent inside the browser, privileged JS in the parent process, invisible to pages | done, patch 07 |
| 1.3 | Control over a pipe, not a TCP port, so pages can't find it by scanning localhost | done, patch 07 |
| 1.4 | WebDriver BiDi for Playwright, Puppeteer and Selenium; off by default, since it opens a port | stock |
| 1.5 | Script gate: every script (network, inline, eval, Function, workers) passes our rules before it runs | patch, SpiderMonkey compile hook |
| 1.6 | Gate rules run inside the content process: block, replace, regex-rewrite, no round trip | patch |
| 1.7 | Live mode: script source goes to a Python callback that returns the replacement | patch |
| 1.8 | Response rewrite: read and change any response body before the page parses it | patch, stock channel API |
| 1.9 | Request control: block, redirect, change headers, mock responses | patch |
| 1.10 | API trace: log which fingerprint APIs each script URL reads, with the values returned | patch |
| 1.11 | Our own page scripts run in an isolated world; the page can't see them | patch |
| 1.12 | Trusted input: mouse paths, typing rhythm and scrolling like a person's | done, `ifox/human.py` |
| 1.13 | Change fingerprint values live, without a restart | patch, pref observers |
| 1.14 | Several identities in one browser, one per container tab | patch, later stage |
| 1.15 | File upload: one file dialog answers with the given files, from the parent process; the page sees a normal choice | done, `Tab.upload` |

## 2. Running hidden without headless leaks

Detectors such as Cloudflare and PerimeterX flag software rendering (SwiftShader, WARP) and headless screens.
So we run a normal window on a hidden Windows desktop: same GPU, same rendering.

| # | Item | How |
|---|---|---|
| 2.1 | Start the browser on a hidden Windows desktop (CreateDesktop) | launcher |
| 2.2 | `document.hidden` false, `visibilityState` "visible" while hidden | stock occlusion pref off; patch only if the build test fails |
| 2.3 | No timer or requestAnimationFrame slowdown while hidden | stock occlusion pref; test rendering on a hidden desktop after the build |
| 2.4 | `document.hasFocus()` true, focus and blur events stay consistent | stock `focusmanager.testmode` |
| 2.4b | If GPU rendering stops on a hidden desktop: an off-screen window on the real desktop instead | launcher |
| 2.5 | Linux later: Xvfb with a real GPU | launcher |
| 2.6 | Measure `-headless` against a visible window: CreepJS, WebGL renderer, pixel hashes, screen and window sizes | tests |

## 3. Automation traces removed

| # | Item | How |
|---|---|---|
| 3.1 | `navigator.webdriver` false, in pages and workers | patch |
| 3.2 | Remote agent leaves page-visible prefs unchanged | stock `remote.prefs.recommended` false |
| 3.3 | No extension installed, so no moz-extension:// traces | rule |
| 3.4 | Our JS never touches page prototypes, so toString checks find nothing | rule |
| 3.5 | Page never gets input while hidden or unfocused: driven windows act as the front window | done, stock prefs |
| 3.6 | Mouse, wheel and keys enter through the top window and APZ, like OS input, not flagged as test events | done, patch 07 |
| 3.7 | Wheel events still carry Firefox's internal test flag (chrome-only, pages can't read it) | patch, later |

## 4. Version range

One build claims any recent Firefox version, picked per profile with `ifox.version`.
The engine must be the newest claimed version: features can be hidden, never added.
Range: latest release down 6 releases, plus the current ESR. Today: 154 to 160, and ESR 153.

| # | Item | How |
|---|---|---|
| 4.1 | Measure each real Firefox version: download its official build, run our probes locally | scripts |
| 4.2 | Feature probe: every global, prototype member, CSS property and JS builtin | tests |
| 4.3 | TLS probe: a local server records the full ClientHello (JA3, JA4, extension order) | scripts |
| 4.4 | HTTP probe: HTTP/2 settings, header order, Accept and Priority headers per request type | scripts |
| 4.5 | Results stored as `data/versions/<version>.json`, never hand-written | data |
| 4.6 | UA, appVersion and buildID follow the claimed version | stock overrides |
| 4.7 | WebIDL APIs newer than the claimed version disappear, generated from 4.5 | patch, binding codegen |
| 4.8 | JS builtins newer than the claimed version disappear at global creation | patch, SpiderMonkey |
| 4.9 | CSS properties newer than the claimed version disappear | stock `layout.css.*` prefs + patch |
| 4.10 | TLS ClientHello rebuilt to the claimed version's measured one | patch, NSS |
| 4.11 | HTTP/2 settings and headers set to the claimed version's | patch, necko |
| 4.12 | Switching version applies on the next page load; open connections are closed | patch |
| 4.13 | Check: our build with version X gives the same probe results as real Firefox X | tests |
| 4.14 | Rebase onto each new release, so the range moves forward every 4 weeks | scripts |

Limit: new syntax (not APIs) can't be hidden, and old bugs aren't recreated. Detectors rarely test either.

## 5. Network and VPN

Proxies first: each profile has its own proxy, and nothing leaves around it.
If the proxy drops, pages fail; they never fall back to your real address.
The WireGuard VPN tunnel (5.1 to 5.3, 5.10, 5.11, 5.15) comes later, for VPN providers.

| # | Item | How |
|---|---|---|
| 5.1 | `ifox-tunnel`: one Go process per profile, WireGuard in userspace, no admin rights | later; tunnel, wireguard-go + gVisor netstack |
| 5.2 | Ships inside the browser folder; the browser starts and stops it, nothing to install | patch + tunnel |
| 5.2b | Browser reaches the tunnel over a named pipe, so pages find no open localhost port | tunnel, check Firefox SOCKS pipe support |
| 5.2c | Many browsers at once: each has its own tunnel, config and exit IP | tunnel |
| 5.3 | Import any WireGuard `.conf` from a VPN provider | tunnel |
| 5.4 | HTTPS, HTTP and SOCKS5 proxies with login; 5 common text formats; HTTPS preferred (login encrypted) | done, `ifox/network.py`, login via the agent |
| 5.4b | HTTP proxy login without the person-facing prompt | done, patch 09 |
| 5.5 | Kill switch: no direct route, `network.proxy.failover_direct` false | stock |
| 5.6 | DNS only through the proxy: Firefox resolves just the proxy's own name (tested on Decodo) | done, stock `socks_remote_dns` |
| 5.6b | Provider gateway lookups show where you are: Decodo's entry server near you (Singapore) asks Cloudflare Singapore | later, provider side: US relay, other provider, or DoH through the proxy (`remoteDns=False`, unreliable on home exits) |
| 5.7 | IPv6 off unless the tunnel carries it | stock |
| 5.8 | HTTP/3 off, since UDP would skip the tunnel | stock |
| 5.9 | WebRTC behind a proxy: no UDP of its own, real IP never shown (CreepJS: "blocked", 0 IPs) | done, stock `proxy_only` via `ifox.Browser(proxy=...)` |
| 5.9b | WebRTC UDP through the proxy or tunnel (SOCKS5 UDP ASSOCIATE), so STUN shows the exit IP instead of "blocked" | patch, needs 5.1 |
| 5.9c | Direct profiles keep stock WebRTC: the STUN IP is the same IP the site already sees | done, rule |
| 5.10 | TCP packets look like Windows: TTL 128, window 64240, Windows option order | tunnel, netstack settings |
| 5.11 | Report: connected, last handshake, bytes, exit IP, country and city, checked through the tunnel | tunnel |
| 5.12 | Exit sets the profile's timezone: asked through the proxy at start, no page opened (`b.exit`) | done for timezone; language and location later |
| 5.13 | Leak test on a real proxy: exit IP, WebRTC, local DNS, DNS server country, login never sent to sites, CreepJS (`tests/real/run_decodo.py`) | Decodo fails DNS server country (5.6b); rest pass |
| 5.13b | Home exits differ: some refuse new connections above ~10 at once (Decodo 522 / SOCKS reply 4) | measured; retry or cap later |
| 5.14 | Real IP is checked once on your machine, kept locally, never sent anywhere | launcher |
| 5.15 | Auto-reconnect; the browser waits rather than going direct | tunnel |
| 5.16 | Background requests pages can't see are off: 33 idle hosts down to 8 | done, stock prefs in `QUIET` |
| 5.16b | Kept, since pages can tell: media plug-ins, push, Safe Browsing, tracker lists, remote settings | rule |
| 5.16c | Find why an idle blank tab still looks up www.google.com | check |
| 5.17 | `goto`, `back`, `reload` raise `LoadError` when a page fails (host not found, refused) | done |

Why 5.10 matters: with a plain proxy, sites see the proxy server's Linux TCP stack under a Windows UA.
Our tunnel makes the packets itself, so it can match Windows.
Limit: datacenter VPN IPs have a bad reputation on many sites; residential exits score better.

## 6. Machine fingerprint (one real device per profile)

Every value is changed in C++, in pages, iframes and all worker types alike.
CreepJS compares those against each other.

| # | Item | How |
|---|---|---|
| 6.1 | navigator: userAgent, platform, oscpu, appVersion, buildID | stock overrides, check workers |
| 6.2 | navigator.hardwareConcurrency, maxTouchPoints | patch |
| 6.3 | Languages and Intl default locale, number and date formats | stock + patch |
| 6.4 | Timezone in Date and Intl, in workers too | launcher `TZ` + patch |
| 6.5 | screen size, avail size, colorDepth, devicePixelRatio | patch |
| 6.6 | CSS media queries (device-width, resolution) match the screen values | patch |
| 6.7 | Window outer size and position fit inside the fake screen | patch + launcher |
| 6.8 | WebGL vendor and renderer | stock overrides |
| 6.9 | WebGL parameters and extensions for the claimed GPU (shader precision is the same on all D3D11 GPUs) | patch 05 |
| 6.10 | WebGPU adapter info matches the claimed GPU | patch |
| 6.11 | Claim only GPUs of the host's vendor and family: WebGL pixels come from the real GPU, and detectors match pixels to GPU names | launcher, data |
| 6.12 | WebGL pixel hash (CreepJS "pixels") stayed the same with WebGL noise on: find out why | patch |
| 6.11 | Font list per OS, with matching text widths | stock whitelist + bundled fonts |
| 6.12 | Speech voices list | patch |
| 6.13 | Media devices: count and kinds of cameras, mics, speakers | patch |
| 6.14 | Color scheme, reduced motion, contrast, accent color | patch |
| 6.15 | Permissions start as a fresh install's | stock |
| 6.16 | Keyboard layout follows the host; launcher warns on a mismatch | launcher |

## 7. Random by default

Each new profile gets a random real device, version and exit, then keeps them forever.

Found in the source: stock Firefox 160 already adds canvas noise for every desktop user, new each session.
It also reports avail height as screen height minus 48, and collapses touch points above 1 to 5.
So our values go underneath these built-in protections, never around them, and the output looks like stock 160.

| # | Item | How |
|---|---|---|
| 7.1 | Canvas noise stays stock; its key comes from `ifox.noise.seed`, so it stays the same across restarts | patch, nsRFPService session key |
| 7.2 | Empty seed = stock behaviour, a new key each session | patch |
| 7.3 | WebGL readPixels noise, using Firefox's own WebGLRandomization | stock baseline overrides pref |
| 7.4 | No audio noise: Firefox uses the same SSE4.2 audio code on nearly every x64 CPU, so noise would make us unique | decision |
| 7.4b | Audio sample rate (44100 or 48000) from the device data | stock `media.cubeb.force_sample_rate` |
| 7.5 | GPU mode, fake or real, chosen per profile | launcher |
| 7.6 | Fake: claim another real GPU from the dataset, add WebGL noise | launcher |
| 7.7 | Real: claim the host GPU, no WebGL overrides, exactly stock Firefox | launcher |
| 7.8 | Real mode only picks devices with the host's GPU, so cores and screen still fit | launcher |
| 7.9 | Each claimed version gets the protections that version shipped with | data, from 4.5 |

Turning canvas noise off would make a profile look less like real Firefox 160, not more.

## 8. Writing automations

Test case: sign up for an account on a real site, by script and by AI.

| # | Item | How |
|---|---|---|
| 8.1 | Element picker: hover lights up an element and shows its best locator; click copies it or sends it to Python | patch, overlay page scripts can't see |
| 8.2 | Recorder: do a task once by hand, get a Python script back | agent + launcher |
| 8.3 | Locators by role and label first, then stable attributes, then CSS, all stored per step | launcher |
| 8.4 | Report when a stored locator stops matching, and which fallback worked | launcher |
| 8.5 | Every action waits until its element is visible, enabled and still | agent |
| 8.6 | Locators reach into iframes and shadow DOM | agent |
| 8.7 | AI view: numbered list of the page's controls plus a screenshot; "type into 12" | agent |
| 8.8 | Pause for a person (CAPTCHA, unexpected page), notify, then resume | agent + launcher |
| 8.9 | Read verification codes from your own inbox over IMAP | launcher |

## 9. Data and testing

| # | Item | How |
|---|---|---|
| 9.1 | Device dataset measured from real machines, never invented | data |
| 9.2 | Self-test: run CreepJS and other checkers, report every leak | launcher + tests |
| 9.3 | Each patch has a test page that proves its value changed in pages, iframes and workers | tests |
| 9.4 | Detector bench: open real protected pages with the API trace (1.10) on; record what each detector script reads and whether it lets us through | tests |
| 9.5 | Save a detector script once, replay it locally through the script gate (1.7), so fixes are tested without hitting the site | tests |
| 9.6 | Pipe test: a sign-up page records event trust, mouse moves, key codes, added globals, port 2828 | tests/pipe |
| 9.7 | WebRTC leak test: direct finds the real IP, proxied runs show no address at all | tests/webrtc |
| 9.8 | Identity lab: local TLS, HTTP/2 and HTTP/1.1 servers compare our build with official Firefox, no outside sites | done, tests/identity |
| 9.9 | Bot lab: the same page opened by hand and by script; any difference is an automation trace | done, tests/identity/bot.py |

## 10. Upkeep

| # | Item | How |
|---|---|---|
| 10.0 | Assembled versions: one 160 build shows 158 or 159 through `ifox.compat.*` switches; only lab-verified versions are offered | done, patch 12 + ifox/versions.json |
| 10.1 | Package a portable zip: browser, tunnel, launcher | scripts |

## 11. Adorea built in (from 2026-11-24)

Adorea moves from a separate Chrome extension into Innocent Fox. Box 1 stays the brain; the browser carries the panel, the hands and a command channel.
This repo keeps only the open hooks (sidebar slot, pipe verbs). Adorea's own code is closed and ships in a separate Adorea download, not on GitHub.

| # | Item | How |
|---|---|---|
| 11.0 | Two downloads from one build: Innocent Fox, and Innocent Fox with Adorea (same browser plus one closed Adorea pack). A public hook loads the pack only if it is present and signed with our key | browser + scripts |
| 11.1 | Adorea panel in the browser's own sidebar: sign in, profiles, Apply, Bulk; screens reused from the extension | browser chrome |
| 11.2 | Driver on the pipe agent verbs (find, mouse, key, js, shot) in place of `chrome.scripting` and `chrome.debugger` | agent |
| 11.3 | Command channel: `adorea` verbs on the agent pipe (apply, bulk, stop, status), so Python and any outside AI can run it | agent + launcher |
| 11.4 | Off by default, one profile setting turns it on; identity and bot labs must still show 0 differences with it on | profile + tests |
| 11.5 | Page reader: the browser's own view of a page (controls, labels, layout, screenshot) as one compact input for a model | agent |
| 11.6 | Tiny model, step 1: name each form field (email, first name, salary...) from the page reader; trained on box 1 turn logs | data + training |
| 11.7 | Tiny model, step 2: plain commands ("register here with test values") become pipe verbs; box 1's model takes what it can't do | data + training |

## 12. Planned: speed and typing (from 2026-11-25)

The rule for every item: nothing a page can see or measure may change. A change that saves memory but shows to a page is dropped.
Each item is measured before and after, and the identity lab must still show 0 differences.

### Lighter and faster

| # | Item | How |
|---|---|---|
| 12.1 | Measure first: memory per open profile, start time, page load time, against official Firefox 160 on the same PC | tests/perf/bench.py: 412 ms official, 556 ms ours, 888 MB and 699 MB |
| 12.2 | Build like official: PGO and LTO, two compiler steps official Firefox uses to make the same code run faster. Ours has neither. Speed only: every value a page reads is already the same | build |
| 12.3 | No spare content process waiting in the background (`dom.ipc.processPrelaunch`); one less process per window, never seen by a page | done, `PERF` in the launcher; identity lab check after the 12.2 build |
| 12.4 | Smaller memory and disk caches for the default profile, which is deleted on close anyway | not tried yet: 12.3 and 12.5 already cut 38 MB and 3 processes |
| 12.5 | Firefox's local AI models, sync, and new-tab feeds never load in a driven window | done, `PERF` in the launcher; identity lab check after the 12.2 build |
| 12.6 | Kept on purpose: the back-forward cache, JIT, workers, WebGL and fonts. Pages can tell when these are off | none |

### Typing

`tab.type()` already types any sentence or paragraph with real key presses, about 5 letters a second, in a random rhythm.
These items add choice, so a script doesn't have to time keys itself.

| # | Item | How |
|---|---|---|
| 12.7 | Speed per profile: each saved profile keeps its own typing speed and rhythm, like a real person | done, `human.Typist` from the profile's seed |
| 12.8 | `speed=` to set it for one call, from slow to fast, and `speed="instant"` for long text where timing doesn't matter | done |
| 12.9 | Word rhythm: short pauses between words, longer ones after commas and sentences, quicker runs on common letter pairs | done |
| 12.10 | `mistakes=`: a share of typos, each fixed with Backspace, as people do | done |
| 12.11 | `paste=True`: puts the text on the clipboard and presses Control+V, as people do with long text | done; the clipboard's text is put back |
