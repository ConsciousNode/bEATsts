# bEATsts: GBA-Exportable Data Formats (`DATA.md`)

All game data in `beatsts.html` is stored in flat, deterministic tables designed for direct export to C structs / ROM arrays for a Game Boy Advance (`240×160`) build.

## 1. Screen, Tile & Palette Format
- **Logical Display**: `240 × 160` pixels (`30 × 20` 8×8 tiles; overworld uses `30 × 18` map tiles + `16px` top HUD bar).
- **Tile Format**: `8 × 8` 4-bit indexed pixels (`Uint8Array(64)`), index `0` = transparent, indices `1..15` = palette entries.
- **Sprite Format**: `24 × 24` pixels (`3 × 3` 8×8 GBA tiles, `Uint8Array(576)`), front & back views per species.
- **Color Space**: 15-bit RGB (`5 bits/channel`, masked `& 0xF8` in 24-bit hex `#RRGGBB`), max `16` colors per sprite or tilemap palette (`1` transparent + `15` opaque).

## 2. Species Table (`RAW_BEATSTS` / `BEATSTS`)
Each of the 151 entries maps to a fixed-size C struct:
```c
typedef struct {
  uint8_t  id;          // 1..151 (#151 is secret)
  char     name[16];    // Unique ASCII name
  uint8_t  family;      // 0=Sandwiches, 1=Dumplings, 2=Noodles, 3=Soup
  uint8_t  type1, type2;// 0..11 (TYPES enum)
  uint8_t  hp, atk, def, spd;
  uint8_t  catchRate_q8;// round(catchRate * 255)
  uint8_t  evoTo;       // 0 if none, else 1..151
  uint8_t  evoLevel;    // 0 if none
  uint8_t  learnset[4]; // Move IDs (0..50)
  uint8_t  nightOnly;   // 0 or 1
  uint8_t  minTier;     // 1..5
  uint16_t palette[16]; // 15-bit BGR555
} BeatstSpecies;
```

## 3. Types & Type Chart (`TYPES`, `TYPE_CHART`)
- **12 Types**: `Toasted (0)`, `Steamed (1)`, `Fried (2)`, `Pickled (3)`, `Spicy (4)`, `Brothy (5)`, `Raw (6)`, `Fermented (7)`, `Sweet (8)`, `Savory (9)`, `Chilled (10)`, `Herbal (11)`.
- **Matrix**: `uint8_t TYPE_CHART[12][12]` encoded as `1 = 0.5x`, `2 = 1.0x`, `4 = 2.0x` (fixed-point `Q1`).

## 4. Moves Table (`MOVES`)
`51` moves with `id`, `name`, `type`, `power`, `acc`, `pp`, `temp` (`-2..+2` Kitchen Temp shift), `cat` (`physical`/`special`/`status`), `anim`, `status`, `sChance`, `drain`.

## 5. Maps & Trainers (`MAPS`, `TRAINERS`)
- **Maps**: `30 × 18` `uint8_t` tile grid (`TILES_8X8` IDs `0..11`), `portals` (`x, y, to, tx, ty, reqSeals`), `wildPool` (`[speciesId, minLv, maxLv]`), and `npcs`.
- **Trainers**: `8` Head Chefs (`chef_greg` .. `chef_bouillon`), `4` Rival Saffron encounters (`rival_1` .. `rival_4`), `3` Master Tasters (`taster_pip`, `taster_roux`, `taster_mochi`), and `Champion Chef Aurelia` (`champion_aurelia`).

## 6. Chiptune Audio Tables (`MUSIC_TRACKS`, `SFX_DEFS`)
- **4 Declared GBA Channels**: `pulse1` (50% duty), `pulse2` (25% duty), `wave` (4-bit 32-sample wavetable `GBA_WAVETABLE`), `noise` (15-bit LFSR).
- **Note Format**: `[midiNote, durationSteps]` (`midiNote = 0` for rest; `noise` uses `1 = trigger`, `0 = rest`).
- **14 Music Tracks** & **12 Sound Effects**, deterministically renderable offline at `22050 Hz`.

## 7. Save Format (`beatsts_save_v1_slot_0..2`)
JSON-serializable struct (exportable/importable via `.json` file) containing `slot`, `name`, `playTimeSec`, `rngSeed`, `steps`, `isNight`, `gold`, `mapId`, `x`, `y`, `dir`, `seals[]`, `defeatedTrainers[]`, `quests{}`, `championBeaten`, `dexSeen[]`, `dexCaught[]`, `party[]`, `box[]`, and `bag{}`.
