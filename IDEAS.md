
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

## Redesign: cooking/breeding mechanic, three food schools, and the brothers arc (Kham + Kehai, 2026-11-18)

### Core cooking/breeding mechanic
Breeding is replaced (or supplemented) by a **cooking mini-game** — think Dragon Warrior: Monsters level of complexity. Variables:
- **Timing** — when in the cook you do things matters
- **Ingredients** — collectible like berries; each school (fermented/engineered/processed) has its own ingredient set
- **Conditions** — location, time of day (step-based), temperature (cold vs. hot environment)
- **Doneness spectrum** — raw → rare → medium → well-done → burnt; some results are optimal raw (sashimi, poke bowls, fruit salad, frozen desserts, cold-climate creatures), burning is usually bad but may unlock specific burnt-type lineages
- **Raw/cold notes:** raw is NOT automatically bad. Requires cold climate OR acidic ingredients (vinegar, lemon juice) OR brine (which shifts the result to pickled, not raw). Wet salads (potato, egg), green salads, frozen desserts can all be raw-optimal.
- **Fermentation:** has a **step-count wait** mechanic — you start the ferment, walk steps, come back. Different ferments need different step counts. Some lineages are only accessible by waiting out the full ferment cycle.
- **Starter cultures:** fermentation requires a starter batch, specific per lineage. Getting the right starter is part of the quest.
- **Cooking with love:** bonus mechanic — intentionally using high-level bEATsts as ingredients. They're consumed. Unlocks rare results. The player has to choose to sacrifice something they've leveled up.

### The three food schools and their NPCs

#### Hippie Gregg — Fermented school
- Recurring NPC, always slightly ahead of you. You take the ferry to the island, he's on the dock. You climb the mountain, he's at the peak with a jar.
- Always has something fermenting. Always. The jar is eternal.
- Gives the player their first SCOBY and other fermentation starters throughout the game.
- Starters are **single-use ingredients** — specific, precious, unlock fermented lineages.
- Everything he gives you is called **"a secret detox secret the big guys don't want you to know about."** No exceptions.
- Item descriptions are written in his voice — three sentences of conspiracy before the actual mechanical description.
  - e.g. *"Gregg's Ancestral Probiotic Stack: They don't want you to know what this does to your gut biome. Big Pharma has been sitting on this for decades. It smells like victory. [Starter culture for Booch line. Single use.]"*
- He is not wrong. His knowledge is impeccable. The framing is just a lot.
- Calls Carl Jr. "my little buddy" every single time. Has done this their entire lives.
- **Gregg's original SCOBY culture is from their mother's lab.** He's been keeping it alive.

#### QSR Carl Jr. — Engineered school
- Chrome Fork Syndicate field representative. Has a territory. Has quotas. Has pamphlets.
- **Does not believe in fermentation.** Won't eat yeasty products. Thinks wild cultures are a public health hazard.
- Gives the player **single-use** Syndi-Cult™ probiotic sachets and engineered starters — controlled, certified, faster than fermentation.
  - Item descriptions: corporate wellness copywriting. "Contains 11 live and active cultures. Clinically tested. No SCOBY required. No mess. No odor."
  - Mechanically worse than what Gregg gives you.
- Has pamphlets about Gregg specifically. Has pamphlets about Salvatore's sugar content.
- His district manager is **Derek.** He is afraid of Derek. He is trying very hard to impress Derek.
  - **Carl Jr. does not know Derek is the leader of the Chrome Fork Syndicate.** He is not a villain. He is being used. He genuinely believes in safe, certified food science and has no idea what Derek is actually running.
  - His entire safety crusade is GRIEF — he watched what uncontrolled food science did to his family and has been trying to make everything controlled and certifiable ever since.
- One scene mid-game: the player walks in on Carl Jr. eating one of Salvatore's snacks when he doesn't know you're watching. He sees you. Neither of you say anything.

#### Sweet Salvatore — Processed school
- Processed junk food magnate. Generous. Warm. Presses a full bag of something into your hands the first time you meet him whether you want it or not. "Take, take. You look thin."
- Gives the player **perpetual ingredients** — once you have them, they never run out. His stuff is everywhere. Easy entry, abundant, different ceiling than the other schools.
- Not opposing anyone. He's just a businessman and more product in the world is good for Salvatore.
- Finds the Carl Jr./Gregg dynamic very charming. Periodically tries to give Carl Jr. a snack. Carl Jr. refuses. (Except once. See above.)
- **Salvatore has known where their father is for a while and visits regularly.** He goes to movie night at the lab ruins. He brings nooch. He figured everyone else would work it out eventually — through the player, as it turned out.

