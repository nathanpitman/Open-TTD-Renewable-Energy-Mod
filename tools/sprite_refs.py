#!/usr/bin/env python3
"""
Annotated sprite references (docs/sprite_design_spec.md, section 12).

For every sprite this writes docs/sprites/<key>.png: the 1x sprite on its
ground, enlarged with nearest-neighbour scaling, with every visible part
labelled.  It also writes a part map, the sprite at actual size (1x and
2x), and docs/sprites/index.md listing every sprite's part names.

Part names come from the drawing code: each drawing call in
tools/make_sprites.py runs inside `with cv.part("name"):`, and the canvas
records which part drew each pixel.  A visible pixel with no part name is
an error, so every visible part gets a name.

tools/make_sprites.py runs this after writing the sprite sheets.  To
regenerate only the references:

    python3 tools/sprite_refs.py            # all of them
    python3 tools/sprite_refs.py nuclear_plant ground
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "sprites")

# One reference per review issue (children of #34):
# (file key, title, group, what draws it, review issue, note)
#   tile:   ("tile", industry, tile key)
#   ground: ("ground", kind)
#   icon:   ("icon", cargo label)
REFS = [
    ("hydro_dam_n", "Dam wall", "Hydro Dam", ("tile", "hydro_dam", "hydro_dam_n"), 39,
     "Shown facing north-east. The turned copies (hydro_dam_n_nw, _sw, _se) have the same parts."),
    ("hydro_dam_s", "Dam wall with intake tower", "Hydro Dam", ("tile", "hydro_dam", "hydro_dam_s"), 40,
     "Shown facing north-east. The turned copies (hydro_dam_s_nw, _sw, _se) have the same parts."),
    ("hydro_power_n", "Spillway channel", "Hydro Dam", ("tile", "hydro_dam", "hydro_power_n"), 41,
     "Shown facing north-east. The turned copies (hydro_power_n_nw, _sw, _se) have the same parts."),
    ("hydro_power_s", "Powerhouse", "Hydro Dam", ("tile", "hydro_dam", "hydro_power_s"), 42,
     "Shown facing north-east. The turned copies (hydro_power_s_nw, _sw, _se) have the same parts."),
    ("uranium_headframe", "Headframe", "Uranium Mine", ("tile", "uranium_mine", "uranium_headframe"), 43, None),
    ("uranium_tailings", "Tailings mound", "Uranium Mine", ("tile", "uranium_mine", "uranium_tailings"), 44, None),
    ("uranium_mill", "Processing mill", "Uranium Mine", ("tile", "uranium_mine", "uranium_mill"), 45, None),
    ("uranium_ore", "Ore pile and truck", "Uranium Mine", ("tile", "uranium_mine", "uranium_ore"), 46, None),
    ("nuc_cooling", "Cooling tower", "Nuclear Power Plant", ("tile", "nuclear_plant", "nuc_cooling"), 47,
     "Used on two tiles of the plant."),
    ("nuc_reactor", "Reactor building", "Nuclear Power Plant", ("tile", "nuclear_plant", "nuc_reactor"), 48, None),
    ("nuc_turbine", "Turbine hall (pitched roof)", "Nuclear Power Plant",
     ("tile", "nuclear_plant", "nuc_turbine"), 49, None),
    ("nuc_turbine2", "Turbine hall (flat roof, stack)", "Nuclear Power Plant",
     ("tile", "nuclear_plant", "nuc_turbine2"), 51, None),
    ("nuc_admin", "Admin building and car park", "Nuclear Power Plant",
     ("tile", "nuclear_plant", "nuc_admin"), 52, None),
    ("nuc_intake", "Cooling water intake", "Nuclear Power Plant", ("tile", "nuclear_plant", "nuc_intake"), 53, None),
    ("nuc_switchyard", "Switchyard", "Nuclear Power Plant", ("tile", "nuclear_plant", "nuc_switchyard"), 54, None),
    ("nuc_tanks", "Storage tanks", "Nuclear Power Plant", ("tile", "nuclear_plant", "nuc_tanks"), 55,
     "Tanks are numbered back to front."),
    ("tidal_barrage", "Barrage", "Tidal Station", ("tile", "tidal_station", "tidal_barrage"), 56, None),
    ("tidal_hall", "Turbine hall", "Tidal Station", ("tile", "tidal_station", "tidal_hall"), 57, None),
    ("wind_a", "Wind turbine", "Wind Farm", ("tile", "wind_farm", "wind_a"), 58,
     "Frame 0 of wind_a. wind_b, wind_c, wind_d and every animation frame have the same parts."),
    ("wind_track_x", "Service track", "Wind Farm", ("tile", "wind_farm", "wind_track_x"), 59,
     "wind_track_y is the same track running the other way."),
    ("wind_kiosk", "Grid connection kiosk", "Wind Farm", ("tile", "wind_farm", "wind_kiosk"), 60, None),
    ("solar_panels", "Panel rows", "Solar Farm", ("tile", "solar_farm", "solar_panels"), 61, None),
    ("solar_inverter", "Inverter station", "Solar Farm", ("tile", "solar_farm", "solar_inverter"), 62, None),
    ("solar_control", "Control building", "Solar Farm", ("tile", "solar_farm", "solar_control"), 63, None),
    ("sub_transformers", "Transformer yard", "Substation", ("tile", "substation", "sub_transformers"), 64, None),
    ("sub_switchgear", "Switchgear and control building", "Substation", ("tile", "substation", "sub_switchgear"), 65, None),
    ("ground_grass", "Grass", "Ground tiles", ("ground", "grass"), 68, None),
    ("ground_dirt", "Dirt", "Ground tiles", ("ground", "dirt"), 69, None),
    ("ground_concrete", "Concrete", "Ground tiles", ("ground", "concrete"), 70, None),
    ("ground_water", "Water", "Ground tiles", ("ground", "water"), 71, None),
    ("ground_shore", "Shore", "Ground tiles", ("ground", "shore"), 72, None),
    ("cargo_power", "Power", "Cargo icons", ("icon", "powr"), 73, None),
    ("cargo_uranium", "Uranium", "Cargo icons", ("icon", "uran"), 74, None),
]

ISSUE_URL = "https://github.com/nathanpitman/Open-TTD-Renewable-Energy-Mod/issues/%d"

# Distinct, bright label colours that stand out against the game palette.
PART_COLOURS = [
    (255, 64, 129), (0, 229, 255), (255, 214, 0), (118, 255, 3), (213, 0, 249), (255, 109, 0),
    (41, 121, 255), (29, 233, 182), (255, 23, 68), (174, 234, 0), (101, 31, 255), (255, 171, 64),
    (0, 176, 255), (240, 98, 146), (100, 221, 23), (224, 64, 251),
]
BG = (37, 40, 44)
PANEL = (58, 63, 69)
TEXT = (235, 235, 235)
DIM = (160, 166, 173)
LINE_H = 34
LABEL_W = 300


def _font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "Arial Bold.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf"]
    for n in names:
        for d in ("/usr/share/fonts/truetype/dejavu", "/Library/Fonts", "C:/Windows/Fonts", ""):
            try:
                return ImageFont.truetype(os.path.join(d, n) if d else n, size)
            except OSError:
                pass
    return ImageFont.load_default(size)


# ── Rendering one sprite with its part names ──────────────────────────
def _tile_draw(ms, industry, key):
    for k, draw in ms.INDUSTRIES[industry][2]:
        if k == key:
            return draw
    raise KeyError(key)


def _render(ms, spec, s):
    """(RGBA image, {(col,row): part} or None) for one sprite at scale s."""
    kind = spec[0]
    if kind == "icon":
        parts = {}
        im = ms.render_icon(ms.CARGO_ICONS[spec[1]], s, parts)
        im.putpalette(ms.PALETTE)
        return _rgba(im), parts
    if kind == "ground":
        parts = {}
        im = ms.ground_tile(spec[1], s, parts)
        return _rgba(im), parts
    _, industry, key = spec
    ground_kind, H, _ = ms.INDUSTRIES[industry]
    ground_kind = ms.TILE_GROUND.get(key, ground_kind)
    cv = ms.Canvas(s, H)
    _tile_draw(ms, industry, key)(cv)
    g = ms.ground_tile(ground_kind, s)
    out = Image.new("RGBA", (cv.w, cv.h), (0, 0, 0, 0))
    out.alpha_composite(_rgba(g), (0, H * s))
    parts = {}
    gpx = g.load()
    for r in range(g.size[1]):
        for c in range(g.size[0]):
            if gpx[c, r]:
                parts[c, r + H * s] = "ground (%s)" % ground_kind
    spr = cv.image()
    out.alpha_composite(_rgba(spr))
    for i, idx in enumerate(cv.px):
        if idx:
            name = cv.parts[i]
            if name is None:
                raise SystemExit("%s: visible pixel at %s has no part name; wrap its drawing call in "
                                 "`with cv.part(...)`" % (key, divmod(i, cv.w)[::-1]))
            parts[i % cv.w, i // cv.w] = name
    return out, parts


def _rgba(im):
    out = im.convert("RGBA")
    out.putalpha(Image.frombytes("L", im.size, bytes(0 if i == 0 else 255 for i in im.tobytes())))
    return out


# ── Label layout ───────────────────────────────────────────────────────
def _depth(pts):
    """Steps from each pixel to the nearest pixel outside the set (capped at 3)."""
    s = set(pts)
    depth = {}
    frontier = [p for p in pts if any((p[0] + dx, p[1] + dy) not in s
                                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for p in frontier:
        depth[p] = 1
    k = 1
    while frontier and k < 3:
        k += 1
        nxt = []
        for p in frontier:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (p[0] + dx, p[1] + dy)
                if q in s and q not in depth:
                    depth[q] = k
                    nxt.append(q)
        frontier = nxt
    return {p: depth.get(p, 3) for p in pts}


def _anchors(parts):
    """part → the pixel its label points at: well inside the part, near its
    middle, and clear of the other parts' anchors.  Small parts go first."""
    by = {}
    for (c, r), name in parts.items():
        by.setdefault(name, []).append((c, r))
    out = {}
    for name in sorted(by, key=lambda n: (len(by[n]), n)):
        pts = by[name]
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        depth = _depth(pts)

        def score(p):
            crowd = sum(1 for a in out.values() if abs(a[0] - p[0]) <= 3 and abs(a[1] - p[1]) <= 3)
            return (crowd, -depth[p], (p[0] - mx) ** 2 + (p[1] - my) ** 2, p)
        out[name] = min(pts, key=score)
    return out


