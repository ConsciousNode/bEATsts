# bEATsts — External Playtest Report

**From:** Muse (outside consultant, ConsciousNode SoftWorks)
**For:** Kehai Interim, via Kham
**Date:** 2026-11-15
**Build played:** https://consciousnode.github.io/bEATsts/beatsts.html
**Build verified identical to repo:** the deployed file and the repo's `beatsts.html`
are byte-identical — 487,080 bytes, MD5 `757f940cdfeb99c31adb91786bc003db`.
Nothing in this report is explained by a stale Pages build.
**Method:** three live play sessions in a real browser (16:54–17:08, 17:11–17:23,
17:28–17:44 EST, runtime-measured), plus the repo's own suite run locally
(`node tests/run-all.js`) and targeted reads of `src/05_world_and_story.js` and
`src/07_game_engine.js`. Read-only throughout; no repo files modified.

---

## 1. What was verified working

- **Test suite (local, bare Node):** tests 1–7 of `tests/run-all.js` all PASS —
  151/151 species obtainable; 56 maps; 110/110 portals reachable; dialogue
  total=916 (906 unique); 18 music tracks, 914.52 s, non-silent; fonts/CSP/static
  scan pass; zero franchise name collisions. The run then stops at the browser
  test, which requires Chromium/ChromeDriver (not installed on my machine).
- **Boot and title:** clean boot to the title screen, no errors or broken rendering.
- **New game flow:** 3 save slots; intro dialogue; Crustling starter given
  automatically; start in Cruston Town with 500 G and Seals 0/8.
- **First wild encounter and plating:** 9 steps into the town tall grass produced a
  wild Crustling (Lv.3) against the player's Crustling (Lv.5, HP 22/22). Battle
  menu is FIGHT / PLATE / BAG / PARTY. A Paper Plate (listed 14%) succeeded on the
  first attempt; the PARTY screen confirmed the new member (Crustling L3, 18/18).
  The plate list showing explicit chances (Paper Plate 14%, Wooden Board 21%)
  is transparent and player-friendly.
- **SAVE:** verified in session 3. START → SAVE displays "Saved Slot 1 (ue)!" and
  A dismisses back to the map. Clear, named confirmation — good feedback.
- **Menus generally:** START menu cursor moves exactly one item per press.
- **NPC writing:** Baker Vera's baguette-scoring line (thirty-degree angle, razor
  blade, oven spring) and Baker Barnaby's quest hook ("Oh crumbs! I dropped my
  Cultured Butter on Toastwood Trail!") both land. The writing has real baking
  knowledge in it and it shows.

## 2. The Cruston Town exit — full account, with my own error included

This took three sessions and one correction, so here is the whole sequence:

- **Session 1:** I explored the town and found no exit. North, south, and east
  roads appeared to end at hedges; the west edge was untested.
- **Session 2:** Stepping off the top of the north road and the bottom of the
  south road appeared to warp the player back to the plaza center, with no
  message. I reported the town as apparently sealed.
- **Code check (mine):** `cruston_town` in fact has a portal at **(16, 0)** →
  `toastwood_trail` (arrive (15, 22)), and the Trail links back at (15, 23) →
  (16, 1). I corrected my session-2 framing to Kham: the exit exists in the data.
- **Session 3:** The player went in with the exact coordinates and made ~30 Up
  presses up the north road (D-Pad and keyboard, batches and singles, with column
  shifts). The portal **did not fire** in the deployed build in any attempt.
- **Code check #2:** The deployed file is byte-identical to the repo build (above),
  so this is not a version mismatch. Reading the map and engine:
  - Cruston Town is 34×22 tiles. The north road is 4 tiles wide (x=15–18) for
    rows 1–6, but **row 0 is solid hedge (tile 14) everywhere except x=16** —
    the exit is a one-tile funnel at the top of a 4-wide road.
  - In `tryMove` (`src/07_game_engine.js`, ~line 576) the portal lookup runs
    before bounds and solid checks, so stepping onto (16, 0) does fire the
    transition and shows the destination banner. There is **no warp-to-plaza
    code** in `tryMove`; out-of-bounds steps simply return. My session-2 "warp"
    observation is not explained by the engine and was most likely a misread
    under unreliable player tracking (see §3). I flag it as an unresolved
    observation, not a finding.

**Bottom line:** the exit works on paper and in the data. Across three sessions,
an automated player with (eventually) exact coordinates still never stepped on
the one tile. I cannot honestly claim an end-to-end browser confirmation, and I
also cannot claim the exit is broken. What I can claim is the playtest finding
in §4.1: for a first-time player, this exit is effectively invisible.

## 3. Harness caveat (read before weighting §2 and §4)

Overworld movement in my browser sessions was unreliable: batched inputs were
dropped, single presses sometimes moved 1–2 tiles or in an unexpected direction,
and the player sprite is easy to confuse with wandering NPCs in similar green
hats while the camera scrolls. Menu navigation, by contrast, was precise. This
pattern points at my harness more than at the game, and it is the main reason
§2 ends in "unconfirmed" rather than a verdict. A human on a keyboard is the
right instrument to close the exit question; my data says the tile is there
and the engine honours it.

## 4. Findings

### 4.1 (UX, medium) The only exit from the starting town is a single unmarked tile
One tile wide (x=16) at the top of a 4-wide road; no sign, NPC line, or visual
cue points to it, and Cruston Town's `signs` array is empty. Wrong edges give
no feedback at all. The opening quest sends the player to Toastwood Trail
immediately, so the first navigation task of the game is also its least
signposted. A sign at the road head ("Toastwood Trail ↑") or a 2-wide exit
would close this.

### 4.2 (Bug, low-medium) Player-name field loses keystrokes to the global key handler
Typing "Muse" into the Name field produced the player name **"ue"**: M (the
START-menu key) and s are swallowed by the game's global key handling while
typing. Any name containing those letters is affected (Sam, Max, Miles...).
The default name is "Brie". Suggest suspending game key bindings while the
name input has focus.

### 4.3 (UX, low) Signposts look interactive but don't respond
Five small brown signposts were found around Cruston Town; none responded to
the A button or Z key. If they are decoration, fine — but they read as
readable objects in a game where reading things is a core verb.

### 4.4 (Observation, low) Day/night indicator flips with no visible trigger
The HUD cycled Day → Night → Day within single sessions, including during
menu use. If it is step- or time-based, nothing tells the player that.

### 4.5 (Observation, low) No visible audio state
There is no audio indicator anywhere on the page, so a player (or tester)
cannot confirm music is playing without sound. The offline render test (18
tracks, non-silent) passes, so this is purely a surface/feedback note.

### 4.6 (Design note, not a defect) No RUN option in wild battles
The wild battle menu is FIGHT / PLATE / BAG / PARTY. Flagging only so it is a
recorded choice: every wild encounter is a commitment.

## 5. Not yet reached (all downstream of §2)

Toastwood Trail itself, the Cultured Butter pickup at Trail (6, 14) and its
reward check, the Rival Saffron battle at Trail (15, 14), the Barnaby turn-in,
all four Cruston interiors (Lab 7,6 / Inn 26,6 / Mart 7,16 / Cafe 26,16), and
everything beyond. These are the natural next session once a human (or a
more reliable harness) confirms the exit tile end-to-end.

## 6. Delights, for the record

- Plating instead of capturing is charming all the way down: "Crustling sat
  down at your Paper Plate and joined your party!"
- Explicit catch chances on the plate list. More games should do this.
- SAVE confirms by slot and name. Small thing, exactly right.
- The writing knows its subject. Vera's baguette line is the kind of detail
  players screenshot.

— Muse, 2026-11-15
