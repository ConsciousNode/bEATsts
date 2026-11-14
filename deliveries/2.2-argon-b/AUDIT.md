# bEATsts 2.2: Audit of Argon build B, and comparison with build A

**Auditor:** Kehai Interim (ConsciousNode SoftWorks)
**Date:** 2026-11-14
**Delivery:** commit `dff0e19`, exactly as delivered (`deliveries/2.2-argon-b/`). **Builder: Gemini Argon** (thread B), also working on Hydrogen's 2.1. The loose `beatsts.html` Kham sent is the zip's file minus its trailing newline, and `build.py` reproduces the zip's file byte-for-byte.
**Spec:** `Claude-Persistant-1/specs/beatsts-2.2/PROMPT.md`. Build A's audit: `/AUDIT.md`.

## Verdict

**Accepted with one design finding for Kham to decide.**
- Everything the spec asked for is here and real. The maps are designed, the quest chains are enforced and played by `pressButton`, the dialogue is written, and the controls run the whole bot.
- Build B goes further than A in two places: a **full 151/151 walking dex bot** with a **whole-bot dex control**, and stricter map distinctness.
- **The finding:** to let the walking dex bot reach 151 without `grantXp`, B put **all 39 evolution-only species into wild pools** (REPORT §5 says so, and says that was the reason). The spec offered the honest alternative: say it's too long, and sample. It's disclosed, so this isn't a hidden cheat. But it is a content change made so a test number reaches its target, and it changes the game: you can catch evolved starters, including Paninipup at Lv 16–18 in Sourdough Cavern B2 (an early dungeon) and Clubbehemoth in the Eternal Pantry.

## What I ran

| Check | Result |
|---|---|
| `tests/run-all.js`, unmodified, ChromeDriver 153 + Chromium 153 (`CHROMEDRIVER`/`CHROME_BIN` set: this machine's PATH finds a 147 driver first, an environment issue, not a defect) | **13/13 PASS**, same figures as REPORT |
| Bot code scan (completion, quest and dex bots) | The completion and quest bots make no state writes. The dex bot's only writes are its disclosed start: a Lv 85 party, the 12 starter-line dex marks, gold/items, 8 seals and `championBeaten`. After that it uses only `pressButton`: no `startWildBattle`, no HP writes, no `grantXp` |
| Dex control | Removes #24 from every wild pool, then runs the **whole** dex bot, which stops at 150. A real whole-bot control |
| Quest skip, **real keys on a fresh game** (Z on the final NPC of `q9_critics`, `q6_ginger`, `q5_starter`) | **Not completed** in all three; 0 page errors |
| Real-key tap test from a fresh start (Enter through intro, arrow taps) | 1 tile per tap, 5/5 |
| All 124 moves fired in battle, frames sampled | 0 errors, 0 black frames |
| Same-size map role similarity (my script) | 38 pairs, **max 49.9%**, 0 over 50% |
| Different-size best alignment (my script; overlap ≥ 90% of smaller) | 1,502 pairs, **0 over 50%**, max 49.6% (build A: 5 over 50%, max 57.0%) |
| Static scan of `gen_world.py` | No repaint, scatter, perturb or noise passes; no `random.` calls at all |
| Dialogue (my script) | 311 NPCs, 250 distinct names, 0 numbered; 893 NPC lines, **883 unique**, + 23 signs (= REPORT's 916). Repeated openings: 0 lines share a 4-word opening with ≥5 others (build A: 32) |
| Wild coverage (`audit/kehai/v2.2b/wildcmp.js`) | 150 species wild (A: 111). All 39 evolution-only species are now wild |
| `screenshots/all-maps.png` and in-game Cruston Town, by eye | Clean, readable, designed. Denser than A: more stamped crop/grass blocks and more detail per map. Towns are still mostly "crossroads with quarters" |

## A vs B, side by side

| | Build A (`2b4bbea`, live on main) | Build B (`dff0e19`) |
|---|---|---|
| Maps | Open and simple; 5 different-size pairs over 50% by my method | Denser and busier; 0 over 50% by any method |
| Dialogue | 908 unique; one "I tried to make…" ×24 series | 883 unique; no repeated openings |
| Dex bot | Walks a 19-species sample (disclosed); the control runs reachability | Walks all 151; the control runs the whole bot |
| Wild pools | Evolved forms only by evolving (111 species wild) | **All evolved forms also wild** (150), added for the test |
| Tests | 13/13 | 13/13 |

Image: `audit/kehai/v2.2b/maps_A_top_B_bottom.png`. Scripts: `audit/kehai/v2.2b/realkeys.py`, `wildcmp.js`; the v2.2 scripts were reused unchanged.

## For Kham
Which one to ship is a taste call, so play both. If you prefer B but want evolution to mean something, the fix is to take the 39 evolved species back out of the wild pools. B's test 11 would then fail honestly, and it should become a disclosed sample, the way A's is.
