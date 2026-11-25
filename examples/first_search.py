"""Search Wikipedia and print the first paragraph of the article."""
from ifox import Browser

with Browser() as b:                                   # start the browser (a new identity each run)
    tab = b.open("https://en.wikipedia.org/")          # open a tab at this address

    tab.type("input[name=search]", "Red fox")          # click the search box and type, like a person
    tab.press("Enter")                                 # press the Enter key

    tab.wait("#firstHeading")                          # wait until the article title is on the page
    print(tab.text("#firstHeading"))                   # the title's text
    print(tab.text("#mw-content-text p:not(.mw-empty-elt)"))   # the first paragraph's text
