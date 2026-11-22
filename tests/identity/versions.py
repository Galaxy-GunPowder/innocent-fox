"""What changed between two Firefox versions, and can a setting undo it?

  python tests/identity/versions.py prefs 159.0.1            prefs whose default differs from 160
  python tests/identity/versions.py explain 159.0.1          each measured difference: which pref gates it, or "code"
  python tests/identity/versions.py make 159.0.1             write versions/159.0.1.json for compare.py --assemble

Reads the unpacked sources (D:\\ifox\\src for 160, D:\\ifox\\v159\\src ...) and the lab's
saved results (D:\\ifox\\identity\\official-<ver>-1.json).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(r"D:\ifox")
RESULTS = WORK / "identity"
VERSIONS = HERE / "versions"
BASE = "160.0.1"
PREF_FILES = ["modules/libpref/init/StaticPrefList.yaml", "modules/libpref/init/all.js",
              "browser/app/profile/firefox.js"]


def tree(version):
    """The version's unpacked source; older versions without one are read from BASE's."""
    t = WORK / "src" if version == BASE else WORK / f"v{version.split('.')[0]}" / "src"
    return t if t.exists() else WORK / "src"


def pristine(version, rel):
    """The unpatched file: our patches add ifox.* prefs, which must not count as a version change."""
    t = tree(version).parent
    p = (t / "pristine" / rel) if version != BASE else (WORK / "pristine" / rel)
    return p if p.exists() else tree(version) / rel


# ---------------------------------------------------------------- prefs

def read_prefs(version):
    """{name: value text}. #if blocks are kept as written: 'A | B' when a pref has two definitions."""
    out = {}
    yaml = pristine(version, PREF_FILES[0]).read_text(encoding="utf-8", errors="replace")
    name, cond = None, []
    for line in yaml.splitlines():
        if line.startswith("#if"):
            cond.append(line.split(None, 1)[1] if " " in line else line)
        elif line.startswith("#else"):
            cond[-1:] = ["!(" + (cond[-1] if cond else "") + ")"]
        elif line.startswith("#endif") and cond:
            cond.pop()
        elif line.startswith("- name: "):
            name = line[8:].strip()
        elif name and line.startswith("  value: "):
            v = line[9:].strip()
            v = f"{v} [{' && '.join(cond)}]" if cond else v
            out[name] = f"{out[name]} | {v}" if name in out else v
    rx = re.compile(r'^\s*(?:pref|sticky_pref)\(\s*"([^"]+)"\s*,\s*(.+?)\s*\)\s*;', re.M)
    for rel in PREF_FILES[1:]:
        text = pristine(version, rel).read_text(encoding="utf-8", errors="replace")
        for m in rx.finditer(text):
            out.setdefault(m.group(1), m.group(2))
    return out


def pref_changes(old):
    a, b = read_prefs(old), read_prefs(BASE)
    changed = {k: (a[k], b[k]) for k in a.keys() & b.keys() if a[k] != b[k]}
    return changed, sorted(b.keys() - a.keys()), sorted(a.keys() - b.keys())


def as_value(text):
    """A pref's default as user.js wants it, or None when it depends on the build or platform."""
    t = text.strip()
    if "|" in t or "[" in t or "@" in t:
        return None
    if t in ("true", "false"):
        return t == "true"
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r'"[^"]*"', t):
        return t[1:-1]
    return None


# ---------------------------------------------------------------- what gates a feature

def webidl_gate(version, iface, member=None):
    """Pref="..." on an interface (or one member), from the version's WebIDL."""
    for f in (tree(version) / "dom" / "webidl").glob("*.webidl"):
        text = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(rf"(\[[^\]]*\])?\s*(?:partial\s+)?interface\s+(?:mixin\s+)?{re.escape(iface)}\b[^{{]*\{{", text)
        if not m:
            continue
        head = text[max(0, m.start() - 600):m.end()]
        if member is None:
            p = re.findall(r'Pref="([^"]+)"', head[-700:].split(";")[-1])
            return (p[-1] if p else "code", f.name)
        body = text[m.end():text.find("};", m.end())]
        for line_m in re.finditer(rf"(\[[^\]]*\])?[^;\[]*\b{re.escape(member)}\b[^;]*;", body):
            p = re.findall(r'Pref="([^"]+)"', line_m.group(0))
            return (p[0] if p else "code", f.name)
    return ("not in WebIDL (JS engine or code)", "")


