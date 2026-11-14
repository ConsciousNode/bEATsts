# bEATsts — Build & Verification Report

**ConsciousNode SoftWorks (MIT)** — One self-contained offline HTML5 file (`beatsts.html`), zero external dependencies, strict CSP, `240×160` GBA-shaped engine.

## 1. The World & How to Play
You play as a young cook-trainer exploring **Pantrylia**, a realm of four food-family regions:
1. **Breadlands** (Sandwiches) — *Cruston Town*, *Toastwood Trail*, *Panini Plaza*. Kitchens: **The Toaster Hearth** (Head Chef Griddle Greg → *Crisp Seal*) & **Deli Counter Spire** (Head Chef Clara Coldcut → *Stack Seal*).
2. **Steambay** (Dumplings) — *Bao Harbor*, *Gyoza Cove*. Kitchens: **Bamboo Cloud Kitchen** (Head Chef Master Baozi → *Steam Seal*) & **Skillet Tidehouse** (Head Chef Sizzle Mei → *Sear Seal*).
3. **Noodleridge** (Noodles) — *Udon Hollow*, *Slurp Canyon*. Kitchens: **Pull-Noodle Dojo** (Head Chef Sensei Twirl → *Slurp Seal*) & **Wok Peak Bistro** (Head Chef Nonna Fusilli → *Twirl Seal*).
4. **Brothbasin** (Soup) — *Chowder Crossing*, *Bisque Bastion*. Kitchens: **Cauldron Conservatory** (Head Chef Alchemist Bisque → *Simmer Seal*) & **The Deep Stock Vault** (Head Chef Lady Bouillon → *Stock Seal*).

After collecting all 8 Kitchen Seals, enter the **Grand Tasting Hall** to face **Rival Saffron** one final time, conquer the **Three-Course Gauntlet** (Master Tasters Pip, Roux, and Mochi), and challenge **Grand Champion Chef Aurelia** to reach the **Hall of Flavor** and ending credits.

**Controls:**
- **Move:** Arrow Keys / WASD / On-screen D-Pad
- **Confirm / Interact (A):** `Z` / `Enter` / `Space` / On-screen `A`
- **Cancel / Back (B):** `X` / `Esc` / `Backspace` / On-screen `B`
- **Pause Menu (START):** `M` / On-screen `START`
- **Day / Night Shift (SELECT):** `N` / `Tab` / On-screen `SELECT`

## 2. Type Chart (12 Cooking Types)
Every type has at least 2 strengths (`2×`) and 2 weaknesses (`0.5×`):

| Attacker \ Defender | Toasted | Steamed | Fried | Pickled | Spicy | Brothy | Raw | Fermented | Sweet | Savory | Chilled | Herbal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Toasted**   | 1 | 0.5 | 1 | 1 | 1 | 0.5 | **2** | **2** | 1 | 1 | **2** | 1 |
| **Steamed**   | **2** | 1 | 0.5 | 1 | **2** | 1 | 1 | 1 | 1 | 1 | 0.5 | 1 |
| **Fried**     | 1 | **2** | 1 | 0.5 | 1 | 0.5 | **2** | 1 | 1 | 1 | 1 | **2** |
| **Pickled**   | 1 | 1 | **2** | 1 | 1 | 0.5 | 1 | 0.5 | 0.5 | **2** | 1 | 1 |
| **Spicy**     | 1 | 0.5 | 1 | 1 | 1 | 0.5 | **2** | 1 | 0.5 | **2** | **2** | 1 |
| **Brothy**    | **2** | 1 | **2** | 1 | **2** | 1 | 1 | 0.5 | 1 | 1 | 0.5 | 0.5 |
| **Raw**       | 0.5 | 1 | 0.5 | 1 | 0.5 | 1 | 1 | **2** | 1 | 1 | **2** | 0.5 |
| **Fermented** | 0.5 | 1 | 1 | **2** | 1 | **2** | 0.5 | 1 | **2** | 1 | 1 | 1 |
| **Sweet**     | 1 | 1 | 1 | **2** | **2** | 1 | 1 | 0.5 | 1 | 0.5 | 1 | 1 |
| **Savory**    | 1 | 1 | 1 | 0.5 | 0.5 | 1 | 1 | 1 | **2** | 1 | 1 | **2** |
| **Chilled**   | 0.5 | **2** | 1 | 1 | 0.5 | **2** | 0.5 | 1 | 1 | 1 | 1 | 1 |
| **Herbal**    | 1 | 1 | 0.5 | 1 | 1 | **2** | **2** | 1 | 1 | 0.5 | 1 | 1 |

