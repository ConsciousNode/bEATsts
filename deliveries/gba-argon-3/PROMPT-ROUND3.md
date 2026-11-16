# bEATsts GBA, round 3: four small fixes

Round 2 passed Kehai's audit for play-testing (attached `AUDIT.md`). The fuzz differential, the dex and mGBA all agree. Keep everything that's there. Change only the following.

## Fix
1. **Map-change fade.**
   - Port the reference's 0.22 s fade on map change (`transitionTimer`, `07_game_engine.js` ~l.597 / ~l.1492).
   - Hardware blending (BLDCNT/BLDY) is fine, as long as the pixels match the reference's `rgba(10,12,20,a)` overlay after 5-bit quantization.
2. **Battle move flash.**
   - Port the 0.35 s move flash (`animTimer` / `animType`, ~l.1066 / ~l.1552): a 68×68 box at (150,18) in the flame, chill or default color at 0.45 alpha.
3. **bEATdex paging.** LEFT/RIGHT in the bEATdex jump ±10 entries, as in the reference.
4. **Small rendering fixes.**
   - Draw the full credits border box.
   - A dialog with no lines must draw an empty box, not stale text.
   - Find and fix the ≤128 px tile-animation phase differences on interior maps such as `chowder_mart`.
   - `acceptingInput` must not be set before the ROM will actually read the next press.

5. **New reference: dialog paging.** The HTML reference changed after playtesting. Use the attached `beatsts.html` (sha256 `ad4fd025d624eef75b0e96f4c42e0e79d453d6a500a15c027896a1b5e4c669e6`, bEATsts commit `c29912f`) as `beatsts-2.2/beatsts.html`.
   - `showDialog` now splits each entry into 4-line pages (`paginateDialog`, same 27-character wrap). Port that exactly. Before, 388 of 691 NPC lines overflowed the box on the PSP.
   - The keyboard changes in that commit (name-field focus, Tab) are browser-only, so the ROM needs nothing for them.
   - Rebuild every table from the new file and re-record the bot replays against it.

## Tests
- **The pixel differential must not set any reference state before rendering, except `frameCount`** (aligned to the ROM's frame counter). Advance the reference only with its own `update(1/60)`, called once per ROM frame between presses.
  - Remove the overrides of `transitionTimer`, `animTimer`, `moveCooldown`, `bannerTimer` and `creditsScroll`.
- **Random-input pixel coverage.** Add random-input segments to the pixel differential: 400 presses each from 3 checkpoints (mid-game, late-game, post-credits), seeded, using every button. Report per screen type, as raw counts.
- **New positive controls, each of which must fail:**
  - a ROM with no fade;
  - a ROM with no move flash;
  - a ROM where RIGHT doesn't page the dex.
- **`.sav` loading.** Load `.sav` files as SRAM before boot. Don't restore RAM or register snapshots.

## Report
- No claim beyond what a test exercises.
- Every non-matching frame is listed with its cause and left failing.

**Verbatim:** "If a requirement can't be met, or conflicts with another, say so in REPORT.md and leave it failing. Never change emulator or VM accessors, I/O, consoles, test harnesses, or the auditor's scripts to make a check pass. An emulator must never read or write a guest's private memory."
