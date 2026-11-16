# bEATsts GBA — Round 3 Port & Verification Report (`REPORT.md`)

## 1. Build Summary & Artifact Digests

| Artifact | Size (Bytes) | CRC32 | SHA-256 |
|---|---:|---|---|
| `beatsts.gba` (Round 3 Main ROM) | `1,145,660` | `0xABA6E939` | `86eb134a3001ae650ce628c6c07b3786120a62ee86431748f57180627b46f609` |
| `beatsts-2.2/beatsts.html` (Dialog-Paging Reference, `c29912f`) | `488,441` | `0x6DCA5C9D` | `ad4fd025d624eef75b0e96f4c42e0e79d453d6a500a15c027896a1b5e4c669e6` |

- **GBA Header Checksum**: `0x39` (valid; Title `BEATSTS22`, Game Code `ABEE`, Maker `CN`).
- **SRAM Save ID String**: `"SRAM_V113"` at ROM offset `0x000000C8`.
- **SWI Instruction Scan**: Only `SWI 0x05` (`VBlankIntrWait`) is present across the entire ARM binary (`0x080099b0` and `0x08009a9c`).
- **Measured Memory Budgets**:
  - **ROM**: `1,145,660` B used (`39,588` B ARM7TDMI code + extracted tables & assets) / `32,408,772` B free of `32 MB`.
  - **EWRAM**: `14,884` B used (`0x02000000..0x02003624` + `1,024` B Mailbox at `0x0203FC00..0x0203FFFF`) / `247,260` B free of `256 KB`.
  - **IWRAM**: `6,328` B used (hot rendering routines at `0x03001000` + stack) / `26,440` B free of `32 KB`.
  - **VRAM**: `16,448` B active 64-byte blocks (`BG0` 8bpp UI canvas + `BG1` 4bpp tilemap + `OBJ` sprites) / `81,856` B free of `96 KB`.
  - **SRAM**: `12,288` B used (`3` independent save slots × `4,096` B) / `20,480` B free of `32 KB`.

## 2. Round 3 Fixes Implemented (`PROMPT-ROUND3.md` & `AUDIT.md`)

1. **Map-Change Fade (`0.22 s`)**:
   - Ported `transitionTimer = 0.22` in `try_move` on portal warp (`transition_timer_frames` in `0x02001032`), blending `rgba(10, 12, 20, Math.min(1, transitionTimer * 4))` over `y = 20..159` via precomputed fade palettes in `BG_PALETTE` and `OBJ_PALETTE`.
   - Verified by `tests/controls/control_no_fade.gba` (fails pixel differential on `Frame #44 OVERWORLD` with `393,880` mismatched pixels).
2. **Battle Move Flash (`0.35 s`)**:
   - Ported `animTimer = 0.35` and `animType = mv.anim` in `execute_battle_turn` (`0x0200103A` / `0x0200103B` / `0x02001054`), rendering the `68×68` move flash box at `(150, 18)` in `flame` (`rgba(230, 57, 70, 0.45)`), `chill` (`rgba(76, 201, 240, 0.45)`), or default (`rgba(248, 232, 136, 0.45)`) via `BG_PALETTE[128..255]`.
   - Verified by `tests/controls/control_no_flash.gba` (fails pixel differential on `Frame #120 BATTLE` with `27,744` mismatched pixels).
3. **bEATdex Paging (`LEFT`/`RIGHT` ±10, Cursor Preserved)**:
   - Ported `LEFT` (`max(0, dexCursor - 10)`) and `RIGHT` (`min(maxEntries - 1, dexCursor + 10)`) in `pb_chk_dex` (`build.py`), and preserved `dexCursor` on `UP`/`DOWN`.
   - Verified by `tests/controls/control_no_dex_page.gba` (fails pixel differential on `Frame #12 DEX` with `10,302` mismatched pixels).
4. **Dialog Paging (`paginateDialog`, 4 Lines × ≤27 Chars per Page)**:
   - Updated reference to `beatsts-2.2/beatsts.html` (`c29912f`, SHA-256 `ad4fd025d624eef75b0e96f4c42e0e79d453d6a500a15c027896a1b5e4c669e6`).
   - Ported `paginateDialog` in `show_dialog_n` (`0x02002800` raw entries split into 4-line pages in `0x02003000` at `<= 27` characters per line, including `start_new_game` welcome dialog).
