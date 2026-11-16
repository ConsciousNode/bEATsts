# bEATsts GBA: Packed Binary Save Format (`SAVE.md`)

`beatsts.gba` stores three independent save slots in 32 KB battery-backed cartridge SRAM (`0x0E000000..0x0E007FFF`), identified in the ROM image by the standard GBA save signature string `SRAM_V113`.

Each save slot occupies a fixed **4,096-byte (`0x1000`)** region in SRAM:

| Slot | SRAM Address Range | Byte Offset in `.sav` | Size (Bytes) |
|---|---|---|---|
| Slot 0 | `0x0E000000..0x0E000FFF` | `0x0000..0x0FFF` | `4,096` (`0x1000`) |
| Slot 1 | `0x0E001000..0x0E001FFF` | `0x1000..0x1FFF` | `4,096` (`0x1000`) |
| Slot 2 | `0x0E002000..0x0E002FFF` | `0x2000..0x2FFF` | `4,096` (`0x1000`) |
| Unused / Reserved | `0x0E003000..0x0E007FFF` | `0x3000..0x7FFF` | `20,480` (`0x5000`, filled with `0xFF`) |

Because GBA SRAM sits on an 8-bit data bus, all reads and writes in the ROM use byte instructions (`LDRB` / `STRB`). All multi-byte integers in the save format are little-endian.

## Slot Validation & Checksum

A slot is considered **valid** if and only if all three conditions hold:
1. `magic` (`0x000..0x003`) equals `0x54414542` (ASCII `"BEAT"`).
2. `version` (`0x004`) equals `0x22` (representing bEATsts 2.2).
3. `checksum` (`0x008..0x00B`) equals the unsigned 32-bit FNV-1a hash computed over bytes `0x00C..0xFFF` (`4,084` bytes):
   ```c
   uint32_t hash = 0x811C9DC5u;
   for (uint32_t i = 0x00C; i < 0x1000; i++) {
       hash ^= slot_bytes[i];
       hash *= 0x01000193u;
   }
   ```
If a slot is blank (`0xFF`) or fails any of the three checks above, the ROM treats that slot as empty (`[ NEW GAME ]`) and starts fresh without crashing.

## Slot Layout (`0x000..0xFFF`, 4,096 Bytes)

| Offset | Length | Type | Field | Description |
|---|---|---|---|---|
| `0x000` | `4` | `u32` | `magic` | Magic word `0x54414542` (`"BEAT"`). |
| `0x004` | `1` | `u8` | `version` | Save format version byte (`0x22`). |
| `0x005` | `1` | `u8` | `slotIdx` | Slot index (`0`, `1`, or `2`). |
| `0x006` | `2` | `u16` | `reserved0` | Reserved (`0x0000`). |
| `0x008` | `4` | `u32` | `checksum` | FNV-1a 32-bit checksum over bytes `0x00C..0xFFF`. |
| `0x00C` | `12` | `char[12]` | `name` | Null-terminated ASCII player name (up to 10 characters, default `"Brie"`). |
| `0x018` | `4` | `u32` | `playTimeSec` | Play time in whole seconds. |
| `0x01C` | `4` | `u32` | `rngState` | Current 32-bit Mulberry32 PRNG state (`rngSeed` on fresh load/export). |
| `0x020` | `4` | `u32` | `steps` | Total overworld steps taken. |
| `0x024` | `4` | `u32` | `gold` | Player gold (`G`). |
| `0x028` | `1` | `u8` | `mapId` | Current map index (`0..55` in `MAPS` order). |
| `0x029` | `1` | `u8` | `x` | Player tile X coordinate on current map. |
| `0x02A` | `1` | `u8` | `y` | Player tile Y coordinate on current map. |
| `0x02B` | `1` | `u8` | `dir` | Player facing direction (`0=down`, `1=up`, `2=left`, `3=right`). |
| `0x02C` | `1` | `u8` | `isNight` | Day/Night flag (`0=Day`, `1=Night`). |
| `0x02D` | `1` | `u8` | `playerLook` | Player sprite variant (`0=player_0`, `1=player_1`, `2=player_2`). |
| `0x02E` | `1` | `u8` | `championBeaten` | Champion Aurelia defeated flag (`0` or `1`). |
| `0x02F` | `1` | `u8` | `sealsMask` | 8-bit bitmask of earned Kitchen Seals (`bit 0` = Crisp Seal .. `bit 7` = Stock Seal). |
| `0x030` | `8` | `u8[8]` | `switchesBits` | 64-bit bitmap of active dungeon/gym floor switches indexed by `mapId` (`0..55`). |
| `0x038` | `8` | `u8[8]` | `defeatedTrainersBits` | 64-bit bitmap of defeated trainers indexed by `TRAINERS` order (`0..32`). |
| `0x040` | `2` | `u16` | `secretsMask` | 16-bit bitmap of discovered secrets indexed by `SECRETS` order (`0..11`). |
| `0x042` | `2` | `u16` | `questsDoneMask` | 16-bit bitmap of completed quests (`state.quests[qid] === true`, `0..15`). |
| `0x044` | `2` | `u16` | `questsStartedMask` | 16-bit bitmap of started quests (`state.quests[qid + '_started'] === true`, `0..15`). |
| `0x046` | `16` | `u8[16]` | `questSteps` | Step progress (`0..3`) for each of the 16 quests (`state.quests[qid + '_step']`). |
| `0x056` | `20` | `u8[20]` | `dexSeenBits` | 160-bit bitmap of seen species (`speciesId` `1..151` mapped to bit `speciesId - 1`). |
| `0x06A` | `20` | `u8[20]` | `dexCaughtBits` | 160-bit bitmap of caught species (`speciesId` `1..151` mapped to bit `speciesId - 1`). |
| `0x07E` | `50` | `u16[25]` | `bagCounts` | Item quantities (`u16` each) for all 25 items in canonical `ITEMS` order (`0..24`). |
| `0x0B0` | `1` | `u8` | `partyCount` | Number of bEATsts in party (`0..6`). |
| `0x0B1` | `1` | `u8` | `boxCount` | Number of bEATsts in storage box (`0..151`). |
| `0x0B2` | `2` | `u16` | `reserved1` | Padding for 4-byte alignment (`0x0000`). |
| `0x0B4` | `288` | `Mon[6]` | `party` | Up to 6 party bEATst records (`6 × 48` bytes). |
| `0x1D4` | `3624` | `Mon[151]` | `box` | Up to 151 box bEATst records (`151 × 24` bytes). |
| `0xFFC` | `4` | `u32` | `reserved2` | Trailing padding (`0x00000000`). |

