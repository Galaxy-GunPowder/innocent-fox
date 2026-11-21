# Major changes

A summary of what Innocent Fox changes, one line each. Every change, with how it was made and what is still planned, is in the [build list](build-list.md).

| Category | What we did |
|---|---|
| Scripting | Python controls the browser through a private channel, not an automation port |
| Scripting | Mouse and keyboard use the normal input path, with human mouse paths and typing rhythm |
| Scripting | Selectors reach into frames, including other sites' payment frames, and shadow DOM |
| Bot detection | `navigator.webdriver` is always false, in pages and workers |
| Bot detection | Your scripts run in a sandbox the page can't see |
| Bot detection | Driven windows act as the front window, so pages never switch to hidden |
| Proxy | HTTPS, HTTP and SOCKS5 proxies with login, pasted in any of 5 common formats |
| Proxy | Time zone and languages follow the proxy's country |
| Proxy | WebRTC goes through the proxy only; sites see 0 addresses |
| Proxy | DNS lookups go through the proxy |
| Proxy | Kill switch: if the proxy drops, pages stop loading instead of using your connection |
| Proxy | HTTP proxy login is sent without a prompt |
| Fingerprint | 15 device values set inside the engine, such as screen, display scale, CPU cores and touch |
| Fingerprint | Graphics card name, WebGL limits and extensions match the claimed card |
| Fingerprint | Canvas noise key kept per profile, so a profile looks the same after restarts |
| Fingerprint | Windows "Text size" no longer changes the display scale pages see |
| Profiles | Saved profiles keep the same device, cookies and logins every run |
| Profiles | Built-in default profile: a new random device every run, nothing kept |
| Profiles | `print(p)` shows every setting plus session history: proxies, countries, websites |
| Profiles | Wiping history keeps every setting |
| Background | Idle background connections cut from 33 addresses to 8 |
| Install | The browser downloads itself on first use and closes when your script ends |
