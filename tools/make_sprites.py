#!/usr/bin/env python3
"""
Procedural sprite generator for the Energy Transition NewGRF.

Renders every industry tile and ground tile from simple 3D primitives
(boxes, tapered cylinders, domes, quads, height-field mounds) into
8bpp PNGs that use OpenTTD's DOS palette exactly as nmlc expects it.
Only 1x (ZOOM_LEVEL_NORMAL) sprites are shipped, like almost all NewGRFs:
OpenTTD enlarges them when zoomed in, as it does the base graphics (see
docs/sprite_design_spec.md, section 2).  The canvas can still render at
other scales, which tools/sprite_refs.py does not need but keeps possible.

Usage:
    pip install nml pillow
    python3 tools/make_sprites.py          # writes sprites/*.png
    python3 tools/make_sprites.py cargo_icons   # just one sheet (or an industry name)

It also writes the annotated references in docs/sprites/ (see
tools/sprite_refs.py).  Wrap every drawing call in `with cv.part("name"):`
so each visible part is named there.

Conventions (see README "Sprites" section):
  * World units: one tile is 16x16, one height level is 8 units.
    +x points to the lower-left of the screen (SW), +y to the lower-right
    (SE), +z is up.  Projection matches OpenTTD: X = 2(y-x), Y = x+y-z.
  * Light comes from high up at the lower right of the screen ("4:30"),
    as in original TTD art (OpenTTD wiki, NewGRF "Recommended Standards"):
    roofs are brightest, SE-facing (right) walls are lit, SW-facing (left)
    walls are in shade, and shadows would fall towards the top-left.
  * Index 0 is transparent.  Only non-animated palette entries are used,
    except the sea-water cycle (245-249) on water surfaces, which makes
    water animate like the base game's.
  * Every sheet holds one sprite per distinct industry tile, laid out
    left to right, each cell CELL_W*scale wide and (32+H)*scale high
    with offsets (-31*scale, -H*scale).  nmlc crops the empty borders.
"""

import contextlib
import math
import os
import re
import sys

from PIL import Image

try:
    from nml import palette as nml_palette
except ImportError:  # pragma: no cover
    sys.exit("nml is required (pip install nml) - its DOS palette is used verbatim")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "sprites")
PALETTE = list(nml_palette.raw_palette_data[0])  # DEFAULT (DOS) palette

CELL_W = 64
LIGHT = (-0.15, 0.55, 0.82)  # world (x, y, z): from +y (screen lower right), high up
_l = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _l for c in LIGHT)

# ── Palette ramps (dark → light), DOS palette indices ─────────────────
GREY = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
WHITE = [7, 8, 9, 10, 11, 12, 13, 14, 15]
STEEL = [16, 17, 18, 19, 20, 21, 22, 23]
CONCRETE = [5, 6, 7, 8, 9, 10, 11, 12]
BEIGE = [32, 33, 34, 35, 36, 37, 38, 39]
SAND = [56, 57, 58, 59, 37, 38]
BRICK = [72, 73, 74, 75, 76, 77, 78]
RED = [178, 179, 180, 181, 182, 183, 184]
YELLOW = [62, 63, 64, 65, 66, 67, 68]
GRASS = [80, 81, 82, 83, 84, 85, 86, 87]  # 2nd company colour, as base-game grass; never recoloured
DIRT = [104, 105, 106, 107, 108, 109, 110, 111]
TAILINGS = [24, 25, 26, 27, 28, 29, 30]
COAL = [1, 2, 3, 4, 5, 6]
TOWER = [105, 32, 33, 34, 35, 36, 37]  # weathered cooling-tower concrete, as the base-game power station
PANEL = [128, 129, 130, 131, 132, 133]
GLASS = [198, 199, 200, 201, 202, 203, 204, 205]  # 1st company colour, as base-game windows; never recoloured
WATER = [245, 246, 247, 248, 249]
GREEN_ROOF = [96, 97, 98, 99, 100, 101]
BLUE_ROOF = [154, 155, 156, 157, 158, 159]
PORCELAIN = [112, 113, 114, 115, 116, 117]  # brown glazed insulators


def hash01(*v):
    """Deterministic pseudo-random value in [0,1) from world coordinates."""
    h = 0
    for n in v:
        h = (h * 1000003) ^ (int(math.floor(n)) & 0xFFFFFFFF)
        h &= 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0x5BD1E995) & 0xFFFFFFFF
    h ^= h >> 15
    return (h & 0xFFFF) / 65536.0


