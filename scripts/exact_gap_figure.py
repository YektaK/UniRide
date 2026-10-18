#!/usr/bin/env python3
"""Deterministic figure writer of the WP-E6 gap report: one scene, two backends (SVG and PNG), standard library only.

The existing paper figures (``scripts/plan_fleet_pareto.py``, ``plan_resource_profile.py``) are hand-written SVG from the
standard library; the project venv has no plotting library. This module keeps that style and adds a small PNG
rasteriser (a 5x7 bitmap font, filled and hollow markers, axis-aligned lines) so that no plotting dependency is added.

Determinism: no timestamps, no random numbers, no set iteration, fixed float formatting, a fixed pixel scale (the PNG is
the scene at 2x, pHYs 192 dpi) and zlib level 9 (identical bytes need the same zlib build; the report manifest records
``zlib.ZLIB_VERSION``). There is no matplotlib, so there is no ``svg.hashsalt``.
"""
from __future__ import annotations

import struct
import zlib
from typing import List, Sequence, Tuple

PNG_SCALE = 2  # pixels per scene unit
PNG_DPI = 192

_GLYPHS = {
    " ": ("00000",) * 7,
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "10001", "11001", "10101", "10011", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00001", "00010", "00100", "01000", "10000", "10000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    ">": ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "%": ("11000", "11001", "00010", "00100", "01000", "10011", "00011"),
    "*": ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "|": ("00100",) * 7,
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
}
GLYPH_W, GLYPH_H = 5, 7


