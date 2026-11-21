"""First Innocent Fox script: search Wikipedia like a person, read the result, save a screenshot.

  python first_script.py               no proxy (your own IP)
  python first_script.py --proxy https://user:pass@us.decodo.com:10001

Runs from any folder once `ifox` is installed.
"""
import argparse

from ifox import Browser

ap = argparse.ArgumentParser()
ap.add_argument("--proxy", help="any common proxy format; the clock follows the exit")
ap.add_argument("--query", default="Red fox")
a = ap.parse_args()

with Browser(proxy=a.proxy) as b:                 # new random device every run
    if b.exit:
        print("exit:", b.exit["country"], b.exit["city"], b.exit["timezone"])
    tab = b.open("https://en.wikipedia.org/")
    tab.type("input[name=search]", a.query)       # clicks the box, types with human timing
    tab.press("Enter")
    tab.wait("#firstHeading", timeout=20)
    print("page:", tab.title)
    print("heading:", tab.text("#firstHeading"))
    print("first line:", tab.js("return document.querySelector('#mw-content-text p:not(.mw-empty-elt)')?.textContent.trim().slice(0, 120)"))
    tab.shot("first_script.png")
    print("screenshot: first_script.png")
