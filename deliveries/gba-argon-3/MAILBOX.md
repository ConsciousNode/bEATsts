# bEATsts GBA: Test Mailbox & Table Directory (`MAILBOX.md`)

The ROM maintains a live test mailbox in EWRAM at **`0x0203FC00..0x0203FFFF`** (`1,024` bytes), written unconditionally on every frame by the main game loop immediately prior to `SWI 0x05` (`VBlankIntrWait`). There is no test mode; the ROM never checks whether the mailbox is being read.

All multi-byte values are little-endian.

## 1. Shared Header & Overworld State (`0x0203FC00..0x0203FC9F`)

| Address | Offset | Size | Type | Field | Description |
|---|---|---|---|---|---|
| `0x0203FC00` | `0x000` | `4` | `u32` | `magic` | Constant `0x42454154` (`"TAEB"` / `"BEAT"` in little-endian). |
| `0x0203FC04` | `0x004` | `4` | `u32` | `frameCounter` | Total game frames elapsed since boot (incremented once per main loop frame). |
| `0x0203FC08` | `0x008` | `1` | `u8` | `acceptingInput` | `1` when the game is ready to accept a new button press on the next frame, `0` during declared map transition loading frames. |
| `0x0203FC09` | `0x009` | `1` | `u8` | `loadingFlag` | `1` during map transition loading frames (at most 1 frame per portal transition, well under the `<= 30` frame cap), `0` otherwise. |
| `0x0203FC0A` | `0x00A` | `2` | `u16` | `lagCounter` | Cumulative count of frames outside declared loading frames where logic took more than 1 VBlank. |
| `0x0203FC0C` | `0x00C` | `1` | `u8` | `screenId` | Current UI screen: `0=TITLE`, `1=SLOTS`, `2=STARTER`, `3=OVERWORLD`, `4=DIALOG`, `5=BATTLE`, `6=MENU`, `7=DEX`, `8=PARTY`, `9=BOX`, `10=BAG`, `11=SHOP`, `12=LEARN_MOVE`, `13=OPTIONS`, `14=CONTROLS`, `15=CREDITS`, `16=NAME_ENTRY`. |
| `0x0203FC0D` | `0x00D` | `1` | `u8` | `mapId` | Current map index (`0..55` in `MAPS` order). |
| `0x0203FC0E` | `0x00E` | `1` | `u8` | `x` | Player tile X coordinate on current map. |
| `0x0203FC0F` | `0x00F` | `1` | `u8` | `y` | Player tile Y coordinate on current map. |
| `0x0203FC10` | `0x010` | `1` | `u8` | `facing` | Player facing direction: `0=down`, `1=up`, `2=left`, `3=right`. |
| `0x0203FC11` | `0x011` | `1` | `u8` | `isNight` | Day/Night state: `0=Day`, `1=Night`. |
| `0x0203FC12` | `0x012` | `1` | `u8` | `sealsCount` | Number of Kitchen Seals earned (`0..8`). |
| `0x0203FC13` | `0x013` | `1` | `u8` | `sealsMask` | 8-bit bitmask of earned Kitchen Seals (`bit 0..7`). |
| `0x0203FC14` | `0x014` | `4` | `u32` | `gold` | Player gold (`G`). |
| `0x0203FC18` | `0x018` | `1` | `u8` | `championBeaten` | `1` if Champion Aurelia has been defeated, `0` otherwise. |
| `0x0203FC19` | `0x019` | `1` | `u8` | `partyCount` | Number of bEATsts currently in the player's party (`0..6`). |
| `0x0203FC1A` | `0x01A` | `2` | `u16` | `questsDoneMask` | 16-bit bitmask of completed quests (`bit i = 1` iff `QUESTS[i]` is complete). |
| `0x0203FC1C` | `0x01C` | `4` | `u32` | `questStateHash` | Live FNV-1a 32-bit digest computed over all 16 quests (`started` flag, `completed` flag, and `step` counter `0..3` for `q_0..q_15`). |
| `0x0203FC20` | `0x020` | `20` | `u8[20]` | `dexSeenBits` | 160-bit bitmap of seen species (`speciesId` `1..151` at bit `speciesId - 1`). |
| `0x0203FC34` | `0x034` | `20` | `u8[20]` | `dexCaughtBits` | 160-bit bitmap of caught species (`speciesId` `1..151` at bit `speciesId - 1`). |
| `0x0203FC48` | `0x048` | `72` | `PartyMbx[6]` | `party` | 6 party slots (`12` bytes each): `+0: u8 speciesId`, `+1: u8 level`, `+2: u16 hp`, `+4: u16 maxHp`, `+6: u8 status`, `+7: u8 moveCount`, `+8: u8[4] moveIds`. |
| `0x0203FC90` | `0x090` | `4` | `u32` | `rngDrawsTotal` | Cumulative number of Mulberry32 PRNG draws consumed since game/battle init. |
| `0x0203FC94` | `0x094` | `4` | `u32` | `steps` | Total overworld steps taken. |
| `0x0203FC98` | `0x098` | `2` | `u16` | `boxCount` | Number of bEATsts in the storage box. |
| `0x0203FC9A` | `0x09A` | `2` | `u16` | `secretsMask` | 16-bit bitmask of found secrets (`0..11`). |
| `0x0203FC9C` | `0x09C` | `4` | `u32` | `tableDirRomAddr` | Absolute ROM address (`0x08xxxxxx`) of the Table Directory (Section 4). |

