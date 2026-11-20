#!/usr/bin/env python3
"""
Deterministic pixel-art (.bmp) and retro SFX (.wav) asset generator
for Skyline Strike (Thumby Color 128x128 16-bit RGB565).

Generates:
- 16-bit RGB565 BITMAPV3INFOHEADER .bmp files for 128x128 sky backgrounds & 32x32 icon
- 8-bit indexed .bmp files for crisp pixel-art sprites, guns, enemies, props & parallax layers
- 11025 Hz 8-bit mono .wav sound effects compatible with Thumby Color WaveSoundResource
"""

import math
import os
import random
import struct

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DIR = os.path.join(ROOT_DIR, "game")
ASSETS_DIR = os.path.join(GAME_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Reserved transparency color key: pure magenta (255, 0, 255) -> RGB565 0xF81F
TRANSPARENT_RGB = (255, 0, 255)
TRANSPARENT_565 = 0xF81F


def rgb_to_565(r, g, b, allow_key=False):
    val = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    if not allow_key and val == TRANSPARENT_565:
        # Nudge green slightly so opaque pixels never accidentally turn transparent
        val = 0xF83F
    return val


def sanitize_rgb(rgb, allow_key=False):
    if allow_key:
        return rgb
    r, g, b = rgb
    if rgb_to_565(r, g, b, allow_key=True) == TRANSPARENT_565:
        return (r, min(255, g + 8), b)
    return rgb


def write_bmp_16bit_565(path, w, h, pixels_rgb):
    """Write a BITMAPV3INFOHEADER (56-byte) 16-bit RGB565 BMP for Thumby Color."""
    row_bytes = ((w * 2 + 3) // 4) * 4
    img_size = row_bytes * h
    offset = 14 + 56
    file_size = offset + img_size
    with open(path, "wb") as f:
        f.write(struct.pack("<2sIHHI", b"BM", file_size, 0, 0, offset))
        f.write(struct.pack("<IIIHHIIIIII", 56, w, h, 1, 16, 3, img_size, 2835, 2835, 0, 0))
        f.write(struct.pack("<IIII", 0xF800, 0x07E0, 0x001F, 0x0000))
        for y in range(h - 1, -1, -1):
            row = bytearray(row_bytes)
            base = y * w
            for x in range(w):
                r, g, b = pixels_rgb[base + x]
                val = rgb_to_565(r, g, b, allow_key=False)
                row[x * 2] = val & 0xFF
                row[x * 2 + 1] = (val >> 8) & 0xFF
            f.write(row)


def write_bmp_8bit(path, w, h, pixels_rgb, transparent_key=True):
    """Write an 8-bit indexed uncompressed BMP with index 0 = TRANSPARENT_RGB."""
    palette = []
    color_to_idx = {}
    if transparent_key:
        palette.append(TRANSPARENT_RGB)
        color_to_idx[TRANSPARENT_RGB] = 0

    indices = bytearray(w * h)
    for i, raw_rgb in enumerate(pixels_rgb):
        is_key = transparent_key and (raw_rgb is None or raw_rgb == TRANSPARENT_RGB)
        rgb = TRANSPARENT_RGB if is_key else sanitize_rgb(raw_rgb, allow_key=False)
        idx = color_to_idx.get(rgb)
        if idx is None:
            idx = len(palette)
            if idx >= 256:
                raise ValueError(f"Palette overflow (>256 colors) in {path}")
            palette.append(rgb)
            color_to_idx[rgb] = idx
        indices[i] = idx

    row_bytes = ((w + 3) // 4) * 4
    img_size = row_bytes * h
    ncolors = len(palette)
    offset = 14 + 40 + 256 * 4
    file_size = offset + img_size
    with open(path, "wb") as f:
        f.write(struct.pack("<2sIHHI", b"BM", file_size, 0, 0, offset))
        f.write(struct.pack("<IIIHHIIIIII", 40, w, h, 1, 8, 0, img_size, 2835, 2835, 256, ncolors))
        for i in range(256):
            r, g, b = palette[i] if i < ncolors else (0, 0, 0)
            f.write(struct.pack("<BBBB", b, g, r, 0))
        for y in range(h - 1, -1, -1):
            row = bytearray(row_bytes)
            start = y * w
            row[0:w] = indices[start:start + w]
            f.write(row)


class Canvas:
    def __init__(self, w, h, fill=None):
        self.w = w
        self.h = h
        self.px = [fill] * (w * h)

    def set(self, x, y, color):
        ix, iy = int(x), int(y)
        if 0 <= ix < self.w and 0 <= iy < self.h:
            self.px[iy * self.w + ix] = color

    def get(self, x, y):
        ix, iy = int(x), int(y)
        if 0 <= ix < self.w and 0 <= iy < self.h:
            return self.px[iy * self.w + ix]
        return None

    def rect(self, x, y, w, h, color):
        for dy in range(h):
            for dx in range(w):
                self.set(x + dx, y + dy, color)

    def hline(self, x, y, length, color):
        for dx in range(length):
            self.set(x + dx, y, color)

    def vline(self, x, y, length, color):
        for dy in range(length):
            self.set(x, y + dy, color)

    def circle(self, cx, cy, r, color):
        r2 = r * r
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                    self.set(x, y, color)

    def stamp_ascii(self, ox, oy, rows, cmap):
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch in cmap and cmap[ch] is not None:
                    self.set(ox + x, oy + y, cmap[ch])


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


BAYER_2X2 = ((0.0, 0.5), (0.75, 0.25))


def generate_sky(filename, stops, moon_pos, moon_color, halo_color, seed):
    rng = random.Random(seed)
    c = Canvas(128, 128, (0, 0, 0))
    for y in range(128):
        t = y / 127.0
        # Find stop segment
        seg_col = stops[-1][1]
        for i in range(len(stops) - 1):
            t0, col0 = stops[i]
            t1, col1 = stops[i + 1]
            if t0 <= t <= t1:
                local = (t - t0) / max(1e-6, (t1 - t0))
                for x in range(128):
                    dither = (BAYER_2X2[y & 1][x & 1] - 0.375) * 0.08
                    c.set(x, y, lerp_color(col0, col1, local + dither))
                break
        else:
            for x in range(128):
                c.set(x, y, seg_col)

    # Pixel stars in upper sky
    for _ in range(38):
        sx = rng.randint(2, 125)
        sy = rng.randint(14, 72)
        bright = rng.choice([(190, 210, 255), (255, 245, 210), (150, 175, 225)])
        c.set(sx, sy, bright)
        if rng.random() < 0.2:
            dim = tuple(v // 2 for v in bright)
            c.set(sx - 1, sy, dim)
            c.set(sx + 1, sy, dim)
            c.set(sx, sy - 1, dim)
            c.set(sx, sy + 1, dim)

    # Soft moon halo & crisp pixel moon
    mx, my = moon_pos
    for y in range(my - 18, my + 19):
        for x in range(mx - 18, mx + 19):
            d = math.hypot(x - mx, y - my)
            if 8.5 < d < 16.5 and 0 <= x < 128 and 0 <= y < 128:
                base = c.get(x, y)
                strength = (1.0 - (d - 8.5) / 8.0) * 0.35
                c.set(x, y, lerp_color(base, halo_color, strength))
    c.circle(mx, my, 8.2, moon_color)
    # Subtle craters on moon
    crater = lerp_color(moon_color, halo_color, 0.35)
    c.circle(mx - 3, my - 2, 2.0, crater)
    c.circle(mx + 2, my + 2, 1.5, crater)
    c.set(mx + 3, my - 3, crater)

    # Subtle drifting twilight cloud streaks
    cloud_col = lerp_color(stops[1][1], stops[2][1], 0.55)
    cloud_hi = lerp_color(cloud_col, (255, 220, 200), 0.22)
    for cx, cy, cw in [(22, 42, 26), (76, 54, 30), (10, 66, 22), (96, 36, 20)]:
        c.hline(cx + 3, cy, cw - 6, cloud_hi)
        c.hline(cx, cy + 1, cw, cloud_col)
        c.hline(cx + 2, cy + 2, cw - 4, cloud_col)

    write_bmp_16bit_565(os.path.join(ASSETS_DIR, filename), 128, 128, c.px)


def generate_parallax_far():
    """Seamless 128x56 distant city skyline silhouettes with tiny lit windows."""
    c = Canvas(128, 56, None)
    sil = (22, 22, 46)
    sil_hi = (34, 34, 68)
    win_y = (232, 200, 110)
    win_c = (100, 205, 235)
    win_dim = (72, 66, 108)

    buildings = [
        (0, 14, 18), (16, 26, 14), (28, 8, 16), (42, 20, 18),
        (58, 12, 14), (70, 24, 16), (84, 6, 18), (100, 18, 14), (112, 10, 16),
    ]
    rng = random.Random(101)
    for bx, top, bw in buildings:
        c.rect(bx, top, bw, 56 - top, sil)
        c.hline(bx, top, bw, sil_hi)
        c.vline(bx, top, 56 - top, sil_hi)
        # Spire / stepped crown on tall towers
        if top <= 14:
            mid = bx + bw // 2
            c.rect(bx + 3, top - 3, bw - 6, 3, sil)
            c.vline(mid, max(0, top - 8), 5, sil_hi)
            if top <= 8:
                c.set(mid, max(0, top - 8), (255, 160, 80))
        # Tiny windows
        for wy in range(top + 3, 52, 4):
            for wx in range(bx + 2, bx + bw - 2, 3):
                r = rng.random()
                if r < 0.25:
                    c.set(wx, wy, win_y)
                elif r < 0.36:
                    c.set(wx, wy, win_c)
                elif r < 0.55:
                    c.set(wx, wy, win_dim)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "bg_far.bmp"), 128, 56, c.px)


def generate_parallax_mid():
    """Seamless 128x64 midground skyscrapers with window grids & neon trims."""
    c = Canvas(128, 64, None)
    body = (30, 32, 60)
    shade = (22, 24, 48)
    edge = (54, 60, 98)
    win_warm = (245, 205, 108)
    win_cool = (96, 224, 248)
    win_off = (42, 46, 78)
    neon_c = (60, 235, 255)
    neon_p = (245, 96, 188)

    buildings = [
        (0, 16, 22, neon_c),
        (20, 28, 18, None),
        (36, 10, 24, neon_p),
        (58, 22, 20, None),
        (76, 14, 22, neon_c),
        (96, 26, 16, None),
        (110, 12, 18, neon_p),
    ]
    rng = random.Random(202)
    for bx, top, bw, neon in buildings:
        c.rect(bx, top, bw, 64 - top, body)
        c.rect(bx + bw - 4, top, 4, 64 - top, shade)
        c.hline(bx, top, bw, edge)
        c.vline(bx, top, 64 - top, edge)
        if neon:
            c.hline(bx + 2, top + 2, bw - 5, neon)
        # Water tank / rooftop box silhouette on some
        if bw >= 22:
            c.rect(bx + 4, top - 4, 6, 4, shade)
            c.hline(bx + 4, top - 4, 6, edge)
        # Windows 2x2
        for wy in range(top + 6, 60, 5):
            for wx in range(bx + 3, bx + bw - 5, 4):
                r = rng.random()
                col = win_off
                if r < 0.24:
                    col = win_warm
                elif r < 0.36:
                    col = win_cool
                c.rect(wx, wy, 2, 3, col)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "bg_mid.bmp"), 128, 64, c.px)


