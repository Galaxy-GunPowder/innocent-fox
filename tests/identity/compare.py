"""Does one browser look exactly like another to a website? Local lab, no outside sites.

  python tests/identity/compare.py 160.0.1                       official 160.0.1 against our build
  python tests/identity/compare.py 160.0.1 --vs-official 159.0.1 two official versions: what changed between them
  python tests/identity/compare.py 159.0.1 --assemble 160.0.1    official 160 with versions/159.0.1.json prefs
                                                                 against official 159: what settings can't hide
  python tests/identity/compare.py 160.0.1 --ours-pref ifox.hardwareConcurrency=4   self-check: must find it
  --runs 2   run each twice; values that change between runs of one browser are noise, left out
  --late 60  read DRM and codecs again after 60 s (Widevine and OpenH264 download after start)

Each browser opens tests/identity/probe.html from tests/identity/lab.py in a fresh
profile with the same first-run prefs. The page reads what a script can (APIs, CSS,
engine, media, DRM, WebGL, fonts, workers, bot signals); the lab's servers record
what a server can (TLS ClientHello with JA3/JA4, HTTP/2 frames, header order).
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))
from ifox.winjob import Job  # noqa: E402
import lab  # noqa: E402

WORK = Path(r"D:\ifox")
OFFICIAL = WORK / "official"
RESULTS = WORK / "identity"
VERSIONS = HERE / "versions"
SEVEN_ZIP = Path(r"C:\mozilla-build\bin\7zip\7z.exe")
DEFAULT = "160.0.1"

# The same for every browser: skip first-run pages and prompts. None of these change what a page sees.
USER_JS = """\
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("startup.homepage_welcome_url", "");
user_pref("startup.homepage_welcome_url.additional", "");
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("datareporting.policy.dataSubmissionPolicyBypassNotification", true);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("app.update.disabledForTesting", true);
user_pref("browser.startup.windowsLaunchOnLogin.enabled", false);
user_pref("browser.startup.windowsLaunchOnLogin.alreadyApplied", true);
"""

# No policies.json in the official copies: any active enterprise policy turns Web Serial off
# by default (EnterprisePoliciesParent.sys.mjs), which a page sees as a missing navigator.serial.


# ---------------------------------------------------------------- browsers

def ours(version):
    major = version.split(".")[0]
    tree = WORK if version == DEFAULT else WORK / f"v{major}"
    return tree / "obj" / "dist" / "bin" / "firefox.exe"


def no_updater(exe):
    """Official copies never update: without updater.exe a downloaded update can't be installed.
    Pages can't see it."""
    for name in ("updater.exe", "updater.ini", "maintenanceservice.exe", "maintenanceservice_installer.exe"):
        (exe.parent / name).unlink(missing_ok=True)
    return exe


