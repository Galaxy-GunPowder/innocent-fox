"""WebRTC leak test: with a proxy set, no page may ever see this machine's real IP.

  python tests/webrtc/run_webrtc.py

1. direct:  stock Firefox, no proxy. Its STUN reply gives this machine's real public IP.
2. proxy:   stock Firefox behind a local SOCKS5 proxy.
3. profile: a fake-device profile behind the same proxy.
Runs 2 and 3 must show no address at all from WebRTC. IPs are printed masked.
"""
import json
import re
import sys
import threading
import time
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from ifox import Browser  # noqa: E402
from socks import Socks5  # noqa: E402

PORT = 8768
IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|\b[0-9a-f]{1,4}(?::[0-9a-f]{0,4}){2,7}\b", re.I)
NOT_AN_ADDRESS = {"0.0.0.0", "127.0.0.1", "::"}


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def mask(ip):
    parts = ip.split(".")
    return ".".join(parts[:2] + ["x", "x"]) if len(parts) == 4 else ip[:9] + "..."


def gather(**browser_args):
    with Browser(**browser_args) as b:
        tab = b.open(f"http://127.0.0.1:{PORT}/page.html")
        for _ in range(60):
            text = tab.js("return document.getElementById('report').textContent")
            if text:
                break
            time.sleep(0.5)
    r = json.loads(text)
    # The DTLS fingerprint line is colon-separated hex, not an address.
    lines = [x for x in r["candidates"] + r["sdp"].splitlines() if not x.startswith("a=fingerprint")]
    addresses = {a for line in lines for a in IP.findall(line)}
    r["addresses"] = sorted(addresses - NOT_AN_ADDRESS)
    r["types"] = sorted({m.group(1) for c in r["candidates"] for m in [re.search(r" typ (\w+)", c)] if m})
    return r


def main():
    server = HTTPServer(("127.0.0.1", PORT), partial(Quiet, directory=str(HERE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    proxy = Socks5()
    # The test page is on 127.0.0.1, which Firefox never proxies by default.
    via_proxy = {"network.proxy.allow_hijacking_localhost": True}

    direct = gather(stock=True)
    behind = gather(stock=True, proxy=proxy.url, prefs=via_proxy)
    page_via_proxy = any(c.endswith(f":{PORT}") for c in proxy.connects)
    profile = gather(device="i7-12700-gtx1660", seed=22, proxy=proxy.url, prefs=via_proxy)
    proxy.close()
    server.shutdown()

    real = [a for a in direct["addresses"] if not a.startswith(("10.", "192.168.", "172."))]
    for name, r in (("direct", direct), ("proxy", behind), ("profile", profile)):
        print(f"{name:8} types={r['types']} addresses={[mask(a) for a in r['addresses']]} error={r['error']}")
    print(f"proxy saw {len(proxy.connects)} connections, {proxy.udp_requests} UDP requests")

    checks = [
        ("direct run finds the real public IP (test works)", "srflx" in direct["types"] and bool(real)),
        ("page loaded through the proxy", page_via_proxy),
        ("behind proxy: no WebRTC address at all", behind["addresses"] == [] and behind["error"] is None),
        ("behind proxy: real IP nowhere", not set(real) & set(behind["addresses"])),
        ("profile behind proxy: no WebRTC address", profile["addresses"] == [] and profile["error"] is None),
        ("WebRTC still works as an API behind proxy", behind["sdp"].startswith("v=0")),
    ]
    width = max(len(n) for n, _ in checks)
    for n, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n:<{width}}")
    failed = sum(not ok for _, ok in checks)
    print(f"{len(checks) - failed}/{len(checks)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
