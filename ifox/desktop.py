"""Open Innocent Fox for use by hand: a saved profile behind a proxy, clock set to the exit.

  ifox-open --name main --proxy https://user:pass@us.decodo.com:10001
  ifox-open --name main --proxy-file decodo_proxy.txt

--proxy-file takes either a proxy URL on its first line, or the layout
"host port" / user / password on three lines (sent as https).
The login reaches the browser over the private pipe only; it is never written to the profile.
Stays running until the window is closed. Errors open a message box.
"""
import argparse
import ctypes
import time
import traceback
from pathlib import Path

from . import fingerprint as fp
from .browser import PROFILES, Browser
from .network import Proxy, parse

LOG = PROFILES.parent / "desktop.log"


def proxy_from_file(path):
    lines = [x.strip() for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    if "://" in lines[0]:
        return parse(lines[0])
    host, port = lines[0].split()
    return Proxy("https", host, int(port), lines[1], lines[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="main", help="saved profile: same fingerprint every start")
    ap.add_argument("--place", choices=fp.PLACES, help="no proxy: where the profile is (default US-East)")
    ap.add_argument("--device", choices=[d["name"] for d in fp.DEVICES])
    ap.add_argument("--proxy", help="proxy in any common format (see ifox/network.py)")
    ap.add_argument("--proxy-file", help="file holding the proxy (see above)")
    ap.add_argument("--url", default="about:blank")
    a = ap.parse_args()

    proxy = proxy_from_file(a.proxy_file) if a.proxy_file else (parse(a.proxy) if a.proxy else None)
    b = Browser(a.name, place=a.place, device=a.device, proxy=proxy, front=False, timeout=90)
    try:
        tab = b.tab
        if proxy:
            info = b.exit or {}          # Browser already set the clock to the exit's
            LOG.write_text(f"{time.ctime()}: {a.name} via {proxy.scheme}://{proxy.host}:{proxy.port}, "
                           f"exit {info.get('country')} {info.get('city')} {info.get('timezone')}\n")
        tab.goto(a.url)
        b.wait_closed()    # until the person closes the window
    finally:
        b.close()


def main_safe():
    """main(), with any error shown in a message box (no console under pythonw)."""
    try:
        main()
    except Exception as e:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        LOG.write_text(traceback.format_exc())
        ctypes.windll.user32.MessageBoxW(0, f"{type(e).__name__}: {e}\n\nDetails: {LOG}", "Innocent Fox", 0x10)


if __name__ == "__main__":
    main_safe()
