"""Run CreepJS on Innocent Fox, driven over the private pipe, and save what it reports.

  python tests/creep/run_creep.py            all three profiles
  python tests/creep/run_creep.py real       one profile

stock: no fingerprint changes (Firefox 160 on this machine), still driven.
real:  this laptop's own device and GPU.
fake:  another device and GPU.
proxy: fake, behind a local SOCKS5 proxy (tests/webrtc/socks.py).
Visible window per profile. Page text goes to D:\\ifox\\creep\\<name>.txt.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "webrtc"))
from ifox import Browser  # noqa: E402
from socks import Socks5  # noqa: E402

OUT = Path(r"D:\ifox\creep")
URL = "https://abrahamjuliot.github.io/creepjs/"

PROFILES = {
    "stock": dict(stock=True),
    "real": dict(device="ryzen5-4600h-laptop", gpu_mode="real", seed=11),
    "fake": dict(device="i7-12700-gtx1660", gpu_mode="fake", seed=22),
    "proxy": dict(device="i7-12700-gtx1660", gpu_mode="fake", seed=22, proxy="local"),
}


def run(name):
    args = dict(PROFILES[name])
    proxy = Socks5() if args.get("proxy") == "local" else None
    if proxy:
        args["proxy"] = proxy.url
    with Browser(place="US-East", **args) as b:
        tab = b.open(URL, timeout=60)
        # CreepJS fills in over several seconds; wait until the text stops growing.
        last, stable = -1, 0
        for _ in range(90):
            time.sleep(1)
            n = tab.js("return document.body ? document.body.innerText.length : 0")
            stable = stable + 1 if n == last and n > 2000 else 0
            last = n
            if stable >= 8:
                break
        text = tab.js("return document.body.innerText")
    if proxy:
        proxy.close()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.txt").write_text(text, encoding="utf-8")
    print(f"{name}: {len(text)} chars saved to {OUT / (name + '.txt')}")


if __name__ == "__main__":
    for name in sys.argv[1:] or list(PROFILES):
        run(name)