def generate_rooftop_tiles():
    """Three distinct 32x64 playable building facade tiles with crisp roof parapets."""
    # 1) Brick Brownstone
    c = Canvas(32, 64, (58, 40, 48))
    # Crisp walkable concrete parapet cap (top 5 rows)
    c.hline(0, 0, 32, (200, 214, 232))  # bright rooftop rim
    c.hline(0, 1, 32, (148, 162, 186))
    c.hline(0, 2, 32, (98, 108, 132))
    c.hline(0, 3, 32, (40, 30, 38))     # sharp ledge shadow
    # Brick courses
    for y in range(4, 64):
        if y % 4 == 0:
            c.hline(0, y, 32, (46, 31, 38))
        else:
            off = 4 if ((y // 4) % 2) else 0
            for x in range(off, 32, 8):
                c.set(x, y, (46, 31, 38))
            if (y % 4) == 1:
                for x in range(0, 32, 4):
                    c.set(x, y, (72, 50, 58))
    # Lit & dark windows
    rng = random.Random(301)
    for row_y in (9, 23, 37, 51):
        for col_x in (4, 18):
            c.rect(col_x - 1, row_y - 1, 10, 11, (32, 24, 32))
            c.hline(col_x - 1, row_y + 10, 10, (120, 128, 148))  # window sill
            lit = rng.random() < 0.6
            if lit:
                c.rect(col_x, row_y, 8, 9, (242, 196, 98))
                c.rect(col_x, row_y, 8, 3, (255, 228, 148))
                c.vline(col_x + 4, row_y, 9, (92, 68, 52))
                c.hline(col_x, row_y + 4, 8, (92, 68, 52))
            else:
                c.rect(col_x, row_y, 8, 9, (34, 42, 66))
                c.vline(col_x + 4, row_y, 9, (22, 26, 42))
                c.hline(col_x, row_y + 4, 8, (22, 26, 42))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "roof_brick.bmp"), 32, 64, c.px, transparent_key=False)

    # 2) Glass Corporate Tower
    c = Canvas(32, 64, (36, 52, 82))
    c.hline(0, 0, 32, (164, 238, 255))  # bright cyan-steel parapet
    c.hline(0, 1, 32, (108, 178, 212))
    c.hline(0, 2, 32, (62, 102, 142))
    c.hline(0, 3, 32, (24, 34, 56))
    for y in range(4, 64, 12):
        c.rect(0, y, 32, 3, (44, 54, 78))
        c.hline(0, y, 32, (74, 92, 124))
        # Glass ribbon
        for gx in range(2, 30, 7):
            c.rect(gx, y + 3, 5, 8, (48, 86, 126))
            c.vline(gx, y + 3, 8, (76, 134, 178))
            if ((y // 12) + gx) % 3 == 0:
                c.rect(gx + 1, y + 4, 3, 5, (144, 238, 255))
            # Diagonal specular glint
            c.set(gx + 1, y + 4, (200, 250, 255))
            c.set(gx + 2, y + 5, (160, 232, 250))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "roof_glass.bmp"), 32, 64, c.px, transparent_key=False)

    # 3) Industrial Steel Tower
    c = Canvas(32, 64, (50, 56, 72))
    c.hline(0, 0, 32, (230, 224, 198))  # crisp industrial roof rim
    c.hline(0, 1, 32, (168, 166, 154))
    c.hline(0, 2, 32, (98, 104, 118))
    c.hline(0, 3, 32, (32, 36, 48))
    # Hazard yellow-black accent band
    for x in range(32):
        col = (224, 176, 48) if ((x // 4) % 2 == 0) else (36, 38, 48)
        c.set(x, 5, col)
        c.set(x, 6, col)
    # Riveted panels & teal vents
    for y in range(10, 64, 14):
        c.hline(0, y, 32, (36, 40, 54))
        c.hline(0, y + 1, 32, (70, 78, 98))
        for vx in (4, 18):
            c.rect(vx, y + 3, 10, 8, (30, 36, 48))
            for sy in range(y + 4, y + 10, 2):
                c.hline(vx + 1, sy, 8, (88, 188, 196) if (y == 10 or y == 38) else (62, 74, 92))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "roof_steel.bmp"), 32, 64, c.px, transparent_key=False)


