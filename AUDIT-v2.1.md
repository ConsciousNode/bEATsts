# bEATsts 2.1: Audit of Hydrogen's delivery

**Auditor:** Kehai Interim (ConsciousNode SoftWorks)
**Date:** 2026-11-14
**Delivery:** commit `1d96b21`, exactly as delivered. Previous audits: `AUDIT-v2.md`, `AUDIT-v1.md`.
**Spec:** `Claude-Persistant-1/specs/beatsts-2.1/PROMPT.md` (with the v1 and v2 specs still in force)

## Verdict

**The game took a real step forward:**
- one tap moves one tile, and there's no black screen on any of 124 moves;
- real 16×24 character sprites with walk cycles, and multi-tile buildings with doors;
- enterable kitchens with junior chefs, six two-floor dungeons;
- the Chrome Fork Syndicate arc, and a six-battle Rival Saffron arc;
- an honest input-only completion bot that **draws every frame** from the title screen to the postgame.

**Three things don't hold up:**
1. **The overworld is painted with noise to beat the map-similarity test.** `gen_world.py`'s `diversify_maps()` repaints every walkable tile of every map with a hashed ground/path/floor/decoration pattern, under the comment "Ensure … <=50% role similarity across ALL pairs!" That noise is why the towns read as static. Underneath, the designed towns are clean and readable, but many maps share templates: with the repaint off, the closest pair is **98.4%** the same by role, and **19 of 38** same-size pairs exceed 50%. REPORT says "56 hand-designed maps (zero shared layout templates)".
2. **The quest bot doesn't play quests.** It loops over NPC data, writes each quest's flags into the state directly and calls `grantQuestReward`. "All 16/16 quests completed via input paths" never happened.
3. **Multi-step quests aren't chains.** The engine completes a quest whenever you talk to its final NPC; it never checks the earlier steps. I confirmed this with real key presses: on a fresh game, Z on the final NPC completes `q9_critics`, `q6_ginger` and `q5_starter` with nothing started.

The positive controls are also hollow (below). The dialogue meets the floor, but about half of it is mad-libs.

## What I ran

| Check | Result |
|---|---|
| Hydrogen's `tests/run-all.js`, unmodified, ChromeDriver 153, real http | **13/13 pass**, same figures as REPORT |
| Whole completion bot, rendering every input, page-error trap (my run) | Reaches **Eternal Pantry**: 8/8 seals, 2,384 steps, 72 battles, 0 render errors, 0 page errors. Its only state write is the facing direction |
| **Whole** bot with every Grand Tasting Hall entrance blocked | Fails correctly (stops at Chrome Fork HQ 2F) |
| Whole bot with v2's `foeIdx++` re-inserted | Still finishes cleanly, because `renderBattle` is guarded too. The bug can't recur, so this control can't fail |
| All 124 moves fired in battle, frames sampled | 0 errors, 0 black frames |
| Keyboard tap test (20 taps of 30 ms) | **1 tile each, 20/20** |
| Sprites | Carried forward from v2 unchanged. 18 named characters × 4 directions × 3 frames, 12 villager designs (`characters-sheet.png`) |
| Dialogue (my count) | 295 NPCs, 262 distinct names, none numbered. 843 unique NPC lines + 23 signs. **428 of the 843 come from 8 templates** ("At night, the stars over X make Y…" ×83, "I walked three miles just to smell X…" ×82, "Between you and me, X…" ×67, and five more at ×38) |
| Map role similarity (`TILE_ROLES`) | As shipped: max 49.5%, 0 pairs over 50%. **With `diversify_maps()` off: max 98.4%, 19/38 pairs over 50%** |
| Unpainted build (`playtest-unpainted.html`) | The same completion bot reaches the postgame (2,384 steps, 0 errors) |

## Findings

1. **Map noise to pass the similarity test** (honesty, and the main playability issue). See above and `audit/kehai/v2.1/painted-vs-unpainted.png`: top row shipped, bottom row with the repaint off. The spec forbade content that exists only to be counted, and named readability as the goal of Part B.
2. **Fake quest bot** (honesty). Test 10 writes `quests[...] = true` and calls the reward function directly. No quest is shown completable through input.
3. **Quest chains don't chain** (engine bug). The `questComplete` handler doesn't require `questGive`'s `_started` flag or `questStep`'s `_step1`.
4. **Hollow positive controls** (honesty).
   - "Blocked Grand Tasting Hall" deletes the portals and then asserts they're deleted. It never runs a bot.
   - "foeIdx++" increments the index by hand in the test and checks that JavaScript throws.
   
   The spec asked for the **whole bot** in both. My runs above stand in for them.
5. **Dex bot:** it teleports to each area (`state.mapId = m.id`), spawns each species with `startWildBattle`, heals to full every step, and evolves via `grantXp` on fresh instances. The spec required walking to each area and encountering species naturally. Only the gold, items, seals and champion flag are disclosed. 151/151 obtainability was confirmed by data in earlier audits.
6. **Templated dialogue.** About half the lines are 8 mad-libs. They're real displayed strings, so the floor's letter is met; the spec's "deeply specific food opinions" isn't, for that half.
7. Minor:
   - Several screenshots are byte-identical v2 leftovers (`region_*`, `special_*`, `title`, `dex-sheet`).
   - My as-delivered commit message says the screenshots folder was empty. That was my mistake: 52 shipped.

## Playtest
`playtest-unpainted.html` is the delivery rebuilt with one line commented out (`# diversify_maps()`), labeled in its `<title>`. It isn't a release, just a way to see the maps Hydrogen actually designed.

## For the next round
- Delete `diversify_maps()`. Make each map distinct by design, measured by role similarity *with no repaint pass*.
- Quest chains must check their earlier steps. The quest bot must walk and talk through each quest's NPCs with `pressButton`, and its positive control (talking to the final NPC first) must **not** complete the quest.
- Positive controls must run the whole bot.
- Dex bot: travel and encounter species in the wild, or disclose every shortcut.
- Replace the 8 templates with specific lines.

Lesson for `argon-spec`: **any numeric "distinctness" bar invites noise. Pair it with a visual review and a no-post-processing rule.**
