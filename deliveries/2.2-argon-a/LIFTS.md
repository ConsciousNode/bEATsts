# LIFTS.md — Provenance of Reused / Adapted Code and Assets

Every file or asset copied, inlined, or adapted from `beatsts-2.1-spec/` (`beatsts-v2/` and `fonts/`) is listed below.

| Target File | Source in `beatsts-2.1-spec/` | What Was Lifted / Adapted |
|---|---|---|
| `src/00_fonts.js` | `fonts/consciousnode-sans-8x8.hex` (`1f64a9bd…`) & `fonts/cnsw-serif-8x16.hex` (`612a7db3…`) | Carried forward byte-exact from `beatsts-v2/src/00_fonts.js`. |
| `src/01_types_and_moves.js` | `beatsts-v2/src/01_types_and_moves.js` | 12 cooking types, `TYPE_CHART`, `FLAVOR_COMBOS`, and 124 moves carried forward. |
| `src/02_beatsts_data.js` | `beatsts-v2/src/02_beatsts_data.js` | 151 species, learnsets, and shape parameters carried forward. |
| `src/03_sprites_and_tiles.js` | `beatsts-v2/src/03_sprites_and_tiles.js` | 32×32 species sprites carried forward; upgraded tileset (`TILE_ROLES`, doors/windows/stalls/puzzles) and `16×24` 4-dir × 3-frame character sprites. |
| `src/04_items_and_plating.js` | `beatsts-v2/src/04_items_and_plating.js` | Core items, Recipe Cards, and `REGIONAL_SHOPS` carried forward; added `soup_ladle` and `kitchen_lantern` key items. |
| `src/05_world_and_story.js` | `beatsts-v2/src/05_world_and_story.js` | `TRAINERS` structure lifted and expanded for 56 hand-designed maps, 8 gym interiors, 6 multi-floor dungeons, Chrome Fork Syndicate, 6 Rival Saffron battles, and 866 real displayed lines. |
| `src/06_audio_engine.js` | `beatsts-v2/src/06_audio_engine.js` | 18-track GBA chiptune engine carried forward. |
| `src/07_game_engine.js` | `beatsts-v2/src/07_game_engine.js` | Core engine carried forward; fixed `moveCooldown`, `foeIdx++`, battle/overworld HUDs, and added scrolling camera, transitions, banners, puzzles, and stretch features. |
| `build.py` | `beatsts-v2/build.py` | Single-file HTML assembler with strict CSP carried forward. |
