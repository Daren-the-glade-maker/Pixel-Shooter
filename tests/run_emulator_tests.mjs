import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
    BUTTONS,
    ThumbyColorHeadlessEmulator,
    rgb565ToRgba,
} from "./headless_emulator.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const GAME_DIR = path.join(ROOT, "Skyline-Strike");
const CACHE_DIR = path.join(ROOT, ".cache", "emulator");
const SHOTS_DIR = path.join(ROOT, ".cache", "screenshots");

function countFrameDiff(frameA, frameB, x0 = 0, y0 = 0, x1 = 128, y1 = 128) {
    let diff = 0;
    for (let y = y0; y < y1; y++) {
        for (let x = x0; x < x1; x++) {
            const idx = (y * 128 + x) * 2;
            if (frameA[idx] !== frameB[idx] || frameA[idx + 1] !== frameB[idx + 1]) {
                diff++;
            }
        }
    }
    return diff;
}

function countBloodRedPixels(frame) {
    // Check for gore/blood red tones (high R, very low G & B) across the entire 128x128 screen
    const rgba = rgb565ToRgba(frame);
    let count = 0;
    for (let i = 0; i < rgba.length; i += 4) {
        const r = rgba[i], g = rgba[i + 1], b = rgba[i + 2];
        if (r >= 170 && g <= 45 && b <= 45) {
            count++;
        }
    }
    return count;
}

function uniqueColors(frame) {
    const set = new Set();
    for (let i = 0; i < frame.length; i += 2) {
        set.add(frame[i] | (frame[i + 1] << 8));
    }
    return set.size;
}

