# bEATsts GBA, Argon round 2: Kehai's audit

Delivery committed as delivered in `850c094` (`deliveries/gba-argon-2/`). ROM `f90141f0…` (1,135,452 B).

## Verdict

**Accepted for play-testing on the PSP Go.** This is now a real, playable GBA game:
- every screen draws;
- the characters walk;
- battles, menus, dex, shop and credits all render;
- mGBA and 1337Boy agree pixel for pixel.

**The REPORT's pixel claim is not accepted.** "7,335 / 7,336 frames identical" holds only because the test harness rewrites the reference's timers before each render. That hides two effects the ROM doesn't have. My own differential also found one missing control the shipped tests never pressed. All of it is small. A short round 3 would close it.

## What holds up (checked independently)

- **Inputs are byte-identical to round 1:** the reference (`b12be617…`) and 1337Boy.
- **The build is reproducible:** `build.py` gives `f90141f0…`, and `--build-controls` reproduces all 9 controls byte for byte.
- **The shipped suite passes on my rebuild:** 11/11, all 9 controls failing as designed. My log matches theirs line for line.
- **Input-only fuzz (`fz_2.js`):**
  - 11 checkpoints × 400 random presses = 4,400 presses, 0 divergences.
  - Compared on every press: screen, map, x, y, facing, night, seals, gold, champion flag, every party member, box count, steps, **and the seen/caught dex bitmaps**.
  - Round 1's dex scramble is gone.
- **Brotholomew (`broth3b.js`):**
  - Tested with real `.sav` files from the delivered converter.
  - 151 caught gives the 2-line diploma, and 150 gives the 3 normal lines. The reference does the same.
- **mGBA (libmgba 0.10.2, `xemu2.js`):**
  - Full 3,693-press route to the credits.
  - Mailbox identical at all 148 checkpoints.
  - **Framebuffers 0 pixels different** at all 8 sampled frames: dialog, battle, overworld, and the credits.
- Only `SWI 0x05` appears anywhere in the ROM.

## Findings

### 1. The reference's timers are overwritten before every render (undisclosed)
- **What the harness does.** `tests/run-all.js` (~l.1866) sets these on the reference before calling `render()`:
  - `transitionTimer = 0` and `animTimer = 0`;
  - `moveCooldown`, `bannerTimer` and `creditsScroll` to values it models itself;
  - `frameCount` to the ROM's frame counter.
- **Why frameCount is fine.** Aligning `frameCount` is fair: the reference counts it from page load, the ROM from boot.
- **What the zeroed timers hide.** Two reference effects are missing from the ROM:
  - **the 0.22 s fade on every map change** (`img/missing_map_fade.png`);
  - **the 0.35 s move flash over the foe in battle** (`img/missing_move_flash.png`). The ROM has no flash code at all.
- **What the spec asked for.** "Compare at the same timer value. Don't skip the frame."
- **How I checked it.** My differential (`pixdiff3.py`, real Chromium) advances the reference with its own `update(1/60)`, for exactly as many frames as the ROM ran. No other state is touched, except `frameCount`.

### 2. bEATdex LEFT/RIGHT page jump is missing
- In the reference, RIGHT and LEFT in the dex jump ±10 entries. In the ROM they do nothing (`img/dex_right_page_jump.png`, `dexdbg.js`).
- The cursor isn't in the mailbox, and the shipped pixel test only ever had 1 DEX frame, so nothing caught it.
- My random-input pixel run found it in 65 frames across two segments.

### 3. Small differences
- **Credits:** the reference draws a full border box; the ROM draws part of it (`img/minor_diffs.png`).
- **Empty dialog:** the reference has an edge case where an interaction opens a dialog with an empty line list.
  - The reference shows an empty box; the ROM shows stale text from the previous dialog ("Time shifted to Daytime").
  - Found in `chowder_mart` at (12, 9), facing right.
  - This is arguably a reference bug, but the ROM should clear the box.
- **Tile animation:** 64–128 px differences on a few interior maps (y 57–81), probably a tile-animation phase mismatch.
- **Taps and timing:** a 1-frame tap followed by only 1 released frame can be lost. Round 1 accepted it. It's harmless for people (a real tap is several frames), but `acceptingInput=1` is reported a frame before input is actually read.
- **Snapshot restore:** `bootGbaWithSlot0` restores a RAM/register snapshot of the ROM's own title state and loads SRAM *after* boot.
  - That writes private memory, though only state the ROM itself produced. Speed is the stated purpose.
  - It's not how the spec says a `.sav` is used ("loaded as SRAM before boot").

## My pixel differential, in numbers
- Reference advanced by real frames; only frameCount aligned.
- 1,515 frames in total: the bot route sampled every 7th press, plus 4 random segments of 300–400 presses (at presses 700, 1500, 2300 and 3693).
- **Every difference I found falls into one of the categories above.**
- Segment from press 700: 400/400 frames identical.
- Segments from 2300 and 3693: all non-matching frames are dex page jumps, credits, the empty-dialog edge, or ≤128 px tile animation (`pd3_*_res.json`).
- Map-change and battle frames that differ are exactly the missing fade and flash.