def generate_props():
    """Rooftop city props: AC unit, water tower, neon billboard, antenna, extraction beacon."""
    # 1) AC Unit (16x10) - also walkable elevated platform!
    c = Canvas(16, 10, None)
    c.rect(1, 1, 14, 9, (118, 130, 150))
    c.hline(1, 0, 14, (206, 220, 238))  # bright walkable top
    c.hline(0, 1, 16, (164, 178, 198))
    c.rect(12, 2, 3, 8, (76, 86, 104))
    c.rect(3, 3, 7, 5, (36, 42, 56))    # fan recess
    c.hline(4, 4, 5, (72, 84, 102))
    c.hline(4, 6, 5, (72, 84, 102))
    c.set(13, 3, (64, 240, 170))        # green power LED
    c.rect(2, 9, 2, 1, (48, 54, 68))    # feet
    c.rect(12, 9, 2, 1, (48, 54, 68))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "prop_ac.bmp"), 16, 10, c.px)

    # 2) Water Tower (20x28)
    c = Canvas(20, 28, None)
    # Steel legs
    for lx in (4, 9, 14):
        c.vline(lx, 18, 10, (78, 86, 108))
    c.hline(4, 22, 11, (64, 72, 94))
    c.hline(4, 25, 11, (64, 72, 94))
    # Wooden tank barrel
    c.rect(3, 7, 14, 11, (132, 86, 58))
    for bx in (5, 8, 11, 14):
        c.vline(bx, 7, 11, (98, 62, 42))
    c.rect(14, 7, 3, 11, (86, 54, 36))
    # Steel hoops
    c.hline(3, 9, 14, (64, 72, 90))
    c.hline(3, 14, 14, (64, 72, 90))
    c.hline(2, 17, 16, (108, 118, 138))
    # Conical roof
    for i in range(6):
        c.hline(2 + i, 6 - i, 16 - 2 * i, (96, 108, 132) if i < 5 else (170, 184, 208))
    c.vline(9, 0, 2, (190, 204, 226))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "prop_watertower.bmp"), 20, 28, c.px)

    # 3) Neon Sign (22x14)
    c = Canvas(22, 14, None)
    # Support poles
    c.vline(4, 10, 4, (74, 82, 102))
    c.vline(17, 10, 4, (74, 82, 102))
    # Sign frame
    c.rect(1, 1, 20, 10, (24, 20, 44))
    c.hline(1, 1, 20, (56, 232, 255))
    c.hline(1, 10, 20, (56, 232, 255))
    c.vline(1, 1, 10, (56, 232, 255))
    c.vline(20, 1, 10, (56, 232, 255))
    # Glowing cyberpunk wave / glyph bars inside
    pink = (255, 84, 184)
    gold = (255, 220, 76)
    c.rect(4, 3, 3, 5, pink)
    c.set(5, 4, (24, 20, 44))
    c.set(5, 6, (24, 20, 44))
    c.rect(9, 3, 2, 5, gold)
    c.hline(9, 5, 4, gold)
    c.rect(14, 3, 4, 2, pink)
    c.rect(14, 6, 4, 2, (84, 245, 255))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "prop_neon.bmp"), 22, 14, c.px)

    # 4) Antenna Spire (10x22)
    c = Canvas(10, 22, None)
    c.vline(5, 3, 19, (124, 138, 162))
    c.hline(2, 18, 7, (84, 96, 118))
    c.hline(3, 14, 5, (104, 116, 138))
    c.hline(1, 9, 9, (150, 164, 188))
    c.hline(3, 6, 5, (150, 164, 188))
    # Glowing amber aviation beacon tip
    c.rect(4, 1, 3, 3, (255, 190, 56))
    c.set(5, 2, (255, 248, 200))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "prop_antenna.bmp"), 10, 22, c.px)

    # 5) Extraction Beacon (18x26)
    c = Canvas(18, 26, None)
    # Holographic light beam rising up
    for y in range(0, 21):
        c.rect(6, y, 6, 1, (56, 224, 255) if (y % 2 == 0) else (120, 245, 255))
        c.rect(8, y, 2, 1, (235, 255, 255))
    # Base pad
    c.rect(1, 21, 16, 5, (64, 76, 102))
    c.hline(2, 21, 14, (255, 220, 76))
    c.hline(3, 22, 12, (88, 240, 255))
    c.rect(0, 24, 18, 2, (112, 126, 152))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "prop_beacon.bmp"), 18, 26, c.px)


