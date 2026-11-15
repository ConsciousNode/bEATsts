# Kehai patch on 2.2 build B: evolution only (2026-11-14)

**Kham's call:** evolved forms come only from evolving. Otherwise there's no reason to evolve.

- **`gen_world.py`:** took the 39 evolution-only species out of the six wild pools Argon added them to:
  - `sourdough_cavern_b2`
  - `truffle_cellar_b2`
  - `steamer_spire_f2`
  - `wok_volcano_f2`
  - `broth_catacombs_b2`
  - `eternal_pantry` (the evolved starters)

  I also rewrote one Eternal Pantry line that said fully evolved bEATsts live there wild. Then I regenerated `src/05_world_and_story.js` and rebuilt `beatsts.html`. Before the edit, the generator reproduced the delivered world file byte-for-byte.
- **`tests/run-all.js`, test 11:** the walking dex bot must now plate **every species that has a wild source**: 112, counting #151's door. Test 2's 151/151 reachability covers the evolution-only species. The whole-bot control (#24's source removed) must plate exactly one fewer. Both changes are labeled `KEHAI PATCH` in the code.
- **Result:** 13/13 PASS here.
  - Walking bot: 112/112 wild-sourced species plated (dex total 120 with the disclosed starter-line marks); the control plated 119.
  - Test 2's own control now drops to 149, because removing #6 also removes its evolution #7. That's correct.
- **Full diff:** `audit/kehai/v2.2b/kehai-evolution-only.diff`. Argon's delivery is untouched in `deliveries/2.2-argon-b/`. Build A is archived in `deliveries/2.2-argon-a/` with its audit.
