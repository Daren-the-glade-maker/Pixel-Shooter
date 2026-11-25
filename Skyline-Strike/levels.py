# Handcrafted multi-sector city rooftop levels for Skyline Strike.
# Coordinate system: +X is right, +Y is down (Thumby Color engine_nodes convention).
# Each building: (x_left, width_mult32, roof_y, style_index)
#   style_index: 0 = brick brownstone, 1 = glass tower, 2 = industrial steel
# Each prop: (x_center, roof_y, kind)
#   kind: "ac" (walkable elevated platform), "watertower", "neon", "antenna"
# Each enemy: (kind, x, y, min_x, max_x)
#   kind: "scout", "drone", "turret", "hopper", "boss"
# Each pickup: (kind, x, y)
#   kind: "med" (+1 shield HP), "star" (+250 score & rapid overcharge)

SECTORS = [
    {
        "tag": "S1",
        "name": "DUSK SKYLINE",
        "sky": "assets/sky_dusk.bmp",
        "spawn": (0.0, 16.0),
        "buildings": [
            (-32, 128, 32, 0),   # Start roof: x=-32..96
            (126, 96, 24, 1),    # Gap 30px, step up 8px: x=126..222
            (254, 96, 36, 2),    # Gap 32px, drop 12px: x=254..350
            (382, 96, 26, 0),    # Gap 32px, step up 10px: x=382..478
            (512, 128, 30, 1),   # Gap 34px, Extraction Roof: x=512..640
        ],
        "props": [
            (-10, 32, "watertower"),
            (28, 32, "neon"),
            (154, 24, "ac"),
            (204, 24, "antenna"),
            (278, 36, "ac"),
            (334, 36, "neon"),
            (404, 26, "watertower"),
            (456, 26, "ac"),
            (542, 30, "antenna"),
        ],
        "enemies": [
            ("scout", 60, 25, 22, 86),
            ("drone", 172, -4, 134, 212),
            ("scout", 192, 17, 166, 214),
            ("turret", 322, 29, 322, 322),
            ("hopper", 434, 19, 392, 468),
            ("drone", 548, -2, 518, 600),
            ("scout", 584, 23, 534, 608),
        ],
        "pickups": [
            ("star", 154, 6),
            ("med", 278, 18),
            ("star", 456, 8),
        ],
        "beacon": (622, 30),
        "has_boss": False,
    },
    {
        "tag": "S2",
        "name": "NEON DOWNTOWN",
        "sky": "assets/sky_neon.bmp",
        "spawn": (0.0, 16.0),
        "buildings": [
            (-32, 96, 32, 1),    # x=-32..64
            (96, 96, 22, 2),     # Gap 32px, up 10px: x=96..192
            (226, 64, 16, 1),    # Gap 34px, up 6px: x=226..290
            (324, 128, 34, 0),   # Gap 34px, big rooftop drop: x=324..452
            (488, 96, 24, 2),    # Gap 36px, up 10px: x=488..584
            (618, 128, 28, 1),   # Gap 34px, Extraction Roof: x=618..746
        ],
        "props": [
            (-8, 32, "neon"),
            (126, 22, "ac"),
            (178, 22, "antenna"),
            (258, 16, "neon"),
            (356, 34, "watertower"),
            (418, 34, "ac"),
            (516, 24, "ac"),
            (566, 24, "neon"),
            (646, 28, "antenna"),
        ],
        "enemies": [
            ("scout", 44, 25, 16, 56),
            ("drone", 142, -6, 102, 184),
            ("turret", 174, 15, 174, 174),
            ("hopper", 258, 9, 234, 282),
            ("scout", 376, 27, 336, 410),
            ("turret", 436, 27, 436, 436),
            ("drone", 536, -6, 496, 578),
            ("hopper", 554, 17, 502, 576),
            ("scout", 678, 21, 636, 706),
            ("turret", 706, 21, 706, 706),
        ],
        "pickups": [
            ("star", 126, 4),
            ("med", 356, 20),
            ("star", 516, 6),
            ("med", 648, 16),
        ],
        "beacon": (728, 28),
        "has_boss": False,
    },
    {
        "tag": "S3",
        "name": "APEX SPIRE",
        "sky": "assets/sky_spire.bmp",
        "spawn": (0.0, 16.0),
        "buildings": [
            (-32, 96, 32, 2),    # x=-32..64
            (98, 96, 22, 0),     # Gap 34px: x=98..194
            (230, 96, 14, 1),    # Gap 36px: x=230..326
            (360, 96, 26, 2),    # Gap 34px: x=360..456
            (492, 160, 32, 1),   # Gap 36px, Boss Spire Helipad: x=492..652
        ],
        "props": [
            (-8, 32, "antenna"),
            (130, 22, "ac"),
            (176, 22, "neon"),
            (262, 14, "watertower"),
            (306, 14, "ac"),
            (390, 26, "neon"),
            (434, 26, "ac"),
            (516, 32, "ac"),
            (628, 32, "ac"),
        ],
        "enemies": [
            ("hopper", 42, 25, 16, 56),
            ("turret", 172, 15, 172, 172),
            ("drone", 142, -8, 106, 186),
            ("scout", 276, 7, 240, 314),
            ("drone", 308, -14, 248, 322),
            ("hopper", 404, 19, 370, 446),
            ("turret", 442, 19, 442, 442),
            ("boss", 604, -4, 514, 634),
        ],
        "pickups": [
            ("star", 130, 4),
            ("med", 306, -4),
            ("med", 434, 8),
            ("star", 572, 18),
        ],
        "beacon": (634, 32),
        "has_boss": True,
    },
    {
        "tag": "S4",
        "name": "ORBITAL RELAY",
        "sky": "assets/sky_spire.bmp",
        "spawn": (4, 24),
        "buildings": [
            (-32, 112, 34, 2),
            (110, 96, 26, 1),
            (236, 112, 32, 2),
            (378, 96, 24, 1),
            (504, 160, 30, 2),
        ],
        "props": [
            (22, 34, "ac"),
            (60, 34, "antenna"),
            (154, 26, "ac"),
            (272, 32, "neon"),
            (318, 32, "ac"),
            (418, 24, "watertower"),
            (548, 30, "ac"),
        ],
        "enemies": [
            ("scout", 142, 13, 118, 192),
            ("drone", 196, -12, 130, 224),
            ("turret", 296, 21, 296, 296),
            ("hopper", 410, 11, 386, 456),
            ("drone", 448, -14, 390, 470),
            ("boss", 610, -4, 518, 646),
        ],
        "pickups": [
            ("med", 154, 6),
            ("star", 318, 12),
            ("med", 418, 4),
            ("star", 548, 10),
        ],
        "beacon": (644, 30),
        "has_boss": True,
    },
    {
        "tag": "S5",
        "name": "CANOPY EDGE",
        "sky": "assets/sky_forest.bmp",
        "spawn": (4, 24),
        "buildings": [
            (-32, 112, 34, 3),
            (108, 104, 26, 3),
            (238, 116, 30, 3),
            (380, 100, 22, 3),
            (504, 144, 28, 3),
        ],
        "props": [
            (32, 34, "ac"),
            (152, 26, "watertower"),
            (284, 30, "ac"),
            (422, 22, "antenna"),
        ],
        "enemies": [
            ("scout", 140, 13, 116, 194),
            ("drone", 204, -10, 136, 232),
            ("hopper", 280, 17, 246, 334),
            ("turret", 418, 17, 418, 418),
            ("scout", 548, 15, 514, 610),
        ],
        "pickups": [
            ("med", 152, 6),
            ("star", 284, 10),
            ("med", 548, 10),
        ],
        "beacon": (628, 28),
        "has_boss": False,
    },
    {
        "tag": "S6",
        "name": "ELDER GROVE",
        "sky": "assets/sky_forest.bmp",
        "spawn": (4, 24),
        "buildings": [
            (-32, 112, 34, 3),
            (106, 96, 24, 3),
            (228, 116, 32, 3),
            (372, 104, 22, 3),
            (500, 160, 30, 3),
        ],
        "props": [
            (40, 34, "ac"),
            (148, 24, "ac"),
            (276, 32, "watertower"),
            (414, 22, "ac"),
            (548, 30, "antenna"),
        ],
        "enemies": [
            ("hopper", 142, 11, 114, 186),
            ("drone", 202, -12, 130, 226),
            ("turret", 294, 27, 294, 294),
            ("scout", 408, 9, 380, 456),
            ("boss", 610, -4, 518, 646),
        ],
        "pickups": [
            ("star", 148, 4),
            ("med", 276, 12),
            ("star", 414, 2),
        ],
        "beacon": (644, 30),
        "has_boss": True,
    },
    {
        "tag": "S7",
        "name": "MAGMA FOUNDRY",
        "sky": "assets/sky_lava.bmp",
        "spawn": (4, 24),
        "buildings": [
            (-32, 112, 34, 4),
            (108, 100, 26, 4),
            (236, 116, 32, 4),
            (378, 100, 24, 4),
            (504, 148, 30, 4),
        ],
        "props": [(32, 34, "ac"), (152, 26, "antenna"), (284, 32, "ac"), (422, 24, "watertower")],
        "enemies": [
            ("scout", 140, 13, 116, 194),
            ("drone", 204, -10, 136, 232),
            ("hopper", 280, 19, 246, 334),
            ("turret", 418, 19, 418, 418),
            ("scout", 548, 17, 514, 610),
        ],
        "pickups": [("med", 152, 6), ("star", 284, 12), ("med", 548, 12)],
        "beacon": (632, 30),
        "has_boss": False,
    },
    {
        "tag": "S8",
        "name": "OBSIDIAN CORE",
        "sky": "assets/sky_lava.bmp",
        "spawn": (4, 24),
        "buildings": [
            (-32, 112, 34, 4),
            (106, 96, 24, 4),
            (228, 116, 32, 4),
            (372, 104, 22, 4),
            (500, 160, 30, 4),
        ],
        "props": [(40, 34, "ac"), (148, 24, "ac"), (276, 32, "antenna"), (414, 22, "ac")],
        "enemies": [
            ("hopper", 142, 11, 114, 186),
            ("drone", 202, -12, 130, 226),
            ("turret", 294, 27, 294, 294),
            ("boss", 610, -4, 518, 646),
        ],
        "pickups": [("star", 148, 4), ("med", 276, 12), ("star", 414, 2)],
        "beacon": (644, 30),
        "has_boss": True,
    },
    {
        "tag": "S9",
        "name": "FROST PEAKS",
        "sky": "assets/sky_ice.bmp",
        "spawn": (4, 24),
        "buildings": [
            (-32, 112, 34, 5),
            (108, 104, 26, 5),
            (238, 116, 30, 5),
            (380, 100, 22, 5),
            (504, 144, 28, 5),
        ],
        "props": [(32, 34, "ac"), (152, 26, "watertower"), (284, 30, "ac"), (422, 22, "antenna")],
        "enemies": [
            ("scout", 140, 13, 116, 194),
            ("drone", 204, -10, 136, 232),
            ("hopper", 280, 17, 246, 334),
            ("turret", 418, 17, 418, 418),
        ],
        "pickups": [("med", 152, 6), ("star", 284, 10), ("med", 548, 10)],
        "beacon": (628, 28),
        "has_boss": False,
    },
    {
        "tag": "S10",
        "name": "CRYO CITADEL",
        "sky": "assets/sky_ice.bmp",
        "spawn": (4, 24),
        "buildings": [
            (-32, 112, 34, 5),
            (106, 96, 24, 5),
            (228, 116, 32, 5),
            (372, 104, 22, 5),
            (500, 160, 30, 5),
        ],
        "props": [(40, 34, "ac"), (148, 24, "ac"), (276, 32, "watertower"), (414, 22, "ac")],
        "enemies": [
            ("hopper", 142, 11, 114, 186),
            ("drone", 202, -12, 130, 226),
            ("turret", 294, 27, 294, 294),
            ("boss", 610, -4, 518, 646),
        ],
        "pickups": [("star", 148, 4), ("med", 276, 12), ("star", 414, 2)],
        "beacon": (644, 30),
        "has_boss": True,
    },
]


