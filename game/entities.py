import math
import random

import engine_io
from engine_draw import Color
from engine_math import Vector2
from engine_nodes import Rectangle2DNode, Sprite2DNode

TRANSPARENT_KEY = Color(1.0, 0.0, 1.0)

# Strictly bloodless mechanical / energy FX colors
COL_SPARK_CYAN = Color(0.28, 0.96, 1.0)
COL_SPARK_GOLD = Color(1.0, 0.86, 0.24)
COL_SPARK_WHITE = Color(1.0, 1.0, 1.0)
COL_SPARK_STEEL = Color(0.68, 0.74, 0.86)
COL_SPARK_PURPLE = Color(0.86, 0.42, 1.0)
COL_DUST = Color(0.76, 0.84, 0.94)

COL_HP_BG = Color(0.08, 0.09, 0.16)
COL_HP_HIGH = Color(0.24, 0.94, 0.56)
COL_HP_MID = Color(1.0, 0.84, 0.22)
COL_HP_LOW = Color(1.0, 0.54, 0.16)

COL_ENEMY_BOLT = Color(1.0, 0.64, 0.18)
COL_ENEMY_DRONE_BOLT = Color(0.32, 0.92, 1.0)
COL_BOSS_BOLT = Color(0.95, 0.48, 1.0)


def set_pos(node, x, y):
    p = node.position
    p.x = x
    p.y = y


def set_scale_x(node, sx):
    s = node.scale
    s.x = sx


class FxParticle:
    def __init__(self, layer=14):
        self.active = False
        self.x = -999.0
        self.y = -999.0
        self.vx = 0.0
        self.vy = 0.0
        self.gravity = 0.0
        self.life = 0.0
        self.max_life = 0.2
        self.node = Rectangle2DNode(
            position=Vector2(-999.0, -999.0),
            width=2,
            height=2,
            color=COL_SPARK_CYAN,
            opacity=0.0,
            layer=layer,
        )

    def spawn(self, x, y, vx, vy, size, color, life, gravity=0.0):
        self.active = True
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.gravity = gravity
        self.life = life
        self.max_life = life
        self.node.width = size
        self.node.height = size
        self.node.color = color
        set_pos(self.node, x, y)
        self.node.opacity = 1.0

    def hide(self):
        self.active = False
        self.node.opacity = 0.0
        set_pos(self.node, -999.0, -999.0)


class FxPool:
    """Pooled mechanical sparks, electric flashes, metallic bolts & landing dust (zero blood)."""

    def __init__(self, count=18):
        self.items = [FxParticle(14) for _ in range(count)]
        self.cursor = 0

    def _next(self):
        p = self.items[self.cursor]
        self.cursor = (self.cursor + 1) % len(self.items)
        return p

    def clear(self):
        for p in self.items:
            p.hide()

    def spawn_sparks(self, x, y, count=4, col_a=COL_SPARK_CYAN, col_b=COL_SPARK_GOLD):
        for i in range(count):
            ang = random.uniform(0.0, 6.283)
            spd = random.uniform(28.0, 88.0)
            col = col_a if (i % 2 == 0) else col_b
            sz = 2 if (i % 3 != 0) else 3
            self._next().spawn(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd - 14.0,
                sz, col, random.uniform(0.14, 0.28), gravity=160.0
            )

    def spawn_explosion(self, x, y, big=False):
        # Bright energy core flash
        self._next().spawn(x, y, 0.0, 0.0, 12 if big else 8, COL_SPARK_WHITE, 0.09, 0.0)
        self._next().spawn(x, y, 0.0, -4.0, 10 if big else 6, COL_SPARK_GOLD, 0.16, 0.0)
        # Mechanical scrap bolts & electric cyan sparks (100% bloodless!)
        n = 10 if big else 6
        cols = (COL_SPARK_CYAN, COL_SPARK_GOLD, COL_SPARK_STEEL, COL_SPARK_WHITE)
        for i in range(n):
            ang = (6.283 * i) / n + random.uniform(-0.25, 0.25)
            spd = random.uniform(35.0, 110.0 if big else 82.0)
            self._next().spawn(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd - 26.0,
                3 if (i % 2 == 0) else 2, cols[i % 4],
                random.uniform(0.22, 0.44), gravity=220.0
            )

    def spawn_dust(self, x, y):
        for dx in (-3.0, 3.0):
            self._next().spawn(
                x + dx, y, dx * 7.0, random.uniform(-16.0, -6.0),
                2, COL_DUST, 0.16, gravity=40.0
            )

    def update(self, dt):
        for p in self.items:
            if not p.active:
                continue
            p.life -= dt
            if p.life <= 0.0:
                p.hide()
                continue
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            set_pos(p.node, p.x, p.y)
            ratio = p.life / p.max_life
            p.node.opacity = 1.0 if ratio > 0.35 else ratio / 0.35