def fmt(value: float) -> str:
    """Fixed float formatting (two decimals, trailing zeros removed) used by the SVG backend."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def text_units(text: str, size: float) -> float:
    """Width of ``text`` in scene units as the PNG bitmap font draws it (also used to place legends)."""
    return _png_scale_for(size) * (GLYPH_W + 1) * len(text) / PNG_SCALE


def _png_scale_for(size: float) -> int:
    return 3 if size >= 14 else 2


class Scene:
    """A list of drawing primitives in scene units (origin top left)."""

    def __init__(self, width: int, height: int, title: str, description: str):
        self.width, self.height, self.title, self.description = width, height, title, description
        self.items: List[tuple] = []

    def line(self, x1, y1, x2, y2, color="#333333", width=1.0, dash=None):
        self.items.append(("line", x1, y1, x2, y2, color, width, dash))

    def rect(self, x, y, w, h, fill="none", stroke="none", width=1.0):
        self.items.append(("rect", x, y, w, h, fill, stroke, width))

    def marker(self, shape, cx, cy, r, color, hollow=False, opacity=1.0):
        self.items.append(("marker", shape, cx, cy, r, color, hollow, opacity))

    def text(self, x, y, text, size=11, anchor="start", color="#222222", bold=False, rotate=False):
        self.items.append(("text", x, y, str(text), size, anchor, color, bold, rotate))

    # ------------------------------------------------------------------ SVG
    def to_svg(self) -> str:
        out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
               'font-family="Arial, Helvetica, sans-serif">' % (self.width, self.height, self.width, self.height),
               "<title>%s</title>" % esc(self.title), "<desc>%s</desc>" % esc(self.description),
               '<rect width="100%" height="100%" fill="#ffffff"/>']
        for item in self.items:
            kind = item[0]
            if kind == "line":
                _, x1, y1, x2, y2, color, width, dash = item
                out.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"%s/>' % (
                    fmt(x1), fmt(y1), fmt(x2), fmt(y2), color, fmt(width),
                    ' stroke-dasharray="%s"' % dash if dash else ""))
            elif kind == "rect":
                _, x, y, w, h, fill, stroke, width = item
                out.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
                    fmt(x), fmt(y), fmt(w), fmt(h), fill, stroke, fmt(width)))
            elif kind == "marker":
                out.append(_svg_marker(*item[1:]))
            else:
                _, x, y, text, size, anchor, color, bold, rotate = item
                attrs = 'x="%s" y="%s" font-size="%s" text-anchor="%s" fill="%s"' % (
                    fmt(x), fmt(y), fmt(size), anchor, color)
                if bold:
                    attrs += ' font-weight="bold"'
                if rotate:
                    attrs += ' transform="rotate(-90 %s %s)"' % (fmt(x), fmt(y))
                out.append("<text %s>%s</text>" % (attrs, esc(text)))
        out.append("</svg>")
        return "\n".join(out) + "\n"

    # ------------------------------------------------------------------ PNG
    def to_png(self) -> bytes:
        canvas = _Canvas(self.width * PNG_SCALE, self.height * PNG_SCALE)
        for item in self.items:
            kind = item[0]
            if kind == "line":
                canvas.line(*item[1:])
            elif kind == "rect":
                canvas.rect(*item[1:])
            elif kind == "marker":
                canvas.marker(*item[1:])
            else:
                canvas.text(*item[1:])
        return canvas.png()


def _svg_shape_points(shape: str, cx: float, cy: float, r: float) -> str:
    if shape == "square":
        return "%s,%s %s,%s %s,%s %s,%s" % (fmt(cx - r), fmt(cy - r), fmt(cx + r), fmt(cy - r), fmt(cx + r), fmt(cy + r),
                                           fmt(cx - r), fmt(cy + r))
    if shape == "diamond":
        return "%s,%s %s,%s %s,%s %s,%s" % (fmt(cx), fmt(cy - 1.3 * r), fmt(cx + 1.3 * r), fmt(cy), fmt(cx), fmt(cy + 1.3 * r),
                                           fmt(cx - 1.3 * r), fmt(cy))
    return "%s,%s %s,%s %s,%s" % (fmt(cx), fmt(cy - 1.2 * r), fmt(cx + 1.1 * r), fmt(cy + 0.9 * r), fmt(cx - 1.1 * r),
                                  fmt(cy + 0.9 * r))  # triangle (up)


def _svg_marker(shape, cx, cy, r, color, hollow, opacity) -> str:
    paint = ('fill="none" stroke="%s" stroke-width="1.6"' % color) if hollow else (
        'fill="%s" fill-opacity="%s" stroke="%s" stroke-width="0.6"' % (color, fmt(opacity), color))
    if shape == "circle":
        return '<circle cx="%s" cy="%s" r="%s" %s/>' % (fmt(cx), fmt(cy), fmt(r), paint)
    return '<polygon points="%s" %s/>' % (_svg_shape_points(shape, cx, cy, r), paint)


def _rgb(color: str) -> Tuple[int, int, int]:
    if color in ("none", ""):
        raise ValueError("no colour")
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


class _Canvas:
    def __init__(self, width: int, height: int):
        self.w, self.h = width, height
        self.px = bytearray(b"\xff" * (width * height * 3))

    def _put(self, x: int, y: int, rgb, alpha: float = 1.0):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            if alpha >= 1.0:
                self.px[i:i + 3] = bytes(rgb)
            else:
                for c in range(3):
                    self.px[i + c] = int(round(self.px[i + c] * (1 - alpha) + rgb[c] * alpha))

    def _fill(self, x0: float, y0: float, x1: float, y1: float, rgb, alpha: float = 1.0):
        for y in range(max(0, int(round(y0))), min(self.h, int(round(y1)))):
            for x in range(max(0, int(round(x0))), min(self.w, int(round(x1)))):
                self._put(x, y, rgb, alpha)

    def rect(self, x, y, w, h, fill, stroke, width):
        s = PNG_SCALE
        if fill not in ("none", ""):
            self._fill(x * s, y * s, (x + w) * s, (y + h) * s, _rgb(fill))
        if stroke not in ("none", ""):
            for (a, b, c, d) in ((x, y, x + w, y), (x, y + h, x + w, y + h), (x, y, x, y + h), (x + w, y, x + w, y + h)):
                self.line(a, b, c, d, stroke, width)

    def line(self, x1, y1, x2, y2, color, width, dash=None):
        s = PNG_SCALE
        rgb = _rgb(color)
        t = max(1.0, width * s)
        if abs(y1 - y2) < 1e-9 or abs(x1 - x2) < 1e-9:  # axis-aligned (the only lines the report draws)
            horizontal = abs(y1 - y2) < 1e-9
            lo, hi = sorted((x1, x2) if horizontal else (y1, y2))
            segments = [(lo, hi)]
            if dash:
                on, off = [float(v) for v in dash.split()[:2]]
                segments, pos = [], lo
                while pos < hi:
                    segments.append((pos, min(hi, pos + on)))
                    pos += on + off
            for a, b in segments:
                if horizontal:
                    self._fill(a * s, y1 * s - t / 2, b * s, y1 * s + t / 2, rgb)
                else:
                    self._fill(x1 * s - t / 2, a * s, x1 * s + t / 2, b * s, rgb)
            return
        n = int(max(abs(x2 - x1), abs(y2 - y1)) * s) + 1  # general segment: square brush
        for k in range(n + 1):
            px = (x1 + (x2 - x1) * k / n) * s
            py = (y1 + (y2 - y1) * k / n) * s
            self._fill(px - t / 2, py - t / 2, px + t / 2, py + t / 2, rgb)

    @staticmethod
    def _inside(shape: str, dx: float, dy: float, r: float) -> bool:
        if shape == "circle":
            return dx * dx + dy * dy <= r * r
        if shape == "square":
            return abs(dx) <= r and abs(dy) <= r
        if shape == "diamond":
            return abs(dx) + abs(dy) <= 1.3 * r
        return -1.2 * r <= dy <= 0.9 * r and abs(dx) <= 1.1 * r * (dy + 1.2 * r) / (2.1 * r)  # triangle (up)

    def marker(self, shape, cx, cy, r, color, hollow, opacity):
        s = PNG_SCALE
        rgb, cxp, cyp, rp = _rgb(color), cx * s, cy * s, r * s
        ring = 1.6 * s
        box = int(rp * 1.5) + 2
        for y in range(int(cyp) - box, int(cyp) + box + 1):
            for x in range(int(cxp) - box, int(cxp) + box + 1):
                dx, dy = x + 0.5 - cxp, y + 0.5 - cyp
                if not self._inside(shape, dx, dy, rp):
                    continue
                if hollow and rp - ring > 0 and self._inside(shape, dx, dy, rp - ring):
                    continue
                self._put(x, y, rgb, 1.0 if hollow else opacity)

    def text(self, x, y, text, size, anchor, color, bold, rotate):
        scale = _png_scale_for(size)
        rgb = _rgb(color)
        glyphs = [_GLYPHS.get(ch if ch in _GLYPHS else ch.upper(), _GLYPHS["?"]) for ch in text]
        width = len(glyphs) * (GLYPH_W + 1) * scale - scale
        height = GLYPH_H * scale
        origin = x * PNG_SCALE - (width / 2 if anchor == "middle" else width if anchor == "end" else 0)
        base = y * PNG_SCALE  # SVG y is the baseline; the bitmap bottom sits on it
        bitmap = []
        for i, glyph in enumerate(glyphs):
            for row, bits in enumerate(glyph):
                for col, bit in enumerate(bits):
                    if bit == "1":
                        bitmap.append((i * (GLYPH_W + 1) * scale + col * scale, row * scale))
        for bx, by in bitmap:
            for fx in range(scale):
                for fy in range(scale):
                    if rotate:  # text reads bottom to top, anchored at (x, y) (rotate(-90) about the anchor)
                        px, py = int(x * PNG_SCALE + by + fy - height), int(y * PNG_SCALE + (width / 2 if anchor == "middle" else 0)
                                                                          - bx - fx)
                    else:
                        px, py = int(origin + bx + fx), int(base - height + by + fy)
                    self._put(px, py, rgb)
                    if bold:
                        self._put(px + 1, py, rgb)

    def png(self) -> bytes:
        raw = bytearray()
        stride = self.w * 3
        for row in range(self.h):
            raw.append(0)
            raw += self.px[row * stride:(row + 1) * stride]

        def chunk(tag: bytes, data: bytes) -> bytes:
            body = tag + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

        ppm = int(round(PNG_DPI / 0.0254))
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
                + chunk(b"pHYs", struct.pack(">IIB", ppm, ppm, 1)) + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
                + chunk(b"IEND", b""))


# ---------------------------------------------------------------------------------------------------------------
# The gap figure: per-wave (or per-option) gD against students, one panel per R, marker by dK.
# ---------------------------------------------------------------------------------------------------------------
SHAPE_DK0, SHAPE_DKPOS = "circle", "triangle"
KIND_COLOR = {"base": "#0072B2", "q": "#D55E00"}
KIND_DODGE = {"base": -0.14, "q": 0.14}  # a horizontal offset (students) so base and q at the same point both show


def nice_step(top: float) -> float:
    for step in (0.005, 0.01, 0.02, 0.025, 0.05, 0.1, 0.2):
        if top / step <= 6:
            return step
    return 0.5


def gap_points(rows: Sequence[dict]) -> List[dict]:
    """Drawable points of one panel from wave_gaps.csv rows: (students, y, shape, kind) with the group size.

    ``dK = 0`` rows draw ``gD`` (a circle). ``dK >= 1`` rows have no ``gD`` (``K_GA > K*``, design 1.2): they draw
    ``gD_free`` (a hollow triangle). Rows without a GA answer or without an exact value are not drawn.
    """
    groups: dict = {}
    for r in rows:
        if r["dK"] == "" or r["students"] == "":
            continue
        positive = int(r["dK"]) >= 1
        y = r["gD_free"] if positive else r["gD"]
        if y == "":
            continue
        key = (int(r["students"]), round(float(y), 6), SHAPE_DKPOS if positive else SHAPE_DK0, r["option"] if r["option"] == "base" else "q")
        groups[key] = groups.get(key, 0) + 1
    return [{"students": k[0], "y": k[1], "shape": k[2], "kind": k[3], "n": n} for k, n in sorted(groups.items())]


def build_gap_figure(panels: Sequence[Sequence[dict]], panel_titles: Sequence[str], columns: int, title: str,
                     subtitle: str, kinds: Sequence[str], description: str) -> Scene:
    """``panels``: one list of wave_gaps rows per panel, laid out row-major in ``columns`` columns."""
    pw, ph, left, top, gapx, gapy = 360, 250, 70, 120, 56, 70
    rows_n = (len(panels) + columns - 1) // columns
    width = left + columns * (pw + gapx) - gapx + 30
    height = top + rows_n * (ph + gapy) - gapy + 50
    scene = Scene(width, height, title, description)
    points = [gap_points(p) for p in panels]
    ymax = max([pt["y"] for pts in points for pt in pts] + [0.0])
    step = nice_step(max(ymax, 0.005))
    ytop = step * (int(ymax / step + 1e-9) + 1)
    ylo = -0.06 * ytop
    xmax = 21
    scene.text(left, 24, title, size=16, bold=True)
    scene.text(left, 44, subtitle, size=12, color="#444444")
    lx = left
    legend_y = 76
    for kind in kinds:
        label = {"base": "base (K, xbase vs GA base)", "q": "q (K_m, xq vs GA q)"}[kind] if len(kinds) > 1 else "wave"
        scene.marker("circle", lx + 5, legend_y - 4, 4.5, KIND_COLOR[kind])
        scene.text(lx + 14, legend_y, label + "; dK = 0, y = gD", size=11)
        lx += 14 + text_units(label + "; dK = 0, y = gD", 11) + 24
    scene.marker("triangle", lx + 5, legend_y - 4, 4.5, "#444444", hollow=True)
    scene.text(lx + 14, legend_y, "dK >= 1, gD not defined: y = gD_free (hollow)", size=11)
    scene.text(left, 96, "A point is one wave (or option) per distinct (students, y); 'xN' = N coincident rows. Base and q are offset by "
                         "+-0.14 students.", size=11, color="#444444")
    for idx, (pts, ptitle) in enumerate(zip(points, panel_titles)):
        x0 = left + (idx % columns) * (pw + gapx)
        y0 = top + (idx // columns) * (ph + gapy)
        X = lambda v, x0=x0: x0 + pw * v / xmax
        Y = lambda v, y0=y0: y0 + ph - ph * (v - ylo) / (ytop - ylo)
        scene.rect(x0, y0, pw, ph, fill="#ffffff", stroke="#888888", width=0.8)
        k = 0
        while k * step <= ytop + 1e-9:
            scene.line(x0, Y(k * step), x0 + pw, Y(k * step), color="#eeeeee")
            scene.text(x0 - 5, Y(k * step) + 4, ("%g" % (k * step)), size=11, anchor="end", color="#333333")
            k += 1
        for v in (0, 5, 10, 15, 20):
            scene.line(X(v), y0, X(v), y0 + ph, color="#f0f0f0")
            scene.text(X(v), y0 + ph + 14, str(v), size=11, anchor="middle", color="#333333")
        scene.line(x0, Y(0), x0 + pw, Y(0), color="#999999", dash="4 3")
        scene.text(x0 + pw / 2, y0 - 8, ptitle, size=12, anchor="middle", bold=True, color="#111111")
        scene.text(x0 + pw / 2, y0 + ph + 32, "Students per wave", size=11, anchor="middle")
        if idx % columns == 0:
            scene.text(x0 - 48, y0 + ph / 2, "gD (or gD_free, hollow)", size=11, anchor="middle", rotate=True)
        for pt in pts:
            cx = X(pt["students"] + (KIND_DODGE[pt["kind"]] if len(kinds) > 1 else 0))
            cy = Y(pt["y"])
            scene.marker(pt["shape"], cx, cy, 4.5, KIND_COLOR[pt["kind"]], hollow=pt["shape"] == SHAPE_DKPOS, opacity=0.55)
            if pt["n"] > 1:
                scene.text(cx + 7, cy - 5, "x%d" % pt["n"], size=11, color=KIND_COLOR[pt["kind"]])
    return scene
