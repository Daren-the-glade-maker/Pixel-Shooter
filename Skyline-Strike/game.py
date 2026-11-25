import math
import time

import engine
import engine_audio
import engine_draw
import engine_io
import engine_save
from engine_draw import Color
from engine_math import Vector2
from engine_nodes import CameraNode, Rectangle2DNode, Sprite2DNode, Text2DNode
from engine_resources import TextureResource, WaveSoundResource

from entities import (
    BulletPool,
    COL_HP_BG,
    COL_SPARK_CYAN,
    COL_SPARK_GOLD,
    COL_SPARK_WHITE,
    EnemyManager,
    FxPool,
    Player,
    TRANSPARENT_KEY,
    set_pos,
)
from levels import SECTORS, generate_endless_chunk
from link import LinkManager
from weapons import WEAPONS

STATE_TITLE = 0
STATE_PLAYING = 1
STATE_PAUSED = 2
STATE_SECTOR_CLEAR = 3
STATE_GAMEOVER = 4
STATE_VICTORY = 5
STATE_UPGRADE = 6
STATE_LINK_WAIT = 7

PROP_HALF_H = {
    "ac": 5.0,
    "watertower": 14.0,
    "neon": 7.0,
    "antenna": 11.0,
    "beacon": 13.0,
}

# Pre-allocated HUD & UI colors (zero per-frame allocations)
COL_HUD_BG = Color(0.06, 0.07, 0.14)
COL_HUD_LINE = Color(0.24, 0.78, 0.96)
COL_HUD_GUN_FILL = Color(0.10, 0.12, 0.22)
COL_HUD_SECTOR = Color(0.75, 0.85, 1.0)
COL_HUD_SCORE = Color(1.0, 0.92, 0.45)
COL_PIP_OK = Color(0.24, 0.96, 0.68)
COL_PIP_LOW = Color(1.0, 0.72, 0.22)
COL_PIP_OFF = Color(0.18, 0.20, 0.30)
COL_TOAST_BG = Color(0.06, 0.08, 0.16)
COL_BOSS_FG = Color(0.86, 0.36, 1.0)
COL_BOSS_LBL = Color(1.0, 0.86, 0.35)
COL_OV_CYAN = Color(0.28, 0.92, 1.0)
COL_OV_GREEN = Color(0.32, 1.0, 0.62)
COL_OV_WARN = Color(1.0, 0.62, 0.24)
COL_OV_CARD = Color(0.07, 0.08, 0.16)
COL_OV_TITLE = Color(0.32, 0.96, 1.0)
COL_OV_SUB = Color(1.0, 0.86, 0.32)
COL_OV_LINE1 = Color(0.92, 0.95, 1.0)
COL_OV_LINE2 = Color(0.74, 0.84, 0.96)