def css_gate(version, prop):
    """gecko_pref of a CSS property, from servo's property definitions."""
    root = tree(version) / "servo" / "components" / "style" / "properties"
    for f in list(root.rglob("*.py")) + list(root.rglob("*.rs")) + list(root.rglob("*.toml")):
        text = f.read_text(encoding="utf-8", errors="replace")
        i = text.find(f'"{prop}"')
        if i >= 0:
            seg = text[i:i + 1500]
            m = re.search(r'gecko_pref\s*=\s*"([^"]+)"', seg[:seg.find("\n\n") if "\n\n" in seg else 1500])
            return m.group(1) if m else "code"
    return "code"


# Differences with a known switch in Innocent Fox's code (patch 12), by result path.
KNOWN_CODE = {
    "WebTransportDatagramDuplexStream.incomingHighWaterMark": {"ifox.compat.webtransport.highWaterMark": True},
    "WebTransportDatagramDuplexStream.outgoingHighWaterMark": {"ifox.compat.webtransport.highWaterMark": True},
    # 160 probes decoders with AssertCanInstantiate and makes up a VP9/AV1/HEVC config: powerEfficient.
    "drm.decoding.": {"ifox.compat.media.assertCanInstantiate": False,
                      "ifox.compat.media.synthesizeCodecConfig": False},
}
AV1_FMTP = "video/AV1 profile=0;level-idx=9;tier=0"     # 158+ getCapabilities; 157 and older: "video/AV1"
WRITABLE = {("RTCSessionDescription", "sdp"), ("RTCSessionDescription", "type")}   # rw up to 157
USER_AGENT_PATHS = ("navigator.userAgent", "worker.ua", "navigator.appVersion")


def load(version):
    return json.loads((RESULTS / f"official-{version}-1.json").read_text(encoding="utf-8"))


def alias_gate(name):
    """webkitSpeechRecognition and the like are LegacyFactoryFunction names of an interface: its gate."""
    for f in (tree(BASE) / "dom" / "webidl").glob("*.webidl"):
        text = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(rf"LegacyFactoryFunction={re.escape(name)}\b[^\]]*\][^{{]*?interface\s+(\w+)", text, re.S)
        if m:
            return webidl_gate(BASE, m.group(1))[0]
    return None


# Values that change between runs of one browser or with the run's timing, never a version.
# bot.hasFocus and a timed-out device list depend on whether the window was in front, not the version.
NOISE = ("drm.com.widevine", "drmLate.com.widevine", "timerSteps", ".ech.kdf_aead",
         "bot.hasFocus", "bot.mediaDevices", "bot.rafPerSecond", "bot.hidden", "bot.visibility", "bot.userActivation")


