# LIFTS.md — Provenance of Reused / Adapted Code and Assets

Every file or asset copied, inlined, or adapted from an attached file in `beatsts-2-spec/` is listed below with its source and SHA-256 hash (where applicable).

| Target File | Source in `beatsts-2-spec/` | What Was Lifted / Adapted |
|---|---|---|
| `src/00_fonts.js` | `fonts/consciousnode-sans-8x8.hex` (`1f64a9bddd96cb254fc702c0dae5f585eb2e61675481b066c67f96019bf52a87`) | Exact 96-glyph, 768-byte bitmap font data inlined verbatim. |
| `src/00_fonts.js` | `fonts/cnsw-serif-8x16.hex` (`612a7db3713593c8d183aec0546929ef0ad9cd90857d53a0434ccd237f2e9369`) | Exact 96-glyph, 1,536-byte serif bitmap font data inlined verbatim. |
| `src/01_types_and_moves.js` | `beatsts-v1/src/01_types_and_moves.js` | 12 cooking types (`TYPES`), `TYPE_CHART`, `FLAVOR_COMBOS`, and moves `0..50` lifted; extended with moves `51..123`. |
| `src/02_beatsts_data.js` | `beatsts-v1/src/02_beatsts_data.js` | Species names, families, types, base stats, and dex entries lifted; upgraded with 8-move level-up learnsets and per-species `32×32` shape parameters. |
| `src/04_items_and_plating.js` | `beatsts-v1/src/04_items_and_plating.js` | Core `ITEMS` and `calcPlatingChance` lifted; extended with 12 `card_*` Recipe Cards and progressive `REGIONAL_SHOPS`. |
| `src/05_world_and_story.js` | `beatsts-v1/src/05_world_and_story.js` | `TRAINERS` roster lifted and extended with after-battle lines; maps, NPCs, quests, and secrets expanded to 22 maps, 133 NPCs, 16 quests, and 12 secrets. |
| `src/06_audio_engine.js` | `beatsts-v1/src/06_audio_engine.js` | 4-channel GBA chiptune synthesis (`pulse1`, `pulse2`, `wave`, `noise`) and offline renderer lifted; expanded to 18 tracks (15.24 min total). |
| `src/07_game_engine.js` | `beatsts-v1/src/07_game_engine.js` | Core state machine, battle loop, and save/export/import lifted; upgraded for bitmap font rendering, `32×32` sprites, `16×16` directional characters, wild switching, Recipe Cards, quests, and postgame. |
| `build.py` | `beatsts-v1/build.py` | Single-file HTML assembler with strict CSP and phone touch controls. |
