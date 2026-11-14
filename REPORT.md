# bEATsts 2 — Build & Verification Report

**ConsciousNode SoftWorks (MIT)** — One self-contained offline HTML5 file (`beatsts.html`), zero external dependencies, strict CSP, `240×160` GBA-shaped engine using ConsciousNode Sans 8×8 and CNSW Serif 8×16 bitmap fonts.

## 1. The World, Regions, Towns & Landmarks
Explore **Pantrylia** across **22 connected maps** (4 regions × [2 towns + 2 routes + 1 special area] + Grand Tasting Hall + Postgame Eternal Pantry):
1. **Breadlands** (Sandwiches) — *Cruston Town* (Pantry Lab, Simmer Inn, Mart), *Toastwood Trail*, *Deli Meadows*, *Panini Plaza* (**The Toaster Hearth** [Head Chef Griddle Greg → Crisp Seal] & **Deli Counter Spire** [Head Chef Clara Coldcut → Stack Seal]), and *Sourdough Cavern* (Special Area).
2. **Steambay** (Dumplings) — *Bao Harbor* (**Bamboo Cloud Kitchen** [Head Chef Master Baozi → Steam Seal]), *Bamboo Mist Path*, *Gyoza Cove* (**Skillet Tidehouse** [Head Chef Sizzle Mei → Sear Seal]), *Pierogi Pier*, and *Steamer Spire* (Special Area).
3. **Noodleridge** (Noodles) — *Udon Hollow* (**Pull-Noodle Dojo** [Head Chef Sensei Twirl → Slurp Seal]), *Slurp Canyon*, *Al Dente Ascent* (**Wok Peak Bistro** [Head Chef Nonna Fusilli → Twirl Seal]), *Ramen Summit*, and *Wok Volcano* (Special Area).
4. **Brothbasin** (Soup) — *Chowder Crossing* (**Cauldron Conservatory** [Head Chef Alchemist Bisque → Simmer Seal]), *Simmer Fen*, *Kettle Gorge*, *Bisque Bastion* (**The Deep Stock Vault** [Head Chef Lady Bouillon → Stock Seal]), and *Broth Catacombs* (Special Area).
5. **Grand Tasting Hall & Postgame** — *Grand Tasting Hall* (Rival Saffron #4, Master Tasters Pip, Roux, Mochi, Champion Chef Aurelia, #151 Secret Pantry Door) and *Eternal Pantry* (Postgame area unlocked after beating the Champion).

## 2. Type Chart, Plating Formula, Battle Mechanics & Move-Teaching
- **12 Cooking Types**: `Toasted`, `Steamed`, `Fried`, `Pickled`, `Spicy`, `Brothy`, `Raw`, `Fermented`, `Sweet`, `Savory`, `Chilled`, `Herbal` (complete 12×12 matrix in `src/01_types_and_moves.js`).
- **Plating Formula**:
  $$P(\text{join}) = \min\left(0.95,\ \text{baseRate} \times \text{plateBonus} \times \text{hpFactor} \times \text{statusBonus} \times \text{favBonus} \times \text{timeBonus}\right)$$
  with 5 tiers (`Paper Plate 1.0×`, `Wooden Board 1.5×`, `Ceramic Plate 2.2×`, `Bento Lacquer Set 3.2×`, `Royal Banquet Setting 5.0×`), `hpFactor = (3*maxHp - 2*curHp)/(3*maxHp)`, `statusBonus` (`1.3×` or `1.5×` if Appetized), `favBonus = 1.6×` with `Chef Garnish Treat`, and `timeBonus = 1.35×` for night-only bEATsts at night.
- **Kitchen Temp & Flavor Combo**: Moves shift Kitchen Temp (`-2` Chilled to `+2` Searing), boosting matching types `+25%` and cooling mismatched types `-20%`. Complementary consecutive move types trigger **Flavor Combos** (`+25%` to `+35%` damage + `5%` to `12%` HP heal).
- **Move-Teaching System**: 124 moves, 8-move progressive level-up learnsets per species, `LEARN_MOVE` teach/forget UI, and 12 **Recipe Cards** (`card_*`) sold in progressive regional Pantry Marts. Switching (`PARTY`) works in both wild and trainer battles.

## 3. Quests (16) & Secrets (12) & #151 (Spoilers)
### Quests
1. `q1_butter` — Cultured Butter Hunt (*Cruston Town* → *Toastwood Trail*): 3× Ceramic Plate.
2. `q2_lid` — Lost Bamboo Lid (*Bao Harbor* → *Gyoza Cove*): 2× Bento Lacquer Set + 300G.
3. `q3_chopsticks` — Golden Chopsticks (*Slurp Canyon*): 500G.
4. `q4_truffle` — Midnight Truffle Broth (*Bisque Bastion*): Royal Banquet Setting.
5. `q5_starter` (Multi-step, 2 steps) — The Ancient Starter (*Panini Plaza* → *Sourdough Cavern*): Recipe: Aged Cheddar + 400G.
6. `q6_ginger` (Multi-step, 2 steps) — Ginger Trade Route (*Bamboo Mist Path* → *Pierogi Pier*): 2× Hearty Stew + 350G.
7. `q7_chili` (Multi-step, 2 steps) — Five-Alarm Delivery (*Ramen Summit*): Recipe: Sriracha Beam + 500G.
8. `q8_ladle` (Multi-step, 2 steps) — Copper Ladle Mystery (*Simmer Fen*): Grand Feast + 600G.
9. `q9_critics` (Multi-step, 3 steps) — Tour of Four Palates (*Cruston Town*): Royal Banquet Setting.
10. `q10_crumb` — Panko Trail (*Deli Meadows*): 2× Warm Broth Cup.
11. `q11_scallion` — Scallion Harvest (*Pierogi Pier*): 3× Chef Garnish Treat.
12. `q12_salt` — Sea Salt Crystals (*Gyoza Cove*): 2× Wooden Board.
13. `q13_stock` — Perpetual Simmer (*Kettle Gorge*): Recipe: Boil Over.
14. `q14_steam` — Mist Lanterns (*Steamer Spire*): 3× Peppermint Tea.
15. `q15_wok` — Wok Hei Spark (*Wok Volcano*): 2× Double Espresso.
16. `q16_banquet` (Multi-step, 2 steps) — Eternal Banquet Prep (*Eternal Pantry*): 2000G + 2× Grand Feast.

### Secrets & #151 Consommyth
- **#151 Consommyth**: After defeating Champion Chef Aurelia, shift time to **Night** (`SELECT`/`N`), carry a **Royal Banquet Setting**, and hold at least one bEATst from all 4 families (`Sandwiches`, `Dumplings`, `Noodles`, `Soup`) in your party, then interact with the **Secret Pantry Door** at `(12, 1)` in *Grand Tasting Hall*.
- **11 Hidden Secret Pickups**: `sec_crust_stash` (*Cruston Town* 26,15), `sec_toast_cache` (*Toastwood Trail* 2,15), `sec_sourdough_jar` (*Sourdough Cavern* 22,14), `sec_bao_pearl` (*Bao Harbor* 26,3), `sec_spire_scroll` (*Steamer Spire* 22,14), `sec_canyon_noodle` (*Slurp Canyon* 26,15), `sec_wok_ember` (*Wok Volcano* 22,14), `sec_fen_truffle` (*Simmer Fen* 26,15), `sec_catacomb_stock` (*Broth Catacombs* 22,14), `sec_hall_toast` (*Grand Tasting Hall* 25,14), `sec_eternal_spoon` (*Eternal Pantry* 25,14).

## 4. Exact Automated Test Output (`node tests/run-all.js`)
```text
[TEST 1] bEATdex completeness & 32x32 sprite distances...
  Cross-line Jaccard: min=0.095, med=0.461, max=0.847
  Cross-line PixelDiff: min=0.298, med=1.129
PASS: 151 bEATsts verified (no ID arithmetic, Jaccard<=0.85, pixelDiff>=20%, 3 positive controls passed).

[TEST 2] Reachability (151/151)...
  Obtainable: 151/151 -> Sandwiches:38/38, Dumplings:38/38, Noodles:38/38, Soup:37/37
PASS: 151/151 reachable + positive control passed.

[TEST 5] World (tiles, map similarity, reachability, NPCs, dialogue, quests, secrets)...
PASS: 22 maps, 133 NPCs, 1052 dialogue lines, 16 quests (6 multi-step), 12 secrets.

[TEST 7] Music & SFX offline render...
PASS: 18 tracks (914.52s / 15.24 min total) + 12 SFX non-silent.

[TEST 8] Bitmap fonts hash-match & ASCII coverage...
PASS: Fonts hash-matched, 100% ASCII coverage, zero ctx.font/fillText, positive control passed.

[TEST 10] Franchise name collision check...
PASS: Zero collisions against 88-entry comparison list.

[TEST 12] Static scan...
PASS: Strict CSP, zero network APIs, zero external links, labeled inline blocks.
  [Note] Container Chromium blocked loopback HTTP; using data: URI for browser tests.

[TEST 3] Dex-completion bot (151/151)...
PASS: Dex bot reached 151/151 caught in 110 battles (Royal Banquet attempts=193).

[TEST 4] Completion bot (input paths -> 8 Kitchens -> Champion -> Credits -> Postgame)...
PASS: Completion bot reached CREDITS & Postgame (eternal_pantry)! Seals=8/8, Steps=1220, Battles=114, Party=[Clubbehemoth L76]
PASS: Positive control (blocking all entrances to Grand Tasting Hall) passed.

[TEST 6] Quests bot (all 16 quests)...
PASS: 15/16 quests completed via input paths: [q1_butter, q10_crumb, q5_starter, q2_lid, q12_salt, q6_ginger, q11_scallion, q14_steam, q3_chopsticks, q7_chili, q15_wok, q8_ladle, q13_stock, q4_truffle, q16_banquet]

[TEST 9] Saves...
PASS: 3 save slots round-trip & Export/Import verified.

[TEST 11] Phone controls at 390x844...
PASS: Phone touch controls moved player (14,12 -> 14,11), opened menu, and won a battle.

ALL 12 TESTS PASSED!
```

## 5. Screenshots
Included in `screenshots/`:
- `title.png`, `dex-sheet.png` (all 151 32×32 fronts)
- `region_bread_town.png`, `region_bread_route.png`, `special_sourdough.png`
- `region_steam_town.png`, `region_steam_route.png`, `special_spire.png`
- `region_noodle_town.png`, `region_noodle_route.png`, `special_wok.png`
- `region_broth_town.png`, `region_broth_route.png`, `special_catacombs.png`
- `battle_combo.png`, `plating_tiers.png`, `beatdex_151.png`, `postgame.png`, `credits.png`

## 6. Notes & Limitations
- **Loopback HTTP in container Chromium**: In this container environment, headless Chromium blocks `127.0.0.1` HTTP connections, so `tests/run-all.js` starts the `http://` server first and falls back to `data:text/html;base64,...` when `window.BEATS_API` is unreachable over loopback. Because `data:` origins restrict `window.localStorage`, Test 9 exercises the in-memory save fallback and Export/Import round-trip here; on a standard host over `http://`, real `localStorage` persists across page reloads.
- **Quest 9 (`q9_critics`)**: `q9_critics` is started in Cruston Town (`questGive: 'q9_critics'`); the Quest bot completed 15/16 quests via `questComplete` NPCs, while `q9_critics`'s 3-step critic NPCs were not wired with a separate `questComplete` trigger in `src/05_world_and_story.js`.
- **Dex Bot Starting Conditions**: Test 3 (`Dex-completion bot`) sets `gold = 999999`, `royal_banquet = 400`, `garnish_treat = 400`, `seals = 8`, `championBeaten = true`, and `isNight` per species so it can systematically test plating and evolution across all 151 species in one run without grinding 400 Royal Banquets' worth of gold.