def shade(normal):
    nx, ny, nz = normal
    l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    d = (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / l
    return 0.25 + 0.75 * max(0.0, d)


class Material:
    """Maps (point, normal) to a palette index."""

    def __init__(self, ramp, noise=0.0, grain=1.0, bias=0.0, pattern=None):
        self.ramp, self.noise, self.grain, self.bias, self.pattern = ramp, noise, grain, bias, pattern

    def colour(self, p, n):
        if self.pattern:
            c = self.pattern(p, n)
            if c is not None:
                return c
        b = shade(n) + self.bias
        if self.noise:
            g = self.grain
            b += (hash01(p[0] / g, p[1] / g, p[2] / g) - 0.5) * self.noise
        i = int(round(b * (len(self.ramp) - 1)))
        return self.ramp[max(0, min(len(self.ramp) - 1, i))]


class Canvas:
    """A single sprite: z-buffered point-splat rasteriser in world space."""

    def __init__(self, scale, height):
        self.s = scale
        self.H = height
        self.w = CELL_W * scale
        self.h = (32 + height) * scale
        self.xoff = -31 * scale
        self.yoff = -height * scale
        self.px = [0] * (self.w * self.h)
        self.depth = [-1e9] * (self.w * self.h)
        self.step = 0.2 / scale
        # name of the part that drew each pixel, for the annotated references
        self.parts = [None] * (self.w * self.h)
        self._part = [None]

    @contextlib.contextmanager
    def part(self, name):
        """Tag everything drawn inside the block with a part name.  The
        innermost name wins, so shared helpers keep their own name."""
        self._part.append(name)
        try:
            yield
        finally:
            self._part.pop()

    # -- low level --------------------------------------------------------
    def splat(self, p, n, mat):
        x, y, z = p
        X = 2.0 * (y - x)
        Y = x + y - z
        c = int(math.floor((X + 1.0) * self.s - self.xoff))
        r = int(math.floor(Y * self.s - self.yoff))
        if 0 <= c < self.w and 0 <= r < self.h:
            i = r * self.w + c
            d = x + y + z
            if d >= self.depth[i]:
                self.depth[i] = d
                self.px[i] = mat.colour(p, n)
                self.parts[i] = self._part[-1]

    def _n(self, length):
        return max(1, int(math.ceil(abs(length) / self.step)))

    def parallelogram(self, o, u, v, mat, normal=None):
        """Fill o + a*u + b*v for a,b in [0,1]."""
        if normal is None:
            normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            # face the viewer (view direction is +x,+y,+2z)
            if normal[0] + normal[1] + 2 * normal[2] < 0:
                normal = tuple(-c for c in normal)
        lu = math.sqrt(sum(c * c for c in u)) * 2
        lv = math.sqrt(sum(c * c for c in v)) * 2
        nu, nv = self._n(lu), self._n(lv)
        for i in range(nu + 1):
            a = i / nu
            for j in range(nv + 1):
                b = j / nv
                self.splat((o[0] + a * u[0] + b * v[0], o[1] + a * u[1] + b * v[1], o[2] + a * u[2] + b * v[2]),
                           normal, mat)

    # -- primitives -------------------------------------------------------
    def box(self, x0, y0, z0, x1, y1, z1, mat, top=None, side=None):
        top = top or mat
        side = side or mat
        self.parallelogram((x0, y0, z1), (x1 - x0, 0, 0), (0, y1 - y0, 0), top, (0, 0, 1))
        self.parallelogram((x1, y0, z0), (0, y1 - y0, 0), (0, 0, z1 - z0), side, (1, 0, 0))
        self.parallelogram((x0, y1, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0), side, (0, 1, 0))

    def gable(self, x0, y0, z0, x1, y1, z1, ridge, wall, roof, along_x=True):
        """Box with a pitched roof rising to z1+ridge."""
        self.box(x0, y0, z0, x1, y1, z1, wall)
        roof_part = self.part("%s roof" % self._part[-1]) if self._part[-1] else contextlib.nullcontext()
        if along_x:
            ym = (y0 + y1) / 2
            with roof_part:
                self.parallelogram((x0, y0, z1), (x1 - x0, 0, 0), (0, ym - y0, ridge), roof, (0, -ridge, ym - y0))
                self.parallelogram((x0, ym, z1 + ridge), (x1 - x0, 0, 0), (0, y1 - ym, -ridge), roof,
                                   (0, ridge, y1 - ym))
            self._tri_gable_x(x1, y0, y1, z1, ridge, wall)
        else:
            xm = (x0 + x1) / 2
            with roof_part:
                self.parallelogram((x0, y0, z1), (0, y1 - y0, 0), (xm - x0, 0, ridge), roof, (-ridge, 0, xm - x0))
                self.parallelogram((xm, y0, z1 + ridge), (0, y1 - y0, 0), (x1 - xm, 0, -ridge), roof,
                                   (ridge, 0, x1 - xm))
            self._tri_gable_y(y1, x0, x1, z1, ridge, wall)

    def _tri_gable_x(self, x, y0, y1, z, ridge, mat):
        ym = (y0 + y1) / 2
        n = self._n((y1 - y0) * 2)
        for i in range(n + 1):
            yy = y0 + (y1 - y0) * i / n
            h = ridge * (1 - abs(yy - ym) / ((y1 - y0) / 2))
            for k in range(self._n(h) + 1):
                self.splat((x, yy, z + h * k / max(1, self._n(h))), (1, 0, 0), mat)

    def _tri_gable_y(self, y, x0, x1, z, ridge, mat):
        xm = (x0 + x1) / 2
        n = self._n((x1 - x0) * 2)
        for i in range(n + 1):
            xx = x0 + (x1 - x0) * i / n
            h = ridge * (1 - abs(xx - xm) / ((x1 - x0) / 2))
            for k in range(self._n(h) + 1):
                self.splat((xx, y, z + h * k / max(1, self._n(h))), (0, 1, 0), mat)

    def column(self, cx, cy, z0, z1, radius, mat, cap=None, flare=0.0):
        """Vertical solid of revolution. radius may be a number or f(t), t in [0,1]."""
        rf = radius if callable(radius) else (lambda t, r=radius: r)
        height = z1 - z0
        nz = self._n(height)
        rmax = max(rf(k / nz) for k in range(nz + 1))
        na = max(12, int(2 * math.pi * rmax * 2 / self.step))
        for k in range(nz + 1):
            t = k / nz
            r = rf(t)
            dr = (rf(min(1, t + 0.01)) - rf(max(0, t - 0.01))) / 0.02 / max(height, 1e-6)
            z = z0 + height * t
            for a in range(na):
                th = 2 * math.pi * a / na
                ca, sa = math.cos(th), math.sin(th)
                if ca + sa < -0.3:  # back side, never visible
                    continue
                self.splat((cx + r * ca, cy + r * sa, z), (ca, sa, -dr), mat)
        if cap is not False:
            self.disc(cx, cy, z1, rf(1.0), cap or mat)

    def disc(self, cx, cy, z, r, mat, normal=(0, 0, 1)):
        n = self._n(r * 2)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                dx, dy = r * i / n, r * j / n
                if dx * dx + dy * dy <= r * r:
                    self.splat((cx + dx, cy + dy, z), normal, mat)

    def dome(self, cx, cy, z0, r, mat, squash=1.0):
        n = self._n(r * math.pi)
        for i in range(n + 1):
            phi = (math.pi / 2) * i / n
            rr = r * math.cos(phi)
            z = z0 + r * squash * math.sin(phi)
            na = max(8, int(2 * math.pi * rr * 2 / self.step))
            for a in range(na):
                th = 2 * math.pi * a / na
                ca, sa = math.cos(th), math.sin(th)
                self.splat((cx + rr * ca, cy + rr * sa, z),
                           (math.cos(phi) * ca, math.cos(phi) * sa, math.sin(phi) / squash), mat)

    def heightfield(self, x0, y0, x1, y1, f, mat):
        """Surface z=f(x,y) over a rectangle; f returns None for holes."""
        nx, ny = self._n((x1 - x0) * 2), self._n((y1 - y0) * 2)
        e = 0.05
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            for j in range(ny + 1):
                y = y0 + (y1 - y0) * j / ny
                z = f(x, y)
                if z is None:
                    continue
                zx = (f(x + e, y) or z) - (f(x - e, y) or z)
                zy = (f(x, y + e) or z) - (f(x, y - e) or z)
                self.splat((x, y, z), (-zx / (2 * e), -zy / (2 * e), 1.0), mat)
                # skirt down to ground so steep mounds stay solid
                zb = min(f(x + 0.5, y) or 0, f(x, y + 0.5) or 0, z)
                zz = z - self.step
                while zz > zb:
                    self.splat((x, y, zz), (-zx / (2 * e), -zy / (2 * e), 1.0), mat)
                    zz -= self.step

    def beam(self, a, b, w, mat):
        """Thin square-section member from point a to b (lattice work, pipes)."""
        d = [b[i] - a[i] for i in range(3)]
        L = math.sqrt(sum(c * c for c in d)) or 1
        n = self._n(L * 2)
        for k in range(n + 1):
            t = k / n
            p = [a[i] + d[i] * t for i in range(3)]
            for ox, oy, nn in ((w, 0, (1, 0, 0)), (0, w, (0, 1, 0)), (0, 0, (0, 0, 1))):
                self.splat((p[0] + ox * 0.5, p[1] + oy * 0.5, p[2] + (w * 0.5 if nn[2] else 0)), nn, mat)
            if w > 0.6:
                for u in (0.25, -0.25):
                    self.splat((p[0] + w * 0.5, p[1] + w * u, p[2]), (1, 0, 0), mat)
                    self.splat((p[0] + w * u, p[1] + w * 0.5, p[2]), (0, 1, 0), mat)

    def image(self):
        im = Image.new("P", (self.w, self.h), 0)
        im.putpalette(PALETTE)
        im.putdata(self.px)
        return im


# ── Ground tiles ───────────────────────────────────────────────────────
GROUND_ORDER = ["grass", "dirt", "concrete", "water", "shore"]


def ground_colour(kind, x, y):
    """(palette index, part name) of the ground at world point (x, y)."""
    n = hash01(x * 2, y * 2, 7)
    n2 = hash01(x / 3, y / 3, 11)
    if kind == "grass":
        return GRASS[[2, 3, 3, 4, 4, 4, 5, 5, 6][int((n * 0.6 + n2 * 0.4) * 9)]], "grass"
    if kind == "dirt":
        return DIRT[[2, 3, 3, 4, 4, 5, 5, 6][int((n * 0.7 + n2 * 0.3) * 8)]], "dirt"
    if kind == "concrete":
        if (x % 8 < 0.5) or (y % 8 < 0.5):
            return 7, "slab seams"
        return [9, 10, 10, 10, 11][int(n * 5)], "concrete slabs"
    if kind == "water":
        return WATER[int((n * 0.5 + n2 * 0.5) * len(WATER))], "water"
    if kind == "shore":
        edge = 12 + (hash01(x, 3) - 0.5) * 1.5
        if y < edge - 1.2:
            return WATER[int((n * 0.5 + n2 * 0.5) * len(WATER))], "sea"
        if y < edge:
            return (252 if n > 0.6 else 251), "surf"
        return SAND[[1, 2, 2, 3, 3, 4][int(n * 6)]], "sand"
    raise ValueError(kind)


def ground_tile(kind, s, parts=None):
    """64x31 flat ground diamond in the standard TTD pixel shape (scaled).
    If `parts` is a dict, it is filled with (col, row) -> part name."""
    w, h = CELL_W * s, 31 * s + (s - 1)
    im = Image.new("P", (w, h), 0)
    im.putpalette(PALETTE)
    px = im.load()
    half = 16 * s
    for r in range(h):
        rr = r if r < half else (2 * half - 2 - r)
        if rr < 0:
            continue
        width = 4 * rr + 4
        c0 = 32 * s - width // 2
        for c in range(c0, c0 + width):
            X = (c + 0.5) / s - 32.0
            Y = (r + 0.5) / s
            x = (Y - X / 2) / 2
            y = (Y + X / 2) / 2
            px[c, r], name = ground_colour(kind, min(max(x, 0), 15.99), min(max(y, 0), 15.99))
            if parts is not None:
                parts[c, r] = name
    return im


# ── Materials ──────────────────────────────────────────────────────────
M = {
    "concrete": Material(CONCRETE, 0.08),
    "concrete_dark": Material(CONCRETE, 0.08, bias=-0.2),
    "white": Material(WHITE, 0.04),
    "grey": Material(GREY, 0.05),
    "steel": Material(STEEL, 0.05),
    "steel_dark": Material(STEEL, 0.05, bias=-0.25),
    "beige": Material(BEIGE, 0.06),
    "brick": Material(BRICK, 0.12, grain=0.5),
    "red": Material(RED),
    "yellow": Material(YELLOW),
    "tailings": Material(TAILINGS, 0.25, grain=0.7),
    "ore": Material(DIRT, 0.35, grain=0.6, bias=-0.1),
    "coal": Material(COAL, 0.4, grain=0.5),
    "tower": Material(TOWER, 0.12, grain=0.5),
    "panel": Material(PANEL, 0.0),
    "glass": Material(GLASS),
    "water": Material(WATER, 0.6, grain=1.0),
    "green_roof": Material(GREEN_ROOF),
    "blue_roof": Material(BLUE_ROOF),
    "dark": Material([1, 2, 3, 4]),
    "gravel": Material([33, 34, 35, 36, 37], 0.5, grain=0.4),
    "porcelain": Material(PORCELAIN),
}


def windowed(base, glass_idx=201, every=3.0, band=(0.35, 0.7), z_every=5.0, z_band=(0.3, 0.7)):
    """Wall material with a regular grid of windows on vertical faces."""
    def pat(p, n):
        if abs(n[2]) > 0.5:
            return None
        u = p[1] if abs(n[0]) > 0.5 else p[0]
        fu = (u / every) % 1.0
        fz = (p[2] / z_every) % 1.0
        if band[0] < fu < band[1] and z_band[0] < fz < z_band[1]:
            return glass_idx if n[1] > 0.5 else glass_idx - 2  # lit (SE) walls get the lighter glass
        return None
    return Material(base.ramp, base.noise, base.grain, base.bias, pat)


def striped(a, b, period):
    """Horizontal bands (chimney / cooling tower markings)."""
    def pat(p, n):
        return None if (p[2] // period) % 2 == 0 else b.colour(p, n)
    return Material(a.ramp, a.noise, a.grain, a.bias, pat)


# ── Reusable structures ────────────────────────────────────────────────
def transformer(cv, x, y, sx=4, sy=5, h=5, bushings=None):
    """`bushings`: None for plain white ones, or a function drawing one at (x, y, z)."""
    with cv.part("transformer"):
        _transformer(cv, x, y, sx, sy, h, bushings)


def _transformer(cv, x, y, sx, sy, h, bushings):
    cv.box(x, y, 0, x + sx, y + sy, h, M["steel"])
    for k in range(4):  # radiator fins
        cv.box(x + sx, y + 0.6 + k * (sy - 1) / 4, 0.8, x + sx + 1.0, y + 0.9 + k * (sy - 1) / 4, h - 1, M["steel_dark"])
    for k in range(3):  # bushings
        if bushings:
            bushings(x + sx / 2, y + 1 + k * (sy - 2) / 2, h)
        else:
            cv.column(x + sx / 2, y + 1 + k * (sy - 2) / 2, h, h + 2.5, 0.35, M["white"])


def gantry(cv, x0, y0, y1, h):
    with cv.part("gantry"):
        _gantry(cv, x0, y0, y1, h)


def _gantry(cv, x0, y0, y1, h):
    for yy in (y0, y1):
        cv.beam((x0, yy, 0), (x0, yy, h), 0.6, M["steel"])
    cv.beam((x0, y0, h), (x0, y1, h), 0.6, M["steel"])
    for k in range(3):
        yy = y0 + (k + 1) * (y1 - y0) / 4
        with cv.part("insulators"):
            cv.beam((x0, yy, h), (x0, yy, h - 1.5), 0.35, M["white"])


def fence(cv, x0, y0, x1, y1, mat=None, h=1.4):
    with cv.part("fence"):
        _fence(cv, x0, y0, x1, y1, mat or M["steel_dark"], h)


def _fence(cv, x0, y0, x1, y1, mat, h):
    # A tall fence gets a mid rail, but at 1x that and close posts fill in
    # to a solid band, so there it keeps only the top rail and sparser posts.
    tall = h > 1.6
    thin = tall and cv.s == 1
    for z in sorted({h - 0.2, h / 2}) if tall and not thin else (h - 0.2,):
        cv.beam((x0, y0, z), (x1, y1, z), 0.2, mat)
    L = max(abs(x1 - x0), abs(y1 - y0))
    gap = 4 if thin else 2
    for k in range(int(L / gap) + 1):
        t = k * gap / L if L else 0
        cv.beam((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0), (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, h), 0.2, mat)


def cooling_tower(cv, cx, cy, h=52, rb=7.4):
    def r(t):
        # hyperboloid: wide base, waist at 70% height, slight flare at top
        return rb * (0.64 + 0.36 * ((t - 0.72) / 0.72) ** 2) if t < 0.72 else rb * (0.64 + 0.35 * ((t - 0.72) / 0.28) ** 2 * 0.4)
    # Weathered tan concrete like the base-game coal power station's towers,
    # a step lighter since no coal is burnt here.  The top is open: the far
    # inside wall faces the other way from the outside, so its shading is
    # mirrored (lit on the left, dark on the right), and it darkens with depth.
    wall = 0.5
    with cv.part("cooling tower"):
        cv.column(cx, cy, 0, h, r, M["tower"], cap=False)
    with cv.part("cooling tower inside"):
        nz = cv._n(h)
        na = max(12, int(2 * math.pi * rb * 2 / cv.step))
        for k in range(nz + 1):
            t = k / nz
            ri = r(t) - wall
            dr = (r(min(1, t + 0.01)) - r(max(0, t - 0.01))) / 0.02 / h
            inside = Material(M["tower"].ramp, 0.12, grain=0.5, bias=-0.45 * (1 - t) ** 0.5)
            for a in range(na):
                th = 2 * math.pi * a / na
                ca, sa = math.cos(th), math.sin(th)
                if ca + sa > 0.3:  # front half, always behind the outer wall
                    continue
                cv.splat((cx + ri * ca, cy + ri * sa, h * t), (-ca, -sa, dr), inside)
    with cv.part("cooling tower rim"):
        ro = r(1.0)
        n = cv._n(ro * 2)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                dx, dy = ro * i / n, ro * j / n
                if (ro - wall) ** 2 <= dx * dx + dy * dy <= ro * ro:
                    cv.splat((cx + dx, cy + dy, h), (0, 0, 1), M["tower"])


def reactor(cv, cx, cy, r=6.5, h=18):
    with cv.part("reactor building"):
        cv.column(cx, cy, 0, h, r, M["concrete"], cap=False)
    with cv.part("reactor dome"):
        cv.dome(cx, cy, h, r, M["white"], squash=0.9)


def wind_turbine(cv, cx, cy, angle, h=34, rotor=20.0):
    """Three-bladed turbine whose rotor faces the viewer.

    The rotor plane is perpendicular to the view (normal +x+y), and blade
    lengths are set in screen pixels so the rotor reads as a circle of
    radius `rotor` px rather than a squashed ellipse.  `angle` (degrees,
    anticlockwise) is the first blade's angle.  The base angles in
    WIND_TURBINES keep every blade well away from straight down (270), so
    the still frame 0 shows no blade hidden against the tower.
    """
    with cv.part("crane pad"):
        cv.heightfield(cx - 4.5, cy - 4.5, cx + 4.5, cy + 4.5, lambda x, y: 0.05, M["gravel"])
    # track stubs to every tile edge so the access tracks on neighbouring tiles join up
    service_track(cv, along_x=True)
    service_track(cv, along_x=False)
    with cv.part("foundation"):
        cv.box(cx - 2.5, cy - 2.5, 0, cx + 2.5, cy + 2.5, 0.6, M["concrete"])
    with cv.part("tower"):
        cv.column(cx, cy, 0.6, h, lambda t: 1.1 - 0.5 * t, M["white"])
    # nacelle on top of the tower, hub in front of it (towards the viewer)
    with cv.part("nacelle"):
        cv.box(cx - 1.4, cy - 1.4, h - 0.6, cx + 1.0, cy + 1.0, h + 1.2, M["white"])
    hub = (cx + 1.5, cy + 1.5, h + 0.3)
    with cv.part("hub"):
        cv.dome(hub[0], hub[1], hub[2] - 0.4, 0.7, M["grey"])
    # unit vectors: screen-right in the rotor plane, and up
    k = 2 * math.sqrt(2)  # screen px per world unit along (-1, 1, 0)/sqrt(2)
    ux, uy = -1 / math.sqrt(2) / k, 1 / math.sqrt(2) / k  # one screen px to the right
    blade = Material([10, 11, 12, 13, 14], pattern=None)
    edge = Material([7, 8, 9])
    with cv.part("turbine blades"):
        _blades(cv, hub, angle, rotor, ux, uy, blade, edge)


BLADE_CURVE = 0.8  # how far the normal turns across the blade's width


def _unit(v):
    l = math.sqrt(sum(c * c for c in v))
    return tuple(c / l for c in v)


def _blades(cv, hub, angle, rotor, ux, uy, blade, edge):
    face = _unit((1, 1, 0.3))  # the rotor faces the viewer
    for b in range(3):
        th = math.radians(angle + b * 120)
        c, sn = math.cos(th), math.sin(th)
        # world direction across the blade (towards +w), so the blade can be
        # shaded as a rounded section: the edge facing LIGHT comes out lighter
        across = _unit((-sn * ux, -sn * uy, c))
        n = cv._n(rotor)
        for i in range(n + 1):
            t = i / n
            r = rotor * t
            half = 1.3 * (1 - t) + 0.4  # half-width in screen px, tapering to the tip
            m = max(1, int(math.ceil(half * 2 * cv.s)))
            for j in range(-m, m + 1):
                w = half * j / m
                # position in screen px relative to the hub: along the blade + across it
                px = r * c - w * sn
                pz = r * sn + w * c
                p = (hub[0] + px * ux + 0.3, hub[1] + px * uy + 0.3, hub[2] + pz)
                k = BLADE_CURVE * j / m
                normal = tuple(f + k * a for f, a in zip(face, across))
                cv.splat(p, normal, edge if abs(j) == m and t < 0.9 else blade)


def service_track(cv, along_x=True, x0=0.0, x1=16.0):
    """Gravel access track between turbines, flat on the ground."""
    with cv.part("service track"):
        if along_x:
            cv.heightfield(x0, 6.5, x1, 9.5, lambda x, y: 0.05, M["gravel"])
        else:
            cv.heightfield(6.5, x0, 9.5, x1, lambda x, y: 0.05, M["gravel"])


def solar_rows(cv, x0, x1, y0, y1, rows=3):
    """Rows of tilted panels facing SE (+y, screen lower right), towards the light."""
    pitch = (y1 - y0) / rows
    for k in range(rows):
        ya = y0 + k * pitch + 0.8
        depth = pitch * 0.62
        # supports: tall at the back (NW) edge, short at the front (SE) edge
        with cv.part("panel supports"):
            for xx in (x0 + 0.5, (x0 + x1) / 2, x1 - 0.5):
                cv.beam((xx, ya + depth, 0), (xx, ya + depth, 1.1), 0.3, M["steel_dark"])
                cv.beam((xx, ya, 0), (xx, ya, 2.7), 0.3, M["steel_dark"])
        with cv.part("solar panels"):
            cv.parallelogram((x0, ya, 3.0), (x1 - x0, 0, 0), (0, depth, -1.9), panel_mat)


def _panel_pattern(p, n):
    # cell grid lines give the panels texture
    if (p[0] % 2.0) < 0.22:
        return 21
    if (p[2] % 1.0) < 0.12:
        return 131
    return None


panel_mat = Material(PANEL, 0.0, bias=0.1, pattern=_panel_pattern)


# ── Industry tile definitions ──────────────────────────────────────────
# Each entry: name, (x,y) position in the tilelayout, height H, ground, draw(cv)

def t_hydro_dam_n(cv):
    # dam wall along the SW edge, standing in the river (the tile's water
    # ground).  No raised reservoir: it would float in front of the wall
    # when the dam is turned to face the viewer.
    with cv.part("dam wall"):
        cv.box(10.5, 0, 0, 16, 16, 26, M["concrete"], top=M["concrete_dark"])
    with cv.part("parapet"):
        cv.box(10.2, 0, 26, 11.2, 16, 27.5, M["concrete"])
    with cv.part("buttresses"):
        for yy in (3, 8, 13):  # on the downstream face
            cv.box(15.5, yy - 0.8, 0, 16.8, yy + 0.8, 24, M["concrete"])


def t_hydro_dam_s(cv):
    t_hydro_dam_n(cv)
    # intake tower on the reservoir side
    with cv.part("intake tower"):
        cv.box(6, 6, 0, 10, 10, 30, M["concrete"], top=M["grey"])
    with cv.part("tower cap"):
        cv.box(6.5, 6.5, 30, 9.5, 9.5, 32, M["red"])


def t_hydro_power_n(cv):
    # spillway channel + penstocks down from the dam
    with cv.part("spillway water"):
        cv.heightfield(0, 2, 16, 14, lambda x, y: 0.3 + max(0.0, 6 - x) * 0.9, M["water"])
    with cv.part("channel walls"):
        cv.box(0, 1, 0, 16, 2, 2.5, M["concrete"])
        cv.box(0, 14, 0, 16, 15, 2.5, M["concrete"])


def t_hydro_power_s(cv):
    # powerhouse with penstocks
    with cv.part("penstocks"):
        for yy in (3.5, 7.0, 10.5):
            cv.beam((0, yy, 18), (5, yy, 6), 1.4, M["steel"])
    with cv.part("powerhouse"):
        cv.gable(4, 1.5, 0, 13, 14.5, 9, 3, windowed(M["beige"], every=2.5, z_every=4.5), M["green_roof"],
                 along_x=False)
    transformer(cv, 13.5, 3, 2, 3, 3)
    transformer(cv, 13.5, 9, 2, 3, 3)


# Rotated copies of the hydro tiles, so the dam can face whichever side the
# water is on.  The tiles above are drawn with the water on the north-east
# (-x) side; each entry turns the whole 2x2 site about its centre so that
# side becomes the one named.  Keys match the tile names in the NML.
HYDRO_FACINGS = ("ne", "nw", "sw", "se")
_ROT_POINT = {
    "ne": lambda x, y: (x, y),
    "nw": lambda x, y: (16 - y, x),
    "sw": lambda x, y: (16 - x, 16 - y),
    "se": lambda x, y: (y, 16 - x),
}
_ROT_VEC = {
    "ne": lambda x, y: (x, y),
    "nw": lambda x, y: (-y, x),
    "sw": lambda x, y: (-x, -y),
    "se": lambda x, y: (y, -x),
}
_UNROT_POINT = {"ne": "ne", "nw": "se", "sw": "sw", "se": "nw"}


class RotatedCanvas:
    """Canvas proxy that turns the drawing by quarter turns about the tile
    centre.  Boxes and gables stay axis-aligned, so they are re-derived from
    their rotated corners and still draw the faces that face the viewer."""

    def __init__(self, cv, facing):
        self.cv = cv
        self.p = _ROT_POINT[facing]
        self.v = _ROT_VEC[facing]
        self.inv = _ROT_POINT[_UNROT_POINT[facing]]
        self.swap = facing in ("nw", "se")

    def _rect(self, x0, y0, x1, y1):
        ax, ay = self.p(x0, y0)
        bx, by = self.p(x1, y1)
        return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)

    def _p3(self, q):
        return self.p(q[0], q[1]) + (q[2],)

    def _v3(self, q):
        return self.v(q[0], q[1]) + (q[2],)

    def box(self, x0, y0, z0, x1, y1, z1, mat, top=None, side=None):
        a, b, c, d = self._rect(x0, y0, x1, y1)
        self.cv.box(a, b, z0, c, d, z1, mat, top, side)

    def gable(self, x0, y0, z0, x1, y1, z1, ridge, wall, roof, along_x=True):
        a, b, c, d = self._rect(x0, y0, x1, y1)
        self.cv.gable(a, b, z0, c, d, z1, ridge, wall, roof, along_x != self.swap)

    def part(self, name):
        return self.cv.part(name)

    def beam(self, a, b, w, mat):
        self.cv.beam(self._p3(a), self._p3(b), w, mat)

    def column(self, cx, cy, z0, z1, radius, mat, cap=None, flare=0.0):
        cx, cy = self.p(cx, cy)
        self.cv.column(cx, cy, z0, z1, radius, mat, cap, flare)

    def heightfield(self, x0, y0, x1, y1, f, mat):
        a, b, c, d = self._rect(x0, y0, x1, y1)
        self.cv.heightfield(a, b, c, d, lambda x, y: f(*self.inv(x, y)), mat)

    def parallelogram(self, o, u, v, mat, normal=None):
        self.cv.parallelogram(self._p3(o), self._v3(u), self._v3(v), mat,
                              None if normal is None else self._v3(normal))


def rotated(draw, facing):
    if facing == "ne":
        return draw
    return lambda cv: draw(RotatedCanvas(cv, facing))


def hydro_tiles():
    base = [("hydro_dam_n", t_hydro_dam_n), ("hydro_dam_s", t_hydro_dam_s),
            ("hydro_power_n", t_hydro_power_n), ("hydro_power_s", t_hydro_power_s)]
    return [(key if f == "ne" else "%s_%s" % (key, f), rotated(draw, f))
            for f in HYDRO_FACINGS for key, draw in base]


# ── Hydro dam across a river ──
# Drawn for a dam running along x (the river runs along y), with the
# reservoir on the back (-y) side and the downstream face, spillway and power
# house on the front (+y) side, towards the viewer.  "start" and "end" are the
# bank tiles at the low-x and high-x end: the wall meets them at x = 16 and
# x = 0.  The river tiles are drawn by OpenTTD itself; the wall stands on them.
DAM_Z = 12        # crest height
DAM_Y0 = 4.5      # upstream (vertical) face
DAM_Y1 = 7.5      # downstream edge of the crest
DAM_TOE = 12.5    # foot of the sloping downstream face


def dam_wall(cv, x0, x1, spill=False):
    """Gravity dam section from x0 to x1: vertical upstream face, road on the
    crest, sloping downstream face (water pouring down it on a spillway)."""
    with cv.part("dam wall"):
        cv.box(x0, DAM_Y0, 0, x1, DAM_Y1, DAM_Z, M["concrete"], top=M["concrete_dark"])
    if spill:
        with cv.part("spillway water"):
            cv.parallelogram((x0, DAM_Y1, DAM_Z), (x1 - x0, 0, 0), (0, DAM_TOE - DAM_Y1, -DAM_Z), M["water"])
    else:
        with cv.part("downstream face"):
            cv.parallelogram((x0, DAM_Y1, DAM_Z), (x1 - x0, 0, 0), (0, DAM_TOE - DAM_Y1, -DAM_Z), M["concrete"])
        with cv.part("parapets"):
            cv.box(x0, DAM_Y0 - 0.4, DAM_Z, x1, DAM_Y0 + 0.4, DAM_Z + 1.2, M["concrete"])
            cv.box(x0, DAM_Y1 - 0.6, DAM_Z, x1, DAM_Y1 + 0.2, DAM_Z + 1.2, M["concrete"])


def t_hydro_wall(cv):
    dam_wall(cv, 0, 16)


def t_hydro_spillway(cv):
    # gated spillway: water pours over the crest between piers, with a road
    # bridge over the piers and white water where it hits the river
    dam_wall(cv, 0, 16, spill=True)
    with cv.part("piers"):
        for x in (0, 5.3, 10.7, 16):
            a, b = max(0, x - 0.8), min(16, x + 0.8)
            cv.box(a, DAM_Y0, 0, b, DAM_TOE - 1.5, DAM_Z + 5, M["concrete"], top=M["concrete_dark"])
    with cv.part("gates"):
        for x0, x1 in ((0.8, 4.5), (6.1, 9.9), (11.5, 15.2)):  # raised
            cv.box(x0, DAM_Y0 + 0.2, DAM_Z + 2.5, x1, DAM_Y0 + 1.0, DAM_Z + 5, M["steel_dark"])
    with cv.part("road bridge"):
        cv.box(0, DAM_Y0, DAM_Z + 5, 16, DAM_Y1, DAM_Z + 6, M["concrete"], top=M["concrete_dark"])
    with cv.part("white water"):
        cv.box(0, DAM_TOE - 0.2, 0, 16, DAM_TOE + 2.5, 0.6, Material([12, 13, 14, 15], 0.6, grain=0.5))


def dam_bank(cv, reach):
    """The wall running into the bank from the river side (x = 16) as far as
    x = reach, ending in a concrete block set into the ground."""
    dam_wall(cv, reach, 16)
    with cv.part("abutment"):
        cv.box(reach - 3, DAM_Y0 - 1.5, 0, reach, DAM_TOE - 3, DAM_Z + 2, M["concrete"], top=M["concrete_dark"])


def t_hydro_abutment_start(cv):
    dam_bank(cv, 9)
    with cv.part("gate house"):
        cv.box(1, 1, 0, 5, 3, 3, windowed(M["brick"], every=2.0), top=M["grey"])


def t_hydro_power_start(cv):
    dam_bank(cv, 12)
    with cv.part("penstocks"):  # from the reservoir down the bank to the power house
        for x in (2.8, 5.8, 8.8):
            cv.beam((x, DAM_Y1 - 1.5, DAM_Z - 1), (x, 9.5, 5), 1.3, M["steel"])
    with cv.part("powerhouse"):
        cv.gable(1, 9, 0, 11, 15.5, 7, 2.5, windowed(M["beige"], every=2.5, z_every=4.5), M["green_roof"])
    transformer(cv, 12.5, 13, 2, 2.5, 3)
    transformer(cv, 2, 1.5, 2, 2.5, 3)


class MirroredCanvas(RotatedCanvas):
    """Canvas proxy that mirrors the drawing in x (x -> 16 - x)."""

    def __init__(self, cv):
        self.cv = cv
        self.p = lambda x, y: (16 - x, y)
        self.v = lambda x, y: (-x, y)
        self.inv = self.p
        self.swap = False


def mirrored(draw):
    return lambda cv: draw(MirroredCanvas(cv))


def river_dam_tiles():
    """The x tiles as drawn, then the y tiles: the same pieces turned a
    quarter so the dam runs along y with its downstream side still towards
    the viewer.  That turn takes x = 16 to y = 0, so a piece that meets the
    wall at x = 16 (a start piece) becomes the y dam's end piece."""
    abut, power = t_hydro_abutment_start, t_hydro_power_start
    x = [("wall", t_hydro_wall), ("spillway", t_hydro_spillway),
         ("abutment_start", abut), ("abutment_end", mirrored(abut)),
         ("power_start", power), ("power_end", mirrored(power))]
    y = [("wall", t_hydro_wall), ("spillway", t_hydro_spillway),
         ("abutment_start", mirrored(abut)), ("abutment_end", abut),
         ("power_start", mirrored(power)), ("power_end", power)]
    return ([("hydro_%s_x" % k, d) for k, d in x] +
            [("hydro_%s_y" % k, rotated(d, "se")) for k, d in y])


def t_uranium_headframe(cv):
    # steel headframe with sheave wheel over the shaft
    with cv.part("shaft pad"):
        cv.box(3, 3, 0, 13, 13, 1, M["concrete"])
    with cv.part("headframe"):
        for a, b in (((4, 4, 0), (7, 7, 30)), ((4, 12, 0), (7, 9, 30)), ((12, 4, 0), (9, 7, 30)),
                     ((12, 12, 0), (9, 9, 30))):
            cv.beam(a, b, 0.7, M["red"])
        for z in (8, 16, 24):
            f = z / 30.0
            lo, hi = 4 + 3 * f, 12 - 3 * f
            cv.beam((lo, lo, z), (lo, hi, z), 0.5, M["red"])
            cv.beam((lo, lo, z), (hi, lo, z), 0.5, M["red"])
            cv.beam((hi, lo, z), (hi, hi, z), 0.5, M["red"])
            cv.beam((lo, hi, z), (hi, hi, z), 0.5, M["red"])
        cv.box(6.5, 6.5, 30, 9.5, 9.5, 31, M["steel"])
    with cv.part("sheave wheel"):
        for k in range(24):  # in the x-z plane
            th = 2 * math.pi * k / 24
            cv.beam((8 + 3 * math.cos(th), 8, 33 + 3 * math.sin(th)),
                    (8 + 3 * math.cos(th + 0.27), 8, 33 + 3 * math.sin(th + 0.27)), 0.5, M["steel_dark"])
    with cv.part("hoist house"):
        cv.box(12, 2, 0, 16, 6, 6, M["brick"], top=M["steel_dark"])


def t_uranium_tailings(cv):
    def mound(x, y):
        d = math.sqrt(((x - 8) / 7.5) ** 2 + ((y - 8) / 7.0) ** 2)
        if d > 1:
            return None
        return 11 * (1 - d ** 1.6) + hash01(x, y, 3) * 0.6
    with cv.part("tailings mound"):
        cv.heightfield(0, 0, 16, 16, mound, M["tailings"])


def t_uranium_mill(cv):
    with cv.part("mill building"):
        cv.box(1, 2, 0, 12, 14, 12, windowed(M["steel"], every=3, z_every=6), top=M["grey"])
    with cv.part("rooftop block"):
        cv.box(3, 4, 12, 9, 12, 16, M["steel"], top=M["grey"])
    with cv.part("vent stack"):
        cv.column(14, 5, 0, 22, 0.8, M["grey"], cap=M["dark"])
    with cv.part("yellowcake drums"):
        for k, yy in enumerate((3, 6, 9, 12)):
            cv.column(13.8, yy, 0, 2, 0.8, M["yellow"])


def t_uranium_ore(cv):
    def pile(x, y):
        d = math.sqrt(((x - 6) / 5.5) ** 2 + ((y - 8) / 6.5) ** 2)
        if d > 1:
            return None
        return 6 * (1 - d * d) + hash01(x * 2, y * 2, 5) * 0.7
    with cv.part("ore pile"):
        cv.heightfield(0, 0, 12, 16, pile, M["ore"])
    with cv.part("ore truck"):
        cv.box(11, 4, 0.6, 15, 6.5, 3, M["yellow"])
        cv.box(11, 6.5, 0.6, 15, 8, 4.2, M["yellow"], top=M["glass"])
    with cv.part("weighbridge hut"):
        cv.box(12, 9.5, 0, 15.5, 14.5, 3.5, M["concrete"])


def t_nuc_cooling(cv):
    cooling_tower(cv, 8, 8)


def t_nuc_reactor(cv):
    reactor(cv, 8, 8)


def t_nuc_turbine(cv):
    with cv.part("turbine hall"):
        _nuc_turbine(cv)


def _nuc_turbine(cv):
    cv.gable(1, 1, 0, 15, 15, 14, 3, windowed(M["steel"], every=3.5, z_every=5, z_band=(0.2, 0.45)),
             M["blue_roof"], along_x=True)


def t_nuc_turbine2(cv):
    with cv.part("turbine hall"):
        cv.box(1, 1, 0, 15, 15, 14, windowed(M["steel"], every=3.5, z_every=5, z_band=(0.2, 0.45)), top=M["grey"])
    with cv.part("rooftop block"):
        cv.box(4, 4, 14, 9, 12, 17, M["steel"], top=M["grey"])
    with cv.part("vent stack"):
        cv.column(12, 6, 14, 24, 0.9, striped(M["white"], M["red"], 3), cap=M["dark"])


def t_nuc_admin(cv):
    with cv.part("admin building"):
        cv.box(2, 2, 0, 12, 14, 10, windowed(M["white"], every=2.2, z_every=3.3), top=M["grey"])
    with cv.part("parked cars"):
        for k in range(4):
            cv.box(13, 2 + k * 3, 0, 15, 4 + k * 3, 1.2, [M["red"], M["blue_roof"], M["white"], M["yellow"]][k])


def t_nuc_intake(cv):
    with cv.part("intake channel"):
        cv.heightfield(0, 1, 16, 7, lambda x, y: 0.3, M["water"])
    with cv.part("channel walls"):
        cv.box(0, 0, 0, 16, 1, 2, M["concrete"])
        cv.box(0, 7, 0, 16, 8, 2, M["concrete"])
    with cv.part("pump house"):
        cv.box(3, 9, 0, 13, 15, 7, windowed(M["concrete"], every=3, z_every=4), top=M["grey"])
    with cv.part("intake pipes"):
        for xx in (4, 8, 12):
            cv.beam((xx, 7.5, 3), (xx, 2, 1), 0.9, M["steel"])


def t_nuc_switchyard(cv):
    for x in (3, 9):
        gantry(cv, x, 1, 15, 9)
    transformer(cv, 10, 2)
    transformer(cv, 10, 9)
    fence(cv, 15.5, 0, 15.5, 16)


def t_nuc_tanks(cv):
    # tanks numbered back to front
    for k, (cx, cy, r, h) in enumerate(((5, 5, 3.5, 9), (5, 12, 3, 7), (12, 7, 2.5, 12))):
        with cv.part("tank %d" % (k + 1)):
            cv.column(cx, cy, 0, h, r, M["white"], cap=M["grey"])
        with cv.part("ladders"):
            cv.beam((cx + r, cy, 0), (cx + r * 0.7, cy + r * 0.7, h), 0.3, M["steel_dark"])
    fence(cv, 15.5, 0, 15.5, 16)
    fence(cv, 0, 15.5, 16, 15.5)


def t_tidal_barrage(cv):
    with cv.part("barrage wall"):
        cv.box(0, 6, 0, 16, 11, 7, M["concrete"], top=M["concrete_dark"])
    for xx in (2, 7, 12):
        with cv.part("sluice towers"):
            cv.box(xx, 5.5, 7, xx + 3, 11.5, 12, M["concrete"], top=M["steel"])
        with cv.part("sluice gates"):
            cv.box(xx + 0.5, 11.5, 1, xx + 2.5, 11.7, 5, M["dark"])
    with cv.part("roadway"):
        cv.box(0, 8, 7, 16, 9.5, 8, M["steel_dark"])
    with cv.part("surf"):
        cv.heightfield(0, 11.7, 16, 16, lambda x, y: 0.4 if (x % 5) < 3.5 and y < 13.5 else None,
                       Material([251, 252, 252]))


def t_tidal_hall(cv):
    with cv.part("barrage wall"):
        cv.box(0, 6, 0, 6, 11, 7, M["concrete"], top=M["concrete_dark"])
    with cv.part("turbine hall"):
        cv.gable(5, 3, 0, 15, 13, 10, 3, windowed(M["concrete"], every=2.5, z_every=5), M["blue_roof"],
                 along_x=True)
    transformer(cv, 11, 13.2, 3, 2.5, 3)


def t_wind(angle, dx=0.0, dy=0.0):
    return lambda cv: wind_turbine(cv, 8 + dx, 8 + dy, angle)


# Rotor animation: the three blades repeat every 120 degrees, so WIND_FRAMES
# frames step the rotor clockwise through 120 degrees and loop.  Frame 0 is
# the base angle.  Each turbine's frames sit together in the sheet, so its
# sprite is  turbine * WIND_FRAMES + frame  (see sw_wind_rotor in the NML).
WIND_FRAMES = 8
WIND_TURBINES = [("wind_a", 90, 0.0, 0.0), ("wind_b", 70, 0.5, -0.5),
                 ("wind_c", 110, -0.5, 0.5), ("wind_d", 60, 0.5, 0.5)]


def wind_tiles():
    tiles = []
    for key, angle, dx, dy in WIND_TURBINES:
        for f in range(WIND_FRAMES):
            tiles.append((key if f == 0 else "%s_f%d" % (key, f),
                          t_wind(angle - f * 120.0 / WIND_FRAMES, dx, dy)))
    return tiles


def t_wind_track_x(cv):
    service_track(cv, along_x=True)


def t_wind_track_y(cv):
    service_track(cv, along_x=False)


def t_wind_kiosk(cv):
    service_track(cv, along_x=True)
    service_track(cv, along_x=False)
    with cv.part("grid kiosk"):
        cv.box(10.5, 10.5, 0, 14, 14.5, 3.2, M["white"], top=M["grey"])
    with cv.part("kiosk door"):
        cv.box(14, 11.2, 0.6, 14.3, 13.8, 2.4, M["steel_dark"])


def t_solar_panels(cv):
    solar_rows(cv, 0.5, 15.5, 0.5, 15.5)


def t_solar_inverter(cv):
    solar_rows(cv, 0.5, 15.5, 0.5, 9.5)
    with cv.part("inverter"):
        cv.box(3, 11, 0, 9, 15, 4, M["white"], top=M["grey"])
    transformer(cv, 11, 11, 3, 3.5, 3.5)


def t_solar_control(cv):
    solar_rows(cv, 5.5, 15.5, 0.5, 15.5, rows=2)
    with cv.part("control building"):
        cv.gable(0.5, 3, 0, 4.5, 13, 5, 2, windowed(M["beige"], every=2.5, z_every=3.5), M["green_roof"],
                 along_x=False)


def bushing(cv, x, y, z0, h, r=0.45, name="bushings"):
    """Ribbed brown insulator: stacked sheds, wider and narrower in turn.
    At 1x the ribs can't show, so it is a 1px-wide post in light and dark
    bands instead, which keeps neighbouring bushings apart."""
    with cv.part(name):
        if cv.s == 1:
            cv.column(x, y, z0, z0 + h, 0.12, striped(M["porcelain"], Material(PORCELAIN, bias=-0.3), 1.0),
                      cap=M["steel_dark"])
            return
        sheds = max(2, int(h / 0.7))
        cv.column(x, y, z0, z0 + h, lambda t: r if int(t * sheds * 2) % 2 == 0 else r * 0.65,
                  M["porcelain"], cap=M["steel_dark"])


def tank_along_y(cv, cx, y0, y1, cz, r, mat):
    """Horizontal cylinder lying along y (a conservator tank)."""
    na = max(12, int(2 * math.pi * r * 2 / cv.step))
    for k in range(cv._n((y1 - y0) * 2) + 1):
        y = y0 + (y1 - y0) * k / cv._n((y1 - y0) * 2)
        for a in range(na):
            th = 2 * math.pi * a / na
            c, sn = math.cos(th), math.sin(th)
            if c + 2 * sn < -0.5:  # back side, never visible
                continue
            cv.splat((cx + r * c, y, cz + r * sn), (c, 0, sn), mat)
    for j in range(cv._n(r * 2) + 1):  # end cap facing +y
        for i in range(-cv._n(r * 2), cv._n(r * 2) + 1):
            dx, dz = r * i / cv._n(r * 2), r * j / cv._n(r * 2)
            for sz in (1, -1):
                if dx * dx + dz * dz <= r * r:
                    cv.splat((cx + dx, y1, cz + sz * dz), (0, 1, 0), mat)


def radiator_bank(cv, x0, y0, x1, y1, z0, z1, along_x):
    """Row of thin cooling fins standing off a transformer tank."""
    with cv.part("radiators"):
        n = int((x1 - x0 if along_x else y1 - y0) / 0.8)
        for k in range(n):
            if along_x:
                a = x0 + k * (x1 - x0) / n
                cv.box(a, y0, z0, a + 0.4, y1, z1, M["steel_dark"])
            else:
                a = y0 + k * (y1 - y0) / n
                cv.box(x0, a, z0, x1, a + 0.4, z1, M["steel_dark"])


def t_sub_transformers(cv):
    # main grid transformer, fed and taken away by buried cables
    with cv.part("transformer plinth"):
        cv.box(3, 2, 0, 12.5, 11.5, 0.6, M["concrete"])
    with cv.part("transformer tank"):
        cv.box(4.5, 3, 0.6, 10.5, 9, 8, M["steel"], top=M["grey"])
    radiator_bank(cv, 4.8, 9, 10.2, 11, 1.2, 7.2, along_x=True)
    radiator_bank(cv, 10.5, 3.3, 12.2, 8.7, 1.2, 7.2, along_x=False)
    for yy in (4.2, 6, 7.8):
        bushing(cv, 8.8, yy, 8, 7, r=0.42)
    for yy in (4.5, 6, 7.5):
        bushing(cv, 6.2, yy, 8, 3, r=0.35)
    with cv.part("conservator tank"):
        for yy in (4, 8):
            cv.beam((4.2, yy, 8), (4.2, yy, 10.4), 0.4, M["steel_dark"])
        tank_along_y(cv, 4.2, 3, 9, 11.4, 1.2, M["steel"])
    with cv.part("control box"):
        cv.box(11.2, 1, 0, 12.8, 2.4, 3.2, M["grey"])
    with cv.part("switchgear cabinets"):
        for k in range(3):
            cv.box(1, 11.5 + k * 1.4, 0, 3, 12.8 + k * 1.4, 5, M["white"], top=M["grey"])
    for a, b in (((0.5, 0.5), (0.5, 15.5)), ((0.5, 0.5), (16, 0.5)), ((0.5, 15.5), (16, 15.5))):
        fence(cv, *a, *b, mat=M["yellow"], h=2.2)


def t_sub_switchgear(cv):
    with cv.part("control building"):
        cv.box(1.5, 1.5, 0, 7.5, 8.5, 5.5, windowed(M["concrete"], every=3.5, z_every=5.5, z_band=(0.4, 0.7)),
               top=M["grey"])
    with cv.part("building door"):
        cv.box(7.5, 3, 0, 7.7, 5, 3.5, M["steel_dark"])
    for yy in (2, 8):
        transformer(cv, 10, yy, 3, 3.6, 4.5, bushings=lambda bx, by, bz: bushing(cv, bx, by, bz, 2.2, r=0.3))
    with cv.part("switch rack"):
        for xx in (2.5, 7):
            for yy in (10.5, 14):
                cv.beam((xx, yy, 0), (xx, yy, 3), 0.4, M["steel"])
            cv.beam((xx, 10.5, 3), (xx, 14, 3), 0.4, M["steel"])
    for xx in (2.5, 7):
        for yy in (11.3, 12.3, 13.3):
            bushing(cv, xx, yy, 3.2, 2.2, r=0.28, name="insulators")
    with cv.part("switchgear cabinets"):
        cv.box(3.5, 10.5, 0, 6, 14, 3.5, M["white"], top=M["grey"])
    for a, b in (((0, 0.5), (15.5, 0.5)), ((15.5, 0.5), (15.5, 15.5)), ((0, 15.5), (15.5, 15.5))):
        fence(cv, *a, *b, mat=M["yellow"], h=2.2)


# name → (ground, H, [(tile_key, draw), ...]) – order defines sheet order
INDUSTRIES = {
    "hydro_dam": ("water", 36, hydro_tiles() + river_dam_tiles()),
    "uranium_mine": ("dirt", 40, [
        ("uranium_headframe", t_uranium_headframe),
        ("uranium_tailings", t_uranium_tailings),
        ("uranium_mill", t_uranium_mill),
        ("uranium_ore", t_uranium_ore),
    ]),
    "nuclear_plant": ("concrete", 60, [
        ("nuc_cooling", t_nuc_cooling),
        ("nuc_reactor", t_nuc_reactor),
        ("nuc_turbine", t_nuc_turbine),
        ("nuc_turbine2", t_nuc_turbine2),
        ("nuc_admin", t_nuc_admin),
        ("nuc_intake", t_nuc_intake),
        ("nuc_switchyard", t_nuc_switchyard),
        ("nuc_tanks", t_nuc_tanks),
    ]),
    "tidal_station": ("shore", 20, [
        ("tidal_barrage", t_tidal_barrage),
        ("tidal_hall", t_tidal_hall),
    ]),
    "wind_farm": ("grass", 48, wind_tiles() + [
        ("wind_track_x", t_wind_track_x),
        ("wind_track_y", t_wind_track_y),
        ("wind_kiosk", t_wind_kiosk),
    ]),
    "solar_farm": ("grass", 12, [
        ("solar_panels", t_solar_panels),
        ("solar_inverter", t_solar_inverter),
        ("solar_control", t_solar_control),
    ]),
    "substation": ("concrete", 40, [
        ("sub_transformers", t_sub_transformers),
        ("sub_switchgear", t_sub_switchgear),
    ]),
}


# Tiles whose ground differs from their industry's default ground.
TILE_GROUND = {
    **{k: "grass" for k, _ in hydro_tiles() if k.startswith("hydro_power")},
    **{k: "grass" for k, _ in river_dam_tiles() if k.endswith(("_start_x", "_end_x", "_start_y", "_end_y"))},
    "uranium_tailings": "dirt",
}


# ── Cargo icons ────────────────────────────────────────────────────────
# Flat pixel art, not 3D: shapes are defined on a 10x10 grid and sampled at
# each pixel centre (render_icon's `s` scales the sampling grid).
# Each icon gets a near-black outline like the base game's cargo icons.
ICON_W = 10
OUTLINE = 1

_BOLT = [(4.8, 0.6), (8.4, 0.6), (6.3, 3.6), (8.6, 3.6), (2.8, 9.5), (4.3, 5.8), (1.6, 5.8)]


def _in_poly(x, y, pts):
    inside = False
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


def icon_power(u, v):
    """Yellow lightning bolt, shaded lighter towards its upper left.  Returns
    (index, part).  Cargo icons are flat menu art, not world sprites, so this
    shading is part of the drawing and doesn't follow LIGHT."""
    if not _in_poly(u, v, _BOLT):
        return 0, None
    return YELLOW[min(6, max(3, int(7.5 - (u + v) * 0.3)))], "lightning bolt"


_DRUM = [83, 85, 87, 209, 87, 86, 85, 84, 83, 82]  # left to right, highlight left of centre (not LIGHT)


def icon_uranium(u, v):
    """Green drum with a yellow radiation mark.  Returns (index, part)."""
    if not (2.0 <= u < 8.0 and 1.5 <= v < 9.0):
        return 0, None
    if (u - 5.0) ** 2 + ((v - 5.4) * 1.1) ** 2 < 1.6 ** 2:
        r = math.hypot(u - 5.0, v - 5.4)
        ang = math.degrees(math.atan2(v - 5.4, u - 5.0)) % 120
        if r < 0.45 or (r > 0.7 and 0 <= ang < 60):
            return 1, "radiation symbol"
        return YELLOW[5], "radiation symbol"
    if v < 2.5:
        return 208, "lid"
    if 3.0 <= v < 3.5 or 7.8 <= v < 8.3:
        return 82, "rims"
    return _DRUM[min(len(_DRUM) - 1, int((u - 2.0) / 6.0 * len(_DRUM)))], "drum"


CARGO_ICONS = {"powr": icon_power, "uran": icon_uranium}


def render_icon(fn, s, parts=None):
    """If `parts` is a dict, it is filled with (col, row) -> part name."""
    n = ICON_W * s
    cells = [[fn((x + 0.5) / s, (y + 0.5) / s) for x in range(n)] for y in range(n)]
    px = [[c for c, _ in row] for row in cells]
    im = Image.new("P", (n, n), 0)
    for y in range(n):
        for x in range(n):
            c, name = cells[y][x]
            if not c and any(0 <= y + dy < n and 0 <= x + dx < n and px[y + dy][x + dx]
                             for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                c, name = OUTLINE, "outline"
            im.putpixel((x, y), c)
            if parts is not None and c:
                parts[x, y] = name
    return im


def render_icons(s):
    sheet = Image.new("P", (ICON_W * s * len(CARGO_ICONS), ICON_W * s), 0)
    sheet.putpalette(PALETTE)
    for k, fn in enumerate(CARGO_ICONS.values()):
        sheet.paste(render_icon(fn, s), (k * ICON_W * s, 0))
    return sheet


def render_sheet(name, s):
    ground, H, tiles = INDUSTRIES[name]
    cw, ch = CELL_W * s, (32 + H) * s
    sheet = Image.new("P", (cw * len(tiles), ch), 0)
    sheet.putpalette(PALETTE)
    for k, (_, draw) in enumerate(tiles):
        cv = Canvas(s, H)
        draw(cv)
        sheet.paste(cv.image(), (k * cw, 0))
    return sheet


def render_ground(s):
    cw, ch = CELL_W * s, 31 * s + (s - 1)
    sheet = Image.new("P", (cw * len(GROUND_ORDER), ch), 0)
    sheet.putpalette(PALETTE)
    for k, kind in enumerate(GROUND_ORDER):
        sheet.paste(ground_tile(kind, s), (k * cw, 0))
    return sheet


def save(im, fname):
    path = os.path.join(OUT, fname)
    im.save(path, optimize=True)
    print("wrote", os.path.relpath(path, ROOT), im.size)


NML_FILE = os.path.join(ROOT, "energy_transition.nml")
NML_BEGIN = "/* BEGIN GENERATED SPRITESETS"
NML_END = "/* END GENERATED SPRITESETS */"


ANIMATED = set(range(227, 255))  # palette-animated indices (water, lights, fire)


def _entries(fname, n, s, w, h, xoff, yoff):
    """Sprite entries for one sheet; sprites using animated colours get ANIM."""
    im = Image.open(os.path.join(OUT, fname))
    res = []
    for k in range(n):
        cell = im.crop((k * w * s, 0, (k + 1) * w * s, h))
        anim = ", ANIM" if ANIMATED & set(cell.tobytes()) else ""
        res.append("[%d,0,%d,%d,%d,%d%s]" % (k * w * s, w * s, h, xoff * s, yoff * s, anim))
    return " ".join(res)


def nml_spritesets():
    """NML for every spriteset (1x only), matching the sheets."""
    out = [NML_BEGIN + " - written by tools/make_sprites.py, do not edit by hand */"]
    out.append("/* ground: %s */" % ", ".join("%d=%s" % (k, g) for k, g in enumerate(GROUND_ORDER)))

    def block(ss, fname, n, w, h, xoff, yoff):
        out.append('spriteset(%s, "sprites/%s.png") { %s }'
                   % (ss, fname, _entries(fname + ".png", n, 1, w, h, xoff, yoff)))

    block("ss_ground", "ground", len(GROUND_ORDER), CELL_W, 31, -31, 0)
    for name, (_, H, tiles) in INDUSTRIES.items():
        out.append("/* %s: %s */" % (name, ", ".join("%d=%s" % (k, t[0]) for k, t in enumerate(tiles))))
        block("ss_" + name, name, len(tiles), CELL_W, 32 + H, -31, -H)
    for k, cargo in enumerate(CARGO_ICONS):
        w = ICON_W
        out.append('spriteset(ss_cargo_%s, "sprites/cargo_icons.png") { [%d,0,%d,%d,0,0] }' % (cargo, k * w, w, w))
    out.append(NML_END)
    return "\n".join(out)


# GLASS and GRASS sit on the company-colour ranges (0xC6-0xCD, 0x50-0x57),
# as the base game's windows and grass do.  Recolouring a sprite would repaint
# them in the industry's random colour, so sprites are never recoloured (spec
# section 3).
RECOLOUR = re.compile(r"\b(recolour_mode|palette)\s*:")


def check_no_recolour(text):
    for n, line in enumerate(text.splitlines(), 1):
        if RECOLOUR.search(line):
            sys.exit("energy_transition.nml:%d recolours a sprite, which would repaint GLASS and GRASS "
                     "(docs/sprite_design_spec.md, section 3): %s" % (n, line.strip()))


def update_nml():
    with open(NML_FILE, encoding="utf-8") as f:
        text = f.read()
    check_no_recolour(text)
    a, b = text.find(NML_BEGIN), text.find(NML_END)
    if a < 0 or b < 0:
        sys.exit("generated-spriteset markers not found in energy_transition.nml")
    text = text[:a] + nml_spritesets() + text[b + len(NML_END):]
    with open(NML_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print("updated spritesets in", os.path.relpath(NML_FILE, ROOT))


def main():
    only = set(sys.argv[1:])
    if not only or "ground" in only:
        save(render_ground(1), "ground.png")
    if not only or "cargo_icons" in only:
        save(render_icons(1), "cargo_icons.png")
    for name in INDUSTRIES:
        if not only or name in only:
            save(render_sheet(name, 1), "%s.png" % name)
    update_nml()
    # annotated references with part names (docs/sprites/, spec section 12)
    import sprite_refs
    sprite_refs.write_all(sys.modules[__name__], only)


if __name__ == "__main__":
    main()
