"""Sign in to a site by hand once. Every later run starts already signed in."""
from ifox import Browser, profile

p = profile.get("github")                        # first run makes a saved profile, later runs load it

with Browser(p) as b:
    tab = b.open("https://github.com/login")
    if tab.exists("text=Sign in to GitHub"):     # the sign-in page: not signed in yet
        print("Sign in in the browser window, then close the window.")
        b.wait_closed()                           # cookies are saved when the window closes
    else:
        print("Already signed in.")               # the saved cookies did it