### Quest State Hash Formula (`0x0203FC1C`)
Computed fresh every frame from live quest state:
```c
uint32_t h = 0x811C9DC5u;
for (int i = 0; i < 16; i++) {
    uint8_t byte = (quest_done[i] ? 1 : 0) | (quest_started[i] ? 2 : 0) | ((quest_step[i] & 0xF) << 2);
    h ^= byte;
    h *= 0x01000193u;
}
```

## 2. Battle State & Event Ring Buffer (`0x0203FCA0..0x0203FDBF`)

| Address | Offset | Size | Type | Field | Description |
|---|---|---|---|---|---|
| `0x0203FCA0` | `0x0A0` | `1` | `u8` | `battlePhase` | `0=NONE`, `1=MAIN`, `2=FIGHT`, `3=PLATE`, `4=BAG`, `5=PARTY`, `6=LOG`. |
| `0x0203FCA1` | `0x0A1` | `1` | `u8` | `battleCursor` | Current menu cursor inside battle (`0..3`). |
| `0x0203FCA2` | `0x0A2` | `1` | `s8` | `battleTemp` | Kitchen Temp (`-2..+2`). |
| `0x0203FCA3` | `0x0A3` | `1` | `u8` | `battleOutcome` | Pending/last battle outcome (`0=NONE`, `1=WIN`, `2=LOSE`, `3=RUN`, `4=CAUGHT`). |
| `0x0203FCA4` | `0x0A4` | `8` | `ActiveMon` | `playerActive` | Active player bEATst: `+0: u8 speciesId`, `+1: u8 level`, `+2: u16 hp`, `+4: u16 maxHp`, `+6: u8 status`, `+7: u8 partyIdx`. |
| `0x0203FCAC` | `0x0AC` | `8` | `ActiveMon` | `foeActive` | Active foe bEATst: `+0: u8 speciesId`, `+1: u8 level`, `+2: u16 hp`, `+4: u16 maxHp`, `+6: u8 status`, `+7: u8 foeIdx`. |
| `0x0203FCB4` | `0x0B4` | `4` | `u32` | `battleRngDraws` | PRNG draws consumed since the start of the current/last battle. |
| `0x0203FCB8` | `0x0B8` | `2` | `u16` | `battleEventWriteIdx` | Total battle events written (ring buffer index is `battleEventWriteIdx % 32`). |
| `0x0203FCBA` | `0x0BA` | `6` | `u8[6]` | `reservedBattle` | Reserved (`0`). |
| `0x0203FCC0` | `0x0C0` | `256` | `BattleEv[32]` | `battleEventRing` | 32-entry ring buffer of 8-byte battle events (`0x0203FCC0..0x0203FDBF`). |

### Battle Event Entry (`8` Bytes)
Each entry at `0x0203FCC0 + (idx % 32) * 8` records an atomic battle action (player move, foe move, plating attempt, treat/bag item, or switch/run):
- `+0x00` (`u8` `kind`): `1=PLAYER_MOVE`, `2=FOE_MOVE`, `3=PLATE_ATTEMPT`, `4=TREAT_USED`, `5=BAG_ITEM`, `6=SWITCH`, `7=RUN`.
- `+0x01` (`u8` `id`): Move ID (`0..123`), Item ID (`0..24`), or switched party index (`0..5`).
- `+0x02` (`u16` `damage`): Damage dealt (or HP healed for bag items).
- `+0x04` (`u8` `flags`):
  - Bits `0..2`: Effectiveness code (`0` = status/0x, `1` = 0.25x, `2` = 0.5x, `3` = 1.0x, `4` = 2.0x, `5` = 4.0x).
  - Bit `3` (`0x08`): Flavor Combo triggered (`1` = yes, `0` = no).
  - Bit `4` (`0x10`): Status inflicted (`1` = yes, `0` = no).
  - Bit `5` (`0x20`): Plating succeeded (`1` = caught, `0` = failed/N/A).
  - Bit `6` (`0x40`): Target fainted (`1` = fainted, `0` = alive).
- `+0x05` (`u8` `targetHpAfterLo`): Low byte of target's HP after the event (`target.hp & 0xFF`).
- `+0x06` (`u16` `rngDrawsAfter`): `battleRngDraws` (`u16`) immediately after this event completed.

## 3. Audio Note-Event Stream & Extra Digests (`0x0203FDC0..0x0203FFFF`)

