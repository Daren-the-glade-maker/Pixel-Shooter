# Skyline Strike — Thumby Color 2D Rooftop Platformer Shooter

A pixelated 2D side-scrolling platformer shooter built specifically for the **Thumby Color** (RP2350, 128×128 RGB565 display) using the official **TinyCircuits Tiny Game Engine** MicroPython APIs (`engine_main`, `engine`, `engine_nodes`, `engine_resources`, `engine_draw`, `engine_io`, `engine_math`, `engine_audio`, `engine_save`) — *not* the legacy monochrome `thumby` API.

All combat is strictly **blood-free**: every foe is a rogue security robot that sparks with cyan, gold, white, and steel particles when hit or dismantled.

---

## Features

- **Scrolling City Rooftops:** Leap across city chasms between brownstone brick, neon glass, and steel industrial rooftops with multi-layer parallax skylines, rooftop water towers, AC units (jump-through platforms), antennas, glowing neon signs, and extraction beacons.
- **3 Handcrafted Rooftop Sectors:**
  1. **S1: Dusk Skyline** — Twilight city blocks introducing Patrol Scout Bots and Hover Drones.
  2. **S2: Neon Downtown** — Taller mid-town glass towers with Auto-Turrets and Spring Hoppers.
  3. **S3: Apex Spire** — High-altitude rooftops culminating in the **Sky Sentinel** hovering boss arena.
- **5 Equippable, Visually Distinct Guns** (live sprite rendered both in the player's hands and inside the HUD weapon box):
  | Gun | HUD Tag | Look | Behavior |
  | --- | --- | --- | --- |
  | **Pulse Pistol** | `PSTL` | Sleek white & cyan sidearm | Crisp balanced sidearm (`12 DMG`) |
  | **Neon SMG** | `SMG` | Metallic gunmetal with neon-green capacitor & vertical mag | High-rate automatic spray (`7 DMG`, rapid cooldown) |
  | **Flak Shotgun** | `SHTG` | Wood-tan pump stock with chunky dual steel barrels | 4-pellet wide burst (`9 DMG × 4`) |
  | **Plasma Rifle** | `PLSM` | Cobalt chassis with glowing magenta-violet energy core | Heavy plasma bolts (`24 DMG`) |
  | **Ion Railgun** | `RAIL` | Long white & ice-blue twin-rail sniper rifle | High-velocity **piercing** beam (`34 DMG`) |
- **5 Scripted Robotic Enemy Types with Health Bars:**
  - **Scout Bot** (`30 HP`) — Patrols rooftop ledges and fires aimed energy bolts.
  - **Hover Drone** (`24 HP`) — Sinusoidal hovering flyer that strafes and shoots downward.
  - **Auto-Turret** (`55 HP`) — Heavy rooftop emplacement firing burst volleys.
  - **Spring Hopper** (`36 HP`) — Periodic rooftop jumper that hops toward the player and fires.
  - **Sky Sentinel** (`180 HP`) — Sector 3 hovering boss with figure-8 swoops, 3-way fan salvos, and dedicated boss health bar.
- **Retro Chiptune SFX & Persistent High Score:** Procedural 11 kHz WAV sound effects across 4 audio channels plus persistent best-score saving via `engine_save`.

---

## Controls (Thumby Color)

| Button | Action |
| --- | --- |
| `LEFT` / `RIGHT` | Run & aim horizontally |
| `A` or `UP` | Jump (supports coyote time, jump buffering & variable jump height) |
| `B` | Shoot equipped gun |
| `LB` / `RB` | Cycle through all 5 guns (usable mid-action or on the Pause screen) |
| `MENU` | Pause / inspect weapon stats & swap guns (`B` while paused restarts) |

---

## Project Layout

```text
game/
  manifest.ini        # Thumby Color launcher manifest ("Skyline Strike")
  icon.bmp            # 32x32 16-bit RGB565 launcher icon
  main.py             # Entrypoint (imports engine_main first, launches SkylineGame)
  game.py             # Core SkylineGame loop, FSM, parallax skyline, HUD & overlays
  entities.py         # Pooled FxPool, BulletPool, Player physics & scripted EnemyManager
  weapons.py          # Definitions for all 5 equippable guns
  levels.py           # 3 handcrafted city rooftop sectors
  assets/             # 37 generated BMP sprites/skies + WAV retro SFX (162.7 KB total)
tools/
  generate_assets.py  # Deterministic zero-dependency pixel-art BMP & WAV generator
tests/
  headless_emulator.mjs   # Node.js headless runner for the official Thumby Color WASM simulator
  run_emulator_tests.mjs  # 8-part automated end-to-end emulator test suite + screenshot capture
```

---

## Running on Thumby Color Hardware or Web IDE

1. Copy the contents of `game/` into `/Games/SkylineStrike/` on your Thumby Color (via USB mass storage or the official Thumby Color Code Editor at `https://color.thumby.us/code/`).
2. Select **Skyline Strike** from the Thumby Color launcher (`manifest.ini` points to `main.py` and `icon.bmp`).

---

## Regenerating Pixel Art & Sound Assets

All 37 BMP and WAV assets are deterministically generated with Python's standard library (zero third-party dependencies):

```bash
python3 tools/generate_assets.py
```

---

## Running the Headless Official Thumby Color Emulator Tests

The automated test suite executes the game inside a headless Node.js wrapper around the **official Thumby Color WebAssembly MicroPython simulator** (`micropython.mjs` + `micropython.wasm`) from [`TinyCircuits/TinyCircuits-MicroPython-Editor`](https://github.com/TinyCircuits/TinyCircuits-MicroPython-Editor).

```bash
node tests/run_emulator_tests.mjs
```

On first run, `tests/headless_emulator.mjs` automatically downloads and caches `micropython.mjs` and `micropython.wasm` into `.cache/emulator/`. The suite verifies:

1. `manifest.ini`, 32×32 RGB565 `icon.bmp`, and real `execfile("main.py")` boot using official `engine_*` modules.
2. Title screen rendering and transitioning into Sector 1 gameplay via the `A` button.
3. Cycling and firing all 5 guns via `RB`/`LB`, asserting pairwise visual pixel distinctness.
4. Scripted Scout Bot health reduction, destruction, score increment, and strictly 0 blood-red pixels.
5. 2D scrolling and jumping across a rooftop chasm from Building 0 to Building 1.
6. Pause overlay (`MENU`), weapon swapping while paused, and resuming cleanly.
7. Sector 2 Neon Downtown and Sector 3 Sky Sentinel Boss combat (`180 -> 90 -> 0 HP`) through Extraction to Victory.
8. 300-frame active gameplay soak + `gc.collect()` memory stability check with zero stderr errors.

4× upscaled PNG screenshots of every test phase are saved to `.cache/screenshots/`.