def generate_player():
    """6-frame 16x16 cyberpunk rooftop runner spritesheet (96x16)."""
    c = Canvas(96, 16, None)
    cmap = {
        ".": None,
        "K": (18, 20, 32),      # crisp dark outline
        "H": (42, 54, 88),      # helmet / hood dark blue
        "h": (78, 98, 142),     # helmet highlight
        "V": (52, 248, 255),    # glowing cyan visor
        "v": (200, 255, 255),   # visor specular
        "S": (255, 192, 52),    # gold scarf
        "s": (210, 126, 36),    # scarf shadow
        "W": (228, 236, 248),   # crisp white/silver jacket
        "J": (132, 152, 186),   # jacket mid-tone
        "B": (46, 58, 92),      # tactical vest/pants
        "P": (32, 40, 66),      # dark pants shade
        "F": (244, 246, 255),   # sneaker bright
        "G": (82, 220, 240),    # glove/trim
    }

    frames = [
        # Frame 0: Idle ready stance
        [
            ".....KKKKKK.....",
            "....KhhHHHHK....",
            "....KHHVVvVK....",
            "....KHHVVVVK....",
            "...KssSSSSK.....",
            "..KsSKWWWWJK....",
            "..K.KWWBBWWK....",
            "....KWWBBWWK....",
            "....KJJBBJGK....",
            ".....KBBBBK.....",
            ".....KBPBPK.....",
            ".....KBK.KBK....",
            ".....KPK.KPK....",
            ".....KFK.KFK....",
            "....KFFK.KFFK...",
            "....KKKK.KKKK...",
        ],
        # Frame 1: Run stride A
        [
            ".....KKKKKK.....",
            "....KhhHHHHK....",
            "....KHHVVvVK....",
            "....KHHVVVVK....",
            "..KssSSSSSK.....",
            ".KsSKWWWWJK.....",
            ".K..KWWBBWWK....",
            "....KWWBBWWK....",
            ".....KJJBJGK....",
            ".....KBBBBK.....",
            "....KBP..PBK....",
            "...KPK....KBK...",
            "..KFK......KPK..",
            "..KFK......KFFK.",
            "..KKK.......KKK.",
            "................",
        ],
        # Frame 2: Run passing (slightly elevated)
        [
            ".....KKKKKK.....",
            "....KhhHHHHK....",
            "....KHHVVvVK....",
            "....KHHVVVVK....",
            "...KssSSSSK.....",
            "..KsSKWWWWJK....",
            "....KWWBBWWK....",
            "....KWWBBWWK....",
            ".....KJJBGK.....",
            ".....KBBBBK.....",
            ".....KBBPPK.....",
            ".....KPKBK......",
            ".....KFKFK......",
            ".....KFFKK......",
            ".....KKKK.......",
            "................",
        ],
        # Frame 3: Run stride B
        [
            ".....KKKKKK.....",
            "....KhhHHHHK....",
            "....KHHVVvVK....",
            "....KHHVVVVK....",
            "..KsssSSSSK.....",
            ".KssKWWWWJK.....",
            "....KWWBBWWK....",
            "....KWWBBWWK....",
            ".....KJJBJGK....",
            ".....KBBBBK.....",
            "....KPB..BPK....",
            "...KBK....KPK...",
            "...KPK....KFK...",
            "..KFFK....KFK...",
            "..KKK.....KKK...",
            "................",
        ],
        # Frame 4: Jump upward (tucked athletic leap)
        [
            ".....KKKKKK.....",
            "....KhhHHHHK....",
            "....KHHVVvVK....",
            "....KHHVVVVK....",
            "...KssSSSSK.....",
            "..KsSKWWWWJK....",
            "..K.KWWBBWWK....",
            ".K..KWWBBWGK....",
            "....KJJBBBK.....",
            "....KBBBBBPK....",
            "...KPK..KBBK....",
            "...KFK..KFFK....",
            "...KKK..KKKK....",
            "................",
            "................",
            "................",
        ],
        # Frame 5: Fall downward (scarf trailing up, feet ready)
        [
            "..KK.KKKKKK.....",
            ".KsSKhhHHHHK....",
            "..KsKHHVVvVK....",
            "...KKHHVVVVK....",
            "....KSSSSSK.....",
            "....KWWWWJK.....",
            "....KWWBBWWK....",
            "....KWWBBWWK....",
            "....KJJBBJGK....",
            ".....KBBBBK.....",
            "....KBK..KBK....",
            "....KPK..KPK....",
            "....KFK..KFK....",
            "...KFFK..KFFK...",
            "...KKKK..KKKK...",
            "................",
        ],
    ]

    for i, frows in enumerate(frames):
        c.stamp_ascii(i * 16, 0, frows, cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "player.bmp"), 96, 16, c.px)