class Bullet:
    def __init__(self, layer=12):
        self.active = False
        self.from_player = True
        self.x = -999.0
        self.y = -999.0
        self.vx = 0.0
        self.vy = 0.0
        self.w = 4.0
        self.h = 2.0
        self.damage = 10
        self.life = 0.0
        self.pierce = False
        self.hit_mask = 0
        self.spark_col = COL_SPARK_CYAN
        self.node = Rectangle2DNode(
            position=Vector2(-999.0, -999.0),
            width=4,
            height=2,
            color=COL_SPARK_GOLD,
            opacity=0.0,
            layer=layer,
        )

    def spawn(self, x, y, vx, vy, w, h, color, damage, life, from_player=True, pierce=False, spark_col=COL_SPARK_CYAN):
        self.active = True
        self.from_player = from_player
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.w = float(w)
        self.h = float(h)
        self.damage = damage
        self.life = life
        self.pierce = pierce
        self.hit_mask = 0
        self.spark_col = spark_col
        self.node.width = w
        self.node.height = h
        self.node.color = color
        set_pos(self.node, x, y)
        self.node.opacity = 1.0

    def hide(self):
        self.active = False
        self.node.opacity = 0.0
        set_pos(self.node, -999.0, -999.0)


class BulletPool:
    def __init__(self, count=18):
        self.items = [Bullet(12) for _ in range(count)]
        self.cursor = 0

    def clear(self):
        for b in self.items:
            b.hide()

    def spawn(self, x, y, vx, vy, w, h, color, damage, life, from_player=True, pierce=False, spark_col=COL_SPARK_CYAN):
        for b in self.items:
            if not b.active:
                b.spawn(x, y, vx, vy, w, h, color, damage, life, from_player, pierce, spark_col)
                return b
        b = self.items[self.cursor]
        self.cursor = (self.cursor + 1) % len(self.items)
        b.spawn(x, y, vx, vy, w, h, color, damage, life, from_player, pierce, spark_col)
        return b

    def update(self, dt, buildings, fx):
        for b in self.items:
            if not b.active:
                continue
            b.life -= dt
            if b.life <= 0.0:
                b.hide()
                continue
            b.x += b.vx * dt
            b.y += b.vy * dt
            set_pos(b.node, b.x, b.y)
            # Check collision with solid building facades
            hit_wall = False
            for bx, bw, roof_y, _ in buildings:
                if bx <= b.x <= bx + bw and b.y >= roof_y + 1:
                    hit_wall = True
                    break
            if hit_wall:
                fx.spawn_sparks(b.x, b.y, 3, b.spark_col, COL_SPARK_WHITE)
                b.hide()