def classify(old):
    """Every difference between official BASE and official old, sorted into how it is closed:
    prefs (settings), edits (ifox.compat.edits), and what still needs code."""
    sys.path.insert(0, str(HERE))
    from compare import diff
    a, b = load(BASE), load(old)
    prefs, edits, todo, why = user_agent_prefs(old), [], [], {}

    def gate_off(gate, what):
        prefs[gate] = False
        why.setdefault(gate, []).append(what)

    def known(path):
        for k, v in KNOWN_CODE.items():
            if path == k or (k.endswith(".") and path.startswith(k)):
                prefs.update(v)
                for name in v:
                    why.setdefault(name, []).append(path)
                return True
        return False

    ga, gb = set(a["globals"]), set(b["globals"])
    for g in sorted(ga - gb):
        gate = webidl_gate(BASE, g)[0] if not g.startswith("webkit") else (alias_gate(g) or "code")
        (gate_off(gate, f"global {g}") if "." in gate else todo.append(f"global {g} (only {BASE})"))
    for g in sorted(gb - ga):
        todo.append(f"global {g} (only {old})")

    sa, sb = a.get("signatures", {}), b.get("signatures", {})
    for iface in sorted(set(sa) & set(sb)):
        if iface not in ga & gb:
            continue
        ma = {x.split("/")[0].split(" ")[0]: x for x in sa[iface]}
        mb = {x.split("/")[0].split(" ")[0]: x for x in sb[iface]}
        for m in sorted(ma.keys() - mb.keys()):
            if iface == "CSSStyleProperties":
                continue                                   # a CSS property's own name: see cssProperties
            gate = webidl_gate(BASE, iface, m)[0]
            if "." in gate:
                gate_off(gate, f"{iface}.{m}")
            elif not known(f"{iface}.{m}"):
                edits.append(f"{iface}.{m}=hide")
        for m in sorted(mb.keys() - ma.keys()):
            if not known(f"{iface}.{m}"):
                todo.append(f"{iface}.{m} (only {old})")
        for m in sorted(ma.keys() & mb.keys()):
            if ma[m] != mb[m]:
                if (iface, m) in WRITABLE and ma[m].endswith(" r") and mb[m].endswith(" rw"):
                    prefs["ifox.compat.webrtc.writableSessionDescription"] = True
                    why.setdefault("ifox.compat.webrtc.writableSessionDescription", []).append(f"{iface}.{m} writable")
                elif "/" in ma[m] and "/" in mb[m]:
                    edits.append(f"{iface}.{m}=length:{mb[m].split('/')[1]}")
                else:
                    todo.append(f"{iface}.{m}: {ma[m]} in {BASE}, {mb[m]} in {old}")
        kept = [x for x in sb[iface]]
        mine = [x for x in sa[iface] if x.split("/")[0].split(" ")[0] in mb]
        if [x.split("/")[0].split(" ")[0] for x in mine] != [x.split("/")[0].split(" ")[0] for x in kept if x.split("/")[0].split(" ")[0] in ma]:
            todo.append(f"{iface}: member order differs")

    ma_all, mb_all = a.get("members", {}), b.get("members", {})
    signed = {(i, x.split("/")[0].split(" ")[0]) for i in sa for x in sa[i]}
    for key in sorted(set(ma_all) & set(mb_all)):
        if key.endswith(" static"):
            iface, target = key[:-7], "static."
        elif key.endswith(".prototype"):
            iface, target = key[:-10], ""
        else:
            iface, target = key, ""                      # a namespace object such as GPUTextureUsage
        if iface not in ga & gb or iface == "CSSStyleProperties":
            continue
        for m in sorted(set(mb_all[key]) - set(ma_all[key])):
            if not known(f"{iface}.{m}"):
                todo.append(f"{key}.{m} (only {old})")
        for m in sorted(set(ma_all[key]) - set(mb_all[key])):
            if not target and key.endswith(".prototype") and (iface, m) in signed:
                continue                                 # done above, from the signatures
            gate = webidl_gate(BASE, iface, m)[0]
            if "." in gate:
                gate_off(gate, f"{key}.{m}")
            elif not known(f"{iface}.{m}"):
                edits.append(f"{iface}.{target}{m}=hide")

    ca, cb = set(a.get("cssProperties", [])), set(b.get("cssProperties", []))
    for prop in sorted(ca - cb):
        gate = css_gate(BASE, prop)
        (gate_off(gate, f"css {prop}") if "." in gate else todo.append(f"css {prop} (only {BASE}; check after the prefs)"))
    for prop in sorted(cb - ca):
        todo.append(f"css {prop} (only {old})")

    ext = sorted({e for k in ("webgl", "webgl2") for e in set((a.get(k) or {}).get("extensions") or [])
                  - set((b.get(k) or {}).get("extensions") or [])})
    if ext:
        prefs["ifox.webgl.hiddenExtensions"] = ",".join(ext)
        why["ifox.webgl.hiddenExtensions"] = [f"WebGL {e}" for e in ext]

    # TLS: 155 and older add FFDHE 2048/3072 (0100, 0101) to supported_groups. With the switch on,
    # the group list, its length and the JA3 built from it all match, so those paths are covered.
    tls_a = (a.get("network") or {}).get("tls_h2_port") or {}
    tls_b = (b.get("network") or {}).get("tls_h2_port") or {}
    ffdhe = (tls_b.get("supported_groups") == (tls_a.get("supported_groups") or []) + ["0100", "0101"])
    if ffdhe:
        prefs["ifox.compat.tls.ffdheGroups"] = True
        why["ifox.compat.tls.ffdheGroups"] = ["TLS supported_groups adds FFDHE 2048 and 3072, and so JA3"]
    ffdhe_paths = ("supported_groups", "extension_lengths.000a", ".ja3", ".ja3_hash")

    covered = ("globals", "members.", "signatures.", "cssProperties", "webgl.extensions", "webgl2.extensions",
               "network.requests.", "network.tls_", "documentMembers", "navigatorMembers")
    for path, x, y in diff(a, b):
        if ffdhe and path.startswith("network.tls_") and path.endswith(ffdhe_paths):
            continue
        if path.startswith(covered) and not path.startswith(("network.tls_", "network.requests.")):
            continue
        if path in USER_AGENT_PATHS or path.lower().endswith("user-agent") or ":path" in path:
            continue
        if any(n in path for n in NOISE) or known(path):
            continue
        raw_a, raw_b = (a.get("drm") or {}).get(path[4:]), (b.get("drm") or {}).get(path[4:])
        if path.startswith("drm.rtc") and isinstance(raw_a, list) and [v.replace(AV1_FMTP, "video/AV1") for v in raw_a] == raw_b:
            prefs["ifox.compat.webrtc.av1Fmtp"] = False
            why.setdefault("ifox.compat.webrtc.av1Fmtp", []).append(path)
            continue
        if path.endswith("img-headers_h2.values.accept") and "image/jxl" in x and "image/jxl" not in y:
            gate_off("image.jxl.enabled", "image Accept header and JPEG XL support")
            continue
        todo.append(f"{path}: {x[:80]} in {BASE}, {y[:80]} in {old}")
    edits = list(dict.fromkeys(edits))
    if edits:
        prefs["ifox.compat.edits"] = ";".join(edits)
    return prefs, edits, todo, why


