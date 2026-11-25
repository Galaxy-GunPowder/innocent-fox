"""Speed and memory: our build against official Firefox, same PC, same page, nothing from the internet.

  python tests/perf/bench.py [runs=3] [--prefs]     --prefs: also ours with the PERF prefs

Per run: start time (launch until the page is asked for), the page's work times (median of 5),
and memory (private bytes of every process of that browser, 8 s after the work ends).
"""
import json, shutil, statistics, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent / "identity")]
from ifox.winjob import Job  # noqa: E402
from ifox.browser import QUIET, PERF  # noqa: E402
from compare import USER_JS, official, ours, prefs_js  # noqa: E402

PORT = 8831
PAGE = (HERE / "bench.html").read_bytes()
state = {}


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/bench"):
            state.setdefault("asked", time.perf_counter())
        self.send_response(200); self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(PAGE if self.path.startswith("/bench") else b"")

    def do_POST(self):
        state["result"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        state["done"] = time.perf_counter()
        self.send_response(204); self.end_headers()

    def log_message(self, *a):
        pass


def memory(exe):
    total = n = 0
    for p in psutil.process_iter(["exe"]):
        try:
            if p.info["exe"] and Path(p.info["exe"]).resolve() == exe.resolve():
                total += p.memory_info().private; n += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total / 2**20, n


def run(name, exe, prefs):
    state.clear()
    prof = Path(tempfile.mkdtemp(prefix="ifox-bench-"))
    (prof / "user.js").write_text(USER_JS + prefs_js(prefs), encoding="utf-8")
    job = Job()
    t0 = time.perf_counter()
    job.start([str(exe), "-no-remote", "-profile", str(prof), f"http://127.0.0.1:{PORT}/bench.html"])
    try:
        while "done" not in state:
            if time.perf_counter() - t0 > 180:
                raise RuntimeError(f"{name}: no result after 180 s")
            time.sleep(0.1)
        time.sleep(8)
        mem, procs = memory(exe)
    finally:
        job.kill(); job.close()
        time.sleep(2)
        shutil.rmtree(prof, ignore_errors=True)
    return dict(state["result"], start_s=state["asked"] - t0, mem_mb=mem, procs=procs)


if __name__ == "__main__":
    runs = int(next((a for a in sys.argv[1:] if a.isdigit()), 3))
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    configs = [("official 160", official("160.0.1"), {}), ("ours", ours("160.0.1"), QUIET)]
    if "--prefs" in sys.argv:
        configs.append(("ours + PERF", ours("160.0.1"), {**QUIET, **PERF}))
    got = {c[0]: [] for c in configs}
    for i in range(runs):                      # alternate, so a busy moment hits every browser alike
        for name, exe, prefs in configs:
            got[name].append(run(name, exe, prefs))
            print(f"run {i + 1} {name}: total {got[name][-1]['total']:.0f} ms, {got[name][-1]['mem_mb']:.0f} MB", flush=True)
    keys = ["start_s", "total", "js_primes", "json", "dom_layout", "regex", "sort", "strings", "mem_mb", "procs"]
    print(f"\n{'median of ' + str(runs):14}" + "".join(f"{k:>12}" for k in keys))
    for name, rows in got.items():
        print(f"{name:14}" + "".join(f"{statistics.median(r[k] for r in rows):>12.2f}" for k in keys))
    out = HERE / "results"; out.mkdir(exist_ok=True)
    (out / time.strftime("%Y-%m-%d_%H%M.json")).write_text(json.dumps(got, indent=1), encoding="utf-8")