class Player:
    RUN_SPEED = 78.0
    GRAVITY = 420.0
    JUMP_VEL = -168.0
    HALF_W = 4.5
    HALF_H = 7.5

    def __init__(self, player_tex, gun_textures, weapons):
        self.weapons = weapons
        self.gun_textures = gun_textures
        self.weapon_idx = 0

        self.x = 0.0
        self.y = 16.0
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0

        self.max_hp = 5
        self.hp = 5
        self.invuln_timer = 0.0
        self.fire_timer = 0.0
        self.overcharge_timer = 0.0
        self.recoil_offset = 0.0
        self.muzzle_timer = 0.0
        self.anim_timer = 0.0
        self.safe_x = 0.0
        self.safe_y = 16.0
        self._rumbling = False

        self.sprite = Sprite2DNode(
            position=Vector2(self.x, self.y),
            texture=player_tex,
            transparent_color=TRANSPARENT_KEY,
            frame_count_x=6,
            frame_count_y=1,
            playing=False,
            layer=10,
        )
        self.gun_sprite = Sprite2DNode(
            position=Vector2(self.x + 6, self.y + 1),
            texture=gun_textures[0],
            transparent_color=TRANSPARENT_KEY,
            playing=False,
            layer=11,
        )
        self.muzzle_node = Rectangle2DNode(
            position=Vector2(-999.0, -999.0),
            width=4,
            height=4,
            color=COL_SPARK_CYAN,
            opacity=0.0,
            layer=13,
        )

    def reset(self, spawn_x, spawn_y, keep_hp=False):
        self.x = spawn_x
        self.y = spawn_y
        self.safe_x = spawn_x
        self.safe_y = spawn_y
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.coyote_timer = 0.0
        self.jump_buffer = 0.0
        if not keep_hp:
            self.hp = self.max_hp
        self.invuln_timer = 0.5
        self.fire_timer = 0.0
        self.overcharge_timer = 0.0
        self.recoil_offset = 0.0
        self.muzzle_timer = 0.0
        self.sync_visuals(visible=True)

    def equip(self, idx):
        self.weapon_idx = idx % len(self.weapons)
        self.gun_sprite.texture = self.gun_textures[self.weapon_idx]
        self.recoil_offset = 2.0
        self.fire_timer = min(self.fire_timer, 0.05)
        self.sync_visuals(visible=True)
        return self.weapons[self.weapon_idx]

    def current_weapon(self):
        return self.weapons[self.weapon_idx]

    def take_damage(self, amount, fx, play_sfx):
        if self.invuln_timer > 0.0 or self.hp <= 0:
            return False
        self.hp = max(0, self.hp - amount)
        self.invuln_timer = 1.15
        # Bloodless blue/gold shield shatter sparks
        fx.spawn_sparks(self.x, self.y, 6, COL_SPARK_CYAN, COL_SPARK_GOLD)
        play_sfx("hurt", 2)
        try:
            engine_io.rumble(0.35)
            self._rumbling = True
        except Exception:
            pass
        return True

    def try_fire(self, bullets, fx, play_sfx):
        if self.fire_timer > 0.0:
            return 0.0
        w = self.current_weapon()
        cd = w["cooldown"] * (0.65 if self.overcharge_timer > 0.0 else 1.0)
        self.fire_timer = cd
        self.recoil_offset = w["recoil"]
        self.muzzle_timer = 0.055

        gun_x = self.x + self.facing * (6.0 - self.recoil_offset)
        gun_y = self.y + 1.0
        mx = gun_x + self.facing * w["muzzle_x"]
        my = gun_y + w["muzzle_y"]

        self.muzzle_node.color = w["muzzle_color"]
        self.muzzle_node.width = 5 if w["pellets"] > 1 or w["pierce"] else 4
        self.muzzle_node.height = 5 if w["pellets"] > 1 else 3
        set_pos(self.muzzle_node, mx, my)
        self.muzzle_node.opacity = 1.0

        pellets = w["pellets"]
        spread = w["spread"]
        for i in range(pellets):
            if pellets > 1:
                frac = (i / float(pellets - 1)) - 0.5
                vy = frac * spread * 2.0 + random.uniform(-6.0, 6.0)
            elif spread > 0.0:
                vy = random.uniform(-spread, spread)
            else:
                vy = 0.0
            vx = self.facing * w["speed"]
            bullets.spawn(
                mx, my, vx, vy,
                w["bw"], w["bh"],
                w["bullet_color"],
                w["damage"],
                w["life"],
                True,
                w["pierce"],
                w["accent"],
            )

        play_sfx(w["id"], 0)
        return w["shake"]

    def update(self, dt, buildings, ac_platforms, fx, play_sfx, min_x=-26.0, max_x=900.0):
        # Timers
        if self.invuln_timer > 0.0:
            self.invuln_timer = max(0.0, self.invuln_timer - dt)
            if self._rumbling and self.invuln_timer < 0.95:
                self._rumbling = False
                try:
                    engine_io.rumble(0.0)
                except Exception:
                    pass
        if self.fire_timer > 0.0:
            self.fire_timer = max(0.0, self.fire_timer - dt)
        if self.overcharge_timer > 0.0:
            self.overcharge_timer = max(0.0, self.overcharge_timer - dt)
        if self.recoil_offset > 0.0:
            self.recoil_offset = max(0.0, self.recoil_offset - 18.0 * dt)
        if self.muzzle_timer > 0.0:
            self.muzzle_timer -= dt
            if self.muzzle_timer <= 0.0:
                self.muzzle_node.opacity = 0.0

        # Horizontal input
        move = 0
        if engine_io.LEFT.is_pressed:
            move -= 1
        if engine_io.RIGHT.is_pressed:
            move += 1
        if move != 0:
            self.facing = move
            target_vx = move * self.RUN_SPEED
            accel = 640.0 if self.on_ground else 420.0
            if self.vx < target_vx:
                self.vx = min(target_vx, self.vx + accel * dt)
            else:
                self.vx = max(target_vx, self.vx - accel * dt)
        else:
            friction = 620.0 if self.on_ground else 220.0
            if self.vx > 0.0:
                self.vx = max(0.0, self.vx - friction * dt)
            elif self.vx < 0.0:
                self.vx = min(0.0, self.vx + friction * dt)

        # Jump buffering + coyote time
        if engine_io.A.is_just_pressed or engine_io.UP.is_just_pressed:
            self.jump_buffer = 0.11
        elif self.jump_buffer > 0.0:
            self.jump_buffer = max(0.0, self.jump_buffer - dt)

        if self.on_ground:
            self.coyote_timer = 0.10
        elif self.coyote_timer > 0.0:
            self.coyote_timer = max(0.0, self.coyote_timer - dt)

        if self.jump_buffer > 0.0 and self.coyote_timer > 0.0:
            self.vy = self.JUMP_VEL
            self.on_ground = False
            self.coyote_timer = 0.0
            self.jump_buffer = 0.0
            fx.spawn_dust(self.x, self.y + self.HALF_H)
            play_sfx("jump", 1)

        # Variable jump height on early button release
        if self.vy < -60.0 and not (engine_io.A.is_pressed or engine_io.UP.is_pressed):
            self.vy *= 0.84

        # Apply horizontal movement + building side-wall resolution
        prev_bottom = self.y + self.HALF_H
        self.x += self.vx * dt
        if self.x < min_x:
            self.x = min_x
            self.vx = 0.0
        elif self.x > max_x:
            self.x = max_x
            self.vx = 0.0

        for bx, bw, roof_y, _ in buildings:
            if prev_bottom > roof_y + 4.0:
                if self.x + self.HALF_W > bx and self.x - self.HALF_W < bx + bw:
                    if self.vx > 0.0:
                        self.x = bx - self.HALF_W
                        self.vx = 0.0
                    elif self.vx < 0.0:
                        self.x = bx + bw + self.HALF_W
                        self.vx = 0.0

        # Apply gravity + vertical landing
        was_ground = self.on_ground
        self.on_ground = False
        self.vy = min(240.0, self.vy + self.GRAVITY * dt)
        self.y += self.vy * dt
        new_bottom = self.y + self.HALF_H

        if self.vy >= 0.0:
            for bx, bw, roof_y, _ in buildings:
                if self.x + self.HALF_W > bx + 1.0 and self.x - self.HALF_W < bx + bw - 1.0:
                    if prev_bottom <= roof_y + 5.0 and new_bottom >= roof_y:
                        self.y = roof_y - self.HALF_H
                        self.vy = 0.0
                        self.on_ground = True
                        self.safe_x = max(bx + 12.0, min(bx + bw - 12.0, self.x))
                        self.safe_y = roof_y - self.HALF_H - 2.0
                        break
            if not self.on_ground and not engine_io.DOWN.is_pressed:
                for ax, ay in ac_platforms:
                    top_y = ay - 10.0
                    if self.x + self.HALF_W > ax - 7.5 and self.x - self.HALF_W < ax + 7.5:
                        if prev_bottom <= top_y + 4.0 and new_bottom >= top_y:
                            self.y = top_y - self.HALF_H
                            self.vy = 0.0
                            self.on_ground = True
                            break

        if self.on_ground and not was_ground:
            fx.spawn_dust(self.x, self.y + self.HALF_H)

        # Falling into city chasm -> recover on last rooftop (-1 HP)
        fell = False
        if self.y > 92.0:
            fell = True
            self.take_damage(1, fx, play_sfx)
            if self.hp > 0:
                self.x = self.safe_x
                self.y = self.safe_y
                self.vx = 0.0
                self.vy = 0.0
                fx.spawn_sparks(self.x, self.y, 6, COL_SPARK_CYAN, COL_SPARK_WHITE)

        # Animation frame selection
        if not self.on_ground:
            self.sprite.frame_current_x = 4 if self.vy < 0.0 else 5
        elif abs(self.vx) > 8.0:
            self.anim_timer += dt * 11.0
            run_seq = (1, 2, 3, 2)
            self.sprite.frame_current_x = run_seq[int(self.anim_timer) & 3]
        else:
            self.sprite.frame_current_x = 0

        self.sync_visuals(visible=True)
        return fell

    def sync_visuals(self, visible=True):
        if not visible:
            self.sprite.opacity = 0.0
            self.gun_sprite.opacity = 0.0
            self.muzzle_node.opacity = 0.0
            return
        blink_off = (self.invuln_timer > 0.0) and (int(self.invuln_timer * 18) & 1)
        op = 0.35 if blink_off else 1.0
        set_pos(self.sprite, self.x, self.y)
        set_scale_x(self.sprite, float(self.facing))
        self.sprite.opacity = op

        gx = self.x + self.facing * (6.0 - self.recoil_offset)
        gy = self.y + 1.0
        set_pos(self.gun_sprite, gx, gy)
        set_scale_x(self.gun_sprite, float(self.facing))
        self.gun_sprite.opacity = op