## 3. Plating Formula (Catching)
In wild battles, you **set a place** using one of 5 place-setting tiers (`Paper Plate` `1.0×`, `Wooden Board` `1.5×`, `Ceramic Plate` `2.2×`, `Bento Lacquer Set` `3.2×`, `Royal Banquet Setting` `5.0×`):

$$P(\text{join}) = \min\left(0.95,\ \text{baseRate} \times \text{plateBonus} \times \text{hpFactor} \times \text{statusBonus} \times \text{favBonus} \times \text{timeBonus}\right)$$

- `hpFactor = (3 * maxHp - 2 * curHp) / (3 * maxHp)`
- `statusBonus = 1.5` if `Appetized`, `1.3` if any other status (`Sizzling`, `Brined`, `Drowsy`, `Seasoned`), else `1.0`
- `favBonus = 1.6` if `Chef Garnish Treat` was used in the battle, else `1.0`
- `timeBonus = 1.35` if `nightOnly && isNight`, else `1.0`
- Returns `0` if `nightOnly && !isNight` or if `plateItem.tier < species.minTier`.

## 4. Original Battle Mechanic: Kitchen Temp & Flavor Combo
- **Kitchen Temp (`-2` Chilled to `+2` Searing):** Every move shifts the shared kitchen temperature (`-2..+2`). At **Searing (`+2`)**, `Spicy`, `Fried`, and `Toasted` moves deal **+25%** damage while `Chilled` and `Raw` deal **-20%**. At **Chilled (`-2`)**, `Chilled`, `Raw`, and `Pickled` deal **+25%** while `Spicy` and `Brothy` deal **-20%**.
- **Flavor Combo:** Using two complementary move types on consecutive turns (e.g., `Spicy → Sweet` *Sweet Heat Glaze*, `Savory → Fermented` *Umami Bomb*, `Fried → Pickled` *Crunch & Tang*, `Brothy → Herbal` *Aromatic Infusion*, `Toasted → Savory` *Maillard Crust*, `Steamed → Chilled` *Al Dente Shock*, `Raw → Pickled` *Quick Ceviche*) triggers a **FLAVOR COMBO!** for **+25% to +35% bonus damage** and **5% to 12% max HP recovery**.

## 5. Secret #151: Consommyth
- **#151 Consommyth** (`Soup` family, `Brothy / Sweet`, Lv. 55) is hidden from the bEATdex (which shows `150` slots until #151 is seen or caught).
- **How to obtain:**
  1. Defeat **Champion Chef Aurelia** in the Grand Tasting Hall.
  2. Shift time to **Night** (`SELECT` / `N` / step cycle).
  3. Carry a **Royal Banquet Setting** (earned from the *Rare Night Truffle* quest in Bisque Bastion or bought at Chowder Crossing Pantry Mart).
  4. Have at least one bEATst from **all 4 food families** (`Sandwiches`, `Dumplings`, `Noodles`, `Soup`) in your active party.
  5. Interact with the **Secret Pantry Door** behind Champion Aurelia at `(13, 1)` in the Grand Tasting Hall to battle and plate **#151 Consommyth**!

