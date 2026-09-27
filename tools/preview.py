#!/usr/bin/env python3
"""
Compose each industry from the generated sprite sheets the way OpenTTD
places them (ground first, then buildings back-to-front) and write an
RGB preview image.  Useful for checking art and offsets without
launching the game.

Usage:
    python3 tools/preview.py [out.png] [--scale 1|2] [--zoom N]
    python3 tools/preview.py --each docs/industries [--scale 1|2] [--zoom N]
"""

import argparse
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_sprites as ms  # noqa: E402

# industry[/variant] → list of (x, y, tile_key) in tilelayout coordinates;
# tile_key None is a ground-only tile.  Must mirror the tilelayouts in
# energy_transition.nml.
_HYDRO = [(0, 0, "hydro_dam_n"), (0, 1, "hydro_dam_s"), (1, 0, "hydro_power_n"), (1, 1, "hydro_power_s")]
# the hydro dam in its other three facings: the 2x2 site turned about its centre
_HYDRO_TURN = {"nw": lambda x, y: (1 - y, x), "sw": lambda x, y: (1 - x, 1 - y), "se": lambda x, y: (y, 1 - x)}

LAYOUTS = {
    "hydro_dam": _HYDRO,
    **{"hydro_dam/" + f: [turn(x, y) + ("%s_%s" % (k, f),) for x, y, k in _HYDRO]
       for f, turn in _HYDRO_TURN.items()},
    "uranium_mine": [(0, 0, "uranium_headframe"), (1, 0, "uranium_mill"), (0, 1, "uranium_tailings"),
                     (1, 1, "uranium_ore")],
    "nuclear_plant": [(0, 0, "nuc_cooling"), (0, 1, "nuc_cooling"), (0, 2, "nuc_switchyard"),
                      (1, 0, "nuc_turbine2"), (1, 1, "nuc_reactor"), (1, 2, "nuc_turbine"),
                      (2, 0, "nuc_intake"), (2, 1, "nuc_admin"), (2, 2, "nuc_tanks")],
    "tidal_station": [(0, 0, "tidal_barrage"), (1, 0, "tidal_hall")],
    "wind_farm": [(0, 0, "wind_a"), (1, 0, "wind_track_x"), (2, 0, "wind_c"),
                  (0, 1, "wind_track_y"), (1, 1, "wind_kiosk"), (2, 1, "wind_track_y"),
                  (0, 2, "wind_b"), (1, 2, "wind_track_x"), (2, 2, "wind_d")],
    "wind_farm/line_x": [(0, 0, "wind_a"), (1, 0, "wind_track_x"), (2, 0, "wind_d")],
    "wind_farm/line_y": [(0, 0, "wind_c"), (0, 1, "wind_track_y"), (0, 2, "wind_b")],
    "wind_farm/2x2": [(0, 0, None), (1, 0, "wind_b"), (0, 1, "wind_c"), (1, 1, "wind_kiosk")],
    "wind_farm/single": [(0, 0, "wind_a")],
    "solar_farm": [(0, 0, "solar_panels"), (1, 0, "solar_panels"), (2, 0, "solar_inverter"),
                   (0, 1, "solar_control"), (1, 1, "solar_panels"), (2, 1, "solar_panels")],
    "substation": [(0, 0, "sub_transformers"), (1, 0, "sub_pylon")],
}


def rgb(im):
    """Palette image → RGBA with index 0 transparent."""
    out = im.convert("RGBA")
    out.putalpha(Image.frombytes("L", im.size, bytes(0 if i == 0 else 255 for i in im.tobytes())))
    return out


def compose(variant, s, bg=(60, 110, 60, 255)):
    name = variant.split("/")[0]
    _, H, tiles = ms.INDUSTRIES[name]
    keys = [k for k, _ in tiles]
    sheet = Image.open(os.path.join(ms.OUT, "%s%s.png" % (name, "_2x" if s == 2 else "")))
    ground = Image.open(os.path.join(ms.OUT, "ground%s.png" % ("_2x" if s == 2 else "")))
    cw, ch = ms.CELL_W * s, (32 + H) * s
    gh = ground.size[1]
    layout = LAYOUTS[variant]
    span = max(x + y for x, y, _ in layout) + 1
    w = (64 * span + 64) * s
    h = (H + 16 * span + 40) * s
    canvas = Image.new("RGBA", (w, h), bg)
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
        if key is None:
            continue
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
    ap.add_argument("--each", metavar="DIR",
                    help="write one transparent, cropped image per industry into DIR")
    a = ap.parse_args()
    if a.each:
        os.makedirs(a.each, exist_ok=True)
        for n in LAYOUTS:
            if "/" in n:
                continue
            im = compose(n, a.scale, bg=(0, 0, 0, 0))
            im = im.crop(im.getbbox())
            im = im.resize((im.size[0] * a.zoom, im.size[1] * a.zoom), Image.NEAREST)
            path = os.path.join(a.each, n + ".png")
            im.save(path)
            print("wrote", path, im.size)
        return
    parts = [compose(n, a.scale) for n in LAYOUTS]
    per_row = 5
    rows = [parts[i:i + per_row] for i in range(0, len(parts), per_row)]
    W = max(sum(p.size[0] for p in r) for r in rows)
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