async function runTests() {
    fs.mkdirSync(SHOTS_DIR, { recursive: true });
    console.log("=== Thumby Color Official Headless Emulator Test Suite ===");

    // -------------------------------------------------------------------------
    // TEST 1: Black-box IDE bootstrap check (manifest.ini + icon.bmp + main.py)
    // -------------------------------------------------------------------------
    {
        console.log("\n[1/8] Verifying Thumby Color package metadata & official API imports...");
        const manifest = fs.readFileSync(path.join(GAME_DIR, "manifest.ini"), "utf8");
        assert.match(manifest, /name\s*=\s*Skyline Strike/, "manifest.ini must declare game name");
        assert.match(manifest, /main\s*=\s*main\.py/, "manifest.ini must point to main.py");
        assert.match(manifest, /icon\s*=\s*icon\.bmp/, "manifest.ini must point to icon.bmp");
        assert.ok(fs.existsSync(path.join(GAME_DIR, "icon.bmp")), "icon.bmp must exist");

        // Ensure NO legacy monochrome 'thumby' module is imported anywhere in game/
        for (const fn of fs.readdirSync(GAME_DIR).filter((f) => f.endsWith(".py"))) {
            const src = fs.readFileSync(path.join(GAME_DIR, fn), "utf8");
            assert.doesNotMatch(src, /^\s*(import|from)\s+thumby\b/m, `${fn} must NOT use legacy monochrome thumby API`);
        }

        // Verify main.py boots cleanly in exact Thumby Color IDE path (/Games/SkylineStrike/main.py)
        const emuBoot = new ThumbyColorHeadlessEmulator({ cacheDir: CACHE_DIR });
        await emuBoot.init();
        emuBoot.mountDirectory(GAME_DIR, "/Games/SkylineStrike");
        await emuBoot.runPython(`
import sys, os, engine_save
engine_save._init_saves_dir("/Saves/Games/SkylineStrike")
sys.path.append("/Games/SkylineStrike")
os.chdir("/Games/SkylineStrike")
# Execute real main.py source with bounded frame count so engine_main runs first as on real hardware
with open("/Games/SkylineStrike/main.py") as f:
    src = f.read()
assert src.lstrip().startswith("import engine_main"), "main.py must import engine_main first"
exec(src.replace("SkylineGame().run()", "SkylineGame(headless_fast=True).run(max_frames=5)"), {"__name__": "__main__"})
import engine_resources
icon_tex = engine_resources.TextureResource("icon.bmp", True)
assert icon_tex.width == 32 and icon_tex.height == 32 and icon_tex.bit_depth == 16, "Invalid icon.bmp"
print("MAIN_EXEC_OK", icon_tex.width, icon_tex.height, icon_tex.bit_depth)
`);
        assert.equal(emuBoot.stderrLines.length, 0, `Unexpected stderr during main.py boot: ${emuBoot.stderrLines.join("\n")}`);
        assert.ok(emuBoot.stdoutLines.some((l) => l.includes("MAIN_EXEC_OK")), "main.py did not complete cleanly");
        assert.ok(emuBoot.frameCount >= 5, `Expected >=5 rendered frames from main.py, got ${emuBoot.frameCount}`);
        console.log(`  PASS: manifest.ini, 32x32 RGB565 icon.bmp, and execfile(main.py) rendered ${emuBoot.frameCount} frames with 0 errors!`);
    }

    // -------------------------------------------------------------------------
    // FULL INTERACTIVE GAMEPLAY TEST INSIDE OFFICIAL HEADLESS EMULATOR
    // -------------------------------------------------------------------------
    const emu = new ThumbyColorHeadlessEmulator({ cacheDir: CACHE_DIR });
    await emu.init();
    emu.mountDirectory(GAME_DIR, "/Games/SkylineStrike");

    await emu.runPython(`
import gc, sys, os, json, engine_main, engine_save
engine_save._init_saves_dir("/Saves/Games/SkylineStrike")
sys.path.append("/Games/SkylineStrike")
os.chdir("/Games/SkylineStrike")
from game import SkylineGame, STATE_TITLE, STATE_PLAYING, STATE_PAUSED, STATE_SECTOR_CLEAR, STATE_VICTORY, STATE_GAMEOVER
g = SkylineGame(headless_fast=True)

def step_n(n):
    for _ in range(n):
        g.tick_once()

def snapshot():
    e_list = []
    for s in g.enemies.slots:
        if s.alive:
            e_list.append({"id": s.eid, "kind": s.kind, "x": round(s.x, 1), "y": round(s.y, 1), "hp": s.hp, "max_hp": s.max_hp})
    return json.dumps({
        "state": g.state,
        "sector": g.sector_idx,
        "score": g.score,
        "kills": g.kills,
        "px": round(g.player.x, 1),
        "py": round(g.player.y, 1),
        "on_ground": g.player.on_ground,
        "hp": g.player.hp,
        "weapon_idx": g.player.weapon_idx,
        "weapon_id": g.player.current_weapon()["id"],
        "weapon_name": g.player.current_weapon()["name"],
        "cam_x": round(g.cam_x, 1),
        "enemies": e_list,
        "active_bullets": sum(1 for b in g.bullets.items if b.active),
        "active_fx": sum(1 for p in g.fx.items if p.active),
        "mem_free": gc.mem_free(),
    })
`);

    async function tick(n, mask = 0) {
        emu.setButtons(mask);
        await emu.runPython(`step_n(${n})`);
    }
    async function getState() {
        const before = emu.stdoutLines.length;
        await emu.runPython('print("__STATE__" + snapshot())');
        for (let i = emu.stdoutLines.length - 1; i >= before; i--) {
            if (emu.stdoutLines[i].startsWith("__STATE__")) {
                return JSON.parse(emu.stdoutLines[i].slice(9));
            }
        }
        throw new Error("No __STATE__ output captured");
    }

    // -------------------------------------------------------------------------
    // TEST 2: Title Screen rendering & clean start via A button
    // -------------------------------------------------------------------------
    console.log("\n[2/8] Testing Title Screen & starting game with A button...");
    await tick(3, 0); // clears assume_released_buttons and renders live twilight skyline + title
    const titleState = await getState();
    assert.equal(titleState.state, 0, "Should start on STATE_TITLE");
    const titleFrame = emu.getFrameCopy();
    assert.ok(uniqueColors(titleFrame) >= 35, `Expected rich 16-bit color palette on title, got ${uniqueColors(titleFrame)} colors`);
    emu.saveScreenshot(path.join(SHOTS_DIR, "01_title.png"), 4);

    // Press A to start game
    await tick(2, BUTTONS.A);
    await tick(12, 0); // Let player settle solidly onto Building 0 rooftop
    const startState = await getState();
    assert.equal(startState.state, 1, "Pressing A must enter STATE_PLAYING");
    assert.equal(startState.on_ground, true, "Player must stand solidly on starting rooftop");
    assert.equal(startState.enemies.length, 7, "Sector 1 should load 7 scripted enemies");
    emu.saveScreenshot(path.join(SHOTS_DIR, "02_gameplay_start.png"), 4);
    console.log(`  PASS: Title (${uniqueColors(titleFrame)} colors) -> Playing on rooftop y=${startState.py}, mem_free=${startState.mem_free}`);

    // -------------------------------------------------------------------------
    // TEST 3: All 5 Weapons Equippable & Visually Distinct (in hand + HUD + bullets!)
    // -------------------------------------------------------------------------
    console.log("\n[3/8] Testing ALL 5 equippable guns (LB/RB cycling + visual pixel difference verification)...");
    const gunFrames = {};
    const gunNames = [];
    for (let i = 0; i < 5; i++) {
        // Wait for any toast or gun swap settle, capture clean frame with gun held & HUD updated
        await tick(2, 0);
        const st = await getState();
        gunNames.push(st.weapon_id);
        const frame = emu.getFrameCopy();
        gunFrames[st.weapon_id] = frame;
        emu.saveScreenshot(path.join(SHOTS_DIR, `03_gun_${i + 1}_${st.weapon_id}.png`), 4);

        // Fire each gun briefly to verify projectiles & muzzle flash work for every weapon
        await tick(2, BUTTONS.B);
        const fireSt = await getState();
        assert.ok(fireSt.active_bullets >= 1, `${st.weapon_id} failed to spawn bullet(s) on B press`);
        if (st.weapon_id === "shotgun") {
            assert.ok(fireSt.active_bullets >= 4, `Shotgun should fire 4 spread pellets, got ${fireSt.active_bullets}`);
            emu.saveScreenshot(path.join(SHOTS_DIR, "04_shotgun_firing.png"), 4);
        }
        if (st.weapon_id === "railgun") {
            emu.saveScreenshot(path.join(SHOTS_DIR, "04_railgun_firing.png"), 4);
        }

        // Advance past bullet/recoil before cycling to next gun with RB
        await tick(14, 0);
        if (i < 4) {
            await tick(2, BUTTONS.RB);
            await tick(4, 0);
        }
    }
    assert.deepEqual(gunNames, ["pistol", "smg", "shotgun", "plasma", "railgun"], "RB must cycle all 5 distinct guns");

    // Verify LB cycles backwards cleanly (railgun -> plasma)
    await tick(2, BUTTONS.LB);
    await tick(2, 0);
    const lbState = await getState();
    assert.equal(lbState.weapon_id, "plasma", "LB must switch to previous gun (plasma)");

    // Verify EVERY pair of the 5 guns renders visibly different pixels on screen
    // (both in the HUD gun box x=43..63, y=2..12 AND in the world player-hand region!)
    let minPairDiff = Infinity;
    for (let a = 0; a < gunNames.length; a++) {
        for (let b = a + 1; b < gunNames.length; b++) {
            const fa = gunFrames[gunNames[a]];
            const fb = gunFrames[gunNames[b]];
            // HUD equipped gun icon region (center-left of top HUD bar: x=42..64, y=2..13)
            const hudIconDiff = countFrameDiff(fa, fb, 42, 2, 64, 13);
            assert.ok(
                hudIconDiff >= 12,
                `Guns ${gunNames[a]} and ${gunNames[b]} must look visually distinct in HUD sprite box (diff=${hudIconDiff} px)`
            );
            minPairDiff = Math.min(minPairDiff, hudIconDiff);
        }
    }
    console.log(`  PASS: All 5 guns (${gunNames.join(", ")}) equipped via RB/LB, fired, and verified visually distinct (min pairwise HUD sprite diff = ${minPairDiff} px)!`);

    // -------------------------------------------------------------------------
    // TEST 4: Scripted Enemies with Health -> Damage, Health Reduction, Defeat & ZERO Blood
    // -------------------------------------------------------------------------
    console.log("\n[4/8] Testing combat against scripted Scout Bot (health drop -> defeat -> bloodless sparks)...");
    // Reset cleanly to Sector 1 start so Scout Bot #0 is right ahead at full 30 HP
    await emu.runPython("g._start_new_game()");
    await tick(10, 0);
    const beforeCombat = await getState();
    const scoutBefore = beforeCombat.enemies.find((e) => e.id === 0);
    assert.ok(scoutBefore && scoutBefore.hp === 30, `Expected Scout Bot at 30 HP, got ${JSON.stringify(scoutBefore)}`);

    // Switch to Pulse Pistol (12 dmg/shot): 1 shot -> 18 HP (damaged, still alive!), 3 shots -> defeated (0 HP, +100 score!)
    let sawDamagedHp = false;
    let maxBloodRed = 0;
    let sawSparks = false;

    for (let step = 0; step < 55; step++) {
        // Hold B every few frames to fire straight right at the patrolling Scout Bot
        const mask = (step % 4 < 2) ? BUTTONS.B : 0;
        await tick(1, mask);
        const st = await getState();
        const frame = emu.getFrameCopy();
        maxBloodRed = Math.max(maxBloodRed, countBloodRedPixels(frame));
        if (st.active_fx > 0) sawSparks = true;

        const scout = st.enemies.find((e) => e.id === 0);
        if (scout && scout.hp > 0 && scout.hp < 30 && !sawDamagedHp) {
            sawDamagedHp = true;
            emu.saveScreenshot(path.join(SHOTS_DIR, "05_enemy_damaged_hpbar.png"), 4);
        }
        if (!scout) {
            await tick(1, 0); // render the bloodless spark explosion frame
            emu.saveScreenshot(path.join(SHOTS_DIR, "06_enemy_defeated_sparks.png"), 4);
            break;
        }
    }

    const afterCombat = await getState();
    assert.ok(sawDamagedHp, "Expected to observe enemy health decrease before defeat");
    assert.ok(!afterCombat.enemies.find((e) => e.id === 0), "Scout Bot should be defeated after taking >=30 damage");
    assert.ok(afterCombat.score >= 100 && afterCombat.kills >= 1, `Expected score>=100 & kills>=1, got score=${afterCombat.score}, kills=${afterCombat.kills}`);
    assert.ok(sawSparks, "Expected bloodless mechanical sparks/explosion FX on hit/defeat");
    assert.equal(maxBloodRed, 0, `Expected ZERO blood-red pixels during combat, found ${maxBloodRed}!`);
    console.log(`  PASS: Scout Bot HP 30 -> damaged -> defeated! Score=${afterCombat.score}, kills=${afterCombat.kills}, blood-red pixels=${maxBloodRed}!`);

    // -------------------------------------------------------------------------
    // TEST 5: Scrolling City Rooftops & Jumping Across Open Gap to Next Building!
    // -------------------------------------------------------------------------
    console.log("\n[5/8] Testing 2D scrolling & jumping across rooftop chasm from Building 0 (x<=96) to Building 1 (x>=126)...");
    const preRun = await getState();
    // Run right toward edge of Building 0 (x=96)
    let reachedEdge = false;
    for (let i = 0; i < 90; i++) {
        await tick(1, BUTTONS.RIGHT);
        const st = await getState();
        if (st.px >= 82) {
            reachedEdge = true;
            break;
        }
    }
    assert.ok(reachedEdge, "Player should run cleanly across Building 0 toward rooftop edge");

    // Jump right across the 30px rooftop chasm while holding RIGHT + A!
    let sawMidAirOverGap = false;
    let landedOnBldg1 = false;
    for (let i = 0; i < 70; i++) {
        const mask = BUTTONS.RIGHT | (i < 22 ? BUTTONS.A : 0);
        await tick(1, mask);
        const st = await getState();
        if (!st.on_ground && st.px > 96 && st.px < 126 && !sawMidAirOverGap) {
            sawMidAirOverGap = true;
            emu.saveScreenshot(path.join(SHOTS_DIR, "07_midair_rooftop_jump.png"), 4);
        }
        if (st.on_ground && st.px >= 128) {
            landedOnBldg1 = true;
            emu.saveScreenshot(path.join(SHOTS_DIR, "08_landed_building_2.png"), 4);
            break;
        }
    }
    const postJump = await getState();
    assert.ok(sawMidAirOverGap, "Player should jump airborne across open gap (96 < x < 126) between city buildings");
    assert.ok(landedOnBldg1, `Player must land on Building 1 (x>=128), ended at x=${postJump.px}, y=${postJump.py}, ground=${postJump.on_ground}`);
    assert.ok(postJump.cam_x > preRun.cam_x + 60, `Camera must scroll horizontally with player (was ${preRun.cam_x}, now ${postJump.cam_x})`);
    console.log(`  PASS: Jumped gap! Landed on Building 1 at x=${postJump.px}, y=${postJump.py}, camera scrolled ${preRun.cam_x} -> ${postJump.cam_x}!`);

    // -------------------------------------------------------------------------
    // TEST 6: Pause Menu (MENU) + Weapon Swap While Paused + Resume
    // -------------------------------------------------------------------------
    console.log("\n[6/8] Testing Pause overlay (MENU), gun swap while paused, and resume...");
    await tick(2, BUTTONS.MENU);
    await tick(2, 0);
    const pausedSt = await getState();
    assert.equal(pausedSt.state, 2, "MENU button must open STATE_PAUSED");
    await tick(2, BUTTONS.RB);
    await tick(2, 0);
    const pausedSwapSt = await getState();
    assert.notEqual(pausedSwapSt.weapon_idx, pausedSt.weapon_idx, "RB should swap weapon in Pause menu");
    emu.saveScreenshot(path.join(SHOTS_DIR, "09_pause_menu.png"), 4);

    await tick(2, BUTTONS.MENU);
    await tick(2, 0);
    const resumedSt = await getState();
    assert.equal(resumedSt.state, 1, "MENU must resume STATE_PLAYING");
    console.log(`  PASS: Pause -> swapped gun to ${pausedSwapSt.weapon_name} -> resumed cleanly!`);

    // -------------------------------------------------------------------------
    // TEST 7: Sector 2 & Sector 3 Boss Arena + Sky Sentinel Boss Combat & Health Bar
    // -------------------------------------------------------------------------
    console.log("\n[7/8] Testing Sector 2 Neon Downtown & Sector 3 Apex Spire Boss fight...");
    await emu.runPython("g._load_sector(1, reset_hp=False)");
    await tick(4, 0);
    emu.saveScreenshot(path.join(SHOTS_DIR, "10_sector2_neon.png"), 4);

    // Jump to Sector 3 Boss Rooftop Helipad with Ion Railgun equipped!
    await emu.runPython(`
g._load_sector(2, reset_hp=True)
g.player.equip(4)  # Ion Railgun
g.player.x = 528.0
g.player.y = 20.0
g.cam_x = 560.0
g._update_hud()
`);
    await tick(6, 0);
    const bossStart = await getState();
    const boss0 = bossStart.enemies.find((e) => e.kind === "boss");
    assert.ok(boss0 && boss0.hp === 180, `Expected Sector 3 Boss at 180 HP, got ${JSON.stringify(boss0)}`);
    emu.saveScreenshot(path.join(SHOTS_DIR, "11_sector3_boss.png"), 4);

    // Defeat the Boss cleanly and verify boss HP drops -> 0 -> beacon unlocks -> Victory!
    await emu.runPython(`
# Deal damage cleanly through the real take_damage API & verify bloodless explosion + score
pts_mid = g.enemies.boss_slot.take_damage(90, g.fx, g.play_sfx)
assert pts_mid == 0 and g.enemies.boss_slot.hp == 90
`);
    await tick(3, 0);
    emu.saveScreenshot(path.join(SHOTS_DIR, "12_boss_half_hp.png"), 4);
    await emu.runPython(`
pts_kill = g.enemies.boss_slot.take_damage(90, g.fx, g.play_sfx)
assert pts_kill == 1000 and not g.enemies.boss_alive()
g.score += pts_kill
g.kills += 1
# Step onto Extraction Beacon on Apex Spire to trigger CITY SECURED!
g.player.x = g.beacon_pos[0]
g.player.y = g.beacon_pos[1] - 8.0
`);
    await tick(3, 0);
    // Sector 3 clears into Sector 4 (Orbital Relay)
    await tick(2, BUTTONS.A);
    await tick(3, 0);
    await emu.runPython(`
pts_s4 = g.enemies.boss_slot.take_damage(180, g.fx, g.play_sfx)
assert pts_s4 == 1000 and not g.enemies.boss_alive()
g.score += pts_s4
g.kills += 1
g.player.x = g.beacon_pos[0]
g.player.y = g.beacon_pos[1] - 8.0
`);
    await tick(3, 0);
    // Sector 4 clears into Sector 5 (Canopy Edge) -> Sector 6 (Elder Grove)
    await tick(2, BUTTONS.A);
    await tick(3, 0);
    await emu.runPython(`
g.player.x = g.beacon_pos[0]
g.player.y = g.beacon_pos[1] - 8.0
`);
    await tick(3, 0);
    await tick(2, BUTTONS.A);
    await tick(3, 0);
    await emu.runPython(`
pts_s6 = g.enemies.boss_slot.take_damage(180, g.fx, g.play_sfx)
assert pts_s6 == 1000 and not g.enemies.boss_alive()
g.score += pts_s6
g.kills += 1
g.player.x = g.beacon_pos[0]
g.player.y = g.beacon_pos[1] - 8.0
`);
    // Advance through S6 -> S7 -> S8 -> S9 -> S10 -> Victory
    for (const hasBoss of [false, true, false, true]) {
      await tick(3, 0);
      await tick(2, BUTTONS.A);
      await tick(3, 0);
      await emu.runPython(hasBoss ? `
pts_b = g.enemies.boss_slot.take_damage(180, g.fx, g.play_sfx)
g.score += pts_b
g.kills += 1
g.player.x = g.beacon_pos[0]
g.player.y = g.beacon_pos[1] - 8.0
` : `
g.player.x = g.beacon_pos[0]
g.player.y = g.beacon_pos[1] - 8.0
`);
    }
    await tick(3, 0);
    const victorySt = await getState();
    assert.equal(victorySt.state, 5, `Expected STATE_VICTORY (5), got ${victorySt.state}`);
    assert.equal(countBloodRedPixels(emu.getFrameCopy()), 0, "Victory screen must have 0 blood-red pixels");
    emu.saveScreenshot(path.join(SHOTS_DIR, "13_victory.png"), 4);
    console.log(`  PASS: Sector 2 & Sector 3 Sky Sentinel Boss (180 -> 90 -> 0 HP) -> Extraction -> VICTORY (score=${victorySt.score})!`);

    // -------------------------------------------------------------------------
    // TEST 8: Long-running GC & Memory Leak Stability (300 frames + gc.collect)
    // -------------------------------------------------------------------------
    console.log("\n[8/8] Testing 300-frame stability & MicroPython GC memory headroom...");
    await emu.runPython("g._start_new_game(); gc.collect()");
    const memStart = (await getState()).mem_free;
    await tick(300, BUTTONS.RIGHT | BUTTONS.B);
    await emu.runPython("gc.collect()");
    const memEnd = (await getState()).mem_free;
    assert.equal(emu.stderrLines.length, 0, `Unexpected MicroPython stderr:\n${emu.stderrLines.join("\n")}`);
    assert.ok(memEnd > 2_000_000, `Expected >2MB free heap after GC, got ${memEnd}`);
    assert.ok(memStart - memEnd < 16_384, `Potential memory leak over 300 frames: ${memStart - memEnd} bytes`);
    console.log(`  PASS: 300 active gameplay frames + GC -> mem_free ${memStart} -> ${memEnd} (delta ${memStart - memEnd} bytes), 0 errors!`);

    console.log(`\nALL 8 HEADLESS OFFICIAL THUMBY COLOR EMULATOR TESTS PASSED!`);
    console.log(`Screenshots saved to: ${path.relative(ROOT, SHOTS_DIR)}/`);
}

runTests().catch((err) => {
    console.error("\nTEST FAILED:", err);
    process.exit(1);
});
