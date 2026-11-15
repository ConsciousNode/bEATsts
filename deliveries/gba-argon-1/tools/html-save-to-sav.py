#!/usr/bin/env python3
"""
tools/html-save-to-sav.py - bEATsts 2.2 HTML JSON Save <-> 32 KB GBA SRAM (.sav) Converter
Copyright (c) 2026 Khamerron Kizer / ConsciousNode SoftWorks
License: MIT
House Philosophy: Xinu (Single File, Zero Dependencies, Offline-First)
PROVENANCE: Canonical table ordering extracted from beatsts-2.2/beatsts.html (ConsciousNode/bEATsts f1fc208).

Usage:
  python3 tools/html-save-to-sav.py save.json -o beatsts.sav [--slot 0]
  python3 tools/html-save-to-sav.py beatsts.sav --to-json -o roundtrip.json [--slot 0]
"""

import argparse
import json
import os
import re
import struct
import sys

SRAM_SIZE = 0x8000        # 32 KB
SLOT_SIZE = 0x1000        # 4,096 bytes per slot
SAVE_MAGIC = 0x54414542   # "BEAT" in little-endian
SAVE_VERSION = 0x22       # bEATsts 2.2

CANONICAL_TYPES = [
    'Toasted', 'Steamed', 'Fried', 'Pickled',
    'Spicy', 'Brothy', 'Raw', 'Fermented',
    'Sweet', 'Savory', 'Chilled', 'Herbal'
]

CANONICAL_STATUSES = [
    None, 'Sizzling', 'Brined', 'Drowsy', 'Seasoned', 'Appetized'
]

CANONICAL_SEALS = [
    'Crisp Seal', 'Stack Seal', 'Steam Seal', 'Sear Seal',
    'Slurp Seal', 'Twirl Seal', 'Simmer Seal', 'Stock Seal'
]

CANONICAL_DIRS = ['down', 'up', 'left', 'right']

CANONICAL_ITEMS = [
    'paper_plate', 'wooden_board', 'ceramic_plate', 'bento_set', 'royal_banquet',
    'broth_cup', 'hearty_stew', 'grand_feast', 'mint_tea', 'wakeup_espresso',
    'garnish_treat', 'card_toasted', 'card_steamed', 'card_fried', 'card_pickled',
    'card_spicy', 'card_brothy', 'card_raw', 'card_fermented', 'card_sweet',
    'card_savory', 'card_chilled', 'card_herbal', 'soup_ladle', 'kitchen_lantern'
]

CANONICAL_QUESTS = [
    'q1_butter', 'q2_lid', 'q3_chopsticks', 'q4_truffle',
    'q5_starter', 'q6_ginger', 'q7_chili', 'q8_ladle',
    'q9_critics', 'q10_crumb', 'q11_scallion', 'q12_salt',
    'q13_stock', 'q14_steam', 'q15_wok', 'q16_banquet'
]

CANONICAL_SECRETS = [
    'sec_151', 'sec_crust_stash', 'sec_toast_cache', 'sec_sourdough_jar',
    'sec_bao_pearl', 'sec_spire_scroll', 'sec_canyon_noodle', 'sec_wok_ember',
    'sec_fen_truffle', 'sec_catacomb_stock', 'sec_hall_toast', 'sec_eternal_spoon'
]

CANONICAL_TRAINERS = [
    'jr_bread_1', 'jr_bread_2', 'jr_steam_1', 'jr_steam_2',
    'jr_noodle_1', 'jr_noodle_2', 'jr_broth_1', 'jr_broth_2',
    'truffle_guard', 'chef_greg', 'chef_clara', 'chef_baozi',
    'chef_mei', 'chef_twirl', 'chef_fusilli', 'chef_bisque',
    'chef_bouillon', 'officer_vesper', 'officer_crumb', 'officer_glaze',
    'syndicate_grunt_1', 'syndicate_grunt_2', 'boss_ladle',
    'rival_1', 'rival_2', 'rival_3', 'rival_4', 'rival_5', 'rival_6',
    'taster_pip', 'taster_roux', 'taster_mochi', 'champion_aurelia'
]

