# bEATsts 2: GBA-Exportable Data Formats (`DATA.md`)

All game data in `beatsts.html` is stored in flat, deterministic tables designed for direct export to C structs / ROM arrays for a Game Boy Advance (`240×160`) build.

## 1. Screen, Tiles, Fonts & Palettes
- **Logical Display**: `240 × 160` pixels (`30 × 20` 8×8 tiles; overworld uses `30 × 18` map tiles + `16px` top HUD bar).
- **Bitmap Fonts**:
  - `FONT_SANS_BYTES` (`768` bytes, `8×8`, ASCII `32..127`) from `consciousnode-sans-8x8.hex`
  - `FONT_SERIF_BYTES` (`1,536` bytes, `8×16`, ASCII `32..127`) from `cnsw-serif-8x16.hex`
  - Zero `ctx.font` or `fillText` calls; all text rendered via 1-bit glyph bitmaps.
- **Map Tiles (`TILES_8X8`)**: `8 × 8` 4-bit indexed pixels (`Uint8Array(64)`), 12 unique tiles per region (`Breadlands` `10..21`, `Steambay` `22..33`, `Noodleridge` `34..45`, `Brothbasin` `46..57`, `Endgame/Postgame` `58..63`, plus `0..7` core).
- **bEATst Sprites**: `32 × 32` pixels (`4 × 4` GBA `8×8` tiles, `Uint8Array(1024)`), front & back views per species, max `16` colors from 15-bit RGB.
- **Character Sprites (`CHAR_SPRITES`)**: `16 × 16` pixels (`2 × 2` GBA `8×8` tiles) with 4 walk directions (`down`, `up`, `left`, `right`).

## 2. Species, Moves, Items & World Tables
- **Species (`BEATSTS`)**: `151` entries, each with 8-move progressive level-up `learnset: [[lv, moveId], ...]`, `types`, `stats`, `evo`, `catchRate`, `nightOnly`, `minTier`, and authored `shape`.
- **Moves (`MOVES`)**: `124` cooking-themed moves (`0..123`) across 12 types, plus `12` teachable `card_*` Recipe Cards (`ITEMS`).
- **World (`MAPS`, `QUESTS`, `SECRETS`)**: `22` connected maps across 4 regions + Grand Tasting Hall + Postgame Eternal Pantry, `133` NPCs, `1,052` dialogue lines, `16` quests (`6` multi-step), `12` secrets, and progressive `REGIONAL_SHOPS`.
- **Audio (`MUSIC_TRACKS`, `SFX_DEFS`)**: `18` music tracks (`914.52s` / `15.24 min` total, `52.5s–70.0s` per main track) + `12` SFX on 4 GBA channels (`pulse1`, `pulse2`, `wave`, `noise`).
