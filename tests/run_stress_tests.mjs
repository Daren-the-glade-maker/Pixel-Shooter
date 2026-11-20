import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  BUTTONS,
  ThumbyColorHeadlessEmulator,
} from "./headless_emulator.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const GAME_DIR = path.join(ROOT, "game");

async function bootGame() {
  const emu = new ThumbyColorHeadlessEmulator({
    cacheDir: path.join(ROOT, ".cache", "emulator"),
  });
  await emu.init();
  emu.mountDirectory(GAME_DIR, "/Games/SkylineStrike");
  await emu.runPython(`
import gc, sys, os, json, engine_main, engine_save
engine_save._init_saves_dir("/Saves/Games/SkylineStrike")
sys.path.append("/Games/SkylineStrike")
os.chdir("/Games/SkylineStrike")
from game import SkylineGame, STATE_TITLE, STATE_PLAYING, STATE_PAUSED, STATE_SECTOR_CLEAR, STATE_VICTORY, STATE_GAMEOVER
g = SkylineGame(headless_fast=True)
`);
  await stepFrames(emu, 2, 0);
  await stepFrames(emu, 2, BUTTONS.A);
  await stepFrames(emu, 4, 0);
  return emu;
}

async function stepFrames(emu, count, mask = 0) {
  emu.setButtons(mask);
  await emu.runPython(`
for _ in range(${count}):
    g.tick_once()
`);
}

async function evalJson(emu, pyExpr) {
  const beforeLen = emu.stdoutLines.length;
  await emu.runPython(`print("__STATE__" + json.dumps(${pyExpr}))`);
  const line = emu.stdoutLines
    .slice(beforeLen)
    .reverse()
    .find((l) => l.startsWith("__STATE__"));
  if (!line) throw new Error("Missing __STATE__ output");
  return JSON.parse(line.slice("__STATE__".length));
}

async function getState(emu) {
  await emu.runPython("import gc; gc.collect()");
  return evalJson(emu, `{
  "state": g.state,
  "sector": g.sector_idx,
  "hp": g.player.hp,
  "max_hp": g.player.max_hp,
  "score": g.score,
  "best": g.best_score,
  "kills": g.kills,
  "px": round(g.player.x, 2),
  "py": round(g.player.y, 2),
  "on_ground": g.player.on_ground,
  "overcharge": round(g.player.overcharge_timer, 2),
  "gun_idx": g.player.weapon_idx,
  "gun_id": g.player.current_weapon()["id"],
  "mem_free": gc.mem_free(),
}`);
}