def generate_guns():
    """5 unmistakably distinct 16x8 pixel-art weapons (facing right)."""
    # 1) PULSE PISTOL — sleek silver/white slide + cyan energy strip + compact profile
    c = Canvas(16, 8, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "W": (236, 242, 252),   # chrome top slide
        "S": (152, 166, 188),   # silver frame
        "D": (64, 74, 96),      # grip
        "C": (48, 242, 255),    # bright cyan pulse core
    }
    c.stamp_ascii(0, 0, [
        "................",
        "...KKKKKKKKK....",
        "..KWWWWWWWWWK...",
        "..KSCCCCSSSK....",
        "..KDDKKKKKK.....",
        "..KDDK..........",
        "..KKKK..........",
        "................",
    ], cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "gun_pistol.bmp"), 16, 8, c.px)

    # 2) NEON SMG — bright steel/gunmetal body, neon LIME-GREEN top capacitor & distinct long vertical mag!
    c = Canvas(16, 8, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "D": (88, 100, 124),    # readable slate-gunmetal
        "M": (156, 172, 198),   # bright metallic edge
        "G": (72, 255, 112),    # neon lime-green coil
        "g": (36, 196, 84),     # green shade
    }
    c.stamp_ascii(0, 0, [
        "..KKKKKKKKKK....",
        ".KMGGGGGGMMKKK..",
        ".KMDggggMMMMDDK.",
        ".KDDDDDDDDDKKK..",
        ".KDDKKKDDK......",
        ".KDDK..KMK......",
        ".KKK...KDK......",
        ".......KKK......",
    ], cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "gun_smg.bmp"), 16, 8, c.px)

    # 3) FLAK SHOTGUN — chunky heavy scattergun with warm wood/amber stock & dual thick barrels!
    c = Canvas(16, 8, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "S": (146, 158, 178),   # steel top barrel
        "D": (74, 82, 102),     # dark steel
        "W": (224, 134, 54),    # warm wood/amber stock & pump
        "w": (162, 86, 32),     # wood shadow
        "O": (255, 206, 72),    # hot amber barrel vent
    }
    c.stamp_ascii(0, 0, [
        "................",
        "....KKKKKKKKKKK.",
        ".KKKSSSSOSOSSSK.",
        "KWWKDDDDDDDDDDK.",
        "KwwWKKWWWWWWKK..",
        "KwwwKKwwwwwwK...",
        ".KKKK.KKKKKK....",
        "................",
    ], cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "gun_shotgun.bmp"), 16, 8, c.px)

    # 4) PLASMA RIFLE — bulky futuristic cobalt rifle with glowing MAGENTA-VIOLET energy orb & split prongs!
    c = Canvas(16, 8, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "B": (66, 98, 178),     # cobalt armor
        "b": (42, 62, 122),     # dark cobalt
        "P": (212, 72, 255),    # plasma purple-magenta
        "p": (255, 196, 255),   # plasma core bright white-pink
        "C": (96, 224, 255),    # emitter prongs
    }
    c.stamp_ascii(0, 0, [
        "..KKKKKKKKKKKK..",
        ".KBBBBBPPBBBBKK.",
        "KBBbPPppPPbbCCCK",
        "KbbbPPppPPbbKKK.",
        "KbbBBBBPPBBBCCCK",
        ".KKKbbKKKKKKK...",
        "...KbbK.........",
        "...KKKK.........",
    ], cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "gun_plasma.bmp"), 16, 8, c.px)

    # 5) ION RAILGUN — full 16px long sleek white/silver twin-rail sniper cannon with glowing ice-blue rings & scope!
    c = Canvas(16, 8, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "W": (236, 244, 255),   # crisp white composite
        "S": (140, 156, 182),   # steel rail
        "B": (40, 178, 255),    # glowing cobalt-blue coil
        "I": (180, 248, 255),   # bright ice-blue core
        "D": (54, 66, 92),      # grip
    }
    c.stamp_ascii(0, 0, [
        "...KKKKKK.......",
        "..KBBWWBBKKKKKKK",
        "KKWWWWWIBWIBWIBK",
        "KWWWWWWIIIIIIIIK",
        "KSSSSSSIBWIBWIBK",
        ".KKKDDKKKKKKKKKK",
        "...KDDK.........",
        "...KKKK.........",
    ], cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "gun_railgun.bmp"), 16, 8, c.px)


