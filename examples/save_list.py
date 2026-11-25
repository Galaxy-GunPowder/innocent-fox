"""Save the top 10 Hacker News stories to a spreadsheet file (CSV)."""
import csv
from ifox import Browser

with Browser() as b:
    tab = b.open("https://news.ycombinator.com/")
    tab.wait(".titleline")

    # Read many things at once with JavaScript. It runs out of the page's sight.
    stories = tab.js("""
        return [...document.querySelectorAll(".titleline > a")]
            .slice(0, 10)
            .map(a => [a.textContent, a.href]);
    """)

with open("stories.csv", "w", newline="", encoding="utf-8") as f:
    csv.writer(f).writerows([["title", "link"], *stories])
print(f"saved {len(stories)} stories to stories.csv")
