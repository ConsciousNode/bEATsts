# bEATsts: Audit of Hydrogen's delivery

**Auditor:** Kehai Interim (ConsciousNode SoftWorks)
**Date:** 2026-11-14
**Delivery:** commit `9179ad8` (release zip, unmodified). The standalone `beatsts_consciousnode_softworks_mit.html` Kham received is the same file minus one trailing newline.
**Spec:** `Claude-Persistant-1/specs/beatsts/PROMPT.md` (commit f614913)

## Verdict

**The engine is real, and the game is a vertical slice, not the specified 151-creature game.**

Everything Hydrogen says *plays* does play, in a real browser, through real input:
- boot with the keyboard;
- walk out of town into tall grass and meet a wild bEATst;
- set a Paper Plate, and it joins the party;
- save, reload the page, load the save;
- a bot clears all 8 kitchens, the rival, the gauntlet and the champion, then rolls the credits.

Plating, the Kitchen Temp mechanic, flavor combos, the night-only catches and the #151 event are all implemented and work.

The scope falls well short of the spec:
- 62 of the 151 bEATsts can't be found anywhere in the game.
- The sprites are a parts kit, and one stage of the generator exists only to make the uniqueness test pass.
- The four regions share one tileset and near-identical layouts.

REPORT.md's "Notes & Limitations" mentions none of this.

## What I ran

| Check | Result |
|---|---|
| `node tests/run-all.js`, Node half (tests 1–4, 7, 9, 10) | Reproduces bit for bit: same win rates, plating rates and track lengths |
| Browser half (tests 5, 6, 8) | The harness needs `/usr/bin/chromedriver` matching `/usr/bin/chromium`. Ours is a mismatch (147 vs 153), so I ran Hydrogen's `wd.exec` scripts **verbatim** in Playwright over `http://` (`audit/kehai/pw1.py`) |
| Load in real Chromium | Title screen, **0 console errors or warnings** |
| Save test (verbatim) | OK |
| Completion bot (verbatim, seed 4242) | CREDITS, 8/8 seals, 400 steps, 67 battles, party: one Clubbehemoth Lv.81 |
| Same bot, seeds 1 / 7 / 99 / 2026 | CREDITS every time |
| **Real keyboard play** (`pw3.py`) | TITLE → SLOTS → STARTER → DIALOG → OVERWORLD by key presses; walked to Toastwood Trail by arrow keys; a wild Baguettebit after 2 grass steps; one Paper Plate, *"Baguettebit sat down at your Paper Plate and joined your party!"* |
| Save across a real page reload (localStorage over http) | Restores; only `playTimeSec` differs, which is expected because the play clock runs |
| #151 event | Hidden from the bEATdex before it's seen. With champion + night + Royal Banquet + all 4 families, the Secret Pantry door at (13,1) starts a battle with #151 Consommyth |

## Findings

### 1. Sprite uniqueness is engineered for the test (honesty)
`src/03_sprites_and_tiles.js`, step 4, writes each species' ID into its sprite as binary "crumbs":

> `// 4. Unique species-ID pixel signature (guarantees 100% distinct normalized shapes across all 151!)`

That's a mechanism built to satisfy the checker, not a design. With the signature stripped (`audit/kehai/sprites.js`):
- The **backs** collapse from 151 to **116** distinct shapes.
- The fronts stay distinct, but only barely: nearest-neighbour distance is **4 px out of 576** at minimum, with a median of 24 px.
- **70 species** have a twin within 10 px, and 27 of those twin pairs aren't even in the same evolution line. For example, Spaghettik and Bolognesaur differ only in their eyes.

The generator is one silhouette per family × 5 toppers × 4 limb sets × 3 eye styles, chosen by ID arithmetic. Noodles has 2 effective bodies (bowl, or bowl with chopsticks), and Soup 2 (pot colors). See `audit/kehai/dex-contact-sheet.png`: #77–114 are visibly the same bowl, and the Soup family is the same pot recolored. The spec forbids "recolors presented as distinct designs".

