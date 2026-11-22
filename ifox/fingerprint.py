"""Build one consistent fingerprint and turn it into prefs.

Every value in a profile comes from a single real device and a single place,
so nothing contradicts anything else (a 4-core laptop never reports a desktop GPU).
"""
import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

FIREFOX_VERSION = "160.0"      # used until a browser is launched; then the browser's own version


def user_agent(version=FIREFOX_VERSION):
    return f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}"


def browser_version(exe):
    """"159.0" for a Firefox 159.0.1 build, read from application.ini next to firefox.exe."""
    try:
        for line in (Path(exe).parent / "application.ini").read_text(encoding="utf-8").splitlines():
            if line.startswith("Version="):
                return line.split("=", 1)[1].split(".")[0] + ".0"
    except OSError:
        pass
    return FIREFOX_VERSION

# Starter device list: real Windows laptop/desktop configurations.
# Replace with measured data before relying on it; one entry = one physical machine.
# screen is in device pixels. Stock Firefox 160 itself reports avail height = height - 48.
# Optional measured keys, written only when present (never guessed):
#   touch        max touch points before Firefox's own collapse rule
#   audio_rate   sound card sample rate, 44100 or 48000
#   webgl_params {"0x0D33": 16384, "0x0D3A": [32767, 32767]}  getParameter values of this GPU
#   hidden_ext   ["EXT_foo"]  WebGL extensions this GPU lacks but the host has
MEASURED_KEYS = ("touch", "audio_rate", "webgl_params", "hidden_ext")
DEVICES = [
    dict(name="ryzen5-4600h-laptop", cores=12, screen=(1920, 1080), dpr=1.25,
         gpu=("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon(TM) Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)")),
    dict(name="i5-1135g7-laptop", cores=8, screen=(1920, 1080), dpr=1.5,
         gpu=("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)")),
    dict(name="i7-12700-gtx1660", cores=20, screen=(2560, 1440), dpr=1.0,
         gpu=("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)")),
    dict(name="i3-10110u-laptop", cores=4, screen=(1366, 768), dpr=1.0,
         gpu=("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)")),
]

# Place = timezone + languages. Must match the proxy's exit country.
PLACES = {
    "US-East": dict(tz="America/New_York", langs=["en-US", "en"]),
    "US-West": dict(tz="America/Los_Angeles", langs=["en-US", "en"]),
    "UK": dict(tz="Europe/London", langs=["en-GB", "en"]),
    "DE": dict(tz="Europe/Berlin", langs=["de-DE", "de", "en-US", "en"]),
    "SG": dict(tz="Asia/Singapore", langs=["en-SG", "en"]),
}


# Page languages for a new profile, by the proxy exit's country (ISO code).
# Not listed: stock en-US Firefox's own "en-US, en".
LANGS_BY_COUNTRY = {
    "US": ["en-US", "en"], "GB": ["en-GB", "en"], "IE": ["en-GB", "en"], "CA": ["en-CA", "en"],
    "AU": ["en-AU", "en"], "NZ": ["en-NZ", "en"], "SG": ["en-SG", "en"],
    "DE": ["de-DE", "de", "en-US", "en"], "AT": ["de-AT", "de", "en-US", "en"],
    "FR": ["fr-FR", "fr", "en-US", "en"], "ES": ["es-ES", "es", "en-US", "en"],
    "IT": ["it-IT", "it", "en-US", "en"], "NL": ["nl-NL", "nl", "en-US", "en"],
    "PT": ["pt-PT", "pt", "en-US", "en"], "BR": ["pt-BR", "pt", "en-US", "en"],
    "MX": ["es-MX", "es", "en-US", "en"], "AR": ["es-AR", "es", "en-US", "en"],
    "PL": ["pl-PL", "pl", "en-US", "en"], "SE": ["sv-SE", "sv", "en-US", "en"],
    "JP": ["ja-JP", "ja", "en-US", "en"], "KR": ["ko-KR", "ko", "en-US", "en"],
}


def langs_for(country):
    return LANGS_BY_COUNTRY.get((country or "").upper(), ["en-US", "en"])


@dataclass
class Profile:
    device: str
    place: str
    seed: int
    user_agent: str
    cores: int
    screen: tuple
    dpr: float
    gpu: tuple
    tz: str
    langs: list
    webrtc_ip: str = ""
    # "fake": claim the device's GPU, plus WebGL noise. "real": host GPU, exactly stock Firefox.
    # Canvas noise stays on in both: stock Firefox 160 adds it for every user.
    gpu_mode: str = "fake"
    extra: dict = field(default_factory=dict)

    def to_json(self):
        return json.dumps(asdict(self), indent=2)


