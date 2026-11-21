# Pref contract

Each row is one fingerprint value and the pref that sets it.
Stock = Firefox already has the pref. Patch = we add it (patches/01-ifox-prefs.patch registers them all).
Rule: our values replace the real hardware value underneath Firefox's own protections, so stock 160 rules still apply on top.

| Value | Pref | Default | Where in Firefox |
|---|---|---|---|
| User-Agent (HTTP + JS) | stock `general.useragent.override` | real | |
| platform, oscpu, appVersion | stock `general.*.override` | real | |
| Accept-Language, navigator.languages | stock `intl.accept_languages` | real | |
| devicePixelRatio | stock `layout.css.devPixelsPerPx`; stock `browser.display.os-zoom-behavior` = 0 so Windows "Text size" does not zoom pages (101% showed scale 1.0 as 1.0169) | real | |
| WebGL vendor / renderer (fake GPU only) | stock `webgl.override-unmasked-*` | real | |
| Time zone, pages and all workers (Windows ignores `TZ` for IANA names) | `ifox.timezone` | "" = real | js/xpconnect/src/nsXPConnect.cpp |
| Core count, pages and workers | `ifox.hardwareConcurrency` | 0 = real | dom/workers/RuntimeService.cpp |
| navigator.webdriver | `ifox.webdriver` | false | dom/base/Navigator.cpp |
| Touch points (stock collapse to 5 still applies), CSS pointer queries | `ifox.maxTouchPoints` | -1 = real | dom/base/Navigator.cpp, layout/style/nsMediaFeatures.cpp |
| Screen size in device pixels, also CSS device-width (avail = height - 48, stock) | `ifox.screen.width`, `ifox.screen.height` | 0 = real | dom/base/nsScreen.cpp, layout/style/nsMediaFeatures.cpp |
| Canvas noise key, stable across restarts | `ifox.noise.seed` | "" = stock, new each session | toolkit/components/resistfingerprinting/nsRFPService.cpp |
| WebGL readPixels noise (fake GPU only) | stock `privacy.baselineFingerprintingProtection.overrides` = `+WebGLRandomization` | off | |
| WebGL getParameter limits of the claimed GPU | `ifox.webgl.parameters` | "" = real | dom/canvas/ClientWebGLContext.cpp |
| WebGL extensions the claimed GPU lacks (hide only) | `ifox.webgl.hiddenExtensions` | "" | dom/canvas/ClientWebGLContext.cpp |
| Audio sample rate | stock `media.cubeb.force_sample_rate` | 0 = real | |
| Driven window acts as the front window: raised, focused | stock `focusmanager.testmode`, set by `ifox.Browser` | false | |
| Driven window never treated as covered (else pages go hidden) | stock `widget.windows.window_occlusion_tracking.enabled` = false, set by `ifox.Browser` | true | |
| Claimed Firefox version | `ifox.version` | "" = real | planned |
| Proxy, kill switch, remote DNS, WebRTC proxy-only | stock `network.proxy.*`, `media.peerconnection.ice.proxy_only`, set by `ifox/network.py` | off | |
| Login for plain http proxies, sent like https proxies (no 407 prompt) | proxy info header from the agent | | netwerk/protocol/http/nsHttpChannelAuthProvider.cpp |
| WebRTC through the tunnel, STUN shows the exit IP | planned (build list 5.9b) | | |
| Background calls pages can't see (ads, weather, region, updates, studies, DoH probes) off | stock prefs, `QUIET` in `ifox/browser.py` | on | |
