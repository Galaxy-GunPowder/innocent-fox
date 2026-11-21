"""Drive a sign-up page over the ifox pipe and check what the page could tell.

  python tests/pipe/run_pipe.py

Serves page.html on 127.0.0.1 and frame.html on 127.0.0.2 (a different site,
so Firefox puts the iframe in its own process). Opens a visible window:
key events need the window in front.
"""
import json
import sys
import time
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from ifox import Browser  # noqa: E402


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(host, port):
    server = HTTPServer((host, port), partial(Quiet, directory=str(HERE)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main():
    servers = [serve("127.0.0.1", 8766), serve("127.0.0.2", 8767)]
    with Browser(stock=True) as b:
        tab = b.open("http://127.0.0.1:8766/page.html")
        tab.type("#email", "Test.User@example.com")
        tab.type("#pass", "x9!Pq")
        tab.click("text=Create account")
        pay = tab.frame("iframe#pay")
        pay.type("#card", "4242 4242")
        tab.click("iframe#pay >> #paybtn")
        tab.click("#host >> #shadowbtn")
        tab.click("#far")
        time.sleep(0.4)  # the pages refresh their reports every 100 ms
        page = json.loads(tab.js("return document.getElementById('report').textContent"))
        frame = json.loads(pay.js("return document.getElementById('report').textContent"))
        title = tab.title
    for s in servers:
        s.shutdown()

    print(json.dumps({"page": page, "frame": frame}, indent=1))
    clicks = {c["target"]: c for c in page["clicks"]}
    create = clicks.get("create", {})
    typed = [k for k in page["keys"] if k["key"] not in ("Shift",)]
    checks = [
        ("title read", title == "Sign up"),
        ("email typed", page["email"] == "Test.User@example.com"),
        ("password typed", page["pass"] == "x9!Pq"),
        ("every page event trusted", page["untrusted"] == 0),
        ("page visible for every event", page["hiddenEvents"] == 0),
        ("page focused for every key", page["unfocusedKeys"] == 0),
        ("text= click reached the button", create.get("trusted") is True),
        ("click is a mouse pointer", create.get("pointerType") == "mouse" and create.get("source") == 1),
        ("element hovered at mousedown", create.get("hover") is True),
        ("mouse moved before each click", all(c["movesBefore"] >= 5 for c in page["clicks"])),
        ("shift held for capitals", any(k["key"] == "T" and k["shift"] and k["code"] == "KeyT" for k in typed)),
        ("key codes set", all(k["keyCode"] for k in typed)),
        ("scrolled by wheel", len(page["wheels"]) > 0 and all(w["trusted"] for w in page["wheels"])),
        ("far button clicked after scrolling", "far" in clicks),
        ("shadow DOM button clicked", page.get("shadowClicked") is True),
        ("cross-site frame got the typing", frame["card"] == "4242 4242" and frame["untrusted"] == 0),
        ("cross-site frame button clicked", frame["clicked"] is True),
        ("frame really cross-site", frame["origin"] == "http://127.0.0.2:8767"),
        ("navigator.webdriver false", page["webdriver"] is False),
        ("no globals added to the page", page["addedGlobals"] == []),
        ("no automation port 2828", page["portOpen"] is False),
    ]
    width = max(len(n) for n, _ in checks)
    for n, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {n:<{width}}")
    failed = sum(not ok for _, ok in checks)
    print(f"{len(checks) - failed}/{len(checks)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
