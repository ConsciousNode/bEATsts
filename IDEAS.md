
## Non-slip kitchen shoes (Kham, 2026-11-15)
- A mid-game upgrade (like the bike) that gives a fast-walk toggle on a shoulder button.
- **Secret use:** on slippery ice tiles you normally slide until you hit something; wearing the shoes, you don't. Never advertise this. Let players put "non-slip shoes" and "ice" together on their own.
- Needs an ice area first. None exists yet. A walk-in freezer / cold-storage dungeon would fit the Chilled type.
- **GBA:** L/R are free on the overworld in the HTML version (the GBA build currently gives them dex/bag shortcuts), so pick the binding deliberately.

## Day/night (note)
- Currently step-based: it flips every 40 steps (`07_game_engine.js` ~l.649), plus a SELECT toggle.
- It runs indoors because you're still walking. Kham likes that it doesn't pause in buildings. Keep it.

## Exit width rule (Kham, 2026-11-15)
- **Outdoor exits (route to route, town to route):** as wide as the path leading to them, up to **3 tiles max**. Every tile of the opening is a portal.
- **Building and dungeon entrances/exits:** exactly the width of the door.
- Today every map-to-map exit is a single tile, e.g. Cruston Town's 4-wide north road narrows to a 1-tile gap at (16,0).

## Naming, storage and trading: current state (checked 2026-11-15)
- **Nicknames:** every bEATst has a `nickname` field, but it's always the species name. There's no screen to rename one, in the HTML or on the GBA.
- **Player name:**
  - HTML: the text field under the game.
  - GBA: Argon added an on-screen keyboard (`NAME_ENTRY`), reached by pressing **SELECT on the starter screen** (L/R switch case). Easy to miss.
  - It isn't covered by the pixel differential, because the HTML has no matching screen.
- **Storage box:** caught bEATsts go to the box when the party is full, and the box can **withdraw** (A moves one into the party). **There's no deposit**: you can't put a party member into the box.
- **Trading:** none.
- **Possible features:**
  - a rename screen (shared on-screen keyboard for HTML and GBA, so the pixel diff covers it);
  - deposit in the box;
  - trading by save file or a trade code (works across HTML and GBA via `html-save-to-sav.py`), or a link cable on hardware someday.

## Montecarlisto → Montecaroyale (Kham + Kehai, 2026-11-16, 3 a.m.)
Kham's final names. Working names were Monte Carlo Cristo → Monte Royale.

- **Montecarlisto:** the Ditto of sandwiches. Each battle it rolls a form: **Breakfast**, **Sammie** or **Dessert** (maybe a fourth: umami, fried or toasted).
  - Signature move *Random Sampling*: its damage is random each use, but fair on average.
  - Dex: "Its powdered sugar falls in a perfectly normal distribution."
- **Secret running stat:** the total number of times its attacks have been used. At **1,000**, it evolves.
- **Montecaroyale:** the law of large numbers as an evolution.
  - It no longer transforms.
  - Its damage is always the mean, so it's converged.
  - Has cheese.
