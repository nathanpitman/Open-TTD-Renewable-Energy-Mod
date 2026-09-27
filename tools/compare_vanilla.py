#!/usr/bin/env python3
"""
Side-by-side comparison of our industry sprites against vanilla OpenGFX
buildings, without launching OpenTTD.

Each panel shows a vanilla building (with vanilla ground) on one tile and the
matching tile of ours on the next, both at 1x zoom, using the sprites' real
offsets.  Use it to review lighting, scale, colour and detail level against
the base game (see issue #76 for the lighting question).

Usage:
    python3 tools/compare_vanilla.py [out.png] [--opengfx PATH] [--zoom N]

PATH is OpenGFX's `ogfx1_base.grf`, a directory containing it, or an
OpenGFX .tar from OpenTTD's content download.  Without --opengfx the usual
OpenTTD install locations are searched.  OpenGFX is GPL-2.0 and is read
from your install, never copied into this repository; don't commit the
output image either, since it contains OpenGFX art.
"""

import argparse
import glob
import os
import sys
import tarfile
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grf_reader  # noqa: E402
import make_sprites as ms  # noqa: E402
from preview import rgb  # noqa: E402

# (label, vanilla sprites [(sprite, dx, dy)], vanilla ground sprite, our tile key)
# Sprite numbers are OpenGFX ogfx1_base.grf positions (the TTD base sprite
# numbers).  dx/dy nudge a vanilla sprite in screen pixels, because vanilla
# industries place their sprites at sub-tile offsets we don't reproduce.
V_GRASS, V_PAVED, V_DIRT = 3981, 1420, 2022
PAIRS = [
    ("cooling tower", [(2047, 0, 4)], V_PAVED, "nuc_cooling"),
    ("mine headframe", [(2028, 0, 0)], V_DIRT, "uranium_headframe"),
    ("office block", [(1423, 0, 0)], V_PAVED, "nuc_admin"),
    ("factory shed", [(2190, 0, 0)], V_PAVED, "tidal_hall"),
    ("tanks", [(2080, -6, 0), (2082, 10, 4)], V_PAVED, "nuc_tanks"),
    ("brick hall", [(2171, 0, 0)], V_PAVED, "hydro_power_s"),
    ("town house", [(1425, 0, 0)], V_GRASS, "sub_pylon"),
]

SEARCH = [
    "~/.local/share/openttd/baseset",
    "~/.local/share/openttd/content_download/baseset",
    "~/.openttd/baseset",
    "~/Documents/OpenTTD/baseset",
    "~/Documents/OpenTTD/content_download/baseset",
    "/usr/share/games/openttd/baseset",
    "/usr/share/openttd/baseset",
    "/Applications/OpenTTD.app/Contents/Resources/baseset",
]


def find_opengfx(path=None):
    """Return a filesystem path to ogfx1_base.grf (extracting from a .tar if needed)."""
    candidates = [path] if path else [os.path.expanduser(p) for p in SEARCH]
    for c in candidates:
        if not c or not os.path.exists(c):
            continue
        if os.path.isfile(c) and c.endswith(".grf"):
            return c
        tars = [c] if c.endswith(".tar") else []
        if os.path.isdir(c):
            hits = glob.glob(os.path.join(c, "**", "ogfx1_base.grf"), recursive=True)
            if hits:
                return hits[0]
            tars = glob.glob(os.path.join(c, "**", "*.tar"), recursive=True)
        for t in tars:
            with tarfile.open(t) as tf:
                for m in tf.getmembers():
                    if m.name.endswith("ogfx1_base.grf"):
                        out = os.path.join(tempfile.mkdtemp(), "ogfx1_base.grf")
                        with open(out, "wb") as f:
                            f.write(tf.extractfile(m).read())
                        return out
    return None


def our_tile(key):
    """(sprite image, H) for one of our tile keys, from the 1x sheets."""
    for name, (_, H, tiles) in ms.INDUSTRIES.items():
        keys = [k for k, _ in tiles]
        if key in keys:
            sheet = Image.open(os.path.join(ms.OUT, name + ".png"))
            k = keys.index(key)
            cw, ch = ms.CELL_W, 32 + H
            return sheet.crop((k * cw, 0, (k + 1) * cw, ch)), H, name
    raise KeyError(key)


def our_ground(key, industry):
    kind = ms.TILE_GROUND.get(key, ms.INDUSTRIES[industry][0])
    gi = ms.GROUND_ORDER.index(kind)
    ground = Image.open(os.path.join(ms.OUT, "ground.png"))
    return ground.crop((gi * ms.CELL_W, 0, (gi + 1) * ms.CELL_W, ground.size[1]))


def panel(grf, label, vanilla, v_ground, key, bg):
    """Vanilla tile on the left, our tile on the right, on the same screen row."""
    top, gap = 84, 12  # room above the tiles for tall buildings; space between tiles
    w, h = 16 + 64 * 2 + gap + 8, 14 + top + 32 + 14
    im = Image.new("RGBA", (w, h), bg)
    vx, ux, oy = 16 + 31, 16 + 64 + gap + 31, 14 + top  # tile north corners

    g = grf.sprite(v_ground)
    im.alpha_composite(rgb(g.image), (vx + g.xoff, oy + g.yoff))
    for n, dx, dy in vanilla:
        s = grf.sprite(n)
        im.alpha_composite(rgb(s.image), (vx + s.xoff + dx, oy + s.yoff + dy))

    sprite, H, industry = our_tile(key)
    im.alpha_composite(rgb(our_ground(key, industry)), (ux - 31, oy))
    im.alpha_composite(rgb(sprite), (ux - 31, oy - H))

    d = ImageDraw.Draw(im)
    d.text((4, 1), label, fill=(255, 255, 255, 255))
    d.text((vx - 18, h - 12), "OpenGFX", fill=(230, 230, 230, 255))
    d.text((ux - 10, h - 12), "ours", fill=(230, 230, 230, 255))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="vanilla_compare.png")
    ap.add_argument("--opengfx", help="ogfx1_base.grf, a directory containing it, or an OpenGFX .tar")
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()

    path = find_opengfx(a.opengfx)
    if not path:
        sys.exit("OpenGFX not found. Pass --opengfx PATH, or install it (OpenTTD's "
                 "content download, or e.g. `apt install openttd-opengfx`).")
    grf = grf_reader.GRF(path, ms.PALETTE)

    bg = (60, 110, 60, 255)
    panels = [panel(grf, *p, bg=bg) for p in PAIRS]
    pw, ph = panels[0].size
    rows = (len(panels) + a.cols - 1) // a.cols
    out = Image.new("RGBA", (pw * a.cols, ph * rows), bg)
    for i, p in enumerate(panels):
        out.alpha_composite(p, ((i % a.cols) * pw, (i // a.cols) * ph))
    out = out.resize((out.size[0] * a.zoom, out.size[1] * a.zoom), Image.NEAREST)
    out.convert("RGB").save(a.out)
    print("wrote", a.out, out.size, "using", path)


if __name__ == "__main__":
    main()