def explain(old):
    prefs, edits, todo, why = classify(old)
    rows = [(k, repr(v), "; ".join(why.get(k, ["user agent"]))[:200]) for k, v in prefs.items()]
    rows += [("needs code", t, "") for t in todo]
    return rows


def user_agent_prefs(version):
    v = version.split(".")[0] + ".0"
    return {"general.useragent.override": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{v}) Gecko/20100101 Firefox/{v}"}


PACKAGE = HERE.parents[1] / "ifox" / "versions.json"


def make(old):
    """versions/<old>.json for compare.py, and the same prefs in ifox/versions.json for profiles."""
    prefs, edits, todo, why = classify(old)
    VERSIONS.mkdir(exist_ok=True)
    out = VERSIONS / f"{old}.json"
    out.write_text(json.dumps({"base": BASE, "as": old, "prefs": prefs, "why": why, "needs_code": todo}, indent=1),
                   encoding="utf-8")
    table = json.loads(PACKAGE.read_text(encoding="utf-8")) if PACKAGE.exists() else {"base": BASE.split(".")[0], "versions": {}}
    entry = {"measured": old, "prefs": prefs, "needs_code": todo}
    before = table["versions"].get(old.split(".")[0], {})
    if before.get("prefs") == prefs and "verified" in before:
        entry["verified"] = before["verified"]          # same prefs: the last lab check still holds
    table["versions"][old.split(".")[0]] = entry
    table["versions"] = dict(sorted(table["versions"].items(), key=lambda kv: -int(kv[0])))
    PACKAGE.write_text(json.dumps(table, indent=1), encoding="utf-8")
    print(f"{old}: {len(prefs)} prefs, {len(edits)} member edits, {len(todo)} need code  ({out.name}, ifox/versions.json)")
    for t in todo:
        print(f"  needs code: {t}")


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    cmd, old = sys.argv[1:]
    if cmd == "prefs":
        changed, added, removed = pref_changes(old)
        print(f"{old} -> {BASE}: {len(changed)} defaults changed, {len(added)} prefs added, {len(removed)} removed")
        for k, (x, y) in sorted(changed.items()):
            print(f"  {k}: {x}  ->  {y}")
        print("added: " + ", ".join(added[:80]))
        print("removed: " + ", ".join(removed[:80]))
    elif cmd == "explain":
        for row in explain(old):
            print("  " + " | ".join(r for r in row if r))
    elif cmd == "make":
        make(old)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
