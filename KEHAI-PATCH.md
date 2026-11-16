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

---

## Playtest fixes (2026-11-15)

From Kham's PSP Go playtest and Muse's browser playtest (`playtests/2026-11-15_muse_html-play-report.md`). Changes are in `src/07_game_engine.js`, rebuilt with `build.py`. `beatsts.html` sha256 is now `ad4fd025…` (was `b12be617…`).

1. **Dialog paging.**
   - **Bug:** the dialog box holds 4 wrapped lines and never paged. 388 of 691 NPC lines overflowed below the box. Their endings were lost when A/B advanced, and a single long line closed before it could be read.
   - **Fix:** `showDialog` now splits each entry into 4-line pages, using the same 27-character wrap as `renderDialog`.
   - **Checked in Chromium:** 916 NPC and sign lines, 517 of them now paged (max 2 pages); no page over 4 lines; and **no words lost** (the pages rejoin to the original text).
2. **Name field.**
   - **Bug:** game keys were read while typing a name. W A S D Z X M N, Space and Backspace were eaten, and also triggered game actions, so typing "Muse" gave "ue".
   - **Fix:** keys are now ignored while a text field has focus.
   - **Checked in Chromium:** typing into the field gives exactly what was typed, Backspace works, and the game doesn't react.
3. **Tab no longer means SELECT.**
   - **Bug:** Tab and N both mapped to SELECT, which toggles day/night. Tabbing around the page flipped the clock.
   - **Fix:** Tab is removed from SELECT; N still works.
   - **Checked in Chromium:** Tab leaves day/night alone; N toggles it.

**Not changed: the Cruston Town exit.** Muse's §4.1 said the town has no signs. It has three. "North: Toastwood Trail" is at (14,2), right at the head of the north road, and it reads correctly when faced (checked). The one-tile exit at (16,0) is left for Kham's map pass.

**Tests:**
- `node tests/run-all.js` gives **all 13 tests passing** (`audit/kehai/playtest-fixes/run-all.log`): the completion bot, all 16 quests, the dex bot and the browser tests.
- The GBA port (`deliveries/gba-argon-2`) still uses the old unpaged dialog. Its next round has to port the paging and the pixel differential will show if it doesn't.
