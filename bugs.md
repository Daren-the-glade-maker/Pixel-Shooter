# Review findings

The original improvements and the additional findings below are each ordered approximately by value. Findings are based on code inspection unless otherwise noted; they have not all been reproduced on hardware.

## 1. Fatal damage can be undone by a med pickup

- **Paths:** `game/game.py:650–690`
- **Problem:** Enemy damage is processed before pickups, but game over is checked afterward. A player at 1 HP who takes a fatal hit while overlapping a med pickup can be healed from 0 to 1 HP and continue playing.
- **Improvement:** Resolve death before collecting pickups and add a regression test for a fatal hit and med pickup on the same frame.

## 2. Rumble may continue after leaving gameplay

- **Paths:** `game/entities.py:326–337, 386–395`; `game/game.py:581–615`
- **Problem:** Rumble is stopped in `Player.update`, which does not run while paused or on the game-over screen. Pausing immediately after damage or taking fatal damage can leave rumble running until gameplay resumes.
- **Improvement:** Stop rumble explicitly on pause, death, and reset; test the transitions with a mock or on hardware.

## 3. Core progression and combat lack end-to-end coverage

- **Paths:** `tests/run_emulator_tests.mjs:343–380`; `tests/run_stress_tests.mjs:141–159`
- **Problem:** The boss test directly loads sectors, teleports the player, calls `take_damage`, and manually awards score. The piercing test checks a flag rather than verifying that a shot hits multiple enemies once each. These tests can pass even if normal gameplay progression or combat is broken.
- **Improvement:** Add input-driven sector transition and boss lock/unlock tests, including combat and scoring. Add collision tests for railgun piercing and shotgun pellets.

## 4. Emulator downloads are not reproducible or integrity-checked

- **Path:** `tests/headless_emulator.mjs:21–58`
- **Problem:** Emulator files are fetched from the upstream default branch and any cached file over 1 KB is accepted. Separate downloads can come from different revisions, while stale or corrupt cache entries can cause confusing failures.
- **Improvement:** Pin both files to the same upstream commit, verify their hashes, and replace downloads atomically.

## 5. Persistent high-score failures are silent and untested across reloads

- **Paths:** `game/game.py:77–83, 371–377`; `tests/run_stress_tests.mjs:75–98`
- **Problem:** Save and load exceptions are swallowed, so the advertised persistent high score can fail without indication. The restart test checks in-memory state, not loading a saved score in a fresh game instance.
- **Improvement:** Test saving and reloading across game instances, and make failures observable while preserving a graceful fallback.

## 6. Emulator memory checks do not establish hardware viability

- **Paths:** `tests/headless_emulator.mjs:183–189`; `tests/run_emulator_tests.mjs:393–401`
- **Problem:** The emulator heap combines SRAM and flash scratch, and the test requires over 2 MB free. This checks emulator stability but does not prove the game fits or performs well on the target device.
- **Improvement:** Document hardware memory and frame-rate measurements or add a target-representative test, including repeated sector changes.

## 7. A full projectile pool silently replaces active bullets

- **Paths:** `game/entities.py:205–213`; `game/game.py:183–186`
- **Problem:** Player and enemy projectiles share an 18-slot pool. When full, a new shot replaces an active bullet regardless of ownership, potentially causing shots to disappear unexpectedly during dense combat.
- **Improvement:** Define an explicit saturation policy and test it under boss and shotgun fire.

## 8. Test and setup documentation is incomplete

- **Paths:** `README.md:46–62, 84–101`; `tests/run_emulator_tests.mjs:73–86`
- **Problem:** The README omits the existing stress-test command and Node/network prerequisites. It describes a real `execfile("main.py")` boot, but the test reads and modifies the source before executing it. The distinction between simulator coverage and hardware validation is also important.
- **Improvement:** Document both test commands and prerequisites, accurately describe the bootstrap test and hardware coverage, and add CI for both suites against a pinned emulator.

# Additional findings

## 9. Restarting from pause discards a potential high score

- **Paths:** `game/game.py:371–377, 468–475, 581–593, 690–691, 724–725`
- **Problem:** Pressing B on the pause screen calls `_start_new_game()`, which immediately resets the score. `_save_best()` is only called on game over or victory, so a run that has already beaten the high score is discarded if the player restarts from pause.
- **Improvement:** Save the current best before discarding a run, and test that a pause restart preserves a new record across reloads.

