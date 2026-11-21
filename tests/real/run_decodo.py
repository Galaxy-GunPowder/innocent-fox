"""Real proxy test through Decodo: exit IP, WebRTC, DNS, CreepJS.

  set IFOX_PROXY_FILE=path\\to\\decodo_proxy.txt
  python tests/real/run_decodo.py

Reads the socks5h:// line from that file and never prints it.
IPs are printed masked. Output pages go to D:\\ifox\\real\\.
"""
import json
import os
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ifox import Browser  # noqa: E402
from ifox.network import Proxy, parse  # noqa: E402

KEY = Path(os.environ.get("IFOX_PROXY_FILE", "decodo_proxy.txt"))
OUT = Path(r"D:\ifox\real")
IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

WEBRTC = """
const pc = new RTCPeerConnection({ iceServers: [{ urls: "stun:stun.l.google.com:19302" }] });
pc.createDataChannel("probe");
const cands = [];
await new Promise(resolve => {
  pc.onicecandidate = e => { if (e.candidate) cands.push(e.candidate.candidate); else resolve(); };
  setTimeout(resolve, 10000);
  pc.createOffer().then(o => pc.setLocalDescription(o));
});
const sdp = pc.localDescription ? pc.localDescription.sdp : "";
pc.close();
return { cands, sdp };
"""


# Every host name Firefox resolved itself (about:networking, DNS tab).
LOCAL_DNS = """
const d = Components.classes["@mozilla.org/network/dashboard;1"].getService(Components.interfaces.nsIDashboard);
return await new Promise(r => d.requestDNSInfo(x => r(JSON.parse(JSON.stringify(x.entries.map(e => e.hostname))))));
"""


# Country names as browserleaks prints them, for the exit countries we use.
COUNTRY = {"US": "United States", "GB": "United Kingdom", "DE": "Germany", "SG": "Singapore"}


def dns_countries(text):
    """Country of every DNS server the leak page lists ("ip<TAB>isp<TAB>Country, City")."""
    return [loc.split(",")[0].strip() for _, loc in re.findall(r"^\S+\t([^\t]+)\t([^\n]+)$", text, re.M)]


def mask(ip):
    p = ip.split(".")
    return ".".join(p[:2] + ["x", "x"])


def setups():
    """Both Decodo setups as Proxy objects, from the key file."""
    lines = [x.strip() for x in KEY.read_text(encoding="utf-8").splitlines()]
    host, port = lines[0].split()
    gate = parse(next(x for x in lines if x.startswith("socks5")))
    account = gate.user.split("-")[1]          # user-<account>-session-...-country-us
    session = f"user-{account}-country-us-session-ifox{random.randint(10**5, 10**6)}-sessionduration-30"
    return {
        "https": Proxy("https", host, int(port), lines[1], lines[2]),
        "gate": Proxy("https", "gate.decodo.com", random.randint(10001, 10999),
                      f"user-{lines[1]}-country-us", lines[2]),
        "socks": Proxy("socks5h", "gate.decodo.com", 7000, session, gate.password),
    }


def wait_text(tab, min_len=50, tries=60):
    text = ""
    for _ in range(tries):
        text = tab.js("return document.body ? document.body.textContent : ''") or ""
        if len(text) >= min_len:
            break
        time.sleep(0.5)
    return text


def stable_text(tab, seconds=8):
    last, stable = -1, 0
    for _ in range(90):
        time.sleep(1)
        n = tab.js("return document.body ? document.body.innerText.length : 0")
        stable = stable + 1 if n == last and n > 1000 else 0
        last = n
        if stable >= seconds:
            break
    return tab.js("return document.body.innerText")