def official(version):
    import urllib.request
    exe = OFFICIAL / version / "core" / "firefox.exe"
    if exe.exists():
        return no_updater(exe)
    OFFICIAL.mkdir(parents=True, exist_ok=True)
    base = f"https://archive.mozilla.org/pub/firefox/releases/{version}"
    name = f"win64/en-US/Firefox Setup {version}.exe"
    get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ifox-identity-test"}), timeout=120)  # noqa: E731
    sums = get(f"{base}/SHA256SUMS").read().decode()
    want = next(line.split()[0] for line in sums.splitlines() if line.split(maxsplit=1)[1].strip() == name)
    setup = OFFICIAL / f"Firefox Setup {version}.exe"
    print(f"downloading official {name}", flush=True)
    with get(f"{base}/{name.replace(' ', '%20')}") as r, open(setup, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    if hashlib.sha256(setup.read_bytes()).hexdigest() != want:
        setup.unlink()
        sys.exit(f"official {version}: checksum mismatch")
    subprocess.run([str(SEVEN_ZIP), "x", "-y", f"-o{OFFICIAL / version}", str(setup)], check=True, stdout=subprocess.DEVNULL)
    setup.unlink()
    if not exe.exists():
        sys.exit(f"official {version}: no core/firefox.exe after unpacking")
    return no_updater(exe)


def prefs_js(prefs):
    return "".join(f"user_pref({json.dumps(k)}, {json.dumps(v)});\n" for k, v in prefs.items())


def version_prefs(version):
    """versions/<version>.json: the prefs that make a newer Firefox present as <version>."""
    f = VERSIONS / f"{version}.json"
    if not f.exists():
        sys.exit(f"{f} not found; make it with versions.py")
    return json.loads(f.read_text(encoding="utf-8"))["prefs"]


# ---------------------------------------------------------------- one run

class Timeout(RuntimeError):
    pass


def run(exe, prefs=None, timeout=180, late=0, tries=2):
    """Open the probe in a fresh profile; return what the page and the servers saw.
    A run that times out is tried once more, and the stall is printed."""
    for attempt in range(tries):
        try:
            return run_once(exe, prefs, timeout, late)
        except Timeout as e:
            print(f"  {e}" + ("; trying again" if attempt + 1 < tries else ""), flush=True)
    sys.exit(f"{exe}: no result after {tries} tries")


def run_once(exe, prefs, timeout, late):
    srv = lab.Lab()
    # A new profile checks for updates 30 s in (last check = 0); say it just checked. Plain runs
    # ignore app.update.disabledForTesting, so without this an official copy updates itself.
    no_update = {"app.update.lastUpdateTime.background-update-timer": int(time.time())}
    profile = lab.fresh_profile(USER_JS + prefs_js(no_update) + prefs_js(prefs or {}))
    forget_lab_installs()
    job = Job()
    try:
        job.start([str(exe), "-no-remote", "-wait-for-browser", "-profile", str(profile), srv.url(late=late)])
        if not srv.done.wait(timeout + late):
            raise Timeout(f"no result within {timeout + late} s, page stopped at: {srv.stage}")
        result = srv.result
        result["network"] = srv.network()
        result["mediaPlugins"] = sorted(p.name for p in profile.glob("gmp-*") if any(p.iterdir()))
    finally:
        job.kill()
        job.close()
        srv.close()
        lab.remove_profile(profile)
        forget_lab_installs()
    return result


def forget_lab_installs():
    """Remove what a lab Firefox leaves in Windows: a Run value that opens it at login (Mozilla
    can switch that on remotely), its background-update scheduled task, and any update it
    downloaded, which would replace the copy with a newer version on its next start.
    Only entries for installs in D:\\ifox are touched."""
    import winreg
    root = str(WORK).lower()
    for staged in OFFICIAL.glob("*/core/updated"):
        shutil.rmtree(staged, ignore_errors=True)
    update_root = Path(r"C:\ProgramData\Mozilla-1de4eec8-1241-4177-a864-e594e8d1fb38\updates")
    hashes = set()    # Firefox names each install's update folder by a hash it records here
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Mozilla\Firefox\TaskBarIDs") as ids:
            i = 0
            while True:
                try:
                    path, value, _ = winreg.EnumValue(ids, i)
                except OSError:
                    break
                if path.lower().startswith(root):
                    hashes.add(str(value).upper())
                i += 1
    except OSError:
        pass
    for folder in update_root.glob("*"):
        logs = " ".join(f.read_text(errors="ignore") for f in folder.glob("updates/*.log")).lower()
        if folder.name.upper() in hashes or f"installation directory {root}" in logs:
            shutil.rmtree(folder, ignore_errors=True)
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                         winreg.KEY_READ | winreg.KEY_SET_VALUE)
    with key:
        names, i = [], 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
            except OSError:
                break
            if name.startswith("Mozilla-Firefox") and root in str(value).lower():
                names.append(name)
            i += 1
        for name in names:
            winreg.DeleteValue(key, name)
    ps = ("Get-ScheduledTask -TaskPath '\\Mozilla\\' -ErrorAction SilentlyContinue | "
          f"Where-Object {{ ($_.Actions.Execute -join ' ').ToLower().Contains('{root}') }} | "
          "Unregister-ScheduledTask -Confirm:$false")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=60)


# ---------------------------------------------------------------- diff

def diff(a, b, path="", out=None):
    """Differences between two results: list of (path, first, second)."""
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            diff(a.get(k, "<missing>"), b.get(k, "<missing>"), f"{path}.{k}" if path else k, out)
    elif isinstance(a, list) and isinstance(b, list) and all(isinstance(x, str) for x in a + b) \
            and (len(a) > 12 or len(b) > 12):
        only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
        if only_a or only_b:
            out.append((path, f"only here: {only_a[:15]}{' ...' if len(only_a) > 15 else ''}",
                        f"only here: {only_b[:15]}{' ...' if len(only_b) > 15 else ''}"))
        elif a != b:
            out.append((path, "same items, other order", json.dumps(b)[:200]))
    elif a != b:
        out.append((path, json.dumps(a)[:200], json.dumps(b)[:200]))
    return out