## 10. Falling while invulnerable bypasses the chasm penalty

- **Paths:** `game/entities.py:326–330, 501–511`; `tests/run_stress_tests.mjs:101–117`
- **Problem:** Chasm recovery calls `take_damage`, which ignores damage while the player is invulnerable, and then returns the player to safety anyway. A player who falls soon after being hit can recover without the documented one-HP penalty. The existing test explicitly clears invulnerability and does not cover this case.
- **Improvement:** Decide whether falls should bypass combat invulnerability; if the intended penalty is unconditional, apply it separately and test falls both during and outside invulnerability. Confirmed with a local Python stub of the engine APIs; not verified on hardware.

## 11. Weapon switching shortens the firing cooldown

- **Paths:** `game/entities.py:315–319, 341–346`; `game/game.py:623–645`
- **Problem:** Equipping any weapon clamps the current firing timer to 0.05 seconds. Alternating weapons while holding fire can bypass much of a slow weapon's cooldown, such as the railgun's 0.62 seconds, changing balance and increasing projectile load.
- **Improvement:** Preserve a deliberate shared cooldown or track cooldowns per weapon, and test rapid weapon switching after firing. The timer reduction was confirmed with local engine API stubs.

## 12. Restarting or changing sectors can leave a muzzle flash stuck on

- **Paths:** `game/entities.py:295–313, 348–359, 402–405, 526–542`; `game/game.py:419–449, 468–475`
- **Problem:** `Player.reset()` sets `muzzle_timer` to zero but does not hide `muzzle_node`. If a reset occurs while the flash is visible, the normal expiry branch will never run, leaving the flash visible at its old position until another shot updates it.
- **Improvement:** Clear the muzzle node's opacity and position during reset, and test a reset immediately after firing. The retained opacity was confirmed with local engine API stubs.

## 13. Camera shake strength never resets after a stronger effect

- **Paths:** `game/game.py:87–90, 485–492, 569–570, 644–656`
- **Problem:** New effects use `max(self.shake_mag, ...)`, but expiry only resets the timer, not the magnitude. After a strong effect, weaker effects reuse its strength for the rest of the game instance, including after restarting a run.
- **Improvement:** Reset the magnitude when shake expires or start a new shake with the new effect's magnitude; test strong-then-weak effects and restart behavior.

# Link cable and Endless mode findings

These findings refer to GitHub `main` at commit `45322232d819aa1d217f2ac73d71e41c1b84c661`, not the older checkout on this branch. Paths and line numbers below are from that revision. Checks noted below used CPython or API stubs; two-device hardware behavior has not been verified.

## 14. Link sends the wrong buffer type, silently preventing synchronization

- **Paths:** `Skyline-Strike/link.py:73–107`; `tests/run_stress_tests.mjs:320–344`
- **Problem:** `struct.pack()` produces `bytes`, but the official Tiny Game Engine's `engine_link.send()` requires a `bytearray` and raises on other types ([upstream implementation](https://github.com/TinyCircuits/TinyCircuits-Tiny-Game-Engine/blob/main/src/link/engine_link_module.c)). The exception is swallowed before the receive loop runs, so two real devices cannot exchange state. The loopback mock accepts `bytes` and misses this mismatch.
- **Improvement:** Send a `bytearray`, expose communication errors, and test against an API-faithful mock and two devices. Confirmed with a strict local API stub; the hardware test remains outstanding.

## 15. Endless beacon coordinates are swapped, blocking progression

- **Paths:** `Skyline-Strike/levels.py:277–298`; `Skyline-Strike/game.py:889–896`; `Skyline-Strike/entities.py:518–528`
- **Problem:** Buildings are `(x, width, roof_y, style)`, but the last building is unpacked as `(last_x, last_y, last_w, _)`. The beacon consequently uses the roof height as its horizontal offset and the width as its vertical coordinate. For chunk 0 the final building is `(548, 156, 32, 0)` but the beacon is `(562, 156)`; the player is recovered from a fall at y > 92 and cannot reach the beacon's trigger height.
- **Improvement:** Unpack the building in the documented order and test reaching the beacon and advancing through generated chunks. Confirmed by executing the generator under CPython.

## 16. Endless rendering indexes past the Adventure sector list

