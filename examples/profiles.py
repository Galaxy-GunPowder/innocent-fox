"""Every profile setting and every profile call, in one script.

  python profiles.py                                   your own connection
  python profiles.py --proxy https://user:pass@us.decodo.com:10001
  python profiles.py --proxy-file decodo_proxy.txt     same, read from a file

Part 1 works on the profile alone (no browser opens). Part 2 opens browsers.
Every profile call returns the profile; print() shows its full detail.
"""
import argparse

from ifox import Browser, profile
from ifox.desktop import proxy_from_file

ap = argparse.ArgumentParser()
ap.add_argument("--proxy")
ap.add_argument("--proxy-file")
a = ap.parse_args()
PROXY = proxy_from_file(a.proxy_file) if a.proxy_file else a.proxy      # None = no proxy


# ---------------------------------------------------------------- 1. Profile only

# Every setting, its default, what it does.
for name, default in profile.DEFAULTS.items():
    print(f"  {name:9} default {default!r:8}  {profile.HELP[name]}")
print("  devices:", profile.DEVICES)

# Create: every setting written out.
p = profile.create(
    "example-shop",
    overwrite=True,              # replace it if it already exists
    proxy=PROXY,                 # None = this computer's own connection
    timezone="auto",             # the proxy exit's clock, looked up every start; or "America/Chicago"
    langs="auto",                # the exit country's languages, fixed at first start; or ["en-US", "en"]
    version=None,                # Firefox version websites see; None = 158, 159 or 160 at random, then kept
    device="i5-1135g7-laptop",   # one real machine from profile.DEVICES; None = random
    cores=None,                  # None = the device's own value; set only to copy another real machine
    screen=None,                 # e.g. (1920, 1080), device pixels
    dpr=None,                    # e.g. 1.25
    gpu=None,                    # e.g. ("Google Inc. (Intel)", "ANGLE (Intel, ...)")
    touch=0,                     # touch points; 0 = no touch screen
    gpu_mode="fake",             # "fake" = the device's GPU; "real" = this computer's
    seed=None,                   # canvas noise key; None = random once, then kept
    prefs={},                    # extra Firefox prefs, {"name": value}
)
print("\ncreate:\n", p, sep="")

# Load a saved one.
p = profile.load("example-shop")
print("\nload:\n", p, sep="")

# Change saved settings. Cookies and history stay.
p = p.update(langs=["en-US", "en"], touch=0)
print("\nupdate:\n", p, sep="")

# Load it, or create it if it doesn't exist yet.
# p = profile.get("example-shop", proxy=PROXY)

# All profiles: the built-in "default" first, then the saved ones.
print("\nnames:", profile.names())

# The built-in default: always there, nothing to create. A new random device, screen,
# scale and canvas seed every use, this computer's real GPU, nothing kept after close.
print("\ndefault:\n", profile.load("default"), sep="")     # same as profile.default()

# Wipe history: cookies, logins, history, cache gone. Settings and device stay.
# p = p.wipe_history()
# print("\nwipe_history:\n", p, sep="")

# Delete the whole profile, settings included.
# print("\ndelete:", profile.delete("example-shop"))


# ---------------------------------------------------------------- 2. Browser

# A saved profile. The site sets a cookie (like a login); the profile keeps it.
with Browser("example-shop") as b:
    if b.exit:
        print("\nexit:", b.exit["country"], b.exit["city"], b.exit["timezone"])
    tab = b.open("https://example.com/")
    print("what the page sees, next to the profile:")
    print(tab.check())                     # tab.seen() gives the same values as a plain dict
    tab.js("document.cookie = 'login=yes; max-age=86400'")
print("\nafter the browser:\n", profile.load("example-shop"), sep="")   # history now has cookies

# The same profile with other settings for this run only; the saved ones stay.
with Browser("example-shop", timezone="Asia/Tokyo") as b:
    print("\nthis run only, page clock:", b.open("https://example.com/").seen()["timezone"])

# The default profile: Browser() with no name. Random every run, nothing saved.
for run in (1, 2):
    with Browser(proxy=PROXY) as b:                         # same as Browser("default", proxy=PROXY)
        print(f"\ndefault, run {run}:", repr(b.profile))
        print(b.open("https://example.com/").check())

# The default with some settings fixed for this run; the rest stays random.
with Browser(proxy=PROXY, device="i7-12700-gtx1660", timezone="America/Chicago", langs=["en-US", "en"]) as b:
    print("\ndefault with settings:")
    print(b.open("https://example.com/").check())
    print("its settings:\n", b.profile, sep="")
