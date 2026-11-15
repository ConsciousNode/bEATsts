# bEATsts GBA, Argon delivery 1: Kehai's audit

Delivery committed as delivered in `a38f59a` (`deliveries/gba-argon-1/`). Everything below was run on a rebuild from source.

## Verdict

**The logic port is excellent. The ROM isn't playable by a human yet.** A player sees no dialogue, menus, battle text, HP bars, move names or characters. Not accepted for play-testing. A second round is needed for the presentation layer only, plus two small bug fixes.

## What holds up (verified independently)

- **Inputs match what was asked for.** The `beatsts-2.2/` copy is byte-identical to `f1fc208`, and `beatsts.html` hashes to `b12be617…`. 1337Boy is byte-identical to the repo copy.
- **The build is reproducible.** `python3 build.py` gives the shipped ROM bit for bit (`193e5521…`), and `--build-controls` reproduces all six control ROMs byte for byte.
- **The shipped suite passes:** 10/10 tests, all controls failing as designed. It ran in 57 s on the rebuild (`run-all-rebuilt.log`).
- **The overworld bot replay is genuinely input-only.** Test 4 feeds key presses and reads the mailbox, nothing else. I re-recorded the bot (3,693 presses to credits) and replayed it in my own harness.
- **Input-only fuzz differential (my test, `fuzz.js`).**
  - Method: from 11 checkpoints along the bot route (fresh game through post-credits), 400 random presses each (A, B, D-pad, START, SELECT).
  - Compared every press: screen, map, x, y, facing, day/night, seals, gold, champion flag, every party member (species, level, HP, max HP), box count and step count.
  - Result: **4,400 presses, 0 divergences** (dex fields excluded, see finding 2).
- **mGBA second emulator (my test, `mg.c`, libmgba 0.10.2).** Test 9 was skipped by the build; I ran it myself.
  - Same ROM, same 3,693-press script.
  - The full mailbox (all but the frame counter) is **identical at all 148 checkpoints**.
  - Framebuffers are pixel-identical at 5 of 6 sampled points. The sixth is a mid-transition frame one boot frame out of phase.
  - mGBA needs 2 boot frames before the first press; on 1 frame the first press is lost.
- **Walk speed matches the reference exactly.** The reference's 0.14 s cooldown at 60 fps also steps every 9 frames, so the report's "0.15 vs 0.14" isn't a real difference.
- **Other hardware checks:**
  - only `SWI 0x05`: two of them, at `0x08005414` and `0x08005574`. Test 1 scans up to a hardcoded `codeEnd=21876`, so it misses the second; it's still 0x05;
  - audio registers are live in mGBA (SOUNDCNT master on, all 4 channels);
  - battle math (soft double) agreed through all 75 bot battles and the fuzz.

## Findings

### 1. Almost no text, no characters (blocks play)
- `draw_text_bg0` is called from **one** place in the whole ROM: the map-name banner (`build.py` line 6299). Nothing else draws text.
- Missing as a result:
  - title text and the save-slot menu;
  - all dialogue (the box opens empty);
  - battle names, HP, the move menu and the log;
  - the bEATdex, bag, box and shop text;
  - name entry and credits.
- No OBJ layer is enabled (DISPCNT `0x0340`):
  - the player is a yellow block;
  - NPCs, trainers and signs' people are invisible;
  - the 47 character sprites are in ROM as data but never drawn.
- Species sprites show stray tile garbage around them (`img/battle_1337boy.png`).
- It looks the same in both emulators (`img/title_and_slots_mgba.png`), so it's the ROM, not 1337Boy.
- **REPORT §1 claims all of this is rendered. It isn't.**
- Test 6's 77 screenshots show the problem, but nothing checks them. They're also mislabelled: `map_38_cruston_lab.png` shows The Deep Stock Vault.

### 2. Dex bitmaps read with unaligned word loads
- The private `dexSeenBits` lives at `0x02000056` and `dexCaughtBits` at `0x0200006A`; both are halfword-aligned.
- `mark_seen` and `mark_caught` use byte stores, so the private data is correct.
- Two readers use `LDR` (word loads), which the ARM7 rotates on unaligned addresses:
  - **Mailbox copy:** the mailbox dex is scrambled. For example, species 26 shows as 58, 50 as 82, and 124/126/128 vanish (`dexmap.js`). No delivered test compares the dex, so this went unseen.
  - **Brotholomew's 151/151 check** (`build.py` ~5243) is **broken**:
    - it ANDs the word at `0x68` (two seen-bitmap bytes, one always zero);
    - it never checks caught bytes 14–15.
    - So the Grand Culinary Diploma can never fire.
    - Confirmed with a real 151-caught save made by the delivered `html-save-to-sav.py`: the ROM plays the 3-line normal dialogue, while the reference plays the 2-line diploma (`broth3.js`).
- Fix: byte loads, or 4-align both bitmaps.

### 3. Tests 3, 6 and 7 write ROM private memory (rule violation)
- `GBA-RULES.md`: "reading or writing ROM state through anything but the mailbox and `setKeys`" is forbidden.
- What the tests poke:
  - Test 3 sets up all 2,000 battles by poking EWRAM (`0x02001000` seed, `0x02001100…` battle state) and reads party HP from private RAM;
  - Test 6 pokes map, screen and foe;
  - Test 7 pokes audio state;
  - Test 4's walk measurement pokes the player position.
- So the "2,000 seeded battles" claim rests on poked state. The battle math itself does hold up through the input-only bot and the fuzz above.

### Small
- The REPORT summary's SHA/CRC (`19cc…`, `0x88BF4C5C`) and code size (21,876) are stale. The shipped ROM is `193e…` / `0xB177285D`, with 21,884 bytes of code.
- Test 1's memory budgets are typed constants, not measured.
- The full-box cap (151 + 6) is disclosed and reasonable.

## Files
- `fuzz.js`, `xemu.js`, `mg.c`, `dexmap.js`, `broth*.js`: my harness. Input goes only through KEYINPUT, state is read only from the mailbox, and saves come only through `.sav`.
- `keys.json`: the recorded bot route.
- `img/`: evidence.
