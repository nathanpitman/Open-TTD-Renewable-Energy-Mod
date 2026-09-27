#!/usr/bin/env python3
"""
Procedural sprite generator for the Energy Transition NewGRF.

Renders every industry tile and ground tile from simple 3D primitives
(boxes, tapered cylinders, domes, quads, height-field mounds) into
8bpp PNGs that use OpenTTD's DOS palette exactly as nmlc expects it.
Both 1x (ZOOM_LEVEL_NORMAL) and 2x (ZOOM_LEVEL_IN_2X) sprites are
produced from the same geometry, so the two zoom levels always agree.

Usage:
    pip install nml pillow
    python3 tools/make_sprites.py          # writes sprites/*.png
    python3 tools/make_sprites.py cargo_icons   # just one sheet (or an industry name)

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

import math
import os
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
GRASS = [80, 81, 82, 83, 84, 85, 86, 87]
DIRT = [104, 105, 106, 107, 108, 109, 110, 111]
TAILINGS = [24, 25, 26, 27, 28, 29, 30]
COAL = [1, 2, 3, 4, 5, 6]
PANEL = [128, 129, 130, 131, 132, 133]
GLASS = [198, 199, 200, 201, 202, 203, 204, 205]
WATER = [245, 246, 247, 248, 249]
GREEN_ROOF = [96, 97, 98, 99, 100, 101]
BLUE_ROOF = [154, 155, 156, 157, 158, 159]


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
        if along_x:
            ym = (y0 + y1) / 2
            self.parallelogram((x0, y0, z1), (x1 - x0, 0, 0), (0, ym - y0, ridge), roof, (0, -ridge, ym - y0))
            self.parallelogram((x0, ym, z1 + ridge), (x1 - x0, 0, 0), (0, y1 - ym, -ridge), roof, (0, ridge, y1 - ym))
            self._tri_gable_x(x1, y0, y1, z1, ridge, wall)
        else:
            xm = (x0 + x1) / 2
            self.parallelogram((x0, y0, z1), (0, y1 - y0, 0), (xm - x0, 0, ridge), roof, (-ridge, 0, xm - x0))
            self.parallelogram((xm, y0, z1 + ridge), (0, y1 - y0, 0), (x1 - xm, 0, -ridge), roof, (ridge, 0, x1 - xm))
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
    n = hash01(x * 2, y * 2, 7)
    n2 = hash01(x / 3, y / 3, 11)
    if kind == "grass":
        return GRASS[[2, 3, 3, 4, 4, 4, 5, 5, 6][int((n * 0.6 + n2 * 0.4) * 9)]]
    if kind == "dirt":
        return DIRT[[2, 3, 3, 4, 4, 5, 5, 6][int((n * 0.7 + n2 * 0.3) * 8)]]
    if kind == "concrete":
        seam = (x % 8 < 0.5) or (y % 8 < 0.5)
        return 7 if seam else [9, 10, 10, 10, 11][int(n * 5)]
    if kind == "water":
        return WATER[int((n * 0.5 + n2 * 0.5) * len(WATER))]
    if kind == "shore":
        edge = 12 + (hash01(x, 3) - 0.5) * 1.5
        if y < edge - 1.2:
            return WATER[int((n * 0.5 + n2 * 0.5) * len(WATER))]
        if y < edge:
            return 252 if n > 0.6 else 251  # surf
        return SAND[[1, 2, 2, 3, 3, 4][int(n * 6)]]
    raise ValueError(kind)


def ground_tile(kind, s):
    """64x31 flat ground diamond in the standard TTD pixel shape (scaled)."""
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
            px[c, r] = ground_colour(kind, min(max(x, 0), 15.99), min(max(y, 0), 15.99))
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
    "panel": Material(PANEL, 0.0),
    "glass": Material(GLASS),
    "water": Material(WATER, 0.6, grain=1.0),
    "green_roof": Material(GREEN_ROOF),
    "blue_roof": Material(BLUE_ROOF),
    "dark": Material([1, 2, 3, 4]),
    "gravel": Material([33, 34, 35, 36, 37], 0.5, grain=0.4),
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
def lattice_tower(cv, cx, cy, z1, base=3.0, top=1.0, mat=None):
    mat = mat or M["steel"]
    w = 0.5
    legs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for lx, ly in legs:
        cv.beam((cx + lx * base, cy + ly * base, 0), (cx + lx * top, cy + ly * top, z1), w, mat)
    levels = 6
    for k in range(1, levels + 1):
        t = k / levels
        z = z1 * t
        r = base + (top - base) * t
        rp = base + (top - base) * (k - 1) / levels
        zp = z1 * (k - 1) / levels
        for (ax, ay), (bx, by) in zip(legs, legs[1:] + legs[:1]):
            cv.beam((cx + ax * r, cy + ay * r, z), (cx + bx * r, cy + by * r, z), w, mat)
            cv.beam((cx + ax * rp, cy + ay * rp, zp), (cx + bx * r, cy + by * r, z), w * 0.8, mat)
    # cross arms
    for zz, arm in ((z1 * 0.8, 6.0), (z1 * 0.62, 5.0)):
        cv.beam((cx - arm, cy, zz), (cx + arm, cy, zz), w, mat)
        for sgn in (-1, 1):
            cv.beam((cx + sgn * arm, cy, zz), (cx + sgn * arm, cy, zz - 2.5), 0.4, M["dark"])


def transformer(cv, x, y, sx=4, sy=5, h=5):
    cv.box(x, y, 0, x + sx, y + sy, h, M["steel"])
    for k in range(4):  # radiator fins
        cv.box(x + sx, y + 0.6 + k * (sy - 1) / 4, 0.8, x + sx + 1.0, y + 0.9 + k * (sy - 1) / 4, h - 1, M["steel_dark"])
    for k in range(3):  # bushings
        cv.column(x + sx / 2, y + 1 + k * (sy - 2) / 2, h, h + 2.5, 0.35, M["white"])


def gantry(cv, x0, y0, y1, h):
    for yy in (y0, y1):
        cv.beam((x0, yy, 0), (x0, yy, h), 0.6, M["steel"])
    cv.beam((x0, y0, h), (x0, y1, h), 0.6, M["steel"])
    for k in range(3):
        yy = y0 + (k + 1) * (y1 - y0) / 4
        cv.beam((x0, yy, h), (x0, yy, h - 1.5), 0.35, M["white"])


def pylon_wire(cv, x0, y0, x1, y1, z):
    cv.beam((x0, y0, z), (x1, y1, z - 1), 0.2, M["dark"])


def fence(cv, x0, y0, x1, y1):
    cv.beam((x0, y0, 1.2), (x1, y1, 1.2), 0.2, M["steel_dark"])
    L = max(abs(x1 - x0), abs(y1 - y0))
    for k in range(int(L / 2) + 1):
        t = k * 2 / L if L else 0
        cv.beam((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0), (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 1.4), 0.2,
                M["steel_dark"])


def cooling_tower(cv, cx, cy, h=52, rb=7.4):
    def r(t):
        # hyperboloid: wide base, waist at 70% height, slight flare at top
        return rb * (0.64 + 0.36 * ((t - 0.72) / 0.72) ** 2) if t < 0.72 else rb * (0.64 + 0.35 * ((t - 0.72) / 0.28) ** 2 * 0.4)
    cv.column(cx, cy, 0, h, r, M["concrete"], cap=M["dark"])
    cv.disc(cx, cy, h - 0.1, r(1.0) - 0.8, M["dark"])


def reactor(cv, cx, cy, r=6.5, h=18):
    cv.column(cx, cy, 0, h, r, M["concrete"], cap=False)
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
    cv.heightfield(cx - 4.5, cy - 4.5, cx + 4.5, cy + 4.5, lambda x, y: 0.05, M["gravel"])  # crane pad
    # track stubs to every tile edge so the access tracks on neighbouring tiles join up
    service_track(cv, along_x=True)
    service_track(cv, along_x=False)
    cv.box(cx - 2.5, cy - 2.5, 0, cx + 2.5, cy + 2.5, 0.6, M["concrete"])  # foundation
    cv.column(cx, cy, 0.6, h, lambda t: 1.1 - 0.5 * t, M["white"])
    # nacelle on top of the tower, hub in front of it (towards the viewer)
    cv.box(cx - 1.4, cy - 1.4, h - 0.6, cx + 1.0, cy + 1.0, h + 1.2, M["white"])
    hub = (cx + 1.5, cy + 1.5, h + 0.3)
    cv.dome(hub[0], hub[1], hub[2] - 0.4, 0.7, M["grey"])
    # unit vectors: screen-right in the rotor plane, and up
    k = 2 * math.sqrt(2)  # screen px per world unit along (-1, 1, 0)/sqrt(2)
    ux, uy = -1 / math.sqrt(2) / k, 1 / math.sqrt(2) / k  # one screen px to the right
    blade = Material([10, 11, 12, 13, 14], pattern=None)
    edge = Material([7, 8, 9])
    for b in range(3):
        th = math.radians(angle + b * 120)
        c, sn = math.cos(th), math.sin(th)
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
                cv.splat(p, (1, 1, 0.3), edge if abs(j) == m and t < 0.9 else blade)


def service_track(cv, along_x=True, x0=0.0, x1=16.0):
    """Gravel access track between turbines, flat on the ground."""
    if along_x:
        cv.heightfield(x0, 6.5, x1, 9.5, lambda x, y: 0.05, M["gravel"])
    else:
        cv.heightfield(6.5, x0, 9.5, x1, lambda x, y: 0.05, M["gravel"])


def solar_rows(cv, x0, x1, y0, y1, rows=3):
    """Rows of tilted panels (facing SW / the light)."""
    pitch = (x1 - x0) / rows
    for k in range(rows):
        xa = x0 + k * pitch + 0.8
        depth = pitch * 0.62
        # supports
        for yy in (y0 + 0.5, (y0 + y1) / 2, y1 - 0.5):
            cv.beam((xa + depth, yy, 0), (xa + depth, yy, 1.1), 0.3, M["steel_dark"])
            cv.beam((xa, yy, 0), (xa, yy, 2.7), 0.3, M["steel_dark"])
        cv.parallelogram((xa, y0, 3.0), (depth, 0, -1.9), (0, y1 - y0, 0), panel_mat)


def _panel_pattern(p, n):
    # cell grid lines give the panels texture
    if (p[1] % 2.0) < 0.22:
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
    cv.box(10.5, 0, 0, 16, 16, 26, M["concrete"], top=M["concrete_dark"])
    cv.box(10.2, 0, 26, 11.2, 16, 27.5, M["concrete"])  # parapet
    for yy in (3, 8, 13):  # buttresses on the downstream face
        cv.box(15.5, yy - 0.8, 0, 16.8, yy + 0.8, 24, M["concrete"])


def t_hydro_dam_s(cv):
    t_hydro_dam_n(cv)
    # intake tower on the reservoir side
    cv.box(6, 6, 0, 10, 10, 30, M["concrete"], top=M["grey"])
    cv.box(6.5, 6.5, 30, 9.5, 9.5, 32, M["red"])


def t_hydro_power_n(cv):
    # spillway channel + penstocks down from the dam
    cv.heightfield(0, 2, 16, 14, lambda x, y: 0.3 + max(0.0, 6 - x) * 0.9, M["water"])
    cv.box(0, 1, 0, 16, 2, 2.5, M["concrete"])
    cv.box(0, 14, 0, 16, 15, 2.5, M["concrete"])


def t_hydro_power_s(cv):
    # powerhouse with penstocks
    for yy in (3.5, 7.0, 10.5):
        cv.beam((0, yy, 18), (5, yy, 6), 1.4, M["steel"])
    cv.gable(4, 1.5, 0, 13, 14.5, 9, 3, windowed(M["beige"], every=2.5, z_every=4.5), M["green_roof"], along_x=False)
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


def t_uranium_headframe(cv):
    # steel headframe with sheave wheel over the shaft
    cv.box(3, 3, 0, 13, 13, 1, M["concrete"])
    for a, b in (((4, 4, 0), (7, 7, 30)), ((4, 12, 0), (7, 9, 30)), ((12, 4, 0), (9, 7, 30)), ((12, 12, 0), (9, 9, 30))):
        cv.beam(a, b, 0.7, M["red"])
    for z in (8, 16, 24):
        f = z / 30.0
        lo, hi = 4 + 3 * f, 12 - 3 * f
        cv.beam((lo, lo, z), (lo, hi, z), 0.5, M["red"])
        cv.beam((lo, lo, z), (hi, lo, z), 0.5, M["red"])
        cv.beam((hi, lo, z), (hi, hi, z), 0.5, M["red"])
        cv.beam((lo, hi, z), (hi, hi, z), 0.5, M["red"])
    cv.box(6.5, 6.5, 30, 9.5, 9.5, 31, M["steel"])
    for k in range(24):  # sheave wheel (in the x-z plane)
        th = 2 * math.pi * k / 24
        cv.beam((8 + 3 * math.cos(th), 8, 33 + 3 * math.sin(th)),
                (8 + 3 * math.cos(th + 0.27), 8, 33 + 3 * math.sin(th + 0.27)), 0.5, M["steel_dark"])
    cv.box(12, 2, 0, 16, 6, 6, M["brick"], top=M["steel_dark"])  # hoist house


def t_uranium_tailings(cv):
    def mound(x, y):
        d = math.sqrt(((x - 8) / 7.5) ** 2 + ((y - 8) / 7.0) ** 2)
        if d > 1:
            return None
        return 11 * (1 - d ** 1.6) + hash01(x, y, 3) * 0.6
    cv.heightfield(0, 0, 16, 16, mound, M["tailings"])


def t_uranium_mill(cv):
    cv.box(1, 2, 0, 12, 14, 12, windowed(M["steel"], every=3, z_every=6), top=M["grey"])
    cv.box(3, 4, 12, 9, 12, 16, M["steel"], top=M["grey"])
    cv.column(14, 5, 0, 22, 0.8, M["grey"], cap=M["dark"])  # vent stack
    for k, yy in enumerate((3, 6, 9, 12)):  # yellowcake drums
        cv.column(13.8, yy, 0, 2, 0.8, M["yellow"])


def t_uranium_ore(cv):
    def pile(x, y):
        d = math.sqrt(((x - 6) / 5.5) ** 2 + ((y - 8) / 6.5) ** 2)
        if d > 1:
            return None
        return 6 * (1 - d * d) + hash01(x * 2, y * 2, 5) * 0.7
    cv.heightfield(0, 0, 12, 16, pile, M["ore"])
    # ore truck
    cv.box(11, 4, 0.6, 15, 6.5, 3, M["yellow"])
    cv.box(11, 6.5, 0.6, 15, 8, 4.2, M["yellow"], top=M["glass"])
    cv.box(12, 9.5, 0, 15.5, 14.5, 3.5, M["concrete"])  # weighbridge hut


def t_nuc_cooling(cv):
    cooling_tower(cv, 8, 8)


def t_nuc_reactor(cv):
    reactor(cv, 8, 8)


def t_nuc_turbine(cv):
    cv.gable(1, 1, 0, 15, 15, 14, 3, windowed(M["steel"], every=3.5, z_every=5, z_band=(0.2, 0.45)),
             M["blue_roof"], along_x=True)


def t_nuc_turbine2(cv):
    cv.box(1, 1, 0, 15, 15, 14, windowed(M["steel"], every=3.5, z_every=5, z_band=(0.2, 0.45)), top=M["grey"])
    cv.box(4, 4, 14, 9, 12, 17, M["steel"], top=M["grey"])
    cv.column(12, 6, 14, 24, 0.9, striped(M["white"], M["red"], 3), cap=M["dark"])


def t_nuc_admin(cv):
    cv.box(2, 2, 0, 12, 14, 10, windowed(M["white"], every=2.2, z_every=3.3), top=M["grey"])
    for k in range(4):  # car park
        cv.box(13, 2 + k * 3, 0, 15, 4 + k * 3, 1.2, [M["red"], M["blue_roof"], M["white"], M["yellow"]][k])


def t_nuc_intake(cv):
    cv.heightfield(0, 1, 16, 7, lambda x, y: 0.3, M["water"])
    cv.box(0, 0, 0, 16, 1, 2, M["concrete"])
    cv.box(0, 7, 0, 16, 8, 2, M["concrete"])
    cv.box(3, 9, 0, 13, 15, 7, windowed(M["concrete"], every=3, z_every=4), top=M["grey"])
    for xx in (4, 8, 12):
        cv.beam((xx, 7.5, 3), (xx, 2, 1), 0.9, M["steel"])


def t_nuc_switchyard(cv):
    for x in (3, 9):
        gantry(cv, x, 1, 15, 9)
    transformer(cv, 10, 2)
    transformer(cv, 10, 9)
    fence(cv, 15.5, 0, 15.5, 16)


def t_nuc_tanks(cv):
    for cx, cy, r, h in ((5, 5, 3.5, 9), (5, 12, 3, 7), (12, 7, 2.5, 12)):
        cv.column(cx, cy, 0, h, r, M["white"], cap=M["grey"])
        cv.beam((cx + r, cy, 0), (cx + r * 0.7, cy + r * 0.7, h), 0.3, M["steel_dark"])  # ladder
    fence(cv, 15.5, 0, 15.5, 16)
    fence(cv, 0, 15.5, 16, 15.5)


def t_tidal_barrage(cv):
    cv.box(0, 6, 0, 16, 11, 7, M["concrete"], top=M["concrete_dark"])
    for xx in (2, 7, 12):  # sluice gate towers
        cv.box(xx, 5.5, 7, xx + 3, 11.5, 12, M["concrete"], top=M["steel"])
        cv.box(xx + 0.5, 11.5, 1, xx + 2.5, 11.7, 5, M["dark"])
    cv.box(0, 8, 7, 16, 9.5, 8, M["steel_dark"])  # roadway
    cv.heightfield(0, 11.7, 16, 16, lambda x, y: 0.4 if (x % 5) < 3.5 and y < 13.5 else None, Material([251, 252, 252]))


def t_tidal_hall(cv):
    cv.box(0, 6, 0, 6, 11, 7, M["concrete"], top=M["concrete_dark"])
    cv.gable(5, 3, 0, 15, 13, 10, 3, windowed(M["concrete"], every=2.5, z_every=5), M["blue_roof"], along_x=True)
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
    cv.box(10.5, 10.5, 0, 14, 14.5, 3.2, M["white"], top=M["grey"])  # grid connection kiosk
    cv.box(14, 11.2, 0.6, 14.3, 13.8, 2.4, M["steel_dark"])


def t_solar_panels(cv):
    solar_rows(cv, 0.5, 15.5, 0.5, 15.5)


def t_solar_inverter(cv):
    solar_rows(cv, 0.5, 15.5, 0.5, 9.5)
    cv.box(3, 11, 0, 9, 15, 4, M["white"], top=M["grey"])
    transformer(cv, 11, 11, 3, 3.5, 3.5)


def t_solar_control(cv):
    solar_rows(cv, 5.5, 15.5, 0.5, 15.5, rows=2)
    cv.gable(0.5, 3, 0, 4.5, 13, 5, 2, windowed(M["beige"], every=2.5, z_every=3.5), M["green_roof"], along_x=False)


def t_sub_transformers(cv):
    gantry(cv, 2, 1, 15, 10)
    transformer(cv, 6, 2)
    transformer(cv, 6, 9)
    fence(cv, 15.5, 0, 15.5, 16)
    fence(cv, 0, 15.5, 16, 15.5)


def t_sub_pylon(cv):
    lattice_tower(cv, 5, 8, 34)
    cv.box(9, 3, 0, 15, 13, 6, windowed(M["brick"], every=2.5, z_every=6, z_band=(0.35, 0.7)), top=M["grey"])
    fence(cv, 0, 15.5, 16, 15.5)


def t_coal_boiler(cv):
    cv.box(1, 1, 0, 13, 11, 18, windowed(M["brick"], every=2.5, z_every=6, z_band=(0.4, 0.7)), top=M["grey"])
    cv.box(2, 11, 0, 12, 15, 10, M["brick"], top=M["steel_dark"])
    cv.column(13.5, 13, 0, 48, lambda t: 2.0 - 0.7 * t, striped(M["brick"], M["red"], 12), cap=M["dark"])


def t_coal_yard(cv):
    def pile(x, y):
        d = math.sqrt(((x - 7) / 6.5) ** 2 + ((y - 6) / 5.5) ** 2)
        if d > 1:
            return None
        return 7 * (1 - d * d) + hash01(x * 2, y * 2, 9) * 0.8
    cv.heightfield(0, 0, 15, 12, pile, M["coal"])
    cv.beam((1, 13, 1), (1, 13, 12), 0.5, M["steel"])
    cv.beam((14, 13, 1), (-2, 13, 14), 1.2, M["steel"])  # conveyor up to the boiler house


# name → (ground, H, [(tile_key, draw), ...]) – order defines sheet order
INDUSTRIES = {
    "hydro_dam": ("water", 36, hydro_tiles()),
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
        ("sub_pylon", t_sub_pylon),
    ]),
    "coal_power_plant": ("dirt", 52, [
        ("coal_boiler", t_coal_boiler),
        ("coal_yard", t_coal_yard),
    ]),
}


# Tiles whose ground differs from their industry's default ground.
TILE_GROUND = {
    **{k: "grass" for k, _ in hydro_tiles() if k.startswith("hydro_power")},
    "uranium_tailings": "dirt",
}


# ── Cargo icons ────────────────────────────────────────────────────────
# Flat pixel art, not 3D: shapes are defined on a 10x10 grid and sampled at
# each pixel centre, so the 2x icon is the same drawing at twice the detail.
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
    """Yellow lightning bolt, lit from the upper left."""
    if not _in_poly(u, v, _BOLT):
        return 0
    return YELLOW[min(6, max(3, int(7.5 - (u + v) * 0.3)))]


_DRUM = [83, 85, 87, 209, 87, 86, 85, 84, 83, 82]  # left to right, lit from the left


def icon_uranium(u, v):
    """Green drum with a yellow radiation mark."""
    if not (2.0 <= u < 8.0 and 1.5 <= v < 9.0):
        return 0
    if (u - 5.0) ** 2 + ((v - 5.4) * 1.1) ** 2 < 1.6 ** 2:  # radiation mark
        r = math.hypot(u - 5.0, v - 5.4)
        ang = math.degrees(math.atan2(v - 5.4, u - 5.0)) % 120
        if r < 0.45 or (r > 0.7 and 0 <= ang < 60):
            return 1
        return YELLOW[5]
    if v < 2.5:  # lid
        return 208
    if 3.0 <= v < 3.5 or 7.8 <= v < 8.3:  # rims
        return 82
    return _DRUM[min(len(_DRUM) - 1, int((u - 2.0) / 6.0 * len(_DRUM)))]


CARGO_ICONS = {"powr": icon_power, "uran": icon_uranium}


def render_icon(fn, s):
    n = ICON_W * s
    px = [[fn((x + 0.5) / s, (y + 0.5) / s) for x in range(n)] for y in range(n)]
    im = Image.new("P", (n, n), 0)
    for y in range(n):
        for x in range(n):
            c = px[y][x]
            if not c and any(0 <= y + dy < n and 0 <= x + dx < n and px[y + dy][x + dx]
                             for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                c = OUTLINE
            im.putpixel((x, y), c)
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
    """NML for every spriteset, with 2x alternatives, matching the sheets."""
    out = [NML_BEGIN + " - written by tools/make_sprites.py, do not edit by hand */"]
    out.append("/* ground: %s */" % ", ".join("%d=%s" % (k, g) for k, g in enumerate(GROUND_ORDER)))

    def block(ss, fname, n, w, h1, h2, xoff, yoff):
        out.append('spriteset(%s, "sprites/%s.png") { %s }'
                   % (ss, fname, _entries(fname + ".png", n, 1, w, h1, xoff, yoff)))
        out.append('alternative_sprites(%s, ZOOM_LEVEL_IN_2X, BIT_DEPTH_8BPP, "sprites/%s_2x.png") { %s }'
                   % (ss, fname, _entries(fname + "_2x.png", n, 2, w, h2, xoff, yoff)))

    block("ss_ground", "ground", len(GROUND_ORDER), CELL_W, 31, 63, -31, 0)
    for name, (_, H, tiles) in INDUSTRIES.items():
        out.append("/* %s: %s */" % (name, ", ".join("%d=%s" % (k, t[0]) for k, t in enumerate(tiles))))
        block("ss_" + name, name, len(tiles), CELL_W, 32 + H, (32 + H) * 2, -31, -H)
    for k, cargo in enumerate(CARGO_ICONS):
        w = ICON_W
        out.append('spriteset(ss_cargo_%s, "sprites/cargo_icons.png") { [%d,0,%d,%d,0,0] }' % (cargo, k * w, w, w))
        out.append('alternative_sprites(ss_cargo_%s, ZOOM_LEVEL_IN_2X, BIT_DEPTH_8BPP, "sprites/cargo_icons_2x.png") '
                   '{ [%d,0,%d,%d,0,0] }' % (cargo, k * w * 2, w * 2, w * 2))
    out.append(NML_END)
    return "\n".join(out)


def update_nml():
    with open(NML_FILE, encoding="utf-8") as f:
        text = f.read()
    a, b = text.find(NML_BEGIN), text.find(NML_END)
    if a < 0 or b < 0:
        sys.exit("generated-spriteset markers not found in energy_transition.nml")
    text = text[:a] + nml_spritesets() + text[b + len(NML_END):]
    with open(NML_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    print("updated spritesets in", os.path.relpath(NML_FILE, ROOT))


def main():
    only = set(sys.argv[1:])
    for s, suffix in ((1, ""), (2, "_2x")):
        if not only or "ground" in only:
            save(render_ground(s), "ground%s.png" % suffix)
        if not only or "cargo_icons" in only:
            save(render_icons(s), "cargo_icons%s.png" % suffix)
        for name in INDUSTRIES:
            if not only or name in only:
                save(render_sheet(name, s), "%s%s.png" % (name, suffix))
    update_nml()


if __name__ == "__main__":
    main()