ENEMY_STATS = {
    "scout": {"hp": 30, "w": 12, "h": 13, "points": 100, "bar_w": 14},
    "drone": {"hp": 24, "w": 12, "h": 11, "points": 120, "bar_w": 14},
    "turret": {"hp": 55, "w": 14, "h": 13, "points": 160, "bar_w": 16},
    "hopper": {"hp": 36, "w": 12, "h": 13, "points": 140, "bar_w": 14},
    "boss": {"hp": 180, "w": 26, "h": 22, "points": 1000, "bar_w": 26},
}


class EnemySlot:
    """One pooled scripted robotic enemy with its own floating pixel health bar."""

    def __init__(self, eid, default_tex):
        self.eid = eid
        self.bit = 1 << eid
        self.alive = False
        self.kind = "scout"
        self.x = -999.0
        self.y = -999.0
        self.base_y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.min_x = 0.0
        self.max_x = 0.0
        self.facing = -1
        self.hp = 30
        self.max_hp = 30
        self.w = 12.0
        self.h = 13.0
        self.points = 100
        self.bar_w = 14.0
        self.ai_timer = 0.0
        self.fire_timer = 1.0
        self.charge_timer = 0.0
        self.anim_timer = 0.0
        self.hit_flash = 0.0

        self.sprite = Sprite2DNode(
            position=Vector2(-999.0, -999.0),
            texture=default_tex,
            transparent_color=TRANSPARENT_KEY,
            frame_count_x=2,
            frame_count_y=1,
            playing=False,
            opacity=0.0,
            layer=9,
        )
        self.hp_bg = Rectangle2DNode(
            position=Vector2(-999.0, -999.0),
            width=16,
            height=4,
            color=COL_HP_BG,
            opacity=0.0,
            layer=16,
        )
        self.hp_fg = Rectangle2DNode(
            position=Vector2(-999.0, -999.0),
            width=14,
            height=2,
            color=COL_HP_HIGH,
            opacity=0.0,
            layer=17,
        )

    def spawn(self, kind, x, y, min_x, max_x, tex):
        st = ENEMY_STATS[kind]
        self.alive = True
        self.kind = kind
        self.x = float(x)
        self.y = float(y)
        self.base_y = float(y)
        self.vx = -22.0 if kind == "scout" else 0.0
        self.vy = 0.0
        self.min_x = float(min_x)
        self.max_x = float(max_x)
        self.facing = -1
        self.hp = st["hp"]
        self.max_hp = st["hp"]
        self.w = float(st["w"])
        self.h = float(st["h"])
        self.points = st["points"]
        self.bar_w = float(st["bar_w"])
        self.ai_timer = random.uniform(0.0, 2.0)
        self.fire_timer = random.uniform(0.7, 1.4)
        self.charge_timer = 0.0
        self.anim_timer = 0.0
        self.hit_flash = 0.0

        self.sprite.texture = tex
        self.sprite.frame_count_x = 2
        self.sprite.frame_current_x = 0
        self.sprite.opacity = 1.0
        self.hp_bg.width = self.bar_w + 2
        self.hp_bg.opacity = 1.0
        self.hp_fg.opacity = 1.0
        self._sync()

    def hide(self):
        self.alive = False
        self.sprite.opacity = 0.0
        set_pos(self.sprite, -999.0, -999.0)
        self.hp_bg.opacity = 0.0
        set_pos(self.hp_bg, -999.0, -999.0)
        self.hp_fg.opacity = 0.0
        set_pos(self.hp_fg, -999.0, -999.0)

    def take_damage(self, dmg, fx, play_sfx):
        if not self.alive:
            return 0
        self.hp -= dmg
        self.hit_flash = 0.10
        fx.spawn_sparks(self.x, self.y, 4, COL_SPARK_CYAN, COL_SPARK_GOLD)
        if self.hp <= 0:
            self.hp = 0
            ex, ey = self.x, self.y
            big = self.kind == "boss"
            pts = self.points
            self.hide()
            fx.spawn_explosion(ex, ey, big=big)
            play_sfx("boom", 2)
            return pts
        play_sfx("hit", 1)
        self._sync()
        return 0

    def _sync(self):
        set_pos(self.sprite, self.x, self.y)
        set_scale_x(self.sprite, 1.0 if self.facing <= 0 else -1.0)
        self.sprite.opacity = 0.45 if self.hit_flash > 0.0 else 1.0

        ratio = max(0.0, self.hp / float(self.max_hp))
        fill_w = max(1.0, self.bar_w * ratio)
        bar_y = self.y - (self.h * 0.5) - 5.0
        set_pos(self.hp_bg, self.x, bar_y)
        left_x = self.x - (self.bar_w * 0.5)
        self.hp_fg.width = fill_w
        set_pos(self.hp_fg, left_x + fill_w * 0.5, bar_y)
        if ratio > 0.6:
            self.hp_fg.color = COL_HP_HIGH
        elif ratio > 0.3:
            self.hp_fg.color = COL_HP_MID
        else:
            self.hp_fg.color = COL_HP_LOW

    def update(self, dt, player, buildings, bullets, fx):
        if not self.alive:
            return
        if self.hit_flash > 0.0:
            self.hit_flash = max(0.0, self.hit_flash - dt)
        self.ai_timer += dt
        self.anim_timer += dt

        dx = player.x - self.x
        dy = player.y - self.y
        in_range = abs(dx) < 94.0

        if self.kind == "scout":
            self.sprite.frame_current_x = int(self.anim_timer * 6.0) & 1
            self.fire_timer -= dt
            if in_range and self.fire_timer <= 0.0:
                self.facing = -1 if dx < 0.0 else 1
                bullets.spawn(
                    self.x + self.facing * 7.0, self.y - 1.0,
                    self.facing * 92.0, 0.0,
                    4, 3, COL_ENEMY_BOLT, 1, 1.2,
                    False, False, COL_SPARK_GOLD,
                )
                self.fire_timer = 1.65
            else:
                self.x += self.vx * dt
                if self.x <= self.min_x:
                    self.x = self.min_x
                    self.vx = abs(self.vx)
                elif self.x >= self.max_x:
                    self.x = self.max_x
                    self.vx = -abs(self.vx)
                self.facing = -1 if self.vx < 0.0 else 1

        elif self.kind == "drone":
            self.sprite.frame_current_x = int(self.anim_timer * 14.0) & 1
            self.y = self.base_y + math.sin(self.ai_timer * 3.4) * 6.0
            if in_range:
                self.facing = -1 if dx < 0.0 else 1
                if abs(dx) > 34.0:
                    self.x += self.facing * 18.0 * dt
                    self.x = max(self.min_x, min(self.max_x, self.x))
                self.fire_timer -= dt
                if self.fire_timer <= 0.0:
                    dist = max(1.0, math.sqrt(dx * dx + dy * dy))
                    spd = 86.0
                    bullets.spawn(
                        self.x, self.y + 3.0,
                        (dx / dist) * spd, (dy / dist) * spd,
                        4, 4, COL_ENEMY_DRONE_BOLT, 1, 1.4,
                        False, False, COL_SPARK_CYAN,
                    )
                    self.fire_timer = 1.85
            else:
                self.x = (self.min_x + self.max_x) * 0.5 + math.sin(self.ai_timer * 1.1) * ((self.max_x - self.min_x) * 0.45)

        elif self.kind == "turret":
            self.facing = -1 if dx < 0.0 else 1
            if in_range:
                if self.charge_timer > 0.0:
                    self.charge_timer -= dt
                    self.sprite.frame_current_x = 1
                    if self.charge_timer <= 0.0:
                        for offset in (0.0, -14.0):
                            bullets.spawn(
                                self.x + self.facing * 8.0, self.y - 2.0,
                                self.facing * 108.0, offset,
                                5, 3, COL_ENEMY_BOLT, 1, 1.25,
                                False, False, COL_SPARK_GOLD,
                            )
                        self.fire_timer = 1.75
                        self.sprite.frame_current_x = 0
                else:
                    self.sprite.frame_current_x = 0
                    self.fire_timer -= dt
                    if self.fire_timer <= 0.0:
                        self.charge_timer = 0.50
            else:
                self.charge_timer = 0.0
                self.sprite.frame_current_x = 0

        elif self.kind == "hopper":
            if self.vy == 0.0 and abs(self.y - self.base_y) < 0.5:
                self.sprite.frame_current_x = 0
                self.fire_timer -= dt
                if in_range and self.fire_timer <= 0.0:
                    self.facing = -1 if dx < 0.0 else 1
                    self.vx = self.facing * 46.0
                    self.vy = -142.0
                    self.fire_timer = 0.95
                    fx.spawn_dust(self.x, self.y + 6.5)
            else:
                self.sprite.frame_current_x = 1
                self.vy += 380.0 * dt
                self.x += self.vx * dt
                self.y += self.vy * dt
                if self.x < self.min_x:
                    self.x = self.min_x
                    self.vx = abs(self.vx) * 0.5
                elif self.x > self.max_x:
                    self.x = self.max_x
                    self.vx = -abs(self.vx) * 0.5
                if self.y >= self.base_y:
                    self.y = self.base_y
                    self.vy = 0.0
                    self.vx = 0.0
                    fx.spawn_dust(self.x, self.y + 6.5)

        elif self.kind == "boss":
            mid_x = (self.min_x + self.max_x) * 0.5
            span_x = (self.max_x - self.min_x) * 0.45
            self.x = mid_x + math.sin(self.ai_timer * 1.15) * span_x
            self.y = self.base_y + math.sin(self.ai_timer * 2.3) * 8.0
            self.facing = -1 if dx < 0.0 else 1
            if abs(dx) < 130.0:
                if self.charge_timer > 0.0:
                    self.charge_timer -= dt
                    self.sprite.frame_current_x = 1
                    if self.charge_timer <= 0.0:
                        base_ang = math.atan2(dy, dx)
                        for spread_a in (-0.28, 0.0, 0.28):
                            a = base_ang + spread_a
                            bullets.spawn(
                                self.x, self.y + 4.0,
                                math.cos(a) * 96.0, math.sin(a) * 96.0,
                                5, 5, COL_BOSS_BOLT, 1, 1.7,
                                False, False, COL_SPARK_PURPLE,
                            )
                        self.fire_timer = 1.45
                        self.sprite.frame_current_x = 0
                else:
                    self.sprite.frame_current_x = int(self.anim_timer * 5.0) & 1
                    self.fire_timer -= dt
                    if self.fire_timer <= 0.0:
                        self.charge_timer = 0.55

        self._sync()