## 6. Automated Test Output (`node tests/run-all.js`)
```text
[TEST 1] bEATdex completeness...
PASS: 151 bEATsts complete, all front/back shapes unique, #151 event verified, positive controls passed.

[TEST 2] Type chart & 10,000 seeded battles...
PASS: 12x12 Type chart complete. Measured win rates (10,000 battles):
  Toasted: 53.4%, Steamed: 47.2%, Fried: 56.9%, Pickled: 47.5%, Spicy: 49.1%, Brothy: 54.5%, Raw: 41.6%, Fermented: 54.9%, Sweet: 48.7%, Savory: 49.9%, Chilled: 46.7%, Herbal: 49.7%

[TEST 3] Plating formula & 10,000-attempt seeded run per tier...
  Tier 1 (Paper Plate): formula=15.00%, measured=15.42%
  Tier 2 (Wooden Board): formula=22.50%, measured=22.18%
  Tier 3 (Ceramic Plate): formula=33.00%, measured=32.96%
  Tier 4 (Bento Lacquer Set): formula=48.00%, measured=48.30%
  Tier 5 (Royal Banquet Setting): formula=75.00%, measured=75.00%
PASS: Plating strictly increases with tier and matches formula.

[TEST 4] GBA shape...
PASS: GBA 240x160, 8x8 tiles, <=16-color 15-bit palettes, and 4 audio channels verified.

[TEST 7] Audio offline render...
  Track title            : 3.18s (peak=0.579)
  Track overworld_bread  : 3.50s (peak=0.577)
  Track overworld_steam  : 3.89s (peak=0.579)
  Track overworld_noodle : 3.09s (peak=0.579)
  Track overworld_broth  : 4.20s (peak=0.577)
  Track town             : 3.75s (peak=0.579)
  Track battle_wild      : 2.76s (peak=0.579)
  Track battle_chef      : 2.62s (peak=0.558)
  Track battle_rival     : 2.66s (peak=0.565)
  Track battle_champion  : 2.86s (peak=0.579)
  Track victory          : 2.29s (peak=0.578)
  Track healing          : 1.41s (peak=0.480)
  Track evolution        : 2.36s (peak=0.579)
  Track credits          : 4.14s (peak=0.579)
PASS: All 14 tracks and 12 SFX rendered non-silent.

[TEST 9] Franchise name collision check...
PASS: Zero name collisions against franchise comparison list.

[TEST 10] Static scan (CSP, network APIs, external links, labeled inline blocks)...
PASS: Strict CSP, zero network APIs, zero external links, all inline blocks labeled.

[BROWSER] Starting ChromeDriver for Tests 5, 6, 8 and screenshots...

[TEST 5] Saves (3 slots round-trip, Export/Import, localStorage disabled)...
PASS: All 3 save slots round-trip identically, Export/Import works, and game runs with localStorage disabled.

[TEST 6] Completion bot (new game -> 8 Head Chefs -> Gauntlet -> Champion -> Credits)...
PASS: Bot reached CREDITS! Seals=8/8, Steps=400, Battles=67, Party=[Clubbehemoth Lv.81]
PASS: Positive control (blocking required path stops bot) passed.

[TEST 8] Phone controls at 390x844 viewport...
PASS: Phone touch controls started game, moved, opened menu, and won a battle at 390x844.

ALL 10 TESTS PASSED!
```

## 7. Screenshots
- `screenshots/title.png` — Title screen
- `screenshots/region_sandwiches.png` — Breadlands (Cruston Town)
- `screenshots/region_dumplings.png` — Steambay (Bao Harbor)
- `screenshots/region_noodles.png` — Noodleridge (Udon Hollow)
- `screenshots/region_soup.png` — Brothbasin (Chowder Crossing)
- `screenshots/battle.png` — Turn-based battle with Kitchen Temp HUD
- `screenshots/plating.png` — Wild battle Plating menu
- `screenshots/beatdex.png` — bEATdex screen

## 8. Notes & Limitations
- In this container environment, headless Chromium blocks `file://` and `127.0.0.1` navigation, so the test harness loads `beatsts.html` via `data:text/html;base64,...`. Because `data:` origins also restrict `window.localStorage`, Test 5 verifies both the in-memory fallback when `localStorage` is disabled and the save/load/Export/Import round-trip.
- Real-time Web Audio playback requires a user gesture in browsers; all 14 music tracks and 12 sound effects were verified via deterministic offline synthesis in Test 7.