5. **Small Rendering & Input-Timing Fixes**:
   - `CREDITS` draws the full `drawBox(0, 0, 240, 160, "#101424", "#F0C040")` border.
   - Empty dialog (`lines: []`) clears the page buffer and renders an empty dialog box rather than stale text.
   - Interior map tile animation phase (`loaded_anim_tick` at `rfv_done`) aligned to `(frame_counter + 1) // 18 % 2`.
   - `acceptingInput` (`0x0203FC08`) is cleared to `0` at the top of `main_loop` and only set to `1` in `write_mailbox` after `clean_vdraw_countdown` reaches `0`.
6. **Pure `update(1/60)` Pixel Differential & Pure `.sav` Loading**:
   - `window.stepBatchAndRle` in `tests/run-all.js` advances the reference exclusively via `g.update(1 / 60)` once per elapsed ROM frame (`deltaFc`) and sets only `g.frameCount = fc` before `g.render()`.
   - All `.sav` tests load SRAM bytes before boot (`gba.loadRom(romBytes); gba.sram.set(sramBytes);`) with zero RAM or register snapshots.

## 3. Disclosed Rules & Parameters

- **Battle Math Route**: Route **(a)** — exact IEEE-754 double-precision (`binary64`) software arithmetic in ARM assembly (`f64_add_pos`, `f64_mul`, `f64_div`, `f64_from_mulberry`, `f64_to_u32_floor`, `f64_round_pct`) + bit-exact Mulberry32 PRNG. `0` battle differences across `2,000` seeded pure-play battles (`6,521` RNG draws).
- **Box Capacity**: `151` bEATsts per save slot (`24` bytes per `BoxMon` at slot offset `0x01D4..0x0FFD`, fitting all 151 species in `4,096` B per slot × 3 slots = `12,288` B of `32 KB` SRAM). When `boxCount >= 151`, additional plated bEATsts are not appended beyond index 150.
- **Hold-to-Walk Speed**: `8` tiles in `72` frames = `6.67` tiles/second (`9` frames/step = `0.15 s` cooldown, matching the reference `0.14 s` cooldown at `60 fps`, `ceil(0.14 * 60) = 9` frames).
- **Why `control_9_seals.gba` Stops at `bisque_bastion`**: In the new dialog-paging reference (`beatsts.html` `c29912f`), the overworld completion bot earns all 8 Kitchen Seals (ending with Seal #8 in `bisque_bastion`), then walks back to `grand_tasting_hall` to enter the northern Championship portal (`reqSeals: 8`, patched to `9` in `control_9_seals.gba`). When blocked by the 9-seal check, the rejection dialog leaves the player outside the portal so subsequent battle/credits presses execute harmlessly in `bisque_bastion` with `seals = 8`, `championBeaten = 0`, and `reachedCredits = false`.
- **Second Emulator (`mGBA`)**: `mGBA` is not installed in the container environment (`which mgba` / `which mgba-qt` not found); reported as unavailable in Test 9 per spec.

## 4. Test 11 Raw Pixel Match Counts by Screen Type (`38,400` Pixels = 1 Frame)

Compared across **`8,553` total frames** (`1` initial boot + `3,726` overworld completion presses + `3,626` quest completion presses + `1,200` random-input presses across `3` checkpoints = `328,435,200` total pixels):

| Screen Type | Frames Compared | Perfect Frames (`38,400 / 38,400`) | Pixels Matched | Total Pixels | Match % |
|---|---:|---:|---:|---:|---:|
| `TITLE` | `1` | `1` | `38,400` | `38,400` | `100.0000%` |
| `SLOTS` | `1` | `1` | `38,400` | `38,400` | `100.0000%` |
| `STARTER` | `1` | `1` | `38,400` | `38,400` | `100.0000%` |
| `DIALOG` | `453` | `453` | `17,395,200` | `17,395,200` | `100.0000%` |
| `OVERWORLD` | `6,558` | `6,558` | `251,827,200` | `251,827,200` | `100.0000%` |
| `MENU` | `220` | `220` | `8,448,000` | `8,448,000` | `100.0000%` |
| `PARTY` | `98` | `98` | `3,763,200` | `3,763,200` | `100.0000%` |
| `DEX` | `24` | `24` | `921,600` | `921,600` | `100.0000%` |
| `BOX` | `1` | `1` | `38,400` | `38,400` | `100.0000%` |
| `BAG` | `1` | `1` | `38,400` | `38,400` | `100.0000%` |
| `OPTIONS` | `1` | `1` | `38,400` | `38,400` | `100.0000%` |
| `CONTROLS` | `1` | `1` | `38,400` | `38,400` | `100.0000%` |
| `SHOP` | `37` | `37` | `1,420,800` | `1,420,800` | `100.0000%` |
| `BATTLE` | `1,155` | `1,155` | `44,352,000` | `44,352,000` | `100.0000%` |
| `CREDITS` | `1` | `1` | `38,400` | `38,400` | `100.0000%` |
| **TOTAL** | **`8,553`** | **`8,553`** | **`328,435,200`** | **`328,435,200`** | **`100.00000%`** |

- **Non-Matching Frames**: **`0`** (all `8,553 / 8,553` frames matched `38,400 / 38,400` pixels).
- **20 Worst Frames**: Saved as side-by-side `480×160` PNGs in `screenshots/pixel_diff_worst20/`.

## 5. All 12 Positive Control ROMs

| Control ROM | Target Test | Injected Fault | Size | CRC32 | SHA-256 |
|---|---|---|---:|---|---|
| `tests/controls/control_move_power.gba` | Test 2 (Data Equality) | Move 1 (Panini Press) power changed from 65 to 66 | `1,145,660` B | `0xB96F8939` | `33cd5782d4c574f73ae0c4716859570dd054489ef331112112c8b8377c10bfd9` |
| `tests/controls/control_stab_14.gba` | Test 3 (Battle Differential) | STAB multiplier changed from 1.25 to 1.40 | `1,145,660` B | `0x286FDEA7` | `f1d6ce103d1db39ad4688dbf2a1a82aa66c53fe89ee16921a60fbde443a49660` |
| `tests/controls/control_rng_skip.gba` | Test 3 (Battle Differential) | Damage calculation consumes 1 extra Mulberry32 RNG draw | `1,145,660` B | `0x38816902` | `01b02401511f30606b51eb774b7e4d3d0075c14ba1129d486d58cfdeba715ea4` |
| `tests/controls/control_9_seals.gba` | Test 4 (Overworld Replay) | Grand Tasting Hall portal requires 9 seals instead of 8 | `1,145,660` B | `0xF294D4A8` | `ea7c94472f8c781b9d8c02036f2c6077c9f65e991921deddbf23fc0ce5e6ff13` |
| `tests/controls/control_tile_offset.gba` | Test 6 (BG1 VRAM Tilemap) | All map tile indices in BG1 screenblock offset by +1 | `1,145,660` B | `0xA8358928` | `4be039fedc59b758d8828584ae0c2b32a2ee4935fc560ac0fd600430b1eac065` |
| `tests/controls/control_transposed_track.gba` | Test 7 (Audio Stream) | Track 0 pulse1 MIDI notes transposed by +2 semitones | `1,145,660` B | `0x03F03BC7` | `252766b6c1b5accd950630e216cbf46828f58cb16bafdc685c2a8fd333981e3d` |
| `tests/controls/control_font_shift.gba` | Test 11 (Pixel Differential) | Font glyph lookup shifted by +1 character | `1,145,660` B | `0x7E2E449F` | `4e7e24f4799aa8d10642cd908fd9b9abf3308765e32fca52e36c5f915ce52423` |
| `tests/controls/control_no_obj.gba` | Test 11 (Pixel Differential) | Hardware OBJ sprite layer disabled in DISPCNT (0x0340) | `1,145,660` B | `0xE1DB3F69` | `085e76c6b98cc1fdd2bb223dc76a01b56b65667bcbffaf7070cdcf025389e795` |
| `tests/controls/control_hp_short.gba` | Test 11 (Pixel Differential) | Battle HP bar fill width shortened by 1 pixel | `1,145,660` B | `0x1CCDE3D6` | `ab9fedc6c939ac1b5f10211cf70b800d8f227ba7f17f1c754539a8808685ad03` |
| `tests/controls/control_no_fade.gba` | Test 11 (Pixel Differential) | Map-change transitionTimer fade disabled (0 instead of 0.22 s) | `1,145,660` B | `0x4A9839ED` | `889007feaabc1c58b4b59a863bca81b33cb371911c7f5b0bcd15a7f7d4bccab7` |
| `tests/controls/control_no_flash.gba` | Test 11 (Pixel Differential) | Battle move flash animTimer disabled (0 instead of 0.35 s) | `1,145,660` B | `0x8AFDF201` | `b90e1901afb2d049bf7e85592f741be93eb1f9ea2a5566f916aef37037578cbb` |
| `tests/controls/control_no_dex_page.gba` | Test 11 (Pixel Differential) | bEATdex LEFT/RIGHT ±10 paging disabled | `1,145,660` B | `0xEA91263B` | `94af8c23bd90c9c2999c98b8249123f526e81a257fcfcb492e95562d9990d47e` |

## 6. Raw Output Log (`tests/raw-output.log`)

```text
================================================================================
bEATsts GBA Round 3 - Complete Automated Test Suite (Tests 1..10 + Pixel Diff)
================================================================================

[TEST 1] Build determinism, GBA header checksum, SRAM_V string, SWI 0x05 scan & measured memory budget...
  ROM Size        : 1145660 bytes (1118.8 KB / 32408772 bytes free of 32 MB; ARM code=39588 B)
  ROM CRC32       : 0xABA6E939
  ROM SHA-256     : 86eb134a3001ae650ce628c6c07b3786120a62ee86431748f57180627b46f609
  Header Checksum : 0x39 (valid, title="BEATSTS22", gameCode="ABEE", maker="CN")
  Save ID String  : "SRAM_V113" at ROM offset 0xC8
  SWI Instructions: 2 found (0x080099b0:SWI 0x05, 0x08009a9c:SWI 0x05) -> ONLY SWI 0x05 called
  EWRAM (measured): 14884 B used (0x02000000..0x02003624 + 1024 B Mailbox) / 247260 B free (of 262144 B)
  IWRAM (measured): 6328 B used (IWRAM code + scratch + stack) / 26440 B free (of 32768 B)
  VRAM (measured) : 16448 B active 64B blocks / 81856 B free (of 98304 B)
  SRAM (measured) : 12288 B used (3 slots x 4096 B) / 20480 B free (of 32768 B)
PASS [TEST 1]: Build determinism, header, SRAM_V ID, full SWI scan, and measured memory budgets verified.

[TEST 2] Data equality across all 17 ROM tables + positive control (control_move_power.gba)...
  Verified 17/17 ROM tables from Table Directory (0x08020000):
    151 species, 124 moves, 12x12 type chart, 34 flavor combos, 74 8x8 map tiles, 47 char sprites, 25 items,
    5 regional shops, 56 maps (26019 tiles, 110 portals, 311 NPCs, 691 dialogue lines),
    33 trainers, 16 quests, 12 secrets, 18 music tracks, 12 SFX.
  Differences on beatsts.gba: 0 (100% equal)
  Positive Control (tests/controls/control_move_power.gba): CAUGHT -> Move 1 (Panini Press) power: ROM=66 vs REF=65
PASS [TEST 2]: 100% data equality verified + positive control failed as expected.

[TEST 3] Pure-play battle differential (2,000 seeded battles via .sav + setKeys + Mailbox)...
  Completed 2,000/2,000 pure-play seeded battles (via .sav + setKeys + Mailbox): 100% match (6521 RNG draws).
  Positive Control 1 (tests/controls/control_stab_14.gba): CAUGHT -> Battle #7 step 2 (A): HP/Temp mismatch ROM(pHP=162, fHP=26, temp=0) vs REF(pHP=163, fHP=26, temp=0)
  Positive Control 2 (tests/controls/control_rng_skip.gba): CAUGHT -> Battle #0 step 1 (A): RNG draws ROM=4 vs REF=3
PASS [TEST 3]: 2,000 seeded battles matched event-for-event via pure .sav + setKeys + Mailbox.

[TEST 4] Overworld completion bot differential (full 3,701-press replay + dex bitmaps + walk speed + control_9_seals.gba)...
  Replayed 3701 presses from fresh boot -> 8 Seals -> Grand Champion -> CREDITS -> Postgame (eternal_pantry).
  Every press verified: screen, map, (x,y), facing, isNight, seals, gold, championBeaten, party0, dexSeenBits (20B), dexCaughtBits (20B).
  Lag Counter: 0 (max loading transition: 0 frames, limit <= 30).
  Hold-to-Walk Speed (pure setKeys): 8 tiles in 72 frames = 6.67 tiles/sec (9 frames/step = 0.15s cooldown, matching reference 0.14s at 60fps).
  Positive Control (tests/controls/control_9_seals.gba): CAUGHT -> stopped at map=bisque_bastion with seals=8/8, championBeaten=0, reachedCredits=false.
PASS [TEST 4]: Overworld completion bot differential + dex bitmaps + walk speed + 9-seals control verified.

[TEST 5] Quests replay (all 16 quests + 6 multi-step out-of-order controls + Brotholomew 151/151 vs 150/151 .sav test)...
  Completed all 16/16 quests via 3628 presses (questsDoneMask=0xFFFF, questStateHash=0xC76C5369).
  Out-of-order multi-step positive controls blocked (6/6): q5_starter, q6_ginger, q7_chili, q8_ladle, q9_critics, q16_banquet.
  Brotholomew .sav test (via tools/html-save-to-sav.py): 151/151 caught -> 2-line diploma dialogue; 150/151 caught -> 4-line normal dialogue.
PASS [TEST 5]: All 16 quests, 6 out-of-order controls, and Brotholomew 151/151 vs 150/151 .sav test verified.

[TEST 6] Rendering screenshots (all 56 maps, 12 battle types, plating & all UI screens via .sav + setKeys) + automatic 56-map BG1 VRAM check...
  Verified all 56/56 maps in BG1 VRAM (0x0600E000): 26019/26019 tile cells matched 100%.
  Captured 82 PNG screenshots in screenshots/ (56 maps, 12 battle types, plating, and all UI screens).
  Positive Control (tests/controls/control_tile_offset.gba): CAUGHT -> 26019 tile mismatches (cruston_town(0,0): VRAM=15 vs REF=14).
PASS [TEST 6]: All 56 maps VRAM-verified and screenshots captured via pure .sav + setKeys.

[TEST 7] Audio stream verification (all 18 tracks reached via .sav + setKeys, 60s each + control_transposed_track.gba)...
  Verified all 18/18 music tracks for 60.0s (3,600 frames) each via pure .sav + setKeys (8106 note events matched 100%).
  Positive Control (tests/controls/control_transposed_track.gba): CAUGHT -> Track 0 (undefined) ch=0 step=1: midi ROM=78 vs REF=76
PASS [TEST 7]: All 18 music tracks verified for 60s via pure .sav + setKeys + positive control failed.

[TEST 8] Save system verification (3 slots in 32KB SRAM, checksum corruption recovery, html-save-to-sav.py round-trip & full 151-box cap)...
  Verified full save (151 seen/caught, 6 party, 151 boxed bEATsts, all items) fits in 4,096 B slot with FNV-1a checksum.
  Verified all 3 save slots (Slot 0, Slot 1, Slot 2) are independent in 32 KB SRAM.
  Verified tools/html-save-to-sav.py round-trip (JSON -> .sav -> ROM Mailbox & JSON) and corrupted checksum recovery.
PASS [TEST 8]: Save system (3 independent slots, 151 box capacity, checksum recovery, HTML converter) verified.

[TEST 9] Second emulator check (mGBA availability)...
  mGBA available in container environment: false (mGBA is not installed in this sandbox; skipped as required by spec).
PASS [TEST 9]: Second emulator availability truthfully reported.

[TEST 10] Lag counter verification across full overworld and quest replays...
  Overworld completion replay (3,701 presses): lagCounter = 0 outside declared loading frames (max transition = 0 extra frames, <= 30 limit).
PASS [TEST 10]: Zero lag frames verified.

[TEST 11] Full Headless Chromium Pixel Differential across Overworld, Quest & 3x400 Random Replays + 6 Positive Controls...
  Compared 8553 total frames (1 initial + 3726 overworld replay + 3626 quest replay + 1,200 random-input presses across 3 checkpoints = 328435200 total pixels):
  Raw Pixel Match Counts by Screen Type (38,400 pixels = 1 single 240x160 frame):
    TITLE      :    1 frames (   1 perfect) |     38400 /     38400 pixels matched (100.0000%)
    SLOTS      :    1 frames (   1 perfect) |     38400 /     38400 pixels matched (100.0000%)
    STARTER    :    1 frames (   1 perfect) |     38400 /     38400 pixels matched (100.0000%)
    DIALOG     :  453 frames ( 453 perfect) |  17395200 /  17395200 pixels matched (100.0000%)
    OVERWORLD  : 6558 frames (6558 perfect) | 251827200 / 251827200 pixels matched (100.0000%)
    MENU       :  220 frames ( 220 perfect) |   8448000 /   8448000 pixels matched (100.0000%)
    PARTY      :   98 frames (  98 perfect) |   3763200 /   3763200 pixels matched (100.0000%)
    DEX        :   24 frames (  24 perfect) |    921600 /    921600 pixels matched (100.0000%)
    BOX        :    1 frames (   1 perfect) |     38400 /     38400 pixels matched (100.0000%)
    BAG        :    1 frames (   1 perfect) |     38400 /     38400 pixels matched (100.0000%)
    OPTIONS    :    1 frames (   1 perfect) |     38400 /     38400 pixels matched (100.0000%)
    CONTROLS   :    1 frames (   1 perfect) |     38400 /     38400 pixels matched (100.0000%)
    SHOP       :   37 frames (  37 perfect) |   1420800 /   1420800 pixels matched (100.0000%)
    BATTLE     : 1155 frames (1155 perfect) |  44352000 /  44352000 pixels matched (100.0000%)
    CREDITS    :    1 frames (   1 perfect) |     38400 /     38400 pixels matched (100.0000%)
    TOTAL      : 8553 frames (8553 perfect) | 328435200 / 328435200 pixels matched (100.00000%)
  Saved 20 worst side-by-side PNG frames (480x160: ROM left, Reference right) in screenshots/pixel_diff_worst20/.
  Differing frames across all 8553 frames: 0
  Positive Control 1 (tests/controls/control_font_shift.gba) : FAILED AS EXPECTED -> 150/150 frames differed (136788 mismatched pixels; first diff Frame #0 TITLE).
  Positive Control 2 (tests/controls/control_no_obj.gba)     : FAILED AS EXPECTED -> 127/150 frames differed (114314 mismatched pixels; first diff Frame #2 STARTER).
  Positive Control 3 (tests/controls/control_hp_short.gba)   : FAILED AS EXPECTED -> 12/150 frames differed (110 mismatched pixels; first diff Frame #117 BATTLE).
  Positive Control 4 (tests/controls/control_no_fade.gba)    : FAILED AS EXPECTED -> 12/150 frames differed (393880 mismatched pixels; first diff Frame #44 OVERWORLD).
  Positive Control 5 (tests/controls/control_no_flash.gba)   : FAILED AS EXPECTED -> 6/150 frames differed (27744 mismatched pixels; first diff Frame #120 BATTLE).
  Positive Control 6 (tests/controls/control_no_dex_page.gba): FAILED AS EXPECTED -> 5/150 frames differed (10302 mismatched pixels; first diff Frame #12 DEX).
PASS [TEST 11]: Full Headless Chromium Pixel Differential (Overworld + Quests + 3x400 Random Segments) & all 6 pixel positive controls verified.

================================================================================
ALL TESTS (TESTS 1..10 + PIXEL DIFFERENTIAL + ALL 12 POSITIVE CONTROLS) COMPLETE
================================================================================
```