CANONICAL_MAPS = [
    'cruston_town', 'toastwood_trail', 'deli_meadows', 'panini_plaza',
    'bao_harbor', 'bamboo_mist_path', 'gyoza_cove', 'pierogi_pier',
    'udon_hollow', 'slurp_canyon', 'al_dente_ascent', 'ramen_summit',
    'chowder_crossing', 'simmer_fen', 'kettle_gorge', 'bisque_bastion',
    'grand_tasting_hall', 'eternal_pantry',
    'sourdough_cavern', 'sourdough_cavern_b2', 'truffle_cellar', 'truffle_cellar_b2',
    'steamer_spire', 'steamer_spire_f2', 'wok_volcano', 'wok_volcano_f2',
    'broth_catacombs', 'broth_catacombs_b2', 'chrome_fork_hq', 'chrome_fork_hq_f2',
    'gym_toaster', 'gym_deli', 'gym_bamboo', 'gym_skillet',
    'gym_dojo', 'gym_wokpeak', 'gym_cauldron', 'gym_vault',
    'cruston_lab', 'cruston_inn', 'cruston_mart', 'cruston_cafe',
    'panini_inn', 'panini_bakery', 'bao_inn', 'bao_mart',
    'pierogi_inn', 'pierogi_teahouse', 'udon_inn', 'udon_noodlebar',
    'ramen_inn', 'ramen_forge', 'chowder_inn', 'chowder_mart',
    'bisque_inn', 'bisque_archive'
]


def fnv1a32(data_bytes):
    h = 0x811C9DC5
    for b in data_bytes:
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def compute_quest_state_hash(quests_dict):
    h = 0x811C9DC5
    for qid in CANONICAL_QUESTS:
        done = 1 if quests_dict.get(qid) else 0
        started = 2 if quests_dict.get(qid + '_started') else 0
        step = (int(quests_dict.get(qid + '_step', 0)) & 0xF) << 2
        b = done | started | step
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def pack_party_mon(mon):
    buf = bytearray(48)
    uid = int(mon.get('uid', 0)) & 0xFFFFFFFF
    sp_id = int(mon.get('speciesId', 1)) & 0xFF
    level = int(mon.get('level', 1)) & 0xFF
    st_str = mon.get('status', None)
    status = CANONICAL_STATUSES.index(st_str) if st_str in CANONICAL_STATUSES else 0
    lmt_str = mon.get('lastMoveType', None)
    lmt = CANONICAL_TYPES.index(lmt_str) if lmt_str in CANONICAL_TYPES else 0xFF
    hp = int(mon.get('hp', 1)) & 0xFFFF
    max_hp = int(mon.get('maxHp', 1)) & 0xFFFF
    atk = int(mon.get('atk', 1)) & 0xFFFF
    dfn = int(mon.get('def', 1)) & 0xFFFF
    spd = int(mon.get('spd', 1)) & 0xFFFF
    moves = mon.get('moves', [])[:4]
    mv_cnt = len(moves)
    xp = int(mon.get('xp', level * level * 8)) & 0xFFFFFFFF
    next_xp = int(mon.get('nextXp', (level + 1) * (level + 1) * 8)) & 0xFFFFFFFF

    struct.pack_into(
        '<IBBBBHHHHHHII', buf, 0,
        uid, sp_id, level, status, lmt,
        hp, max_hp, atk, dfn, spd, mv_cnt,
        xp, next_xp
    )
    for i in range(4):
        if i < mv_cnt:
            buf[0x1C + i] = int(moves[i].get('id', 0)) & 0xFF
            buf[0x20 + i] = int(moves[i].get('pp', 0)) & 0xFF
            buf[0x24 + i] = int(moves[i].get('maxPp', moves[i].get('pp', 0))) & 0xFF
        else:
            buf[0x1C + i] = 0xFF
            buf[0x20 + i] = 0
            buf[0x24 + i] = 0
    return bytes(buf)


def unpack_party_mon(buf, species_names=None, move_pps=None):
    (uid, sp_id, level, status, lmt,
     hp, max_hp, atk, dfn, spd, mv_cnt,
     xp, next_xp) = struct.unpack_from('<IBBBBHHHHHHII', buf, 0)
    moves = []
    for i in range(min(4, mv_cnt)):
        mid = buf[0x1C + i]
        if mid != 0xFF:
            moves.append({
                'id': mid,
                'pp': buf[0x20 + i],
                'maxPp': buf[0x24 + i]
            })
    name = (species_names or {}).get(sp_id, f'bEATst#{sp_id}')
    return {
        'uid': uid,
        'speciesId': sp_id,
        'nickname': name,
        'level': level,
        'xp': xp,
        'nextXp': next_xp,
        'hp': hp,
        'maxHp': max_hp,
        'atk': atk,
        'def': dfn,
        'spd': spd,
        'status': CANONICAL_STATUSES[status] if status < len(CANONICAL_STATUSES) else None,
        'lastMoveType': CANONICAL_TYPES[lmt] if lmt < len(CANONICAL_TYPES) else None,
        'moves': moves
    }


