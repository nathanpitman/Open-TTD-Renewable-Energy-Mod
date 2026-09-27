#!/usr/bin/env python3
"""
Headless in-game check: load the NewGRF and Game Script in a real OpenTTD
and run a few game months without a screen.

This catches what a build can't: the GRF failing to load or being disabled,
cargos or industry chains not coming out as intended, generators not
producing, crashes, and Game Script errors. It does NOT check how anything
looks (art, icons, animation); that still needs a person in a real game.

Usage:
    python3 tools/ingame_check.py [--openttd PATH] [--ticks N] [--seed N] [--keep]

Needs an OpenTTD binary with the OpenGFX base set installed
(e.g. `apt install openttd openttd-opengfx`). It uses a throwaway profile
in a temp directory, so your own OpenTTD settings are never touched.

Two runs:
  1. tools/ingame_check_gs (a test-only Game Script) checks cargos, industry
     chains and production, and logs "ETCHECK" lines.
  2. The real Game Script (energy_transition_gs) runs with the GRF, and must
     start, find the POWR cargo and raise no script errors.

Exit status is 0 only if both runs pass.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRF = os.path.join(ROOT, "energy_transition.grf")
NML = os.path.join(ROOT, "energy_transition.nml")
REAL_GS = os.path.join(ROOT, "energy_transition_gs")
CHECK_GS = os.path.join(ROOT, "tools", "ingame_check_gs")

# Settings changed from their defaults so one fresh map (starting 1985) can
# contain every industry: the debug setting lifts the generators' start
# years, and the latest coal cut-off lets coal power stations still appear.
OVERRIDES = {"param_debug_all_available": 1, "param_coal_stop_year": 1990}


def grf_params():
    """GRF parameter values, in parameter-number order, from the NML defaults."""
    text = open(NML, encoding="utf-8").read()
    grf = text[text.index("grf {"):text.index("cargotable")]
    values, num = {}, 0
    for m in re.finditer(r"\bparam\s*(\d+)?\s*\{\s*(\w+)\s*\{(.*?)\}\s*\}", grf, re.S):
        if m.group(1):
            num = int(m.group(1))
        d = re.search(r"def_value:\s*(\d+)", m.group(3))
        values[num] = OVERRIDES.get(m.group(2), int(d.group(1)) if d else 0)
        num += 1
    return [values.get(i, 0) for i in range(max(values) + 1)]


def write_profile(home, gs_dir, gs_name):
    data = os.path.join(home, "data", "openttd")
    for sub in ("newgrf", "game"):
        os.makedirs(os.path.join(data, sub), exist_ok=True)
    shutil.copy(GRF, os.path.join(data, "newgrf"))
    shutil.copytree(gs_dir, os.path.join(data, "game", os.path.basename(gs_dir)))
    cfg = os.path.join(home, "openttd.cfg")
    with open(cfg, "w") as f:
        f.write("""[misc]
language = english.lng

[game_creation]
map_x = 8
map_y = 8
landscape = temperate
starting_year = 1985
town_name = english

[difficulty]
industry_density = 5
number_towns = 2

[construction]
raw_industry_construction = 1

[newgrf]
energy_transition.grf = %s

[game_scripts]
"%s" =
""" % (" ".join(str(v) for v in grf_params()), gs_name))
    return cfg


def run(openttd, gs_dir, gs_name, ticks, seed, keep):
    home = tempfile.mkdtemp(prefix="et_ingame_")
    try:
        cfg = write_profile(home, gs_dir, gs_name)
        env = dict(os.environ, HOME=home, XDG_DATA_HOME=os.path.join(home, "data"),
                   XDG_CONFIG_HOME=os.path.join(home, "config"))
        cmd = [openttd, "-x", "-c", cfg, "-g", "-G", str(seed), "-v", "null:ticks=%d" % ticks,
               "-s", "null", "-m", "null", "-b", "8bpp-optimized", "-d", "grf=1,script=4"]
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
        return p.returncode, p.stdout + p.stderr
    finally:
        if keep:
            print("profile kept in", home)
        else:
            shutil.rmtree(home, ignore_errors=True)


GRF_PROBLEM = re.compile(r"\[grf\].*(error|fatal|disabl|invalid|unknown|not found)", re.I)
SCRIPT_ERROR = re.compile(r"your script made an error|script.*(crashed|died)|\[script\].*\[E\]", re.I)


def common_problems(out):
    probs = [l for l in out.splitlines() if GRF_PROBLEM.search(l)]
    if "energy_transition.grf" in out and re.search(r"not found|missing", out, re.I):
        probs += [l for l in out.splitlines() if "energy_transition" in l and re.search(r"not found|missing", l, re.I)]
    return probs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--openttd", default=shutil.which("openttd") or "/usr/games/openttd")
    ap.add_argument("--ticks", type=int, default=74 * 110, help="game ticks per run (74 = one day)")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--keep", action="store_true", help="keep the temp profiles for inspection")
    ap.add_argument("-v", "--verbose", action="store_true", help="print OpenTTD's full output")
    a = ap.parse_args()
    if not os.path.exists(a.openttd):
        sys.exit("OpenTTD not found; pass --openttd PATH (e.g. apt install openttd openttd-opengfx)")

    ok = True
    print("== run 1: chain and production checks (tools/ingame_check_gs)")
    rc, out = run(a.openttd, CHECK_GS, "Energy Transition In-game Check", a.ticks, a.seed, a.keep)
    if a.verbose:
        print(out)
    lines = [l.split("ETCHECK ", 1)[1] for l in out.splitlines() if "ETCHECK " in l]
    for l in lines:
        print("  " + l)
    probs = common_problems(out) + [l for l in out.splitlines() if SCRIPT_ERROR.search(l) and "ETCHECK" not in l]
    for l in probs:
        print("  PROBLEM " + l)
    if rc != 0 or probs or not any(l.startswith("DONE failures=0") for l in lines):
        ok = False
        if not any(l.startswith("DONE") for l in lines):
            print("  FAIL the check script never finished (exit %d). Last output:" % rc)
            print("\n".join("    " + l for l in out.splitlines()[-25:]))

    print("== run 2: real Game Script (energy_transition_gs)")
    rc, out = run(a.openttd, REAL_GS, "Energy Transition Power Grid", 74 * 40, a.seed, a.keep)
    if a.verbose:
        print(out)
    gs = [l for l in out.splitlines() if "[script]" in l]
    for l in gs[:15]:
        print("  " + l.strip())
    probs = common_problems(out) + [l for l in out.splitlines() if SCRIPT_ERROR.search(l)]
    started = any("Energy Transition GS started" in l for l in gs)
    found = any("Found POWR cargo" in l for l in gs)
    for l in probs:
        print("  PROBLEM " + l)
    if not started:
        print("  FAIL the Game Script did not start")
    if not found:
        print("  FAIL the Game Script did not find the POWR cargo")
    if rc != 0 or probs or not started or not found:
        ok = False

    print("== %s" % ("PASS" if ok else "FAIL"))
    print("(Headless only: art, cargo icons and animation still need checking in a real game.)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