def _stack(items, top, bottom):
    """items: [(target_y, name)] sorted by target; returns [(y, name)] spaced LINE_H apart."""
    ys = []
    for t, _ in items:
        ys.append(max(t, ys[-1] + LINE_H if ys else top))
    for i in range(len(ys) - 1, -1, -1):
        limit = bottom if i == len(ys) - 1 else ys[i + 1] - LINE_H
        ys[i] = max(top, min(ys[i], limit))
    return [(y, n) for y, (_, n) in zip(ys, items)]


def _sides(anchors, mid):
    names = sorted(anchors, key=lambda n: (anchors[n][0], anchors[n][1], n))
    left = [n for n in names if anchors[n][0] < mid]
    right = [n for n in names if anchors[n][0] >= mid]
    # keep the columns balanced, moving the parts nearest the middle
    while len(left) > len(right) + 1:
        right.insert(0, left.pop())
    while len(right) > len(left) + 1:
        left.append(right.pop(0))
    return left, right


# ── The reference image ───────────────────────────────────────────────
def render_reference(ms, key, title, group, spec, issue, note):
    img1, parts = _render(ms, spec, 1)
    img2, _ = _render(ms, spec, 2)
    bbox = img1.getbbox()
    x0, y0 = max(0, bbox[0] - 1), max(0, bbox[1] - 1)
    x1, y1 = min(img1.size[0], bbox[2] + 1), min(img1.size[1], bbox[3] + 1)
    img1 = img1.crop((x0, y0, x1, y1))
    img2 = img2.crop((x0 * 2, y0 * 2, x1 * 2, y1 * 2))
    parts = {(c - x0, r - y0): n for (c, r), n in parts.items() if x0 <= c < x1 and y0 <= r < y1}
    w1, h1 = img1.size
    zoom = max(4, min(8, 560 // max(w1, 1))) if spec[0] != "icon" else 32

    anchors = _anchors(parts)
    colours = {}
    for n in sorted(anchors, key=lambda n: (anchors[n][1], anchors[n][0], n)):
        colours[n] = PART_COLOURS[len(colours) % len(PART_COLOURS)]
    left, right = _sides(anchors, w1 / 2)

    f_title, f_sub, f_label, f_cap = _font(30, True), _font(17), _font(19), _font(16)
    pad = 24
    header_h = 118 if note else 94
    sw, sh = w1 * zoom, h1 * zoom
    main_h = max(sh, LINE_H * max(len(left), len(right)) + LINE_H)
    mid_x0 = pad + LABEL_W + pad
    W = mid_x0 + sw + pad + LABEL_W + pad
    zm = max(2, zoom // 2)
    foot_h = max(h1 * zm, img2.size[1]) + 44
    H = header_h + main_h + pad + foot_h + pad
    W = max(W, pad * 4 + w1 * zm + w1 + img2.size[0] + 3 * 40)

    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)

    # header
    d.text((pad, 18), "%s \u2013 %s" % (group, title), font=f_title, fill=TEXT)
    if spec[0] == "tile":
        what = "tile %s \u00b7 drawn by %s() in tools/make_sprites.py" % (spec[2], _fn_name(ms, spec))
    elif spec[0] == "ground":
        what = "ground tile \"%s\" \u00b7 drawn by ground_colour() in tools/make_sprites.py" % spec[1]
    else:
        what = "cargo icon %s \u00b7 drawn by %s() in tools/make_sprites.py" % (
            spec[1], ms.CARGO_ICONS[spec[1]].__name__)
    d.text((pad, 58), "%s \u00b7 review issue #%d \u00b7 1x sprite shown at %d\u00d7" % (what, issue, zoom),
           font=f_sub, fill=DIM)
    if note:
        d.text((pad, 82), note, font=f_sub, fill=DIM)

    # enlarged sprite
    top = header_h + (main_h - sh) // 2
    d.rectangle((mid_x0 - 4, top - 4, mid_x0 + sw + 4, top + sh + 4), fill=PANEL)
    big = img1.resize((sw, sh), Image.NEAREST)
    im.paste(big, (mid_x0, top), big)

    def anchor_xy(n):
        c, r = anchors[n]
        return mid_x0 + int((c + 0.5) * zoom), top + int((r + 0.5) * zoom)

    lo, hi = header_h + LINE_H // 2, header_h + main_h - LINE_H // 2
    for names, side in ((left, "left"), (right, "right")):
        placed = _stack(sorted(((anchor_xy(n)[1], n) for n in names)), lo, hi)
        for y, n in placed:
            col = colours[n]
            ax, ay = anchor_xy(n)
            if side == "left":
                ex = pad + LABEL_W
                d.line((ex, y, ax, ay), fill=(0, 0, 0), width=5)
                d.line((ex, y, ax, ay), fill=col, width=3)
                d.rectangle((ex - 18, y - 9, ex, y + 9), fill=col, outline=(0, 0, 0))
                tw = d.textlength(n, font=f_label)
                d.text((ex - 26 - tw, y - 12), n, font=f_label, fill=TEXT)
            else:
                sx = mid_x0 + sw + pad
                d.line((sx, y, ax, ay), fill=(0, 0, 0), width=5)
                d.line((sx, y, ax, ay), fill=col, width=3)
                d.rectangle((sx, y - 9, sx + 18, y + 9), fill=col, outline=(0, 0, 0))
                d.text((sx + 26, y - 12), n, font=f_label, fill=TEXT)
            d.ellipse((ax - 6, ay - 6, ax + 6, ay + 6), fill=(0, 0, 0))
            d.ellipse((ax - 4, ay - 4, ax + 4, ay + 4), fill=col)

    # footer: part map, actual size 1x and 2x
    fy = header_h + main_h + pad
    x = pad
    pm = Image.new("RGB", (w1, h1), PANEL)
    ppx = pm.load()
    for (c, r), n in parts.items():
        ppx[c, r] = colours[n]
    pm = pm.resize((w1 * zm, h1 * zm), Image.NEAREST)
    for img, cap in ((pm, "part map"), (img1, "1x sprite, actual size"), (img2, "2x sprite, actual size")):
        d.text((x, fy), cap, font=f_cap, fill=DIM)
        d.rectangle((x - 2, fy + 26, x + img.size[0] + 2, fy + 28 + img.size[1]), fill=PANEL)
        if img.mode == "RGBA":
            im.paste(img, (x, fy + 28), img)
        else:
            im.paste(img, (x, fy + 28))
        x += max(img.size[0], int(d.textlength(cap, font=f_cap))) + 40

    order = sorted(anchors, key=lambda n: (anchors[n][1], anchors[n][0], n))
    return im, order


def _fn_name(ms, spec):
    draw = _tile_draw(ms, spec[1], spec[2])
    name = getattr(draw, "__name__", "")
    if name == "<lambda>" and spec[1] == "wind_farm":
        return "wind_turbine"
    return name


# ── Writing everything ─────────────────────────────────────────────────
def _selected(spec, only):
    if not only:
        return True
    if spec[0] == "tile":
        return spec[1] in only
    return {"ground": "ground", "icon": "cargo_icons"}[spec[0]] in only


def write_all(ms, only=()):
    os.makedirs(OUT, exist_ok=True)
    index = []
    for key, title, group, spec, issue, note in REFS:
        path = os.path.join(OUT, key + ".png")
        if _selected(spec, only):
            im, order = render_reference(ms, key, title, group, spec, issue, note)
            im.save(path, optimize=True)
            print("wrote", os.path.relpath(path, ROOT), im.size)
        else:
            _, parts = _render(ms, spec, 1)
            anchors = _anchors(parts)
            order = sorted(anchors, key=lambda n: (anchors[n][1], anchors[n][0], n))
        index.append((key, title, group, spec, issue, note, order))
    _write_index(index)


def _write_index(index):
    lines = [
        "# Sprite part names",
        "",
        "Generated by `tools/sprite_refs.py` (run by `tools/make_sprites.py`). Do not edit by hand.",
        "",
        "Every sprite has an annotated reference image in this folder that labels each visible part. "
        "Use these names when asking for a change, for example \"make the turbine blades thicker\". "
        "See section 12 of [the sprite design spec](../sprite_design_spec.md).",
        "",
        "Parts are listed from the top of the sprite down. Industry tiles also label the ground "
        "they stand on.",
        "",
    ]
    group = None
    for key, title, g, spec, issue, note, order in index:
        if g != group:
            lines += ["## " + g, ""]
            group = g
        lines.append("### %s" % title)
        lines.append("")
        where = ("tile `%s`" % spec[2]) if spec[0] == "tile" else (
            "ground `%s`" % spec[1] if spec[0] == "ground" else "cargo icon `%s`" % spec[1])
        lines.append("[`%s.png`](%s.png) \u00b7 %s \u00b7 review [#%d](%s)" % (key, key, where, issue, ISSUE_URL % issue))
        lines.append("")
        if note:
            lines += [note, ""]
        lines += ["- " + n for n in order]
        lines.append("")
    path = os.path.join(OUT, "index.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote", os.path.relpath(path, ROOT))


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import make_sprites as ms
    write_all(ms, set(sys.argv[1:]))


if __name__ == "__main__":
    main()
