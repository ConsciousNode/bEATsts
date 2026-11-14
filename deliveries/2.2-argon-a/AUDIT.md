# bEATsts 2.2: Audit of Argon build A

**Auditor:** Kehai Interim (ConsciousNode SoftWorks)
**Date:** 2026-11-14
**Delivery:** commit `2b4bbea`, exactly as delivered. **Builder: Gemini Argon** (thread A), working on Hydrogen's 2.1. A second Argon 2.2 build is still in progress. Previous audits: `AUDIT-v2.1.md`, `AUDIT-v2.md`, `AUDIT-v1.md`.
**Spec:** `Claude-Persistant-1/specs/beatsts-2.2/PROMPT.md`

## Verdict

**Accepted. Every 2.1 finding is fixed, and the fixes are real.**
- **Maps are designed, not painted:** `diversify_maps()` and all post-processing passes are gone, and the paths are continuous and readable.
- **Quest chains check their steps**, and the quest bot plays every quest through `pressButton`.
- **Dialogue is written, not templated.**
- **The positive controls run real code:** the whole completion bot with the Grand Tasting Hall blocked, and talking to the final NPC first for every multi-step quest.

REPORT discloses its limits honestly: the dex bot walks and catches a 19-species sample, not 151, and the quest bot starts from the completion bot's postgame save.

## What I ran

| Check | Result |
|---|---|
| `tests/run-all.js`, unmodified, ChromeDriver 153, **real http** (no `data:` fallback needed here) | **13/13 PASS**, same figures as REPORT |
| Bot code scan (inline scripts, `navHelpers`, the completion bot, the quest bot, the dex bot) | The completion and quest bots make **no** state writes and use no shortcuts. The dex bot's only write is the disclosed `bag.royal_banquet = 100`. The `startWildBattle` and position writes in the file belong to the screenshot code, not to any bot |
| Quest skip, **real keys on a fresh game**: Z on the final NPC of `q9_critics`, `q6_ginger`, `q5_starter` | **Not completed** in all three (in 2.1, all three completed) |
| Keyboard tap test (20 taps of 30 ms) | 1 tile each, 20/20 |
| All 124 moves fired in battle, frames sampled | 0 errors, 0 black frames |
| Same-size map role similarity (my script) | 29 pairs, **max 48.7%**, 0 over 50% |
| Different-size best alignment (my script; overlap ≥ 90% of the smaller map) | 1,511 pairs: 5 over 50%, max 57.0% (`gym_bamboo~gym_wokpeak`). REPORT says max 0.500 with the smaller map fully inside. My method also counts slightly partial overlaps, so the gap is method, not a hidden copy |
| Static scan of `gen_world.py` for repaint / scatter / perturb / noise passes | None |
| `screenshots/all-maps.png` (looked at by eye) | 56 maps, all clean and readable. Many towns share a "crossroads with four quarters" idea but differ in shape and detail. Dungeons and interiors are each distinct |
| In-game, Cruston Town | Readable plaza, roads, houses with doors, pond, flower beds, chest, real character sprites, CNSW Serif banner |
| Dialogue (my script) | 298 NPCs, 265 distinct names, 0 numbered. **908 unique NPC lines** + 23 signs. The most common opening is "I tried to make…" ×24 (an individually written series); no mad-lib families remain |

## Findings (minor)

1. **The dex-bot control runs the reachability calculation**, not the dex bot (with `#108`'s only source removed, `computeReachable` drops below 151). That's a real computation, not a tautology. Since the dex bot only samples 19 species, which is disclosed, this is a reasonable substitute for the spec's "dex bot fails".
2. **Different-size similarity method:** see the table. Worth agreeing on one method (fully inside vs ≥ 90% overlap) before the next round.
3. REPORT's loopback note says container Chromium blocks `127.0.0.1`. Here it doesn't, and the full suite ran over real http, including test 12's actual page reload.

## Builder note
This is the first bEATsts round built by Argon rather than Hydrogen, because two sends routed to Argon by accident. If the second Argon 2.2 lands, I'll audit it the same way and compare them.