def pack_box_mon(mon):
    buf = bytearray(24)
    uid = int(mon.get('uid', 0)) & 0xFFFFFFFF
    sp_id = int(mon.get('speciesId', 1)) & 0xFF
    level = int(mon.get('level', 1)) & 0xFF
    st_str = mon.get('status', None)
    status = CANONICAL_STATUSES.index(st_str) if st_str in CANONICAL_STATUSES else 0
    moves = mon.get('moves', [])[:4]
    mv_cnt = len(moves)
    hp = int(mon.get('hp', 1)) & 0xFFFF
    max_hp = int(mon.get('maxHp', 1)) & 0xFFFF
    atk = int(mon.get('atk', 1)) & 0xFFFF
    dfn = int(mon.get('def', 1)) & 0xFFFF
    spd = int(mon.get('spd', 1)) & 0xFFFF
    xp_div8 = (int(mon.get('xp', level * level * 8)) // 8) & 0xFFFF

    struct.pack_into(
        '<IBBBBHHHHHH', buf, 0,
        uid, sp_id, level, status, mv_cnt,
        hp, max_hp, atk, dfn, spd, xp_div8
    )
    for i in range(4):
        buf[0x14 + i] = (int(moves[i].get('id', 0)) & 0xFF) if i < mv_cnt else 0xFF
    return bytes(buf)


def unpack_box_mon(buf, species_names=None, move_pps=None):
    (uid, sp_id, level, status, mv_cnt,
     hp, max_hp, atk, dfn, spd, xp_div8) = struct.unpack_from('<IBBBBHHHHHH', buf, 0)
    moves = []
    for i in range(min(4, mv_cnt)):
        mid = buf[0x14 + i]
        if mid != 0xFF:
            pp = (move_pps or {}).get(mid, 20)
            moves.append({'id': mid, 'pp': pp, 'maxPp': pp})
    name = (species_names or {}).get(sp_id, f'bEATst#{sp_id}')
    return {
        'uid': uid,
        'speciesId': sp_id,
        'nickname': name,
        'level': level,
        'xp': xp_div8 * 8,
        'nextXp': (level + 1) * (level + 1) * 8,
        'hp': hp,
        'maxHp': max_hp,
        'atk': atk,
        'def': dfn,
        'spd': spd,
        'status': CANONICAL_STATUSES[status] if status < len(CANONICAL_STATUSES) else None,
        'lastMoveType': None,
        'moves': moves
    }


def encode_save_slot(state, slot_idx=0):
    slot = bytearray(SLOT_SIZE)
    name_str = str(state.get('name', 'Brie'))[:10].encode('ascii', 'replace')
    slot[0x00C:0x00C + len(name_str)] = name_str

    play_time = int(state.get('playTimeSec', 0)) & 0xFFFFFFFF
    rng_seed = int(state.get('rngSeed', 4242)) & 0xFFFFFFFF
    steps = int(state.get('steps', 0)) & 0xFFFFFFFF
    gold = int(state.get('gold', 500)) & 0xFFFFFFFF
    struct.pack_into('<IIII', slot, 0x018, play_time, rng_seed, steps, gold)

    map_str = state.get('mapId', 'cruston_town')
    map_idx = CANONICAL_MAPS.index(map_str) if map_str in CANONICAL_MAPS else 0
    x = int(state.get('x', 14)) & 0xFF
    y = int(state.get('y', 12)) & 0xFF
    dir_str = state.get('dir', 'up')
    dir_idx = CANONICAL_DIRS.index(dir_str) if dir_str in CANONICAL_DIRS else 1
    is_night = 1 if state.get('isNight', False) else 0
    look_str = str(state.get('playerLook', 'player_0'))
    look_idx = int(look_str.split('_')[-1]) if '_' in look_str and look_str.split('_')[-1].isdigit() else 0
    champ = 1 if state.get('championBeaten', False) else 0

    seals_list = state.get('seals', [])
    seals_mask = 0
    for i, sname in enumerate(CANONICAL_SEALS):
        if sname in seals_list:
            seals_mask |= (1 << i)
    if seals_mask == 0 and len(seals_list) > 0:
        seals_mask = (1 << min(8, len(seals_list))) - 1

    struct.pack_into('<BBBBBBBB', slot, 0x028, map_idx, x, y, dir_idx, is_night, look_idx, champ, seals_mask)

    switches = state.get('switches', {}) or {}
    for mid, active in switches.items():
        if active and mid in CANONICAL_MAPS:
            idx = CANONICAL_MAPS.index(mid)
            slot[0x030 + (idx >> 3)] |= (1 << (idx & 7))

    defeated = state.get('defeatedTrainers', []) or []
    for tid in defeated:
        if tid in CANONICAL_TRAINERS:
            idx = CANONICAL_TRAINERS.index(tid)
            slot[0x038 + (idx >> 3)] |= (1 << (idx & 7))

    secrets = state.get('secrets', []) or []
    secrets_mask = 0
    for sid in secrets:
        if sid in CANONICAL_SECRETS:
            secrets_mask |= (1 << CANONICAL_SECRETS.index(sid))
    struct.pack_into('<H', slot, 0x040, secrets_mask)

    quests = state.get('quests', {}) or {}
    q_done = 0
    q_started = 0
    for i, qid in enumerate(CANONICAL_QUESTS):
        if quests.get(qid):
            q_done |= (1 << i)
        if quests.get(qid + '_started') or quests.get(qid):
            q_started |= (1 << i)
        slot[0x046 + i] = int(quests.get(qid + '_step', 0)) & 0xFF
    struct.pack_into('<HH', slot, 0x042, q_done, q_started)

    for sp_id in state.get('dexSeen', []) or []:
        idx = int(sp_id) - 1
        if 0 <= idx < 151:
            slot[0x056 + (idx >> 3)] |= (1 << (idx & 7))

    for sp_id in state.get('dexCaught', []) or []:
        idx = int(sp_id) - 1
        if 0 <= idx < 151:
            slot[0x056 + (idx >> 3)] |= (1 << (idx & 7))
            slot[0x06A + (idx >> 3)] |= (1 << (idx & 7))

    bag = state.get('bag', {}) or {}
    for i, item_id in enumerate(CANONICAL_ITEMS):
        cnt = max(0, min(65535, int(bag.get(item_id, 0))))
        struct.pack_into('<H', slot, 0x07E + i * 2, cnt)

    party = (state.get('party', []) or [])[:6]
    box = (state.get('box', []) or [])[:151]
    slot[0x0B0] = len(party)
    slot[0x0B1] = len(box)

    for i, mon in enumerate(party):
        slot[0x0B4 + i * 48 : 0x0B4 + (i + 1) * 48] = pack_party_mon(mon)

    for i, mon in enumerate(box):
        slot[0x1D4 + i * 24 : 0x1D4 + (i + 1) * 24] = pack_box_mon(mon)

    chk = fnv1a32(slot[0x00C:0x1000])
    struct.pack_into('<IBBHI', slot, 0x000, SAVE_MAGIC, SAVE_VERSION, slot_idx & 0xFF, 0, chk)
    return bytes(slot)


def decode_save_slot(slot_bytes, species_names=None, move_pps=None):
    if len(slot_bytes) < SLOT_SIZE:
        raise ValueError("Slot buffer shorter than 4096 bytes")
    magic, version, slot_idx, _, chk = struct.unpack_from('<IBBHI', slot_bytes, 0x000)
    if magic != SAVE_MAGIC or version != SAVE_VERSION:
        raise ValueError(f"Invalid slot header: magic=0x{magic:08X}, version=0x{version:02X}")
    calc_chk = fnv1a32(slot_bytes[0x00C:0x1000])
    if chk != calc_chk:
        raise ValueError(f"Checksum mismatch: header=0x{chk:08X} != calculated=0x{calc_chk:08X}")

    raw_name = slot_bytes[0x00C:0x018].split(b'\x00', 1)[0].decode('ascii', 'replace')
    play_time, rng_seed, steps, gold = struct.unpack_from('<IIII', slot_bytes, 0x018)
    map_idx, x, y, dir_idx, is_night, look_idx, champ, seals_mask = struct.unpack_from('<BBBBBBBB', slot_bytes, 0x028)

    switches = {}
    for idx, mid in enumerate(CANONICAL_MAPS):
        if slot_bytes[0x030 + (idx >> 3)] & (1 << (idx & 7)):
            switches[mid] = True

    defeated = []
    for idx, tid in enumerate(CANONICAL_TRAINERS):
        if slot_bytes[0x038 + (idx >> 3)] & (1 << (idx & 7)):
            defeated.append(tid)

    secrets_mask, q_done, q_started = struct.unpack_from('<HHH', slot_bytes, 0x040)
    secrets = [CANONICAL_SECRETS[i] for i in range(len(CANONICAL_SECRETS)) if secrets_mask & (1 << i)]

    quests = {}
    for i, qid in enumerate(CANONICAL_QUESTS):
        step = slot_bytes[0x046 + i]
        if q_started & (1 << i):
            quests[qid + '_started'] = True
            quests[qid + '_step'] = step
            for s in range(1, step + 1):
                quests[f'{qid}_step{s}'] = True
        if q_done & (1 << i):
            quests[qid] = True

    dex_seen = []
    dex_caught = []
    for i in range(151):
        if slot_bytes[0x056 + (i >> 3)] & (1 << (i & 7)):
            dex_seen.append(i + 1)
        if slot_bytes[0x06A + (i >> 3)] & (1 << (i & 7)):
            dex_caught.append(i + 1)

    bag = {}
    for i, item_id in enumerate(CANONICAL_ITEMS):
        cnt = struct.unpack_from('<H', slot_bytes, 0x07E + i * 2)[0]
        if cnt > 0:
            bag[item_id] = cnt

    party_cnt = slot_bytes[0x0B0]
    box_cnt = slot_bytes[0x0B1]
    party = []
    for i in range(min(6, party_cnt)):
        party.append(unpack_party_mon(slot_bytes[0x0B4 + i * 48 : 0x0B4 + (i + 1) * 48], species_names, move_pps))
    box = []
    for i in range(min(151, box_cnt)):
        box.append(unpack_box_mon(slot_bytes[0x1D4 + i * 24 : 0x1D4 + (i + 1) * 24], species_names, move_pps))

    seals = [CANONICAL_SEALS[i] for i in range(8) if seals_mask & (1 << i)]

    return {
        'slot': slot_idx,
        'name': raw_name or 'Brie',
        'playTimeSec': play_time,
        'rngSeed': rng_seed,
        'steps': steps,
        'isNight': bool(is_night),
        'gold': gold,
        'mapId': CANONICAL_MAPS[map_idx] if map_idx < len(CANONICAL_MAPS) else 'cruston_town',
        'x': x,
        'y': y,
        'dir': CANONICAL_DIRS[dir_idx] if dir_idx < 4 else 'down',
        'playerLook': f'player_{look_idx}',
        'switches': switches,
        'seals': seals,
        'defeatedTrainers': defeated,
        'quests': quests,
        'secrets': secrets,
        'championBeaten': bool(champ),
        'dexSeen': dex_seen,
        'dexCaught': dex_caught,
        'party': party,
        'box': box,
        'bag': bag
    }


def main():
    parser = argparse.ArgumentParser(description="Convert bEATsts 2.2 HTML JSON save to/from 32 KB GBA SRAM (.sav).")
    parser.add_argument("input", help="Input .json save file (or .sav file with --to-json)")
    parser.add_argument("-o", "--output", required=True, help="Output .sav file (or .json file with --to-json)")
    parser.add_argument("--slot", type=int, default=None, help="Slot index 0..2 (defaults to state.slot or 0)")
    parser.add_argument("--to-json", action="store_true", help="Convert a .sav slot back to HTML JSON save format")
    args = parser.parse_args()

    if args.to_json:
        with open(args.input, "rb") as f:
            sav = f.read()
        slot_idx = args.slot if args.slot is not None else 0
        off = slot_idx * SLOT_SIZE
        state = decode_save_slot(sav[off : off + SLOT_SIZE])
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        print(f"[html-save-to-sav] Decoded slot {slot_idx} from {args.input} -> {args.output}")
        return 0

    with open(args.input, "r", encoding="utf-8") as f:
        state = json.load(f)

    slot_idx = args.slot if args.slot is not None else int(state.get("slot", 0))
    if not (0 <= slot_idx <= 2):
        raise ValueError(f"Slot index must be 0, 1, or 2 (got {slot_idx})")

    if os.path.exists(args.output) and os.path.getsize(args.output) == SRAM_SIZE:
        with open(args.output, "rb") as f:
            sram = bytearray(f.read())
    else:
        sram = bytearray(b"\xFF" * SRAM_SIZE)

    slot_bytes = encode_save_slot(state, slot_idx)
    off = slot_idx * SLOT_SIZE
    sram[off : off + SLOT_SIZE] = slot_bytes

    with open(args.output, "wb") as f:
        f.write(sram)

    chk = struct.unpack_from("<I", slot_bytes, 0x008)[0]
    print(f"[html-save-to-sav] Wrote slot {slot_idx} ({SLOT_SIZE} B, checksum=0x{chk:08X}) into {args.output} ({len(sram)} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
