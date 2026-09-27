#!/usr/bin/env python3
"""
Compose each industry from the generated sprite sheets the way OpenTTD
places them (ground first, then buildings back-to-front) and write an
RGB preview image.  Useful for checking art and offsets without
launching the game.

Usage:
    python3 tools/preview.py [out.png] [--scale 1|2] [--zoom N]
"""

import argparse
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sprites as ms  # noqa: E402

# industry → list of (x, y, tile_key, ground) in tilelayout coordinates.
# Must mirror the tilelayouts in energy_transition.nml.
LAYOUTS = {
    "hydro_dam": [(0, 0, "hydro_dam_n"), (0, 1, "hydro_dam_s"), (1, 0, "hydro_power_n"), (1, 1, "hydro_power_s")],
    "uranium_mine": [(0, 0, "uranium_headframe"), (1, 0, "uranium_mill"), (0, 1, "uranium_tailings"),
                     (1, 1, "uranium_ore")],
    "nuclear_plant": [(0, 0, "nuc_cooling"), (0, 1, "nuc_cooling"), (0, 2, "nuc_switchyard"),
                      (1, 0, "nuc_turbine2"), (1, 1, "nuc_reactor"), (1, 2, "nuc_turbine"),
                      (2, 0, "nuc_intake"), (2, 1, "nuc_admin"), (2, 2, "nuc_tanks")],
    "tidal_station": [(0, 0, "tidal_barrage"), (1, 0, "tidal_hall")],
    "wind_farm": [(0, 0, "wind_a"), (1, 0, "wind_b"), (0, 1, "wind_c"), (1, 1, "wind_d")],
    "solar_farm": [(0, 0, "solar_panels"), (1, 0, "solar_panels"), (2, 0, "solar_inverter"),
                   (0, 1, "solar_control"), (1, 1, "solar_panels"), (2, 1, "solar_panels")],
    "substation": [(0, 0, "sub_transformers"), (1, 0, "sub_pylon")],
    "coal_power_plant": [(0, 0, "coal_boiler"), (1, 0, "coal_yard")],
}


def rgb(im):
    """Palette image → RGBA with index 0 transparent."""
    out = im.convert("RGBA")
    out.putalpha(Image.frombytes("L", im.size, bytes(0 if i == 0 else 255 for i in im.tobytes())))
    return out


def compose(name, s):
    _, H, tiles = ms.INDUSTRIES[name]
    keys = [k for k, _ in tiles]
    sheet = Image.open(os.path.join(ms.OUT, "%s%s.png" % (name, "_2x" if s == 2 else "")))
    ground = Image.open(os.path.join(ms.OUT, "ground%s.png" % ("_2x" if s == 2 else "")))
    cw, ch = ms.CELL_W * s, (32 + H) * s
    gh = ground.size[1]
    layout = LAYOUTS[name]
    span = max(x + y for x, y, _ in layout) + 1
    w = (64 * span + 64) * s
    h = (H + 16 * span + 40) * s
    canvas = Image.new("RGBA", (w, h), (60, 110, 60, 255))
    ox = (32 + 32 * max(x for x, _, _ in layout)) * s + 32 * s
    oy = (H + 8) * s
    gname = ms.TILE_GROUND
    for x, y, key in sorted(layout, key=lambda t: t[0] + t[1]):
        sx = ox + (y - x) * 32 * s
        sy = oy + (x + y) * 16 * s
        gi = ms.GROUND_ORDER.index(gname.get(key, ms.INDUSTRIES[name][0]))
        g = rgb(ground.crop((gi * cw, 0, gi * cw + cw, gh)))
        canvas.alpha_composite(g, (sx - 31 * s, sy))
    for x, y, key in sorted(layout, key=lambda t: t[0] + t[1]):
        sx = ox + (y - x) * 32 * s
        sy = oy + (x + y) * 16 * s
        k = keys.index(key)
        spr = sheet.crop((k * cw, 0, k * cw + cw, ch))
        canvas.alpha_composite(rgb(spr), (sx - 31 * s, sy - H * s))
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="preview.png")
    ap.add_argument("--scale", type=int, default=1)
    ap.add_argument("--zoom", type=int, default=2)
    a = ap.parse_args()
    parts = [compose(n, a.scale) for n in LAYOUTS]
    W = sum(p.size[0] for p in parts[:4])
    rows = [parts[:4], parts[4:]]
    H = sum(max(p.size[1] for p in r) for r in rows)
    out = Image.new("RGBA", (W, H), (60, 110, 60, 255))
    y = 0
    for r in rows:
        x = 0
        for p in r:
            out.alpha_composite(p, (x, y))
            x += p.size[0]
        y += max(p.size[1] for p in r)
    out = out.resize((W * a.zoom, H * a.zoom), Image.NEAREST)
    out.convert("RGB").save(a.out)
    print("wrote", a.out, out.size)


if __name__ == "__main__":
    main()