def card(r):
    """The few values that name a browser, for the summary."""
    n = r.get("network", {})
    tls = n.get("tls_h2_port") or {}
    return {
        "user agent": r.get("navigator", {}).get("userAgent"),
        "JA4": tls.get("ja4"), "JA3 hash": tls.get("ja3_hash"),
        "HTTP/2 (Akamai)": (n.get("http2") or {}).get("akamai"),
        "globals": len(r.get("globals", [])), "CSS properties": len(r.get("cssProperties", [])),
        "media plug-ins": r.get("mediaPlugins"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version", nargs="?", default=DEFAULT)
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--late", type=int, default=0)
    ap.add_argument("--ours-pref", action="append", default=[], help="name=value, set for the second browser only")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--vs-official", metavar="VER", help="second browser: official VER")
    g.add_argument("--assemble", metavar="BASE", help="second browser: official BASE (or ours) with versions/<version>.json")
    a = ap.parse_args()
    RESULTS.mkdir(parents=True, exist_ok=True)

    prefs = {}
    for item in a.ours_pref:
        k, _, v = item.partition("=")
        prefs[k] = int(v) if v.lstrip("-").isdigit() else {"true": True, "false": False}.get(v, v)
    if a.vs_official:
        second, name = official(a.vs_official), f"official {a.vs_official}"
    elif a.assemble:
        # "ours": our 160 build, which also takes the ifox.* prefs a version file may list
        second = ours(DEFAULT) if a.assemble == "ours" else official(a.assemble)
        name = f"{'ours ' + DEFAULT if a.assemble == 'ours' else 'official ' + a.assemble} as {a.version}"
        prefs = {**version_prefs(a.version), **prefs}
    else:
        second, name = ours(a.version), f"ours {a.version}"
    if not second.exists():
        sys.exit(f"missing: {second}")
    first = f"official {a.version}"
    browsers = {first: (official(a.version), {}), (name if name != first else name + " again"): (second, prefs)}

    results = {}
    for label, (exe, p) in browsers.items():
        for i in range(a.runs):
            print(f"running {label} ({i + 1}/{a.runs})", flush=True)
            r = run(exe, p, late=a.late)
            results[(label, i)] = r
            (RESULTS / f"{label.replace(' ', '-')}-{i + 1}.json").write_text(json.dumps(r, indent=1), encoding="utf-8")

    noise = set()
    for label in browsers:
        for i in range(1, a.runs):
            noise |= {p for p, _, _ in diff(results[(label, 0)], results[(label, i)])}
    second_label = list(browsers)[1]
    found = [d for d in diff(results[(first, 0)], results[(second_label, 0)]) if d[0] not in noise]

    for label in browsers:
        print(f"\n{label}")
        for k, v in card(results[(label, 0)]).items():
            print(f"  {k:16} {v}")
    print(f"\n{len(found)} difference(s) a website could see"
          + (f"; {len(noise)} value(s) changed between runs of one browser and were left out" if noise else ""))
    for p, x, y in found:
        print(f"\n  {p}\n    {first}: {x}\n    {second_label}: {y}")
    if any(r["bot"].get("hasFocus") is False for (label, _), r in results.items()):
        print("\nNOTE: a run had no page focus, so another program was in front. bot.* values then\n"
              "  say what was in front, not which browser it is; rerun with nothing in front.")
    if noise:
        print("\nleft out as noise: " + ", ".join(sorted(noise)[:20]))
    if a.assemble == "ours":
        mark_verified(a.version, a.runs, found)
    return 1 if found else 0


def mark_verified(version, runs, found):
    """The lab's verdict on our build as version, in ifox/versions.json: profiles offer only versions
    that showed 0 differences over 2 or more runs, with the prefs they were checked with."""
    path = HERE.parents[1] / "ifox" / "versions.json"
    table = json.loads(path.read_text(encoding="utf-8"))
    entry = table["versions"].get(version.split(".")[0])
    if entry is None:
        return
    entry["verified"] = {"date": time.strftime("%Y-%m-%d"), "runs": runs, "differences": len(found),
                         "passed": not found and runs >= 2}
    path.write_text(json.dumps(table, indent=1), encoding="utf-8")
    print(f"ifox/versions.json: {version} {'verified' if entry['verified']['passed'] else 'not verified'}")


if __name__ == "__main__":
    sys.exit(main())