ENDLESS_BOSSES = [
    ("IRON HAWK", 150),
    ("NEON VIPER", 165),
    ("APEX CORE", 180),
    ("STORM TITAN", 195),
    ("CYBER WYRM", 210),
    ("VOID REAPER", 220),
    ("SOLAR FLARE", 230),
    ("FROST BITE", 240),
    ("PLASMA KING", 255),
    ("OMEGA DRONE", 270),
]


def generate_endless_chunk(chunk_idx, seed):
    import random
    random.seed(seed)
    rng = random
    has_boss = (rng.random() < 0.45) or ((chunk_idx > 0) and ((chunk_idx % 3) == 2))
    boss_name, boss_hp = rng.choice(ENDLESS_BOSSES) if has_boss else ("", 0)
    theme = chunk_idx % 4
    if theme == 1:
        sky = "assets/sky_forest.bmp"
        style = 3
    elif theme == 2:
        sky = "assets/sky_lava.bmp"
        style = 4
    elif theme == 3:
        sky = "assets/sky_ice.bmp"
        style = 5
    else:
        sky = "assets/sky_neon.bmp" if chunk_idx % 8 == 0 else "assets/sky_spire.bmp"
        style = chunk_idx % 3

    buildings = [(-32, 112, 34, style)]
    props = [(28, 34, "ac")]
    enemies = []
    pickups = []

    x = 104
    for i in range(4):
        w = rng.choice([96, 128, 160, 192, 224, 256]) if i < 3 else rng.choice([156, 192, 224])
        y = rng.choice([24, 28, 32, 36])
        buildings.append((x, w, y, style))
        if rng.random() < 0.75:
            props.append((x + w // 2, y, rng.choice(["ac", "antenna", "watertower"])))
        if i < 3:
            n_enemies = 1 if w <= 128 else (2 if w <= 192 else 3)
            for e_i in range(n_enemies):
                if len(enemies) >= 8:
                    break
                kind = rng.choice(["scout", "drone", "hopper", "turret"])
                ex = x + 24 + int((w - 48) * (e_i + 0.5) / n_enemies)
                ey = y - 13 if kind != "drone" else y - 34
                enemies.append((kind, ex, ey, x + 10, x + w - 10))
            if rng.random() < 0.55:
                pickups.append((rng.choice(["med", "star"]), x + w // 2, y - 20))
        else:
            if has_boss:
                enemies.append(("boss", x + w - 42, y - 34, x + 14, x + w - 14))
            else:
                enemies.append(("scout", x + w // 2, y - 13, x + 12, x + w - 12))
        x += w + rng.choice([24, 28, 32])

    last_x, last_w, last_y, _ = buildings[-1]
    beacon_x = last_x + last_w - 18
    return {
        "tag": "C{}".format(chunk_idx + 1),
        "name": "ENDLESS #{}".format(chunk_idx + 1),
        "sky": sky,
        "spawn": (4, 24),
        "buildings": buildings,
        "props": props,
        "enemies": enemies,
        "pickups": pickups,
        "beacon": (beacon_x, last_y),
        "has_boss": has_boss,
    }
