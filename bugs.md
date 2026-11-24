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