def run(name, proxy, real):
    # JSON viewer off: raw JSON as text (a display setting, not page-visible).
    with Browser(device="i7-12700-gtx1660", seed=33, proxy=proxy,
                 prefs={"devtools.jsonview.enabled": False}) as b:
        tab = b.open("https://ipinfo.io/json", timeout=60)
        exit_info = json.loads(wait_text(tab))
        # Match the profile's clock to the exit, then load pages fresh (build list 5.12).
        b.set_prefs(**{"ifox.timezone": exit_info["timezone"]})
        tab.goto("https://example.com/", timeout=60)
        rtc = tab.js(WEBRTC)
        # Request headers as the website receives them, over https and plain http.
        echoed = ""
        for url in ("https://httpbin.org/headers", "http://httpbin.org/headers"):
            tab.goto(url, timeout=60)
            echoed += wait_text(tab, 20)
        tab.goto("https://abrahamjuliot.github.io/creepjs/", timeout=90)
        creep = stable_text(tab, 8)
        (OUT / f"{name}-creep.txt").write_text(creep, encoding="utf-8")
        # Last: the DNS page fires hundreds of lookups, and Decodo then refuses names for ~15 s.
        tab.goto("https://browserleaks.com/dns", timeout=90)
        dns_text = ""
        for _ in range(90):
            time.sleep(1)
            dns_text = tab.js("return document.body.innerText") or ""
            if "Found" in dns_text:
                time.sleep(4)
                dns_text = tab.js("return document.body.innerText")
                break
        (OUT / f"{name}-dns.txt").write_text(dns_text, encoding="utf-8")
        local = sorted(set(b.call("chrome", code=LOCAL_DNS)))

    lines = [x for x in rtc["cands"] + rtc["sdp"].splitlines() if not x.startswith("a=fingerprint")]
    rtc_ips = sorted({a for x in lines for a in IP.findall(x)} - {"0.0.0.0", "127.0.0.1"})
    print(f"== {name}: {proxy.scheme}://{proxy.host}:{proxy.port}")
    print(f"exit:   {mask(exit_info['ip'])} {exit_info.get('country')} {exit_info.get('city')} {exit_info.get('timezone')}")
    print(f"webrtc: {len(rtc['cands'])} candidates, addresses {[mask(a) for a in rtc_ips]}")
    found = re.search(r"Found [^\n]+", dns_text)
    servers = dns_countries(dns_text)
    elsewhere = sorted({c for c in servers if c != COUNTRY.get(exit_info.get("country"), "?")})
    print(f"dns:    page {found.group(0) if found else 'no result'}; resolved here: {local}; "
          f"servers outside the exit country: {elsewhere or 'none'}")
    checks = [
        ("exit IP differs from real IP", exit_info["ip"] != real["ip"]),
        ("exit is in the US", exit_info.get("country") == "US"),
        ("WebRTC shows no address", rtc_ips == []),
        ("website sees no proxy login", '"Host"' in echoed and "proxy-authorization" not in echoed.lower()),
        ("DNS leak page finished", bool(found)),
        ("real IP not on the DNS leak page", real["ip"] not in dns_text),
        # Resolvers in another country show where you are, even with the right exit IP
        # (Decodo: its Singapore entry server asks Cloudflare Singapore).
        ("every DNS server is in the exit's country", bool(servers) and not elsewhere),
        ("no page name resolved on this machine", local == [proxy.host]),
        ("real IP not in CreepJS", real["ip"] not in creep),
        ("CreepJS 0% headless", "0% headless" in creep and "0% like headless" in creep),
        ("CreepJS time zone = exit's", exit_info["timezone"] in creep),
    ]
    width = max(len(n) for n, _ in checks)
    for n, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n:<{width}}")
    print(f"{sum(ok for _, ok in checks)}/{len(checks)} passed")
    return all(ok for _, ok in checks)


def main():
    real = json.loads(urllib.request.urlopen("https://ipinfo.io/json", timeout=15).read())
    print(f"real:   {mask(real['ip'])} {real.get('country')} {real.get('timezone')}")
    OUT.mkdir(parents=True, exist_ok=True)
    all_setups = setups()
    names = sys.argv[1:] or list(all_setups)
    results = {n: run(n, all_setups[n], real) for n in names}
    print("summary:", {n: "pass" if ok else "FAIL" for n, ok in results.items()}, f"; pages in {OUT}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