def generate_enemies():
    """5 distinct robotic enemies (100% mechanical, zero blood!)."""
    # 1) SCOUT BOT (2 frames of 14x14 = 28x14) — wheeled patrol robot with amber visor
    c = Canvas(28, 14, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "T": (84, 148, 142),    # teal-olive armor
        "t": (50, 96, 96),      # armor shadow
        "H": (152, 214, 206),   # top highlight
        "A": (255, 198, 52),    # amber visor glow
        "a": (255, 245, 180),   # visor center
        "G": (96, 106, 126),    # metal treads/arm
        "D": (42, 48, 64),      # tread dark
    }
    f0 = [
        ".....KKKK.....",
        "....KHHHHK....",
        "...KTTTTTTK...",
        "..KTTAAaaTTK..",
        "..KTTAAAATTK..",
        "..KttttttttK..",
        ".KKTTGGGGTTK..",
        ".KGGtTTTTttK..",
        "..KKttttttK...",
        "...KGGGGGGK...",
        "..KGDGDGDGDK..",
        "..KDGDGDGDGK..",
        "...KKKKKKKK...",
        "..............",
    ]
    f1 = [
        ".....KKKK.....",
        "....KHHHHK....",
        "...KTTTTTTK...",
        "..KTTaaAATTK..",
        "..KTTAAAATTK..",
        "..KttttttttK..",
        ".KKTTGGGGTTK..",
        ".KGGtTTTTttK..",
        "..KKttttttK...",
        "...KGGGGGGK...",
        "..KDGDGDGDGK..",
        "..KGDGDGDGDK..",
        "...KKKKKKKK...",
        "..............",
    ]
    c.stamp_ascii(0, 0, f0, cmap)
    c.stamp_ascii(14, 0, f1, cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "enemy_scout.bmp"), 28, 14, c.px)

    # 2) HOVER DRONE (2 frames of 14x12 = 28x12) — floating sky-drone with spinning rotor & cyan optic
    c = Canvas(28, 12, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "R": (196, 214, 236),   # spinning rotor
        "B": (74, 114, 174),    # slate-blue hull
        "b": (44, 68, 116),     # hull shade
        "L": (132, 182, 236),   # hull sheen
        "C": (48, 245, 255),    # optic eye
        "W": (240, 255, 255),   # optic glint
        "F": (255, 198, 56),    # hover thruster flame
    }
    d0 = [
        ".RRRRRRRRRRRR.",
        "......KK......",
        "...KKLLLLKK...",
        "..KLLBBBBBBK..",
        ".KLBBCWCCBBbK.",
        ".KBBBCWCCBBbK.",
        ".KBBBBBBBBbbK.",
        "..KbbbbbbbbK..",
        "...KKKKKKKK...",
        ".....KFFK.....",
        "......FF......",
        "..............",
    ]
    d1 = [
        "....RRRRRR....",
        "......KK......",
        "...KKLLLLKK...",
        "..KLLBBBBBBK..",
        ".KLBBCCWCBBbK.",
        ".KBBBCCWCBBbK.",
        ".KBBBBBBBBbbK.",
        "..KbbbbbbbbK..",
        "...KKKKKKKK...",
        "......FF......",
        ".....FFFF.....",
        "......FF......",
    ]
    c.stamp_ascii(0, 0, d0, cmap)
    c.stamp_ascii(14, 0, d1, cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "enemy_drone.bmp"), 28, 12, c.px)

    # 3) HEAVY TURRET (2 frames of 16x14 = 32x14) — armored purple/steel gun turret (frame 1 = charge glow!)
    c = Canvas(32, 14, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "P": (118, 78, 168),    # purple armor
        "p": (72, 46, 112),     # armor shade
        "L": (176, 142, 224),   # armor highlight
        "S": (136, 150, 174),   # cannon steel
        "D": (62, 70, 90),      # dark steel base
        "C": (52, 240, 255),    # idle cyan sensor
        "O": (255, 210, 62),    # charging gold telegraph
        "W": (255, 255, 220),   # charge core
    }
    t0 = [
        ".....KKKKKKK....",
        "....KLLLLLLLK...",
        "...KPPPPPPPPPK..",
        "KKKSPPCcPPPPpK..",
        "KSSSPPccPPPPpK..",
        "KKKSPPPPPPPppK..",
        "...KpppppppppK..",
        "....KKDDDDDKK...",
        "...KDDDDDDDDDK..",
        "..KDDKDDDDDKDDK.",
        "..KDK.KDDDK.KDK.",
        ".KDDK.KDDDK.KDDK",
        ".KKKK.KKKKK.KKKK",
        "................",
    ]
    t1 = [
        ".....KKKKKKK....",
        "....KLLLLLLLK...",
        "...KPPPPPPPPPK..",
        "KWWOPPWwPPPPpK..",
        "KOOOPPWwPPPPpK..",
        "KWWOPPPPPPPppK..",
        "...KpppppppppK..",
        "....KKDDDDDKK...",
        "...KDDDDDDDDDK..",
        "..KDDKDDDDDKDDK.",
        "..KDK.KDDDK.KDK.",
        ".KDDK.KDDDK.KDDK",
        ".KKKK.KKKKK.KKKK",
        "................",
    ]
    c.stamp_ascii(0, 0, t0, cmap)
    c.stamp_ascii(16, 0, t1, cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "enemy_turret.bmp"), 32, 14, c.px)

    # 4) HOPPER BOT (2 frames of 14x14 = 28x14) — spring-legged amber/graphite jumper bot
    c = Canvas(28, 14, None)
    cmap = {
        ".": None,
        "K": (16, 18, 28),
        "O": (244, 138, 42),    # bright industrial orange
        "o": (176, 86, 26),     # orange shade
        "Y": (255, 212, 92),    # highlight
        "G": (64, 72, 94),      # graphite frame
        "S": (184, 198, 220),   # steel spring
        "C": (56, 245, 255),    # visor / jump spark
    }
    h0 = [
        "..............",
        "..............",
        "...KKKKKKKK...",
        "..KYYYYYYYYK..",
        ".KYOOOOOOOOoK.",
        ".KOCCOOOOCCoK.",
        ".KOOOOOOOOooK.",
        "..KooooooooK..",
        "...KGGGGGGK...",
        "..KSSKKKKSSK..",
        "..K.KSSSSK.K..",
        ".KGGK....KGGK.",
        ".KKKK....KKKK.",
        "..............",
    ]
    h1 = [
        "...KKKKKKKK...",
        "..KYYYYYYYYK..",
        ".KYOOOOOOOOoK.",
        ".KOCCOOOOCCoK.",
        ".KOOOOOOOOooK.",
        "..KooooooooK..",
        "...KGGGGGGK...",
        "....KS..SK....",
        "...KS....SK...",
        "...K.S..S.K...",
        "..KGK.CC.KGK..",
        "..KKK.CC.KKK..",
        "..............",
        "..............",
    ]
    c.stamp_ascii(0, 0, h0, cmap)
    c.stamp_ascii(14, 0, h1, cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "enemy_hopper.bmp"), 28, 14, c.px)

    # 5) SKY SENTINEL BOSS (2 frames of 28x24 = 56x24) — armored hover-mech boss
    c = Canvas(56, 24, None)
    for fi in range(2):
        ox = fi * 28
        # Armor hull
        c.rect(ox + 5, 2, 18, 15, (64, 56, 108))
        c.rect(ox + 6, 3, 16, 13, (96, 82, 154))
        c.hline(ox + 6, 2, 16, (176, 164, 226))
        c.rect(ox + 4, 5, 20, 9, (74, 84, 118))
        c.rect(ox + 6, 6, 16, 7, (112, 126, 166))
        # Dark outline border
        c.hline(ox + 5, 1, 18, (18, 20, 32))
        c.hline(ox + 5, 17, 18, (18, 20, 32))
        c.vline(ox + 3, 5, 10, (18, 20, 32))
        c.vline(ox + 24, 5, 10, (18, 20, 32))
        # Dual shoulder cannons
        c.rect(ox + 0, 7, 5, 4, (150, 166, 192))
        c.rect(ox + 0, 8, 2, 2, (255, 210, 62) if fi == 1 else (52, 240, 255))
        c.rect(ox + 23, 7, 5, 4, (150, 166, 192))
        c.rect(ox + 26, 8, 2, 2, (255, 210, 62) if fi == 1 else (52, 240, 255))
        # Glowing central reactor core
        core_outer = (255, 196, 56) if fi == 1 else (52, 232, 255)
        core_inner = (255, 252, 220)
        c.rect(ox + 10, 7, 8, 5, (24, 28, 48))
        c.rect(ox + 11, 8, 6, 3, core_outer)
        c.rect(ox + 13, 8, 2, 3, core_inner)
        # Wing fins
        c.rect(ox + 2, 3, 3, 3, (124, 92, 186))
        c.rect(ox + 23, 3, 3, 3, (124, 92, 186))
        # Bottom hover thrusters (animated pulse)
        fl_h = 5 if fi == 0 else 3
        for tx in (7, 17):
            c.rect(ox + tx, 17, 4, 2, (54, 62, 86))
            c.rect(ox + tx + 1, 19, 2, fl_h, (60, 235, 255))
            c.set(ox + tx + 1, 19, (240, 255, 255))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "enemy_boss.bmp"), 56, 24, c.px)