| Address | Offset | Size | Type | Field | Description |
|---|---|---|---|---|---|
| `0x0203FDC0` | `0x1C0` | `1` | `u8` | `currentTrackId` | Currently playing track index (`0..17`, or `0xFF` if none). |
| `0x0203FDC1` | `0x1C1` | `1` | `u8` | `lastSfxId` | Most recently triggered SFX index (`0..11`, or `0xFF` if none). |
| `0x0203FDC2` | `0x1C2` | `2` | `u16` | `audioEventWriteIdx` | Total audio note-step events written to `audioEventRing` (ring index `audioEventWriteIdx % 64`). |
| `0x0203FDC4` | `0x1C4` | `12` | `u8[12]` | `playerName` | Current player name (`char[12]`, null-terminated ASCII). |
| `0x0203FDD0` | `0x1D0` | `48` | `u8[48]` | `bagSummary` | First 24 item counts (`u16[24]`) for direct inspection. |
| `0x0203FE00` | `0x200` | `512` | `AudioEv[64]` | `audioEventRing` | 64-entry ring buffer of 8-byte note events (`0x0203FE00..0x0203FFFF`) written by the PSG music sequencer as each channel step triggers. |

### Audio Note-Event Entry (`8` Bytes)
Each entry at `0x0203FE00 + (idx % 64) * 8`:
- `+0x00` (`u8` `trackId`): Track index (`0..17`).
- `+0x01` (`u8` `channel`): Channel index (`0=pulse1`, `1=pulse2`, `2=wave`, `3=noise`).
- `+0x02` (`u8` `midiOrOn`): MIDI note number (or `0`/`1` for noise).
- `+0x03` (`u8` `durationSteps`): Duration in half-beat steps (`d`).
- `+0x04` (`u16` `noteIndex`): Note index within that channel's sequence (`0..N-1`).
- `+0x06` (`u16` `stepFrame`): Track frame counter when the note was triggered.

## 4. ROM Table Directory (`tableDirRomAddr`)

The word at mailbox `0x0203FC9C` (and at fixed ROM offset `0x080000C4`) points to the **Table Directory** in ROM. The Table Directory begins with magic `0x52494454` (`"TDIR"`) followed by `u32 count` (`18` tables) and `count` entries of `(u32 id, u32 romOffset, u32 byteLength, u32 itemCount)`:

| Table ID | Name | Contents |
|---|---|---|
| `0` | `FONT_SANS` | `768` bytes (`96 × 8`), byte-identical to `FONT_SANS_BYTES`. |
| `1` | `FONT_SERIF` | `1,536` bytes (`96 × 16`), byte-identical to `FONT_SERIF_BYTES`. |
| `2` | `TYPES` | `12` type names + `12 × 12` effectiveness matrix (`0.5->1, 1.0->2, 2.0->4`) + `FLAVOR_COMBOS`. |
| `3` | `MOVES` | `124` moves (id, name, type, power, acc, pp, temp, cat, anim, status, sChance, drain, desc). |
| `4` | `BEATSTS` | `151` species (id, name, family, types, stats, catchRate, evo, learnset, nightOnly, minTier, shape, dex). |
| `5` | `SPECIES_SPRITES` | `151` species palettes (`16 × u16` BGR555 + hex strings) and `32×32` front & back 4bpp pixel grids (`1,024` pixels each). |
| `6` | `TILES_8X8` | `74` `8×8` tiles (`64` 4-bit indices each) + `TILE_PALETTE` + `TILE_ROLES` + `SOLID_TILES`. |
| `7` | `CHAR_SPRITES` | `47` character sprite definitions + `4 × 3` `16×24` grids. |
| `8` | `ITEMS` | `25` items (id, name, kind, tier, plateBonus, price, healHp, moveId, desc). |
| `9` | `REGIONAL_SHOPS` | `5` regional shops (region id, clerkLine, stock item indices). |
| `10` | `MAPS` | `56` maps (id, name, region, music, w, h, dark, wildPool, grid, portals, npcs, signs, and all dialogue strings). |
| `11` | `TRAINERS` | `33` trainers (id, name, title, seal, sealIdx, rewardGold, intro, win, after, party). |
| `12` | `QUESTS` | `16` quests (id, name, steps, reward, map). |
| `13` | `SECRETS` | `12` secrets (id, name, map). |
| `14` | `MUSIC_TRACKS` | `18` music tracks (id, bpm, loop, pulse1, pulse2, wave, noise note arrays). |
| `15` | `SFX_DEFS` | `12` SFX definitions (id, bpm, pulse1, pulse2, wave, noise note arrays). |

## 5. Declared Loading Frames

During a map transition (`portal` warp), the ROM sets `loadingFlag = 1` (`0x0203FC09`) and `acceptingInput = 0` (`0x0203FC08`) for **1 frame** while copying the new map's tilemap into VRAM (`<= 30` frames per the specification). Outside declared map transitions, `loadingFlag` is always `0` and `lagCounter` remains `0`.
