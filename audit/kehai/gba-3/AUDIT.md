# bEATsts GBA, Argon round 3: Kehai's audit

Delivery committed as delivered in `deliveries/gba-argon-3/`. ROM `86eb134a…` (1,145,660 B), built on the paging reference `ad4fd025…` (`c29912f`).

## Verdict

**Accepted.** Every round-2 finding is fixed:
- the fade;
- the move flash;
- dex paging;
- the credits box;
- empty dialogs;
- the tile-animation phase;
- `acceptingInput`.

Dialog paging is ported pixel-exact. The harness is honest now: it only aligns `frameCount`, and `.sav` files are loaded before boot. My own checks found one cosmetic credits detail and one 1337Boy timing quirk; neither is a ROM-logic problem.

## Checked independently
- **Reproducible:** `build.py` gives `86eb134a…`, and `--build-controls` reproduces all **12** controls byte for byte. 1337Boy is unchanged.
- **The shipped suite passes on my rebuild:** 11/11 tests, and all controls fail as designed. My log matches theirs.
- **Harness:**
  - The reference is advanced only with `update(1/60)` per ROM frame, and only `frameCount` is set.
  - SRAM is loaded before boot, with no snapshot restore.
  - The only remaining state writes are in `resetReferenceGame()`, which resets the reference to its title state before replays (the same as a page load).
- **Input-only fuzz (`fz_2.js`, re-recorded on the new reference):**
  - 11 checkpoints × 400 random presses = **4,400 presses, 0 divergences**.
  - Compared on every press: screen, map, x, y, facing, night, seals, gold, champion flag, every party member, box count, steps, and the seen/caught dex.
- **Dialog paging (`vera.js`, `vera_px.py`):**
  - **No bot route ever hits a multi-page dialog** (counted: 0 multi-page entries across the 3,693-press route), so I tested it directly.
  - Method: a real `.sav` from the delivered converter, parked facing Baker Vera.
  - The ROM and the reference both show **6 pages** for her 3 lines, and **every dialog box is pixel-identical** to the Chromium reference. The only differences were 24 px of animated map peeking out under the box.
- **Brotholomew:** 151 caught gives the diploma and 150 gives the normal lines, on both.
- **mGBA:**
  - Full route: mailbox identical at all 148 checkpoints.
  - Framebuffers: 7 of 8 sampled frames pixel-identical.
- **Pixel differential (`pixdiff3.py`, real Chromium):**
  - The reference runs on its own `update(1/60)`; only `frameCount` is aligned.
  - Four 400-press random segments, from presses 700, 1500, 2300 and 3693.
  - **1,597 of 1,600 frames are identical.** That includes the segment that showed the dex-paging and stale-dialog bugs in round 2.

## Findings (small)
1. **Credits: scrolling text overlaps the bottom border.**
   - For the first frames of the credits scroll, the ROM draws the first text line over the yellow border (rows 152–159). The reference keeps the border on top (`img/credits_text_over_border.png`).
   - 3 frames, 54–109 px. The shipped suite has only 1 credits frame, so it can't see this.
2. **1337Boy shows palette changes a frame early.**
   - During the 0.22 s map fade, 1337Boy and mGBA disagree by one fade step for a frame (`img/fade_1337boy_vs_mgba_press1500.png`), with an identical mailbox.
   - The ROM writes the fade palette at VBlank, which is correct. mGBA (like hardware) shows it on the next frame; 1337Boy renders the whole frame at the end and shows it early.
   - On the PSP the fade will look like mGBA's. This is a 1337Boy accuracy note, not a ROM bug.
3. **Coverage gap:** the shipped replays never exercise a multi-page dialog. Paging is verified here by `vera.js`, but the suite itself should include an NPC with a long line.