class SkylineGame:
    def __init__(self, headless_fast=False):
        self.headless_fast = headless_fast
        if headless_fast:
            engine.disable_fps_limit()
        else:
            engine.fps_limit(60)

        engine_draw.set_background_color(COL_HUD_BG)
        engine_audio.set_volume(0.85)

        # Save file for high score (gracefully falls back if saves dir isn't initialized)
        self.best_score = 0
        try:
            engine_save.set_location("skyline_strike.save")
            self.best_score = int(engine_save.load("best_score", 0))
        except Exception as e:
            print("WARN: engine_save load failed:", e)
            self.best_score = 0

        # Camera
        self.camera = CameraNode()
        self.cam_x = 24.0
        self.cam_y = -6.0
        self.shake_timer = 0.0
        self.shake_mag = 0.0

        # Load pixel-art TextureResources
        self.sky_textures = [TextureResource(s["sky"], False) for s in SECTORS]
        self.bg_far_tex = TextureResource("assets/bg_far.bmp", True)
        self.bg_mid_tex = TextureResource("assets/bg_mid.bmp", True)
        self.roof_textures = [
            TextureResource("assets/roof_brick.bmp", True),
            TextureResource("assets/roof_glass.bmp", True),
            TextureResource("assets/roof_steel.bmp", True),
            TextureResource("assets/roof_canopy.bmp", True),
        ]
        self.forest_sky_tex = TextureResource("assets/sky_forest.bmp", False)
        self.player_red_tex = TextureResource("assets/player_red.bmp", True)
        self.link = LinkManager()
        self.pick_mode = 0      # 0 = Adventure, 1 = Endless
        self.pick_players = 0   # 0 = 1P, 1 = 2P Link
        self.pick_cursor = 0    # 0 = mode picker, 1 = players picker
        self.is_endless = False
        self.is_2p = False
        self.endless_seed = 1337
        self.chunk_idx = 0
        self.coins = 0
        self.upgrade_cursor = 0
        self.endless_upgrades = {w["id"]: {"rate": 0, "dmg": 0, "size": 0} for w in WEAPONS}
        self.remote_sprite = Sprite2DNode(
            position=Vector2(-999, 999),
            texture=self.player_red_tex,
            transparent_color=TRANSPARENT_KEY,
            frame_count_x=6,
            playing=False,
            opacity=0.0,
            layer=9,
        )
        self.prop_textures = {
            "ac": TextureResource("assets/prop_ac.bmp", True),
            "watertower": TextureResource("assets/prop_watertower.bmp", True),
            "neon": TextureResource("assets/prop_neon.bmp", True),
            "antenna": TextureResource("assets/prop_antenna.bmp", True),
            "beacon": TextureResource("assets/prop_beacon.bmp", True),
        }
        self.player_tex = TextureResource("assets/player.bmp", True)
        self.gun_textures = [TextureResource(w["tex"], True) for w in WEAPONS]
        self.enemy_textures = {
            "scout": TextureResource("assets/enemy_scout.bmp", True),
            "drone": TextureResource("assets/enemy_drone.bmp", True),
            "turret": TextureResource("assets/enemy_turret.bmp", True),
            "hopper": TextureResource("assets/enemy_hopper.bmp", True),
            "boss": TextureResource("assets/enemy_boss.bmp", True),
        }
        self.pickup_textures = {
            "med": TextureResource("assets/pickup_med.bmp", True),
            "star": TextureResource("assets/pickup_star.bmp", True),
        }

        # Load synthesized retro .wav SFX
        self.sfx = {}
        sfx_map = {
            "pistol": "assets/sfx_pistol.wav",
            "smg": "assets/sfx_smg.wav",
            "shotgun": "assets/sfx_shotgun.wav",
            "plasma": "assets/sfx_plasma.wav",
            "railgun": "assets/sfx_railgun.wav",
            "jump": "assets/sfx_jump.wav",
            "hit": "assets/sfx_hit.wav",
            "boom": "assets/sfx_boom.wav",
            "swap": "assets/sfx_swap.wav",
            "pickup": "assets/sfx_pickup.wav",
            "hurt": "assets/sfx_hurt.wav",
        }
        for k, path in sfx_map.items():
            try:
                self.sfx[k] = WaveSoundResource(path)
            except Exception:
                pass

        self.title_bgm = None
        try:
            from engine_resources import RTTTLSoundResource
            self.title_bgm = RTTTLSoundResource(
                "Skyline:d=8,o=5,b=140:e,g,b,4e6,d6,b,4g,a,b,c6,4b,g,4e,p,e,g,b,4e6,f#6,e6,4d6,b,g,4a,4g"
            )
            engine_audio.play(self.title_bgm, 3, True)
        except Exception:
            self.title_bgm = None

        # Parallax city skyline layers (2 seamlessly tiled sprites per depth layer)
        self.far_nodes = [
            Sprite2DNode(position=Vector2(0, 14), texture=self.bg_far_tex, transparent_color=TRANSPARENT_KEY, layer=1),
            Sprite2DNode(position=Vector2(128, 14), texture=self.bg_far_tex, transparent_color=TRANSPARENT_KEY, layer=1),
        ]
        self.mid_nodes = [
            Sprite2DNode(position=Vector2(0, 26), texture=self.bg_mid_tex, transparent_color=TRANSPARENT_KEY, layer=2),
            Sprite2DNode(position=Vector2(128, 26), texture=self.bg_mid_tex, transparent_color=TRANSPARENT_KEY, layer=2),
        ]

        # Pooled visible foreground building facade tiles (32x64 each) & rooftop props
        self.facade_pool = [
            Sprite2DNode(position=Vector2(-999, 999), texture=self.roof_textures[0], opacity=0.0, layer=4)
            for _ in range(14)
        ]
        self.prop_pool = [
            Sprite2DNode(position=Vector2(-999, 999), texture=self.prop_textures["ac"], transparent_color=TRANSPARENT_KEY, opacity=0.0, layer=5)
            for _ in range(10)
        ]
        self.beacon_node = Sprite2DNode(
            position=Vector2(-999, 999),
            texture=self.prop_textures["beacon"],
            transparent_color=TRANSPARENT_KEY,
            opacity=0.0,
            layer=6,
        )

        # Pooled pickups
        self.pickup_nodes = [
            Sprite2DNode(
                position=Vector2(-999, 999),
                texture=self.pickup_textures["star"],
                transparent_color=TRANSPARENT_KEY,
                opacity=0.0,
                layer=8,
            )
            for _ in range(6)
        ]
        self.pickups = []

        # Core gameplay pools & entities
        self.fx = FxPool(18)
        self.bullets = BulletPool(18)
        self.enemies = EnemyManager(self.enemy_textures, pool_size=10)
        self.player = Player(self.player_tex, self.gun_textures, WEAPONS)

        # Cached HUD tracking so text/colors only update on change
        self._hud_last_hp = -1
        self._hud_last_weapon = -1
        self._hud_last_sector = -1
        self._hud_last_score = -1

        # Build camera-pinned HUD & overlay UI
        self._build_hud()
        self._build_overlays()

        # Game state
        self.state = STATE_TITLE
        self.sector_idx = 0
        self.score = 0
        self.kills = 0
        self.time_acc = 0.0
        self.state_timer = 0.0
        self.toast_timer = 0.0
        self.buildings = []
        self.props = []
        self.ac_platforms = []
        self.beacon_pos = (600.0, 30.0)
        self.level_max_x = 640.0
        self.running = True
        self.frame_count = 0

        # Load Sector 0 backdrop behind the live animated title screen
        self._load_sector(0, reset_hp=True)
        self.player.sync_visuals(visible=True)
        self._enter_title()

    def play_sfx(self, key, channel=0):
        snd = self.sfx.get(key)
        if snd is not None:
            try:
                engine_audio.play(snd, channel, False)
            except Exception:
                pass

    def _add_hud_child(self, node):
        self.camera.add_child(node)
        return node

    def _build_hud(self):
        self.hud_bg = self._add_hud_child(
            Rectangle2DNode(position=Vector2(0, -57), width=128, height=14, color=COL_HUD_BG, layer=25)
        )
        self.hud_line = self._add_hud_child(
            Rectangle2DNode(position=Vector2(0, -50), width=128, height=1, color=COL_HUD_LINE, layer=26)
        )

        # 5 Shield HP pips on the left (clean spacing before S1/S2/S3)
        self.hp_pips = []
        for i in range(5):
            pip = self._add_hud_child(
                Rectangle2DNode(
                    position=Vector2(-60 + i * 4, -57),
                    width=3,
                    height=6,
                    color=COL_PIP_OK,
                    layer=27,
                )
            )
            self.hp_pips.append(pip)

        self.hud_sector = self._add_hud_child(
            Text2DNode(position=Vector2(-32, -57), text="S1", color=COL_HUD_SECTOR, letter_spacing=1.0, layer=28)
        )

        # Equipped Gun Box (color-coded frame + live weapon pixel sprite + short tag)
        self.hud_gun_border = self._add_hud_child(
            Rectangle2DNode(position=Vector2(-11, -57), width=20, height=11, color=WEAPONS[0]["accent"], layer=26)
        )
        self.hud_gun_fill = self._add_hud_child(
            Rectangle2DNode(position=Vector2(-11, -57), width=18, height=9, color=COL_HUD_GUN_FILL, layer=27)
        )
        self.hud_gun_icon = self._add_hud_child(
            Sprite2DNode(
                position=Vector2(-11, -57),
                texture=self.gun_textures[0],
                transparent_color=TRANSPARENT_KEY,
                playing=False,
                layer=28,
            )
        )
        self.hud_gun_tag = self._add_hud_child(
            Text2DNode(position=Vector2(13, -57), text="PSTL", color=WEAPONS[0]["accent"], letter_spacing=0.5, layer=28)
        )

        self.hud_score = self._add_hud_child(
            Text2DNode(position=Vector2(47, -57), text="00000", color=COL_HUD_SCORE, letter_spacing=0.5, layer=28)
        )

        # Toast banner right below HUD
        self.toast_bg = self._add_hud_child(
            Rectangle2DNode(position=Vector2(0, -42), width=86, height=11, color=COL_TOAST_BG, opacity=0.0, layer=29)
        )
        self.toast_text = self._add_hud_child(
            Text2DNode(position=Vector2(0, -42), text="", color=COL_SPARK_GOLD, letter_spacing=1.0, opacity=0.0, layer=30)
        )

        # Boss Health Bar at bottom (with dark pill behind title for high contrast)
        self.boss_bar_bg = self._add_hud_child(
            Rectangle2DNode(position=Vector2(0, 56), width=92, height=8, color=COL_HP_BG, opacity=0.0, layer=28)
        )
        self.boss_bar_fg = self._add_hud_child(
            Rectangle2DNode(position=Vector2(0, 56), width=88, height=4, color=COL_BOSS_FG, opacity=0.0, layer=29)
        )
        self.boss_lbl_bg = self._add_hud_child(
            Rectangle2DNode(position=Vector2(0, 47), width=78, height=9, color=COL_HP_BG, opacity=0.0, layer=28)
        )
        self.boss_label = self._add_hud_child(
            Text2DNode(position=Vector2(0, 47), text="SKY SENTINEL", color=COL_BOSS_LBL, letter_spacing=1.0, opacity=0.0, layer=29)
        )

        self.hud_nodes = [
            self.hud_bg, self.hud_line, self.hud_sector,
            self.hud_gun_border, self.hud_gun_fill, self.hud_gun_icon, self.hud_gun_tag,
            self.hud_score,
        ] + self.hp_pips

    def _build_overlays(self):
        self.ov_border = self._add_hud_child(
            Rectangle2DNode(position=Vector2(0, -6), width=118, height=78, color=COL_OV_CYAN, opacity=0.0, layer=35)
        )
        self.ov_card = self._add_hud_child(
            Rectangle2DNode(position=Vector2(0, -6), width=114, height=74, color=COL_OV_CARD, opacity=0.0, layer=36)
        )
        self.ov_title = self._add_hud_child(
            Text2DNode(position=Vector2(0, -30), text="SKYLINE STRIKE", color=COL_OV_TITLE, letter_spacing=1.0, opacity=0.0, layer=37)
        )
        self.ov_sub = self._add_hud_child(
            Text2DNode(position=Vector2(0, -16), text="", color=COL_OV_SUB, letter_spacing=1.0, opacity=0.0, layer=37)
        )
        self.ov_line1 = self._add_hud_child(
            Text2DNode(position=Vector2(0, -2), text="", color=COL_OV_LINE1, letter_spacing=1.0, opacity=0.0, layer=37)
        )
        self.ov_line2 = self._add_hud_child(
            Text2DNode(position=Vector2(0, 10), text="", color=COL_OV_LINE2, letter_spacing=1.0, opacity=0.0, layer=37)
        )
        self.ov_prompt = self._add_hud_child(
            Text2DNode(position=Vector2(0, 23), text="", color=COL_OV_GREEN, letter_spacing=1.0, opacity=0.0, layer=37)
        )
        self.ov_nodes = [
            self.ov_border, self.ov_card, self.ov_title,
            self.ov_sub, self.ov_line1, self.ov_line2, self.ov_prompt,
        ]

    def _set_hud_visible(self, visible):
        op = 1.0 if visible else 0.0
        for n in self.hud_nodes:
            n.opacity = op
        if not visible:
            self.toast_bg.opacity = 0.0
            self.toast_text.opacity = 0.0
            self.boss_bar_bg.opacity = 0.0
            self.boss_bar_fg.opacity = 0.0
            self.boss_lbl_bg.opacity = 0.0
            self.boss_label.opacity = 0.0

    def _show_overlay(self, title, sub, line1, line2, prompt, border_col=COL_OV_CYAN):
        self.ov_border.color = border_col
        self.ov_title.text = title
        self.ov_sub.text = sub
        self.ov_line1.text = line1
        self.ov_line2.text = line2
        self.ov_prompt.text = prompt
        for n in self.ov_nodes:
            n.opacity = 1.0

    def _hide_overlay(self):
        for n in self.ov_nodes:
            n.opacity = 0.0

    def _show_toast(self, text, color=COL_SPARK_GOLD, duration=1.15):
        self.toast_text.text = text
        self.toast_text.color = color
        self.toast_bg.width = min(124, len(text) * 6 + 10)
        self.toast_bg.opacity = 0.92
        self.toast_text.opacity = 1.0
        self.toast_timer = duration

    def _save_best(self):
        if self.score > self.best_score:
            self.best_score = self.score
            try:
                engine_save.save("best_score", self.best_score)
            except Exception as e:
                print("WARN: engine_save save failed:", e)

    def _update_hud(self):
        if self.player.hp != self._hud_last_hp:
            self._hud_last_hp = self.player.hp
            pip_col = COL_PIP_OK if self.player.hp > 2 else COL_PIP_LOW
            for i, pip in enumerate(self.hp_pips):
                pip.color = pip_col if i < self.player.hp else COL_PIP_OFF

        if self.player.weapon_idx != self._hud_last_weapon:
            self._hud_last_weapon = self.player.weapon_idx
            w = self.player.current_weapon()
            self.hud_gun_border.color = w["accent"]
            self.hud_gun_icon.texture = self.gun_textures[self.player.weapon_idx]
            self.hud_gun_tag.text = w["short"]
            self.hud_gun_tag.color = w["accent"]

        if self.sector_idx != self._hud_last_sector:
            self._hud_last_sector = self.sector_idx
            self.hud_sector.text = "C{}".format(self.chunk_idx + 1) if self.is_endless else SECTORS[self.sector_idx]["tag"]

        if self.score != self._hud_last_score:
            self._hud_last_score = self.score
            self.hud_score.text = "{:05d}".format(min(99999, self.score))

        # Boss health bar
        boss = self.enemies.boss_slot
        if boss is not None and boss.alive and abs(self.player.x - boss.x) < 150.0:
            ratio = max(0.0, boss.hp / float(boss.max_hp))
            fw = max(1.0, 88.0 * ratio)
            self.boss_bar_bg.opacity = 1.0
            self.boss_bar_fg.opacity = 1.0
            self.boss_lbl_bg.opacity = 0.88
            self.boss_label.opacity = 1.0
            self.boss_bar_fg.width = fw
            set_pos(self.boss_bar_fg, -44.0 + fw * 0.5, 56.0)
        else:
            self.boss_bar_bg.opacity = 0.0
            self.boss_bar_fg.opacity = 0.0
            self.boss_lbl_bg.opacity = 0.0
            self.boss_label.opacity = 0.0

    def _current_sec(self):
        return self._cached_sec

    def _load_sector(self, idx, reset_hp=False):
        self.sector_idx = idx
        self.chunk_idx = idx
        if self.is_endless:
            self._cached_sec = generate_endless_chunk(self.chunk_idx, self.endless_seed + self.chunk_idx * 7919)
        else:
            self._cached_sec = SECTORS[idx]
        sec = self._cached_sec
        if self.is_endless:
            sky_tex = self.forest_sky_tex if (idx % 2 == 1) else self.sky_textures[idx % len(self.sky_textures)]
            engine_draw.set_background(sky_tex)
        else:
            engine_draw.set_background(self.sky_textures[idx])

        self.buildings = sec["buildings"]
        self.props = sec["props"]
        self.ac_platforms = [(px, py) for (px, py, kind) in self.props if kind == "ac"]
        self.beacon_pos = sec["beacon"]
        last_b = self.buildings[-1]
        self.level_max_x = float(last_b[0] + last_b[1] - 8)

        self.fx.clear()
        self.bullets.clear()
        self.enemies.load_sector(sec["enemies"])
        if self.is_endless and sec.get("has_boss") and self.enemies.boss_slot is not None:
            bhp = sec.get("boss_hp", 180)
            self.enemies.boss_slot.hp = bhp
            self.enemies.boss_slot.max_hp = bhp

        # Setup pickups
        self.pickups = []
        for i, n in enumerate(self.pickup_nodes):
            if i < len(sec["pickups"]):
                kind, px, py = sec["pickups"][i]
                self.pickups.append({"kind": kind, "x": float(px), "y": float(py), "taken": False})
                n.texture = self.pickup_textures[kind]
                set_pos(n, float(px), float(py))
                n.opacity = 1.0
            else:
                n.opacity = 0.0
                set_pos(n, -999.0, 999.0)

        sx, sy = sec["spawn"]
        self.player.reset(sx, sy, keep_hp=not reset_hp)
        self.cam_x = sx + 22.0
        self.cam_y = -6.0
        self._update_world_render()
        self._update_hud()

    def _refresh_title_pickers(self):
        m_txt = "ADVENTURE" if self.pick_mode == 0 else "ENDLESS"
        p_txt = "1P SOLO" if self.pick_players == 0 else "2P LINK"
        l1 = ("> " if self.pick_cursor == 0 else "  ") + "MODE: <" + m_txt + ">"
        l2 = ("> " if self.pick_cursor == 1 else "  ") + "PLAY: <" + p_txt + ">"
        best_line = "BEST: {:05d}".format(self.best_score) if self.best_score > 0 else "5 GUNS - 6 SECTORS"
        self._show_overlay(
            "SKYLINE STRIKE",
            best_line,
            l1,
            l2,
            "PRESS A TO START",
            COL_OV_TITLE,
        )

    def _enter_title(self):
        self.state = STATE_TITLE
        self._set_hud_visible(False)
        self._refresh_title_pickers()

    def _start_new_game(self):
        try:
            engine_audio.stop(3)
        except Exception:
            pass
        self._hide_overlay()
        self.is_endless = (self.pick_mode == 1)
        self.is_2p = (self.pick_players == 1)
        self._link_announced = False
        if self.is_2p:
            self.link.start()
        else:
            self.link.stop()
        self.remote_sprite.opacity = 0.0
        self.score = 0
        self.kills = 0
        self.chunk_idx = 0
        self.player.equip(0)
        self._load_sector(0, reset_hp=True)
        self._set_hud_visible(True)
        if self.is_2p and not self.link.is_connected():
            self.state = STATE_LINK_WAIT
            self._show_overlay(
                "2P LINK CABLE",
                "CONNECT USB-C",
                "TO OTHER THUMBY",
                "WAITING...",
                "B: PLAY 1P SOLO",
                COL_OV_TITLE,
            )
        else:
            self._hide_overlay()
            self.state = STATE_PLAYING
            tag_name = "ENDLESS #1" if self.is_endless else ("S1: " + SECTORS[0]["name"])
            self._show_toast(tag_name, COL_SPARK_CYAN, 1.4)
        self.play_sfx("swap", 3)

    def _cycle_weapon(self, delta):
        w = self.player.equip(self.player.weapon_idx + delta)
        self._update_hud()
        self._show_toast(w["name"], w["accent"], 1.1)
        self.play_sfx("swap", 3)

    def _update_world_render(self):
        sx = 0.0
        sy = 0.0
        if self.shake_timer > 0.0:
            s = self.shake_mag * (self.shake_timer / 0.14)
            sx = s if ((self.frame_count & 1) == 0) else -s
            sy = (s * 0.5) if (((self.frame_count >> 1) & 1) == 0) else -(s * 0.5)
        set_pos(self.camera, self.cam_x + sx, self.cam_y + sy)

        # Seamless 2-layer parallax city skyline
        far_shift = (self.cam_x * 0.22) % 128.0
        far_x0 = self.cam_x - far_shift
        set_pos(self.far_nodes[0], far_x0, self.cam_y + 18.0)
        set_pos(self.far_nodes[1], far_x0 + 128.0, self.cam_y + 18.0)

        mid_shift = (self.cam_x * 0.48) % 128.0
        mid_x0 = self.cam_x - mid_shift
        set_pos(self.mid_nodes[0], mid_x0, self.cam_y + 30.0)
        set_pos(self.mid_nodes[1], mid_x0 + 128.0, self.cam_y + 30.0)

        # Render visible foreground rooftop facade tiles (32x64)
        f_idx = 0
        view_l = self.cam_x - 84.0
        view_r = self.cam_x + 84.0
        for bx, bw, roof_y, style in self.buildings:
            if bx + bw < view_l or bx > view_r:
                continue
            tex = self.roof_textures[style % len(self.roof_textures)]
            tx = bx + 16
            end_x = bx + bw
            while tx < end_x and f_idx < len(self.facade_pool):
                if view_l <= tx <= view_r:
                    node = self.facade_pool[f_idx]
                    node.texture = tex
                    set_pos(node, float(tx), float(roof_y + 32))
                    node.opacity = 1.0
                    f_idx += 1
                tx += 32
        while f_idx < len(self.facade_pool):
            n = self.facade_pool[f_idx]
            n.opacity = 0.0
            set_pos(n, -999.0, 999.0)
            f_idx += 1

        # Render visible rooftop props
        p_idx = 0
        for px, roof_y, kind in self.props:
            if view_l <= px <= view_r and p_idx < len(self.prop_pool):
                node = self.prop_pool[p_idx]
                node.texture = self.prop_textures[kind]
                set_pos(node, float(px), float(roof_y) - PROP_HALF_H[kind])
                node.opacity = 1.0
                p_idx += 1
        while p_idx < len(self.prop_pool):
            n = self.prop_pool[p_idx]
            n.opacity = 0.0
            set_pos(n, -999.0, 999.0)
            p_idx += 1

        # Extraction beacon
        bx, by = self.beacon_pos
        if view_l <= bx <= view_r:
            set_pos(self.beacon_node, float(bx), float(by) - PROP_HALF_H["beacon"])
            boss_locked = self._current_sec()["has_boss"] and self.enemies.boss_alive()
            if boss_locked:
                self.beacon_node.opacity = 0.25
            else:
                self.beacon_node.opacity = 0.78 + 0.22 * math.sin(self.time_acc * 7.0)
        else:
            self.beacon_node.opacity = 0.0

        # Bobbing pickups
        for i, pk in enumerate(self.pickups):
            node = self.pickup_nodes[i]
            if pk["taken"]:
                node.opacity = 0.0
            else:
                bob = math.sin(self.time_acc * 4.5 + i) * 2.2
                set_pos(node, pk["x"], pk["y"] + bob)
                node.opacity = 1.0

    def step(self, dt):
        self.frame_count += 1
        self.time_acc += dt
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)

        if self.state == STATE_TITLE:
            intro_t = min(1.0, self.time_acc / 1.2)
            self.cam_x = -24.0 + intro_t * 42.0 + math.sin(self.time_acc * 0.45) * 42.0 * intro_t
            self.cam_y = -28.0 + intro_t * 22.0
            self.ov_title.opacity = intro_t
            self.ov_prompt.opacity = (1.0 if ((int(self.time_acc * 3.0) & 1) == 0) else 0.45) if intro_t >= 0.9 else intro_t
            self._update_world_render()
            if engine_io.UP.is_just_pressed or engine_io.DOWN.is_just_pressed:
                self.pick_cursor = 1 - self.pick_cursor
                self._refresh_title_pickers()
            elif engine_io.LEFT.is_just_pressed or engine_io.RIGHT.is_just_pressed:
                if self.pick_cursor == 0:
                    self.pick_mode = 1 - self.pick_mode
                else:
                    self.pick_players = 1 - self.pick_players
                self._refresh_title_pickers()
            elif engine_io.A.is_just_pressed or engine_io.B.is_just_pressed:
                self._start_new_game()
            return

        if self.state == STATE_LINK_WAIT:
            self._update_world_render()
            self.link.sync(
                self.player.x,
                self.player.y,
                self.player.facing,
                self.player.weapon_idx,
                self.player.hp,
                False,
                self.sector_idx,
                self.score,
            )
            if self.link.is_connected() or self.link.remote_seen:
                self._hide_overlay()
                self.state = STATE_PLAYING
                self._show_toast("2P LINKED!", COL_PIP_OK, 1.4)
            elif engine_io.B.is_just_pressed or engine_io.MENU.is_just_pressed:
                self.is_2p = False
                self.link.stop()
                self._hide_overlay()
                self.state = STATE_PLAYING
                self._show_toast("1P SOLO", COL_SPARK_CYAN, 1.2)
            return

        if self.state == STATE_UPGRADE:
            if engine_io.UP.is_just_pressed:
                self.upgrade_cursor = (self.upgrade_cursor - 1) % 5
                self._refresh_upgrade_overlay()
            elif engine_io.DOWN.is_just_pressed:
                self.upgrade_cursor = (self.upgrade_cursor + 1) % 5
                self._refresh_upgrade_overlay()
            elif engine_io.MENU.is_just_pressed or (engine_io.A.is_just_pressed and self.upgrade_cursor == 4):
                self._hide_overlay()
                self.state = STATE_PLAYING
            elif engine_io.A.is_just_pressed:
                wid = self.player.current_weapon()["id"]
                up = self.endless_upgrades[wid]
                if self.upgrade_cursor == 3:
                    for k in self.endless_upgrades:
                        self.endless_upgrades[k]["rate"] = 0
                        self.endless_upgrades[k]["dmg"] = 0
                        self.endless_upgrades[k]["size"] = 0
                    self._show_toast("UPGRADES RESET", COL_SPARK_GOLD, 1.0)
                else:
                    key = ("rate", "dmg", "size")[self.upgrade_cursor]
                    if self.coins >= 5 and up[key] < 5:
                        self.coins -= 5
                        up[key] += 1
                        self.play_sfx("pickup", 3)
                self._refresh_upgrade_overlay()
            return

        if self.state == STATE_PAUSED:
            if engine_io.RB.is_just_pressed:
                self._cycle_weapon(1)
                self._refresh_pause_overlay()
            elif engine_io.LB.is_just_pressed:
                self._cycle_weapon(-1)
                self._refresh_pause_overlay()
            elif engine_io.MENU.is_just_pressed or engine_io.A.is_just_pressed:
                self._hide_overlay()
                self.state = STATE_PLAYING
            elif engine_io.B.is_just_pressed:
                self._start_new_game()
            return

        if self.state == STATE_SECTOR_CLEAR:
            self.state_timer -= dt
            self.fx.update(dt)
            self._update_world_render()
            if self.state_timer <= 0.0 or engine_io.A.is_just_pressed:
                next_idx = self.sector_idx + 1
                self._hide_overlay()
                self._load_sector(next_idx, reset_hp=False)
                self.player.hp = min(self.player.max_hp, self.player.hp + 1)
                self._update_hud()
                self.state = STATE_PLAYING
                tag_name = "ENDLESS #{}".format(next_idx + 1) if self.is_endless else (SECTORS[next_idx]["tag"] + ": " + SECTORS[next_idx]["name"])
                self._show_toast(tag_name, COL_SPARK_CYAN, 1.4)
            return

        if self.state in (STATE_GAMEOVER, STATE_VICTORY):
            self.fx.update(dt)
            self.ov_prompt.opacity = 1.0 if ((int(self.time_acc * 3.0) & 1) == 0) else 0.45
            self._update_world_render()
            if engine_io.A.is_just_pressed or engine_io.B.is_just_pressed:
                self._start_new_game()
            return

        # === STATE_PLAYING ===
        if engine_io.MENU.is_just_pressed:
            self.player.stop_rumble()
            if self.is_endless:
                self.upgrade_cursor = 0
                self.state = STATE_UPGRADE
                self._refresh_upgrade_overlay()
            else:
                self.state = STATE_PAUSED
                self._refresh_pause_overlay()
            return

        if engine_io.RB.is_just_pressed:
            self._cycle_weapon(1)
        elif engine_io.LB.is_just_pressed:
            self._cycle_weapon(-1)

        if self.toast_timer > 0.0:
            self.toast_timer -= dt
            if self.toast_timer <= 0.0:
                self.toast_bg.opacity = 0.0
                self.toast_text.opacity = 0.0

        self.player.update(
            dt,
            self.buildings,
            self.ac_platforms,
            self.fx,
            self.play_sfx,
            min_x=-26.0,
            max_x=self.level_max_x,
        )

        if engine_io.B.is_pressed:
            if self.is_endless:
                up = self.endless_upgrades[self.player.current_weapon()["id"]]
                rate_mult = max(0.45, 1.0 - up["rate"] * 0.1)
                dmg_bonus = up["dmg"] * 4
                bh_bonus = up["size"]
                shake = self.player.try_fire(self.bullets, self.fx, self.play_sfx, rate_mult, dmg_bonus, bh_bonus)
            else:
                shake = self.player.try_fire(self.bullets, self.fx, self.play_sfx)
            if shake > 0.0:
                self.shake_timer = 0.14
                self.shake_mag = max(self.shake_mag, shake)

        self.bullets.update(dt, self.buildings, self.fx)
        gained, kills = self.enemies.update(dt, self.player, self.buildings, self.bullets, self.fx, self.play_sfx)
        if gained > 0:
            self.score += gained
            self.kills += kills
            if self.is_endless:
                self.coins += kills * 2
                if gained >= 1000:
                    self.coins += 20
                    self._show_toast("BOSS +20 COINS!", COL_SPARK_GOLD, 1.2)
            self.shake_timer = 0.14
            self.shake_mag = max(self.shake_mag, 1.6)
        self.fx.update(dt)

        if self.is_2p:
            self.link.sync(
                self.player.x,
                self.player.y,
                self.player.facing,
                self.player.weapon_idx,
                self.player.hp,
                engine_io.B.is_pressed,
                self.sector_idx,
                self.score,
            )
            if self.link.remote_seen:
                if not self._link_announced:
                    self._link_announced = True
                    if not self.link.is_host():
                        self.player.sprite.texture = self.player_red_tex
                        self.remote_sprite.texture = self.player_tex
                    self._show_toast("2P LINKED!", COL_PIP_OK, 1.2)
                set_pos(self.remote_sprite, self.link.remote_x, self.link.remote_y)
                self.remote_sprite.scale.x = 1.0 if self.link.remote_facing >= 0 else -1.0
                self.remote_sprite.opacity = 1.0
                if self.link.remote_sector > self.sector_idx:
                    self._load_sector(self.link.remote_sector, reset_hp=False)
                    return

        if self.player.hp <= 0:
            self.player.stop_rumble()
            self._save_best()
            self.player.sync_visuals(visible=False)
            self.fx.spawn_explosion(self.player.x, self.player.y, big=True)
            self.state = STATE_GAMEOVER
            self._update_world_render()
            self._update_hud()
            self._show_overlay(
                "SHIELD DOWN",
                "SCORE: {:05d}".format(self.score),
                "BEST:  {:05d}".format(self.best_score),
                "BOTS:  {}".format(self.kills),
                "PRESS A TO RETRY",
                COL_OV_WARN,
            )
            return

        for i, pk in enumerate(self.pickups):
            if pk["taken"]:
                continue
            if abs(self.player.x - pk["x"]) < 11.0 and abs(self.player.y - pk["y"]) < 12.0:
                pk["taken"] = True
                self.pickup_nodes[i].opacity = 0.0
                self.play_sfx("pickup", 3)
                if pk["kind"] == "med":
                    if self.player.hp < self.player.max_hp:
                        self.player.hp += 1
                        self._show_toast("SHIELD +1", COL_PIP_OK, 0.95)
                    else:
                        self.score += 150
                        self._show_toast("MAX SHIELD +150", COL_SPARK_GOLD, 0.95)
                    self.fx.spawn_sparks(pk["x"], pk["y"], 6, COL_PIP_OK, COL_SPARK_WHITE)
                else:
                    self.score += 250
                    self.player.overcharge_timer = 5.0
                    self._show_toast("OVERCHARGE +250", COL_SPARK_GOLD, 1.0)
                    self.fx.spawn_sparks(pk["x"], pk["y"], 6, COL_SPARK_GOLD, COL_SPARK_CYAN)

        target_cx = self.player.x + self.player.facing * 16.0
        target_cx = max(24.0, min(self.level_max_x - 38.0, target_cx))
        target_cy = max(-22.0, min(4.0, self.player.y - 22.0))
        lerp_rate = min(1.0, dt * 7.5)
        self.cam_x += (target_cx - self.cam_x) * lerp_rate
        self.cam_y += (target_cy - self.cam_y) * min(1.0, dt * 5.0)

        self._update_world_render()
        self._update_hud()

        bx, by = self.beacon_pos
        boss_locked = self._current_sec()["has_boss"] and self.enemies.boss_alive()
        if not boss_locked and abs(self.player.x - bx) < 14.0 and abs(self.player.y - (by - 10.0)) < 20.0:
            self.score += 500
            self._update_hud()
            self.fx.spawn_sparks(bx, by - 12.0, 10, COL_SPARK_CYAN, COL_SPARK_GOLD)
            self.play_sfx("pickup", 3)
            if self.is_endless or (self.sector_idx + 1 < len(SECTORS)):
                self.state = STATE_SECTOR_CLEAR
                self.state_timer = 1.6
                nxt_name = "ENDLESS #{}".format(self.chunk_idx + 2) if self.is_endless else SECTORS[self.sector_idx + 1]["name"]
                self._show_overlay(
                    "CHUNK CLEAR!" if self.is_endless else "SECTOR CLEAR!",
                    "+500 ROOF BONUS",
                    "NEXT: " + nxt_name,
                    "SHIELD +1 RESTORED",
                    "PRESS A TO CONTINUE",
                    COL_OV_GREEN,
                )
            else:
                self._save_best()
                self.state = STATE_VICTORY
                self._show_overlay(
                    "CITY SECURED!",
                    "SCORE: {:05d}".format(self.score),
                    "BEST:  {:05d}".format(self.best_score),
                    "BOTS:  {}".format(self.kills),
                    "PRESS A PLAY AGAIN",
                    COL_SPARK_GOLD,
                )

    def _refresh_upgrade_overlay(self):
        w = self.player.current_weapon()
        up = self.endless_upgrades[w["id"]]
        items = [
            "RATE LV{} (5C)".format(up["rate"]),
            "DMG  LV{} (5C)".format(up["dmg"]),
            "SIZE LV{} (5C)".format(up["size"]),
            "RESET UPGRADES",
            "RESUME",
        ]
        c = self.upgrade_cursor
        l1 = ("> " if c == 0 else "  ") + items[0]
        l2 = ("> " if c == 1 else "  ") + items[1]
        l3 = ("> " if c == 2 else "  ") + items[2]
        pr = ("> " if c >= 3 else "  ") + items[c if c >= 3 else 4]
        self._show_overlay(
            "UPGRADE " + w["short"] + " C:" + str(self.coins),
            l1,
            l2,
            l3,
            pr,
            COL_OV_TITLE,
        )

    def _refresh_pause_overlay(self):
        w = self.player.current_weapon()
        self._show_overlay(
            "PAUSED",
            w["name"],
            "DMG:{}  LB/RB:GUN".format(w["damage"] * w["pellets"]),
            "A/MENU:RESUME",
            "B:RESTART RUN",
            w["accent"],
        )

    def tick_once(self):
        """Advance exactly one rendered frame."""
        while not engine.tick():
            pass
        dt = 1.0 / 60.0 if self.headless_fast else min(0.05, max(1.0 / 120.0, engine.dt()))
        if dt < 0.008:
            dt = 1.0 / 60.0
        self.step(dt)

    def run(self, max_frames=0):
        last_ms = time.ticks_ms()
        while self.running:
            if not engine.tick():
                continue
            now_ms = time.ticks_ms()
            raw_dt = time.ticks_diff(now_ms, last_ms) * 0.001
            last_ms = now_ms
            dt = 1.0 / 60.0 if (self.headless_fast or raw_dt <= 0.001) else min(0.05, raw_dt)
            self.step(dt)
            if max_frames and self.frame_count >= max_frames:
                break