## Party bEATst Record (`48` Bytes)

Each of the 6 party slots (`0x0B4 + i * 48`) stores the full state of a party bEATst:

| Rel Offset | Length | Type | Field | Description |
|---|---|---|---|---|
| `+0x00` | `4` | `u32` | `uid` | Unique instance ID (`0..999,999,999`). |
| `+0x04` | `1` | `u8` | `speciesId` | Species ID (`1..151`). |
| `+0x05` | `1` | `u8` | `level` | Current level (`1..100`). |
| `+0x06` | `1` | `u8` | `status` | Status ID (`0=None`, `1=Sizzling`, `2=Brined`, `3=Drowsy`, `4=Seasoned`, `5=Appetized`). |
| `+0x07` | `1` | `u8` | `lastMoveType` | Last move type used (`0..11`, or `0xFF` for `null`). |
| `+0x08` | `2` | `u16` | `hp` | Current HP. |
| `+0x0A` | `2` | `u16` | `maxHp` | Maximum HP. |
| `+0x0C` | `2` | `u16` | `atk` | Attack stat. |
| `+0x0E` | `2` | `u16` | `def` | Defense stat. |
| `+0x10` | `2` | `u16` | `spd` | Speed stat. |
| `+0x12` | `2` | `u16` | `moveCount` | Number of moves known (`1..4`). |
| `+0x14` | `4` | `u32` | `xp` | Current XP. |
| `+0x18` | `4` | `u32` | `nextXp` | XP required for next level. |
| `+0x1C` | `4` | `u8[4]` | `moveIds` | Move IDs (`0..123`, `0xFF` if empty) for slots `0..3`. |
| `+0x20` | `4` | `u8[4]` | `movePps` | Current PP for slots `0..3`. |
| `+0x24` | `4` | `u8[4]` | `moveMaxPps` | Max PP for slots `0..3`. |
| `+0x28` | `8` | `char[8]` | `nickOverride` | Zero-filled if nickname equals `BEATSTS_BY_ID[speciesId].name`; otherwise custom prefix. |

## Box bEATst Record (`24` Bytes)

Each of the 151 box slots (`0x1D4 + i * 24`) stores a compact 24-byte bEATst record:

| Rel Offset | Length | Type | Field | Description |
|---|---|---|---|---|
| `+0x00` | `4` | `u32` | `uid` | Unique instance ID. |
| `+0x04` | `1` | `u8` | `speciesId` | Species ID (`1..151`). |
| `+0x05` | `1` | `u8` | `level` | Current level (`1..100`). |
| `+0x06` | `1` | `u8` | `status` | Status ID (`0..5`). |
| `+0x07` | `1` | `u8` | `moveCount` | Number of moves known (`1..4`). |
| `+0x08` | `2` | `u16` | `hp` | Current HP. |
| `+0x0A` | `2` | `u16` | `maxHp` | Maximum HP. |
| `+0x0C` | `2` | `u16` | `atk` | Attack stat. |
| `+0x0E` | `2` | `u16` | `def` | Defense stat. |
| `+0x10` | `2` | `u16` | `spd` | Speed stat. |
| `+0x12` | `2` | `u16` | `xpDiv8` | `xp / 8` (or exact XP reconstructed from `level * level * 8` + offset). |
| `+0x14` | `4` | `u8[4]` | `moveIds` | Move IDs (`0..123`, `0xFF` if empty) for slots `0..3` (PP restored to `MOVES[id].pp` or stored in high bits). |

## HTML Save Converter (`tools/html-save-to-sav.py`)

`tools/html-save-to-sav.py` converts an exported HTML save JSON (`Game.exportSaveJson()`) into a 32 KB `.sav` image (or updates a specific slot in an existing `.sav` file), and also supports `--to-json` for inspecting or round-tripping a `.sav` slot back to JSON:

```bash
python3 tools/html-save-to-sav.py input.json -o beatsts.sav [--slot 0]
```