#### The one thing all three agree on: **Nooch (nutritional yeast)**
- The family food. What their mother cooked with. The taste of home.
- Not fermented (deactivated), not engineered, technically processed — it lives in all three worlds.
- Shows up in all three quest lines as an ingredient. The player has probably been carrying it since the first town without knowing what it meant.
- Salvatore adapted it into a shelf-stable bag format and brings it to movie night.
- **Final item description, after the SnacKing scene:** *"Nutritional yeast. The good kind."*

### The brothers arc

Gregg, Carl Jr., and Salvatore are brothers. The player doesn't know this until the reveal.

**Their mother** was a brilliant food scientist. She was working on a theory: combine fermented, engineered, and processed bEATsts into a super bEATst — the unified food theory. She died in a **tragic explosion of flavor** when she attempted it in her lab.

**Their father** was her research assistant. He was in the room.

The three brothers each took one third of her research notes and went in opposite directions:
- Gregg took the fermentation path. His SCOBY is from her lab. The fermentation is his way of keeping her alive.
- Carl Jr. took the engineered/controlled path. He is trying to make it safe. He has been trying to make it safe ever since the explosion.
- Salvatore took the processed path. He feeds everyone. She was going to change food for everyone — he does it his way.

**The reveal:** late-game, all three are present for the first time. Salvatore says "Carlo, you should listen to your brother—" and Carl Jr. erupts. Gregg is unbothered. He thought Carl Jr. knew.

Gregg had been calling Carl Jr. "my little buddy" because Carl Jr. IS the little buddy. Literally. He's the younger brother. The whole game it was right there.

### SnacKing — the secret ultimate bEATst

Their father did not die in the explosion. He was **transformed** by it — the flavor fusion didn't kill him, it fused him with the combined food research. He became the embodiment of the super bEATst theory his wife was working on. He is **SnacKing**.

- **Availability:** only after completing all three brothers' quest lines (all three schools, fully evolved main lineage bEATst from each). Then he appears at the **lab ruins**.
- **Encounter:** not a battle — a **cook-off**. He's testing whether the player understands what she understood: all three schools combined.
- **If the player wins:** SnacKing joins the party without being plated. No cooking required. He IS the synthesis.
- **His appearance line at the ruins:** *"You've been talking to my kids."* Not a question. He's been patient. He had time.
- Visually: combines all three food type aesthetics. Huge. Melancholy. Peaceful. Dr. Manhattan energy — moved beyond grief into something like acceptance.
- He's been watching his sons from the ruins. He knew they'd find each other eventually.

**Movie night:** Salvatore has been visiting the ruins regularly. SnacKing and Salvatore watch movies together. Salvatore brings nooch. Neither of them told anyone.

**The brothers' reunion scene:**
- Carl Jr. cries. He has pamphlets for every situation except this one.
- Gregg hugs Carl Jr. The hug lands.
- Salvatore confesses he's been going to movie night and has known for a while. Carl Jr. is briefly furious about this too.
- SnacKing watches his three sons. He has the movie he was going to put on tonight. He'd been hoping they'd all show up.

### The three game versions (ternary tribute)
One version per school — each centers a different NPC, different starter ingredients, different balance of what's wild-catchable. Working names: **Version Gregg**, **Version Carl Jr.**, **Version Salvatore**. Exact version-specific content TBD.

### Fermentation lineage example: Booch line
Booch → Combooch → Comboochop
- Each stage requires its own step-count ferment wait AND a specific starter culture
- The starter for each stage is a different batch — the mechanic of "bringing your own culture" recurs here
- Only obtainable via fermentation; not wild-catchable
- Hippie Gregg provides the first Booch starter as the player's introduction to fermentation mechanics

### Processed lineage example: Snack cake line
Lildeb → Hoztez → TastySnake
- Sweet Salvatore's processed school lineage
- Perpetual ingredients — once you have the base ingredient it doesn't run out
- TastySnake is the final form: a snack that became a creature that became a snack again, completely at peace with this

---

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