def generate_pickups():
    # 1) Shield Med-Cell (10x10) — emerald/white energy shield repair cell
    c = Canvas(10, 10, None)
    cmap = {
        ".": None,
        "K": (16, 24, 30),
        "G": (48, 232, 146),
        "g": (28, 154, 98),
        "W": (244, 255, 250),
    }
    c.stamp_ascii(0, 0, [
        "..KKKKKK..",
        ".KGGGGGGK.",
        "KGGWGGWGGK",
        "KGWWGGWWGK",
        "KGGWWWWGGK",
        "KGGWWWWGGK",
        "KGgWGGWgGK",
        "KggWGGWggK",
        ".KggggggK.",
        "..KKKKKK..",
    ], cmap)
    # Clean bright '+' inside
    c.rect(4, 2, 2, 6, (244, 255, 250))
    c.rect(2, 4, 6, 2, (244, 255, 250))
    write_bmp_8bit(os.path.join(ASSETS_DIR, "pickup_med.bmp"), 10, 10, c.px)

    # 2) Cyber Energy Core (10x10) — radiant gold diamond core (+score & overcharge!)
    c = Canvas(10, 10, None)
    cmap = {
        ".": None,
        "K": (28, 22, 14),
        "Y": (255, 214, 56),
        "O": (230, 144, 34),
        "W": (255, 252, 216),
    }
    c.stamp_ascii(0, 0, [
        "....KK....",
        "...KYYK...",
        "..KYWWYK..",
        ".KYWWWWYK.",
        "KYWWYYWWYK",
        "KOYYOOYYOK",
        ".KOYOOYOK.",
        "..KOOOOK..",
        "...KOOK...",
        "....KK....",
    ], cmap)
    write_bmp_8bit(os.path.join(ASSETS_DIR, "pickup_star.bmp"), 10, 10, c.px)


