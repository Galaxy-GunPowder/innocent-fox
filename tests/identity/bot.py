"""Can a website tell that Innocent Fox is being driven by a script? Local lab, no outside sites.

  python tests/identity/bot.py            our 160 build
  python tests/identity/bot.py --runs 2   twice each, to tell noise from automation traces

How it works: the same build opens the same probe page twice with the same prefs.
Once ifox drives it (moves, clicks, types over the private pipe); once nobody
does. Anything that differs between the two is an automation trace. Rule checks
then judge the driven input itself (trusted events, real mouse path, key timing),
and the browser's processes must listen on no network port.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
import lab  # noqa: E402
from compare import USER_JS, diff, prefs_js  # noqa: E402
from ifox import browser as ifb  # noqa: E402
from ifox.winjob import Job  # noqa: E402

BUILD = Path(r"D:\ifox\obj\dist\bin\firefox.exe")
SAME = {**ifb.QUIET, **ifb.FRONT}          # what ifox sets for a stock driven run; the plain run gets it too
# ...except staying behind the program in front: the plain run stands for a person starting
# Firefox, whose window comes to the front.
SAME = {k: v for k, v in SAME.items() if k != "ifox.window.noActivate"}


def ports(root_pid):
    """TCP ports the browser's processes listen on."""
    try:
        procs = [psutil.Process(root_pid), *psutil.Process(root_pid).children(recursive=True)]
    except psutil.NoSuchProcess:
        return ["browser gone"]
    pids = {p.pid for p in procs}
    return sorted({f"{c.laddr.ip}:{c.laddr.port}" for c in psutil.net_connections("tcp")
                   if c.pid in pids and c.status == psutil.CONN_LISTEN})


def plain(exe):
    srv = lab.Lab()
    profile = lab.fresh_profile(USER_JS + prefs_js(SAME), secure=False)
    job = Job()
    try:
        proc = job.start([str(exe), "-no-remote", "-wait-for-browser", "-profile", str(profile), srv.url(secure=False)])
        if not srv.done.wait(180):
            sys.exit("plain run: no result")
        r = srv.result
        r["listening"] = ports(proc.pid)
    finally:
        job.kill()
        job.close()
        srv.close()
        lab.remove_profile(profile)
    return r


def driven(exe):
    srv = lab.Lab()
    b = ifb.Browser(stock=True, binary=exe, match_exit=False)
    try:
        tab = b.open(srv.url(secure=False, drive=1), timeout=60)
        tab.wait("#bot-button", timeout=90)
        time.sleep(0.5)
        tab.click("#bot-button")
        tab.type("#bot-input", "hello")
        r = None
        if srv.done.wait(90):
            r = srv.result
            r["listening"] = ports(b.proc.pid)
    finally:
        b.close()
        srv.close()
    if r is None:
        sys.exit("driven run: no result")
    return r


def rules(d):
    """Checks on the driven input: each is (name, passed, value)."""
    x = d.get("driven", {})
    gaps = x.get("keyGapsMs") or []
    holds = [h for h in x.get("keyHoldMs") or [] if h is not None]
    return [
        ("text arrived", x.get("gotText") == "hello", x.get("gotText")),
        ("every event trusted", x.get("allTrusted") is True, x.get("allTrusted")),
        ("mouse path before click", x.get("moves") == "6+", x.get("moves")),
        ("mouse input source is mouse (1)", x.get("pointerInput") == [1], x.get("pointerInput")),
        # type() clicks the text box first, so a second sequence follows: check the button's own.
        ("click order", (x.get("clickSequence") or "").startswith("pointerdown,mousedown,pointerup,mouseup,click"), x.get("clickSequence")),
        ("button held 30-300 ms", isinstance(x.get("pressMs"), (int, float)) and 30 <= x["pressMs"] <= 300, x.get("pressMs")),
        ("pointer type mouse", x.get("clickPointerType") == "mouse", x.get("clickPointerType")),
        ("key gaps vary, none under 20 ms", len(gaps) >= 3 and len(set(gaps)) > 1 and min(gaps) >= 20, gaps),
        ("keys held 20-250 ms", len(holds) >= 4 and min(holds) >= 20 and max(holds) <= 250, holds),
        ("page focused after input", x.get("hasFocusAfter") is True, x.get("hasFocusAfter")),
        ("user activation after input", x.get("userActivationAfter") == [True, True] or (x.get("userActivationAfter") or [False])[0] is True,
         x.get("userActivationAfter")),
        ("webdriver false", d["bot"]["webdriver"] is False, d["bot"]["webdriver"]),
        ("no listening port", d.get("listening") == [], d.get("listening")),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saved", action="store_true", help="judge the last saved runs again, without running")
    ap.add_argument("--binary", default=str(BUILD))
    ap.add_argument("--runs", type=int, default=1)
    a = ap.parse_args()
    exe = Path(a.binary)
    saved = lab.WORK / "identity" / "bot.json"
    out = json.loads(saved.read_text(encoding="utf-8")) if a.saved else {"plain": [], "driven": []}
    for i in range(0 if a.saved else a.runs):
        print(f"plain run {i + 1}/{a.runs}", flush=True)
        out["plain"].append(plain(exe))
        print(f"driven run {i + 1}/{a.runs}", flush=True)
        out["driven"].append(driven(exe))
    (lab.WORK / "identity" / "bot.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    noise = set()
    for kind in out:
        for r in out[kind][1:]:
            noise |= {p for p, _, _ in diff(out[kind][0], r)}
    skip = {"driven"}
    traces = [d for d in diff(out["plain"][0], out["driven"][0]) if d[0] not in noise and d[0].split(".")[0] not in skip]
    checks = rules(out["driven"][0])
    failed = [c for c in checks if not c[1]]

    # Firefox focuses a window Windows brings to the front. With another program in front (a game),
    # the plain run opens behind it and never gets focus; Firefox also holds enumerateDevices() back
    # until a page has focus. Those differences then say what was in front, not who drives.
    unfocused = any(r["bot"].get("hasFocus") is False for r in out["plain"])
    if unfocused:
        print("\nNOT JUDGED: the plain run never got focus, so another program was in front.\n"
              "  bot.hasFocus and bot.mediaDevices can't be compared; rerun with nothing in front.")
    print(f"\nAutomation traces (driven differs from plain): {len(traces)}")
    for p, x, y in traces:
        print(f"  {p}\n    plain:  {x}\n    driven: {y}")
    print(f"\nDriven input checks: {len(checks) - len(failed)}/{len(checks)} passed")
    for name, ok, value in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {value}")
    if noise:
        print("\nleft out as noise: " + ", ".join(sorted(noise)[:15]))
    return 2 if unfocused else (1 if traces or failed else 0)


if __name__ == "__main__":
    sys.exit(main())
