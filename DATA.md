# bEATsts 2.2: GBA-Exportable Data Formats (`DATA.md`)

All game data in `beatsts.html` is stored in flat, deterministic tables designed for direct export to C structs / ROM arrays for a Game Boy Advance (`240×160`) build.

## 1. Screen, Tiles, Fonts & Palettes
- **Logical Display**: `240 × 160` pixels (`30 × 20` 8×8 tiles; overworld uses `30 × 18` visible map viewport + `20px` top HUD bar with smooth scrolling camera on larger maps).
- **Bitmap Fonts**:
  - `FONT_SANS_BYTES` (`768` bytes, `8×8`, ASCII `32..127`) from `consciousnode-sans-8x8.hex` (`SHA-256: 1f64a9bd9d622ebadcd06fb7ab6f2afeecab22dc08ed98ab1fc0aa4f1eb3da04`)
  - `FONT_SERIF_BYTES` (`1,536` bytes, `8×16`, ASCII `32..127`) from `cnsw-serif-8x16.hex` (`SHA-256: 612a7db38f3dd013a31ff9cdeefda1ca7a0bb2873549ba2fc5ab3a0f124d5195`)
  - Zero `ctx.font`, `fillText`, `strokeText`, or `@font-face` calls; all text rendered via 1-bit glyph bitmaps.
- **Map Tiles (`TILES_8X8`) & Roles (`TILE_ROLES`)**:
  - `8 × 8` 4-bit indexed pixels (`Uint8Array(64)`), covering core tiles (`0..9`), regional tiles (`Breadlands` `10..21`, `Steambay` `22..33`, `Noodleridge` `34..45`, `Brothbasin` `46..57`, `Endgame/Postgame` `58..63`), and puzzle/interior tiles (`64..79`).
  - `TILE_ROLES` maps every tile ID to its semantic role (`grass`, `tall_grass`, `path`, `plaza`, `water`, `bridge`, `tree`, `building`, `wall`, `carpet`, `ledge`, `oil`, `conveyor`, `gate`, `sign`, `heal`, `mart`, `stairs`, `table`).
- **bEATst Sprites**: `32 × 32` pixels (`4 × 4` GBA `8×8` tiles, `Uint8Array(1024)`), front & back views per species, max `16` colors from 15-bit RGB.
- **Character Sprites (`CHAR_SPRITES`)**: `16 × 24` pixels (`2 × 3` GBA `8×8` tiles) with 4 walk directions (`down`, `up`, `left`, `right`) × 3 animation frames (`stand`, `stepL`, `stepR`) across 18 unique named characters and 12 generic villager archetypes.

## 2. Species, Moves, Items & World Tables
- **Species (`BEATSTS`)**: `151` entries, each with 8-move progressive level-up `learnset: [[lv, moveId], ...]`, `types`, `stats`, `evo`, `catchRate`, `nightOnly`, `minTier`, and authored `shape`.
- **Moves (`MOVES`)**: `124` cooking-themed moves (`0..123`) across 12 types, plus `12` teachable `card_*` Recipe Cards (`ITEMS`).
- **World (`MAPS`, `QUESTS`, `SECRETS`)**:
  - `56` hand-designed maps (`8` towns, `8` routes, `12` dungeon floors, `8` gym interiors, `18` town interiors, *Grand Tasting Hall*, and *Eternal Pantry*) with `110` bidirectional portals (`110/110` reachable), max same-size role similarity `0.499 <= 0.50`, and max sliding-window different-size role similarity `0.496 <= 0.50`.
  - `916` displayed dialogue strings (`906` unique, `899` unique after collapsing template families).
  - `16` quests (`6` multi-step chains spanning multiple maps with strict ordered step flags `qid + '_started'` and `qid + '_step'`).
  - `12` secrets (`#151 Consommyth` Secret Pantry Door + `11` hidden world pickups).
- **Audio (`MUSIC_TRACKS`, `SFX_DEFS`)**: `18` music tracks (`914.52s` / `15.24 min` total) + `12` SFX rendered across 4 GBA channels (`pulse1`, `pulse2`, `wave`, `noise`).
