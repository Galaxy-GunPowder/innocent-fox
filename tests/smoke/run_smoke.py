"""Smoke test the built browser: do our ifox.* prefs reach pages and workers?

Starts a local server, launches the build headless with a test profile, reads back what the page saw.
  python tests/smoke/run_smoke.py
"""
import json
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ifox import Browser  # noqa: E402

HERE = Path(__file__).resolve().parent
BROWSER = Path(r"D:\ifox\obj\dist\bin\firefox.exe")
PROFILES = Path(r"D:\ifox\profiles\smoke")
PORT = 8765
HIDDEN_EXT = "EXT_texture_filter_anisotropic"

# Keep test runs quiet: no first-run pages, no update or telemetry chatter.
QUIET = {
    "browser.shell.checkDefaultBrowser": False,
    "browser.aboutwelcome.enabled": False,
    "browser.startup.homepage_override.mstone": "ignore",
    "datareporting.policy.dataSubmissionEnabled": False,
    "toolkit.telemetry.reportingpolicy.firstRun": False,
}

OURS = {
    "ifox.hardwareConcurrency": 6,
    "ifox.maxTouchPoints": 10,          # stock collapse rule should report 5
    "ifox.webdriver": False,
    "ifox.screen.width": 1280,          # device pixels; pages see them / devicePixelRatio
    "ifox.screen.height": 720,
    "ifox.noise.seed": "smoke-seed",
    "ifox.webgl.parameters": "0x0D33:4096;0x0D3A:4096,4096",
    "ifox.webgl.hiddenExtensions": HIDDEN_EXT,
    "ifox.timezone": "America/New_York",
}

result = {}
got = threading.Event()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (HERE / "page.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        result.clear()
        result.update(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self.send_response(204)
        self.end_headers()
        got.set()

    def log_message(self, *a):
        pass


def run(name, prefs, extra_args=()):
    folder = PROFILES / name
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    lines = [f"user_pref({json.dumps(k)}, {json.dumps(v)});" for k, v in {**QUIET, **prefs}.items()]
    (folder / "user.js").write_text("\n".join(lines) + "\n")
    got.clear()
    url = f"http://127.0.0.1:{PORT}/?hidden={HIDDEN_EXT}"
    proc = subprocess.Popen([str(BROWSER), "-no-remote", "-headless", "-profile", str(folder), *extra_args, url])
    ok = got.wait(90)
    # Kill this launch's whole tree: content and GPU processes outlive the parent and lock the profile.
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    proc.wait()
    if not ok:
        sys.exit(f"{name}: page never reported back")
    return dict(result)


def run_piped(name, prefs):
    """Same page, but the browser is started and driven over the ifox pipe."""
    got.clear()
    url = f"http://127.0.0.1:{PORT}/?hidden={HIDDEN_EXT}"
    with Browser(stock=True, prefs=prefs, args=["-headless"]) as b:
        b.open(url)
        ok = got.wait(90)
    if not ok:
        sys.exit(f"{name}: page never reported back")
    return dict(result)


def main():
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    stock = run("stock-1", {})
    # Driven over the pipe, as every automation will be.
    ours1 = run_piped("ours-1", OURS)
    ours2 = run("ours-2", OURS)  # a different, fresh profile folder with the same seed
    stock2 = run("stock-2", {})
    server.shutdown()

    print(json.dumps({"stock": stock, "ours": ours1}, indent=1))
    checks = [
        ("cores in page", ours1["cores"] == 6),
        ("cores in worker", ours1["workerCores"] == 6),
        ("time zone in page", ours1["tz"] == "America/New_York" and ours1["offset"] == 300),
        ("time zone in worker", ours1["workerTz"] == "America/New_York" and ours1["workerOffset"] == 300),
        ("stock keeps the real time zone", stock["tz"] != "America/New_York"),
        ("touch points, stock collapse on top", ours1["maxTouchPoints"] == 5),
        ("webdriver false while driven", ours1["webdriver"] is False),
        ("screen = device pixels / devicePixelRatio",
         ours1["screen"] == [round(1280 / ours1["dpr"]), round(720 / ours1["dpr"])]),
        ("avail width = screen width", ours1["avail"][0] == ours1["screen"][0]),
        ("taskbar gap same as stock", ours1["screen"][1] - ours1["avail"][1] == stock["screen"][1] - stock["avail"][1]),
        ("CSS device-width within 1px of screen", ours1["cssDeviceWidthNear"] is True),
        ("CSS device-height within 1px of screen", ours1["cssDeviceHeightNear"] is True),
        ("stock CSS device-width within 1px too", stock["cssDeviceWidthNear"] is True),
        ("WebGL MAX_TEXTURE_SIZE", ours1["webgl"].get("maxTextureSize") == 4096),
        ("WebGL MAX_VIEWPORT_DIMS", ours1["webgl"].get("maxViewportDims") == [4096, 4096]),
        ("hidden extension not listed", ours1["webgl"].get("hiddenListed") is False),
        ("hidden extension not gettable", ours1["webgl"].get("hiddenGettable") is False),
        ("hidden extension exists on stock", stock["webgl"].get("hiddenListed") is True),
        ("canvas same across launches with seed", ours1["canvas"] == ours2["canvas"]),
        ("canvas differs across launches on stock", stock["canvas"] != stock2["canvas"]),
    ]
    width = max(len(n) for n, _ in checks)
    for n, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n:<{width}}")
    failed = sum(not ok for _, ok in checks)
    print(f"{len(checks) - failed}/{len(checks)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
