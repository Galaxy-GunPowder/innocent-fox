"""Create (or reuse) a browser profile folder and start Innocent Fox with it.

  python launcher/launch.py --name alice --place UK
  python launcher/launch.py --name alice              reuse alice's saved fingerprint
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ifox import fingerprint as fp  # noqa: E402
from ifox.network import proxy_prefs  # noqa: E402

PROFILES = Path(r"D:\ifox\profiles")
BROWSER = Path(r"D:\ifox\obj\dist\bin\firefox.exe")


def load_or_make(name, place, device, proxy_ip, gpu_mode="fake", hidden=False, proxy=None):
    folder = PROFILES / name
    saved = folder / "ifox-profile.json"
    if saved.exists():
        d = json.loads(saved.read_text())
        p = fp.Profile(**{**{k: v for k, v in d.items() if k != "avail"}, "screen": tuple(d["screen"]), "gpu": tuple(d["gpu"])})
    else:
        folder.mkdir(parents=True, exist_ok=True)
        p = fp.make(place=place, device=device, webrtc_ip=proxy_ip, gpu_mode=gpu_mode)
        saved.write_text(p.to_json())
    # Rewritten on every start, so a pref changed in the code reaches old profiles too.
    extra = "".join(f"user_pref({json.dumps(k)}, {json.dumps(v)});\n"
                    for k, v in proxy_prefs(proxy).items()) if proxy else ""
    (folder / "user.js").write_text(fp.user_js(p, hidden) + extra, encoding="utf-8")
    return folder, p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--place", default="US-East", choices=fp.PLACES)
    ap.add_argument("--device", choices=[d["name"] for d in fp.DEVICES])
    ap.add_argument("--proxy", help="socks5://host:port or http://host:port; nothing goes around it")
    ap.add_argument("--proxy-ip", default="", help="public IP of the proxy, shown to WebRTC (planned)")
    ap.add_argument("--gpu-mode", default="fake", choices=["fake", "real"],
                    help="fake: claim another GPU, noise on. real: host GPU, noise off")
    ap.add_argument("--hidden", action="store_true",
                    help="run on a hidden desktop (desktop switching not built yet; sets the prefs only)")
    ap.add_argument("--url", default="about:blank")
    a = ap.parse_args()

    folder, p = load_or_make(a.name, a.place, a.device, a.proxy_ip, a.gpu_mode, a.hidden, a.proxy)
    print(f"{a.name}: {p.device}, {p.place}, {p.tz}")
    subprocess.Popen([str(BROWSER), "-no-remote", "-profile", str(folder), a.url])


if __name__ == "__main__":
    main()