- **Paths:** `Skyline-Strike/game.py:628–636, 732–743, 896–899`; `Skyline-Strike/levels.py:12–246`
- **Problem:** The beacon renderer always reads `SECTORS[self.sector_idx]` to decide whether the boss is alive. Endless mode increments the same index without a bound. Once chunk 7's beacon is rendered, index 6 exceeds the six Adventure sectors and raises `IndexError`. Earlier Endless chunks also use the Adventure sector's boss flag rather than their own for beacon appearance.
- **Improvement:** Use the loaded chunk's boss flag in the renderer, and test progression beyond the Adventure sector count. This is a code-path finding; the beacon issue above currently blocks normal progression first.

## 17. Link mode does not synchronize combat or game state

- **Paths:** `Skyline-Strike/link.py:73–105`; `Skyline-Strike/game.py:801–837`; `Skyline-Strike/entities.py:887–929`
- **Problem:** Each device updates its own enemies and bullets against only its local player. Received position is used to draw a remote sprite, while received firing, weapon, HP and score do not drive combat or a shared world. Consequently one player's shots do not damage the other device's enemies, and enemy deaths, pickups and player outcomes can diverge. Advancing sectors only copies the higher index, not the world state.
- **Improvement:** Define authoritative/shared gameplay semantics and synchronize the necessary events or state; add a two-peer test covering shots, kills, damage, pickups and progression.

## 18. Link packet stream cannot recover from partial sends or lost bytes

- **Paths:** `Skyline-Strike/link.py:91–107`; `tests/run_stress_tests.mjs:325–335`
- **Problem:** The sender ignores the byte count returned by `send()`. The receiver consumes fixed-size blocks and discards any block without the `SK` header, without searching for the next header. A partial send or overwritten/lost byte can permanently misalign subsequent packets. The mock always accepts the full packet and never introduces fragmentation or loss.
- **Improvement:** Handle partial writes, buffer input and resynchronize on packet boundaries, with suitable validation and tests for fragmentation, loss and reconnects.

## 19. Disconnection leaves a stale remote player onscreen

- **Paths:** `Skyline-Strike/link.py:25, 51–61, 91–107`; `Skyline-Strike/game.py:815–837`
- **Problem:** `remote_seen` is set on receipt but is not cleared when the cable disconnects or packets stop arriving. Gameplay continues to display the last remote position indefinitely, with no disconnect indication or recovery policy.
- **Improvement:** Track connection changes and packet freshness, hide or mark stale peers, and test unplug/reconnect during play.

## 20. Endless boss selection is discarded

- **Paths:** `Skyline-Strike/levels.py:248–267, 297–310`; `Skyline-Strike/game.py:481–484, 327–338`
- **Problem:** The generator chooses a boss name and HP but does not return either. Loading the chunk therefore always falls back to 180 HP, and the boss bar remains labeled `SKY SENTINEL`. The ten named boss entries do not produce their intended names or health values.
- **Improvement:** Return and apply the selected boss metadata and test all choices through generation, loading and HUD display. Confirmed the generated dictionary has no boss metadata beyond `has_boss`.

## 21. Regenerating the current Endless chunk resets global randomness every frame

- **Paths:** `Skyline-Strike/levels.py:262–267`; `Skyline-Strike/game.py:456–458, 889–890`; `Skyline-Strike/entities.py:96–104`
- **Problem:** The generator calls global `random.seed()`, and `_current_sec()` regenerates the chunk during each playing frame. This repeatedly resets the random stream used for effects and weapon spread, while allocating a full chunk every frame on a constrained device.
- **Improvement:** Generate and cache the chunk once per transition and isolate generation randomness from gameplay randomness. Repeated generation was confirmed to leave CPython's global RNG at the same state; profile and verify behavior on the target MicroPython runtime.

## 22. Endless coins and upgrades carry over into a new run

- **Paths:** `Skyline-Strike/game.py:114–118, 526–544, 690–714`
- **Problem:** Coins and upgrade levels are initialized only when the game object is created. `_start_new_game()` resets score, kills and chunk but not either upgrade state or coins, so retrying after game over starts the next run with the previous run's resources.
- **Improvement:** Define whether these are intentionally persistent between runs; if not, reset them on a new run and test the game-over retry flow. If persistence is intended, document and save it consistently.