async function main() {
  console.log("=== Thumby Color Extended Stress & Edge-Case Test Suite ===\n");

  // 1. Game Over & Restart flow
  {
    console.log("[1/5] Testing Game Over -> Restart flow...");
    const emu = await bootGame();
    await emu.runPython(`
g.score = 450
g.player.hp = 1
g.player.invuln_timer = 0.0
g.player.take_damage(1, g.fx, g.play_sfx)
`);
    await stepFrames(emu, 3, 0);
    const over = await getState(emu);
    assert.equal(over.state, 4, `Expected STATE_GAMEOVER (4), got ${over.state}`);
    assert.equal(over.hp, 0, "Expected HP 0 on game over");

    // Press A to restart
    await stepFrames(emu, 2, BUTTONS.A);
    await stepFrames(emu, 4, 0);
    const restarted = await getState(emu);
    assert.equal(restarted.state, 1, `Expected STATE_PLAYING (1) after restart, got ${restarted.state}`);
    assert.equal(restarted.hp, restarted.max_hp, "Expected full HP after restart");
    assert.equal(restarted.score, 0, "Expected score 0 after restart");
    assert.equal(emu.stderrLines.length, 0, `Unexpected stderr: ${emu.stderrLines.join(" | ")}`);
    console.log(`  PASS: Game Over (hp=0) -> Restarted cleanly (hp=${restarted.hp}, score=${restarted.score})!`);
  }

  // 2. Chasm fall recovery
  {
    console.log("[2/5] Testing chasm fall recovery (no soft-lock, -1 HP)...");
    const emu = await bootGame();
    const before = await getState(emu);
    await emu.runPython(`
g.player.invuln_timer = 0.0
g.player.x = 112.0
g.player.y = 140.0
g.player.on_ground = False
`);
    await stepFrames(emu, 6, 0);
    const after = await getState(emu);
    assert.equal(after.state, 1, "Should still be playing after chasm recovery");
    assert.equal(after.hp, before.hp - 1, `Expected HP ${before.hp - 1}, got ${after.hp}`);
    assert.ok(after.py < 80, `Expected player recovered onto rooftop, got y=${after.py}`);
    assert.equal(emu.stderrLines.length, 0, `Unexpected stderr: ${emu.stderrLines.join(" | ")}`);
    console.log(`  PASS: Chasm fall recovered to (x=${after.px}, y=${after.py}), HP ${before.hp} -> ${after.hp}!`);
  }

  // 3. Pickup collection (med + star overcharge)
  {
    console.log("[3/5] Testing med & overcharge star pickups...");
    const emu = await bootGame();
    await emu.runPython(`
g.player.hp = 3
g.pickups = [
  {"x": g.player.x, "y": g.player.y, "kind": "med", "taken": False},
  {"x": g.player.x + 2.0, "y": g.player.y, "kind": "star", "taken": False},
]
`);
    await stepFrames(emu, 3, 0);
    const st = await getState(emu);
    assert.equal(st.hp, 4, `Expected HP 4 after med pickup, got ${st.hp}`);
    assert.equal(st.score, 250, `Expected score 250 after star pickup, got ${st.score}`);
    assert.ok(st.overcharge > 4.0, `Expected overcharge > 4.0s, got ${st.overcharge}`);
    assert.equal(emu.stderrLines.length, 0, `Unexpected stderr: ${emu.stderrLines.join(" | ")}`);
    console.log(`  PASS: Pickups collected! HP=4, score=250, overcharge=${st.overcharge}s!`);
  }

  // 4. Railgun piercing & Shotgun multi-pellet
  {
    console.log("[4/5] Testing Railgun piercing & Shotgun multi-pellet...");
    const emu = await bootGame();
    await emu.runPython(`
g.player.weapon_idx = 2
g.player.fire_timer = 0.0
g.player.try_fire(g.bullets, g.fx, g.play_sfx)
shotgun_bullets = sum(1 for b in g.bullets.items if b.active)
g.player.weapon_idx = 4
g.player.fire_timer = 0.0
g.player.try_fire(g.bullets, g.fx, g.play_sfx)
rail_pierce = any(b.active and b.pierce for b in g.bullets.items)
`);
    const res = await evalJson(emu, `{"shotgun_bullets": shotgun_bullets, "rail_pierce": rail_pierce}`);
    assert.equal(res.shotgun_bullets, 4, `Expected 4 shotgun pellets, got ${res.shotgun_bullets}`);
    assert.equal(res.rail_pierce, true, "Expected railgun bullet to have pierce=True");
    assert.equal(emu.stderrLines.length, 0, `Unexpected stderr: ${emu.stderrLines.join(" | ")}`);
    console.log(`  PASS: Shotgun spawned ${res.shotgun_bullets} pellets, Railgun pierce=${res.rail_pierce}!`);
  }

  // 5. 600-frame rapid input stress test
  {
    console.log("[5/5] Running 600-frame rapid input stress test...");
    const emu = await bootGame();
    const startMem = (await getState(emu)).mem_free;
    for (let i = 0; i < 60; i++) {
      const mask =
        (i % 2 === 0 ? BUTTONS.RIGHT : BUTTONS.LEFT) |
        (i % 5 === 0 ? BUTTONS.A : 0) |
        BUTTONS.B |
        (i % 10 === 0 ? BUTTONS.RB : 0);
      await stepFrames(emu, 10, mask);
    }
    const endState = await getState(emu);
    const delta = startMem - endState.mem_free;
    assert.equal(emu.stderrLines.length, 0, `Unexpected stderr: ${emu.stderrLines.join(" | ")}`);
    assert.ok(delta < 8192, `Memory delta too large: ${delta} bytes`);
    console.log(`  PASS: 600-frame rapid input stress test passed! mem_free ${startMem} -> ${endState.mem_free} (delta ${delta} B), 0 errors!`);
  }

  console.log("\nALL 5 EXTENDED STRESS TESTS PASSED!");
}

main().catch((err) => {
  console.error("\nSTRESS TEST FAILED:", err);
  process.exit(1);
});