def generate_launcher_icon():
    """32x32 16-bit RGB565 Thumby Color Launcher icon."""
    c = Canvas(32, 32, (20, 22, 54))
    for y in range(32):
        col = lerp_color((16, 18, 48), (112, 54, 96), y / 31.0)
        c.hline(0, y, 32, col)
    # Moon
    c.circle(25, 7, 3.2, (255, 242, 190))
    # Distant silhouette
    c.rect(12, 12, 8, 20, (32, 30, 62))
    c.rect(21, 15, 11, 17, (26, 26, 54))
    # Foreground rooftop left + gap + right
    c.rect(0, 21, 16, 11, (56, 42, 54))
    c.hline(0, 21, 16, (190, 218, 240))
    c.rect(22, 23, 10, 9, (40, 56, 86))
    c.hline(22, 23, 10, (144, 232, 255))
    # Lit building windows
    for wx, wy in [(3, 24), (9, 24), (3, 28), (25, 26)]:
        c.rect(wx, wy, 3, 2, (255, 216, 100))
    # Hero silhouette + cyan visor + blaster + bright energy beam!
    c.rect(5, 13, 5, 8, (22, 26, 44))
    c.rect(6, 14, 4, 2, (56, 248, 255))   # visor
    c.rect(5, 16, 4, 2, (255, 194, 56))   # scarf
    c.rect(10, 16, 5, 2, (224, 236, 250)) # gun
    c.rect(16, 16, 4, 2, (56, 248, 255))  # laser bolt 1
    c.rect(22, 16, 5, 2, (255, 232, 110)) # laser bolt 2
    write_bmp_16bit_565(os.path.join(GAME_DIR, "icon.bmp"), 32, 32, c.px)


def write_wav_8bit(path, samples_float, sample_rate=11025):
    data = bytes([max(0, min(255, int(128 + s * 112))) for s in samples_float])
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(data)))
        f.write(b"WAVEfmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate, 1, 8))
        f.write(b"data")
        f.write(struct.pack("<I", len(data)))
        f.write(data)


def generate_sfx():
    sr = 11025
    rng = random.Random(777)

    def synth_sweep(dur, f0, f1, wave="square", amp=0.75, noise_mix=0.0):
        n = int(sr * dur)
        out = []
        phase = 0.0
        for i in range(n):
            t = i / max(1, n - 1)
            freq = f0 * ((f1 / max(1.0, f0)) ** t)
            phase += 2.0 * math.pi * freq / sr
            if wave == "square":
                s = 1.0 if math.sin(phase) >= 0 else -1.0
            elif wave == "saw":
                s = 2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0
            else:
                s = math.sin(phase)
            if noise_mix > 0.0:
                s = s * (1.0 - noise_mix) + rng.uniform(-1.0, 1.0) * noise_mix
            env = (1.0 - t) ** 1.2
            out.append(s * env * amp)
        return out

    # Distinct SFX per weapon + gameplay actions
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_pistol.wav"), synth_sweep(0.08, 1250, 340, "square", 0.65))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_smg.wav"), synth_sweep(0.05, 1650, 720, "square", 0.55))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_shotgun.wav"), synth_sweep(0.14, 340, 75, "saw", 0.85, noise_mix=0.55))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_plasma.wav"), synth_sweep(0.13, 620, 210, "sine", 0.80, noise_mix=0.12))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_railgun.wav"), synth_sweep(0.16, 2200, 180, "saw", 0.85, noise_mix=0.25))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_jump.wav"), synth_sweep(0.10, 260, 740, "square", 0.55))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_hit.wav"), synth_sweep(0.055, 900, 1400, "square", 0.50))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_boom.wav"), synth_sweep(0.20, 220, 52, "saw", 0.80, noise_mix=0.65))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_swap.wav"), synth_sweep(0.06, 540, 980, "square", 0.45))
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_hurt.wav"), synth_sweep(0.16, 300, 110, "saw", 0.75, noise_mix=0.2))

    # Ascending 2-tone pickup chime
    p1 = synth_sweep(0.055, 660, 660, "square", 0.55)
    p2 = synth_sweep(0.09, 990, 1320, "square", 0.55)
    write_wav_8bit(os.path.join(ASSETS_DIR, "sfx_pickup.wav"), p1 + p2)


def main():
    # Sector 1: Dusk City Skyline (deep indigo -> twilight violet -> warm dusk horizon)
    generate_sky(
        "sky_dusk.bmp",
        [(0.0, (14, 16, 44)), (0.45, (42, 26, 74)), (0.80, (108, 52, 92)), (1.0, (158, 92, 86))],
        moon_pos=(104, 28),
        moon_color=(255, 244, 200),
        halo_color=(210, 160, 210),
        seed=11,
    )
    # Sector 2: Neon Downtown (midnight navy -> cyber teal-indigo -> electric horizon)
    generate_sky(
        "sky_neon.bmp",
        [(0.0, (8, 16, 36)), (0.50, (18, 32, 76)), (0.82, (28, 72, 114)), (1.0, (56, 128, 152))],
        moon_pos=(26, 30),
        moon_color=(216, 248, 255),
        halo_color=(84, 200, 240),
        seed=22,
    )
    # Sector 3: Apex Spire Dawn (deep storm navy -> crimson-violet -> warm amber sunrise)
    generate_sky(
        "sky_spire.bmp",
        [(0.0, (12, 14, 34)), (0.45, (38, 32, 72)), (0.78, (112, 58, 78)), (1.0, (186, 124, 68))],
        moon_pos=(100, 26),
        moon_color=(255, 232, 184),
        halo_color=(255, 164, 110),
        seed=33,
    )

    generate_parallax_far()
    generate_parallax_mid()
    generate_rooftop_tiles()
    generate_props()
    generate_player()
    generate_guns()
    generate_enemies()
    generate_pickups()
    generate_launcher_icon()
    generate_sfx()

    total_bytes = 0
    count = 0
    for root, _, files in os.walk(ASSETS_DIR):
        for fn in sorted(files):
            sz = os.path.getsize(os.path.join(root, fn))
            total_bytes += sz
            count += 1
    icon_sz = os.path.getsize(os.path.join(GAME_DIR, "icon.bmp"))
    print(f"Generated {count} assets in game/assets/ ({total_bytes / 1024:.1f} KB) + icon.bmp ({icon_sz} bytes)")


if __name__ == "__main__":
    main()
