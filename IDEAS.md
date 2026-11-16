
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
