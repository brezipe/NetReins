"""Vygeneruje ikonu aplikace (icon.ico pro exe a okno, icon.png) bez dalších knihoven.

Motiv: tachometr – tmavý zaoblený čtverec, oblouk stupnice s barevným
přechodem a ručička. Kreslí se vektorově se supersamplingem, takže je ikona
ostrá v každé velikosti.

Použití:  python make_icon.py
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

SIZES = (16, 24, 32, 48, 64, 128, 256)
SS = 4  # supersampling na osu

BG_TOP = (44, 52, 72)
BG_BOTTOM = (18, 21, 30)
TRACK = (70, 78, 98)
ACCENT_A = (76, 194, 255)  # azurová (začátek stupnice)
ACCENT_B = (139, 108, 255)  # fialová (konec vyplněné části)
NEEDLE = (245, 247, 250)

START, SWEEP = 225.0, 270.0  # stupnice od 225° po směru hodin přes vršek
FILL = 0.62  # kam ukazuje ručička (0..1)


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
    return math.hypot(px - ax - vx * t, py - ay - vy * t)


def render(size: int) -> bytes:
    small = size <= 24  # malé ikony: tlustší čáry, méně detailů
    radius = 0.22  # zaoblení rohů (relativně)
    ring_r = 0.30
    ring_w = 0.11 if small else 0.085
    needle_w = 0.05 if small else 0.032
    na = math.radians(START - FILL * SWEEP)
    nx, ny = 0.5 + math.cos(na) * 0.29, 0.56 - math.sin(na) * 0.29
    cx, cy = 0.5, 0.56

    out = bytearray()
    for y in range(size):
        out.append(0)  # PNG filter: none
        for x in range(size):
            r = g = b = a = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    u = (x + (sx + 0.5) / SS) / size
                    v = (y + (sy + 0.5) / SS) / size
                    # zaoblený čtverec s malým okrajem
                    m = 0.03
                    qx = max(abs(u - 0.5) - (0.5 - m - radius), 0.0)
                    qy = max(abs(v - 0.5) - (0.5 - m - radius), 0.0)
                    if math.hypot(qx, qy) > radius:
                        continue
                    col = _lerp(BG_TOP, BG_BOTTOM, v)
                    dx, dy = u - cx, v - cy
                    d = math.hypot(dx, dy)
                    ang = math.degrees(math.atan2(-dy, dx))
                    if ang < -90:
                        ang += 360
                    if abs(d - ring_r) <= ring_w / 2 and -45 <= ang <= 225:
                        p = (START - ang) / SWEEP
                        col = _lerp(ACCENT_A, ACCENT_B, p / FILL) if p <= FILL else TRACK
                    if _seg_dist(u, v, cx, cy, nx, ny) <= needle_w / 2 or d <= (0.075 if small else 0.06):
                        col = NEEDLE
                    r += col[0]
                    g += col[1]
                    b += col[2]
                    a += 1
            n = SS * SS
            if a:
                out += bytes((round(r / a), round(g / a), round(b / a), round(255 * a / n)))
            else:
                out += b"\0\0\0\0"
    return _png(size, bytes(out))


def _png(size: int, raw: bytes) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8 bit RGBA
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def _ico(images: dict[int, bytes]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for size, png in images.items():
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    return header + entries + data


def main() -> None:
    here = Path(__file__).resolve().parent
    images = {s: render(s) for s in SIZES}
    (here / "icon.ico").write_bytes(_ico(images))
    (here / "icon.png").write_bytes(images[256])
    print("icon.ico, icon.png hotovo")


if __name__ == "__main__":
    main()
