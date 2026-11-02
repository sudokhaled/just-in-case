"""The library's icon (a white star on deep green), drawn without any image library.

PNG files are written with zlib and struct, so the build stays standard-library only.
The star sits inside the central 60% so the icon also works as a "maskable" app icon,
which phones crop into circles or rounded squares.
"""

import math
import struct
import zlib

BACKGROUND = (0x1E, 0x3A, 0x2F)
STAR = (0xFF, 0xFF, 0xFF)
SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
       '<rect width="100" height="100" fill="#1e3a2f"/>'
       '<path fill="#fff" d="%s"/></svg>')


def star_points(size, scale=0.30):
    """The 10 corners of a 5-pointed star centered in a size x size square."""
    cx, cy = size / 2.0, size * 0.52
    outer, inner = size * scale, size * scale * 0.382
    pts = []
    for k in range(10):
        r = outer if k % 2 == 0 else inner
        a = -math.pi / 2 + k * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def svg():
    d = "M" + " L".join("%.1f %.1f" % p for p in star_points(100)) + " Z"
    return SVG % d


def png(size, samples=4):
    """A size x size RGBA PNG of the icon, anti-aliased by scanline coverage."""
    pts = star_points(size)
    edges = list(zip(pts, pts[1:] + pts[:1]))
    rows = []
    for y in range(size):
        cover = [0.0] * size
        for sub in range(samples):
            sy = y + (sub + 0.5) / samples
            xs = []
            for (x0, y0), (x1, y1) in edges:
                if (y0 <= sy < y1) or (y1 <= sy < y0):
                    xs.append(x0 + (sy - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for a, b in zip(xs[0::2], xs[1::2]):
                for x in range(max(0, int(a)), min(size, int(math.ceil(b)))):
                    cover[x] += (min(b, x + 1) - max(a, x)) / samples
        row = bytearray()
        for c in cover:
            c = min(1.0, max(0.0, c))
            row += bytes(round(bg + (st - bg) * c) for bg, st in zip(BACKGROUND, STAR)) + b"\xff"
        rows.append(bytes(row))
    raw = b"".join(b"\x00" + r for r in rows)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