class EnemyManager:
    def __init__(self, enemy_textures, pool_size=10):
        self.textures = enemy_textures
        self.slots = [EnemySlot(i, enemy_textures["scout"]) for i in range(pool_size)]
        self.boss_slot = None

    def clear(self):
        self.boss_slot = None
        for s in self.slots:
            s.hide()

    def load_sector(self, enemy_defs):
        self.clear()
        for i, (kind, x, y, min_x, max_x) in enumerate(enemy_defs):
            if i >= len(self.slots):
                break
            slot = self.slots[i]
            slot.spawn(kind, x, y, min_x, max_x, self.textures[kind])
            if kind == "boss":
                self.boss_slot = slot

    def alive_count(self):
        c = 0
        for s in self.slots:
            if s.alive:
                c += 1
        return c

    def boss_alive(self):
        return self.boss_slot is not None and self.boss_slot.alive

    def update(self, dt, player, buildings, bullets, fx, play_sfx):
        gained_score = 0
        kills = 0
        for s in self.slots:
            if s.alive:
                s.update(dt, player, buildings, bullets, fx)
                if (
                    abs(player.x - s.x) < (Player.HALF_W + s.w * 0.42)
                    and abs(player.y - s.y) < (Player.HALF_H + s.h * 0.42)
                ):
                    player.take_damage(1, fx, play_sfx)

        for b in bullets.items:
            if not b.active:
                continue
            if b.from_player:
                for s in self.slots:
                    if not s.alive:
                        continue
                    if b.pierce and (b.hit_mask & s.bit):
                        continue
                    if (
                        abs(b.x - s.x) < (b.w * 0.5 + s.w * 0.5)
                        and abs(b.y - s.y) < (b.h * 0.5 + s.h * 0.5)
                    ):
                        pts = s.take_damage(b.damage, fx, play_sfx)
                        if pts > 0:
                            gained_score += pts
                            kills += 1
                        if b.pierce:
                            b.hit_mask |= s.bit
                        else:
                            b.hide()
                            break
            else:
                if (
                    abs(b.x - player.x) < (b.w * 0.5 + Player.HALF_W)
                    and abs(b.y - player.y) < (b.h * 0.5 + Player.HALF_H)
                ):
                    player.take_damage(b.damage, fx, play_sfx)
                    b.hide()

        return gained_score, kills
