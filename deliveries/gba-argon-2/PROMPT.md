# bEATsts GBA: the whole game as a real Game Boy Advance ROM

ConsciousNode SoftWorks, MIT. The attached `GBA-RULES.md` (the studio's GBA rules) is part of this spec, and so are the Xinu rules: no dependencies, offline, and every lift inlined and labeled.

bEATsts 2.2 (attached) was built in the GBA's shape from day one: 240×160, 8×8 tiles, 16-colour 15-bit palettes, and music written for 2 pulse + wave + noise. **Port all of it to a real `.gba` ROM.** Kham will play it on a PSP Go. This is a translation, not a redesign: the same world, the same words, the same numbers.

## Attached
- `beatsts-2.2/`: the release (ConsciousNode/bEATsts `f1fc208`):
  - `beatsts.html` and `src/`, `gen_world.py`, `build.py`, `DATA.md`, `tests/`;
  - `KEHAI-PATCH.md` (evolved forms come only from evolving);
  - `AUDIT.md`.
  - **`beatsts.html` is the reference** (SHA-256 `b12be617…2c64`, see MANIFEST). Its `BEATS_API` exposes every table.
- `1337boy/1337boy.html`, `1337boy/tools/1337ify.py`, `1337boy/TESTING.md`: the studio's GBA emulator (the test platform) and its ROM tool (lift the header code from it).
- `GBA-RULES.md`: the shared GBA rules.

## What to build
1. **`beatsts.gba`, with everything in the reference:**
   - 151 species with front/back sprites;
   - 124 moves, types, flavour combos, plating, Kitchen Temp;
   - 56 maps with portals, NPCs, signs, puzzles, dungeons, gyms and interiors;
   - trainers, Rival Saffron, the Chrome Fork Syndicate, the champion, credits and the postgame;
   - 16 quests with their step checks, secrets, shops, the box, the bag, day/night (SELECT, as in the reference);
   - the 18 music tracks and every sound effect, on the PSG channels;
   - both studio fonts, byte-exact;
   - name entry on an on-screen keyboard.

   **Controls** as in the reference: D-pad, A, B, START, SELECT. L and R are optional extras; document them.
2. **Saves:**
   - 3 slots in 32 KB SRAM.
   - **A packed binary format, not JSON.** A full save (151 seen and caught, 6 in the party, a full box, every item) must fit, with a version byte and a checksum per slot. Document it in `SAVE.md` with byte offsets.
   - Also **`tools/html-save-to-sav.py`**: it converts an exported HTML save (`exportSaveJson`) into a `.sav`, so Kham can carry his web save to the PSP. Round trip: HTML JSON → `.sav` → load in the ROM → mailbox state equals the JSON.
3. **Numbers that match exactly:**
   - The reference battle math uses JavaScript doubles (for example `Math.floor(base * stab * eff * tempMult * comboMult * rand)`) and Mulberry32 floats. The ROM must give **identical integers**. Two honest routes:
     - **(a)** Reproduce IEEE-754 double results exactly (a small soft-double for the operations used, or an integer method you prove matches for every input range).
     - **(b)** Propose `beatsts 2.2.1`: the HTML with every such formula rewritten as integer math. It ships alongside, all 13 reference tests still pass, and the differential runs against 2.2.1. List every formula changed, and measure how many game outcomes differ from 2.2 over 10,000 seeded battles.
   - Pick one and say which.
4. **`build.py` (or `build.js`):** extracts every table from the reference HTML (run it headless, or parse `src/`) into ROM data, so the content is never retyped by hand. Plus `MAILBOX.md`, `SAVE.md`, `LIFTS.md`, `REPORT.md`, `tests/`.

## Mailbox (on top of the shared fields)
- **Overworld:** map id, x, y, facing, day/night, gold, seals, `championBeaten`, a quest-state hash, a dex seen/caught bitmap, and the party (species, level, HP, moves).
- **Battle:** the phase, both active bEATsts (species, level, HP, status), and **a ring buffer of battle events** (move used, damage, crit/effectiveness flags, plating result, RNG draws consumed).
- **A table directory:** the ROM offset and length of every data table, so tests can read the tables straight out of the ROM file.

## Tests (numbered; each must be able to fail)
1. **Build:**
   - The ROM rebuilds byte for byte.
   - The header checksum is valid, and the `SRAM_V` ID string is present.
   - Only `SWI 0x05` is called.
   - Report the ROM size and the free EWRAM/IWRAM.
2. **Data equality:**
   - Read every table out of the ROM through the table directory and compare it field by field with `BEATS_API` in the reference: species, moves, the type chart, items, shops, maps (grids, portals, NPCs and every line of text), trainers, quests, secrets, music and SFX data.
   - **100% equal.** Any difference is listed with a reason.
   - **Positive control:** a ROM built from a reference with one move's power changed fails.
3. **Battle differential (the main test):**
   - Run 2,000 seeded battles: random species, levels and movesets, and random input scripts through `setKeys`.
   - The ROM's battle-event log must equal the reference `Game` run with the same seed and the same menu choices (through `handleBattleInput`), event for event, including the RNG draws consumed.
   - **Positive controls:**
     - a reference with STAB set to 1.4 fails;
     - a reference whose RNG skips one draw fails.
4. **Overworld differential:**
   - Record the reference completion bot's `pressButton` sequence. This is the 2.2 test-9 bot, run from a fresh game.
   - Replay it in 1337Boy as key presses, each waiting for the mailbox's "accepting input" flag.
   - After every map change and every battle, the mailbox overworld state must equal the reference's.
   - It must reach the credits and the postgame, with 0 page errors on the reference side and a lag counter of 0 outside declared loading frames.
   - **Positive control:** the same replay on a ROM whose Grand Tasting Hall portal needs 9 seals stops short.
5. **Quests:** replay the reference quest bot (2.2 test 10) the same way: all 16 quests complete. Then do the out-of-order attempts on a fresh save: talking to the final NPC of each multi-step quest first does **not** complete it.
6. **Rendering:**
   - Screenshots of every map, a battle per type, plating, the dex, the bag, the box, name entry, the credits and the postgame.
   - **Automatic:** for every map at a fixed camera position, the background tile indices in VRAM match the reference grid. Read VRAM through the bus, auditor-side only.
   - **Positive control:** an off-by-one tile offset is caught.
7. **Audio:**
   - Each track's note-event stream (written to the mailbox by the music player as it plays) equals the reference `MUSIC_TRACKS` sequence for 60 s.
   - **Positive control:** a transposed track fails.
   - Kham judges the sound by ear.
8. **Saves:**
   - A full save fits and round-trips.
   - All 3 slots are independent.
   - A corrupted checksum means a fresh start with no crash.
   - The HTML-save converter round trip works.
9. **Second emulator:** the same ROM and replay in mGBA (if available) give identical framebuffers at 20 checkpoints. If mGBA isn't available, say so.
10. **Lag:** the lag counter stays 0 through the whole overworld replay, apart from frames declared as loading in `MAILBOX.md` (map transitions only, each ≤ 30 frames).

## Forbidden
Everything in `GBA-RULES.md`, plus:
- Retyping, summarizing or "simplifying" content. Text, numbers and maps come from the reference by extraction.
- Cutting content to fit. If something doesn't fit (ROM, RAM, VRAM or SRAM), say so with the numbers before cutting anything.
- Any change to game rules or balance apart from route (b) above, which must be disclosed in full.