def make(place="US-East", device=None, seed=None, webrtc_ip="", gpu_mode="fake"):
    if gpu_mode not in ("fake", "real"):
        raise ValueError(f"gpu_mode must be fake or real, not {gpu_mode!r}")
    rng = random.Random(seed)
    seed = rng.getrandbits(32) if seed is None else seed
    d = next(x for x in DEVICES if x["name"] == device) if device else rng.choice(DEVICES)
    p = PLACES[place]
    # ifox.screen.* takes device pixels; Firefox divides by devPixelsPerPx itself, with its own rounding.
    w, h = d["screen"]
    return Profile(
        device=d["name"], place=place, seed=seed,
        user_agent=user_agent(),
        cores=d["cores"], screen=(w, h), dpr=d["dpr"],
        gpu=d["gpu"], tz=p["tz"], langs=p["langs"], webrtc_ip=webrtc_ip, gpu_mode=gpu_mode,
        extra={k: d[k] for k in MEASURED_KEYS if k in d},
    )


def webgl_params_pref(params):
    """{"0x0D33": 16384, "0x0D3A": [32767, 32767]} -> "0x0D33:16384;0x0D3A:32767,32767"."""
    parts = []
    for pname, value in params.items():
        values = value if isinstance(value, (list, tuple)) else [value]
        parts.append(f"{pname}:" + ",".join(str(v) for v in values))
    return ";".join(parts)


def prefs(p: Profile, hidden=False):
    """Prefs for user.js. Stock Firefox prefs first, then our ifox.* prefs (see docs/prefs.md).

    hidden: the window runs on a hidden desktop, so Firefox must treat it as raised and uncovered.
    """
    fake = p.gpu_mode == "fake"
    out = {
        # stock
        "general.useragent.override": p.user_agent,
        "general.platform.override": "Win32",
        "general.oscpu.override": "Windows NT 10.0; Win64; x64",
        "general.appversion.override": "5.0 (Windows)",
        "intl.accept_languages": ", ".join(p.langs),
        "layout.css.devPixelsPerPx": str(p.dpr),
        # Windows "Text size" (e.g. 101%) otherwise zooms every page: scale 1.0 shows
        # as 1.0169 and the screen shrinks, a rare value that ties profiles to this computer.
        "browser.display.os-zoom-behavior": 0,
        # ifox.* (added by our patches)
        "ifox.hardwareConcurrency": p.cores,
        "ifox.webdriver": False,
        "ifox.maxTouchPoints": p.extra.get("touch", 0),
        "ifox.screen.width": p.screen[0],
        "ifox.screen.height": p.screen[1],
        "ifox.noise.seed": f"{p.seed:08x}",
        "ifox.webrtc.ip": p.webrtc_ip,
        "ifox.timezone": p.tz,
    }
    if "audio_rate" in p.extra:
        out["media.cubeb.force_sample_rate"] = p.extra["audio_rate"]
    if hidden:
        # Stock: raise and focus windows without the OS, and never treat a window as covered.
        out["focusmanager.testmode"] = True
        out["widget.windows.window_occlusion_tracking.enabled"] = False
    if fake:
        # The claimed GPU's own limits and extension list, when measured.
        if "webgl_params" in p.extra:
            out["ifox.webgl.parameters"] = webgl_params_pref(p.extra["webgl_params"])
        if "hidden_ext" in p.extra:
            out["ifox.webgl.hiddenExtensions"] = ",".join(p.extra["hidden_ext"])
        # Stock switch for Firefox's own WebGL readPixels noise, on top of the stock baseline set.
        out["privacy.baselineFingerprintingProtection.overrides"] = "+WebGLRandomization"
        out["webgl.override-unmasked-vendor"] = p.gpu[0]
        out["webgl.override-unmasked-renderer"] = p.gpu[1]
    return out


def user_js(p: Profile, hidden=False):
    lines = [f"// Innocent Fox profile: {p.device} @ {p.place}"]
    for k, v in prefs(p, hidden).items():
        lines.append(f"user_pref({json.dumps(k)}, {json.dumps(v)});")
    return "\n".join(lines) + "\n"
