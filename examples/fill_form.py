"""Fill in a web form and send it. httpbin.org is a public test site that shows what it received."""
import json
from ifox import Browser

with Browser() as b:
    tab = b.open("https://httpbin.org/forms/post")

    tab.type("input[name=custname]", "Alex Doe")             # a text box
    tab.type("input[name=custtel]", "555-0100")
    tab.type("input[name=custemail]", "alex@example.com")
    tab.click("input[value=medium]")                          # a round option button: Medium
    tab.click("input[value=cheese]")                          # a tick box: Cheese
    tab.type("textarea[name=comments]", "Ring the bell twice.")
    tab.click("text=Submit order")                            # the button, found by its words

    tab.wait("text=Raw Data")              # wait for something only the next page has
    tab.click("text=Raw Data")             # Firefox shows the reply in its JSON viewer; this tab is plain text
    sent = json.loads(tab.text("pre"))
    print(sent["form"])                    # just the form part