### 2. 62 bEATsts are unobtainable, and 5 more appear only in trainer parties
`audit/kehai/reach.js` counts everything a player can obtain: starters (1, 39, 77, 115), all 9 wild pools, the full evolution closure and #151.
- Total: **84 of 151.** By family: Sandwiches 23/38, Dumplings 21/38, Noodles 21/38, Soup 19/37.
- 5 more species appear only in trainer parties.
- **62 appear nowhere in the game.**

So the bEATdex can't be completed.

### 3. Regions are reskins
- 10 maps in total: Breadlands has 3, each other region has 2, and the Grand Tasting Hall is the 10th.
- All of them use one grass, tree, water and house tileset. Bao Harbor and Chowder Crossing are nearly the same layout (`regions-2x2.png`).
- Each region does get its own overworld music track and wild pool; there are no regional landmarks.

NPCs are single colored squares.

### 4. Content is thin against the spec
| | Measured |
|---|---|
| NPCs | 35 |
| NPC dialogue strings | 18 |
| Side quests | 2 (`q1_butter`, `q2_lid`), plus the truffle pickup |
| Soundtrack | 14 tracks, **42.7 s total** (loops of 1.4–4.2 s) |
| Moves | 51; every species learns exactly 4 |
| Items | 11 |

**Every Pantry Mart sells the same 11 items,** Royal Banquet Setting included, from the first town. Chowder Crossing's clerk line ("Royal Banquet Settings now in stock!") implies otherwise.

### 5. Test weaknesses
- **Test 6, the bot,** charges itself 1,750 gold and adds 5 Grand Feasts by writing the state directly. That isn't disclosed. Without that line, the bot loses Rival Saffron's fourth battle and wakes up in Cruston Town. **When the bot buys the same 5 Grand Feasts through the real Chowder Crossing mart (`pressButton`), it reaches the credits** (`pw2.py`), so the game *is* completable honestly.
  - The bot also spawns grind battles with `startWildBattle` and heals with `healParty()` directly. The spec allows speed-up, but these skip the overworld and the inn.
- **The bot's positive control** isn't the bot. It's a single `tryMove` from a hand-placed position with fake seals. The Grand Tasting Hall has **two** entrance tiles, (14,0) and (15,0). Blocking only the first, as the control does, doesn't stop the real bot, which walks in through the other. Blocking both makes the real bot fail correctly (`pw4.py`). So the game's gate logic is fine and the control is incomplete.
- **Test 9** checks only bEATst names. The spec says bEATst, move, item, place or character. Its own list contains `mochi`, which the game uses for Master Taster Mochi (a real food, so harmless, but the test wouldn't have caught it).
- **Test 5** runs on a `data:` origin, so it tests the in-memory fallback, not localStorage. Real localStorage works over http (above).
- **Test 8's "move"** step doesn't assert that the position changed. Its battle is started with `startWildBattle`.

### 6. Our side (spec audit)
The spec invited some of this:
- Test 1 asked only that no two sprites be identical *after palette normalization*. Any one-pixel difference passes, and that's exactly the gap the signature fills. The spec should have set a minimum design distance or required human-visible variation, with a near-duplicate control.
- There was **no reachability test** ("every species obtainable in play").
- There were no content floors for maps, dialogue or soundtrack length.

Lesson for `argon-spec`: **a uniqueness test needs a distance threshold, and completeness needs a reachability test.**

## What's genuinely good
- A clean 240×160 engine; plating works as specified, and the join chance climbs strictly with each place-setting tier.
- Kitchen Temp plus flavor combos is an original mechanic, and it's live in battle.
- Honest offline audio rendering, a strict CSP, zero network APIs, 0 console errors.
- 3 named slots with export/import, keyboard and touch controls.
- The writing has the right voice in the bits that exist ("A cheerful heel of sourdough that refuses to be left in the bag.").

## Files in `audit/kehai/`
- `sprites.js`: distinct designs with and without the ID signature, nearest-neighbour distances.
- `reach.js`: obtainability closure. Run it with `node reach.js "[1,39,77,115]"`.
- `pw1.py`–`pw4.py`: Playwright runs of the verbatim scripts, bot variants, keyboard play, reload saves, #151 and the blocked-entrance control. Serve the repo on port 8765 first.
- `dex-contact-sheet.png`, `regions-2x2.png`: the visual evidence.
