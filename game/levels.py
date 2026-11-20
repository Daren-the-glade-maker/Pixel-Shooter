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
]
