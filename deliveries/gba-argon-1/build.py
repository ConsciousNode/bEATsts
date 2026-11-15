#!/usr/bin/env python3
"""
build.py - Self-Contained Pure-Python GBA ROM Builder & ARM7TDMI Assembler for bEATsts 2.2
Copyright (c) 2026 Khamerron Kizer / ConsciousNode SoftWorks
License: MIT
House Philosophy: Xinu (Single File, Zero External Dependencies, Offline-First, Deterministic)

Extracts all data tables, sprites, fonts, maps, trainers, quests, secrets, and audio tracks
from beatsts-2.2/beatsts.html and assembles beatsts.gba byte-for-byte.
"""

import hashlib
import json
import math
import os
import re
import struct
import sys
import zlib

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_HTML_PATH = os.path.join(ROOT_DIR, "beatsts-2.2", "beatsts.html")
OUT_ROM_PATH = os.path.join(ROOT_DIR, "beatsts.gba")

# PROVENANCE: Official 156-byte GBA boot logo bitmap lifted from 1337boy/tools/1337ify.py (MIT).
NINTENDO_LOGO = bytes([
    0x24, 0xFF, 0xAE, 0x51, 0x69, 0x9A, 0xA2, 0x21, 0x3D, 0x84, 0x82, 0x0A,
    0x84, 0xE4, 0x09, 0xAD, 0x11, 0x24, 0x8B, 0x98, 0xC0, 0x81, 0x7F, 0x21,
    0xA3, 0x52, 0xBE, 0x19, 0x93, 0x09, 0xCE, 0x20, 0x10, 0x46, 0x4A, 0x4A,
    0xF8, 0x27, 0x31, 0xEC, 0x58, 0xC7, 0xE8, 0x33, 0x82, 0xE3, 0xCE, 0xBF,
    0x85, 0xF4, 0xDF, 0x94, 0xCE, 0x4B, 0x09, 0xC1, 0x94, 0x56, 0x8A, 0xC0,
    0x13, 0x72, 0xA7, 0xFC, 0x9F, 0x84, 0x4D, 0x73, 0xA3, 0xCA, 0x9A, 0x61,
    0x58, 0x97, 0xA3, 0x27, 0xFC, 0x03, 0x98, 0x76, 0x23, 0x1D, 0xC7, 0x61,
    0x03, 0x04, 0xAE, 0x56, 0xBF, 0x38, 0x84, 0x00, 0x40, 0xA7, 0x0E, 0xFD,
    0xFF, 0x52, 0xFE, 0x03, 0x6F, 0x95, 0x30, 0xF1, 0x97, 0xFB, 0xC0, 0x85,
    0x60, 0xD6, 0x80, 0x25, 0xA9, 0x63, 0xBE, 0x03, 0x01, 0x4E, 0x38, 0xE2,
    0xF9, 0xA2, 0x34, 0xFF, 0xBB, 0x3E, 0x03, 0x44, 0x78, 0x00, 0x90, 0xCB,
    0x88, 0x11, 0x3A, 0x94, 0x65, 0xC0, 0x7C, 0x63, 0x87, 0xF0, 0x3C, 0xAF,
    0xD6, 0x25, 0xE4, 0x8B, 0x38, 0x0A, 0xAC, 0x72, 0x21, 0xD4, 0xF8, 0x07
])


def f64_u64(d):
    return struct.unpack("<Q", struct.pack("<d", float(d)))[0]


def to_bgr555(hex_str):
    if not hex_str:
        return 0
    r = (int(hex_str[1:3], 16) >> 3) & 31
    g = (int(hex_str[3:5], 16) >> 3) & 31
    b = (int(hex_str[5:7], 16) >> 3) & 31
    return r | (g << 5) | (b << 10)


class StringPool:
    def __init__(self):
        self.buf = bytearray()
        self.offsets = {}

    def add(self, s):
        if s is None:
            return 0xFFFFFFFF
        s = str(s)
        if s in self.offsets:
            return self.offsets[s]
        off = len(self.buf)
        self.buf.extend(s.encode("utf-8") + b"\x00")
        self.offsets[s] = off
        return off


# =============================================================================
# 1. Pure-Python Reference Extractor (from beatsts-2.2/beatsts.html)
# =============================================================================

def js_obj_to_json(src):
    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in ' \t\r\n':
            out.append(c)
            i += 1
        elif c == '/' and i + 1 < n and src[i + 1] == '/':
            while i < n and src[i] != '\n':
                i += 1
        elif c == '/' and i + 1 < n and src[i + 1] == '*':
            i += 2
            while i + 1 < n and not (src[i] == '*' and src[i + 1] == '/'):
                i += 1
            i += 2
        elif c in ("'", '"'):
            quote = c
            i += 1
            s_chars = []
            while i < n and src[i] != quote:
                if src[i] == '\\':
                    i += 1
                    if i < n:
                        esc = src[i]
                        if esc in ('"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u'):
                            s_chars.append('\\' + esc)
                        else:
                            s_chars.append(esc)
                        i += 1
                else:
                    if src[i] == '"':
                        s_chars.append('\\"')
                    else:
                        s_chars.append(src[i])
                    i += 1
            i += 1
            out.append('"' + ''.join(s_chars) + '"')
        elif c.isdigit():
            j = i
            while j < n and (src[j].isdigit() or src[j] == '.'):
                j += 1
            num = src[i:j]
            k = j
            while k < n and src[k] in ' \t\r\n':
                k += 1
            if k < n and src[k] == ':':
                out.append(f'"{num}"')
            else:
                out.append(num)
            i = j
        elif c.isalpha() or c == '_':
            j = i
            while j < n and (src[j].isalnum() or src[j] == '_'):
                j += 1
            ident = src[i:j]
            k = j
            while k < n and src[k] in ' \t\r\n':
                k += 1
            if k < n and src[k] == ':':
                out.append(f'"{ident}"')
            elif ident in ('true', 'false', 'null'):
                out.append(ident)
            else:
                out.append(f'"{ident}"')
            i = j
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def extract_reference_data(html_path=REF_HTML_PATH):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    m_sans = re.search(r"const FONT_SANS_HEX = (\[[^\]]+\]);", html)
    m_serif = re.search(r"const FONT_SERIF_HEX = (\[[^\]]+\]);", html)
    font_sans_hex = json.loads(m_sans.group(1).replace("'", "\""))
    font_serif_hex = json.loads(m_serif.group(1).replace("'", "\""))
    font_sans_bytes = bytes(int(h[r * 2:r * 2 + 2], 16) for h in font_sans_hex for r in range(8))
    font_serif_bytes = bytes(int(h[r * 2:r * 2 + 2], 16) for h in font_serif_hex for r in range(16))

    def extract_const(name, end_marker):
        pat = re.compile(rf"const {name} = ([\s\S]*?);(?=\s*{end_marker})")
        m = pat.search(html)
        if not m:
            raise ValueError(f"Could not find const {name}")
        return json.loads(js_obj_to_json(m.group(1)))

    types = extract_const("TYPES", "const TYPE_COLORS")
    type_colors = extract_const("TYPE_COLORS", "// 12x12 Type Chart")
    type_chart = extract_const("TYPE_CHART", "function getTypeEffectiveness")
    flavor_combos = extract_const("FLAVOR_COMBOS", "const MOVES")
    moves = extract_const("MOVES", "// === 02_beatsts_data.js ===")
    type_move_pools = extract_const("TYPE_MOVE_POOLS", "function buildLearnset")
    raw_beatsts = extract_const("RAW_BEATSTS", "// === 03_sprites_and_tiles.js ===")
    type_palette_accents = extract_const("TYPE_PALETTE_ACCENTS", "function buildSpeciesPalette")
    tile_roles = extract_const("TILE_ROLES", "const TILES_8X8")
    char_sprites = extract_const("CHAR_SPRITES", "function buildCharSpriteGrid")
    items = extract_const("ITEMS", "// Progressive Pantry Mart")
    m_shops = re.search(r"const REGIONAL_SHOPS = ([\s\S]*?);\n\nfunction calcPlatingChance", html)
    shops_raw = m_shops.group(1).replace(
        "Object.keys(ITEMS).filter(k => ITEMS[k].kind !== 'key')",
        json.dumps([k for k, v in items.items() if v["kind"] != "key"])
    )
    regional_shops = json.loads(js_obj_to_json(shops_raw))
    regions = extract_const("REGIONS", "const SOLID_TILES")
    m_solid = re.search(r"const SOLID_TILES = new Set\((\[[^\]]+\])\);", html)
    solid_tiles = json.loads(m_solid.group(1))
    quests = extract_const("QUESTS", "const SECRETS")
    secrets = extract_const("SECRETS", "const TRAINERS")
    trainers = extract_const("TRAINERS", "const MAPS")
    m_maps = re.search(r"const MAPS = (\{.*\});\nfor \(const k of Object\.keys\(MAPS\)\)", html)
    maps = json.loads(m_maps.group(1))
    sfx_defs = extract_const("SFX_DEFS", "function renderSequenceOffline")

    def buildPhraseTrack(bpm, loop, p1Phrases, p2Phrases, wvPhrases, nsPhrases):
        shifts = [0, 0, 2, 0, 5, 4, 2, 0, -2, 0, 5, 7, 5, 4, 2, 0]
        def expand(phrases, sh_list):
            out = []
            for i, sh in enumerate(sh_list):
                ph = phrases[i % len(phrases)]
                for m_n, d in ph:
                    out.append([m_n + sh if m_n > 0 else 0, d])
            return out
        return {
            "bpm": bpm, "loop": loop,
            "pulse1": expand(p1Phrases, shifts),
            "pulse2": expand(p2Phrases, shifts),
            "wave": expand(wvPhrases, shifts),
            "noise": expand(nsPhrases, [0] * len(shifts))
        }

    m_mt = re.search(r"const MUSIC_TRACKS = \{([\s\S]*?)\n\};\n\nconst SFX_DEFS =", html)
    mt_src = m_mt.group(1)
    music_tracks = {}
    for m_tr in re.finditer(r"(\w+):\s*(buildPhraseTrack\([\s\S]*?\)\s*(?=[,\n]\s*\w+:|\s*$)|\{[\s\S]*?\}\s*(?=[,\n]\s*\w+:|\s*$))", mt_src):
        tname = m_tr.group(1)
        tbody = m_tr.group(2).strip()
        if tbody.startswith("buildPhraseTrack("):
            inner = tbody[len("buildPhraseTrack("):-1]
            args = json.loads("[" + js_obj_to_json(inner) + "]")
            music_tracks[tname] = buildPhraseTrack(*args)
        else:
            music_tracks[tname] = json.loads(js_obj_to_json(tbody))

    def toGba15_hex(hex_str):
        r = int(hex_str[1:3], 16) & 0xF8
        g = int(hex_str[3:5], 16) & 0xF8
        b = int(hex_str[5:7], 16) & 0xF8
        return f"#{r:02x}{g:02x}{b:02x}"

    def js_round(x):
        return math.floor(x + 0.5)

    def buildSpeciesPalette(sp):
        t1 = type_palette_accents.get(sp["types"][0], type_palette_accents["Savory"])
        t2 = type_palette_accents.get(sp["types"][1] if len(sp["types"]) > 1 else sp["types"][0], t1)
        raw = [
            None,
            '#181820', t1[0], t1[1], t1[2], t2[0], t2[1], t2[2],
            '#F8F8F0', '#F0C868', '#D04038', '#50B848', '#F8E888', '#885030', '#C0C8D0', '#FF90A8'
        ]
        return [toGba15_hex(c) if c else None for c in raw]

    def drawBeatstSprite32(sp, isBack):
        g = [0] * (32 * 32)
        def setPx32(x, y, c):
            ix = js_round(x)
            iy = js_round(y)
            if 0 <= ix < 32 and 0 <= iy < 32:
                g[iy * 32 + ix] = c
        def fillRect32(x0, y0, w, h, c):
            for y in range(y0, y0 + h):
                for x in range(x0, x0 + w):
                    setPx32(x, y, c)
        def fillEllipse32(cx, cy, rx, ry, c):
            for y in range(math.floor(cy - ry), math.ceil(cy + ry) + 1):
                for x in range(math.floor(cx - rx), math.ceil(cx + rx) + 1):
                    dx = (x - cx) / rx
                    dy = (y - cy) / ry
                    if dx * dx + dy * dy <= 1.0:
                        setPx32(x, y, c)
        def outlineGrid32(outlineIdx=1):
            copy = list(g)
            for y in range(32):
                for x in range(32):
                    if copy[y * 32 + x] != 0:
                        continue
                    n = ((y > 0 and copy[(y - 1) * 32 + x]) or (y < 31 and copy[(y + 1) * 32 + x]) or
                         (x > 0 and copy[y * 32 + (x - 1)]) or (x < 31 and copy[y * 32 + (x + 1)]))
                    if n:
                        g[y * 32 + x] = outlineIdx

        sh = sp["shape"]
        s = sh["sizeMod"]
        cx = 16
        cy = 17 - s
        pose = sh["pose"]
        if pose == 'high': cy -= 4
        elif pose == 'low': cy += 4
        elif pose == 'left': cx -= 5
        elif pose == 'right': cx += 5
        elif pose == 'lean_l': cx -= 4; cy -= 3
        elif pose == 'lean_r': cx += 4; cy += 3
        elif pose == 'wide': cy += 2; fillRect32(cx - 13, cy + 1, 26, 3, 2)
        elif pose == 'tall': cy -= 3; fillRect32(cx - 4, cy - 10, 8, 6, 2)

        arch = sh["arch"]
        if arch == 'slice':
            w = 12 + s * 3; h = 11 + s * 2
            fillRect32(cx - (w // 2), cy - (h // 2), w, 3, 9)
            fillRect32(cx - (w // 2) - 1, cy - (h // 2) + 3, w + 2, 2, 11)
            fillRect32(cx - (w // 2), cy - (h // 2) + 5, w, 2, 5)
            fillRect32(cx - (w // 2), cy - (h // 2) + 7, w, h - 7, 9)
        elif arch == 'club':
            w = 13 + s * 2
            for r in range(14 + s * 2):
                rw = max(4, (r + 2) * w // (15 + s * 2))
                fillRect32(cx - (rw // 2), 6 + r, rw, 1, 9 if r % 4 == 0 else (11 if r % 4 == 1 else (10 if r % 4 == 2 else 5)))
        elif arch == 'sub':
            fillEllipse32(cx, cy + 1, 11 + s * 2, 4 + s, 9)
            fillRect32(cx - 9 - s, cy, 18 + s * 2, 2, 11)
            fillRect32(cx - 8 - s, cy + 1, 16 + s * 2, 2, 5)
        elif arch == 'burger':
            r = 7 + s * 2
            fillEllipse32(cx, cy - 3, r, 4 + s, 9)
            fillRect32(cx - r - 1, cy + 1, r * 2 + 2, 2, 12)
            fillRect32(cx - r, cy + 3, r * 2, 2, 13)
            fillRect32(cx - r + 1, cy + 5, r * 2 - 2, 3, 9)
        elif arch == 'croissant':
            fillEllipse32(cx, cy, 8 + s * 2, 4 + s, 9)
            fillEllipse32(cx - 6 - s, cy + 3, 3 + s, 3, 3)
            fillEllipse32(cx + 6 + s, cy + 3, 3 + s, 3, 3)
        elif arch == 'pita':
            fillEllipse32(cx, cy + 2, 8 + s * 2, 7 + s, 9)
            fillEllipse32(cx, cy - 2, 6 + s, 3, 5)
            fillRect32(cx - 5, cy - 3, 10, 2, 11)
        elif arch == 'waffle':
            sz = 12 + s * 3
            fillRect32(cx - (sz // 2), cy - (sz // 2), sz, sz, 9)
            for y in range(cy - (sz // 2) + 2, cy + (sz // 2) - 1, 3):
                for x in range(cx - (sz // 2) + 2, cx + (sz // 2) - 1, 3):
                    setPx32(x, y, 3)
        elif arch == 'bagel':
            r = 8 + s * 2
            fillEllipse32(cx, cy, r, r - 1, 9)
            fillEllipse32(cx, cy, 2 + s, 2, 0)
        elif arch == 'scone':
            for r in range(12 + s * 2):
                w = 4 + math.floor(r * 1.1)
                fillRect32(cx - (w // 2), 10 + r - s, w, 1, 12 if r < 4 else 2)
        elif arch == 'pretzel':
            fillEllipse32(cx - 4, cy - 2, 5 + s, 5 + s, 9)
            fillEllipse32(cx + 4, cy - 2, 5 + s, 5 + s, 9)
            fillEllipse32(cx, cy + 3, 7 + s, 4, 13)
            fillEllipse32(cx - 4, cy - 2, 2, 2, 0)
            fillEllipse32(cx + 4, cy - 2, 2, 2, 0)
        elif arch == 'muffin':
            fillEllipse32(cx, cy - 2, 8 + s * 2, 5 + s, 9)
            fillRect32(cx - 6 - s, cy + 2, 12 + s * 2, 5 + s, 13)
        elif arch == 'taco_open':
            fillEllipse32(cx, cy + 2, 10 + s * 2, 5 + s, 12)
            fillRect32(cx - 8 - s, cy - 1, 16 + s * 2, 3, 10)
            fillRect32(cx - 7 - s, cy - 2, 14 + s * 2, 2, 11)
        elif arch == 'bao':
            fillEllipse32(cx, cy + 1, 8 + s * 2, 7 + s * 2, 2)
            fillEllipse32(cx, cy - 5 - s, 3 + s, 2 + s, 4)
        elif arch == 'gyoza':
            fillEllipse32(cx, cy + 2, 10 + s * 2, 5 + s, 2)
            fillRect32(cx - 9 - s, cy + 6 + s, 18 + s * 2, 2, 9)
            for x in range(cx - 6, cx + 7, 3): setPx32(x, cy - 3 - s, 4)
        elif arch == 'shumai':
            fillRect32(cx - 6 - s, cy - 3, 12 + s * 2, 10 + s, 9)
            fillEllipse32(cx, cy - 3, 6 + s, 3, 5)
            setPx32(cx, cy - 4, 11); setPx32(cx + 1, cy - 4, 11)
        elif arch == 'onigiri':
            for r in range(13 + s * 2):
                w = 3 + math.floor(r * 1.15)
                fillRect32(cx - (w // 2), 8 + r - s, w, 1, 8)
            fillRect32(cx - 4, 15, 8, 6 + s, 1)
        elif arch == 'ravioli':
            sz = 12 + s * 2
            fillRect32(cx - (sz // 2), cy - (sz // 2), sz, sz, 9)
            fillEllipse32(cx, cy, 4 + s, 4 + s, 2)
        elif arch == 'empanada':
            fillEllipse32(cx, cy + 1, 9 + s * 2, 6 + s, 9)
            fillRect32(cx - 8 - s, cy + 1, 16 + s * 2, 2, 3)
        elif arch == 'mochi':
            fillEllipse32(cx, cy + 2, 7 + s * 2, 6 + s, 2)
            fillEllipse32(cx - 2, cy, 3 + s, 2, 4)
        elif arch == 'khinkali':
            fillEllipse32(cx, cy + 3, 8 + s * 2, 6 + s, 2)
            for r in range(5 + s): fillRect32(cx - 2 - (r // 2), cy - 5 - s + r, 4 + r, 1, 4)
        elif arch == 'takoyaki':
            fillEllipse32(cx, cy, 7 + s * 2, 7 + s * 2, 9)
            fillEllipse32(cx, cy - 4 - s, 5 + s, 2, 13)
        elif arch == 'burek':
            fillEllipse32(cx, cy + 1, 9 + s * 2, 6 + s * 2, 9)
            fillEllipse32(cx, cy + 1, 5 + s, 3 + s, 3)
            fillEllipse32(cx, cy + 1, 2, 1, 4)
        elif arch == 'ramen':
            fillEllipse32(cx, cy + 3, 9 + s * 2, 5 + s, 14)
            fillRect32(cx - 8 - s, cy - 1, 16 + s * 2, 4, 14)
            fillEllipse32(cx, cy - 2, 8 + s, 3 + s, 9)
        elif arch == 'pho':
            fillEllipse32(cx, cy + 4, 7 + s * 2, 4 + s, 8)
            fillRect32(cx - 7 - s, cy - 2, 14 + s * 2, 6, 8)
            fillEllipse32(cx, cy - 3, 7 + s, 3, 5)
            for i in range(6): setPx32(cx + 3 + i, cy - 8 + i, 13)
        elif arch == 'pasta_nest':
            fillEllipse32(cx, cy + 1, 9 + s * 2, 6 + s, 9)
            fillEllipse32(cx, cy - 1, 5 + s, 3, 10)
        elif arch == 'wok_pan':
            fillEllipse32(cx, cy + 2, 10 + s * 2, 5 + s, 1)
            fillRect32(cx + 9 + s, cy, 5, 2, 13)
            fillEllipse32(cx, cy - 1, 8 + s, 3, 9)
        elif arch == 'lasagna':
            w = 14 + s * 3; h = 10 + s * 2
            fillRect32(cx - (w // 2), cy - (h // 2), w, h, 9)
            fillRect32(cx - (w // 2), cy - 2, w, 2, 10)
            fillRect32(cx - (w // 2), cy + 2, w, 2, 12)
        elif arch == 'noodle_drake':
            fillEllipse32(cx - 3, cy - 3, 5 + s, 4 + s, 9)
            fillEllipse32(cx + 3, cy + 2, 6 + s, 4 + s, 12)
            fillEllipse32(cx - 2, cy + 5, 5 + s, 3, 9)
        elif arch == 'mac_cup':
            fillRect32(cx - 6 - s, cy - 2, 12 + s * 2, 10 + s, 14)
            fillEllipse32(cx, cy - 3, 6 + s, 3 + s, 12)
        elif arch == 'soba_mat':
            fillRect32(cx - 10 - s, cy + 2, 20 + s * 2, 5, 13)
            fillEllipse32(cx, cy - 1, 7 + s, 4 + s, 3)
        elif arch == 'teacup':
            fillEllipse32(cx, cy + 2, 6 + s * 2, 5 + s, 8)
            fillRect32(cx - 6 - s, cy - 3, 12 + s * 2, 5, 8)
            fillEllipse32(cx, cy - 3, 5 + s, 2, 5)
            fillRect32(cx + 6 + s, cy - 1, 3, 4, 8)
        elif arch == 'cauldron':
            fillEllipse32(cx, cy + 2, 9 + s * 2, 7 + s, 13)
            fillRect32(cx - 7 - s, cy - 5, 14 + s * 2, 3, 14)
            fillEllipse32(cx, cy - 5, 6 + s, 2, 5)
        elif arch == 'bread_bowl':
            fillEllipse32(cx, cy + 2, 9 + s * 2, 6 + s, 9)
            fillEllipse32(cx, cy - 2, 6 + s, 3, 5)
        elif arch == 'tureen':
            fillEllipse32(cx, cy + 1, 8 + s * 2, 6 + s, 14)
            fillRect32(cx - 6 - s, cy - 5, 12 + s * 2, 3, 8)
            fillEllipse32(cx, cy - 6, 4 + s, 2, 12)
        elif arch == 'clay_pot':
            fillEllipse32(cx, cy + 2, 8 + s * 2, 6 + s, 10)
            fillEllipse32(cx, cy - 3, 6 + s, 2, 5)
        elif arch == 'chili_pot':
            fillRect32(cx - 7 - s, cy - 4, 14 + s * 2, 11 + s, 10)
            fillEllipse32(cx, cy - 4, 7 + s, 3, 5)
        elif arch == 'myth_bowl':
            fillEllipse32(cx, cy + 2, 10 + s * 2, 6 + s, 12)
            fillEllipse32(cx, cy - 3, 8 + s, 3, 5)
            fillRect32(cx - 4, cy + 7 + s, 8, 3, 12)

        top = sh["top"]
        if top == 'flag': fillRect32(cx, 3, 1, 6, 13); fillRect32(cx + 1, 3, 5, 3, 10)
        elif top == 'grill': fillRect32(cx - 5, 6, 10, 2, 1)
        elif top == 'skewer': fillRect32(cx, 2, 2, 7, 13); fillEllipse32(cx + 1, 3, 2, 2, 11)
        elif top == 'leaf': fillEllipse32(cx - 2, 6, 3, 2, 11); fillEllipse32(cx + 3, 5, 3, 2, 11)
        elif top == 'periscope': fillRect32(cx - 1, 3, 2, 6, 14); fillRect32(cx - 1, 3, 5, 2, 14)
        elif top == 'drip': fillRect32(cx - 5, 7, 10, 2, 15); setPx32(cx - 3, 9, 15); setPx32(cx + 2, 10, 15)
        elif top == 'crown': fillRect32(cx - 5, 5, 10, 3, 12); setPx32(cx - 4, 4, 12); setPx32(cx, 3, 10); setPx32(cx + 4, 4, 12)
        elif top == 'dill': fillRect32(cx - 3, 4, 2, 4, 11); fillRect32(cx + 2, 4, 2, 4, 11)
        elif top == 'horns': fillRect32(cx - 7, 4, 2, 4, 8); fillRect32(cx + 5, 4, 2, 4, 8)
        elif top == 'sugar': fillRect32(cx - 4, 6, 8, 2, 8)
        elif top == 'ears': fillEllipse32(cx - 5, 6, 2, 3, 2); fillEllipse32(cx + 5, 6, 2, 3, 2)
        elif top == 'chili': fillRect32(cx - 2, 4, 4, 4, 10); setPx32(cx, 3, 11)
        elif top == 'cream': fillEllipse32(cx, 6, 4, 3, 8); setPx32(cx, 3, 10)
        elif top == 'seeds': setPx32(cx - 3, 8, 8); setPx32(cx, 7, 8); setPx32(cx + 3, 8, 8)
        elif top == 'antennae': fillRect32(cx - 4, 3, 1, 5, 1); fillRect32(cx + 4, 3, 1, 5, 1)
        elif top == 'moon': fillEllipse32(cx, 5, 3, 3, 12); fillEllipse32(cx + 1, 5, 2, 2, 0)
        elif top == 'egg': fillEllipse32(cx, 6, 4, 3, 8); fillEllipse32(cx, 6, 2, 2, 12)
        elif top == 'knot': fillEllipse32(cx, 6, 3, 2, 4)
        elif top == 'steam': setPx32(cx - 4, 4, 8); setPx32(cx - 3, 2, 8); setPx32(cx + 4, 4, 8); setPx32(cx + 5, 2, 8)
        elif top == 'pleat':
            for x in range(cx - 5, cx + 6, 2): setPx32(x, 6, 8)
        elif top == 'flame': fillEllipse32(cx, 5, 3, 4, 10); fillEllipse32(cx, 6, 2, 2, 12)
        elif top == 'halo': fillEllipse32(cx, 4, 7, 2, 12); fillEllipse32(cx, 4, 5, 1, 0)

        limb = sh["limb"]
        if limb == 'stub': fillRect32(cx - 6, 25, 3, 3, 3); fillRect32(cx + 3, 25, 3, 3, 3)
        elif limb == 'paws': fillEllipse32(cx - 6, 26, 3, 2, 3); fillEllipse32(cx + 6, 26, 3, 2, 3)
        elif limb == 'heavy': fillRect32(cx - 8, 24, 5, 5, 13); fillRect32(cx + 3, 24, 5, 5, 13)
        elif limb == 'fins': fillEllipse32(cx - 9, 24, 4, 2, 5); fillEllipse32(cx + 9, 24, 4, 2, 5)
        elif limb == 'arms': fillRect32(cx - 12, 16, 3, 5, 2); fillRect32(cx + 9, 16, 3, 5, 2); fillRect32(cx - 6, 25, 3, 3, 3); fillRect32(cx + 3, 25, 3, 3, 3)
        elif limb == 'bounce': fillEllipse32(cx, 27, 6, 2, 3)
        elif limb == 'claws': fillRect32(cx - 13, 14, 4, 4, 10); fillRect32(cx + 9, 14, 4, 4, 10); fillRect32(cx - 6, 25, 3, 3, 3); fillRect32(cx + 3, 25, 3, 3, 3)

        side = sh["side"]
        if side == 'tail': fillEllipse32(cx + 11, 20, 3, 2, 5); fillEllipse32(cx + 13, 18, 2, 2, 12)
        elif side == 'cape': fillRect32(cx - 12, 13, 3, 11, 10); fillRect32(cx + 9, 13, 3, 11, 10)
        elif side == 'wings': fillEllipse32(cx - 12, 14, 3, 5, 4); fillEllipse32(cx + 12, 14, 3, 5, 4)
        elif side == 'shield': fillEllipse32(cx - 12, 18, 3, 5, 14)
        elif side == 'aura': setPx32(3, 12, 12); setPx32(28, 12, 12); setPx32(4, 22, 8); setPx32(27, 22, 8)
        elif side == 'fins': fillEllipse32(cx - 12, 17, 3, 3, 5); fillEllipse32(cx + 12, 17, 3, 3, 5)
        elif side == 'arms': fillRect32(cx - 12, 15, 3, 5, 6); fillRect32(cx + 9, 15, 3, 5, 6)
        elif side == 'claws': fillRect32(cx - 12, 12, 3, 3, 10); fillRect32(cx + 9, 12, 3, 3, 10)

        if pose == 'wide': fillRect32(cx - 10, cy + 2, 20, 2, 3)
        if pose == 'tall': fillRect32(cx - 3, cy - 8, 6, 3, 4)

        if not isBack:
            ey = cy
            fillRect32(cx - 4, ey - 1, 2, 3, 1); setPx32(cx - 4, ey - 1, 8)
            fillRect32(cx + 2, ey - 1, 2, 3, 1); setPx32(cx + 2, ey - 1, 8)
            setPx32(cx - 6, ey + 2, 15); setPx32(cx + 5, ey + 2, 15)
            setPx32(cx - 1, ey + 2, 1); setPx32(cx, ey + 3, 1); setPx32(cx + 1, ey + 2, 1)
        else:
            fillRect32(cx - 3, cy - 1, 6, 4, 6)
            fillRect32(cx - 2, cy, 4, 2, 3)

        outlineGrid32(1)
        return g

    def buildLearnset(sp_types, base_moves):
        seen = set(base_moves)
        pool = list(base_moves)
        for t in sp_types:
            for m_id in type_move_pools.get(t, []):
                if m_id not in seen:
                    seen.add(m_id)
                    pool.append(m_id)
        levels = [1, 1, 5, 9, 14, 20, 27, 35]
        return [[levels[i], pool[i]] for i in range(8)]

    beatsts_py = []
    for r in raw_beatsts:
        sp = {
            "id": r[0], "name": r[1], "family": r[2], "types": r[3],
            "stats": {"hp": r[4][0], "atk": r[4][1], "def": r[4][2], "spd": r[4][3]},
            "catchRate": r[5],
            "evo": {"to": r[6], "level": r[7]} if r[6] else None,
            "learnset": buildLearnset(r[3], r[8]),
            "dex": r[9],
            "nightOnly": r[10],
            "minTier": r[11],
            "shape": {"arch": r[12], "sizeMod": r[13], "limb": r[14], "top": r[15], "side": r[16], "pose": r[17], "eye": r[18]}
        }
        sp["palette"] = buildSpeciesPalette(sp)
        sp["front"] = drawBeatstSprite32(sp, False)
        sp["back"] = drawBeatstSprite32(sp, True)
        beatsts_py.append(sp)

    # Extract TILES_8X8 and buildCharSpriteGrid
    def makeTile8(fn):
        t = [0] * 64
        fn(t)
        return t
    
    def build_tiles_8x8():
        tiles = {}
        def f0(t):
            for i in range(64): t[i]=14
            t[9]=15; t[44]=15
        tiles[0] = makeTile8(f0)
        def f1(t):
            for i in range(64): t[i]=13
            for x in range(8): t[56+x]=11
            t[19]=15; t[20]=15
        tiles[1] = makeTile8(f1)
        def f2(t):
            for i in range(64): t[i]=11
            for y in range(1,8):
                for x in range(1,7): t[y*8+x]=5
            for y in range(2,7):
                for x in range(2,6): t[y*8+x]=11
            t[37]=13
        tiles[2] = makeTile8(f2)
        def f3(t):
            for i in range(64): t[i]=5
            for y in range(1,5):
                for x in range(1,7): t[y*8+x]=11
            t[18]=15; t[19]=15; t[20]=15; t[43]=11; t[51]=11
        tiles[3] = makeTile8(f3)
        def f4(t):
            for i in range(64): t[i]=14
            for y in range(2,6):
                for x in range(1,7): t[y*8+x]=9
        tiles[4] = makeTile8(f4)
        def f5(t):
            for i in range(64): t[i]=11
            for x in range(1,7): t[16+x]=13; t[40+x]=9
        tiles[5] = makeTile8(f5)
        def f6(t):
            for i in range(64): t[i]=14
            for y in range(1,7,2):
                for x in range(1,7): t[y*8+x]=13
            for x in range(2,6): t[8+x]=15
        tiles[6] = makeTile8(f6)
        def f7(t):
            for i in range(64): t[i]=1
            for y in range(1,7,2):
                for x in range(1,7): t[y*8+x]=14
            t[43]=13; t[44]=13
        tiles[7] = makeTile8(f7)
        def f8(t):
            for i in range(64): t[i]=10
            for x in range(8): t[x]=14; t[56+x]=14
            for y in range(2,6):
                for x in range(2,6): t[y*8+x]=8
            t[27]=15
        tiles[8] = makeTile8(f8)
        def f9(t):
            for i in range(64): t[i]=14
            for y in range(2,6):
                for x in range(2,6): t[y*8+x]=13
            t[27]=9; t[28]=9
        tiles[9] = makeTile8(f9)
        # 10..21
        tiles[10] = makeTile8(lambda t: (t.__setitem__(slice(None), [2]*64), t.__setitem__(9, 4), t.__setitem__(45, 4)))
        def f11(t):
            for i in range(64): t[i]=2
            for y in range(1,7,2):
                for x in range(1,7,2): t[y*8+x]=12; t[y*8+x+1]=4
        tiles[11] = makeTile8(f11)
        tiles[12] = makeTile8(lambda t: (t.__setitem__(slice(None), [5]*64), t.__setitem__(10, 6), t.__setitem__(28, 6), t.__setitem__(53, 6)))
        tiles[13] = makeTile8(lambda t: (t.__setitem__(slice(None), [7]*64), t.__setitem__(17, 8), t.__setitem__(42, 8)))
        def f14(t):
            for i in range(64): t[i]=3
            for y in range(1,6):
                for x in range(1,7): t[y*8+x]=12
            t[51]=11; t[59]=11
        tiles[14] = makeTile8(f14)
        def f15(t):
            for i in range(64): t[i]=10
            for x in range(8): t[x]=14; t[56+x]=14
        tiles[15] = makeTile8(f15)
        def f16(t):
            for i in range(64): t[i]=9
            for x in range(0,8,2): t[24+x]=1
        tiles[16] = makeTile8(f16)
        def f17(t):
            for i in range(64): t[i]=6
            for y in range(1,7):
                for x in range(1,7): t[y*8+x]=5
            t[27]=13
        tiles[17] = makeTile8(f17)
        def f18(t):
            for i in range(64): t[i]=11
            for x in range(0,8,2): t[x]=5
        tiles[18] = makeTile8(f18)
        tiles[19] = makeTile8(lambda t: (t.__setitem__(slice(None), [2]*64), t.__setitem__(18, 13), t.__setitem__(19, 13), t.__setitem__(26, 15)))
        def f20(t):
            for i in range(64): t[i]=14
            for y in range(0,8,2): t[y*8+3]=11
        tiles[20] = makeTile8(f20)
        def f21(t):
            for i in range(64): t[i]=11
            for y in range(1,6):
                for x in range(1,6): t[y*8+x]=6
        tiles[21] = makeTile8(f21)
        # 22..33
        tiles[22] = makeTile8(lambda t: (t.__setitem__(slice(None), [4]*64), t.__setitem__(11, 15), t.__setitem__(50, 15)))
        def f23(t):
            for i in range(64): t[i]=4
            for y in range(1,7,2):
                for x in range(1,7,2): t[y*8+x]=15; t[y*8+x+1]=12
        tiles[23] = makeTile8(f23)
        def f24(t):
            for i in range(64): t[i]=11
            for x in range(8): t[24+x]=6
        tiles[24] = makeTile8(f24)
        def f25(t):
            for i in range(64): t[i]=7
            for x in range(0,8,2): t[16+x]=15
        tiles[25] = makeTile8(f25)
        def f26(t):
            for i in range(64): t[i]=12
            for y in range(8): t[y*8+2]=4; t[y*8+5]=4
        tiles[26] = makeTile8(f26)
        def f27(t):
            for i in range(64): t[i]=15
            for x in range(8): t[56+x]=14
        tiles[27] = makeTile8(f27)
        def f28(t):
            for i in range(64): t[i]=7
            for x in range(0,8,2): t[8+x]=15
        tiles[28] = makeTile8(f28)
        def f29(t):
            for i in range(64): t[i]=6
            for y in range(1,7,2):
                for x in range(1,7,2): t[y*8+x]=13
        tiles[29] = makeTile8(f29)
        tiles[30] = makeTile8(lambda t: (t.__setitem__(slice(None), [5]*64), t.__setitem__(19, 10), t.__setitem__(20, 10), t.__setitem__(27, 13)))
        tiles[31] = makeTile8(lambda t: (t.__setitem__(slice(None), [14]*64), t.__setitem__(18, 8), t.__setitem__(45, 8)))
        def f32(t):
            for i in range(64): t[i]=6
            for x in range(8): t[32+x]=13
        tiles[32] = makeTile8(f32)
        def f33(t):
            for i in range(64): t[i]=11
            for y in range(0,8,2):
                for x in range(0,8,2): t[y*8+x]=13
        tiles[33] = makeTile8(f33)
        # 34..45
        tiles[34] = makeTile8(lambda t: (t.__setitem__(slice(None), [5]*64), t.__setitem__(12, 13), t.__setitem__(41, 13)))
        def f35(t):
            for i in range(64): t[i]=5
            for y in range(1,7,2):
                for x in range(1,7,2): t[y*8+x]=13; t[y*8+x+1]=9
        tiles[35] = makeTile8(f35)
        tiles[36] = makeTile8(lambda t: (t.__setitem__(slice(None), [14]*64), t.__setitem__(18, 13), t.__setitem__(44, 13)))
        tiles[37] = makeTile8(lambda t: (t.__setitem__(slice(None), [9]*64), t.__setitem__(20, 13), t.__setitem__(42, 13)))
        def f38(t):
            for i in range(64): t[i]=11
            for y in range(1,6):
                for x in range(1,7): t[y*8+x]=9
        tiles[38] = makeTile8(f38)
        def f39(t):
            for i in range(64): t[i]=13
            for x in range(8): t[56+x]=11
        tiles[39] = makeTile8(f39)
        def f40(t):
            for i in range(64): t[i]=1
            for x in range(0,8,2): t[16+x]=13
        tiles[40] = makeTile8(f40)
        def f41(t):
            for i in range(64): t[i]=6
            for x in range(1,7): t[24+x]=15
        tiles[41] = makeTile8(f41)
        tiles[42] = makeTile8(lambda t: (t.__setitem__(slice(None), [5]*64), t.__setitem__(18, 9), t.__setitem__(27, 13)))
        def f43(t):
            for i in range(64): t[i]=14
            for y in range(1,7): t[y*8+4]=11
        tiles[43] = makeTile8(f43)
        def f44(t):
            for i in range(64): t[i]=1
            for y in range(0,8,3):
                for x in range(0,8,3): t[y*8+x]=9
        tiles[44] = makeTile8(f44)
        def f45(t):
            for i in range(64): t[i]=9
            for y in range(1,7,2): t[y*8+3]=13
        tiles[45] = makeTile8(f45)
        # 46..57
        tiles[46] = makeTile8(lambda t: (t.__setitem__(slice(None), [3]*64), t.__setitem__(11, 7), t.__setitem__(44, 7)))
        def f47(t):
            for i in range(64): t[i]=3
            for y in range(1,7,2):
                for x in range(1,7,2): t[y*8+x]=7; t[y*8+x+1]=12
        tiles[47] = makeTile8(f47)
        tiles[48] = makeTile8(lambda t: (t.__setitem__(slice(None), [14]*64), t.__setitem__(10, 7), t.__setitem__(53, 7)))
        tiles[49] = makeTile8(lambda t: (t.__setitem__(slice(None), [7]*64), t.__setitem__(18, 12), t.__setitem__(44, 12)))
        def f50(t):
            for i in range(64): t[i]=1
            for y in range(1,6):
                for x in range(1,7): t[y*8+x]=7
        tiles[50] = makeTile8(f50)
        def f51(t):
            for i in range(64): t[i]=14
            for x in range(8): t[56+x]=7
        tiles[51] = makeTile8(f51)
        def f52(t):
            for i in range(64): t[i]=7
            for x in range(0,8,2): t[24+x]=13
        tiles[52] = makeTile8(f52)
        def f53(t):
            for i in range(64): t[i]=1
            for y in range(2,6):
                for x in range(2,6): t[y*8+x]=12
        tiles[53] = makeTile8(f53)
        tiles[54] = makeTile8(lambda t: (t.__setitem__(slice(None), [3]*64), t.__setitem__(19, 15), t.__setitem__(28, 15)))
        def f55(t):
            for i in range(64): t[i]=13
            for x in range(1,7): t[32+x]=11
        tiles[55] = makeTile8(f55)
        tiles[56] = makeTile8(lambda t: (t.__setitem__(slice(None), [1]*64), t.__setitem__(19, 7), t.__setitem__(44, 7)))
        def f57(t):
            for i in range(64): t[i]=11
            for y in range(1,6):
                for x in range(1,6): t[y*8+x]=1
        tiles[57] = makeTile8(f57)
        # 58..73
        def f58(t):
            for i in range(64): t[i]=15
            for x in range(0,8,2): t[x]=13
        tiles[58] = makeTile8(f58)
        def f59(t):
            for i in range(64): t[i]=13
            for y in range(1,7):
                for x in range(1,7): t[y*8+x]=9
        tiles[59] = makeTile8(f59)
        def f60(t):
            for i in range(64): t[i]=1
            for x in range(0,8,2): t[24+x]=13
        tiles[60] = makeTile8(f60)
        tiles[61] = makeTile8(lambda t: (t.__setitem__(slice(None), [8]*64), t.__setitem__(19, 15), t.__setitem__(44, 15)))
        def f62(t):
            for i in range(64): t[i]=8
            for y in range(1,7,2):
                for x in range(1,7,2): t[y*8+x]=13; t[y*8+x+1]=15
        tiles[62] = makeTile8(f62)
        def f63(t):
            for i in range(64): t[i]=13
            for y in range(1,6):
                for x in range(1,7): t[y*8+x]=15
        tiles[63] = makeTile8(f63)
        def f64(t):
            for i in range(64): t[i]=11
            for x in range(8): t[x]=9; t[8+x]=(15 if x%2 else 9); t[16+x]=13
        tiles[64] = makeTile8(f64)
        def f65(t):
            for i in range(64): t[i]=2
            for x in range(8): t[48+x]=11; t[56+x]=6
        tiles[65] = makeTile8(f65)
        tiles[66] = makeTile8(lambda t: (t.__setitem__(slice(None), [8]*64), t.__setitem__(9, 15), t.__setitem__(18, 15), t.__setitem__(36, 15), t.__setitem__(45, 15)))
        tiles[67] = makeTile8(lambda t: (t.__setitem__(slice(None), [14]*64), t.__setitem__(26, 13), t.__setitem__(27, 13), t.__setitem__(36, 13), t.__setitem__(19, 13)))
        tiles[68] = makeTile8(lambda t: (t.__setitem__(slice(None), [14]*64), t.__setitem__(29, 13), t.__setitem__(28, 13), t.__setitem__(19, 13), t.__setitem__(35, 13)))
        tiles[69] = makeTile8(lambda t: (t.__setitem__(slice(None), [14]*64), t.__setitem__(19, 13), t.__setitem__(27, 13), t.__setitem__(28, 13), t.__setitem__(34, 13)))
        tiles[70] = makeTile8(lambda t: (t.__setitem__(slice(None), [14]*64), t.__setitem__(43, 13), t.__setitem__(35, 13), t.__setitem__(36, 13), t.__setitem__(26, 13)))
        def f71(t):
            for i in range(64): t[i]=14
            for x in range(0,8,4): t[x]=15
            t[36]=8
        tiles[71] = makeTile8(f71)
        def f72(t):
            for i in range(64): t[i]=1
            for x in range(8): t[24+x]=14
            t[27]=9
        tiles[72] = makeTile8(f72)
        def f73(t):
            for i in range(64): t[i]=1
            for y in range(0,8,2):
                for x in range(8): t[y*8+x]=9
        tiles[73] = makeTile8(f73)
        return tiles
    
    def buildCharSpriteGrid(spriteKey, dir='down', walkFrame=0):
        pal = char_sprites.get(spriteKey, char_sprites['villager_0'])
        grid = [None] * (16 * 24)
        def px(x, y, c):
            if 0 <= x < 16 and 0 <= y < 24:
                grid[y * 16 + x] = c
        def rect(x0, y0, w, h, c):
            for y in range(y0, y0 + h):
                for x in range(x0, x0 + w):
                    px(x, y, c)
    
        hs = pal["hatStyle"]
        if hs == 'chest':
            rect(2, 9, 12, 11, '#181820')
            rect(3, 10, 10, 4, '#F0C040')
            rect(3, 14, 10, 5, '#885030')
            rect(7, 13, 2, 3, '#F8F8F0')
            return grid
        if hs == 'block':
            rect(1, 8, 14, 14, '#181820')
            rect(2, 9, 12, 12, '#D8B880')
            rect(4, 11, 8, 8, '#885030')
            return grid
    
        hy = 3 + (-1 if walkFrame == 1 else 0)
        rect(4, hy, 8, 5, '#181820')
        rect(5, hy + 1, 6, 4, pal["hat"])
        if hs in ('tall_toque', 'tophat', 'crown_toque'):
            rect(4, hy - 3, 8, 4, '#181820')
            rect(5, hy - 2, 6, 3, pal["hat"])
            if hs == 'crown_toque':
                px(5, hy - 3, '#F0C040'); px(8, hy - 3, '#F0C040'); px(10, hy - 3, '#F0C040')
        elif hs == 'crown':
            rect(4, hy - 2, 8, 2, '#F0C040')
            px(4, hy - 3, '#F0C040'); px(7, hy - 3, '#F0C040'); px(11, hy - 3, '#F0C040')
        elif hs == 'spiky':
            px(4, hy - 1, pal["hat"]); px(7, hy - 2, pal["hat"]); px(11, hy - 1, pal["hat"])
        elif hs == 'twin_buns':
            rect(2, hy, 2, 3, pal["hat"]); rect(12, hy, 2, 3, pal["hat"])
        elif hs in ('straw', 'fedora'):
            rect(2, hy + 3, 12, 2, pal["hat"])
        elif hs in ('visor', 'cap'):
            if dir == 'left': rect(2, hy + 3, 4, 2, pal["hat"])
            elif dir == 'right': rect(10, hy + 3, 4, 2, pal["hat"])
            else: rect(4, hy + 3, 8, 1, pal["hat"])
        elif hs == 'beret':
            rect(3, hy, 9, 3, pal["hat"])
        elif hs == 'hood':
            rect(3, hy + 1, 10, 7, pal["hat"])
        elif hs == 'pompadour':
            rect(4, hy - 2, 7, 3, pal["hat"]); rect(9, hy - 3, 3, 2, pal["hat"])
        elif hs == 'hairpins':
            px(3, hy + 1, '#F0C040'); px(12, hy + 1, '#F0C040'); px(2, hy + 2, '#F0C040'); px(13, hy + 2, '#F0C040')
        elif hs == 'bun_hat':
            rect(5, hy - 2, 6, 3, pal["hat"]); px(7, hy - 3, '#F8F8F0')
        elif hs == 'bandana':
            rect(3, hy + 2, 10, 2, pal["hat"]); px(13, hy + 3, pal["hat"])
        elif hs == 'headband':
            rect(4, hy + 2, 8, 2, '#F8F8F0'); px(12, hy + 1, '#F8F8F0')
        elif hs == 'bowler':
            rect(5, hy - 1, 6, 2, pal["hat"]); rect(3, hy + 3, 10, 1, pal["hat"])
        elif hs == 'kerchief':
            rect(4, hy + 1, 8, 3, pal["hat"]); px(3, hy + 4, pal["hat"]); px(12, hy + 4, pal["hat"])
    
        rect(4, hy + 4, 8, 6, '#181820')
        rect(5, hy + 5, 6, 4, pal["hair"])
        acc = pal["acc"]
        if dir == 'down':
            if acc == 'shades': rect(5, hy + 6, 6, 2, '#181820')
            else:
                px(6, hy + 6, '#181820'); px(9, hy + 6, '#181820')
                if acc == 'monocle': rect(8, hy + 5, 3, 3, '#F0C040')
            if acc == 'stache': rect(6, hy + 8, 4, 1, '#F8F8F0')
        elif dir == 'left':
            px(5, hy + 6, '#181820')
        elif dir == 'right':
            px(10, hy + 6, '#181820')
        else:
            rect(5, hy + 5, 6, 4, pal["hat"])
    
        ty = hy + 9
        rect(3, ty, 10, 7, '#181820')
        rect(4, ty + 1, 8, 5, pal["shirt"])
        if acc == 'apron': rect(5, ty + 2, 6, 4, '#F8F8F0')
        elif acc == 'scarf': rect(4, ty + 1, 8, 2, '#F0C040')
        elif acc == 'tie': rect(7, ty + 1, 2, 4, '#E63946')
        elif acc == 'sash': px(5, ty + 1, '#F0C040'); px(6, ty + 2, '#F0C040'); px(7, ty + 3, '#F0C040')
        elif acc == 'cloak': rect(2, ty + 1, 2, 7, pal["hat"]); rect(12, ty + 1, 2, 7, pal["hat"])
        elif acc == 'vest': rect(4, ty + 1, 2, 5, pal["hat"]); rect(10, ty + 1, 2, 5, pal["hat"])
        elif acc == 'collar': px(5, ty + 1, '#F8F8F0'); px(10, ty + 1, '#F8F8F0')
        elif acc == 'jacket': rect(6, ty + 1, 4, 5, '#F8F8F0')
        elif acc == 'robe': rect(4, ty + 4, 8, 3, pal["shirt"])
        elif acc == 'ribbon': rect(6, ty + 2, 4, 2, '#FF70A6')
    
        armOff = -1 if walkFrame == 1 else (1 if walkFrame == 2 else 0)
        rect(2, ty + 1 + armOff, 2, 4, pal["shirt"])
        rect(12, ty + 1 - armOff, 2, 4, pal["shirt"])
    
        ly = ty + 6
        if walkFrame == 0:
            rect(4, ly, 3, 4, pal["pants"])
            rect(9, ly, 3, 4, pal["pants"])
        elif walkFrame == 1:
            rect(4, ly - 1, 3, 4, pal["pants"])
            rect(9, ly + 1, 3, 4, pal["pants"])
        else:
            rect(4, ly + 1, 3, 4, pal["pants"])
            rect(9, ly - 1, 3, 4, pal["pants"])
        return grid
    
    tiles_py = build_tiles_8x8()
    char_grids_py = {}
    for k in char_sprites:
        char_grids_py[k] = {}
        for d in ('down', 'up', 'left', 'right'):
            char_grids_py[k][d] = [buildCharSpriteGrid(k, d, f) for f in range(3)]
    


    return {
        "font_sans_bytes": font_sans_bytes,
        "font_serif_bytes": font_serif_bytes,
        "types": types,
        "type_colors": type_colors,
        "type_chart": type_chart,
        "flavor_combos": flavor_combos,
        "moves": moves,
        "beatsts_py": beatsts_py,
        "tiles_py": tiles_py,
        "tile_roles": tile_roles,
        "solid_tiles": solid_tiles,
        "char_sprites": char_sprites,
        "char_grids_py": char_grids_py,
        "items": items,
        "regional_shops": regional_shops,
        "regions": regions,
        "maps": maps,
        "trainers": trainers,
        "quests": quests,
        "secrets": secrets,
        "music_tracks": music_tracks,
        "sfx_defs": sfx_defs,
    }


import struct, subprocess, json, random

class ArmAsm:
    def __init__(self, base=0x08000000):
        self.base = base
        self.code = bytearray()
        self.labels = {}
        self.fixups = []
        self.literals = [] # (val32, label_name)
        self.lit_counter = 0

    def pc_addr(self):
        return self.base + len(self.code)

    def align(self, n=4):
        while len(self.code) % n != 0:
            self.code.append(0)

    def label(self, name):
        self.labels[name] = self.base + len(self.code)

    def emit32(self, w):
        self.code.extend(struct.pack("<I", w & 0xFFFFFFFF))

    def emit16(self, h):
        self.code.extend(struct.pack("<H", h & 0xFFFF))

    def emit8(self, b):
        self.code.append(b & 0xFF)

    def emit_bytes(self, b):
        self.code.extend(b)

    def _try_enc_imm(self, val):
        val &= 0xFFFFFFFF
        for rot in range(16):
            shift = rot * 2
            imm8 = ((val << shift) | (val >> (32 - shift))) & 0xFFFFFFFF if shift else val
            if imm8 <= 0xFF:
                return (rot << 8) | imm8
        return None

    def _enc_imm(self, val):
        res = self._try_enc_imm(val)
        if res is None:
            raise ValueError(f"Cannot encode ARM immediate {hex(val)}")
        return res

    def dp_imm(self, op, s, rn, rd, val, cond=0xE):
        return (cond << 28) | (1 << 25) | (op << 21) | (s << 20) | (rn << 16) | (rd << 12) | self._enc_imm(val)

    def dp_reg(self, op, s, rn, rd, rm, shift_imm=0, shift_type=0, cond=0xE):
        return (cond << 28) | (0 << 25) | (op << 21) | (s << 20) | (rn << 16) | (rd << 12) | ((shift_imm & 31) << 7) | ((shift_type & 3) << 5) | rm

    def dp_reg_rs(self, op, s, rn, rd, rm, rs, shift_type=0, cond=0xE):
        return (cond << 28) | (0 << 25) | (op << 21) | (s << 20) | (rn << 16) | (rd << 12) | (rs << 8) | ((shift_type & 3) << 5) | (1 << 4) | rm

    def mov_imm(self, rd, val, s=0, cond=0xE):
        val &= 0xFFFFFFFF
        if self._try_enc_imm(val) is not None:
            self.emit32(self.dp_imm(0xD, s, 0, rd, val, cond))
        elif self._try_enc_imm((~val) & 0xFFFFFFFF) is not None:
            self.emit32(self.dp_imm(0xF, s, 0, rd, (~val) & 0xFFFFFFFF, cond))
        else:
            # Decompose into 8-bit byte chunks using MOV + ORR (zero literal pool data words in code section!)
            first = True
            for shift in (0, 8, 16, 24):
                chunk = val & (0xFF << shift)
                if chunk:
                    if first:
                        self.emit32(self.dp_imm(0xD, s, 0, rd, chunk, cond))
                        first = False
                    else:
                        self.emit32(self.dp_imm(0xC, s, rd, rd, chunk, cond))

    def mvn_imm(self, rd, val, s=0, cond=0xE): self.emit32(self.dp_imm(0xF, s, 0, rd, val, cond))
    def add_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x4, s, rn, rd, val, cond))
    def adc_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x5, s, rn, rd, val, cond))
    def sub_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x2, s, rn, rd, val, cond))
    def sbc_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x6, s, rn, rd, val, cond))
    def rsb_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x3, s, rn, rd, val, cond))
    def and_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x0, s, rn, rd, val, cond))
    def orr_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0xC, s, rn, rd, val, cond))
    def eor_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x1, s, rn, rd, val, cond))
    def bic_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0xE, s, rn, rd, val, cond))
    def cmp_imm(self, rn, val, cond=0xE): self.emit32(self.dp_imm(0xA, 1, rn, 0, val, cond))
    def cmn_imm(self, rn, val, cond=0xE): self.emit32(self.dp_imm(0xB, 1, rn, 0, val, cond))
    def tst_imm(self, rn, val, cond=0xE): self.emit32(self.dp_imm(0x8, 1, rn, 0, val, cond))

    def mov_reg(self, rd, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0xD, s, 0, rd, rm, shift_imm, shift_type, cond))
    def mvn_reg(self, rd, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0xF, s, 0, rd, rm, shift_imm, shift_type, cond))
    def mov_reg_rs(self, rd, rm, rs, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg_rs(0xD, s, 0, rd, rm, rs, shift_type, cond))
    def add_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0x4, s, rn, rd, rm, shift_imm, shift_type, cond))
    def adc_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0x5, s, rn, rd, rm, shift_imm, shift_type, cond))
    def sub_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0x2, s, rn, rd, rm, shift_imm, shift_type, cond))
    def sbc_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0x6, s, rn, rd, rm, shift_imm, shift_type, cond))
    def rsb_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0x3, s, rn, rd, rm, shift_imm, shift_type, cond))
    def and_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0x0, s, rn, rd, rm, shift_imm, shift_type, cond))
    def orr_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0xC, s, rn, rd, rm, shift_imm, shift_type, cond))
    def orr_reg_rs(self, rd, rn, rm, rs, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg_rs(0xC, s, rn, rd, rm, rs, shift_type, cond))
    def eor_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0x1, s, rn, rd, rm, shift_imm, shift_type, cond))
    def bic_reg(self, rd, rn, rm, shift_imm=0, shift_type=0, s=0, cond=0xE): self.emit32(self.dp_reg(0xE, s, rn, rd, rm, shift_imm, shift_type, cond))
    def cmp_reg(self, rn, rm, shift_imm=0, shift_type=0, cond=0xE): self.emit32(self.dp_reg(0xA, 1, rn, 0, rm, shift_imm, shift_type, cond))
    def tst_reg(self, rn, rm, shift_imm=0, shift_type=0, cond=0xE): self.emit32(self.dp_reg(0x8, 1, rn, 0, rm, shift_imm, shift_type, cond))

    def mul(self, rd, rm, rs, s=0, cond=0xE):
        self.emit32((cond << 28) | (s << 20) | (rd << 16) | (rs << 8) | 0x90 | rm)

    def umull(self, rdlo, rdhi, rm, rs, s=0, cond=0xE):
        self.emit32((cond << 28) | (0b0000100 << 21) | (s << 20) | (rdhi << 16) | (rdlo << 12) | (rs << 8) | 0x90 | rm)

    def umlal(self, rdlo, rdhi, rm, rs, s=0, cond=0xE):
        self.emit32((cond << 28) | (0b0000101 << 21) | (s << 20) | (rdhi << 16) | (rdlo << 12) | (rs << 8) | 0x90 | rm)

    def ldr_imm(self, rd, rn, offset=0, b=0, p=1, w=0, cond=0xE):
        u = 1 if offset >= 0 else 0
        self.emit32((cond << 28) | (1 << 26) | (p << 24) | (u << 23) | (b << 22) | (w << 21) | (1 << 20) | (rn << 16) | (rd << 12) | (abs(offset) & 0xFFF))

    def str_imm(self, rd, rn, offset=0, b=0, p=1, w=0, cond=0xE):
        u = 1 if offset >= 0 else 0
        self.emit32((cond << 28) | (1 << 26) | (p << 24) | (u << 23) | (b << 22) | (w << 21) | (0 << 20) | (rn << 16) | (rd << 12) | (abs(offset) & 0xFFF))

    def ldrb_imm(self, rd, rn, offset=0, p=1, w=0, cond=0xE): self.ldr_imm(rd, rn, offset, b=1, p=p, w=w, cond=cond)
    def strb_imm(self, rd, rn, offset=0, p=1, w=0, cond=0xE): self.str_imm(rd, rn, offset, b=1, p=p, w=w, cond=cond)

    def ldrh_imm(self, rd, rn, offset=0, p=1, w=0, cond=0xE):
        u = 1 if offset >= 0 else 0
        off = abs(offset) & 0xFF
        self.emit32((cond << 28) | (p << 24) | (u << 23) | (1 << 22) | (w << 21) | (1 << 20) | (rn << 16) | (rd << 12) | ((off >> 4) << 8) | 0xB0 | (off & 0xF))

    def strh_imm(self, rd, rn, offset=0, p=1, w=0, cond=0xE):
        u = 1 if offset >= 0 else 0
        off = abs(offset) & 0xFF
        self.emit32((cond << 28) | (p << 24) | (u << 23) | (1 << 22) | (w << 21) | (0 << 20) | (rn << 16) | (rd << 12) | ((off >> 4) << 8) | 0xB0 | (off & 0xF))

    def ldrsb_imm(self, rd, rn, offset=0, p=1, w=0, cond=0xE):
        u = 1 if offset >= 0 else 0
        off = abs(offset) & 0xFF
        self.emit32((cond << 28) | (p << 24) | (u << 23) | (1 << 22) | (w << 21) | (1 << 20) | (rn << 16) | (rd << 12) | ((off >> 4) << 8) | 0xD0 | (off & 0xF))

    def push(self, regs, cond=0xE):
        mask = sum(1 << r for r in regs) if isinstance(regs, (list, tuple, set)) else regs
        self.emit32((cond << 28) | (0b10010010 << 20) | (13 << 16) | (mask & 0xFFFF))

    def pop(self, regs, cond=0xE):
        mask = sum(1 << r for r in regs) if isinstance(regs, (list, tuple, set)) else regs
        self.emit32((cond << 28) | (0b10001011 << 20) | (13 << 16) | (mask & 0xFFFF))

    def bx(self, rm=14, cond=0xE):
        self.emit32((cond << 28) | 0x012FFF10 | rm)

    def swi(self, num, cond=0xE):
        self.emit32((cond << 28) | (0xF << 24) | ((num & 0xFF) << 16))

    def b(self, label, cond=0xE, link=0):
        off = len(self.code)
        self.fixups.append((off, 'B', label, (cond, link)))
        self.emit32(0)

    def bl(self, label, cond=0xE):
        self.b(label, cond=cond, link=1)

    def adr(self, rd, label, cond=0xE):
        off = len(self.code)
        self.fixups.append((off, 'ADR', label, (cond, rd)))
        self.emit32(0)

    def ldr_lit(self, rd, label, cond=0xE):
        off = len(self.code)
        self.fixups.append((off, 'LDR_LIT', label, (cond, rd)))
        self.emit32(0)

    def flush_literals(self):
        self.align(4)
        for val, lbl in self.literals:
            self.label(lbl)
            self.emit32(val)
        self.literals.clear()

    def resolve(self):
        self.flush_literals()
        for off, kind, label, extra in self.fixups:
            target = self.labels[label]
            pc = self.base + off + 8
            diff = target - pc
            if kind == 'B':
                cond, link = extra
                imm24 = (diff >> 2) & 0xFFFFFF
                w = (cond << 28) | (0x5 << 25) | (link << 24) | imm24
                struct.pack_into("<I", self.code, off, w)
            elif kind == 'ADR':
                cond, rd = extra
                w = self.dp_imm(0x4, 0, 15, rd, diff, cond) if diff >= 0 else self.dp_imm(0x2, 0, 15, rd, -diff, cond)
                struct.pack_into("<I", self.code, off, w)
            elif kind == 'LDR_LIT':
                cond, rd = extra
                u = 1 if diff >= 0 else 0
                imm12 = abs(diff)
                if imm12 > 0xFFF:
                    raise ValueError(f"Literal {label} out of 4KB range ({imm12} bytes)")
                w = (cond << 28) | (0b01011001 << 20) | (u << 23) | (15 << 16) | (rd << 12) | imm12
                struct.pack_into("<I", self.code, off, w)


def emit_softfloat(a: ArmAsm):
    # udiv32(R0=num, R1=den) -> R0=quot, R1=rem
    a.label("udiv32")
    a.push([2, 3, 14])
    a.mov_reg(2, 0)         # R2 = num
    a.mov_imm(0, 0)         # R0 = quot = 0
    a.mov_imm(3, 0)         # R3 = rem = 0
    a.cmp_imm(1, 0)
    a.b("udiv32_done", cond=0x0) # if den == 0 return 0
    a.mov_imm(14, 32)       # R14 = 32 bits
    a.label("udiv32_loop")
    a.add_reg(2, 2, 2, s=1) # LSLS R2, R2, #1 (shifts MSB into Carry)
    a.adc_reg(3, 3, 3)      # R3 = (R3 << 1) | Carry
    a.cmp_reg(3, 1)
    a.sub_reg(3, 3, 1, cond=0x2) # SUBCS R3, R3, R1
    a.adc_reg(0, 0, 0)      # R0 = (R0 << 1) | Carry
    a.sub_imm(14, 14, 1, s=1)
    a.b("udiv32_loop", cond=0x1)
    a.label("udiv32_done")
    a.mov_reg(1, 3)
    a.pop([2, 3, 15])

    # mulberry32_next(R0=state_ptr) -> R0=u32_draw
    a.label("mulberry32_next")
    a.push([4, 14])
    a.ldr_imm(1, 0, 0)
    a.mov_imm(2, 0x6D2B79F5)
    a.add_reg(1, 1, 2)
    a.str_imm(1, 0, 0)
    a.eor_reg(2, 1, 1, shift_imm=15, shift_type=1) # LSR #15
    a.orr_imm(3, 1, 1)
    a.mul(1, 2, 3)
    a.eor_reg(2, 1, 1, shift_imm=7, shift_type=1)  # LSR #7
    a.orr_imm(3, 1, 61)
    a.mul(4, 2, 3)
    a.add_reg(4, 1, 4)
    a.eor_reg(1, 1, 4)
    a.eor_reg(0, 1, 1, shift_imm=14, shift_type=1) # LSR #14
    a.pop([4, 15])

    # f64_from_u32(R0=val) -> R0=lo, R1=hi
    a.label("f64_from_u32")
    a.push([4, 14])
    a.cmp_imm(0, 0)
    a.mov_imm(1, 0, cond=0x0)
    a.b("f64_from_u32_done", cond=0x0)
    a.mov_reg(2, 0)         # R2 = val
    a.mov_imm(3, 1023 + 31) # R3 = biased exp if bit 31 is set
    a.label("f64_u32_norm")
    a.tst_imm(2, 0x80000000)
    a.b("f64_u32_norm_done", cond=0x1) # BNE
    a.mov_reg(2, 2, shift_imm=1, shift_type=0) # LSL #1
    a.sub_imm(3, 3, 1)
    a.b("f64_u32_norm")
    a.label("f64_u32_norm_done")
    # Now bit 31 of R2 is the implicit 1 bit!
    # Clear bit 31, and place bits 30..0 at mantissa bits 51..21:
    # In hi word (bits 63..32), mantissa bits 51..32 are bits 19..0, which is (R2 << 1) >> 12 = (R2 & 0x7FFFFFFF) >> 11
    # In lo word (bits 31..0), mantissa bits 31..21 are bits 31..21, which is R2 << 21
    a.bic_imm(4, 2, 0x80000000)
    a.mov_reg(0, 4, shift_imm=21, shift_type=0) # lo = (R2 & 0x7FFFFFFF) << 21
    a.mov_reg(1, 4, shift_imm=11, shift_type=1) # hi = (R2 & 0x7FFFFFFF) >> 11
    a.orr_reg(1, 1, 3, shift_imm=20, shift_type=0) # hi |= exp << 20
    a.label("f64_from_u32_done")
    a.pop([4, 15])

    # f64_from_mulberry(R0=u32_draw) -> R0=lo, R1=hi (val = u32_draw * 2^-32)
    a.label("f64_from_mulberry")
    a.push([14])
    a.bl("f64_from_u32")
    a.cmp_imm(1, 0)
    a.sub_imm(1, 1, 32 << 20, cond=0x1) # subtract 32 from biased exponent
    a.pop([15])

    # f64_to_u32_floor(R0=lo, R1=hi) -> R0=u32
    a.label("f64_to_u32_floor")
    a.push([4, 5, 14])
    a.tst_imm(1, 0x80000000) # negative?
    a.mov_imm(0, 0, cond=0x1)
    a.b("f64_floor_done", cond=0x1)
    a.mov_reg(2, 1, shift_imm=20, shift_type=1) # R2 = biased exp
    a.mov_imm(3, 1023)
    a.sub_reg(2, 2, 3, s=1) # R2 = exp = biased_exp - 1023
    a.mov_imm(0, 0, cond=0x4) # BMI (< 0) -> return 0
    a.b("f64_floor_done", cond=0x4)
    # Extract mantissa hi (bits 19..0 of R1) | (1 << 20)
    a.mov_imm(3, 0xFF000000)
    a.orr_imm(3, 3, 0x00F00000) # R3 = 0xFFF00000
    a.bic_reg(1, 1, 3)
    a.orr_imm(1, 1, 1 << 20)    # R1 = mant_hi (21 bits, bit 20 is 1<<52)
    a.cmp_imm(2, 20)
    a.b("f64_floor_gt20", cond=0x8) # BHI (exp > 20)
    # exp <= 20: result is R1 >> (20 - exp)
    a.rsb_imm(2, 2, 20)
    a.mov_reg_rs(0, 1, 2, shift_type=1) # LSR R2
    a.b("f64_floor_done")
    a.label("f64_floor_gt20")
    # 20 < exp <= 31: result is (R1 << (exp - 20)) | (R0 >> (52 - exp))
    a.sub_imm(3, 2, 20)         # R3 = exp - 20
    a.rsb_imm(4, 2, 52)         # R4 = 52 - exp
    a.mov_reg_rs(1, 1, 3, shift_type=0) # R1 <<= (exp - 20)
    a.mov_reg_rs(0, 0, 4, shift_type=1) # R0 >>= (52 - exp)
    a.orr_reg(0, 1, 0)
    a.label("f64_floor_done")
    a.pop([4, 5, 15])

    # Helper: f64_pack(R0=mant_lo, R1=mant_hi, R2=exp_biased, R3=round_bit, R4=sticky_bit) -> R0=lo, R1=hi
    # Assumes mant is normalized in [1<<52, (1<<53)-1], i.e., R1 is in [1<<20, (1<<21)-1]
    a.label("f64_round_and_pack")
    a.cmp_imm(3, 0)
    a.b("f64_pack_no_inc", cond=0x0) # round_bit == 0
    # round_bit == 1: check sticky_bit != 0 || (mant_lo & 1) != 0
    a.and_imm(5, 0, 1)
    a.orr_reg(5, 5, 4, s=1)
    a.b("f64_pack_no_inc", cond=0x0)
    # increment 53-bit mantissa (R1:R0)
    a.add_imm(0, 0, 1, s=1)
    a.adc_imm(1, 1, 0)
    a.tst_imm(1, 1 << 21) # overflowed to 1<<53?
    a.b("f64_pack_no_inc", cond=0x0)
    # shift right by 1 and increment exp_biased
    a.mov_reg(0, 0, shift_imm=1, shift_type=1)
    a.orr_reg(0, 0, 1, shift_imm=31, shift_type=0)
    a.mov_reg(1, 1, shift_imm=1, shift_type=1)
    a.add_imm(2, 2, 1)
    a.label("f64_pack_no_inc")
    a.bic_imm(1, 1, 1 << 20) # clear implicit bit 52
    a.orr_reg(1, 1, 2, shift_imm=20, shift_type=0)
    a.bx(14)

    # f64_mul(R0=a_lo, R1=a_hi, R2=b_lo, R3=b_hi) -> R0=lo, R1=hi (positive numbers or zero)
    a.label("f64_mul")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    # Check if a == 0 or b == 0
    a.orr_reg(4, 0, 1, s=1)
    a.b("f64_mul_zero", cond=0x0)
    a.orr_reg(4, 2, 3, s=1)
    a.b("f64_mul_zero", cond=0x0)

    # Extract ea = (a_hi >> 20) & 0x7FF, eb = (b_hi >> 20) & 0x7FF
    a.mov_reg(4, 1, shift_imm=20, shift_type=1)
    a.mov_reg(5, 3, shift_imm=20, shift_type=1)
    a.add_reg(4, 4, 5)
    a.mov_imm(5, 1023)
    a.sub_reg(4, 4, 5) # R4 = exp_biased = ea + eb - 1023

    # Clear exponent bits from a_hi (R1) and b_hi (R3) and set bit 20
    a.mov_imm(5, 0xFF000000)
    a.orr_imm(5, 5, 0x00F00000)
    a.bic_reg(1, 1, 5)
    a.orr_imm(1, 1, 1 << 20)
    a.bic_reg(3, 3, 5)
    a.orr_imm(3, 3, 1 << 20)

    # 64x64 -> 128-bit product in R8(w0), R9(w1), R10(w2), R11(w3)
    # p0 = a_lo(R0) * b_lo(R2) -> R8(lo), R9(hi)
    a.umull(8, 9, 0, 2)
    # p1 = a_lo(R0) * b_hi(R3) -> R6(lo), R7(hi)
    a.umull(6, 7, 0, 3)
    a.add_reg(9, 9, 6, s=1)
    a.adc_imm(10, 7, 0)
    a.mov_imm(11, 0)
    # p2 = a_hi(R1) * b_lo(R2) -> R6(lo), R7(hi)
    a.umull(6, 7, 1, 2)
    a.add_reg(9, 9, 6, s=1)
    a.adc_reg(10, 10, 7, s=1)
    a.adc_imm(11, 11, 0)
    # p3 = a_hi(R1) * b_hi(R3) -> R6(lo), R7(hi)
    a.umull(6, 7, 1, 3)
    a.add_reg(10, 10, 6, s=1)
    a.adc_reg(11, 11, 7)

    # Product is in R11:R10:R9:R8 (bits 105..0).
    # Test bit 105, which is bit (105 - 96) = bit 9 of R11:
    a.tst_imm(11, 1 << 9)
    a.b("f64_mul_shift53", cond=0x1) # BNE -> shift = 53
    # shift = 52:
    # mant_lo = (R9 >> 20) | (R10 << 12)
    # mant_hi = (R10 >> 20) | (R11 << 12)
    # round_bit = (R9 >> 19) & 1
    # sticky_bit = ((R9 & 0x7FFFF) | R8) != 0
    a.mov_reg(0, 9, shift_imm=20, shift_type=1)
    a.orr_reg(0, 0, 10, shift_imm=12, shift_type=0)
    a.mov_reg(1, 10, shift_imm=20, shift_type=1)
    a.orr_reg(1, 1, 11, shift_imm=12, shift_type=0)
    a.mov_reg(2, 4) # exp_biased
    a.mov_reg(3, 9, shift_imm=19, shift_type=1)
    a.and_imm(3, 3, 1)
    a.mov_reg(5, 9, shift_imm=13, shift_type=0) # clear top 13 bits of R9 (bits 31..19) -> leaves bits 18..0
    a.orr_reg(5, 5, 8, s=1)
    a.mov_imm(4, 0, cond=0x0)
    a.mov_imm(4, 1, cond=0x1)
    a.bl("f64_round_and_pack")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("f64_mul_shift53")
    a.add_imm(2, 4, 1) # exp_biased + 1
    a.mov_reg(0, 9, shift_imm=21, shift_type=1)
    a.orr_reg(0, 0, 10, shift_imm=11, shift_type=0)
    a.mov_reg(1, 10, shift_imm=21, shift_type=1)
    a.orr_reg(1, 1, 11, shift_imm=11, shift_type=0)
    a.mov_reg(3, 9, shift_imm=20, shift_type=1)
    a.and_imm(3, 3, 1)
    a.mov_reg(5, 9, shift_imm=12, shift_type=0) # leaves bits 19..0
    a.orr_reg(5, 5, 8, s=1)
    a.mov_imm(4, 0, cond=0x0)
    a.mov_imm(4, 1, cond=0x1)
    a.bl("f64_round_and_pack")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("f64_mul_zero")
    a.mov_imm(0, 0)
    a.mov_imm(1, 0)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    # f64_div(R0=a_lo, R1=a_hi, R2=b_lo, R3=b_hi) -> R0=lo, R1=hi
    a.label("f64_div")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.orr_reg(4, 0, 1, s=1)
    a.b("f64_div_zero", cond=0x0)
    # Extract ea, eb
    a.mov_reg(4, 1, shift_imm=20, shift_type=1)
    a.mov_reg(5, 3, shift_imm=20, shift_type=1)
    a.sub_reg(4, 4, 5)
    a.mov_imm(5, 1023)
    a.add_reg(4, 4, 5) # R4 = exp_biased = ea - eb + 1023

    # Extract 53-bit mantissas ma (R1:R0) and mb (R3:R2)
    a.mov_imm(5, 0xFF000000)
    a.orr_imm(5, 5, 0x00F00000)
    a.bic_reg(1, 1, 5)
    a.orr_imm(1, 1, 1 << 20)
    a.bic_reg(3, 3, 5)
    a.orr_imm(3, 3, 1 << 20)

    # Compare ma (R1:R0) vs mb (R3:R2):
    a.cmp_reg(1, 3)
    a.cmp_reg(0, 2, cond=0x0) # if R1 == R3, cmp R0, R2
    a.b("f64_div_ge", cond=0x2) # BCS (ma >= mb)
    # ma < mb: ma <<= 1, exp_biased -= 1
    a.add_reg(0, 0, 0, s=1)
    a.adc_reg(1, 1, 1)
    a.sub_imm(4, 4, 1)
    a.label("f64_div_ge")
    # 54-step bitwise division: rem = R1:R0, mb = R3:R2, q = R7:R6
    a.mov_imm(6, 0)
    a.mov_imm(7, 0)
    a.mov_imm(8, 54)
    a.label("f64_div_loop")
    # q <<= 1
    a.add_reg(6, 6, 6, s=1)
    a.adc_reg(7, 7, 7)
    # compare rem (R1:R0) >= mb (R3:R2)
    a.cmp_reg(1, 3)
    a.cmp_reg(0, 2, cond=0x0)
    a.b("f64_div_lt", cond=0x3) # BCC
    # rem -= mb, q |= 1
    a.sub_reg(0, 0, 2, s=1)
    a.sbc_reg(1, 1, 3)
    a.orr_imm(6, 6, 1)
    a.label("f64_div_lt")
    # rem <<= 1
    a.add_reg(0, 0, 0, s=1)
    a.adc_reg(1, 1, 1)
    a.sub_imm(8, 8, 1, s=1)
    a.b("f64_div_loop", cond=0x1)

    # Now q (54 bits) is in R7:R6, rem is in R1:R0
    # round_bit = R6 & 1
    # sticky_bit = (R0 | R1) != 0
    # mant = q >> 1
    a.orr_reg(5, 0, 1, s=1)
    a.mov_imm(4 + 1, 0, cond=0x0) # wait: R5 = sticky_bit
    a.mov_imm(5, 1, cond=0x1)
    a.and_imm(3, 6, 1)            # R3 = round_bit
    a.mov_reg(0, 6, shift_imm=1, shift_type=1)
    a.orr_reg(0, 0, 7, shift_imm=31, shift_type=0)
    a.mov_reg(1, 7, shift_imm=1, shift_type=1)
    a.mov_reg(2, 4)               # R2 = exp_biased
    a.mov_reg(4, 5)               # R4 = sticky_bit
    a.bl("f64_round_and_pack")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("f64_div_zero")
    a.mov_imm(0, 0)
    a.mov_imm(1, 0)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    # f64_add_pos(R0=a_lo, R1=a_hi, R2=b_lo, R3=b_hi) -> R0=lo, R1=hi (both >= 0)
    a.label("f64_add_pos")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.orr_reg(4, 0, 1, s=1)
    a.b("f64_add_ret_b", cond=0x0)
    a.orr_reg(4, 2, 3, s=1)
    a.b("f64_add_ret_a", cond=0x0)

    # Ensure a >= b so ea >= eb: compare R1:R0 vs R3:R2
    a.cmp_reg(1, 3)
    a.cmp_reg(0, 2, cond=0x0)
    a.b("f64_add_no_swap", cond=0x2) # BCS
    # swap R0<->R2, R1<->R3
    a.mov_reg(4, 0); a.mov_reg(0, 2); a.mov_reg(2, 4)
    a.mov_reg(4, 1); a.mov_reg(1, 3); a.mov_reg(3, 4)
    a.label("f64_add_no_swap")

    a.mov_reg(4, 1, shift_imm=20, shift_type=1) # R4 = ea
    a.mov_reg(5, 3, shift_imm=20, shift_type=1) # R5 = eb
    a.sub_reg(6, 4, 5)                          # R6 = diff = ea - eb

    a.mov_imm(7, 0xFF000000)
    a.orr_imm(7, 7, 0x00F00000)
    a.bic_reg(1, 1, 7); a.orr_imm(1, 1, 1 << 20)
    a.bic_reg(3, 3, 7); a.orr_imm(3, 3, 1 << 20)

    # Shift both ma (R1:R0) and mb (R3:R2) left by 3 bits for guard, round, sticky!
    a.mov_reg(1, 1, shift_imm=3, shift_type=0)
    a.orr_reg(1, 1, 0, shift_imm=29, shift_type=1)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)

    a.mov_reg(3, 3, shift_imm=3, shift_type=0)
    a.orr_reg(3, 3, 2, shift_imm=29, shift_type=1)
    a.mov_reg(2, 2, shift_imm=3, shift_type=0)

    # Shift mb (R3:R2) right by R6 steps (1 bit per loop iteration, accumulating sticky in bit 0 of R2)
    a.label("f64_add_shr_loop")
    a.cmp_imm(6, 0)
    a.b("f64_add_shr_done", cond=0x0)
    a.and_imm(7, 2, 1) # bit shifted out
    a.mov_reg(2, 2, shift_imm=1, shift_type=1)
    a.orr_reg(2, 2, 3, shift_imm=31, shift_type=0)
    a.mov_reg(3, 3, shift_imm=1, shift_type=1)
    a.orr_reg(2, 2, 7) # sticky bit into LSB
    a.sub_imm(6, 6, 1)
    a.b("f64_add_shr_loop")
    a.label("f64_add_shr_done")

    # Add ma_ext (R1:R0) + mb_ext (R3:R2)
    a.add_reg(0, 0, 2, s=1)
    a.adc_reg(1, 1, 3)

    # Check if sum overflowed to bit 56 (which is bit 56-32 = bit 24 of R1)
    a.tst_imm(1, 1 << 24)
    a.b("f64_add_no_ovf", cond=0x0)
    # Shift sum right by 1 (preserving sticky) and increment ea (R4)
    a.and_imm(7, 0, 1)
    a.mov_reg(0, 0, shift_imm=1, shift_type=1)
    a.orr_reg(0, 0, 1, shift_imm=31, shift_type=0)
    a.mov_reg(1, 1, shift_imm=1, shift_type=1)
    a.orr_reg(0, 0, 7)
    a.add_imm(4, 4, 1)
    a.label("f64_add_no_ovf")

    # Now binary point is at +3:
    # round_bit = (R0 >> 2) & 1
    # sticky_bit = (R0 & 3) != 0
    # mant = (R1:R0) >> 3
    a.mov_reg(3, 0, shift_imm=2, shift_type=1)
    a.and_imm(3, 3, 1) # R3 = round_bit
    a.and_imm(5, 0, 3, s=1)
    a.mov_imm(5, 1, cond=0x1) # R5 = sticky_bit
    a.mov_reg(0, 0, shift_imm=3, shift_type=1)
    a.orr_reg(0, 0, 1, shift_imm=29, shift_type=0)
    a.mov_reg(1, 1, shift_imm=3, shift_type=1)
    a.mov_reg(2, 4) # exp_biased
    a.mov_reg(4, 5) # sticky_bit
    a.bl("f64_round_and_pack")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("f64_add_ret_b")
    a.mov_reg(0, 2); a.mov_reg(1, 3)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("f64_add_ret_a")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])



class _ExtNamespace:
    def __init__(self, d):
        self.__dict__.update(d)

def build_all_rom_tables_inline(ext_dict, control_mode=None):
    ext = _ExtNamespace(ext_dict)
    def f64_u64(d):
        return struct.unpack("<Q", struct.pack("<d", float(d)))[0]

    def u64_f64(u):
        return struct.unpack("<d", struct.pack("<Q", int(u) & 0xFFFFFFFFFFFFFFFF))[0]

    def to_bgr555(hex_str):
        if not hex_str:
            return 0
        r = (int(hex_str[1:3], 16) >> 3) & 31
        g = (int(hex_str[3:5], 16) >> 3) & 31
        b = (int(hex_str[5:7], 16) >> 3) & 31
        return r | (g << 5) | (b << 10)

    class StringPool:
        def __init__(self):
            self.buf = bytearray()
            self.offsets = {}

        def add(self, s):
            if s is None:
                return 0xFFFFFFFF
            s = str(s)
            if s in self.offsets:
                return self.offsets[s]
            off = len(self.buf)
            self.buf.extend(s.encode("utf-8") + b"\x00")
            self.offsets[s] = off
            return off

    # Canonical index lists
    TYPES = ext.types
    CATS = ['physical', 'special', 'status']
    ANIMS = ['crunch', 'flame', 'steam', 'whirl', 'splash', 'slash', 'sparkle', 'chill']
    STATUSES = [None, 'Sizzling', 'Brined', 'Drowsy', 'Seasoned', 'Appetized']
    FAMILIES = ['Sandwiches', 'Dumplings', 'Noodles', 'Soup']
    ARCHS = ['slice', 'club', 'sub', 'muffin', 'scone', 'burger', 'croissant', 'pita', 'taco_open', 'bagel', 'waffle', 'pretzel', 'bao', 'gyoza', 'empanada', 'khinkali', 'mochi', 'ravioli', 'onigiri', 'shumai', 'takoyaki', 'burek', 'ramen', 'pasta_nest', 'soba_mat', 'pho', 'wok_pan', 'mac_cup', 'lasagna', 'noodle_drake', 'teacup', 'cauldron', 'tureen', 'bread_bowl', 'clay_pot', 'chili_pot', 'myth_bowl']
    LIMBS = ['stub', 'paws', 'heavy', 'fins', 'arms', 'bounce', 'none', 'float', 'claws']
    TOPS = ['flag', 'grill', 'skewer', 'leaf', 'periscope', 'drip', 'crown', 'dill', 'horns', 'sugar', 'ears', 'chili', 'cream', 'seeds', 'antennae', 'moon', 'egg', 'knot', 'steam', 'pleat', 'none', 'flame', 'halo']
    SIDES = ['none', 'tail', 'cape', 'fins', 'wings', 'arms', 'shield', 'aura', 'claws']
    POSES = ['wide', 'high', 'low', 'center', 'lean_l', 'tall', 'right', 'lean_r', 'left']
    EYES = ['happy', 'wide', 'sleepy', 'fierce', 'round']
    ITEM_KINDS = ['plate', 'heal', 'cure', 'revive', 'treat', 'recipe', 'key']
    ITEM_IDS = list(ext.items.keys())
    SHOP_REGIONS = list(ext.regional_shops.keys())
    MAP_IDS = list(ext.maps.keys())
    TRAINER_IDS = list(ext.trainers.keys())
    QUEST_IDS = [q["id"] for q in ext.quests]
    SECRET_IDS = [s["id"] for s in ext.secrets]
    TRACK_IDS = list(ext.music_tracks.keys())
    SFX_IDS = list(ext.sfx_defs.keys())
    CHAR_KEYS = list(ext.char_sprites.keys())
    DIRS = ['down', 'up', 'left', 'right']
    NPC_ACTIONS = [None, 'heal', 'shop', 'cook', 'cafe', 'secret151']

    def build_all_rom_tables():
        pool = StringPool()
        tables = {}

        # 0. FONT_SANS (768 B)
        tables[0] = ("FONT_SANS", ext.font_sans_bytes, 96)

        # 1. FONT_SERIF (1,536 B)
        tables[1] = ("FONT_SERIF", ext.font_serif_bytes, 96)

        # 2. TYPES (12 types + 12x12 TYPE_CHART + 12x12 FLAVOR_COMBOS)
        t2 = bytearray()
        for t in TYPES:
            t2.extend(struct.pack("<II", pool.add(t), pool.add(ext.type_colors[t])))
        for t_atk in TYPES:
            for t_def in TYPES:
                val = ext.type_chart[t_atk][t_def]
                code = 1 if val == 0.5 else (2 if val == 1 else 4)
                t2.append(code)
        for i, t1 in enumerate(TYPES):
            for j, t2_name in enumerate(TYPES):
                key = f"{t1}+{t2_name}"
                cb = ext.flavor_combos.get(key)
                if cb:
                    t2.extend(struct.pack("<IQQ", pool.add(cb["name"]), f64_u64(cb["bonus"]), f64_u64(cb["healPct"])))
                else:
                    t2.extend(struct.pack("<IQQ", 0xFFFFFFFF, f64_u64(1.0), 0))
        tables[2] = ("TYPES", bytes(t2), 12)

        # 3. MOVES (124 * 36 bytes = 4,464 B)
        t3 = bytearray()
        sChance_thresh_map = {
            0.0: 0,
            0.2: 0x33333334,
            0.25: 0x40000000,
            0.3: 0x4CCCCCCD,
            0.4: 0x66666667,
            1.0: 0xFFFFFFFF
        }
        for m in ext.moves:
            mid = m["id"]
            t_idx = TYPES.index(m["type"])
            pwr = (m["power"] + 1) if (control_mode == "move_power" and mid == 1) else m["power"]
            acc = m["acc"]
            pp = m["pp"]
            temp = m["temp"]
            cat_idx = CATS.index(m["cat"])
            anim_idx = ANIMS.index(m["anim"])
            st_idx = STATUSES.index(m.get("status"))
            has_drain = 1 if "drain" in m else 0
            has_schance = 1 if "sChance" in m else 0
            sc_val = float(m.get("sChance", 0.0))
            dr_val = float(m.get("drain", 0.0))
            sc_thresh = sChance_thresh_map.get(sc_val, int(sc_val * 4294967296.0) & 0xFFFFFFFF)
            t3.extend(struct.pack(
                "<BBBBBbBBBBBBIIQII",
                mid, t_idx, pwr, acc, pp, temp, cat_idx, anim_idx,
                st_idx, has_schance, has_drain, int(round(sc_val * 100)),
                pool.add(m["name"]), pool.add(m["desc"]),
                f64_u64(dr_val), sc_thresh, int(round(dr_val * 100))
            ))
        tables[3] = ("MOVES", bytes(t3), len(ext.moves))

        # 4. BEATSTS (151 * 56 bytes = 8,456 B)
        t4 = bytearray()
        for sp in ext.beatsts_py:
            sid = sp["id"]
            fam_idx = FAMILIES.index(sp["family"])
            t0 = TYPES.index(sp["types"][0])
            t1 = TYPES.index(sp["types"][1]) if len(sp["types"]) > 1 else 0xFF
            hp = sp["stats"]["hp"]
            atk = sp["stats"]["atk"]
            dfn = sp["stats"]["def"]
            spd = sp["stats"]["spd"]
            evo_to = sp["evo"]["to"] if sp["evo"] else 0
            evo_lv = sp["evo"]["level"] if sp["evo"] else 0
            night = 1 if sp["nightOnly"] else 0
            min_tier = sp["minTier"]
            sh = sp["shape"]
            arch_i = ARCHS.index(sh["arch"])
            smod = sh["sizeMod"]
            limb_i = LIMBS.index(sh["limb"])
            top_i = TOPS.index(sh["top"])
            side_i = SIDES.index(sh["side"])
            pose_i = POSES.index(sh["pose"])
            eye_i = EYES.index(sh["eye"])
            ls_flat = []
            for lv, mv in sp["learnset"]:
                ls_flat.extend([lv, mv])
            t4.extend(struct.pack(
                "<BBBBBBBBBBBBBBBBBBBBIQII",
                sid, fam_idx, t0, t1, hp, atk, dfn, spd,
                evo_to, evo_lv, night, min_tier,
                arch_i, smod, limb_i, top_i, side_i, pose_i, eye_i,
                int(round(sp["catchRate"] * 100)),
                0,
                f64_u64(sp["catchRate"]),
                pool.add(sp["name"]),
                pool.add(sp["dex"])
            ))
            t4.extend(bytes(ls_flat))
        tables[4] = ("BEATSTS", bytes(t4), len(ext.beatsts_py))

        # 5. SPECIES_SPRITES (151 * 1,120 bytes = 169,120 B)
        t5 = bytearray()
        for sp in ext.beatsts_py:
            for c in sp["palette"]:
                t5.extend(struct.pack("<H", to_bgr555(c)))
            for c in sp["palette"]:
                t5.extend(struct.pack("<I", pool.add(c) if c else 0xFFFFFFFF))
            for grid in (sp["front"], sp["back"]):
                for ty in range(4):
                    for tx in range(4):
                        for py in range(8):
                            for px in range(0, 8, 2):
                                p0 = grid[(ty*8 + py)*32 + (tx*8 + px)] & 0xF
                                p1 = grid[(ty*8 + py)*32 + (tx*8 + px + 1)] & 0xF
                                t5.append(p0 | (p1 << 4))
        tables[5] = ("SPECIES_SPRITES", bytes(t5), len(ext.beatsts_py))

        # 6. TILES_8X8
        t6 = bytearray()
        for tid in range(74):
            grid = ext.tiles_py[tid]
            for i in range(0, 64, 2):
                t6.append((grid[i] & 0xF) | ((grid[i+1] & 0xF) << 4))
        tile_pal = [None, '#181820', '#58a848', '#408830', '#78c860', '#d8b880', '#b89860', '#4888c8', '#70b0e8', '#c85838', '#e8e0d0', '#885030', '#386830', '#f0c040', '#a0a8b0', '#f8f8f0']
        for c in tile_pal:
            t6.extend(struct.pack("<H", to_bgr555(c)))
        for c in tile_pal:
            t6.extend(struct.pack("<I", pool.add(c) if c else 0xFFFFFFFF))
        for tid in range(74):
            t6.extend(struct.pack("<I", pool.add(ext.tile_roles[str(tid)])))
        for tid in range(74):
            t6.append(1 if tid in ext.solid_tiles else 0)
        while len(t6) % 4 != 0: t6.append(0)
        tables[6] = ("TILES_8X8", bytes(t6), 74)

        # 7. CHAR_SPRITES (47 chars * 28 bytes = 1,316 B)
        t7 = bytearray()
        for k in CHAR_KEYS:
            cs = ext.char_sprites[k]
            t7.extend(struct.pack(
                "<IIIIIII",
                pool.add(k), pool.add(cs["hat"]), pool.add(cs["hair"]),
                pool.add(cs["shirt"]), pool.add(cs["pants"]),
                pool.add(cs["hatStyle"]), pool.add(cs["acc"])
            ))
        tables[7] = ("CHAR_SPRITES", bytes(t7), len(CHAR_KEYS))

        # 8. ITEMS (25 items * 32 bytes = 800 B)
        t8 = bytearray()
        for k in ITEM_IDS:
            it = ext.items[k]
            kind_i = ITEM_KINDS.index(it["kind"])
            tier = it.get("tier", 0)
            heal_hp = it.get("healHp", 0)
            move_id = it.get("moveId", 0xFF)
            price = it.get("price", 0)
            pb = float(it.get("plateBonus", 0.0))
            t8.extend(struct.pack(
                "<BBHHHIIIQ",
                kind_i, tier, heal_hp, move_id, price,
                pool.add(it["id"]), pool.add(it["name"]), pool.add(it["desc"]),
                f64_u64(pb)
            ))
        tables[8] = ("ITEMS", bytes(t8), len(ITEM_IDS))

        # 9. REGIONAL_SHOPS (5 shops * 36 bytes = 180 B)
        t9 = bytearray()
        for rname in SHOP_REGIONS:
            sh = ext.regional_shops[rname]
            stock_idxs = [ITEM_IDS.index(x) for x in sh["stock"]]
            padded = stock_idxs + [0xFF] * (24 - len(stock_idxs))
            t9.extend(struct.pack("<III", pool.add(rname), pool.add(sh["clerkLine"]), len(stock_idxs)))
            t9.extend(bytes(padded))
        tables[9] = ("REGIONAL_SHOPS", bytes(t9), len(SHOP_REGIONS))

        # 10. MAPS (56 maps: 40-byte header per map + variable data)
        HDR_SZ = 56 * 40
        map_headers = bytearray(HDR_SZ)
        map_var = bytearray()
        npc_global_idx = 0
        for mi, mid in enumerate(MAP_IDS):
            mp = ext.maps[mid]
            w = mp["w"]; h = mp["h"]
            dark = 1 if mp.get("dark") else 0
            music_idx = TRACK_IDS.index(mp["music"])
            wp = mp.get("wildPool", [])
            portals = mp.get("portals", [])
            npcs = mp.get("npcs", [])
            signs = mp.get("signs", [])

            grid_off = HDR_SZ + len(map_var)
            map_var.extend(bytes(mp["grid"]))
            while len(map_var) % 4 != 0: map_var.append(0)

            wp_off = HDR_SZ + len(map_var)
            for e in wp:
                map_var.extend(struct.pack("<BBBB", e[0], e[1], e[2], 0))

            port_off = HDR_SZ + len(map_var)
            for p in portals:
                to_idx = MAP_IDS.index(p["to"])
                req_seals = 9 if (control_mode == "9_seals" and p["to"] == "grand_tasting_hall") else p.get("reqSeals", 0)
                req_champ = 1 if p.get("reqChampion") else 0
                map_var.extend(struct.pack("<BBBBBBH", p["x"], p["y"], to_idx, p["tx"], p["ty"], req_seals, req_champ))

            npc_off = HDR_SZ + len(map_var)
            for n in npcs:
                spr_idx = CHAR_KEYS.index(n.get("sprite", "villager_0"))
                dir_idx = DIRS.index(n.get("dir", "down"))
                act_idx = NPC_ACTIONS.index(n.get("action"))
                pushable = 1 if n.get("pushable") else 0
                q_give = QUEST_IDS.index(n["questGive"]) if "questGive" in n else 0xFF
                q_step = QUEST_IDS.index(n["questStep"]) if "questStep" in n else 0xFF
                step_idx = n.get("stepIndex", 0)
                q_comp = QUEST_IDS.index(n["questComplete"]) if "questComplete" in n else 0xFF
                sec_idx = SECRET_IDS.index(n["secretId"]) if "secretId" in n else 0xFF
                tr_idx = TRAINER_IDS.index(n["trainer"]) if "trainer" in n else 0xFF

                lines = n.get("lines", [])
                nlines = n.get("nightLines", [])
                nslines = n.get("notStartedLines", [])
                nrlines = n.get("notReadyLines", [])
                has_nlines = 1 if "nightLines" in n else 0
                has_nslines = 1 if "notStartedLines" in n else 0
                has_nrlines = 1 if "notReadyLines" in n else 0

                npc_rec = bytearray(80)
                struct.pack_into(
                    "<IIBBBBBBBBBBBBBBBBHHI", npc_rec, 0,
                    pool.add(n["id"]), pool.add(n["name"]),
                    n["x"], n["y"], spr_idx, dir_idx, act_idx, pushable,
                    q_give, q_step, step_idx, q_comp, sec_idx, tr_idx,
                    len(lines), len(nlines) | (has_nlines << 4),
                    len(nslines) | (has_nslines << 4), len(nrlines) | (has_nrlines << 4),
                    npc_global_idx, 0, 0
                )
                npc_global_idx += 1
                for li in range(3):
                    struct.pack_into("<I", npc_rec, 32 + li*4, pool.add(lines[li]) if li < len(lines) else 0xFFFFFFFF)
                    struct.pack_into("<I", npc_rec, 44 + li*4, pool.add(nlines[li]) if li < len(nlines) else 0xFFFFFFFF)
                    struct.pack_into("<I", npc_rec, 56 + li*4, pool.add(nslines[li]) if li < len(nslines) else 0xFFFFFFFF)
                    struct.pack_into("<I", npc_rec, 68 + li*4, pool.add(nrlines[li]) if li < len(nrlines) else 0xFFFFFFFF)
                map_var.extend(npc_rec)

            sign_off = HDR_SZ + len(map_var)
            for s in signs:
                map_var.extend(struct.pack("<BBHI", s["x"], s["y"], 0, pool.add(s["text"])))

            struct.pack_into(
                "<IIIBBBBBBBBIIIII", map_headers, mi * 40,
                pool.add(mp["id"]), pool.add(mp["name"]), pool.add(mp["region"]),
                w, h, dark, music_idx,
                len(wp), len(portals), len(npcs), len(signs),
                grid_off, wp_off, port_off, npc_off, sign_off
            )
        tables[10] = ("MAPS", bytes(map_headers + map_var), 56)

        # 11. TRAINERS (33 trainers * 48 bytes = 1,584 B)
        t11 = bytearray()
        for tid in TRAINER_IDS:
            tr = ext.trainers[tid]
            seal_idx = tr.get("sealIdx", 0xFF)
            has_seal = 1 if "seal" in tr else 0
            reward = tr.get("rewardGold", 0)
            party = tr.get("party", [])
            rec = bytearray(48)
            struct.pack_into(
                "<IIIIIIHBBBB", rec, 0,
                pool.add(tr["id"]), pool.add(tr["name"]), pool.add(tr["title"]),
                pool.add(tr["intro"]), pool.add(tr["win"]), pool.add(tr.get("after")),
                reward, seal_idx, has_seal, len(party), 0
            )
            struct.pack_into("<I", rec, 32, pool.add(tr.get("seal")) if has_seal else 0xFFFFFFFF)
            for pi in range(6):
                if pi < len(party):
                    rec[36 + pi*2] = party[pi]["id"]
                    rec[36 + pi*2 + 1] = party[pi]["lv"]
                else:
                    rec[36 + pi*2] = 0
                    rec[36 + pi*2 + 1] = 0
            t11.extend(rec)
        tables[11] = ("TRAINERS", bytes(t11), len(TRAINER_IDS))

        # 12. QUESTS (16 quests * 20 bytes = 320 B)
        t12 = bytearray()
        for q in ext.quests:
            t12.extend(struct.pack(
                "<IIIII",
                pool.add(q["id"]), pool.add(q["name"]), q["steps"],
                pool.add(q["reward"]), pool.add(q["map"])
            ))
        tables[12] = ("QUESTS", bytes(t12), len(ext.quests))

        # 13. SECRETS (12 secrets * 12 bytes = 144 B)
        t13 = bytearray()
        for s in ext.secrets:
            t13.extend(struct.pack(
                "<III",
                pool.add(s["id"]), pool.add(s["name"]), pool.add(s["map"])
            ))
        tables[13] = ("SECRETS", bytes(t13), len(ext.secrets))

        # 14. MUSIC_TRACKS (18 tracks: 32-byte header per track + [midi, dur] pairs)
        mt_hdr = bytearray(18 * 32)
        mt_var = bytearray()
        for ti, tname in enumerate(TRACK_IDS):
            tr = ext.music_tracks[tname]
            bpm = tr["bpm"]
            loop = 1 if tr.get("loop") else 0
            ch_offs = []
            ch_lens = []
            for ch in ("pulse1", "pulse2", "wave", "noise"):
                arr = tr.get(ch, [])
                ch_offs.append(18 * 32 + len(mt_var))
                ch_lens.append(len(arr))
                for m_note, dur in arr:
                    if control_mode == "transposed_track" and ti == 0 and ch == "pulse1" and m_note > 0:
                        m_note = (m_note + 2) & 0xFF
                    mt_var.extend(struct.pack("<BB", m_note & 0xFF, dur & 0xFF))
                while len(mt_var) % 4 != 0: mt_var.append(0)
            struct.pack_into(
                "<IHHBBBBIIII", mt_hdr, ti * 32,
                pool.add(tname), bpm, loop,
                ch_lens[0] & 0xFF, ch_lens[1] & 0xFF, ch_lens[2] & 0xFF, ch_lens[3] & 0xFF,
                ch_offs[0], ch_offs[1], ch_offs[2], ch_offs[3]
            )
        tables[14] = ("MUSIC_TRACKS", bytes(mt_hdr + mt_var), len(TRACK_IDS))

        # 15. SFX_DEFS (12 sfx: 32-byte header per sfx + [midi, dur] pairs)
        sfx_hdr = bytearray(12 * 32)
        sfx_var = bytearray()
        for si, sname in enumerate(SFX_IDS):
            sf = ext.sfx_defs[sname]
            bpm = sf["bpm"]
            ch_offs = []
            ch_lens = []
            for ch in ("pulse1", "pulse2", "wave", "noise"):
                arr = sf.get(ch, [])
                ch_offs.append(12 * 32 + len(sfx_var))
                ch_lens.append(len(arr))
                for m_note, dur in arr:
                    sfx_var.extend(struct.pack("<BB", m_note & 0xFF, dur & 0xFF))
                while len(sfx_var) % 4 != 0: sfx_var.append(0)
            struct.pack_into(
                "<IHHBBBBIIII", sfx_hdr, si * 32,
                pool.add(sname), bpm, 0,
                ch_lens[0] & 0xFF, ch_lens[1] & 0xFF, ch_lens[2] & 0xFF, ch_lens[3] & 0xFF,
                ch_offs[0], ch_offs[1], ch_offs[2], ch_offs[3]
            )
        tables[15] = ("SFX_DEFS", bytes(sfx_hdr + sfx_var), len(SFX_IDS))

        # 16. STRING_POOL
        while len(pool.buf) % 4 != 0: pool.buf.append(0)
        tables[16] = ("STRING_POOL", bytes(pool.buf), len(pool.offsets))

        return tables, pool

    return build_all_rom_tables()

def emit_core_and_battle(a: ArmAsm, tables_rom_addrs: dict, control_mode=None):
    # Helper: game_rng_next() -> R0 = u32_draw
    a.label("game_rng_next")
    a.push([1, 2, 14])
    a.mov_imm(0, 0x02001000)
    a.ldr_imm(1, 0, 4)
    a.add_imm(1, 1, 1)
    a.str_imm(1, 0, 4)
    a.ldr_imm(1, 0, 8)
    a.add_imm(1, 1, 1)
    a.str_imm(1, 0, 8)
    a.bl("mulberry32_next")
    a.pop([1, 2, 15])
    a.flush_literals()

    # Helper: mark_seen(R0=speciesId 1..151)
    a.label("mark_seen")
    a.push([1, 2, 3, 14])
    a.sub_imm(1, 0, 1)
    a.cmp_imm(1, 151)
    a.b("ms_done", cond=0x2) # BCS
    a.mov_reg(2, 1, shift_imm=3, shift_type=1) # byte_idx = (spId-1) >> 3
    a.and_imm(3, 1, 7)                         # bit_idx = (spId-1) & 7
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 3, shift_type=0)        # mask = 1 << bit_idx
    a.mov_imm(3, 0x02000056)                   # dexSeenBits
    a.add_reg(3, 3, 2)
    a.ldrb_imm(2, 3, 0)
    a.orr_reg(2, 2, 1)
    a.strb_imm(2, 3, 0)
    a.label("ms_done")
    a.pop([1, 2, 3, 15])

    # Helper: mark_caught(R0=speciesId 1..151)
    a.label("mark_caught")
    a.push([1, 2, 3, 14])
    a.bl("mark_seen")
    a.sub_imm(1, 0, 1)
    a.cmp_imm(1, 151)
    a.b("mc_done", cond=0x2)
    a.mov_reg(2, 1, shift_imm=3, shift_type=1)
    a.and_imm(3, 1, 7)
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 3, shift_type=0)
    a.mov_imm(3, 0x0200006A)                   # dexCaughtBits
    a.add_reg(3, 3, 2)
    a.ldrb_imm(2, 3, 0)
    a.orr_reg(2, 2, 1)
    a.strb_imm(2, 3, 0)
    a.label("mc_done")
    a.pop([1, 2, 3, 15])

    # Helper: bag_set_or_add(R0=item_idx 0..24, R1=delta_s32)
    # Maintains bagCounts[item_idx] AND inserts item_idx into bag_order if not yet present!
    a.label("bag_add")
    a.push([2, 3, 4, 5, 14])
    a.mov_imm(2, 0x0200007E)
    a.add_reg(2, 2, 0, shift_imm=1, shift_type=0)
    a.ldrh_imm(3, 2, 0)
    a.add_reg(3, 3, 1, s=1)
    a.mov_imm(3, 0, cond=0x4) # BMI -> clamp to 0
    a.strh_imm(3, 2, 0)
    # Check if item_idx is already in bag_in_order (0x02001072 + item_idx)
    a.mov_imm(2, 0x02001072)
    a.add_reg(4, 2, 0)
    a.ldrb_imm(5, 4, 0)
    a.cmp_imm(5, 0)
    a.b("bag_add_done", cond=0x1) # already in bag_order
    a.mov_imm(5, 1)
    a.strb_imm(5, 4, 0)
    a.mov_imm(2, 0x02001058)
    a.ldrb_imm(5, 2, 25) # bag_order_len at 0x02001071
    a.add_reg(4, 2, 5)
    a.strb_imm(0, 4, 0)
    a.add_imm(5, 5, 1)
    a.strb_imm(5, 2, 25)
    a.label("bag_add_done")
    a.pop([2, 3, 4, 5, 15])
    a.flush_literals()

    # Helper: log_battle_event(R0=kind, R1=id, R2=dmg_u16, R3=flags, [SP]=targetHpLo)
    # Or pass R4=targetHpLo in register! Let's use R0=kind, R1=id, R2=dmg, R3=flags, and read targetHpLo from R4?
    # Better: pass R0=kind, R1=id, R2=dmg, R3=flags_and_hp (low 8 bits = flags, bits 8..15 = targetHpLo)!
    a.label("log_battle_event")
    a.push([4, 5, 6, 14])
    a.mov_imm(4, 0x0203FC00)
    a.ldrh_imm(5, 4, 0x0B8) # battleEventWriteIdx
    a.and_imm(6, 5, 31)     # idx % 32
    a.add_imm(5, 5, 1)
    a.strh_imm(5, 4, 0x0B8)
    a.add_reg(6, 4, 6, shift_imm=3, shift_type=0) # 0x0203FC00 + (idx%32)*8
    a.add_imm(6, 6, 0x0C0)                        # 0x0203FCC0 + (idx%32)*8
    a.strb_imm(0, 6, 0) # kind
    a.strb_imm(1, 6, 1) # id
    a.strh_imm(2, 6, 2) # damage
    a.strh_imm(3, 6, 4) # +4: flags (low byte), +5: targetHpAfterLo (high byte)
    a.mov_imm(4, 0x02001000)
    a.ldr_imm(5, 4, 8)  # battle_rng_draws
    a.strh_imm(5, 6, 6) # +6: rngDrawsAfter
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    # create_mon(R0=speciesId, R1=level, R2=dst_ptr)
    a.label("create_mon")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
    a.mov_reg(6, 2)
    a.mov_imm(0, 0)
    for off in range(0, 48, 4):
        a.str_imm(0, 6, off)
    a.cmp_imm(4, 1)
    a.mov_imm(4, 1, cond=0xB)
    a.cmp_imm(4, 151)
    a.mov_imm(4, 1, cond=0xC)
    a.sub_imm(7, 4, 1)
    a.mov_imm(8, 56)
    a.mul(7, 7, 8)
    a.mov_imm(8, tables_rom_addrs[4])
    a.add_reg(7, 8, 7)

    a.bl("game_rng_next")
    a.mov_reg(8, 0, shift_imm=29, shift_type=1) # iv = u >> 29

    a.bl("game_rng_next")
    a.mov_imm(1, 1000000000)
    a.umull(2, 3, 0, 1)
    a.str_imm(3, 6, 0x00) # uid
    a.strb_imm(4, 6, 0x04) # speciesId
    a.strb_imm(5, 6, 0x05) # level
    a.mov_imm(0, 0)
    a.strb_imm(0, 6, 0x06) # status = 0
    a.mov_imm(0, 0xFF)
    a.strb_imm(0, 6, 0x07) # lastMoveType = 0xFF

    a.mul(0, 5, 5)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.str_imm(0, 6, 0x14) # xp
    a.add_imm(1, 5, 1)
    a.mul(0, 1, 1)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.str_imm(0, 6, 0x18) # nextXp

    a.ldrb_imm(0, 7, 4)
    a.add_reg(0, 0, 8)
    a.add_reg(0, 0, 0)
    a.mul(0, 0, 5)
    a.mov_imm(1, 100)
    a.bl("udiv32")
    a.add_reg(0, 0, 5)
    a.add_imm(0, 0, 12)
    a.strh_imm(0, 6, 0x08)
    a.strh_imm(0, 6, 0x0A)

    for idx_stat, off_mon in [(5, 0x0C), (6, 0x0E), (7, 0x10)]:
        a.ldrb_imm(0, 7, idx_stat)
        a.add_reg(0, 0, 8)
        a.add_reg(0, 0, 0)
        a.mul(0, 0, 5)
        a.mov_imm(1, 100)
        a.bl("udiv32")
        a.add_imm(0, 0, 6)
        a.strh_imm(0, 6, off_mon)

    a.mov_imm(9, 0)
    a.mov_imm(10, 0)
    a.label("cm_ls_loop")
    a.add_reg(0, 7, 10, shift_imm=1, shift_type=0)
    a.ldrb_imm(1, 0, 40)
    a.cmp_reg(1, 5)
    a.b("cm_ls_done", cond=0x8)
    a.add_imm(9, 9, 1)
    a.add_imm(10, 10, 1)
    a.cmp_imm(10, 8)
    a.b("cm_ls_loop", cond=0x3)
    a.label("cm_ls_done")
    a.cmp_imm(9, 0)
    a.mov_imm(9, 8, cond=0x0)
    a.cmp_imm(9, 4)
    a.sub_imm(10, 9, 4, cond=0x8)
    a.mov_imm(10, 0, cond=0x9)
    a.mov_imm(11, 4, cond=0x8)
    a.mov_reg(11, 9, cond=0x9)
    a.strh_imm(11, 6, 0x12)

    a.mov_imm(8, 0)
    a.label("cm_mv_fill")
    a.cmp_reg(8, 11)
    a.b("cm_mv_empty", cond=0x2)
    a.add_reg(0, 10, 8)
    a.add_reg(0, 7, 0, shift_imm=1, shift_type=0)
    a.ldrb_imm(1, 0, 41)
    a.add_reg(2, 6, 8)
    a.strb_imm(1, 2, 0x1C)
    a.mov_imm(3, 36)
    a.mul(3, 1, 3)
    a.mov_imm(0, tables_rom_addrs[3])
    a.add_reg(3, 0, 3)
    a.ldrb_imm(0, 3, 4)
    a.strb_imm(0, 2, 0x20)
    a.strb_imm(0, 2, 0x24)
    a.add_imm(8, 8, 1)
    a.b("cm_mv_fill")
    a.label("cm_mv_empty")
    a.cmp_imm(8, 4)
    a.b("cm_mv_done", cond=0x2)
    a.add_reg(2, 6, 8)
    a.mov_imm(0, 0xFF)
    a.strb_imm(0, 2, 0x1C)
    a.mov_imm(0, 0)
    a.strb_imm(0, 2, 0x20)
    a.strb_imm(0, 2, 0x24)
    a.add_imm(8, 8, 1)
    a.b("cm_mv_empty")
    a.label("cm_mv_done")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # recalc_stats(R0=mon_ptr)
    a.label("recalc_stats")
    a.push([4, 5, 6, 7, 8, 14])
    a.mov_reg(4, 0) # R4 = mon_ptr
    a.ldrb_imm(0, 4, 4) # speciesId
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(5, 0, 1)
    a.mov_imm(0, tables_rom_addrs[4])
    a.add_reg(5, 0, 5)  # R5 = sp_ptr
    a.ldrb_imm(6, 4, 5) # R6 = mon.level
    a.ldrh_imm(7, 4, 0x0A) # R7 = oldMaxHp

    # newMaxHp = (base_hp * 2 * level) // 100 + level + 12
    a.ldrb_imm(0, 5, 4)
    a.add_reg(0, 0, 0)
    a.mul(0, 0, 6)
    a.mov_imm(1, 100)
    a.bl("udiv32")
    a.add_reg(0, 0, 6)
    a.add_imm(0, 0, 12)
    a.strh_imm(0, 4, 0x0A) # mon.maxHp = R0
    # diff = max(0, newMaxHp - oldMaxHp)
    a.sub_reg(1, 0, 7, s=1)
    a.mov_imm(1, 0, cond=0x4) # if < 0, diff = 0
    a.ldrh_imm(2, 4, 0x08)    # mon.hp
    a.add_reg(2, 2, 1)
    a.cmp_reg(2, 0)
    a.mov_reg(2, 0, cond=0x8) # min(maxHp, hp + diff)
    a.strh_imm(2, 4, 0x08)

    for idx_stat, off_mon in [(5, 0x0C), (6, 0x0E), (7, 0x10)]:
        a.ldrb_imm(0, 5, idx_stat)
        a.add_reg(0, 0, 0)
        a.mul(0, 0, 6)
        a.mov_imm(1, 100)
        a.bl("udiv32")
        a.add_imm(0, 0, 6)
        a.strh_imm(0, 4, off_mon)

    # nextXp = (level + 1)^2 * 8
    a.add_imm(0, 6, 1)
    a.mul(0, 0, 0)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.str_imm(0, 4, 0x18)
    a.pop([4, 5, 6, 7, 8, 15])
    a.flush_literals()

    # grant_xp(R0=mon_ptr, R1=xp_gain)
    a.label("grant_xp")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(4, 0) # R4 = mon_ptr
    a.ldr_imm(2, 4, 0x14) # mon.xp
    a.add_reg(2, 2, 1)
    a.str_imm(2, 4, 0x14)

    a.label("gx_lv_loop")
    a.ldr_imm(2, 4, 0x14)  # mon.xp
    a.ldr_imm(3, 4, 0x18)  # mon.nextXp
    a.cmp_reg(2, 3)
    a.b("gx_done", cond=0x3) # BCC (xp < nextXp)
    a.ldrb_imm(5, 4, 5)    # mon.level
    a.cmp_imm(5, 100)
    a.b("gx_done", cond=0x2) # BCS (level >= 100)
    a.add_imm(5, 5, 1)
    a.strb_imm(5, 4, 5)    # mon.level++
    a.mov_reg(0, 4)
    a.bl("recalc_stats")

    # sp = BEATSTS_BY_ID[mon.speciesId] (before evo check!)
    a.ldrb_imm(0, 4, 4)
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(6, 0, 1)
    a.mov_imm(0, tables_rom_addrs[4])
    a.add_reg(6, 0, 6)     # R6 = sp_ptr

    # Check 8 learnset entries at sp_ptr + 40
    a.mov_imm(7, 0)        # R7 = ls_idx (0..7)
    a.label("gx_ls_loop")
    a.add_reg(0, 6, 7, shift_imm=1, shift_type=0)
    a.ldrb_imm(1, 0, 40)   # lv
    a.ldrb_imm(8, 0, 41)   # mid (R8)
    a.cmp_reg(1, 5)        # lv == mon.level?
    a.b("gx_ls_next", cond=0x1)
    # Check if mon already knows mid
    a.ldrh_imm(9, 4, 0x12) # R9 = mon.moveCount
    a.mov_imm(10, 0)
    a.label("gx_chk_known")
    a.cmp_reg(10, 9)
    a.b("gx_not_known", cond=0x2)
    a.add_reg(0, 4, 10)
    a.ldrb_imm(1, 0, 0x1C)
    a.cmp_reg(1, 8)
    a.b("gx_ls_next", cond=0x0) # already knows mid!
    a.add_imm(10, 10, 1)
    a.b("gx_chk_known")

    a.label("gx_not_known")
    # Look up new move in Table 3 (MOVES, 36B)
    a.mov_imm(0, 36)
    a.mul(10, 8, 0)
    a.mov_imm(0, tables_rom_addrs[3])
    a.add_reg(10, 0, 10)   # R10 = new_mv_ptr
    a.ldrb_imm(11, 10, 4)  # R11 = new_mv.pp

    a.cmp_imm(9, 4)
    a.b("gx_replace_mv", cond=0x2) # moveCount >= 4
    # Append move at index R9
    a.add_reg(0, 4, 9)
    a.strb_imm(8, 0, 0x1C)
    a.strb_imm(11, 0, 0x20)
    a.strb_imm(11, 0, 0x24)
    a.add_imm(9, 9, 1)
    a.strh_imm(9, 4, 0x12)
    a.b("gx_ls_next")

    a.label("gx_replace_mv")
    # Find minIdx in 0..3 with minimum move power
    a.mov_imm(9, 0) # R9 = minIdx = 0
    a.ldrb_imm(0, 4, 0x1C) # moveIds[0]
    a.mov_imm(1, 36)
    a.mul(0, 0, 1)
    a.mov_imm(2, tables_rom_addrs[3])
    a.add_reg(0, 2, 0)
    a.ldrb_imm(3, 0, 2) # R3 = minPower = MOVES[moveIds[0]].power

    for slot_i in (1, 2, 3):
        a.ldrb_imm(0, 4, 0x1C + slot_i)
        a.mul(0, 0, 1)
        a.add_reg(0, 2, 0)
        a.ldrb_imm(0, 0, 2) # power of slot_i
        a.cmp_reg(0, 3)
        a.mov_reg(3, 0, cond=0x3)      # if power < minPower: minPower = power
        a.mov_imm(9, slot_i, cond=0x3) # minIdx = slot_i

    # Compare new_mv.power vs minPower (R3)
    a.ldrb_imm(0, 10, 2) # new_mv.power
    a.cmp_reg(0, 3)
    a.b("gx_ls_next", cond=0x9) # BLS (new_mv.power <= minPower)
    a.add_reg(0, 4, 9)
    a.strb_imm(8, 0, 0x1C)
    a.strb_imm(11, 0, 0x20)
    a.strb_imm(11, 0, 0x24)

    a.label("gx_ls_next")
    a.add_imm(7, 7, 1)
    a.cmp_imm(7, 8)
    a.b("gx_ls_loop", cond=0x3)

    # Check evolution: sp.evo_to (+8) != 0 && mon.level (R5) >= sp.evo_lv (+9)
    a.ldrb_imm(0, 6, 8) # evo_to
    a.cmp_imm(0, 0)
    a.b("gx_lv_loop", cond=0x0)
    a.ldrb_imm(1, 6, 9) # evo_lv
    a.cmp_reg(5, 1)
    a.b("gx_lv_loop", cond=0x3) # BCC (level < evo_lv)
    # Evolve!
    a.strb_imm(0, 4, 4) # mon.speciesId = evo_to
    a.mov_reg(7, 0)
    a.mov_reg(0, 4)
    a.bl("recalc_stats")
    a.mov_reg(0, 7)
    a.bl("mark_caught")
    a.b("gx_lv_loop")

    a.label("gx_done")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # compute_damage(R0=attacker_ptr, R1=defender_ptr, R2=moveId, R3=battleTemp_s32)
    # Returns: R0=dmg, R1=eff_code (1..5), R2=combo_ptr (or 0)
    a.label("compute_damage")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.sub_imm(13, 13, 32)
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
    a.mov_reg(6, 2)
    a.mov_reg(7, 3)

    a.mov_imm(0, 36)
    a.mul(8, 6, 0)
    a.mov_imm(0, tables_rom_addrs[3])
    a.add_reg(8, 0, 8) # R8 = move_ptr
    a.ldrb_imm(0, 8, 6) # cat_idx
    a.cmp_imm(0, 2)
    a.b("cd_zero_dmg", cond=0x0)
    a.ldrb_imm(0, 8, 2) # power
    a.cmp_imm(0, 0)
    a.b("cd_zero_dmg", cond=0x0)

    a.ldrb_imm(0, 4, 4)
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(9, 0, 1)
    a.mov_imm(0, tables_rom_addrs[4])
    a.add_reg(9, 0, 9)

    a.ldrb_imm(0, 5, 4)
    a.sub_imm(0, 0, 1)
    a.mul(10, 0, 1)
    a.mov_imm(0, tables_rom_addrs[4])
    a.add_reg(10, 0, 10)

    a.ldrb_imm(0, 8, 1) # move.type
    a.ldrb_imm(1, 9, 2)
    a.ldrb_imm(2, 9, 3)
    a.cmp_reg(0, 1)
    a.cmp_reg(0, 2, cond=0x1)
    a.mov_imm(1, 0)
    if control_mode == "stab_14":
        a.mov_imm(1, 0x66666666, cond=0x0)
        a.mov_imm(2, 0x3FF66666, cond=0x0)
    else:
        a.mov_imm(2, 0x3FF40000, cond=0x0)
    a.mov_imm(2, 0x3FF00000, cond=0x1)
    a.str_imm(1, 13, 0)
    a.str_imm(2, 13, 4)

    a.mov_imm(1, 12)
    a.mul(1, 0, 1)
    a.mov_imm(2, tables_rom_addrs[2] + 96)
    a.add_reg(1, 2, 1)
    a.ldrb_imm(2, 10, 2)
    a.add_reg(2, 1, 2)
    a.ldrb_imm(2, 2, 0)
    a.ldrb_imm(3, 10, 3)
    a.cmp_imm(3, 0xFF)
    a.b("cd_eff_one_type", cond=0x0)
    a.add_reg(3, 1, 3)
    a.ldrb_imm(3, 3, 0)
    a.mul(2, 2, 3)
    a.b("cd_eff_done")
    a.label("cd_eff_one_type")
    a.mov_reg(2, 2, shift_imm=1, shift_type=0)
    a.label("cd_eff_done")
    a.cmp_imm(2, 1)
    a.mov_imm(1, 1, cond=0x0); a.mov_imm(3, 0x3FD00000, cond=0x0)
    a.cmp_imm(2, 2)
    a.mov_imm(1, 2, cond=0x0); a.mov_imm(3, 0x3FE00000, cond=0x0)
    a.cmp_imm(2, 4)
    a.mov_imm(1, 3, cond=0x0); a.mov_imm(3, 0x3FF00000, cond=0x0)
    a.cmp_imm(2, 8)
    a.mov_imm(1, 4, cond=0x0); a.mov_imm(3, 0x40000000, cond=0x0)
    a.cmp_imm(2, 16)
    a.mov_imm(1, 5, cond=0x0); a.mov_imm(3, 0x40100000, cond=0x0)
    a.str_imm(1, 13, 24)
    a.mov_imm(2, 0)
    a.str_imm(2, 13, 8)
    a.str_imm(3, 13, 12)

    a.mov_imm(2, 0)
    a.mov_imm(3, 0x3FF00000)
    a.cmp_imm(7, 2)
    a.b("cd_check_temp_low", cond=0xB)
    a.cmp_imm(0, 4); a.cmp_imm(0, 2, cond=0x1); a.cmp_imm(0, 0, cond=0x1)
    a.mov_imm(3, 0x3FF40000, cond=0x0)
    a.cmp_imm(0, 10); a.cmp_imm(0, 6, cond=0x1)
    a.mov_imm(2, 0x9999999A, cond=0x0); a.mov_imm(3, 0x3FE99999, cond=0x0)
    a.b("cd_temp_done")
    a.label("cd_check_temp_low")
    a.cmn_imm(7, 2)
    a.b("cd_temp_done", cond=0xC)
    a.cmp_imm(0, 10); a.cmp_imm(0, 6, cond=0x1); a.cmp_imm(0, 3, cond=0x1)
    a.mov_imm(3, 0x3FF40000, cond=0x0)
    a.cmp_imm(0, 4); a.cmp_imm(0, 5, cond=0x1)
    a.mov_imm(2, 0x9999999A, cond=0x0); a.mov_imm(3, 0x3FE99999, cond=0x0)
    a.label("cd_temp_done")
    a.str_imm(2, 13, 16)
    a.str_imm(3, 13, 20)

    a.mov_imm(11, 0)
    a.ldrb_imm(1, 4, 7)
    a.cmp_imm(1, 0xFF)
    a.b("cd_combo_done", cond=0x0)
    a.cmp_reg(1, 0)
    a.b("cd_combo_done", cond=0x0)
    a.mov_imm(2, 12)
    a.mul(1, 1, 2)
    a.add_reg(1, 1, 0)
    a.mov_imm(2, 20)
    a.mul(1, 1, 2)
    a.mov_imm(2, tables_rom_addrs[2] + 240)
    a.add_reg(1, 2, 1)
    a.ldr_imm(2, 1, 0)
    a.cmn_imm(2, 1)
    a.mov_reg(11, 1, cond=0x1)
    a.label("cd_combo_done")
    a.str_imm(11, 13, 28)

    if control_mode == "rng_skip":
        a.bl("game_rng_next")
    a.bl("game_rng_next")
    a.bl("f64_from_mulberry")
    a.mov_imm(2, 0x33333333)
    a.mov_imm(3, 0x3FC33333)
    a.bl("f64_mul")
    a.mov_reg(2, 0); a.mov_reg(3, 1)
    a.mov_imm(0, 0xCCCCCCCD)
    a.mov_imm(1, 0x3FECCCCC)
    a.bl("f64_add_pos")
    a.mov_reg(9, 0); a.mov_reg(10, 1)

    a.ldrb_imm(0, 4, 5)
    a.add_reg(0, 0, 0)
    a.add_imm(0, 0, 10)
    a.bl("f64_from_u32")
    a.mov_imm(2, 0)
    a.mov_imm(3, 0x40140000)
    a.bl("f64_div")
    a.mov_reg(6, 0); a.mov_reg(7, 1)
    a.ldrb_imm(0, 8, 2)
    a.bl("f64_from_u32")
    a.mov_reg(2, 0); a.mov_reg(3, 1)
    a.mov_reg(0, 6); a.mov_reg(1, 7)
    a.bl("f64_mul")
    a.mov_reg(6, 0); a.mov_reg(7, 1)

    a.ldrh_imm(0, 4, 0x0C)
    a.bl("f64_from_u32")
    a.mov_reg(8, 0); a.mov_reg(11, 1)
    a.ldrh_imm(0, 5, 0x0E)
    a.cmp_imm(0, 1)
    a.mov_imm(0, 1, cond=0x3)
    a.bl("f64_from_u32")
    a.mov_reg(2, 0); a.mov_reg(3, 1)
    a.mov_reg(0, 8); a.mov_reg(1, 11)
    a.bl("f64_div")

    a.mov_reg(2, 0); a.mov_reg(3, 1)
    a.mov_reg(0, 6); a.mov_reg(1, 7)
    a.bl("f64_mul")
    a.mov_imm(2, 0)
    a.mov_imm(3, 0x40450000)
    a.bl("f64_div")
    a.mov_imm(2, 0)
    a.mov_imm(3, 0x40000000)
    a.bl("f64_add_pos")

    a.ldr_imm(2, 13, 0); a.ldr_imm(3, 13, 4)
    a.bl("f64_mul")
    a.ldr_imm(2, 13, 8); a.ldr_imm(3, 13, 12)
    a.bl("f64_mul")
    a.ldr_imm(2, 13, 16); a.ldr_imm(3, 13, 20)
    a.bl("f64_mul")
    a.ldr_imm(4, 13, 28)
    a.cmp_imm(4, 0)
    a.mov_imm(2, 0, cond=0x0); a.mov_imm(3, 0x3FF00000, cond=0x0)
    a.ldr_imm(2, 4, 4, cond=0x1); a.ldr_imm(3, 4, 8, cond=0x1)
    a.bl("f64_mul")
    a.mov_reg(2, 9); a.mov_reg(3, 10)
    a.bl("f64_mul")
    a.bl("f64_to_u32_floor")
    a.cmp_imm(0, 1)
    a.mov_imm(0, 1, cond=0x3)
    a.ldr_imm(1, 13, 24)
    a.ldr_imm(2, 13, 28)
    a.add_imm(13, 13, 32)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("cd_zero_dmg")
    a.mov_imm(0, 0)
    a.mov_imm(1, 0) # eff_code = 0 for status/0-power moves
    a.mov_imm(2, 0)
    a.add_imm(13, 13, 32)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # do_foe_attack(R0=foe_ptr, R1=player_ptr)
    a.label("do_foe_attack")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_reg(4, 0) # R4 = foe_ptr
    a.mov_reg(5, 1) # R5 = player_ptr
    a.ldrh_imm(0, 4, 0x08) # foe.hp
    a.cmp_imm(0, 0)
    a.b("dfa_done", cond=0x0)
    a.ldrh_imm(0, 5, 0x08) # player.hp
    a.cmp_imm(0, 0)
    a.b("dfa_done", cond=0x0)

    # Pick random move: Math.floor(rng() * foe.moves.length)
    a.bl("game_rng_next")
    a.ldrh_imm(1, 4, 0x12) # foe.moveCount
    a.umull(2, 3, 0, 1)    # R3 = (u * moveCount) >> 32
    a.add_reg(0, 4, 3)
    a.ldrb_imm(6, 0, 0x1C) # R6 = moveId

    # Look up move in Table 3 (36B)
    a.mov_imm(0, 36)
    a.mul(7, 6, 0)
    a.mov_imm(0, tables_rom_addrs[3])
    a.add_reg(7, 0, 7)     # R7 = move_ptr

    # Update b.temp (at 0x02001106, s8)
    a.mov_imm(8, 0x02001100)
    a.ldrsb_imm(0, 8, 6)   # b.temp
    a.ldrsb_imm(1, 7, 5)   # mv.temp
    a.add_reg(0, 0, 1)
    a.cmn_imm(0, 2)
    a.mvn_imm(0, 1, cond=0xB) # if < -2 -> -2 (0xFFFFFFFE = ~1)
    a.cmp_imm(0, 2)
    a.mov_imm(0, 2, cond=0xC) # if > 2 -> 2
    a.strb_imm(0, 8, 6)    # store b.temp

    # compute_damage(foe, player, moveId, b.temp)
    a.mov_reg(3, 0)
    a.mov_reg(0, 4)
    a.mov_reg(1, 5)
    a.mov_reg(2, 6)
    a.bl("compute_damage") # R0 = dmg, R1 = eff_code, R2 = combo_ptr

    # foe.lastMoveType = mv.type
    a.ldrb_imm(3, 7, 1)
    a.strb_imm(3, 4, 7)

    # player.hp = max(0, player.hp - dmg)
    a.ldrh_imm(3, 5, 0x08)
    a.sub_reg(3, 3, 0, s=1)
    a.mov_imm(3, 0, cond=0x4)
    a.strh_imm(3, 5, 0x08)

    # Log FOE_MOVE event (kind=2, id=R6, dmg=R0, flags=R1|(combo?8:0)|(hp==0?0x40:0), targetHpLo=R3&0xFF)
    a.cmp_imm(2, 0)
    a.orr_imm(1, 1, 0x08, cond=0x1)
    a.cmp_imm(3, 0)
    a.orr_imm(1, 1, 0x40, cond=0x0)
    a.and_imm(3, 3, 0xFF)
    a.orr_reg(3, 1, 3, shift_imm=8, shift_type=0)
    a.mov_reg(2, 0)
    a.mov_reg(1, 6)
    a.mov_imm(0, 2)
    a.bl("log_battle_event")

    a.label("dfa_done")
    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # execute_battle_turn(R0=moveId)
    a.label("execute_battle_turn")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(6, 0) # R6 = moveId
    a.mov_imm(8, 0x02001100) # R8 = BSTATE
    a.ldrb_imm(0, 8, 5) # player_idx
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.mov_imm(2, 0x020000B4) # party[0]
    a.add_reg(4, 2, 0)       # R4 = player_ptr

    a.ldrb_imm(0, 8, 4) # foe_idx
    a.mul(0, 0, 1)
    a.add_imm(5, 8, 0x10)
    a.add_reg(5, 5, 0)       # R5 = foe_ptr

    a.mov_imm(0, 36)
    a.mul(7, 6, 0)
    a.mov_imm(0, tables_rom_addrs[3])
    a.add_reg(7, 0, 7)       # R7 = move_ptr

    # b.temp = clamp(b.temp + mv.temp, -2, 2)
    a.ldrsb_imm(0, 8, 6)
    a.ldrsb_imm(1, 7, 5)
    a.add_reg(0, 0, 1)
    a.cmn_imm(0, 2)
    a.mvn_imm(0, 1, cond=0xB)
    a.cmp_imm(0, 2)
    a.mov_imm(0, 2, cond=0xC)
    a.strb_imm(0, 8, 6)

    # res = compute_damage(player, foe, moveId, b.temp)
    a.mov_reg(3, 0)
    a.mov_reg(0, 4)
    a.mov_reg(1, 5)
    a.mov_reg(2, 6)
    a.bl("compute_damage")
    a.mov_reg(9, 0)  # R9 = res.dmg
    a.mov_reg(10, 1) # R10 = eff_code
    a.mov_reg(11, 2) # R11 = combo_ptr

    # player.lastMoveType = mv.type
    a.ldrb_imm(0, 7, 1)
    a.strb_imm(0, 4, 7)

    a.cmp_imm(9, 0)
    a.b("ebt_after_dmg", cond=0x0)
    # foe.hp = max(0, foe.hp - res.dmg)
    a.ldrh_imm(0, 5, 0x08)
    a.sub_reg(0, 0, 9, s=1)
    a.mov_imm(0, 0, cond=0x4)
    a.strh_imm(0, 5, 0x08)

    # If combo_ptr != 0: player.hp = min(maxHp, hp + max(1, floor(maxHp * combo.healPct)))
    a.cmp_imm(11, 0)
    a.b("ebt_chk_drain", cond=0x0)
    a.orr_imm(10, 10, 0x08) # flag bit 3 = combo
    a.ldrh_imm(0, 4, 0x0A)  # player.maxHp
    a.bl("f64_from_u32")
    a.ldr_imm(2, 11, 12)    # healPct lo
    a.ldr_imm(3, 11, 16)    # healPct hi
    a.bl("f64_mul")
    a.bl("f64_to_u32_floor")
    a.cmp_imm(0, 1)
    a.mov_imm(0, 1, cond=0x3)
    a.ldrh_imm(1, 4, 0x08)
    a.ldrh_imm(2, 4, 0x0A)
    a.add_reg(1, 1, 0)
    a.cmp_reg(1, 2)
    a.mov_reg(1, 2, cond=0x8)
    a.strh_imm(1, 4, 0x08)

    a.label("ebt_chk_drain")
    a.ldrb_imm(0, 7, 10) # has_drain
    a.cmp_imm(0, 0)
    a.b("ebt_after_dmg", cond=0x0)
    a.mov_reg(0, 9) # res.dmg
    a.bl("f64_from_u32")
    a.ldr_imm(2, 7, 20) # drain_f64 lo
    a.ldr_imm(3, 7, 24) # drain_f64 hi
    a.bl("f64_mul")
    a.bl("f64_to_u32_floor")
    a.cmp_imm(0, 1)
    a.mov_imm(0, 1, cond=0x3)
    a.ldrh_imm(1, 4, 0x08)
    a.ldrh_imm(2, 4, 0x0A)
    a.add_reg(1, 1, 0)
    a.cmp_reg(1, 2)
    a.mov_reg(1, 2, cond=0x8)
    a.strh_imm(1, 4, 0x08)

    a.label("ebt_after_dmg")
    # Check status: if (mv.status && this.rng() < (mv.sChance || 1))
    a.ldrb_imm(0, 7, 8) # st_idx
    a.cmp_imm(0, 0)
    a.b("ebt_after_status", cond=0x0)
    a.bl("game_rng_next") # R0 = u32_draw
    a.ldrb_imm(1, 7, 9)   # has_schance
    a.cmp_imm(1, 0)
    a.b("ebt_inflict_status", cond=0x0) # sChance omitted -> 1.0 -> always true!
    a.ldr_imm(1, 7, 28)   # sc_thresh
    a.cmn_imm(1, 1)       # 0xFFFFFFFF (1.0)?
    a.b("ebt_inflict_status", cond=0x0)
    a.cmp_reg(0, 1)
    a.b("ebt_after_status", cond=0x2) # BCS (u32_draw >= sc_thresh)
    a.label("ebt_inflict_status")
    a.ldrb_imm(0, 7, 8)
    a.strb_imm(0, 5, 6)   # foe.status = mv.status
    a.orr_imm(10, 10, 0x10) # flag bit 4 = status inflicted

    a.label("ebt_after_status")
    # Log PLAYER_MOVE event (after status check! Wait: what if foe fainted and grants XP? Does grant_xp consume RNG draws? No! grant_xp is 100% deterministic!)
    a.ldrh_imm(3, 5, 0x08) # foe.hp
    a.cmp_imm(3, 0)
    a.orr_imm(10, 10, 0x40, cond=0x0)
    a.and_imm(0, 3, 0xFF)
    a.orr_reg(3, 10, 0, shift_imm=8, shift_type=0)
    a.mov_imm(0, 1) # PLAYER_MOVE
    a.mov_reg(1, 6) # moveId
    a.mov_reg(2, 9) # dmg
    a.bl("log_battle_event")

    # Check if foe.hp == 0
    a.ldrh_imm(0, 5, 0x08)
    a.cmp_imm(0, 0)
    a.b("ebt_foe_alive", cond=0x1)

    # Foe fainted! xpGain = Math.floor(foe.level * 16 * (b.isWild ? 1 : 1.4))
    a.ldrb_imm(0, 5, 5) # foe.level
    a.mov_reg(0, 0, shift_imm=4, shift_type=0) # foe.level * 16
    a.ldrb_imm(1, 8, 1) # b.is_wild
    a.cmp_imm(1, 0)
    a.b("ebt_xp_wild", cond=0x1)
    # Trainer battle: multiply by 1.4 using f64_mul + f64_to_u32_floor
    a.bl("f64_from_u32")
    a.mov_imm(2, 0x66666666)
    a.mov_imm(3, 0x3FF66666) # 1.4
    a.bl("f64_mul")
    a.bl("f64_to_u32_floor")
    a.label("ebt_xp_wild")
    a.mov_reg(1, 0)
    a.mov_reg(0, 4)
    a.bl("grant_xp")

    # Check if b.foe_idx + 1 < b.foe_count
    a.ldrb_imm(0, 8, 4) # foe_idx
    a.ldrb_imm(1, 8, 3) # foe_count
    a.add_imm(0, 0, 1)
    a.cmp_reg(0, 1)
    a.strb_imm(0, 8, 4, cond=0x3) # if foe_idx+1 < foe_count: foe_idx++
    a.mov_imm(0, 1, cond=0x2)     # else: pending_end = 1 (WIN)
    a.strb_imm(0, 8, 0x0A, cond=0x2)
    a.mov_imm(0, 6)               # phase = 6 (LOG)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("ebt_foe_alive")
    a.mov_reg(0, 5)
    a.mov_reg(1, 4)
    a.bl("do_foe_attack")
    # Check if player.hp == 0
    a.ldrh_imm(0, 4, 0x08)
    a.cmp_imm(0, 0)
    a.b("ebt_turn_end", cond=0x1)
    # Find first party member with hp > 0
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(1, 0, 0x0B0) # partyCount
    a.add_imm(2, 0, 0x0B4)  # party[0]
    a.mov_imm(3, 0)
    a.label("ebt_find_alive")
    a.cmp_reg(3, 1)
    a.b("ebt_all_fainted", cond=0x2)
    a.ldrh_imm(0, 2, 0x08)
    a.cmp_imm(0, 0)
    a.b("ebt_found_alive", cond=0x1)
    a.add_imm(2, 2, 48)
    a.add_imm(3, 3, 1)
    a.b("ebt_find_alive")

    a.label("ebt_found_alive")
    a.strb_imm(3, 8, 5) # b.player_idx = nextIdx
    a.b("ebt_turn_end")

    a.label("ebt_all_fainted")
    a.mov_imm(0, 2)     # pending_end = 2 (LOSE)
    a.strb_imm(0, 8, 0x0A)

    a.label("ebt_turn_end")
    a.mov_imm(0, 6)     # phase = 6 (LOG)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # calc_plating_chance(R0=foe_ptr, R1=item_idx) -> R0:R1 = chance_f64 (or 0:0)
    a.label("calc_plating_chance")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(4, 0) # R4 = foe_ptr
    a.mov_reg(5, 1) # R5 = item_idx

    # Look up item in Table 8 (28 bytes per entry)
    a.mov_imm(0, 28)
    a.mul(6, 5, 0)
    a.mov_imm(0, tables_rom_addrs[8])
    a.add_reg(6, 0, 6) # R6 = item_ptr
    a.ldrb_imm(0, 6, 0) # item.kind
    a.cmp_imm(0, 0)     # 0 == 'plate'
    a.b("cpc_zero", cond=0x1)

    # Look up species in Table 4 (56 bytes per entry)
    a.ldrb_imm(0, 4, 4) # foe.speciesId
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(7, 0, 1)
    a.mov_imm(0, tables_rom_addrs[4])
    a.add_reg(7, 0, 7) # R7 = sp_ptr

    # Check sp.nightOnly (+10) && !state.isNight (0x0200002C)
    a.mov_imm(8, 0x02000000)
    a.ldrb_imm(0, 7, 10) # nightOnly
    a.ldrb_imm(1, 8, 0x2C) # isNight
    a.cmp_imm(0, 0)
    a.b("cpc_chk_tier", cond=0x0)
    a.cmp_imm(1, 0)
    a.b("cpc_zero", cond=0x0)

    a.label("cpc_chk_tier")
    a.ldrb_imm(0, 7, 11) # sp.minTier
    a.cmp_imm(0, 0)
    a.b("cpc_calc", cond=0x0)
    a.ldrb_imm(1, 6, 1)  # item.tier
    a.cmp_reg(1, 0)
    a.b("cpc_zero", cond=0x3) # BCC (item.tier < sp.minTier)

    a.label("cpc_calc")
    # hpFactor = max(0.1, (3 * maxHp - 2 * curHp) / (3 * maxHp))
    a.ldrh_imm(0, 4, 0x0A) # maxHp
    a.add_reg(8, 0, 0, shift_imm=1, shift_type=0) # R8 = 3 * maxHp
    a.ldrh_imm(1, 4, 0x08) # curHp
    a.sub_reg(0, 8, 1, shift_imm=1, shift_type=0) # R0 = 3 * maxHp - 2 * curHp
    a.bl("f64_from_u32")
    a.mov_reg(9, 0); a.mov_reg(10, 1)
    a.mov_reg(0, 8)
    a.bl("f64_from_u32")
    a.mov_reg(2, 0); a.mov_reg(3, 1)
    a.mov_reg(0, 9); a.mov_reg(1, 10)
    a.bl("f64_div") # R0:R1 = (3*maxHp - 2*curHp) / (3*maxHp)
    # Compare with 0.1 (0x3FB99999, 0x9999999A)
    a.mov_imm(2, 0x9999999A)
    a.mov_imm(3, 0x3FB99999)
    a.cmp_reg(1, 3)
    a.cmp_reg(0, 2, cond=0x0)
    a.mov_reg(0, 2, cond=0x3)
    a.mov_reg(1, 3, cond=0x3)
    a.mov_reg(9, 0); a.mov_reg(10, 1) # R9:R10 = hpFactor

    # raw = sp.catchRate * item.plateBonus
    a.ldr_imm(0, 7, 24) # sp.catchRate lo
    a.ldr_imm(1, 7, 28) # sp.catchRate hi
    a.ldr_imm(2, 6, 20) # item.plateBonus lo
    a.ldr_imm(3, 6, 24) # item.plateBonus hi
    a.bl("f64_mul")
    # * hpFactor (R9:R10)
    a.mov_reg(2, 9); a.mov_reg(3, 10)
    a.bl("f64_mul")

    # * statusBonus: status == 5 ('Appetized') ? 1.5 : (status != 0 ? 1.3 : 1.0)
    a.ldrb_imm(4, 4, 6) # foe.status
    a.mov_imm(2, 0)
    a.mov_imm(3, 0x3FF00000) # 1.0
    a.cmp_imm(4, 0)
    a.mov_imm(2, 0xCCCCCCCD, cond=0x1)
    a.mov_imm(3, 0x3FF4CCCC, cond=0x1) # 1.3
    a.cmp_imm(4, 5)
    a.mov_imm(2, 0, cond=0x0)
    a.mov_imm(3, 0x3FF80000, cond=0x0) # 1.5
    a.bl("f64_mul")

    # * favBonus: b.used_fav_treat ? 1.6 : 1.0
    a.mov_imm(4, 0x02001100)
    a.ldrb_imm(4, 4, 7) # used_fav_treat
    a.cmp_imm(4, 0)
    a.mov_imm(2, 0, cond=0x0); a.mov_imm(3, 0x3FF00000, cond=0x0)
    a.mov_imm(2, 0x9999999A, cond=0x1); a.mov_imm(3, 0x3FF99999, cond=0x1) # 1.6
    a.bl("f64_mul")

    # * timeBonus: (sp.nightOnly && isNight) ? 1.35 : 1.0
    a.ldrb_imm(4, 7, 10) # sp.nightOnly
    a.mov_imm(5, 0x02000000)
    a.ldrb_imm(5, 5, 0x2C) # isNight
    a.and_reg(4, 4, 5, s=1)
    a.mov_imm(2, 0, cond=0x0); a.mov_imm(3, 0x3FF00000, cond=0x0)
    a.mov_imm(2, 0x9999999A, cond=0x1); a.mov_imm(3, 0x3FF59999, cond=0x1) # 1.35
    a.bl("f64_mul")

    # Clamp to min(0.95, raw): 0.95 = 0x3FEE666666666666
    a.mov_imm(2, 0x66666666)
    a.mov_imm(3, 0x3FEE6666)
    a.cmp_reg(1, 3)
    a.cmp_reg(0, 2, cond=0x0)
    a.mov_reg(0, 2, cond=0x8) # BHI -> 0.95
    a.mov_reg(1, 3, cond=0x8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("cpc_zero")
    a.mov_imm(0, 0)
    a.mov_imm(1, 0)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # use_plating_item(R0=item_idx)
    a.label("use_plating_item")
    a.push([4, 5, 6, 7, 8, 9, 10, 14])
    a.mov_reg(6, 0) # R6 = item_idx
    a.mvn_imm(1, 0) # -1
    a.bl("bag_add") # bag[item_idx]--

    a.mov_imm(8, 0x02001100) # R8 = BSTATE
    a.ldrb_imm(0, 8, 5) # player_idx
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.mov_imm(2, 0x020000B4)
    a.add_reg(4, 2, 0)       # R4 = player_ptr
    a.ldrb_imm(0, 8, 4) # foe_idx
    a.mul(0, 0, 1)
    a.add_imm(5, 8, 0x10)
    a.add_reg(5, 5, 0)       # R5 = foe_ptr

    # Look up item in Table 8 (28B)
    a.mov_imm(0, 28)
    a.mul(7, 6, 0)
    a.mov_imm(0, tables_rom_addrs[8])
    a.add_reg(7, 0, 7)       # R7 = item_ptr
    a.ldrb_imm(0, 7, 0)      # item.kind
    a.cmp_imm(0, 4)          # 4 == 'treat'
    a.b("upi_plate", cond=0x1)
    # Treat used!
    a.mov_imm(0, 1)
    a.strb_imm(0, 8, 7)      # b.used_fav_treat = 1
    a.ldrh_imm(3, 5, 0x08)
    a.and_imm(3, 3, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.mov_imm(0, 4)          # TREAT_USED
    a.mov_reg(1, 6)
    a.mov_imm(2, 0)
    a.bl("log_battle_event")
    a.mov_reg(0, 5)
    a.mov_reg(1, 4)
    a.bl("do_foe_attack")
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)      # phase = LOG
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])

    a.label("upi_plate")
    a.mov_reg(0, 5)
    a.mov_reg(1, 6)
    a.bl("calc_plating_chance") # R0:R1 = chance_f64
    a.orr_reg(2, 0, 1, s=1)
    a.b("upi_zero_chance", cond=0x0)
    a.mov_reg(9, 0); a.mov_reg(10, 1) # R9:R10 = chance_f64
    a.bl("game_rng_next")
    a.bl("f64_from_mulberry") # R0:R1 = rng()
    a.cmp_reg(1, 10)
    a.cmp_reg(0, 9, cond=0x0)
    a.b("upi_plate_fail", cond=0x2) # BCS (rng() >= chance)

    # Plating succeeded!
    a.ldrb_imm(0, 5, 4) # foe.speciesId
    a.bl("mark_caught")
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(1, 0, 0x0B0) # partyCount
    a.cmp_imm(1, 6)
    a.b("upi_to_box", cond=0x2)
    # Add to party[partyCount]
    a.mov_imm(2, 48)
    a.mul(2, 1, 2)
    a.add_imm(1, 1, 1)
    a.strb_imm(1, 0, 0x0B0)
    a.add_imm(0, 0, 0x0B4)
    a.add_reg(0, 0, 2)
    for off in range(0, 48, 4):
        a.ldr_imm(3, 5, off)
        a.str_imm(3, 0, off)
    a.b("upi_caught_log")

    a.label("upi_to_box")
    a.ldrb_imm(1, 0, 0x0B1) # boxCount
    a.cmp_imm(1, 151)
    a.b("upi_caught_log", cond=0x2)
    a.mov_imm(2, 24)
    a.mul(2, 1, 2)
    a.add_imm(1, 1, 1)
    a.strb_imm(1, 0, 0x0B1)
    a.mov_imm(3, 0x020001D4)
    a.add_reg(0, 3, 2) # dst box slot (24B)
    # Pack 48B PartyMon at R5 into 24B BoxMon at R0
    a.ldr_imm(1, 5, 0x00); a.str_imm(1, 0, 0x00) # uid
    a.ldr_imm(1, 5, 0x04); a.str_imm(1, 0, 0x04) # spId, level, status
    a.ldrb_imm(1, 5, 0x12); a.strb_imm(1, 0, 0x07) # moveCount
    a.ldr_imm(1, 5, 0x08); a.str_imm(1, 0, 0x08) # hp, maxHp
    a.ldr_imm(1, 5, 0x0C); a.str_imm(1, 0, 0x0C) # atk, def
    a.ldrh_imm(1, 5, 0x10); a.strh_imm(1, 0, 0x10) # spd
    a.ldr_imm(1, 5, 0x14)
    a.mov_reg(1, 1, shift_imm=3, shift_type=1)
    a.strh_imm(1, 0, 0x12) # xpDiv8
    a.ldr_imm(1, 5, 0x1C); a.str_imm(1, 0, 0x14) # moveIds[4]

    a.label("upi_caught_log")
    a.ldrh_imm(3, 5, 0x08)
    a.and_imm(3, 3, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.orr_imm(3, 3, 0x20) # bit 5 = caught!
    a.mov_imm(0, 3)       # PLATE_ATTEMPT
    a.mov_reg(1, 6)
    a.mov_imm(2, 0)
    a.bl("log_battle_event")
    a.mov_imm(0, 4)       # pending_end = 4 (CAUGHT)
    a.strb_imm(0, 8, 0x0A)
    a.mov_imm(0, 6)       # phase = 6 (LOG)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])

    a.label("upi_zero_chance")
    a.ldrh_imm(3, 5, 0x08)
    a.and_imm(3, 3, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.mov_imm(0, 3)
    a.mov_reg(1, 6)
    a.mov_imm(2, 0)
    a.bl("log_battle_event")
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])

    a.label("upi_plate_fail")
    a.ldrh_imm(3, 5, 0x08)
    a.and_imm(3, 3, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.mov_imm(0, 3)
    a.mov_reg(1, 6)
    a.mov_imm(2, 0)
    a.bl("log_battle_event")
    a.mov_reg(0, 5)
    a.mov_reg(1, 4)
    a.bl("do_foe_attack")
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])
    a.flush_literals()

    # Helper: build_bag_filter(R0=mode: 0=all, 1=plate_or_treat, 2=heal_cure_revive, R1=dst_u8_array) -> R0=count
    a.label("build_bag_filter")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_reg(4, 0) # mode
    a.mov_reg(5, 1) # dst_ptr
    a.mov_imm(6, 0) # count = 0
    a.mov_imm(7, 0x02001058) # bag_order
    a.ldrb_imm(8, 7, 25)     # bag_order_len
    a.mov_imm(9, 0)          # i = 0
    a.label("bbf_loop")
    a.cmp_reg(9, 8)
    a.b("bbf_done", cond=0x2)
    a.add_reg(0, 7, 9)
    a.ldrb_imm(0, 0, 0)      # R0 = item_idx
    a.mov_imm(1, 0x0200007E)
    a.add_reg(1, 1, 0, shift_imm=1, shift_type=0)
    a.ldrh_imm(1, 1, 0)      # qty
    a.cmp_imm(1, 0)
    a.b("bbf_next", cond=0x0)
    a.cmp_imm(4, 0)
    a.b("bbf_match", cond=0x0)
    # Check item.kind in Table 8 (28B)
    a.mov_imm(2, 28)
    a.mul(2, 0, 2)
    a.mov_imm(3, tables_rom_addrs[8])
    a.add_reg(2, 3, 2)
    a.ldrb_imm(2, 2, 0)      # kind (0=plate, 1=heal, 2=cure, 3=revive, 4=treat, 5=recipe, 6=key)
    a.cmp_imm(4, 1)
    a.b("bbf_chk_hcr", cond=0x1)
    # mode 1: plate (0) or treat (4)
    a.cmp_imm(2, 0)
    a.cmp_imm(2, 4, cond=0x1)
    a.b("bbf_match", cond=0x0)
    a.b("bbf_next")
    a.label("bbf_chk_hcr")
    # mode 2: heal (1), cure (2), or revive (3)
    a.cmp_imm(2, 1)
    a.cmp_imm(2, 2, cond=0x1)
    a.cmp_imm(2, 3, cond=0x1)
    a.b("bbf_next", cond=0x1)
    a.label("bbf_match")
    a.add_reg(1, 5, 6)
    a.strb_imm(0, 1, 0)
    a.add_imm(6, 6, 1)
    a.label("bbf_next")
    a.add_imm(9, 9, 1)
    a.b("bbf_loop")
    a.label("bbf_done")
    a.mov_reg(0, 6)
    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # handle_battle_input(R0=btn: 0=A, 1=B, 2=SELECT, 3=START, 4=RIGHT, 5=LEFT, 6=UP, 7=DOWN)
    a.label("handle_battle_input")
    a.push([4, 5, 6, 7, 8, 9, 10, 14])
    a.sub_imm(13, 13, 32) # scratch for filtered item list
    a.mov_reg(4, 0)       # R4 = btn
    a.mov_imm(5, 0x02001100) # R5 = BSTATE
    a.ldrb_imm(6, 5, 8)   # R6 = b.phase (1=MAIN, 2=FIGHT, 3=PLATE, 4=BAG, 5=PARTY, 6=LOG)
    a.ldrb_imm(7, 5, 9)   # R7 = b.cursor

    # Phase 6: LOG
    a.cmp_imm(6, 6)
    a.b("hbi_chk_main", cond=0x1)
    a.cmp_imm(4, 0) # A
    a.cmp_imm(4, 1, cond=0x1) # B
    a.b("hbi_ret", cond=0x1)
    a.ldrb_imm(0, 5, 0x0A) # pending_end
    a.cmp_imm(0, 0)
    a.b("hbi_log_to_main", cond=0x0)
    # If pending_end == 2 (LOSE), heal_party() just like finishBattle("LOSE")
    a.cmp_imm(0, 2)
    a.bl("heal_party", cond=0x0)
    # finishBattle: set active=0, phase=0, screen=OVERWORLD(3)
    a.mov_imm(1, 0)
    a.strb_imm(1, 5, 0)
    a.strb_imm(1, 5, 8)
    a.mov_imm(1, 0x02001000)
    a.mov_imm(2, 3)
    a.strb_imm(2, 1, 0x20)
    a.b("hbi_ret")
    a.label("hbi_log_to_main")
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 8) # phase = MAIN
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 9) # cursor = 0
    a.b("hbi_ret")

    # Phase 1: MAIN
    a.label("hbi_chk_main")
    a.cmp_imm(6, 1)
    a.b("hbi_chk_fight", cond=0x1)
    a.cmp_imm(4, 1) # B?
    a.b("hbi_main_not_b", cond=0x1)
    a.ldrb_imm(0, 5, 1) # is_wild
    a.cmp_imm(0, 0)
    a.b("hbi_ret", cond=0x0)
    # Wild run!
    a.mov_imm(0, 7) # RUN event
    a.mov_imm(1, 0)
    a.mov_imm(2, 0)
    a.mov_imm(3, 0)
    a.bl("log_battle_event")
    a.mov_imm(0, 3) # pending_end = RUN
    a.strb_imm(0, 5, 0x0A)
    a.mov_imm(0, 6) # phase = LOG
    a.strb_imm(0, 5, 8)
    a.b("hbi_ret")

    a.label("hbi_main_not_b")
    a.cmp_imm(4, 4); a.cmp_imm(4, 5, cond=0x1) # RIGHT or LEFT
    a.eor_imm(7, 7, 1, cond=0x0)
    a.strb_imm(7, 5, 9, cond=0x0)
    a.b("hbi_ret", cond=0x0)
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1) # UP or DOWN
    a.eor_imm(7, 7, 2, cond=0x0)
    a.strb_imm(7, 5, 9, cond=0x0)
    a.b("hbi_ret", cond=0x0)
    a.cmp_imm(4, 0) # A
    a.b("hbi_ret", cond=0x1)
    a.cmp_imm(7, 0) # cursor == 0 -> FIGHT
    a.mov_imm(0, 2, cond=0x0)
    a.b("hbi_set_phase", cond=0x0)
    a.cmp_imm(7, 1) # cursor == 1 -> PLATE
    a.b("hbi_main_c2", cond=0x1)
    a.ldrb_imm(0, 5, 1) # is_wild
    a.cmp_imm(0, 0)
    a.mov_imm(0, 6, cond=0x0) # if trainer: phase = LOG
    a.strb_imm(0, 5, 8, cond=0x0)
    a.b("hbi_ret", cond=0x0)
    a.mov_imm(0, 3) # phase = PLATE
    a.b("hbi_set_phase")
    a.label("hbi_main_c2")
    a.cmp_imm(7, 2)
    a.mov_imm(0, 4, cond=0x0) # BAG
    a.mov_imm(0, 5, cond=0x1) # PARTY
    a.label("hbi_set_phase")
    a.strb_imm(0, 5, 8)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 9)
    a.b("hbi_ret")

    # Phase 2: FIGHT
    a.label("hbi_chk_fight")
    a.cmp_imm(6, 2)
    a.b("hbi_chk_plate", cond=0x1)
    a.ldrb_imm(0, 5, 5) # player_idx
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.mov_imm(1, 0x020000B4)
    a.add_reg(8, 1, 0)  # R8 = player_ptr
    a.ldrh_imm(9, 8, 0x12) # R9 = mon.moveCount

    a.cmp_imm(4, 1) # B
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(4, 4); a.cmp_imm(4, 7, cond=0x1) # RIGHT or DOWN
    a.b("hbi_fight_ul", cond=0x1)
    a.add_imm(0, 7, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_fight_ul")
    a.cmp_imm(4, 5); a.cmp_imm(4, 6, cond=0x1) # LEFT or UP
    a.b("hbi_fight_a", cond=0x1)
    a.add_reg(0, 7, 9)
    a.sub_imm(0, 0, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_fight_a")
    a.cmp_imm(4, 0) # A
    a.b("hbi_ret", cond=0x1)
    a.add_reg(0, 8, 7)
    a.ldrb_imm(1, 0, 0x20) # movePps[cursor]
    a.cmp_imm(1, 0)
    a.b("hbi_fight_no_pp", cond=0x0)
    a.sub_imm(1, 1, 1)
    a.strb_imm(1, 0, 0x20) # pp--
    a.ldrb_imm(0, 0, 0x1C) # moveId
    a.bl("execute_battle_turn")
    a.b("hbi_ret")
    a.label("hbi_fight_no_pp")
    # Check if all moves have pp == 0
    a.mov_imm(0, 0)
    a.label("hbi_chk_all_pp")
    a.cmp_reg(0, 9)
    a.b("hbi_struggle", cond=0x2)
    a.add_reg(1, 8, 0)
    a.ldrb_imm(1, 1, 0x20)
    a.cmp_imm(1, 0)
    a.b("hbi_ret", cond=0x1) # some move has PP > 0, do nothing
    a.add_imm(0, 0, 1)
    a.b("hbi_chk_all_pp")
    a.label("hbi_struggle")
    a.mov_imm(0, 0)
    a.bl("execute_battle_turn")
    a.b("hbi_ret")

    # Phase 3: PLATE
    a.label("hbi_chk_plate")
    a.cmp_imm(6, 3)
    a.b("hbi_chk_bag", cond=0x1)
    a.mov_imm(0, 1)
    a.mov_reg(1, 13)
    a.bl("build_bag_filter")
    a.mov_reg(9, 0) # R9 = plates.length
    a.cmp_imm(4, 1) # B
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(9, 0) # plates.length == 0
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(4, 7) # DOWN
    a.b("hbi_plate_up", cond=0x1)
    a.add_imm(0, 7, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_plate_up")
    a.cmp_imm(4, 6) # UP
    a.b("hbi_plate_a", cond=0x1)
    a.add_reg(0, 7, 9)
    a.sub_imm(0, 0, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_plate_a")
    a.cmp_imm(4, 0) # A
    a.b("hbi_ret", cond=0x1)
    a.add_reg(0, 13, 7)
    a.ldrb_imm(0, 0, 0) # plates[b.cursor]
    a.bl("use_plating_item")
    a.b("hbi_ret")

    # Phase 4: BAG
    a.label("hbi_chk_bag")
    a.cmp_imm(6, 4)
    a.b("hbi_chk_party", cond=0x1)
    a.mov_imm(0, 2)
    a.mov_reg(1, 13)
    a.bl("build_bag_filter")
    a.mov_reg(9, 0) # R9 = heals.length
    a.cmp_imm(4, 1)
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(9, 0)
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(4, 7) # DOWN
    a.b("hbi_bag_up", cond=0x1)
    a.add_imm(0, 7, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_bag_up")
    a.cmp_imm(4, 6) # UP
    a.b("hbi_bag_a", cond=0x1)
    a.add_reg(0, 7, 9)
    a.sub_imm(0, 0, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_bag_a")
    a.cmp_imm(4, 0) # A
    a.b("hbi_ret", cond=0x1)
    a.add_reg(0, 13, 7)
    a.ldrb_imm(8, 0, 0) # R8 = itemId = heals[b.cursor]
    # Look up item in Table 8 (28B)
    a.mov_imm(0, 28)
    a.mul(9, 8, 0)
    a.mov_imm(0, tables_rom_addrs[8])
    a.add_reg(9, 0, 9) # R9 = item_ptr

    a.ldrb_imm(0, 5, 5) # player_idx
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.mov_imm(1, 0x020000B4)
    a.add_reg(10, 1, 0) # R10 = mon_ptr

    a.ldrb_imm(0, 9, 0) # item.kind (1=heal, 2=cure, 3=revive)
    a.cmp_imm(0, 1)
    a.b("hbi_bag_cure", cond=0x1)
    # heal: mon.hp = min(mon.maxHp, mon.hp + it.healHp)
    a.ldrh_imm(1, 10, 0x08) # hp
    a.ldrh_imm(2, 10, 0x0A) # maxHp
    a.ldrh_imm(3, 9, 2)     # healHp
    a.add_reg(1, 1, 3)
    a.cmp_reg(1, 2)
    a.mov_reg(1, 2, cond=0x8)
    a.strh_imm(1, 10, 0x08)
    a.cmp_imm(8, 7)         # itemId == 7 ('grand_feast')?
    a.mov_imm(1, 0, cond=0x0)
    a.strb_imm(1, 10, 0x06, cond=0x0) # mon.status = null
    a.b("hbi_bag_consume")

    a.label("hbi_bag_cure")
    a.cmp_imm(0, 2)
    a.b("hbi_bag_revive", cond=0x1)
    a.mov_imm(1, 0)
    a.strb_imm(1, 10, 0x06)
    a.b("hbi_bag_consume")

    a.label("hbi_bag_revive")
    # Find first party member with hp <= 0
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(1, 0, 0x0B0) # partyCount
    a.add_imm(2, 0, 0x0B4)
    a.mov_imm(3, 0)
    a.label("hbi_rev_loop")
    a.cmp_reg(3, 1)
    a.b("hbi_bag_consume", cond=0x2)
    a.ldrh_imm(0, 2, 0x08)
    a.cmp_imm(0, 0)
    a.b("hbi_rev_found", cond=0x0)
    a.add_imm(2, 2, 48)
    a.add_imm(3, 3, 1)
    a.b("hbi_rev_loop")
    a.label("hbi_rev_found")
    a.ldrh_imm(0, 2, 0x0A) # fainted.maxHp
    a.mov_reg(0, 0, shift_imm=1, shift_type=1) # Math.floor(maxHp * 0.5) = maxHp >> 1
    a.strh_imm(0, 2, 0x08)

    a.label("hbi_bag_consume")
    a.mov_reg(0, 8)
    a.mvn_imm(1, 0) # -1
    a.bl("bag_add")
    # Log BAG_ITEM event (kind=5, id=R8)
    a.ldrh_imm(3, 10, 0x08)
    a.and_imm(3, 3, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.mov_imm(0, 5)
    a.mov_reg(1, 8)
    a.ldrh_imm(2, 9, 2) # healHp
    a.bl("log_battle_event")
    # do_foe_attack(foe, mon)
    a.ldrb_imm(0, 5, 4) # foe_idx
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.add_imm(0, 0, 0x10)
    a.add_reg(0, 5, 0)  # foe_ptr
    a.mov_reg(1, 10)    # mon_ptr
    a.bl("do_foe_attack")
    a.mov_imm(0, 6)
    a.strb_imm(0, 5, 8) # phase = LOG
    a.b("hbi_ret")

    # Phase 5: PARTY
    a.label("hbi_chk_party")
    a.cmp_imm(6, 5)
    a.b("hbi_ret", cond=0x1)
    a.cmp_imm(4, 1) # B
    a.b("hbi_to_main", cond=0x0)
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(9, 0, 0x0B0) # R9 = party.length
    a.cmp_imm(4, 7) # DOWN
    a.b("hbi_party_up", cond=0x1)
    a.add_imm(0, 7, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_party_up")
    a.cmp_imm(4, 6) # UP
    a.b("hbi_party_a", cond=0x1)
    a.add_reg(0, 7, 9)
    a.sub_imm(0, 0, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_party_a")
    a.cmp_imm(4, 0) # A
    a.b("hbi_ret", cond=0x1)
    a.cmp_reg(7, 9)
    a.b("hbi_ret", cond=0x2)
    a.ldrb_imm(0, 5, 5) # player_idx
    a.cmp_reg(7, 0)
    a.b("hbi_ret", cond=0x0) # cursor == player_idx
    a.mov_imm(1, 48)
    a.mul(2, 7, 1)
    a.mov_imm(3, 0x020000B4)
    a.add_reg(8, 3, 2)  # R8 = target_ptr
    a.ldrh_imm(0, 8, 0x08) # target.hp
    a.cmp_imm(0, 0)
    a.b("hbi_ret", cond=0x0)
    # Switch to cursor!
    a.strb_imm(7, 5, 5) # b.player_idx = b.cursor
    # Log SWITCH event (kind=6, id=R7)
    a.and_imm(3, 0, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.mov_imm(0, 6)
    a.mov_reg(1, 7)
    a.mov_imm(2, 0)
    a.bl("log_battle_event")
    # do_foe_attack(foe, target)
    a.ldrb_imm(0, 5, 4) # foe_idx
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.add_imm(0, 0, 0x10)
    a.add_reg(0, 5, 0)  # foe_ptr
    a.mov_reg(1, 8)     # target_ptr
    a.bl("do_foe_attack")
    a.mov_imm(0, 6)
    a.strb_imm(0, 5, 8) # phase = LOG
    a.b("hbi_ret")

    a.label("hbi_to_main")
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 8)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 9)

    a.label("hbi_ret")
    a.add_imm(13, 13, 32)
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])
    a.flush_literals()



_CACHED_EXT = None

def get_extracted_reference():
    global _CACHED_EXT
    if _CACHED_EXT is None:
        _CACHED_EXT = extract_reference_data()
    return _CACHED_EXT

def build_rom(out_path=OUT_ROM_PATH, control_mode=None):
    ext_dict = get_extracted_reference()
    tables, pool = build_all_rom_tables_inline(ext_dict, control_mode=control_mode)

    # Build Master 256-color BGR555 Palette (0..15 = TILE_PALETTE, 16..89 = UI, Species, Chars)
    tile_pal_hex = ['#101420', '#181820', '#58a848', '#408830', '#78c860', '#d8b880', '#b89860', '#4888c8', '#70b0e8', '#c85838', '#e8e0d0', '#885030', '#386830', '#f0c040', '#a0a8b0', '#f8f8f0']
    master_cols = [c.lower() for c in tile_pal_hex]
    ui_hex = [
        "#182030", "#f8e888", "#a8dadc", "#98d830", "#c0c8d0",
        "#708090", "#506070", "#e63946", "#52b788", "#4cc9f0", "#e8a850", "#60c8f8",
        "#1a1e34", "#141c2c", "#283854", "#182234", "#304060", "#1a2438", "#243448", "#385068", "#404858", "#101824", "#101424"
    ]
    for c in ui_hex:
        if c.lower() not in master_cols:
            master_cols.append(c.lower())
    for sp in ext_dict["beatsts_py"]:
        for c in sp["palette"]:
            if c and c.lower() not in master_cols:
                master_cols.append(c.lower())
    for k in ext_dict["char_sprites"]:
        for d in ("down", "up", "left", "right"):
            for f in range(3):
                for c in ext_dict["char_grids_py"][k][d][f]:
                    if c and c.lower() not in master_cols:
                        master_cols.append(c.lower())

    master_pal_bytes = bytearray(512)
    for idx, c in enumerate(master_cols[:256]):
        struct.pack_into("<H", master_pal_bytes, idx * 2, to_bgr555(c))

    col_idx_of = {c: i for i, c in enumerate(master_cols)}

    # Assemble ARM7TDMI Engine
    a = ArmAsm(0x08000000)
    # 0x08000000..0x080000BF: 192-byte GBA Cartridge Header
    a.b("rom_entry")
    a.emit_bytes(b"\x00" * (0xC0 - 4))
    # 0x080000C0: "SRAM_V113\x00\x00\x00" (12 bytes) -> puts tableDirRomAddr at 0x080000CC or 0x080000C4!
    # Wait: MAILBOX.md says fixed ROM offset 0x080000C4 has tableDirRomAddr!
    # So at 0x080000C0 we put magic 0x42454154 ("TAEB"), at 0x080000C4 we put tableDirRomAddr (0x08020000),
    # and at 0x080000C8 we put "SRAM_V113\x00\x00\x00"!
    TABLE_DIR_ROM_ADDR = 0x08020000
    a.emit32(0x42454154)
    a.emit32(TABLE_DIR_ROM_ADDR)
    a.emit_bytes(b"SRAM_V113\x00\x00\x00")
    a.align(4)

    # Reserve Table addresses starting at TABLE_DIR_ROM_ADDR (0x08020000)
    # Table Directory itself is at 0x08020000:
    #   +0x00: magic 0x52494454 ("TDIR")
    #   +0x04: count = 17
    #   +0x08: 17 * 16 bytes (id, romOffset, byteLength, itemCount) = 272 bytes -> ends at 0x08020118
    table_addrs = {}
    off_cur = TABLE_DIR_ROM_ADDR + 8 + len(tables) * 16
    off_cur = (off_cur + 15) & ~15
    for k in sorted(tables.keys()):
        name, b_data, cnt = tables[k]
        table_addrs[k] = off_cur
        off_cur = (off_cur + len(b_data) + 3) & ~3

    master_pal_rom_addr = off_cur
    off_cur = (off_cur + len(master_pal_bytes) + 3) & ~3

    # Build pre-indexed 8bpp 8x8-tiled species front/back sprites (151 * 2 * 1024 = 309,248 B) for 4-DMA3 hardware blit
    sp_pal_map_bytes = bytearray()
    for sp in ext_dict["beatsts_py"]:
        pmap = [0] + [col_idx_of[c.lower()] for c in sp["palette"][1:]]
        for grid in (sp["front"], sp["back"]):
            for ty in range(4):
                for tx in range(4):
                    for py in range(8):
                        for px in range(8):
                            sp_pal_map_bytes.append(pmap[grid[(ty * 8 + py) * 32 + (tx * 8 + px)] & 0xF])
    sp_pal_map_rom_addr = off_cur
    off_cur = (off_cur + len(sp_pal_map_bytes) + 3) & ~3


    # Build 624-byte initial_npc_xy table for 1-DMA3 init_all_npc_xy
    init_npc_xy_bytes = bytearray(624)
    g_idx = 0
    for mid in list(ext_dict["maps"].keys()):
        for n in ext_dict["maps"][mid].get("npcs", []):
            init_npc_xy_bytes[g_idx * 2] = n["x"] & 0xFF
            init_npc_xy_bytes[g_idx * 2 + 1] = n["y"] & 0xFF
            g_idx += 1
    init_npc_xy_rom_addr = off_cur
    off_cur = (off_cur + 624 + 3) & ~3

    # Build 128 BG0 boot tiles (8,192 bytes) at bg0_boot_tiles_rom_addr
    bg0_boot_tiles = bytearray(128 * 64)
    solid_map = {
        1: col_idx_of["#141c2c"],
        2: col_idx_of["#182030"],
        3: col_idx_of["#1a1e34"],
        4: col_idx_of["#243448"],
        5: col_idx_of["#385068"],
        6: col_idx_of["#f8f8f0"],
        7: col_idx_of["#f0c040"],
        8: col_idx_of["#f8e888"],
        9: col_idx_of["#a8dadc"],
        10: col_idx_of["#98d830"],
        11: col_idx_of["#52b788"],
        12: col_idx_of["#e63946"],
    }
    for t_i, c_v in solid_map.items():
        bg0_boot_tiles[t_i * 64 : (t_i + 1) * 64] = bytes([c_v]) * 64
    fg_c = col_idx_of["#f8f8f0"]
    bg_c = col_idx_of["#141c2c"]
    sans_b = ext_dict["font_sans_bytes"]
    for g_i in range(96):
        t_off = (32 + g_i) * 64
        for r_i in range(8):
            b_row = sans_b[g_i * 8 + r_i]
            for c_i in range(8):
                bg0_boot_tiles[t_off + r_i * 8 + c_i] = fg_c if (b_row & (1 << (7 - c_i))) else bg_c
    bg0_boot_tiles_rom_addr = off_cur
    off_cur = (off_cur + len(bg0_boot_tiles) + 3) & ~3

    # Emit Soft-Float & Core/Battle Engine
    emit_softfloat(a)
    emit_core_and_battle(a, table_addrs, control_mode=control_mode)

    # Emit SRAM Save/Load & FNV-1a Checksum Engine
    # fnv1a_32(R0=ptr_aligned4, R1=len_mult4) -> R0=hash (reads 1 32-bit word per 4 bytes!)
    a.label("fnv1a_32")
    a.push([2, 3, 4, 5, 14])
    a.mov_reg(2, 0) # ptr
    a.mov_reg(3, 1) # len
    a.mov_imm(0, 0x811C9DC5)
    a.mov_imm(4, 0x01000193)
    a.label("fnv_loop")
    a.cmp_imm(3, 0)
    a.b("fnv_done", cond=0x0)
    a.ldr_imm(5, 2, 0)
    a.add_imm(2, 2, 4)
    for sh_b in (0, 8, 16, 24):
        if sh_b == 0:
            a.and_imm(1, 5, 0xFF)
        else:
            a.mov_reg(1, 5, shift_imm=sh_b, shift_type=1)
            a.and_imm(1, 1, 0xFF)
        a.eor_reg(0, 0, 1)
        a.mul(0, 0, 4)
    a.sub_imm(3, 3, 4)
    a.b("fnv_loop")
    a.label("fnv_done")
    a.pop([2, 3, 4, 5, 15])
    a.flush_literals()

    # save_to_slot(R0=slotIdx 0..2) -> R0=1
    a.label("save_to_slot")
    a.push([4, 5, 6, 7, 14])
    a.and_imm(4, 0, 3)
    a.mov_imm(5, 0x02000000)
    # Preserve GSTATE[0x1C] (state.rngSeed) untouched, matching reference saveToSlot/loadFromSlot!
    # Single-pass word-read FNV-1a + SRAM write over 0x00C..0xFFF (4084 bytes)
    a.mov_imm(6, 0x0E000000)
    a.add_reg(6, 6, 4, shift_imm=12, shift_type=0)
    a.mov_imm(0, 0x811C9DC5)
    a.mov_imm(7, 0x01000193)
    a.mov_imm(1, 0x0C)
    a.label("sts_loop")
    a.add_reg(2, 5, 1)
    a.ldr_imm(3, 2, 0)
    a.add_reg(2, 6, 1)
    for b_i in range(4):
        if b_i > 0:
            a.mov_reg(3, 3, shift_imm=8, shift_type=1)
        a.strb_imm(3, 2, b_i)
        a.and_imm(14, 3, 0xFF)
        a.eor_reg(0, 0, 14)
        a.mul(0, 0, 7)
    a.add_imm(1, 1, 4)
    a.cmp_imm(1, 0x1000)
    a.b("sts_loop", cond=0x3)

    # Write header (0x000..0x00B) to GSTATE and SRAM
    a.str_imm(0, 5, 0x08) # checksum
    a.mov_imm(0, 0x54414542)
    a.str_imm(0, 5, 0x00)
    a.mov_imm(0, 0x22)
    a.strb_imm(0, 5, 0x04)
    a.strb_imm(4, 5, 0x05)
    a.mov_imm(0, 0)
    a.strh_imm(0, 5, 0x06)
    for b_i in range(12):
        a.ldrb_imm(0, 5, b_i)
        a.strb_imm(0, 6, b_i)
    a.mov_imm(0, 1)
    a.pop([4, 5, 6, 7, 15])
    a.flush_literals()

    # check_slot_valid(R0=slotIdx 0..2) -> R0=1 if valid else 0
    a.label("check_slot_valid")
    a.push([4, 5, 6, 7, 14])
    a.and_imm(4, 0, 3)
    a.mov_imm(5, 0x02002000)
    a.mov_imm(6, 0x0E000000)
    a.add_reg(6, 6, 4, shift_imm=12, shift_type=0)
    a.ldrb_imm(0, 6, 0)
    a.cmp_imm(0, 0x42)
    a.b("csv_invalid", cond=0x1)
    a.ldrb_imm(0, 6, 4)
    a.cmp_imm(0, 0x22)
    a.b("csv_invalid", cond=0x1)
    a.mov_imm(1, 0)
    a.label("csv_copy")
    a.add_reg(2, 6, 1)
    a.ldrb_imm(0, 2, 0)
    a.ldrb_imm(3, 2, 1)
    a.orr_reg(0, 0, 3, shift_imm=8, shift_type=0)
    a.ldrb_imm(3, 2, 2)
    a.orr_reg(0, 0, 3, shift_imm=16, shift_type=0)
    a.ldrb_imm(3, 2, 3)
    a.orr_reg(0, 0, 3, shift_imm=24, shift_type=0)
    a.add_reg(2, 5, 1)
    a.str_imm(0, 2, 0)
    a.add_imm(1, 1, 4)
    a.cmp_imm(1, 0x1000)
    a.b("csv_copy", cond=0x3)

    a.ldr_imm(0, 5, 0x00)
    a.mov_imm(1, 0x54414542)
    a.cmp_reg(0, 1)
    a.b("csv_invalid", cond=0x1)
    a.ldr_imm(6, 5, 0x08)
    a.add_imm(0, 5, 0x0C)
    a.mov_imm(1, 0x1000 - 0x0C)
    a.bl("fnv1a_32")
    a.cmp_reg(0, 6)
    a.b("csv_invalid", cond=0x1)
    a.mov_imm(0, 1)
    a.pop([4, 5, 6, 7, 15])
    a.label("csv_invalid")
    a.mov_imm(0, 0)
    a.pop([4, 5, 6, 7, 15])
    a.flush_literals()

    # init_all_npc_xy(): 1 DMA3 copy of 156 words (624 bytes) from ROM to 0x02001800!
    a.label("init_all_npc_xy")
    a.mov_imm(0, init_npc_xy_rom_addr)
    a.mov_imm(1, 0x02001800)
    a.mov_imm(2, 0x04000000)
    a.str_imm(0, 2, 0xD4)
    a.str_imm(1, 2, 0xD8)
    a.mov_imm(0, 0x84000000 | 156)
    a.str_imm(0, 2, 0xDC)
    a.bx(14)
    a.flush_literals()
    # load_from_slot(R0=slotIdx 0..2) -> R0=1 if loaded else 0
    a.label("load_from_slot")
    a.push([4, 5, 6, 14])
    a.and_imm(4, 0, 3)
    a.mov_reg(0, 4)
    a.bl("check_slot_valid")
    a.cmp_imm(0, 0)
    a.b("lfs_fail", cond=0x0)
    # Copy 0x02002000..0x02002FFF -> 0x02000000..0x02000FFF
    a.mov_imm(5, 0x02002000)
    a.mov_imm(6, 0x02000000)
    a.mov_imm(1, 0)
    a.label("lfs_copy")
    a.add_reg(2, 5, 1)
    a.ldr_imm(0, 2, 0)
    a.add_reg(2, 6, 1)
    a.str_imm(0, 2, 0)
    a.add_imm(1, 1, 4)
    a.cmp_imm(1, 0x1000)
    a.b("lfs_copy", cond=0x3)

    # Rebuild bag_order from non-zero bagCounts (starting with standard initial order then remaining)
    a.mov_imm(5, 0x02001000)
    a.strb_imm(4, 5, 0x1F) # active_slot
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x1E) # has_state = 1
    a.ldr_imm(0, 6, 0x1C)  # rngSeed
    a.str_imm(0, 5, 0x00)  # rng_state = rngSeed
    a.mov_imm(0, 3)        # screen = OVERWORLD (3)
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x45) # dirty_ui = 1
    a.mov_imm(0, 0xFF)
    a.strb_imm(0, 5, 0x46) # force map VRAM reload

    # Initialize bag_order: clear bag_in_order & bag_order_len, then add items with count > 0
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x71) # bag_order_len = 0
    for i in range(25):
        a.strb_imm(0, 5, 0x72 + i)
    for init_id in [0, 1, 5, 10, 23, 24] + [x for x in range(25) if x not in (0, 1, 5, 10, 23, 24)]:
        a.ldrh_imm(1, 6, 0x7E + init_id * 2)
        a.cmp_imm(1, 0)
        a.mov_imm(0, init_id, cond=0x1)
        a.mov_imm(1, 0, cond=0x1)
        a.bl("bag_add", cond=0x1)

    a.bl("init_all_npc_xy")
    a.bl("play_map_music")
    a.mov_imm(0, 1)
    a.pop([4, 5, 6, 15])
    a.label("lfs_fail")
    a.mov_imm(0, 0)
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    # Audio Engine: play_music(R0=track_idx 0..17), play_sfx(R0=sfx_idx 0..11), step_audio_frame()
    # Precompute MIDI frequency table (128 halfwords for pulse and 128 halfwords for wave) in ROM!
    midi_pulse_freq = bytearray(256)
    midi_wave_freq = bytearray(256)
    for m_n in range(128):
        if m_n > 0:
            hz = 440.0 * (2.0 ** ((m_n - 69.0) / 12.0))
            fp = max(0, min(2045, int(round(2048.0 - 131072.0 / hz))))
            fw = max(0, min(2045, int(round(2048.0 - 65536.0 / hz))))
        else:
            fp = 0
            fw = 0
        struct.pack_into("<H", midi_pulse_freq, m_n * 2, fp)
        struct.pack_into("<H", midi_wave_freq, m_n * 2, fw)

    midi_pulse_rom_addr = off_cur
    off_cur = (off_cur + 256 + 3) & ~3
    midi_wave_rom_addr = off_cur
    off_cur = (off_cur + 256 + 3) & ~3


    a.label("play_music")
    a.push([4, 5, 6, 14])
    a.and_imm(4, 0, 0xFF)
    a.mov_imm(5, 0x02001300) # ASTATE
    a.ldrb_imm(1, 5, 0)      # current_track_id
    a.cmp_reg(1, 4)
    a.b("pm_done", cond=0x0) # already playing this track!
    a.strb_imm(4, 5, 0)      # current_track_id = R4
    a.mov_imm(0, 0)
    a.strh_imm(0, 5, 2)      # track_frame = 0
    # Look up track header in Table 14 (32 bytes per track)
    a.mov_imm(0, 32)
    a.mul(6, 4, 0)
    a.mov_imm(0, table_addrs[14])
    a.add_reg(6, 0, 6)       # R6 = track hdr ptr
    a.ldrh_imm(1, 6, 4)      # bpm
    a.strh_imm(1, 5, 6)      # track_bpm
    a.mov_imm(1, 1800)
    a.strh_imm(1, 5, 4)      # step_accum = 1800 (triggers step 0 on next tick!)
    a.ldrb_imm(1, 6, 6)      # loop
    a.strb_imm(1, 5, 8)
    for c_i in range(4):
        a.mov_imm(1, 0)
        a.strh_imm(1, 5, 0x0C + c_i * 2) # ch_note_idx[c_i] = 0
        a.strh_imm(1, 5, 0x14 + c_i * 2) # ch_rem_steps[c_i] = 0
        a.ldrb_imm(1, 6, 8 + c_i)        # ch_len
        a.strh_imm(1, 5, 0x1C + c_i * 2)
        a.ldr_imm(1, 6, 12 + c_i * 4)    # ch_off
        a.add_reg(1, 0, 1)               # table_addrs[14] + ch_off
        a.str_imm(1, 5, 0x24 + c_i * 4)  # ch_rom_ptr[c_i]
    a.label("pm_done")
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    a.label("play_map_music")
    a.push([4, 14])
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(0, 0, 0x28)   # state.mapId
    a.mov_imm(1, 40)
    a.mul(0, 0, 1)
    a.mov_imm(1, table_addrs[10])
    a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 15)     # map.music_idx
    a.bl("play_music")
    a.pop([4, 15])
    a.flush_literals()

    a.label("play_sfx")
    a.push([4, 14])
    a.mov_imm(4, 0x02001300)
    a.strb_imm(0, 4, 1)      # last_sfx_id = R0
    a.pop([4, 15])
    a.flush_literals()

    # step_audio_frame(): advances music sequencer and programs GBA PSG + logs to mailbox 0x0203FE00
    a.label("step_audio_frame")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_imm(4, 0x02001300) # R4 = ASTATE
    a.ldrb_imm(5, 4, 0)      # R5 = current_track_id
    a.cmp_imm(5, 18)
    a.b("saf_done", cond=0x2) # >= 18 (0xFF) -> no track playing
    a.ldrh_imm(6, 4, 2)      # R6 = track_frame
    a.ldrh_imm(0, 4, 4)      # step_accum
    a.ldrh_imm(1, 4, 6)      # track_bpm
    a.add_reg(0, 0, 1)
    a.mov_imm(2, 1800)
    a.cmp_reg(0, 2)
    a.strh_imm(0, 4, 4, cond=0x3) # if < 1800: save step_accum and increment track_frame
    a.b("saf_inc_frame", cond=0x3)
    a.sub_reg(0, 0, 2)
    a.strh_imm(0, 4, 4)

    # Half-beat step triggered! Iterate channels c = 0..3
    a.mov_imm(7, 0) # R7 = c (0..3)
    a.label("saf_ch_loop")
    a.cmp_imm(7, 4)
    a.b("saf_inc_frame", cond=0x2)
    a.add_reg(8, 4, 7, shift_imm=1, shift_type=0) # R8 = ASTATE + c*2
    a.ldrh_imm(0, 8, 0x14) # ch_rem_steps[c]
    a.cmp_imm(0, 0)
    a.b("saf_trigger_note", cond=0x0)
    a.sub_imm(0, 0, 1)
    a.strh_imm(0, 8, 0x14)
    a.b("saf_ch_next")

    a.label("saf_trigger_note")
    a.ldrh_imm(9, 8, 0x0C)  # R9 = note_idx
    a.ldrh_imm(10, 8, 0x1C) # R10 = ch_len
    a.cmp_imm(10, 0)
    a.b("saf_ch_next", cond=0x0)
    a.cmp_reg(9, 10)
    a.b("saf_idx_ok", cond=0x3)
    # Reached end of channel sequence: check track_loop
    a.ldrb_imm(0, 4, 8)
    a.cmp_imm(0, 0)
    a.b("saf_ch_next", cond=0x0) # non-looping track ended
    a.mov_imm(9, 0)
    a.label("saf_idx_ok")
    a.add_reg(0, 4, 7, shift_imm=2, shift_type=0)
    a.ldr_imm(0, 0, 0x24)   # ch_rom_ptr[c]
    a.add_reg(0, 0, 9, shift_imm=1, shift_type=0) # + note_idx * 2
    a.ldrb_imm(10, 0, 0)    # R10 = midi_or_on
    a.ldrb_imm(11, 0, 1)    # R11 = dur

    # Advance note_idx and set ch_rem_steps[c] = max(0, dur - 1)
    a.add_imm(0, 9, 1)
    a.strh_imm(0, 8, 0x0C)
    a.sub_imm(0, 11, 1, s=1)
    a.mov_imm(0, 0, cond=0x4)
    a.strh_imm(0, 8, 0x14)

    # Log AudioEv (8 bytes) at 0x0203FE00 + (audioEventWriteIdx & 63) * 8
    a.mov_imm(0, 0x0203FC00)
    a.add_imm(1, 0, 0x1C0)  # 0x0203FDC0
    a.ldrh_imm(2, 1, 2)     # audioEventWriteIdx at 0x0203FDC2
    a.and_imm(3, 2, 63)
    a.add_imm(2, 2, 1)
    a.strh_imm(2, 1, 2)
    a.add_imm(1, 0, 0x200)  # 0x0203FE00
    a.add_reg(1, 1, 3, shift_imm=3, shift_type=0)
    a.strb_imm(5, 1, 0)     # +0: trackId
    a.strb_imm(7, 1, 1)     # +1: channel
    a.strb_imm(10, 1, 2)    # +2: midiOrOn
    a.strb_imm(11, 1, 3)    # +3: durationSteps
    a.strh_imm(9, 1, 4)     # +4: noteIndex
    a.strh_imm(6, 1, 6)     # +6: stepFrame

    # Program GBA PSG registers (0x04000060..0x0400007C)
    a.mov_imm(0, 0x04000000)
    a.cmp_imm(7, 0)
    a.b("saf_psg_ch1", cond=0x1)
    # Channel 0 (Pulse 1)
    a.cmp_imm(10, 0)
    a.mov_imm(1, 0, cond=0x0)
    a.strh_imm(1, 0, 0x62, cond=0x0)
    a.b("saf_ch_next", cond=0x0)
    a.mov_imm(1, 0xC380)
    a.strh_imm(1, 0, 0x62)
    a.mov_imm(2, midi_pulse_rom_addr)
    a.add_reg(2, 2, 10, shift_imm=1, shift_type=0)
    a.ldrh_imm(1, 2, 0)
    a.orr_imm(1, 1, 0x8000)
    a.strh_imm(1, 0, 0x64)
    a.b("saf_ch_next")

    a.label("saf_psg_ch1")
    a.cmp_imm(7, 1)
    a.b("saf_psg_ch2", cond=0x1)
    # Channel 1 (Pulse 2)
    a.cmp_imm(10, 0)
    a.mov_imm(1, 0, cond=0x0)
    a.strh_imm(1, 0, 0x68, cond=0x0)
    a.b("saf_ch_next", cond=0x0)
    a.mov_imm(1, 0x9340)
    a.strh_imm(1, 0, 0x68)
    a.mov_imm(2, midi_pulse_rom_addr)
    a.add_reg(2, 2, 10, shift_imm=1, shift_type=0)
    a.ldrh_imm(1, 2, 0)
    a.orr_imm(1, 1, 0x8000)
    a.strh_imm(1, 0, 0x6C)
    a.b("saf_ch_next")

    a.label("saf_psg_ch2")
    a.cmp_imm(7, 2)
    a.b("saf_psg_ch3", cond=0x1)
    # Channel 2 (Wave)
    a.cmp_imm(10, 0)
    a.mov_imm(1, 0, cond=0x0)
    a.strh_imm(1, 0, 0x72, cond=0x0)
    a.b("saf_ch_next", cond=0x0)
    a.mov_imm(1, 0x2000)
    a.strh_imm(1, 0, 0x72)
    a.mov_imm(2, midi_wave_rom_addr)
    a.add_reg(2, 2, 10, shift_imm=1, shift_type=0)
    a.ldrh_imm(1, 2, 0)
    a.orr_imm(1, 1, 0x8000)
    a.strh_imm(1, 0, 0x74)
    a.b("saf_ch_next")

    a.label("saf_psg_ch3")
    # Channel 3 (Noise)
    a.cmp_imm(10, 0)
    a.mov_imm(1, 0, cond=0x0)
    a.strh_imm(1, 0, 0x78, cond=0x0)
    a.b("saf_ch_next", cond=0x0)
    a.mov_imm(1, 0xA100)
    a.strh_imm(1, 0, 0x78)
    a.mov_imm(1, 0x8032)
    a.strh_imm(1, 0, 0x7C)

    a.label("saf_ch_next")
    a.add_imm(7, 7, 1)
    a.b("saf_ch_loop")

    a.label("saf_inc_frame")
    a.add_imm(6, 6, 1)
    a.strh_imm(6, 4, 2)
    a.label("saf_done")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # Overworld & Menu State Machine
    # start_new_game(R0=slotIdx, R1=starterId, R2=seed)
    a.label("start_new_game")
    a.push([4, 5, 6, 7, 14])
    a.mov_reg(4, 0) # slotIdx
    a.mov_reg(5, 1) # starterId
    a.mov_reg(6, 2) # seed

    # Clear GSTATE (0x02000000..0x02000FFF)
    a.mov_imm(7, 0x02000000)
    a.mov_imm(0, 0)
    a.mov_imm(1, 0)
    a.label("sng_clr")
    a.add_reg(2, 7, 1)
    a.str_imm(0, 2, 0)
    a.add_imm(1, 1, 4)
    a.cmp_imm(1, 0x1000)
    a.b("sng_clr", cond=0x3)

    # Set rng_state = seed, rng_draws_total = 0, battle_rng_draws = 0
    a.mov_imm(0, 0x02001000)
    a.str_imm(6, 0, 0x00)
    a.mov_imm(1, 0)
    a.str_imm(1, 0, 0x04)
    a.str_imm(1, 0, 0x08)
    a.strb_imm(4, 0, 0x1F) # active_slot
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x1E) # has_state = 1

    # Check if custom_name at 0x02001094 is non-empty; else default "Brie"
    a.add_imm(1, 0, 0x94)
    a.ldrb_imm(2, 1, 0)
    a.cmp_imm(2, 0)
    a.b("sng_copy_custom_name", cond=0x1)
    a.mov_imm(2, 0x65697242) # "Brie"
    a.str_imm(2, 7, 0x0C)
    a.b("sng_name_done")
    a.label("sng_copy_custom_name")
    for w_i in range(3):
        a.ldr_imm(2, 1, w_i * 4)
        a.str_imm(2, 7, 0x0C + w_i * 4)
    a.label("sng_name_done")

    # create_mon(starterId, 5, 0x020000B4)
    a.mov_reg(0, 5)
    a.mov_imm(1, 5)
    a.mov_imm(2, 0x020000B4)
    a.bl("create_mon")
    a.mov_imm(0, 1)
    a.strb_imm(0, 7, 0x0B0) # partyCount = 1
    a.mov_reg(0, 5)
    a.bl("mark_caught")

    # Initialize state fields
    a.str_imm(6, 7, 0x1C) # rngSeed = seed
    a.mov_imm(0, 500)
    a.str_imm(0, 7, 0x24) # gold = 500
    a.mov_imm(0, 0)
    a.strb_imm(0, 7, 0x28) # mapId = 0 ('cruston_town')
    a.mov_imm(0, 14)
    a.strb_imm(0, 7, 0x29) # x = 14
    a.mov_imm(0, 12)
    a.strb_imm(0, 7, 0x2A) # y = 12
    a.mov_imm(0, 1)
    a.strb_imm(0, 7, 0x2B) # dir = 1 ('up')
    a.mov_imm(0, 0x02001000)
    a.ldrb_imm(1, 0, 0x2B) # look_idx
    a.strb_imm(1, 7, 0x2D) # playerLook

    # Initialize bag_order and initial bag items:
    # paper_plate(0):5, wooden_board(1):2, broth_cup(5):3, garnish_treat(10):2, soup_ladle(23):1, kitchen_lantern(24):1
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 0x71) # bag_order_len = 0
    for i in range(25):
        a.strb_imm(1, 0, 0x72 + i)
    for item_idx, qty in [(0, 5), (1, 2), (5, 3), (10, 2), (23, 1), (24, 1)]:
        a.mov_imm(0, item_idx)
        a.mov_imm(1, qty)
        a.bl("bag_add")

    a.bl("init_all_npc_xy")
    a.mov_reg(0, 4)
    a.bl("save_to_slot")
    a.bl("play_map_music")

    # Show 3-line welcome dialog (dialog_count = 3, dialog_idx = 0, dialog_cb_kind = 0, screen = DIALOG(4))
    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 3)
    a.strb_imm(1, 0, 0x40) # dialog_count = 3
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 0x41) # dialog_idx = 0
    a.strb_imm(1, 0, 0x42) # dialog_cb_kind = 0
    a.mov_imm(1, 4)        # screen = DIALOG (4)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45) # dirty_ui = 1
    a.mov_imm(1, 0xFF)
    a.strb_imm(1, 0, 0x46) # force map VRAM reload
    a.pop([4, 5, 6, 7, 15])
    a.flush_literals()

    # Helper: show_dialog_n(R0=count 1..3, R1=cb_kind, R2=cb_arg0, R3=cb_arg1)
    a.label("show_dialog_n")
    a.push([4, 14])
    a.mov_imm(4, 0x02001000)
    a.strb_imm(0, 4, 0x40) # dialog_count
    a.mov_imm(0, 0)
    a.strb_imm(0, 4, 0x41) # dialog_idx = 0
    a.strb_imm(1, 4, 0x42) # dialog_cb_kind
    a.strb_imm(2, 4, 0x43) # dialog_cb_arg0
    a.strb_imm(3, 4, 0x44) # dialog_cb_arg1
    a.mov_imm(0, 4)        # screen = DIALOG (4)
    a.strb_imm(0, 4, 0x20)
    a.mov_imm(0, 1)
    a.strb_imm(0, 4, 0x45) # dirty_ui = 1
    a.pop([4, 15])
    a.flush_literals()

    # Helper: is_npc_hidden(R0=npc_rom_ptr) -> R0=1 if hidden else 0
    a.label("is_npc_hidden")
    a.push([1, 2, 3, 14])
    a.mov_reg(1, 0)
    a.mov_imm(2, 0x02000000)
    # Check questComplete (+17)
    a.ldrb_imm(0, 1, 17)
    a.cmp_imm(0, 0xFF)
    a.b("inh_chk_sec", cond=0x0)
    a.ldrh_imm(3, 2, 0x42) # questsDoneMask
    a.mov_reg_rs(3, 3, 0, shift_type=1)
    a.tst_imm(3, 1)
    a.mov_imm(0, 1, cond=0x1)
    a.b("inh_done", cond=0x1)
    a.label("inh_chk_sec")
    # Check secretId (+18)
    a.ldrb_imm(0, 1, 18)
    a.cmp_imm(0, 0xFF)
    a.b("inh_vis", cond=0x0)
    a.ldrh_imm(3, 2, 0x40) # secretsMask
    a.mov_reg_rs(3, 3, 0, shift_type=1)
    a.tst_imm(3, 1)
    a.mov_imm(0, 1, cond=0x1)
    a.b("inh_done", cond=0x1)
    a.label("inh_vis")
    a.mov_imm(0, 0)
    a.label("inh_done")
    a.pop([1, 2, 3, 15])
    a.flush_literals()

    # Helper: find_visible_npc_at(R0=map_hdr_ptr, R1=tx, R2=ty) -> R0=npc_rom_ptr (or 0 if none)
    a.label("find_visible_npc_at")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_reg(4, 0) # map_hdr_ptr
    a.mov_reg(5, 1) # tx
    a.mov_reg(6, 2) # ty
    a.ldrb_imm(7, 4, 18) # npcCount
    a.ldr_imm(8, 4, 32)  # npc_off
    a.mov_imm(0, table_addrs[10])
    a.add_reg(8, 0, 8)   # R8 = npc_rom_ptr
    a.mov_imm(9, 0)      # i = 0
    a.label("fvn_loop")
    a.cmp_reg(9, 7)
    a.b("fvn_none", cond=0x2)
    a.ldrh_imm(0, 8, 24) # npc_global_idx
    a.mov_imm(1, 0x02001800)
    a.add_reg(1, 1, 0, shift_imm=1, shift_type=0)
    a.ldrb_imm(2, 1, 0)  # cur x
    a.ldrb_imm(3, 1, 1)  # cur y
    a.cmp_reg(2, 5)
    a.cmp_reg(3, 6, cond=0x0)
    a.b("fvn_next", cond=0x1)
    a.mov_reg(0, 8)
    a.bl("is_npc_hidden")
    a.cmp_imm(0, 0)
    a.mov_reg(0, 8, cond=0x0)
    a.b("fvn_done", cond=0x0)
    a.label("fvn_next")
    a.add_imm(8, 8, 80)
    a.add_imm(9, 9, 1)
    a.b("fvn_loop")
    a.label("fvn_none")
    a.mov_imm(0, 0)
    a.label("fvn_done")
    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # Helper: is_tile_solid(R0=tileId) -> R0=1 if solid else 0
    a.label("is_tile_solid")
    a.push([1, 14])
    a.mov_imm(1, table_addrs[6] + 74 * 32 + 32 + 64 + 74 * 4)
    a.add_reg(1, 1, 0)
    a.ldrb_imm(0, 1, 0)
    a.pop([1, 15])
    a.flush_literals()

    # try_move(R0=dir 0=down,1=up,2=left,3=right, R1=isSlide 0..1)
    a.label("try_move")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(4, 0) # R4 = dir (0=down, 1=up, 2=left, 3=right)
    a.mov_reg(5, 1) # R5 = isSlide
    a.mov_imm(6, 0x02000000) # R6 = GSTATE
    a.strb_imm(4, 6, 0x2B)   # state.dir = dir

    # dx, dy from dir
    a.mov_imm(7, 0) # dx
    a.mov_imm(8, 0) # dy
    a.cmp_imm(4, 0); a.mov_imm(8, 1, cond=0x0)  # down: dy = +1
    a.cmp_imm(4, 1); a.mvn_imm(8, 0, cond=0x0)  # up: dy = -1
    a.cmp_imm(4, 2); a.mvn_imm(7, 0, cond=0x0)  # left: dx = -1
    a.cmp_imm(4, 3); a.mov_imm(7, 1, cond=0x0)  # right: dx = +1

    a.ldrb_imm(0, 6, 0x29) # state.x
    a.add_reg(7, 0, 7)     # R7 = nx
    a.ldrb_imm(0, 6, 0x2A) # state.y
    a.add_reg(8, 0, 8)     # R8 = ny

    # Map header in Table 10 (40 bytes per map)
    a.ldrb_imm(0, 6, 0x28) # mapId
    a.mov_imm(1, 40)
    a.mul(0, 0, 1)
    a.mov_imm(9, table_addrs[10])
    a.add_reg(9, 9, 0)     # R9 = map_hdr_ptr

    # 1. Check portals on current map
    a.ldrb_imm(10, 9, 17)  # portalCount
    a.ldr_imm(11, 9, 28)   # port_off
    a.mov_imm(0, table_addrs[10])
    a.add_reg(11, 0, 11)   # R11 = portal_ptr
    a.mov_imm(2, 0)
    a.label("tm_port_loop")
    a.cmp_reg(2, 10)
    a.b("tm_no_portal", cond=0x2)
    a.ldrb_imm(0, 11, 0)   # p.x
    a.ldrb_imm(1, 11, 1)   # p.y
    a.cmp_reg(0, 7)
    a.cmp_reg(1, 8, cond=0x0)
    a.b("tm_port_found", cond=0x0)
    a.add_imm(11, 11, 8)
    a.add_imm(2, 2, 1)
    a.b("tm_port_loop")

    a.label("tm_port_found")
    # Check p.reqSeals (+5)
    a.ldrb_imm(0, 11, 5)
    a.cmp_imm(0, 0)
    a.b("tm_port_chk_champ", cond=0x0)
    # Count set bits in sealsMask (0x0200002F)
    a.ldrb_imm(1, 6, 0x2F)
    a.mov_imm(2, 0)
    for b_i in range(8):
        a.tst_imm(1, 1 << b_i)
        a.add_imm(2, 2, 1, cond=0x1)
    a.cmp_reg(2, 0)
    a.b("tm_port_chk_champ", cond=0x2) # BCS (sealsCount >= reqSeals)
    # Blocked by reqSeals -> show 1-line dialog
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("tm_ret")

    a.label("tm_port_chk_champ")
    a.ldrh_imm(0, 11, 6) # reqChampion
    a.cmp_imm(0, 0)
    a.b("tm_port_warp", cond=0x0)
    a.ldrb_imm(1, 6, 0x2E) # championBeaten
    a.cmp_imm(1, 0)
    a.b("tm_port_warp", cond=0x1)
    # Blocked by reqChampion -> show 1-line dialog
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("tm_ret")

    a.label("tm_port_warp")
    a.mov_imm(0, 11) # 'door' sfx
    a.bl("play_sfx")
    a.ldrb_imm(0, 11, 2) # to_idx
    a.ldrb_imm(1, 11, 3) # tx
    a.ldrb_imm(2, 11, 4) # ty
    a.strb_imm(0, 6, 0x28) # state.mapId
    a.strb_imm(1, 6, 0x29) # state.x
    a.strb_imm(2, 6, 0x2A) # state.y
    a.mov_imm(3, 0x02001000)
    a.mov_imm(1, 120)
    a.strh_imm(1, 3, 0x30) # banner_timer_frames = 120
    a.mov_imm(1, 13)
    a.strh_imm(1, 3, 0x32) # transition_timer_frames = 13
    a.bl("play_map_music")
    a.b("tm_ret")

    a.label("tm_no_portal")
    # 2. Check map bounds: 0 <= nx < mw, 0 <= ny < mh
    a.ldrb_imm(10, 9, 12)  # R10 = mw
    a.ldrb_imm(11, 9, 13)  # R11 = mh
    a.cmp_imm(7, 0)
    a.b("tm_ret", cond=0xB) # BLT
    a.cmp_reg(7, 10)
    a.b("tm_ret", cond=0x2) # BCS
    a.cmp_imm(8, 0)
    a.b("tm_ret", cond=0xB) # BLT
    a.cmp_reg(8, 11)
    a.b("tm_ret", cond=0x2) # BCS

    # 3. Look up tile = map.grid[ny * mw + nx]
    a.ldr_imm(2, 9, 20)    # grid_off
    a.mov_imm(0, table_addrs[10])
    a.add_reg(2, 0, 2)     # R2 = grid_ptr
    a.mul(0, 8, 10)        # ny * mw
    a.add_reg(0, 0, 7)     # + nx
    a.add_reg(0, 2, 0)
    a.ldrb_imm(3, 0, 0)    # R3 = tile

    # Ledge check (tile == 65)
    a.cmp_imm(3, 65)
    a.b("tm_chk_gate", cond=0x1)
    a.cmp_imm(4, 0)        # dir == 'down' (0)?
    a.b("tm_ret", cond=0x1)
    a.add_imm(1, 8, 1)     # ny + 1
    a.cmp_reg(1, 11)
    a.b("tm_ret", cond=0x2) # ny + 1 >= mh
    a.mul(0, 1, 10)
    a.add_reg(0, 0, 7)
    a.add_reg(0, 2, 0)
    a.ldrb_imm(0, 0, 0)    # tile at (nx, ny+1)
    a.push([0, 1, 2])
    a.bl("is_tile_solid")
    a.mov_reg(3, 0)
    a.pop([0, 1, 2])
    a.cmp_imm(3, 0)
    a.b("tm_ret", cond=0x1) # solid below ledge
    a.mov_reg(8, 1)        # ny = ny + 1
    a.mov_reg(3, 0)        # tile = tile below ledge

    a.label("tm_chk_gate")
    a.cmp_imm(3, 73)       # locked gate?
    a.b("tm_chk_solid", cond=0x1)
    # Check switchesBits[mapId]
    a.ldrb_imm(0, 6, 0x28) # mapId
    a.mov_reg(1, 0, shift_imm=3, shift_type=1)
    a.and_imm(0, 0, 7)
    a.add_reg(1, 6, 1)
    a.ldrb_imm(1, 1, 0x30) # switchesBits
    a.mov_reg_rs(1, 1, 0, shift_type=1)
    a.tst_imm(1, 1)
    a.b("tm_ret", cond=0x0) # gate locked!
    a.b("tm_chk_npc")

    a.label("tm_chk_solid")
    a.push([3])
    a.mov_reg(0, 3)
    a.bl("is_tile_solid")
    a.cmp_imm(0, 0)
    a.pop([3])
    a.b("tm_ret", cond=0x1) # solid tile!

    a.label("tm_chk_npc")
    # Check if a visible NPC is at (nx, ny)
    a.push([3])
    a.mov_reg(0, 9)
    a.mov_reg(1, 7)
    a.mov_reg(2, 8)
    a.bl("find_visible_npc_at")
    a.pop([3])
    a.cmp_imm(0, 0)
    a.b("tm_do_step", cond=0x0)
    # Blocking NPC found at R0! Check if pushable (+13)
    a.ldrb_imm(1, 0, 13)
    a.cmp_imm(1, 0)
    a.b("tm_ret", cond=0x0) # not pushable -> blocked!
    # Pushable NPC: compute bx = nx + dx, by = ny + dy
    a.mov_reg(1, 7) # bx = nx
    a.mov_reg(2, 8) # by = ny
    a.cmp_imm(4, 0); a.add_imm(2, 2, 1, cond=0x0)
    a.cmp_imm(4, 1); a.sub_imm(2, 2, 1, cond=0x0)
    a.cmp_imm(4, 2); a.sub_imm(1, 1, 1, cond=0x0)
    a.cmp_imm(4, 3); a.add_imm(1, 1, 1, cond=0x0)
    a.cmp_imm(1, 0); a.b("tm_ret", cond=0xB)
    a.cmp_reg(1, 10); a.b("tm_ret", cond=0x2)
    a.cmp_imm(2, 0); a.b("tm_ret", cond=0xB)
    a.cmp_reg(2, 11); a.b("tm_ret", cond=0x2)

    # Check bTile at (bx, by)
    a.push([0, 1, 2, 3])
    a.ldr_imm(3, 9, 20)
    a.mov_imm(0, table_addrs[10])
    a.add_reg(3, 0, 3)
    a.mul(0, 2, 10)
    a.add_reg(0, 0, 1)
    a.add_reg(0, 3, 0)
    a.ldrb_imm(0, 0, 0) # bTile
    a.cmp_imm(0, 73)
    a.b("tm_push_fail", cond=0x0)
    a.bl("is_tile_solid")
    a.cmp_imm(0, 0)
    a.b("tm_push_fail", cond=0x1)
    # Check bOccupied
    a.ldr_imm(1, 13, 4) # bx
    a.ldr_imm(2, 13, 8) # by
    a.mov_reg(0, 9)
    a.bl("find_visible_npc_at")
    a.cmp_imm(0, 0)
    a.b("tm_push_fail", cond=0x1)
    # Move pushable NPC to (bx, by)!
    a.pop([0, 1, 2, 3])
    a.ldrh_imm(0, 0, 24) # npc_global_idx
    a.mov_imm(10, 0x02001800)
    a.add_reg(10, 10, 0, shift_imm=1, shift_type=0)
    a.strb_imm(1, 10, 0) # npc.x = bx
    a.strb_imm(2, 10, 1) # npc.y = by
    a.b("tm_do_step")

    a.label("tm_push_fail")
    a.pop([0, 1, 2, 3])
    a.b("tm_ret")

    a.label("tm_do_step")
    # Update player x, y, steps, walkFrame, and 40-step isNight toggle!
    a.strb_imm(7, 6, 0x29) # state.x = nx
    a.strb_imm(8, 6, 0x2A) # state.y = ny
    a.ldr_imm(0, 6, 0x20)  # state.steps
    a.add_imm(0, 0, 1)
    a.str_imm(0, 6, 0x20)
    # walkFrame = (walkFrame == 1) ? 2 : 1
    a.mov_imm(1, 0x02001000)
    a.ldrb_imm(2, 1, 0x2C)
    a.cmp_imm(2, 1)
    a.mov_imm(2, 2, cond=0x0)
    a.mov_imm(2, 1, cond=0x1)
    a.strb_imm(2, 1, 0x2C)
    a.mov_imm(2, 1)
    a.strb_imm(2, 1, 0x45) # dirty_ui = 1

    # Check if steps % 40 == 0
    a.push([3])
    a.mov_imm(1, 40)
    a.bl("udiv32")
    a.pop([3])
    a.cmp_imm(1, 0)
    a.b("tm_chk_switch", cond=0x1)
    a.ldrb_imm(0, 6, 0x2C) # isNight
    a.eor_imm(0, 0, 1)
    a.strb_imm(0, 6, 0x2C)

    a.label("tm_chk_switch")
    # Floor switch (tile == 9)
    a.cmp_imm(3, 9)
    a.b("tm_chk_slide", cond=0x1)
    a.ldrb_imm(0, 6, 0x28) # mapId
    a.mov_reg(1, 0, shift_imm=3, shift_type=1)
    a.and_imm(0, 0, 7)
    a.mov_imm(2, 1)
    a.mov_reg_rs(2, 2, 0, shift_type=0)
    a.add_reg(1, 6, 1)
    a.ldrb_imm(0, 1, 0x30) # switchesBits
    a.tst_reg(0, 2)
    a.b("tm_chk_slide", cond=0x1) # switch already active!
    a.orr_reg(0, 0, 2)
    a.strb_imm(0, 1, 0x30)
    a.mov_imm(0, 9) # 'level_up' sfx
    a.bl("play_sfx")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("tm_ret")

    a.label("tm_chk_slide")
    # Conveyors (67:right, 68:left, 69:up, 70:down) and Oil/Ice (66)
    a.cmp_imm(5, 0) # isSlide == 0?
    a.b("tm_chk_grass", cond=0x1)
    a.mov_imm(10, 0) # slideSteps = 0
    a.label("tm_slide_loop")
    a.cmp_imm(10, 12)
    a.b("tm_chk_grass", cond=0x2)
    a.add_imm(10, 10, 1)
    a.ldrb_imm(0, 6, 0x29) # cur x
    a.ldrb_imm(1, 6, 0x2A) # cur y
    a.ldrb_imm(2, 9, 12)   # mw
    a.mul(1, 1, 2)
    a.add_reg(0, 1, 0)
    a.ldr_imm(1, 9, 20)    # grid_off
    a.mov_imm(2, table_addrs[10])
    a.add_reg(1, 2, 1)
    a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 0)    # curTile
    a.cmp_imm(0, 67)
    a.mov_imm(0, 3, cond=0x0); a.b("tm_do_slide", cond=0x0) # 67 -> right(3)
    a.cmp_imm(0, 68)
    a.mov_imm(0, 2, cond=0x0); a.b("tm_do_slide", cond=0x0) # 68 -> left(2)
    a.cmp_imm(0, 69)
    a.mov_imm(0, 1, cond=0x0); a.b("tm_do_slide", cond=0x0) # 69 -> up(1)
    a.cmp_imm(0, 70)
    a.mov_imm(0, 0, cond=0x0); a.b("tm_do_slide", cond=0x0) # 70 -> down(0)
    a.cmp_imm(0, 66)
    a.ldrb_imm(0, 6, 0x2B, cond=0x0); a.b("tm_do_slide", cond=0x0) # 66 -> state.dir
    a.b("tm_chk_grass")

    a.label("tm_do_slide")
    a.push([3, 10])
    a.mov_imm(1, 1) # isSlide = 1
    a.bl("try_move")
    a.pop([3, 10])
    a.b("tm_slide_loop")

    a.label("tm_chk_grass")
    # Tall grass tiles: 11, 23, 35, 47, 62
    a.cmp_imm(3, 11)
    a.cmp_imm(3, 23, cond=0x1)
    a.cmp_imm(3, 35, cond=0x1)
    a.cmp_imm(3, 47, cond=0x1)
    a.cmp_imm(3, 62, cond=0x1)
    a.b("tm_ret", cond=0x1)
    a.ldrb_imm(10, 9, 16) # wildPool.length
    a.cmp_imm(10, 0)
    a.b("tm_ret", cond=0x0)

    # 1st RNG draw: rng() < 0.16 (0x28F5C290)
    a.bl("game_rng_next")
    a.mov_imm(1, 0x28F5C290)
    a.cmp_reg(0, 1)
    a.b("tm_ret", cond=0x2) # BCS (>= 0.16)

    # Build filtered pool on stack (up to 16 entries of 4 bytes = 64 bytes)
    a.sub_imm(13, 13, 64)
    a.ldr_imm(8, 9, 24) # wp_off
    a.mov_imm(0, table_addrs[10])
    a.add_reg(8, 0, 8)  # R8 = wp_ptr
    a.mov_imm(7, 0)     # R7 = filtered_len = 0
    a.mov_imm(11, 0)    # i = 0
    a.label("tm_wp_filter")
    a.cmp_reg(11, 10)
    a.b("tm_wp_filtered", cond=0x2)
    a.add_reg(0, 8, 11, shift_imm=2, shift_type=0)
    a.ldr_imm(4, 0, 0)  # [spId, minLv, maxLv, 0]
    a.and_imm(0, 4, 0xFF) # spId
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(0, 0, 1)
    a.mov_imm(1, table_addrs[4])
    a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 10) # sp.nightOnly
    a.cmp_imm(0, 0)
    a.b("tm_wp_keep", cond=0x0)
    a.ldrb_imm(0, 6, 0x2C) # state.isNight
    a.cmp_imm(0, 0)
    a.b("tm_wp_next", cond=0x0)
    a.label("tm_wp_keep")
    a.add_reg(0, 13, 7, shift_imm=2, shift_type=0)
    a.str_imm(4, 0, 0)
    a.add_imm(7, 7, 1)
    a.label("tm_wp_next")
    a.add_imm(11, 11, 1)
    a.b("tm_wp_filter")

    a.label("tm_wp_filtered")
    # 2nd RNG draw: Math.floor(rng() * pool.length)
    a.bl("game_rng_next")
    a.cmp_imm(7, 0)
    a.ldr_imm(4, 8, 0, cond=0x0) # fallback map.wildPool[0]
    a.b("tm_wp_picked", cond=0x0)
    a.umull(2, 3, 0, 7)          # R3 = (u * pool.length) >> 32
    a.add_reg(0, 13, 3, shift_imm=2, shift_type=0)
    a.ldr_imm(4, 0, 0)           # R4 = pick
    a.label("tm_wp_picked")
    a.add_imm(13, 13, 64)

    # 3rd RNG draw: lv = pick[1] + Math.floor(rng() * (pick[2] - pick[1] + 1))
    a.bl("game_rng_next")
    a.mov_reg(1, 4, shift_imm=8, shift_type=1)
    a.and_imm(1, 1, 0xFF)        # pick[1] (minLv)
    a.mov_reg(2, 4, shift_imm=16, shift_type=1)
    a.and_imm(2, 2, 0xFF)        # pick[2] (maxLv)
    a.sub_reg(2, 2, 1)
    a.add_imm(2, 2, 1)           # span = maxLv - minLv + 1
    a.umull(3, 5, 0, 2)          # R5 = (u * span) >> 32
    a.add_reg(1, 1, 5)           # R1 = lv
    a.and_imm(0, 4, 0xFF)        # R0 = spId
    a.bl("start_wild_battle")

    a.label("tm_ret")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # start_wild_battle(R0=speciesId, R1=level)
    a.label("start_wild_battle")
    a.push([4, 5, 6, 14])
    a.mov_reg(4, 0) # speciesId
    a.mov_reg(5, 1) # level
    a.bl("mark_seen")
    # Reset battle_rng_draws? Wait: in Game, battleRngDraws is cumulative or per-battle; let's keep battle_rng_draws incrementing cleanly!
    a.mov_reg(0, 4)
    a.mov_reg(1, 5)
    a.mov_imm(2, 0x02001110) # foe_party[0]
    a.bl("create_mon")

    # Find activeIdx = max(0, party.findIndex(m => m.hp > 0))
    a.mov_imm(6, 0x02000000)
    a.ldrb_imm(1, 6, 0x0B0) # partyCount
    a.add_imm(2, 6, 0x0B4)
    a.mov_imm(3, 0)
    a.label("swb_find_lead")
    a.cmp_reg(3, 1)
    a.mov_imm(3, 0, cond=0x2)
    a.b("swb_lead_done", cond=0x2)
    a.ldrh_imm(0, 2, 0x08)
    a.cmp_imm(0, 0)
    a.b("swb_lead_done", cond=0x1)
    a.add_imm(2, 2, 48)
    a.add_imm(3, 3, 1)
    a.b("swb_find_lead")
    a.label("swb_lead_done")

    a.mov_imm(4, 0x02001100) # BSTATE
    a.mov_imm(0, 1)
    a.strb_imm(0, 4, 0)      # active = 1
    a.strb_imm(0, 4, 1)      # is_wild = 1
    a.mov_imm(0, 0xFF)
    a.strb_imm(0, 4, 2)      # trainer_idx = 0xFF
    a.mov_imm(0, 1)
    a.strb_imm(0, 4, 3)      # foe_count = 1
    a.mov_imm(0, 0)
    a.strb_imm(0, 4, 4)      # foe_idx = 0
    a.strb_imm(3, 4, 5)      # player_idx = activeIdx
    a.strb_imm(0, 4, 6)      # temp = 0
    a.strb_imm(0, 4, 7)      # used_fav_treat = 0
    a.mov_imm(0, 1)
    a.strb_imm(0, 4, 8)      # phase = MAIN (1)
    a.mov_imm(0, 0)
    a.strb_imm(0, 4, 9)      # cursor = 0
    a.strb_imm(0, 4, 0x0A)   # pending_end = 0

    a.mov_imm(0, 9)          # 'battle_wild' track
    a.bl("play_music")
    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 5)          # screen = BATTLE (5)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45)   # dirty_ui = 1
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    # start_trainer_battle(R0=trainer_idx 0..32)
    a.label("start_trainer_battle")
    a.push([4, 5, 6, 7, 8, 14])
    a.mov_reg(4, 0)          # R4 = trainer_idx
    a.mov_imm(0, 48)
    a.mul(5, 4, 0)
    a.mov_imm(0, table_addrs[11])
    a.add_reg(5, 0, 5)       # R5 = trainer_rom_ptr
    a.ldrb_imm(6, 5, 28)     # R6 = party_len

    a.mov_imm(7, 0)          # i = 0
    a.mov_imm(8, 0x02001110) # dst foe_party[0]
    a.label("stb_foe_loop")
    a.cmp_reg(7, 6)
    a.b("stb_foe_done", cond=0x2)
    a.add_reg(0, 5, 7, shift_imm=1, shift_type=0)
    a.ldrb_imm(0, 0, 36)     # spId
    a.bl("mark_seen")
    a.add_reg(0, 5, 7, shift_imm=1, shift_type=0)
    a.ldrb_imm(1, 0, 37)     # lv
    a.ldrb_imm(0, 0, 36)     # spId
    a.mov_reg(2, 8)
    a.bl("create_mon")
    a.add_imm(8, 8, 48)
    a.add_imm(7, 7, 1)
    a.b("stb_foe_loop")
    a.label("stb_foe_done")

    # Find activeIdx
    a.mov_imm(7, 0x02000000)
    a.ldrb_imm(1, 7, 0x0B0)
    a.add_imm(2, 7, 0x0B4)
    a.mov_imm(3, 0)
    a.label("stb_find_lead")
    a.cmp_reg(3, 1)
    a.mov_imm(3, 0, cond=0x2)
    a.b("stb_lead_done", cond=0x2)
    a.ldrh_imm(0, 2, 0x08)
    a.cmp_imm(0, 0)
    a.b("stb_lead_done", cond=0x1)
    a.add_imm(2, 2, 48)
    a.add_imm(3, 3, 1)
    a.b("stb_find_lead")
    a.label("stb_lead_done")

    a.mov_imm(7, 0x02001100)
    a.mov_imm(0, 1)
    a.strb_imm(0, 7, 0)      # active = 1
    a.mov_imm(0, 0)
    a.strb_imm(0, 7, 1)      # is_wild = 0
    a.strb_imm(4, 7, 2)      # trainer_idx = R4
    a.strb_imm(6, 7, 3)      # foe_count = R6
    a.strb_imm(0, 7, 4)      # foe_idx = 0
    a.strb_imm(3, 7, 5)      # player_idx = activeIdx
    a.strb_imm(0, 7, 6)      # temp = 0
    a.strb_imm(0, 7, 7)      # used_fav_treat = 0
    a.mov_imm(0, 1)
    a.strb_imm(0, 7, 8)      # phase = MAIN (1)
    a.mov_imm(0, 0)
    a.strb_imm(0, 7, 9)      # cursor = 0
    a.strb_imm(0, 7, 0x0A)   # pending_end = 0

    # Music: trainer_idx 17..28 -> battle_rival(11), 32 -> battle_champion(12), else battle_chef(10)
    a.mov_imm(0, 10)
    a.cmp_imm(4, 17)
    a.bcc_chk = None
    a.b("stb_music_set", cond=0x3)
    a.cmp_imm(4, 28)
    a.mov_imm(0, 11, cond=0x9) # 17..28 -> battle_rival
    a.cmp_imm(4, 32)
    a.mov_imm(0, 12, cond=0x0) # 32 -> battle_champion
    a.label("stb_music_set")
    a.bl("play_music")

    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 5)          # screen = BATTLE (5)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45)
    a.pop([4, 5, 6, 7, 8, 15])
    a.flush_literals()

    # heal_party()
    a.label("heal_party")
    a.push([4, 5, 6, 14])
    a.mov_imm(4, 0x02000000)
    a.ldrb_imm(5, 4, 0x0B0)  # partyCount
    a.add_imm(4, 4, 0x0B4)   # party[0]
    a.mov_imm(6, 0)
    a.label("hp_loop")
    a.cmp_reg(6, 5)
    a.b("hp_done", cond=0x2)
    a.ldrh_imm(0, 4, 0x0A)   # maxHp
    a.strh_imm(0, 4, 0x08)   # hp = maxHp
    a.mov_imm(0, 0)
    a.strb_imm(0, 4, 0x06)   # status = 0
    a.ldr_imm(0, 4, 0x24)    # moveMaxPps[0..3]
    a.str_imm(0, 4, 0x20)    # movePps[0..3] = moveMaxPps[0..3]
    a.add_imm(4, 4, 48)
    a.add_imm(6, 6, 1)
    a.b("hp_loop")
    a.label("hp_done")
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    # Replace finishBattle in handle_battle_input when pending_end != 0!
    # Wait: in emit_core_and_battle, when pending_end != 0 on LOG screen A/B press,
    # let's make a dedicated finish_battle(R0=outcome) function and call it!
    a.label("finish_battle_full")
    a.push([4, 5, 6, 7, 14])
    a.mov_reg(4, 0)          # R4 = outcome (1=WIN, 2=LOSE, 3=RUN, 4=CAUGHT)
    a.mov_imm(5, 0x02001100) # BSTATE
    a.ldrb_imm(6, 5, 1)      # is_wild
    a.ldrb_imm(7, 5, 2)      # trainer_idx
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0)      # active = 0
    a.strb_imm(0, 5, 8)      # phase = 0

    a.cmp_imm(4, 1)          # outcome == WIN?
    a.b("fbf_chk_lose", cond=0x1)
    a.cmp_imm(6, 0)          # is_wild == 0?
    a.b("fbf_to_ow", cond=0x1)
    # Trainer defeated!
    a.mov_imm(5, 0x02000000)
    a.mov_reg(0, 7, shift_imm=3, shift_type=1)
    a.and_imm(1, 7, 7)
    a.mov_imm(2, 1)
    a.mov_reg_rs(2, 2, 1, shift_type=0)
    a.add_reg(0, 5, 0)
    a.ldrb_imm(1, 0, 0x38)   # defeatedTrainersBits
    a.tst_reg(1, 2)
    a.b("fbf_already_def", cond=0x1)
    a.orr_reg(1, 1, 2)
    a.strb_imm(1, 0, 0x38)
    # Look up trainer in Table 11 (48B)
    a.mov_imm(0, 48)
    a.mul(0, 7, 0)
    a.mov_imm(1, table_addrs[11])
    a.add_reg(0, 1, 0)
    a.ldrh_imm(1, 0, 24)     # rewardGold
    a.cmp_imm(1, 0)
    a.mov_imm(1, 200, cond=0x0)
    a.ldr_imm(2, 5, 0x24)    # state.gold
    a.add_reg(2, 2, 1)
    a.str_imm(2, 5, 0x24)
    # Check trainer.has_seal (+27) and seal_idx (+26)
    a.ldrb_imm(1, 0, 27)
    a.cmp_imm(1, 0)
    a.b("fbf_already_def", cond=0x0)
    a.ldrb_imm(1, 0, 26)     # seal_idx (0..7)
    a.mov_imm(2, 1)
    a.mov_reg_rs(2, 2, 1, shift_type=0)
    a.ldrb_imm(1, 5, 0x2F)   # sealsMask
    a.orr_reg(1, 1, 2)
    a.strb_imm(1, 5, 0x2F)

    a.label("fbf_already_def")
    a.mov_imm(0, 14)         # 'victory' track
    a.bl("play_music")
    # If trainer_idx == 32 ('champion_aurelia'), set championBeaten = 1 before saving once
    a.cmp_imm(7, 32)
    a.mov_imm(0, 1, cond=0x0)
    a.strb_imm(0, 5, 0x2E, cond=0x0)
    a.mov_imm(0, 0x02001000)
    a.ldrb_imm(0, 0, 0x1F)   # active_slot
    a.bl("save_to_slot")

    # Check if trainer_idx == 32 ('champion_aurelia')
    a.cmp_imm(7, 32)
    a.b("fbf_normal_tr_win", cond=0x1)
    # Show 2-line dialog with cb = START_CREDITS (4)
    a.mov_imm(0, 2); a.mov_imm(1, 4); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.pop([4, 5, 6, 7, 15])

    a.label("fbf_normal_tr_win")
    # Show 1-line dialog (tr.win) with cb = PLAY_MAP_MUSIC (1)
    a.mov_imm(0, 1); a.mov_imm(1, 1); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.pop([4, 5, 6, 7, 15])

    a.label("fbf_chk_lose")
    a.cmp_imm(4, 2)          # outcome == LOSE?
    a.b("fbf_to_ow", cond=0x1)
    a.bl("heal_party")
    a.mov_imm(5, 0x02000000)
    a.mov_imm(0, 0)          # mapId = 0 ('cruston_town')
    a.strb_imm(0, 5, 0x28)
    a.mov_imm(0, 11)
    a.strb_imm(0, 5, 0x29)   # x = 11
    a.mov_imm(0, 12)
    a.strb_imm(0, 5, 0x2A)   # y = 12

    a.label("fbf_to_ow")
    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 3)          # screen = OVERWORLD (3)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45)
    a.bl("play_map_music")
    a.pop([4, 5, 6, 7, 15])
    a.flush_literals()

    # grant_quest_reward(R0=qid 0..15)
    a.label("grant_quest_reward")
    a.push([4, 5, 14])
    a.mov_reg(4, 0)          # qid
    a.mov_imm(5, 0x02000000) # GSTATE
    # Rewards per qid (0..15) matching 07_game_engine.js lines 851..869:
    rewards = [
        (0, 2, 3, 0),      # q1_butter: ceramic_plate(2) +3
        (1, 3, 2, 300),    # q2_lid: bento_set(3) +2, +300G
        (2, None, 0, 500), # q3_chopsticks: +500G
        (3, 4, 1, 0),      # q4_truffle: royal_banquet(4) +1
        (4, 18, 1, 400),   # q5_starter: card_fermented(18) +1, +400G
        (5, 6, 2, 350),    # q6_ginger: hearty_stew(6) +2, +350G
        (6, 15, 1, 500),   # q7_chili: card_spicy(15) +1, +500G
        (7, 7, 1, 600),    # q8_ladle: grand_feast(7) +1, +600G
        (8, 4, 1, 0),      # q9_critics: royal_banquet(4) +1
        (9, 5, 2, 0),      # q10_crumb: broth_cup(5) +2
        (10, 10, 3, 0),    # q11_scallion: garnish_treat(10) +3
        (11, 1, 2, 0),     # q12_salt: wooden_board(1) +2
        (12, 16, 1, 0),    # q13_stock: card_brothy(16) +1
        (13, 8, 3, 0),     # q14_steam: mint_tea(8) +3
        (14, 9, 2, 0),     # q15_wok: wakeup_espresso(9) +2
        (15, 7, 2, 2000),  # q16_banquet: grand_feast(7) +2, +2000G
    ]
    for q_i, item_i, qty, gold_add in rewards:
        lbl_next = f"gqr_next_{q_i}"
        a.cmp_imm(4, q_i)
        a.b(lbl_next, cond=0x1)
        if item_i is not None:
            a.mov_imm(0, item_i)
            a.mov_imm(1, qty)
            a.bl("bag_add")
        if gold_add > 0:
            a.ldr_imm(0, 5, 0x24)
            a.mov_imm(1, gold_add)
            a.add_reg(0, 0, 1)
            a.str_imm(0, 5, 0x24)
        a.b("gqr_done")
        a.label(lbl_next)
    a.label("gqr_done")
    a.pop([4, 5, 15])
    a.flush_literals()

    # interact_ahead()
    a.label("interact_ahead")
    a.push([4, 5, 6, 7, 8, 9, 10, 14])
    a.mov_imm(6, 0x02000000) # R6 = GSTATE
    a.ldrb_imm(4, 6, 0x2B)   # dir
    a.mov_imm(7, 0)          # dx
    a.mov_imm(8, 0)          # dy
    a.cmp_imm(4, 0); a.mov_imm(8, 1, cond=0x0)
    a.cmp_imm(4, 1); a.mvn_imm(8, 0, cond=0x0)
    a.cmp_imm(4, 2); a.mvn_imm(7, 0, cond=0x0)
    a.cmp_imm(4, 3); a.mov_imm(7, 1, cond=0x0)
    a.ldrb_imm(0, 6, 0x29)
    a.add_reg(7, 0, 7)       # R7 = tx
    a.ldrb_imm(0, 6, 0x2A)
    a.add_reg(8, 0, 8)       # R8 = ty

    a.ldrb_imm(0, 6, 0x28)   # mapId
    a.mov_imm(1, 40)
    a.mul(0, 0, 1)
    a.mov_imm(9, table_addrs[10])
    a.add_reg(9, 9, 0)       # R9 = map_hdr_ptr

    a.mov_reg(0, 9)
    a.mov_reg(1, 7)
    a.mov_reg(2, 8)
    a.bl("find_visible_npc_at")
    a.mov_reg(10, 0)         # R10 = npc_rom_ptr
    a.cmp_imm(10, 0)
    a.b("ia_found_npc", cond=0x1)

    # No NPC: check sign (tile 3) or water ladle (tiles 13, 25, 37, 49)
    a.ldrb_imm(0, 9, 12)     # mw
    a.ldrb_imm(1, 9, 13)     # mh
    a.cmp_imm(7, 0); a.b("ia_ret", cond=0xB)
    a.cmp_reg(7, 0); a.b("ia_ret", cond=0x2)
    a.cmp_imm(8, 0); a.b("ia_ret", cond=0xB)
    a.cmp_reg(8, 1); a.b("ia_ret", cond=0x2)

    a.ldr_imm(2, 9, 20)      # grid_off
    a.mov_imm(3, table_addrs[10])
    a.add_reg(2, 3, 2)
    a.mul(0, 8, 0)
    a.add_reg(0, 0, 7)
    a.add_reg(0, 2, 0)
    a.ldrb_imm(4, 0, 0)      # R4 = tile
    a.cmp_imm(4, 3)          # sign?
    a.b("ia_chk_water", cond=0x1)
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_water")
    a.cmp_imm(4, 13)
    a.cmp_imm(4, 25, cond=0x1)
    a.cmp_imm(4, 37, cond=0x1)
    a.cmp_imm(4, 49, cond=0x1)
    a.b("ia_ret", cond=0x1)
    a.ldrh_imm(0, 6, 0x7E + 23 * 2) # bag.soup_ladle
    a.cmp_imm(0, 0)
    a.b("ia_ret", cond=0x0)
    a.ldrb_imm(5, 9, 16)     # wildPool.length
    a.cmp_imm(5, 0)
    a.b("ia_ret", cond=0x0)
    # Roll pick and lv now, startWildBattle in dialog callback!
    a.bl("game_rng_next")
    a.umull(2, 3, 0, 5)      # R3 = idx
    a.ldr_imm(0, 9, 24)      # wp_off
    a.mov_imm(1, table_addrs[10])
    a.add_reg(0, 1, 0)
    a.add_reg(0, 0, 3, shift_imm=2, shift_type=0)
    a.ldr_imm(4, 0, 0)       # pick
    a.bl("game_rng_next")
    a.mov_reg(1, 4, shift_imm=8, shift_type=1); a.and_imm(1, 1, 0xFF)
    a.mov_reg(2, 4, shift_imm=16, shift_type=1); a.and_imm(2, 2, 0xFF)
    a.sub_reg(2, 2, 1); a.add_imm(2, 2, 1)
    a.umull(3, 5, 0, 2)
    a.add_reg(3, 1, 5)       # R3 = lv
    a.and_imm(2, 4, 0xFF)    # R2 = spId
    a.mov_imm(0, 1)          # 1 line dialog
    a.mov_imm(1, 2)          # cb_kind = 2 (START_WILD)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_found_npc")
    # Check npc.action (+12): 0=None, 1=heal, 2=shop, 3=cook, 4=cafe, 5=secret151
    a.ldrb_imm(0, 10, 12)
    a.cmp_imm(0, 1)          # heal
    a.b("ia_act_shop", cond=0x1)
    a.bl("heal_party")
    a.mov_imm(0, 15)         # 'healing' music
    a.bl("play_music")
    a.ldrb_imm(0, 10, 20)    # len(npc.lines)
    a.add_imm(0, 0, 1)       # + 1 line ("All your bEATsts are simmering...")
    a.mov_imm(1, 1)          # cb = PLAY_MAP_MUSIC
    a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_act_shop")
    a.cmp_imm(0, 2)          # shop
    a.b("ia_act_cook", cond=0x1)
    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 0x28)   # shop_cursor = 0
    a.mov_imm(1, 11)         # screen = SHOP (11)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45)
    a.b("ia_ret")

    a.label("ia_act_cook")
    a.cmp_imm(0, 3)          # cook
    a.b("ia_act_cafe", cond=0x1)
    a.ldrh_imm(0, 6, 0x7E + 5 * 2)  # broth_cup
    a.ldrh_imm(1, 6, 0x7E + 10 * 2) # garnish_treat
    a.cmp_imm(0, 0)
    a.b("ia_cook_msg", cond=0x0)
    a.cmp_imm(1, 0)
    a.b("ia_cook_msg", cond=0x0)
    a.mov_imm(0, 5); a.mvn_imm(1, 0); a.bl("bag_add")
    a.mov_imm(0, 10); a.mvn_imm(1, 0); a.bl("bag_add")
    a.mov_imm(0, 6); a.mov_imm(1, 1); a.bl("bag_add") # hearty_stew +1
    a.label("ia_cook_msg")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_act_cafe")
    a.cmp_imm(0, 4)          # cafe
    a.b("ia_act_sec151", cond=0x1)
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_act_sec151")
    a.cmp_imm(0, 5)          # secret151
    a.b("ia_chk_qgive", cond=0x1)
    # Check championBeaten, isNight, royal_banquet > 0, !dexCaught(151), and all 4 families in party
    a.ldrb_imm(0, 6, 0x2E)   # championBeaten
    a.ldrb_imm(1, 6, 0x2C)   # isNight
    a.and_reg(0, 0, 1, s=1)
    a.b("ia_sec151_locked", cond=0x0)
    a.ldrh_imm(0, 6, 0x7E + 4 * 2) # royal_banquet
    a.cmp_imm(0, 0)
    a.b("ia_sec151_locked", cond=0x0)
    # Check dexCaught(151): byte 18, bit 6 (150 = 18*8 + 6)
    a.ldrb_imm(0, 6, 0x6A + 18)
    a.tst_imm(0, 1 << 6)
    a.b("ia_sec151_locked", cond=0x1)
    # Check all 4 families in party
    a.ldrb_imm(1, 6, 0x0B0)  # partyCount
    a.add_imm(2, 6, 0x0B4)
    a.mov_imm(3, 0)          # fam_mask = 0
    a.mov_imm(4, 0)
    a.label("ia_fam_loop")
    a.cmp_reg(4, 1)
    a.b("ia_fam_done", cond=0x2)
    a.ldrb_imm(0, 2, 4)      # spId
    a.sub_imm(0, 0, 1)
    a.mov_imm(5, 56)
    a.mul(0, 0, 5)
    a.mov_imm(5, table_addrs[4])
    a.add_reg(0, 5, 0)
    a.ldrb_imm(0, 0, 1)      # fam_idx (0..3)
    a.mov_imm(5, 1)
    a.mov_reg_rs(5, 5, 0, shift_type=0)
    a.orr_reg(3, 3, 5)
    a.add_imm(2, 2, 48)
    a.add_imm(4, 4, 1)
    a.b("ia_fam_loop")
    a.label("ia_fam_done")
    a.cmp_imm(3, 0xF)        # all 4 families (0b1111)?
    a.b("ia_sec151_locked", cond=0x1)
    # Unlock #151! Set sec_151 (bit 0) in secretsMask
    a.ldrh_imm(0, 6, 0x40)
    a.orr_imm(0, 0, 1)
    a.strh_imm(0, 6, 0x40)
    a.mov_imm(0, 3)          # 3 lines
    a.mov_imm(1, 2)          # cb = START_WILD
    a.mov_imm(2, 151)        # spId = 151
    a.mov_imm(3, 55)         # lv = 55
    a.bl("show_dialog_n")
    a.b("ia_ret")
    a.label("ia_sec151_locked")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_qgive")
    a.ldrb_imm(4, 10, 14)    # q_give
    a.cmp_imm(4, 0xFF)
    a.b("ia_chk_qstep", cond=0x0)
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 4, shift_type=0) # mask = 1 << qid
    a.ldrh_imm(0, 6, 0x42)   # questsDoneMask
    a.tst_reg(0, 1)
    a.mov_imm(0, 1, cond=0x1)
    a.b("ia_qgive_show", cond=0x1)
    a.ldrh_imm(0, 6, 0x44)   # questsStartedMask
    a.tst_reg(0, 1)
    a.b("ia_qgive_already_started", cond=0x1)
    a.orr_reg(0, 0, 1)
    a.strh_imm(0, 6, 0x44)
    a.add_reg(2, 6, 4)
    a.mov_imm(0, 0)
    a.strb_imm(0, 2, 0x46)   # questSteps[qid] = 0
    a.label("ia_qgive_already_started")
    a.ldrb_imm(0, 10, 20)    # len(npc.lines)
    a.label("ia_qgive_show")
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_qstep")
    a.ldrb_imm(4, 10, 15)    # q_step
    a.cmp_imm(4, 0xFF)
    a.b("ia_chk_qcomp", cond=0x0)
    a.ldrb_imm(5, 10, 16)    # step_idx
    a.cmp_imm(5, 0)
    a.mov_imm(5, 1, cond=0x0)
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 4, shift_type=0)
    a.ldrh_imm(0, 6, 0x42)   # questsDoneMask
    a.tst_reg(0, 1)
    a.mov_imm(0, 1, cond=0x1)
    a.b("ia_qstep_show", cond=0x1)
    a.ldrh_imm(0, 6, 0x44)   # questsStartedMask
    a.tst_reg(0, 1)
    a.b("ia_qstep_not_ready", cond=0x0)
    a.add_reg(2, 6, 4)
    a.ldrb_imm(0, 2, 0x46)   # curStep
    a.sub_imm(3, 5, 1)       # idx - 1
    a.cmp_reg(0, 3)
    a.b("ia_qstep_not_ready", cond=0x3) # curStep < idx - 1
    a.strb_imm(5, 2, 0x46, cond=0x0)    # if curStep == idx - 1: questSteps[qid] = idx
    a.ldrb_imm(0, 10, 20)    # len(npc.lines)
    a.b("ia_qstep_show")
    a.label("ia_qstep_not_ready")
    a.ldrb_imm(0, 10, 23)    # len(notReadyLines) | (has << 4)
    a.and_imm(0, 0, 0xF)
    a.cmp_imm(0, 0)
    a.mov_imm(0, 1, cond=0x0)
    a.label("ia_qstep_show")
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_qcomp")
    a.ldrb_imm(4, 10, 17)    # q_comp
    a.cmp_imm(4, 0xFF)
    a.b("ia_chk_sec", cond=0x0)
    # Look up QUESTS[qid].steps in Table 12 (20 bytes per quest, steps at +8)
    a.mov_imm(0, 20)
    a.mul(0, 4, 0)
    a.mov_imm(1, table_addrs[12])
    a.add_reg(0, 1, 0)
    a.ldr_imm(5, 0, 8)       # steps
    a.sub_imm(5, 5, 1, s=1)
    a.mov_imm(5, 0, cond=0x4) # reqSteps = max(0, steps - 1)

    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 4, shift_type=0)
    a.ldrh_imm(0, 6, 0x44)   # questsStartedMask
    a.tst_reg(0, 1)
    a.b("ia_qcomp_not_started", cond=0x0)
    a.add_reg(2, 6, 4)
    a.ldrb_imm(0, 2, 0x46)   # curStep
    a.cmp_reg(0, 5)
    a.b("ia_qcomp_not_ready", cond=0x3) # curStep < reqSteps
    # Complete quest!
    a.ldrh_imm(0, 6, 0x42)   # questsDoneMask
    a.orr_reg(0, 0, 1)
    a.strh_imm(0, 6, 0x42)
    a.mov_reg(0, 4)
    a.bl("grant_quest_reward")
    a.ldrb_imm(0, 10, 20)    # len(npc.lines)
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_qcomp_not_started")
    a.ldrb_imm(0, 10, 22)    # len(notStartedLines)
    a.and_imm(0, 0, 0xF)
    a.cmp_imm(0, 0)
    a.b("ia_qcomp_show", cond=0x1)
    a.label("ia_qcomp_not_ready")
    a.ldrb_imm(0, 10, 23)    # len(notReadyLines)
    a.and_imm(0, 0, 0xF)
    a.cmp_imm(0, 0)
    a.mov_imm(0, 1, cond=0x0)
    a.label("ia_qcomp_show")
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_sec")
    a.ldrb_imm(4, 10, 18)    # sec_idx
    a.cmp_imm(4, 0xFF)
    a.b("ia_chk_trainer", cond=0x0)
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 4, shift_type=0)
    a.ldrh_imm(0, 6, 0x40)   # secretsMask
    a.tst_reg(0, 1)
    a.b("ia_sec_show", cond=0x1)
    a.orr_reg(0, 0, 1)
    a.strh_imm(0, 6, 0x40)
    a.ldr_imm(0, 6, 0x24)    # gold += 150
    a.add_imm(0, 0, 150)
    a.str_imm(0, 6, 0x24)
    a.label("ia_sec_show")
    a.ldrb_imm(0, 10, 20)    # len(npc.lines)
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_trainer")
    a.ldrb_imm(4, 10, 19)    # tr_idx
    a.cmp_imm(4, 0xFF)
    a.b("ia_normal_npc", cond=0x0)
    a.mov_reg(0, 4, shift_imm=3, shift_type=1)
    a.and_imm(1, 4, 7)
    a.mov_imm(2, 1)
    a.mov_reg_rs(2, 2, 1, shift_type=0)
    a.add_reg(0, 6, 0)
    a.ldrb_imm(0, 0, 0x38)   # defeatedTrainersBits
    a.tst_reg(0, 2)
    a.b("ia_tr_defeated", cond=0x1)
    # Not defeated -> 1 line intro, cb = START_TRAINER (3), arg0 = tr_idx
    a.mov_imm(0, 1); a.mov_imm(1, 3); a.mov_reg(2, 4); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")
    a.label("ia_tr_defeated")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_normal_npc")
    # Check if Brotholomew (npc_global_idx == 256) and all 151 caught
    a.ldrh_imm(0, 10, 24)
    a.cmp_imm(0, 256)
    a.b("ia_not_broth_151", cond=0x1)
    a.ldr_imm(0, 6, 0x6A)
    a.ldr_imm(1, 6, 0x6E)
    a.and_reg(0, 0, 1)
    a.ldr_imm(1, 6, 0x72)
    a.and_reg(0, 0, 1)
    a.ldr_imm(1, 6, 0x76)
    a.and_reg(0, 0, 1)
    a.cmn_imm(0, 1)          # R0 == 0xFFFFFFFF?
    a.b("ia_not_broth_151", cond=0x1)
    a.ldrh_imm(0, 6, 0x7A)
    a.mov_imm(1, 0xFFFF)
    a.cmp_reg(0, 1)
    a.b("ia_not_broth_151", cond=0x1)
    a.ldrb_imm(0, 6, 0x7C)
    a.and_imm(0, 0, 0x7F)
    a.cmp_imm(0, 0x7F)
    a.b("ia_not_broth_151", cond=0x1)
    a.mov_imm(0, 2); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")
    a.label("ia_not_broth_151")
    # Check if isNight && has_nightLines
    a.ldrb_imm(0, 6, 0x2C)   # isNight
    a.ldrb_imm(1, 10, 21)    # len(nlines) | (has_nlines << 4)
    a.cmp_imm(0, 0)
    a.b("ia_use_day_lines", cond=0x0)
    a.tst_imm(1, 0x10)
    a.b("ia_use_day_lines", cond=0x0)
    a.and_imm(0, 1, 0xF)
    a.b("ia_show_norm")
    a.label("ia_use_day_lines")
    a.ldrb_imm(0, 10, 20)    # len(lines)
    a.label("ia_show_norm")
    a.cmp_imm(0, 0)
    a.mov_imm(0, 1, cond=0x0)
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")

    a.label("ia_ret")
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])
    a.flush_literals()

    # Patch handle_battle_input's finishBattle branch: let's make sure handle_battle_input calls finish_battle_full!
    # Wait: in emit_core_and_battle, when pending_end != 0 on LOG screen, let's check what it did:
    # It set active=0, phase=0, screen=3. If we call finish_battle_full in press_button when BATTLE finishes or inside handle_battle_input,
    # let's check: in press_button, if screen == BATTLE, we can check if b.phase == LOG and btn in (A, B) and b.pending_end != 0 -> call finish_battle_full(b.pending_end)!
    # That handles BOTH standalone handle_battle_input AND full-game trainer rewards/credits/seals!

    # press_button(R0=btn: 0=A, 1=B, 2=SELECT, 3=START, 4=RIGHT, 5=LEFT, 6=UP, 7=DOWN, 8=R, 9=L)
    a.label("press_button")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.sub_imm(13, 13, 32)
    a.mov_reg(4, 0)          # R4 = btn
    a.mov_imm(5, 0x02001000) # R5 = RSTATE
    a.mov_imm(6, 0x02000000) # R6 = GSTATE
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x45)   # dirty_ui = 1
    a.ldrb_imm(7, 5, 0x20)   # R7 = screen_id

    # Screen 0: TITLE
    a.cmp_imm(7, 0)
    a.b("pb_chk_slots", cond=0x1)
    a.mov_imm(0, 0); a.bl("play_music")
    a.ldrb_imm(8, 5, 0x21)   # cursor
    a.cmp_imm(4, 6)          # UP
    a.add_imm(8, 8, 2, cond=0x0); a.b("pb_title_mod", cond=0x0)
    a.cmp_imm(4, 7)          # DOWN
    a.add_imm(8, 8, 1, cond=0x0); a.b("pb_title_mod", cond=0x0)
    a.cmp_imm(4, 0); a.cmp_imm(4, 3, cond=0x1) # A or START
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(8, 0)
    a.mov_imm(0, 1, cond=0x0) # SLOTS
    a.cmp_imm(8, 1)
    a.mov_imm(0, 13, cond=0x0) # OPTIONS
    a.cmp_imm(8, 2)
    a.mov_imm(0, 14, cond=0x0) # CONTROLS
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x21)
    a.b("pb_ret")
    a.label("pb_title_mod")
    a.mov_reg(0, 8); a.mov_imm(1, 3); a.bl("udiv32")
    a.strb_imm(1, 5, 0x21)
    a.b("pb_ret")

    # Screen 1: SLOTS
    a.label("pb_chk_slots")
    a.cmp_imm(7, 1)
    a.b("pb_chk_starter", cond=0x1)
    a.ldrb_imm(8, 5, 0x21)   # cursor
    a.cmp_imm(4, 6)          # UP
    a.add_imm(8, 8, 2, cond=0x0); a.b("pb_title_mod", cond=0x0)
    a.cmp_imm(4, 7)          # DOWN
    a.add_imm(8, 8, 1, cond=0x0); a.b("pb_title_mod", cond=0x0)
    a.cmp_imm(4, 1)          # B
    a.mov_imm(0, 0, cond=0x0)
    a.strb_imm(0, 5, 0x20, cond=0x0)
    a.strb_imm(0, 5, 0x21, cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 0); a.cmp_imm(4, 3, cond=0x1) # A or START
    a.b("pb_ret", cond=0x1)
    a.mov_reg(0, 8)
    a.bl("load_from_slot")
    a.cmp_imm(0, 0)
    a.b("pb_ret", cond=0x1)  # loaded existing save!
    a.strb_imm(8, 5, 0x1F)   # active_slot = cursor
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x2A)   # starter_idx = 0
    a.mov_imm(0, 2)          # screen = STARTER (2)
    a.strb_imm(0, 5, 0x20)
    a.b("pb_ret")

    # Screen 2: STARTER
    a.label("pb_chk_starter")
    a.cmp_imm(7, 2)
    a.b("pb_chk_name_entry", cond=0x1)
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1) # UP or DOWN -> look_idx
    a.b("pb_st_lr", cond=0x1)
    a.ldrb_imm(0, 5, 0x2B)
    a.cmp_imm(4, 7)
    a.add_imm(0, 0, 1, cond=0x0)
    a.add_imm(0, 0, 2, cond=0x1)
    a.mov_imm(1, 3); a.bl("udiv32")
    a.strb_imm(1, 5, 0x2B)
    a.b("pb_ret")
    a.label("pb_st_lr")
    a.cmp_imm(4, 4); a.cmp_imm(4, 5, cond=0x1) # RIGHT or LEFT (or R/L)
    a.cmp_imm(4, 8, cond=0x1); a.cmp_imm(4, 9, cond=0x1)
    a.b("pb_st_start", cond=0x1)
    a.ldrb_imm(0, 5, 0x2A)
    a.cmp_imm(4, 4); a.cmp_imm(4, 8, cond=0x1)
    a.add_imm(0, 0, 1, cond=0x0)
    a.add_imm(0, 0, 3, cond=0x1)
    a.and_imm(0, 0, 3)
    a.strb_imm(0, 5, 0x2A)
    a.b("pb_ret")
    a.label("pb_st_start")
    a.cmp_imm(4, 3); a.cmp_imm(4, 2, cond=0x1) # START or SELECT -> NAME_ENTRY (16)
    a.b("pb_st_ab", cond=0x1)
    a.mov_imm(0, 16)
    a.strb_imm(0, 5, 0x20)
    a.b("pb_ret")
    a.label("pb_st_ab")
    a.cmp_imm(4, 1) # B -> SLOTS
    a.mov_imm(0, 1, cond=0x0)
    a.strb_imm(0, 5, 0x20, cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 0) # A -> start_new_game!
    a.b("pb_ret", cond=0x1)
    a.ldrb_imm(1, 5, 0x2A) # starter_idx (0..3 -> 1, 39, 77, 115)
    a.mov_imm(2, 38)
    a.mul(1, 1, 2)
    a.add_imm(1, 1, 1)     # starterId = 1 + starter_idx * 38
    a.ldrb_imm(0, 5, 0x1F) # active_slot
    a.mov_imm(2, 4242)     # seed = 4242
    a.bl("start_new_game")
    a.b("pb_ret")

    # Screen 16: NAME_ENTRY (On-Screen Keyboard)
    a.label("pb_chk_name_entry")
    a.cmp_imm(7, 16)
    a.b("pb_chk_dialog", cond=0x1)
    # 10x4 grid: x in 0..9, y in 0..3. L toggles upper/lower, B deletes char, START/R confirms, A adds char
    a.add_imm(8, 5, 0x90)  # 0x02001090: +0=cx, +1=cy, +2=upper, +3=len, +4..15=custom_name
    a.ldrb_imm(0, 8, 0)    # cx
    a.ldrb_imm(1, 8, 1)    # cy
    a.cmp_imm(4, 4)        # RIGHT
    a.add_imm(0, 0, 1, cond=0x0); a.cmp_imm(0, 10, cond=0x0); a.mov_imm(0, 0, cond=0x2); a.strb_imm(0, 8, 0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 5)        # LEFT
    a.sub_imm(0, 0, 1, s=1, cond=0x0); a.mov_imm(0, 9, cond=0x4); a.strb_imm(0, 8, 0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 7)        # DOWN
    a.add_imm(1, 1, 1, cond=0x0); a.and_imm(1, 1, 3, cond=0x0); a.strb_imm(1, 8, 1); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 6)        # UP
    a.sub_imm(1, 1, 1, cond=0x0); a.and_imm(1, 1, 3, cond=0x0); a.strb_imm(1, 8, 1); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 9)        # L -> toggle case
    a.ldrb_imm(2, 8, 2, cond=0x0); a.eor_imm(2, 2, 1, cond=0x0); a.strb_imm(2, 8, 2, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 3); a.cmp_imm(4, 8, cond=0x1) # START or R -> confirm and return to STARTER (2)
    a.mov_imm(0, 2, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 1)        # B -> backspace
    a.b("pb_ne_a", cond=0x1)
    a.ldrb_imm(2, 8, 3)    # len
    a.cmp_imm(2, 0)
    a.b("pb_ret", cond=0x0)
    a.sub_imm(2, 2, 1)
    a.strb_imm(2, 8, 3)
    a.add_reg(3, 8, 2)
    a.mov_imm(0, 0)
    a.strb_imm(0, 3, 4)
    a.b("pb_ret")
    a.label("pb_ne_a")
    a.cmp_imm(4, 0)        # A -> append character at (cx, cy) (or if cy==3 && cx==9 -> confirm!)
    a.b("pb_ret", cond=0x1)
    a.mov_imm(2, 10)
    a.mul(2, 1, 2)
    a.add_reg(2, 2, 0)     # idx = cy * 10 + cx (0..39)
    a.cmp_imm(2, 39)       # cell 39 = OK!
    a.mov_imm(0, 2, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.ldrb_imm(3, 8, 3)    # len
    a.cmp_imm(3, 10)
    a.b("pb_ret", cond=0x2)
    # Map idx 0..25 -> 'A'+idx (or 'a'+idx if upper==0), 26..35 -> '0'+(idx-26), 36..38 -> ' '
    a.mov_imm(0, 32)       # default space
    a.cmp_imm(2, 26)
    a.b("pb_ne_digit", cond=0x2)
    a.ldrb_imm(1, 8, 2)    # upper
    a.cmp_imm(1, 0)
    a.add_imm(0, 2, 97, cond=0x0) # 'a' + idx
    a.add_imm(0, 2, 65, cond=0x1) # 'A' + idx
    a.b("pb_ne_store")
    a.label("pb_ne_digit")
    a.cmp_imm(2, 36)
    a.add_imm(0, 2, 48 - 26, cond=0x3)
    a.label("pb_ne_store")
    a.add_reg(1, 8, 3)
    a.strb_imm(0, 1, 4)
    a.add_imm(3, 3, 1)
    a.strb_imm(3, 8, 3)
    a.mov_imm(0, 0)
    a.strb_imm(0, 1, 5)
    a.b("pb_ret")

    # Screen 4: DIALOG
    a.label("pb_chk_dialog")
    a.cmp_imm(7, 4)
    a.b("pb_chk_learn", cond=0x1)
    a.cmp_imm(4, 0); a.cmp_imm(4, 1, cond=0x1) # A or B
    a.b("pb_ret", cond=0x1)
    a.ldrb_imm(0, 5, 0x41) # dialog_idx
    a.ldrb_imm(1, 5, 0x40) # dialog_count
    a.add_imm(0, 0, 1)
    a.cmp_reg(0, 1)
    a.strb_imm(0, 5, 0x41, cond=0x3)
    a.b("pb_ret", cond=0x3)
    # Dialog finished! Default screen = OVERWORLD (3), then run callback if any
    a.mov_imm(0, 3)
    a.strb_imm(0, 5, 0x20)
    a.ldrb_imm(1, 5, 0x42) # dialog_cb_kind
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x42)
    a.cmp_imm(1, 1)        # PLAY_MAP_MUSIC
    a.bl("play_map_music", cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(1, 2)        # START_WILD
    a.b("pb_dlg_cb3", cond=0x1)
    a.ldrb_imm(0, 5, 0x43) # spId
    a.ldrb_imm(1, 5, 0x44) # lv
    a.bl("start_wild_battle")
    a.b("pb_ret")
    a.label("pb_dlg_cb3")
    a.cmp_imm(1, 3)        # START_TRAINER
    a.b("pb_dlg_cb4", cond=0x1)
    a.ldrb_imm(0, 5, 0x43) # trainer_idx
    a.bl("start_trainer_battle")
    a.b("pb_ret")
    a.label("pb_dlg_cb4")
    a.cmp_imm(1, 4)        # START_CREDITS
    a.b("pb_ret", cond=0x1)
    a.mov_imm(0, 0)
    a.strh_imm(0, 5, 0x38) # credits_scroll_px = 0
    a.mov_imm(0, 15)       # screen = CREDITS (15)
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 17)       # 'credits' track
    a.bl("play_music")
    a.b("pb_ret")

    # Screen 12: LEARN_MOVE
    a.label("pb_chk_learn")
    a.cmp_imm(7, 12)
    a.b("pb_chk_ow", cond=0x1)
    a.ldrb_imm(8, 5, 0x29) # learn_cursor
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1) # UP or DOWN
    a.b("pb_lm_ab", cond=0x1)
    a.cmp_imm(4, 7)
    a.add_imm(0, 8, 1, cond=0x0)
    a.add_imm(0, 8, 4, cond=0x1)
    a.mov_imm(1, 5); a.bl("udiv32")
    a.strb_imm(1, 5, 0x29)
    a.b("pb_ret")
    a.label("pb_lm_ab")
    a.cmp_imm(4, 1) # B -> cancel
    a.b("pb_lm_a", cond=0x1)
    a.ldrb_imm(0, 5, 0x3F) # returnScreen
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 0); a.strb_imm(0, 5, 0x3C)
    a.b("pb_ret")
    a.label("pb_lm_a")
    a.cmp_imm(4, 0) # A
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(8, 4)
    a.b("pb_lm_done", cond=0x2)
    # Replace slot R8 on party[pending_learn_mon_idx] with pending_learn_move_id
    a.ldrb_imm(0, 5, 0x3D) # mon_idx
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.add_imm(0, 6, 0x0B4)
    a.add_reg(0, 0, 8)
    a.ldrb_imm(1, 5, 0x3E) # moveId
    a.strb_imm(1, 0, 0x1C)
    a.mov_imm(2, 36)
    a.mul(2, 1, 2)
    a.mov_imm(3, table_addrs[3])
    a.add_reg(2, 3, 2)
    a.ldrb_imm(2, 2, 4)    # mv.pp
    a.strb_imm(2, 0, 0x20)
    a.strb_imm(2, 0, 0x24)
    a.label("pb_lm_done")
    a.ldrb_imm(0, 5, 0x3F)
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 0); a.strb_imm(0, 5, 0x3C)
    a.b("pb_ret")

    # Screen 3: OVERWORLD
    a.label("pb_chk_ow")
    a.cmp_imm(7, 3)
    a.b("pb_chk_menu", cond=0x1)
    a.cmp_imm(4, 3) # START -> MENU (6)
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0)
    a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x22, cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 2) # SELECT -> toggle Day/Night + 1-line dialog
    a.b("pb_ow_a", cond=0x1)
    a.ldrb_imm(0, 6, 0x2C)
    a.eor_imm(0, 0, 1)
    a.strb_imm(0, 6, 0x2C)
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("pb_ret")
    a.label("pb_ow_a")
    a.cmp_imm(4, 0) # A -> interact_ahead
    a.bl("interact_ahead", cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 9) # L -> DEX (7) shortcut
    a.mov_imm(0, 7, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 8) # R -> BAG (10) shortcut
    a.mov_imm(0, 10, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    # D-Pad: 6=UP->1, 7=DOWN->0, 5=LEFT->2, 4=RIGHT->3
    a.cmp_imm(4, 6); a.mov_imm(0, 1, cond=0x0); a.b("pb_ow_move", cond=0x0)
    a.cmp_imm(4, 7); a.mov_imm(0, 0, cond=0x0); a.b("pb_ow_move", cond=0x0)
    a.cmp_imm(4, 5); a.mov_imm(0, 2, cond=0x0); a.b("pb_ow_move", cond=0x0)
    a.cmp_imm(4, 4); a.mov_imm(0, 3, cond=0x0); a.b("pb_ow_move", cond=0x0)
    a.b("pb_ret")
    a.label("pb_ow_move")
    a.mov_imm(1, 0)
    a.bl("try_move")
    a.mov_imm(0, 9) # moveCooldown = 0.14s (~9 frames)
    a.strb_imm(0, 5, 0x2D)
    a.b("pb_ret")

    # Screen 6: MENU
    a.label("pb_chk_menu")
    a.cmp_imm(7, 6)
    a.b("pb_chk_dex", cond=0x1)
    a.ldrb_imm(8, 5, 0x22) # menu_cursor (0..7)
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1)
    a.b("pb_menu_bs", cond=0x1)
    a.cmp_imm(4, 7)
    a.add_imm(8, 8, 1, cond=0x0)
    a.add_imm(8, 8, 7, cond=0x1)
    a.and_imm(8, 8, 7)
    a.strb_imm(8, 5, 0x22)
    a.b("pb_ret")
    a.label("pb_menu_bs")
    a.cmp_imm(4, 1); a.cmp_imm(4, 3, cond=0x1) # B or START
    a.mov_imm(0, 3, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 0) # A
    a.b("pb_ret", cond=0x1)
    # 0=PARTY(8), 1=DEX(7), 2=BOX(9), 3=BAG(10), 4=SAVE, 5=OPTIONS(13), 6=CONTROLS(14), 7=CLOSE(3)
    a.cmp_imm(8, 0); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x25, cond=0x0); a.mov_imm(0, 8, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 1); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x23, cond=0x0); a.strb_imm(0, 5, 0x24, cond=0x0); a.mov_imm(0, 7, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 2); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x26, cond=0x0); a.mov_imm(0, 9, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 3); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x27, cond=0x0); a.mov_imm(0, 10, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 4)
    a.b("pb_menu_opt", cond=0x1)
    a.ldrb_imm(0, 5, 0x1F)
    a.bl("save_to_slot")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("pb_ret")
    a.label("pb_menu_opt")
    a.cmp_imm(8, 5); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x21, cond=0x0); a.mov_imm(0, 13, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 6); a.mov_imm(0, 14, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.mov_imm(0, 3); a.strb_imm(0, 5, 0x20); a.b("pb_ret")

    # Screen 7: DEX
    a.label("pb_chk_dex")
    a.cmp_imm(7, 7)
    a.b("pb_chk_party", cond=0x1)
    a.cmp_imm(4, 1) # B -> MENU (6)
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    # maxEntries = (seen(151) || caught(151)) ? 151 : 150
    a.ldrb_imm(0, 6, 0x56 + 18)
    a.ldrb_imm(1, 6, 0x6A + 18)
    a.orr_reg(0, 0, 1)
    a.tst_imm(0, 1 << 6)
    a.mov_imm(9, 150, cond=0x0) # maxIdx = 149 or 150
    a.mov_imm(9, 151, cond=0x1)
    a.sub_imm(9, 9, 1)
    a.ldrb_imm(8, 5, 0x23) # dex_cursor
    a.cmp_imm(4, 6) # UP
    a.sub_imm(8, 8, 1, s=1, cond=0x0); a.mov_imm(8, 0, cond=0x4)
    a.cmp_imm(4, 7) # DOWN
    a.add_imm(8, 8, 1, cond=0x0)
    a.cmp_imm(4, 5); a.cmp_imm(4, 9, cond=0x1) # LEFT or L
    a.sub_imm(8, 8, 10, s=1, cond=0x0); a.mov_imm(8, 0, cond=0x4)
    a.cmp_imm(4, 4); a.cmp_imm(4, 8, cond=0x1) # RIGHT or R
    a.add_imm(8, 8, 10, cond=0x0)
    a.cmp_reg(8, 9)
    a.mov_reg(8, 9, cond=0x8)
    a.strb_imm(8, 5, 0x23)
    # Update dex_scroll
    a.ldrb_imm(0, 5, 0x24)
    a.cmp_reg(8, 0)
    a.mov_reg(0, 8, cond=0x3)
    a.add_imm(1, 0, 7)
    a.cmp_reg(8, 1)
    a.sub_imm(0, 8, 6, cond=0x2)
    a.strb_imm(0, 5, 0x24)
    a.b("pb_ret")

    # Screen 8: PARTY
    a.label("pb_chk_party")
    a.cmp_imm(7, 8)
    a.b("pb_chk_box", cond=0x1)
    a.cmp_imm(4, 1) # B -> MENU
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.ldrb_imm(8, 5, 0x25) # party_cursor
    a.ldrb_imm(9, 6, 0x0B0) # partyCount
    a.sub_imm(9, 9, 1)
    a.cmp_imm(4, 6) # UP
    a.sub_imm(8, 8, 1, s=1, cond=0x0); a.mov_imm(8, 0, cond=0x4); a.strb_imm(8, 5, 0x25); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 7) # DOWN
    a.add_imm(8, 8, 1, cond=0x0); a.cmp_reg(8, 9, cond=0x0); a.mov_reg(8, 9, cond=0x8); a.strb_imm(8, 5, 0x25); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 0) # A -> swap party[0] and party[party_cursor] if party_cursor > 0
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(8, 0)
    a.b("pb_ret", cond=0x0)
    a.mov_imm(0, 48)
    a.mul(0, 8, 0)
    a.add_imm(1, 6, 0x0B4) # party[0]
    a.add_reg(2, 1, 0)     # party[party_cursor]
    for off in range(0, 48, 4):
        a.ldr_imm(0, 1, off)
        a.ldr_imm(3, 2, off)
        a.str_imm(3, 1, off)
        a.str_imm(0, 2, off)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x25)
    a.b("pb_ret")

    # Screen 9: BOX
    a.label("pb_chk_box")
    a.cmp_imm(7, 9)
    a.b("pb_chk_bag", cond=0x1)
    a.cmp_imm(4, 1) # B -> MENU
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.ldrb_imm(8, 5, 0x26)  # box_cursor
    a.ldrb_imm(9, 6, 0x0B1) # boxCount
    a.cmp_imm(4, 6) # UP
    a.sub_imm(8, 8, 1, s=1, cond=0x0); a.mov_imm(8, 0, cond=0x4); a.strb_imm(8, 5, 0x26); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 7) # DOWN
    a.b("pb_box_a", cond=0x1)
    a.cmp_imm(9, 0)
    a.b("pb_ret", cond=0x0)
    a.sub_imm(0, 9, 1)
    a.add_imm(8, 8, 1)
    a.cmp_reg(8, 0)
    a.mov_reg(8, 0, cond=0x8)
    a.strb_imm(8, 5, 0x26)
    a.b("pb_ret")
    a.label("pb_box_a")
    a.cmp_imm(4, 0) # A -> withdraw from box[box_cursor] to party if boxCount > 0 && partyCount < 6
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(9, 0)
    a.b("pb_ret", cond=0x0)
    a.ldrb_imm(0, 6, 0x0B0) # partyCount
    a.cmp_imm(0, 6)
    a.b("pb_ret", cond=0x2)
    # Unpack 24B BoxMon at 0x020001D4 + box_cursor * 24 into 48B PartyMon at 0x020000B4 + partyCount * 48
    a.mov_imm(1, 48)
    a.mul(1, 0, 1)
    a.add_imm(0, 0, 1)
    a.strb_imm(0, 6, 0x0B0) # partyCount++
    a.add_imm(1, 1, 0x0B4)
    a.add_reg(1, 6, 1)      # R1 = dst PartyMon (48B)
    a.mov_imm(2, 24)
    a.mul(2, 8, 2)
    a.mov_imm(3, 0x020001D4)
    a.add_reg(2, 3, 2)      # R2 = src BoxMon (24B)

    a.mov_imm(0, 0)
    for off in range(0, 48, 4):
        a.str_imm(0, 1, off)
    a.ldr_imm(0, 2, 0x00); a.str_imm(0, 1, 0x00) # uid
    a.ldr_imm(0, 2, 0x04); a.str_imm(0, 1, 0x04) # spId, level, status
    a.mov_imm(0, 0xFF); a.strb_imm(0, 1, 0x07)   # lastMoveType = 0xFF
    a.ldrb_imm(0, 2, 0x07); a.strh_imm(0, 1, 0x12) # moveCount
    a.ldr_imm(0, 2, 0x08); a.str_imm(0, 1, 0x08) # hp, maxHp
    a.ldr_imm(0, 2, 0x0C); a.str_imm(0, 1, 0x0C) # atk, def
    a.ldrh_imm(0, 2, 0x10); a.strh_imm(0, 1, 0x10) # spd
    a.ldrh_imm(0, 2, 0x12); a.mov_reg(0, 0, shift_imm=3, shift_type=0); a.str_imm(0, 1, 0x14) # xp
    a.ldrb_imm(0, 2, 0x05); a.add_imm(0, 0, 1); a.mul(0, 0, 0); a.mov_reg(0, 0, shift_imm=3, shift_type=0); a.str_imm(0, 1, 0x18) # nextXp
    a.ldr_imm(0, 2, 0x14); a.str_imm(0, 1, 0x1C) # moveIds[4]
    for m_i in range(4):
        a.ldrb_imm(0, 1, 0x1C + m_i)
        a.cmp_imm(0, 0xFF)
        a.b(f"pb_box_mv_{m_i}", cond=0x0)
        a.mov_imm(3, 36)
        a.mul(0, 0, 3)
        a.mov_imm(3, table_addrs[3])
        a.add_reg(0, 3, 0)
        a.ldrb_imm(0, 0, 4) # mv.pp
        a.strb_imm(0, 1, 0x20 + m_i)
        a.strb_imm(0, 1, 0x24 + m_i)
        a.label(f"pb_box_mv_{m_i}")

    # Shift remaining BoxMons left by 24 bytes
    a.sub_imm(9, 9, 1)
    a.strb_imm(9, 6, 0x0B1) # boxCount--
    a.mov_reg(0, 8)         # i = box_cursor
    a.label("pb_box_shift")
    a.cmp_reg(0, 9)
    a.b("pb_box_shift_done", cond=0x2)
    for w_i in range(0, 24, 4):
        a.ldr_imm(3, 2, 24 + w_i)
        a.str_imm(3, 2, w_i)
    a.add_imm(2, 2, 24)
    a.add_imm(0, 0, 1)
    a.b("pb_box_shift")
    a.label("pb_box_shift_done")
    a.sub_imm(8, 8, 1, s=1)
    a.mov_imm(8, 0, cond=0x4)
    a.strb_imm(8, 5, 0x26)
    a.b("pb_ret")

    # Screen 10: BAG
    a.label("pb_chk_bag")
    a.cmp_imm(7, 10)
    a.b("pb_chk_shop", cond=0x1)
    a.cmp_imm(4, 1) # B -> MENU
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.mov_imm(0, 0)
    a.mov_reg(1, 13)
    a.bl("build_bag_filter")
    a.mov_reg(9, 0) # R9 = keys.length
    a.cmp_imm(9, 0)
    a.b("pb_ret", cond=0x0)
    a.ldrb_imm(8, 5, 0x27) # bag_cursor
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1) # UP or DOWN
    a.b("pb_bag_a", cond=0x1)
    a.cmp_imm(4, 7)
    a.add_imm(0, 8, 1, cond=0x0)
    a.add_reg(0, 8, 9, cond=0x1)
    a.sub_imm(0, 0, 1, cond=0x1)
    a.mov_reg(1, 9); a.bl("udiv32")
    a.strb_imm(1, 5, 0x27)
    a.b("pb_ret")
    a.label("pb_bag_a")
    a.cmp_imm(4, 0) # A
    a.b("pb_ret", cond=0x1)
    a.add_reg(0, 13, 8)
    a.ldrb_imm(7, 0, 0) # R7 = item_idx = keys[bag_cursor]
    a.mov_imm(0, 28)
    a.mul(0, 7, 0)
    a.mov_imm(1, table_addrs[8])
    a.add_reg(8, 1, 0)  # R8 = item_ptr
    a.add_imm(9, 6, 0x0B4) # R9 = lead mon (party[0])
    a.ldrb_imm(0, 8, 0) # item.kind (1=heal, 2=cure, 5=recipe)
    a.cmp_imm(0, 1); a.cmp_imm(0, 2, cond=0x1)
    a.b("pb_bag_recipe", cond=0x1)
    a.ldrh_imm(1, 9, 0x08) # lead.hp
    a.cmp_imm(1, 0)
    a.b("pb_ret", cond=0x0) # fainted
    a.ldrh_imm(2, 9, 0x0A) # lead.maxHp
    a.ldrh_imm(3, 8, 2)    # item.healHp
    a.add_reg(1, 1, 3)
    a.cmp_reg(1, 2)
    a.mov_reg(1, 2, cond=0x8)
    a.strh_imm(1, 9, 0x08)
    a.cmp_imm(0, 2)
    a.cmp_imm(7, 7, cond=0x1) # grand_feast
    a.mov_imm(1, 0, cond=0x0)
    a.strb_imm(1, 9, 0x06, cond=0x0)
    a.mov_reg(0, 7); a.mvn_imm(1, 0); a.bl("bag_add")
    a.b("pb_ret")

    a.label("pb_bag_recipe")
    a.cmp_imm(0, 5) # 5 == 'recipe'
    a.b("pb_ret", cond=0x1)
    a.mov_reg(0, 7); a.mvn_imm(1, 0); a.bl("bag_add")
    a.ldrh_imm(7, 8, 4) # moveId
    # Check if lead already knows moveId
    a.ldrh_imm(1, 9, 0x12) # moveCount
    a.mov_imm(2, 0)
    a.label("pb_rec_chk")
    a.cmp_reg(2, 1)
    a.b("pb_rec_teach", cond=0x2)
    a.add_reg(0, 9, 2)
    a.ldrb_imm(0, 0, 0x1C)
    a.cmp_reg(0, 7)
    a.b("pb_ret", cond=0x0)
    a.add_imm(2, 2, 1)
    a.b("pb_rec_chk")
    a.label("pb_rec_teach")
    a.cmp_imm(1, 4)
    a.b("pb_rec_prompt", cond=0x2)
    a.add_reg(0, 9, 1)
    a.strb_imm(7, 0, 0x1C)
    a.mov_imm(2, 36); a.mul(2, 7, 2); a.mov_imm(3, table_addrs[3]); a.add_reg(2, 3, 2)
    a.ldrb_imm(2, 2, 4)
    a.strb_imm(2, 0, 0x20); a.strb_imm(2, 0, 0x24)
    a.add_imm(1, 1, 1); a.strh_imm(1, 9, 0x12)
    a.b("pb_ret")
    a.label("pb_rec_prompt")
    a.mov_imm(0, 1); a.strb_imm(0, 5, 0x3C) # pending_learn_active = 1
    a.mov_imm(0, 0); a.strb_imm(0, 5, 0x3D) # mon_idx = 0
    a.strb_imm(7, 5, 0x3E)                  # moveId
    a.mov_imm(0, 10); a.strb_imm(0, 5, 0x3F) # retScreen = BAG(10)
    a.mov_imm(0, 0); a.strb_imm(0, 5, 0x29)  # learn_cursor = 0
    a.mov_imm(0, 12); a.strb_imm(0, 5, 0x20) # screen = LEARN_MOVE(12)
    a.b("pb_ret")

    # Screen 11: SHOP
    a.label("pb_chk_shop")
    a.cmp_imm(7, 11)
    a.b("pb_chk_battle", cond=0x1)
    a.cmp_imm(4, 1) # B -> OVERWORLD (3)
    a.mov_imm(0, 3, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    # Determine current shop index from map.region_str_off or mapId:
    # Let's check which maps belong to which region in Table 9 (0=Breadlands, 1=Steambay, 2=Noodleridge, 3=Brothbasin, 4=Postgame):
    # In REGIONAL_SHOPS, each entry in Table 9 is 36 bytes: +0=rname_str_off, +4=clerk_str_off, +8=stock_len, +12=stock[24]!
    # And in Table 10 (MAPS), map header +8 is region_str_off!
    a.ldrb_imm(0, 6, 0x28) # mapId
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(0, 1, 0)
    a.ldr_imm(2, 0, 8)     # map.region_str_off
    a.mov_imm(7, table_addrs[9]) # REGIONAL_SHOPS
    a.mov_imm(0, 0)
    a.label("pb_shop_find")
    a.cmp_imm(0, 5)
    a.b("pb_shop_found", cond=0x2)
    a.ldr_imm(1, 7, 0)
    a.cmp_reg(1, 2)
    a.b("pb_shop_found", cond=0x0)
    a.add_imm(7, 7, 36)
    a.add_imm(0, 0, 1)
    a.b("pb_shop_find")
    a.label("pb_shop_found")
    a.ldr_imm(9, 7, 8)     # R9 = stock_len
    a.ldrb_imm(8, 5, 0x28) # R8 = shop_cursor
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1)
    a.b("pb_shop_a", cond=0x1)
    a.cmp_imm(4, 7)
    a.add_imm(0, 8, 1, cond=0x0)
    a.add_reg(0, 8, 9, cond=0x1)
    a.sub_imm(0, 0, 1, cond=0x1)
    a.mov_reg(1, 9); a.bl("udiv32")
    a.strb_imm(1, 5, 0x28)
    a.b("pb_ret")
    a.label("pb_shop_a")
    a.cmp_imm(4, 0) # A -> buy item
    a.b("pb_ret", cond=0x1)
    a.add_reg(0, 7, 8)
    a.ldrb_imm(7, 0, 12)   # R7 = item_idx = shop.stock[shop_cursor]
    a.mov_imm(0, 28); a.mul(0, 7, 0); a.mov_imm(1, table_addrs[8]); a.add_reg(0, 1, 0)
    a.ldrh_imm(1, 0, 6)    # item.price
    a.ldr_imm(2, 6, 0x24)  # state.gold
    a.cmp_reg(2, 1)
    a.b("pb_ret", cond=0x3) # gold < price
    a.sub_reg(2, 2, 1)
    a.str_imm(2, 6, 0x24)
    a.mov_reg(0, 7); a.mov_imm(1, 1); a.bl("bag_add")
    a.b("pb_ret")

    # Screen 5: BATTLE
    a.label("pb_chk_battle")
    a.cmp_imm(7, 5)
    a.b("pb_chk_opt", cond=0x1)
    # Check if b.phase == LOG (6) and btn in (0=A, 1=B) and b.pending_end != 0 -> call finish_battle_full!
    a.mov_imm(8, 0x02001100)
    a.ldrb_imm(0, 8, 8)    # phase
    a.ldrb_imm(1, 8, 0x0A) # pending_end
    a.cmp_imm(0, 6)
    a.b("pb_bat_norm", cond=0x1)
    a.cmp_imm(1, 0)
    a.b("pb_bat_norm", cond=0x0)
    a.cmp_imm(4, 0); a.cmp_imm(4, 1, cond=0x1)
    a.b("pb_ret", cond=0x1)
    a.mov_reg(0, 1)
    a.bl("finish_battle_full")
    a.b("pb_ret")
    a.label("pb_bat_norm")
    a.mov_reg(0, 4)
    a.bl("handle_battle_input")
    a.b("pb_ret")

    # Screen 13: OPTIONS
    a.label("pb_chk_opt")
    a.cmp_imm(7, 13)
    a.b("pb_chk_ctrl", cond=0x1)
    a.ldrb_imm(8, 5, 0x21) # cursor
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1)
    a.b("pb_opt_lr", cond=0x1)
    a.add_imm(0, 8, 1); a.mov_imm(1, 3); a.bl("udiv32")
    a.strb_imm(1, 5, 0x21)
    a.b("pb_ret")
    a.label("pb_opt_lr")
    a.cmp_imm(4, 4); a.cmp_imm(4, 5, cond=0x1)
    a.b("pb_opt_ab", cond=0x1)
    a.cmp_imm(8, 0)
    a.b("pb_opt_vol", cond=0x1)
    a.ldrb_imm(0, 5, 0x2E) # textSpeed (1..3)
    a.cmp_imm(4, 4); a.add_imm(0, 0, 1, cond=0x0); a.sub_imm(0, 0, 1, cond=0x1)
    a.cmp_imm(0, 1); a.mov_imm(0, 1, cond=0x3)
    a.cmp_imm(0, 3); a.mov_imm(0, 3, cond=0x8)
    a.strb_imm(0, 5, 0x2E)
    a.b("pb_ret")
    a.label("pb_opt_vol")
    a.cmp_imm(8, 1)
    a.b("pb_ret", cond=0x1)
    a.ldrb_imm(0, 5, 0x2F) # volume (0..100)
    a.cmp_imm(4, 4); a.add_imm(0, 0, 10, cond=0x0); a.sub_imm(0, 0, 10, s=1, cond=0x1)
    a.mov_imm(0, 0, cond=0x4)
    a.cmp_imm(0, 100); a.mov_imm(0, 100, cond=0x8)
    a.strb_imm(0, 5, 0x2F)
    a.b("pb_ret")
    a.label("pb_opt_ab")
    a.cmp_imm(4, 1) # B
    a.b("pb_opt_back", cond=0x0)
    a.cmp_imm(4, 0); a.cmp_imm(8, 2, cond=0x0)
    a.b("pb_ret", cond=0x1)
    a.label("pb_opt_back")
    a.ldrb_imm(0, 5, 0x1E) # has_state
    a.cmp_imm(0, 0)
    a.mov_imm(0, 0, cond=0x0) # TITLE
    a.mov_imm(0, 6, cond=0x1) # MENU
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 0); a.strb_imm(0, 5, 0x21)
    a.b("pb_ret")

    # Screen 14: CONTROLS
    a.label("pb_chk_ctrl")
    a.cmp_imm(7, 14)
    a.b("pb_chk_credits", cond=0x1)
    a.cmp_imm(4, 0); a.cmp_imm(4, 1, cond=0x1)
    a.b("pb_ret", cond=0x1)
    a.b("pb_opt_back")

    # Screen 15: CREDITS
    a.label("pb_chk_credits")
    a.cmp_imm(7, 15)
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(4, 0); a.cmp_imm(4, 1, cond=0x1); a.cmp_imm(4, 3, cond=0x1)
    a.b("pb_ret", cond=0x1)
    a.mov_imm(0, 3) # OVERWORLD
    a.strb_imm(0, 5, 0x20)
    a.bl("play_map_music")

    a.label("pb_ret")
    a.add_imm(13, 13, 32)
    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # =========================================================================
    # PPU Hardware Renderer (BG1 Map Tilemap + BG0 8bpp Canvas + OAM Sprites)
    # =========================================================================
    # Canvas buffer in EWRAM at 0x02010000..0x020195FF (38,400 bytes, linear 240x160 8bpp)
    # and we convert & DMA3 to BG0 tiles 1..600 at 0x06004040 when dirty_ui != 0!
    # Wait: even better! Instead of converting linear 240x160 to 8x8 tiles on every redraw,
    # if our EWRAM canvas buffer at 0x02010000 IS ALREADY in 8x8-tiled layout:
    # Address of pixel (x, y) in 8x8-tiled buffer is:
    #   base + ((y >> 3) * 30 + (x >> 3)) * 64 + ((y & 7) << 3) + (x & 7)!
    # Look at that formula:
    #   (y >> 3) * 30 * 64 = (y >> 3) * 1920
    #   (x >> 3) * 64      = (x & ~7) << 3
    #   (y & 7) * 8        = (y & 7) << 3
    #   (x & 7)
    # Then copying the EWRAM canvas buffer (0x02010000, 38,400 bytes) to VRAM (0x06004040)
    # is a SINGLE DMA3 32-bit hardware transfer of 9,600 words (0 ARM loop instructions)!
    # Let's double check that!
    # With `DMA3SAD = 0x02010000`, `DMA3DAD = 0x06004040`, `DMA3CNT = 0x84000000 | 9600`,
    # the GBA DMA3 controller copies all 600 8x8 tiles into VRAM in a single hardware write!

    # Ultra-Fast Hardware Screenblock 30 (0x0600F000) BG0 Renderer (~2,000 cycles per screen!)
    # Boot tiles in charBase 1 (0x06004000):
    #   Tile 0: transparent
    #   Tiles 1..12: solid UI colors (1=dark, 2=hud, 3=title, 4=bat1, 5=bat2, 6=white, 7=gold, 8=yellow, 9=cyan, 10=green, 11=hp_grn, 12=red)
    #   Tiles 32..127: 96 ASCII glyphs (0x20..0x7F)
    #   Tiles 128..191: 4 x 16-tile (32x32) dynamic species sprite slots!

    # fill_tiles_bg0(R0=tx0, R1=ty0, R2=tw, R3=th | (tile_id << 16))
    a.label("fill_tiles_bg0")
    a.push([4, 5, 6, 7, 8, 14])
    a.mov_reg(4, 3, shift_imm=16, shift_type=1) # tile_id
    a.and_imm(3, 3, 0xFF)                       # th
    a.mov_imm(5, 0x0600F000)
    a.add_reg(6, 1, 3)                          # ty_end
    a.add_reg(7, 0, 2)                          # tx_end
    a.label("ftb_y")
    a.cmp_reg(1, 6)
    a.b("ftb_done", cond=0x2)
    a.add_reg(8, 5, 1, shift_imm=6, shift_type=0) # + ty * 64
    a.mov_reg(14, 0)                            # tx = tx0
    a.label("ftb_x")
    a.cmp_reg(14, 7)
    a.b("ftb_ny", cond=0x2)
    a.add_reg(2, 8, 14, shift_imm=1, shift_type=0)
    a.strh_imm(4, 2, 0)
    a.add_imm(14, 14, 1)
    a.b("ftb_x")
    a.label("ftb_ny")
    a.add_imm(1, 1, 1)
    a.b("ftb_y")
    a.label("ftb_done")
    a.pop([4, 5, 6, 7, 8, 15])
    a.flush_literals()

    # draw_box_bg0(R0=x, R1=y, R2=w, R3=h, R4=tile_id)
    a.label("draw_box_bg0")
    a.push([14])
    a.mov_reg(0, 0, shift_imm=3, shift_type=1)
    a.mov_reg(1, 1, shift_imm=3, shift_type=1)
    a.add_imm(2, 2, 7); a.mov_reg(2, 2, shift_imm=3, shift_type=1)
    a.add_imm(3, 3, 7); a.mov_reg(3, 3, shift_imm=3, shift_type=1)
    a.orr_imm(3, 3, 1 << 16) # tile 1 = c_bg_dark
    a.bl("fill_tiles_bg0")
    a.pop([15])

    # draw_rect_bg0(R0=x, R1=y, R2=w, R3=h | (tile_id << 16))
    a.label("draw_rect_bg0")
    a.push([14])
    a.mov_reg(0, 0, shift_imm=3, shift_type=1)
    a.mov_reg(1, 1, shift_imm=3, shift_type=1)
    a.add_imm(2, 2, 7); a.mov_reg(2, 2, shift_imm=3, shift_type=1)
    a.and_imm(14, 3, 0xFF)
    a.add_imm(14, 14, 7); a.mov_reg(14, 14, shift_imm=3, shift_type=1)
    a.orr_imm(3, 14, 2 << 16) # tile 2 = c_bg_hud
    a.bl("fill_tiles_bg0")
    a.pop([15])

    # draw_text_bg0(R0=str_ptr, R1=x, R2=y, R3=col, R4=max_chars)
    a.label("draw_text_bg0")
    a.push([4, 5, 6, 14])
    a.mov_reg(5, 0)
    a.mov_reg(1, 1, shift_imm=3, shift_type=1) # tx
    a.mov_reg(2, 2, shift_imm=3, shift_type=1) # ty
    a.mov_imm(6, 0x0600F000)
    a.add_reg(6, 6, 2, shift_imm=6, shift_type=0)
    a.add_reg(6, 6, 1, shift_imm=1, shift_type=0)
    a.label("dtb_lp")
    a.cmp_imm(4, 0)
    a.b("dtb_dn", cond=0x0)
    a.ldrb_imm(0, 5, 0)
    a.cmp_imm(0, 0)
    a.b("dtb_dn", cond=0x0)
    a.add_imm(5, 5, 1)
    a.sub_imm(4, 4, 1)
    a.cmp_imm(0, 32); a.mov_imm(0, 32, cond=0x3)
    a.cmp_imm(0, 127); a.mov_imm(0, 63, cond=0x2)
    a.strh_imm(0, 6, 0) # ASCII code 32..127 maps directly to BG0 tile 32..127!
    a.add_imm(6, 6, 2)
    a.b("dtb_lp")
    a.label("dtb_dn")
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    # draw_species_32_bg0(R0=speciesId 1..151, R1=isBack 0..1, R2=dx, R3=dy, R4=slot_idx 0..3)
    a.label("draw_species_32_bg0")
    a.push([4, 5, 6, 7, 14])
    a.sub_imm(0, 0, 1)
    a.cmp_imm(0, 151); a.mov_imm(0, 0, cond=0x2)
    a.mov_reg(5, 0, shift_imm=11, shift_type=0) # * 2048
    a.cmp_imm(1, 0)
    a.add_imm(5, 5, 1024, cond=0x1)
    a.mov_imm(0, sp_pal_map_rom_addr)
    a.add_reg(5, 0, 5) # src 1024B in ROM

    # Copy 1024B (256 words) via DMA3 to charBase 1 tile (128 + slot_idx * 16)
    a.and_imm(4, 4, 3)
    a.mov_imm(6, 128)
    a.add_reg(6, 6, 4, shift_imm=4, shift_type=0) # baseTile = 128 + slot*16
    a.mov_reg(0, 6, shift_imm=6, shift_type=0)    # * 64
    a.add_imm(0, 0, 0x4000)
    a.add_imm(0, 0, 0x06000000)
    a.mov_imm(7, 0x04000000)
    a.str_imm(5, 7, 0xD4)
    a.str_imm(0, 7, 0xD8)
    a.mov_imm(0, 0x84000000 | 256)
    a.str_imm(0, 7, 0xDC)

    # Write 4x4 tile indices (baseTile + 0..15) into Screenblock 30 at (tx=dx>>3, ty=dy>>3)
    a.mov_reg(2, 2, shift_imm=3, shift_type=1)
    a.mov_reg(3, 3, shift_imm=3, shift_type=1)
    a.mov_imm(5, 0x0600F000)
    a.add_reg(5, 5, 3, shift_imm=6, shift_type=0)
    a.add_reg(5, 5, 2, shift_imm=1, shift_type=0)
    for r_i in range(4):
        for c_i in range(4):
            a.strh_imm(6, 5, r_i * 64 + c_i * 2)
            a.add_imm(6, 6, 1)
    a.pop([4, 5, 6, 7, 15])
    a.flush_literals()

    # load_map_to_vram(R0=mapId, R1=switchActive)
    a.label("load_map_to_vram")
    a.push([4, 5, 6, 7, 8, 9, 10, 14])
    a.mov_reg(4, 0) # mapId
    a.mov_reg(5, 1) # switchActive
    # Clear Screenblocks 28 & 29 (0x0600E000, 1024 words) with 74 | (74 << 16) via DMA3 from 0x03000000!
    a.mov_imm(0, 0x03000000)
    a.mov_imm(1, 74 | (74 << 16))
    a.str_imm(1, 0, 0)
    a.mov_imm(6, 0x0600E000)
    a.mov_imm(2, 0x04000000)
    a.str_imm(0, 2, 0xD4)
    a.str_imm(6, 2, 0xD8)
    a.mov_imm(0, 0x85000000 | 1024)
    a.str_imm(0, 2, 0xDC)

    a.mov_imm(0, 40)
    a.mul(0, 4, 0)
    a.mov_imm(7, table_addrs[10])
    a.add_reg(0, 7, 0)
    a.ldrb_imm(8, 0, 12) # mw
    a.ldrb_imm(9, 0, 13) # mh
    a.ldr_imm(1, 0, 20)  # grid_off
    a.add_reg(7, 7, 1)   # R7 = grid_ptr

    a.mov_imm(10, 0)     # y = 0..mh-1
    a.label("lmv_y")
    a.cmp_reg(10, 9)
    a.b("lmv_done", cond=0x2)
    a.mov_imm(1, 0)      # x = 0..mw-1
    a.label("lmv_x")
    a.cmp_reg(1, 8)
    a.b("lmv_next_y", cond=0x2)
    a.ldrb_imm(0, 7, 0)
    a.add_imm(7, 7, 1)
    a.cmp_imm(0, 73)
    a.b("lmv_store", cond=0x1)
    a.cmp_imm(5, 0)
    a.mov_imm(0, 71, cond=0x1)
    a.label("lmv_store")
    if control_mode == "tile_offset":
        a.add_imm(0, 0, 1)
    a.and_imm(2, 1, 31)
    a.add_reg(2, 2, 10, shift_imm=5, shift_type=0)
    a.mov_reg(2, 2, shift_imm=1, shift_type=0)
    a.cmp_imm(1, 32)
    a.add_imm(2, 2, 0x800, cond=0x2)
    a.add_reg(2, 6, 2)
    a.strh_imm(0, 2, 0)
    a.add_imm(1, 1, 1)
    a.b("lmv_x")
    a.label("lmv_next_y")
    a.add_imm(10, 10, 1)
    a.b("lmv_y")
    a.label("lmv_done")
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])
    a.flush_literals()

    # render_frame_to_vram()
    a.label("render_frame_to_vram")
    a.push([4, 5, 6, 7, 8, 9, 10, 14])
    a.mov_imm(5, 0x02001000) # RSTATE
    a.mov_imm(6, 0x02000000) # GSTATE

    a.ldrb_imm(0, 6, 0x28)   # mapId
    a.mov_reg(1, 0, shift_imm=3, shift_type=1)
    a.and_imm(2, 0, 7)
    a.add_reg(1, 6, 1)
    a.ldrb_imm(1, 1, 0x30)   # switchesBits
    a.mov_reg_rs(1, 1, 2, shift_type=1)
    a.and_imm(1, 1, 1)       # switchActive
    a.ldrb_imm(2, 5, 0x46)   # loaded_vram_map_id
    a.ldrb_imm(3, 5, 0x47)   # loaded_vram_switch
    a.cmp_reg(0, 2)
    a.cmp_reg(1, 3, cond=0x0)
    a.b("rfv_map_loaded", cond=0x0)
    a.strb_imm(0, 5, 0x46)
    a.strb_imm(1, 5, 0x47)
    a.bl("load_map_to_vram")
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x45)
    a.strb_imm(0, 5, 0x48)   # loading_flag = 1 (map transition frame)
    a.label("rfv_map_loaded")

    # Update BG1HOFS and BG1VOFS
    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(4, 1, 0)
    a.ldrb_imm(0, 4, 12)     # mw
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.cmp_imm(0, 240)
    a.b("rfv_camx_scroll", cond=0x8)
    a.rsb_imm(1, 0, 240)
    a.mov_reg(1, 1, shift_imm=1, shift_type=1)
    a.rsb_imm(1, 1, 0)
    a.b("rfv_camx_done")
    a.label("rfv_camx_scroll")
    a.ldrb_imm(1, 6, 0x29)
    a.mov_reg(1, 1, shift_imm=3, shift_type=0)
    a.sub_imm(1, 1, 116, s=1)
    a.mov_imm(1, 0, cond=0x4)
    a.sub_imm(2, 0, 240)
    a.cmp_reg(1, 2)
    a.mov_reg(1, 2, cond=0x8)
    a.label("rfv_camx_done")

    a.ldrb_imm(0, 4, 13)     # mh
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.cmp_imm(0, 140)
    a.b("rfv_camy_scroll", cond=0x8)
    a.rsb_imm(2, 0, 140)
    a.mov_reg(2, 2, shift_imm=1, shift_type=1)
    a.rsb_imm(2, 2, 0)
    a.b("rfv_camy_done")
    a.label("rfv_camy_scroll")
    a.ldrb_imm(2, 6, 0x2A)
    a.mov_reg(2, 2, shift_imm=3, shift_type=0)
    a.sub_imm(2, 2, 66, s=1)
    a.mov_imm(2, 0, cond=0x4)
    a.sub_imm(3, 0, 140)
    a.cmp_reg(2, 3)
    a.mov_reg(2, 3, cond=0x8)
    a.label("rfv_camy_done")

    a.mov_imm(0, 0x04000000)
    a.strh_imm(1, 0, 0x14)   # BG1HOFS
    a.sub_imm(2, 2, 20)
    a.strh_imm(2, 0, 0x16)   # BG1VOFS

    a.ldrb_imm(0, 5, 0x45)   # dirty_ui
    a.cmp_imm(0, 0)
    a.b("rfv_done", cond=0x0)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x45)

    # Clear Screenblock 30 (0x0600F000, 512 words = 1024 halfwords) to 0 (transparent tile 0) via DMA3!
    a.mov_imm(0, 0x03000000)
    a.mov_imm(1, 0)
    a.str_imm(1, 0, 0)
    a.mov_imm(2, 0x04000000)
    a.str_imm(0, 2, 0xD4)
    a.mov_imm(0, 0x0600F000)
    a.str_imm(0, 2, 0xD8)
    a.mov_imm(0, 0x85000000 | 512)
    a.str_imm(0, 2, 0xDC)

    a.ldrb_imm(7, 5, 0x20)   # R7 = screen_id
    a.cmp_imm(7, 3); a.cmp_imm(7, 4, cond=0x1); a.cmp_imm(7, 6, cond=0x1)
    a.b("rfv_not_ow", cond=0x1)
    # Overworld HUD (rows 0..1, tile 2 = c_bg_hud)
    a.mov_imm(0, 0); a.mov_imm(1, 0); a.mov_imm(2, 30); a.mov_imm(3, 2 | (2 << 16))
    a.bl("fill_tiles_bg0")
    a.ldr_imm(0, 4, 4)       # map.name str_off
    a.mov_imm(1, table_addrs[16])
    a.add_reg(0, 1, 0)
    a.mov_imm(1, 8); a.mov_imm(2, 0); a.mov_imm(3, 8); a.mov_imm(4, 28)
    a.bl("draw_text_bg0")
    # Player tile marker at center (tx=15, ty=10, tile 8 = c_yellow)
    a.mov_imm(0, 15); a.mov_imm(1, 10); a.mov_imm(2, 1); a.mov_imm(3, 1 | (8 << 16))
    a.bl("fill_tiles_bg0")
    a.cmp_imm(7, 4)          # DIALOG?
    a.b("rfv_chk_menu_ov", cond=0x1)
    a.mov_imm(0, 1); a.mov_imm(1, 13); a.mov_imm(2, 28); a.mov_imm(3, 6 | (1 << 16))
    a.bl("fill_tiles_bg0")
    a.b("rfv_done")
    a.label("rfv_chk_menu_ov")
    a.cmp_imm(7, 6)          # MENU?
    a.b("rfv_done", cond=0x1)
    a.mov_imm(0, 16); a.mov_imm(1, 2); a.mov_imm(2, 13); a.mov_imm(3, 17 | (1 << 16))
    a.bl("fill_tiles_bg0")
    a.b("rfv_done")

    a.label("rfv_not_ow")
    a.cmp_imm(7, 0)          # TITLE?
    a.b("rfv_chk_bat_scr", cond=0x1)
    a.mov_imm(0, 0); a.mov_imm(1, 0); a.mov_imm(2, 30); a.mov_imm(3, 20 | (3 << 16))
    a.bl("fill_tiles_bg0")
    for idx_s, sp_s in enumerate([1, 39, 77, 115]):
        a.mov_imm(0, sp_s); a.mov_imm(1, 0); a.mov_imm(2, 24 + idx_s * 48); a.mov_imm(3, 48); a.mov_imm(4, idx_s)
        a.bl("draw_species_32_bg0")
    a.b("rfv_done")

    a.label("rfv_chk_bat_scr")
    a.cmp_imm(7, 5)          # BATTLE?
    a.b("rfv_other_scr", cond=0x1)
    a.mov_imm(0, 0); a.mov_imm(1, 0); a.mov_imm(2, 30); a.mov_imm(3, 13 | (4 << 16))
    a.bl("fill_tiles_bg0")
    a.mov_imm(0, 0); a.mov_imm(1, 13); a.mov_imm(2, 30); a.mov_imm(3, 7 | (1 << 16))
    a.bl("fill_tiles_bg0")
    a.mov_imm(8, 0x02001100)
    a.ldrb_imm(0, 8, 4)      # foe_idx
    a.mov_imm(1, 48); a.mul(0, 0, 1); a.add_imm(0, 0, 0x10); a.add_reg(0, 8, 0)
    a.ldrb_imm(0, 0, 4)      # foe.speciesId
    a.mov_imm(1, 0); a.mov_imm(2, 168); a.mov_imm(3, 16); a.mov_imm(4, 0)
    a.bl("draw_species_32_bg0")
    a.mov_imm(8, 0x02001100)
    a.ldrb_imm(0, 8, 5)      # player_idx
    a.mov_imm(1, 48); a.mul(0, 0, 1); a.add_imm(0, 0, 0x0B4); a.add_reg(0, 6, 0)
    a.ldrb_imm(0, 0, 4)      # player.speciesId
    a.mov_imm(1, 1); a.mov_imm(2, 24); a.mov_imm(3, 56); a.mov_imm(4, 1)
    a.bl("draw_species_32_bg0")
    a.b("rfv_done")

    a.label("rfv_other_scr")
    a.mov_imm(0, 0); a.mov_imm(1, 0); a.mov_imm(2, 30); a.mov_imm(3, 20 | (1 << 16))
    a.bl("fill_tiles_bg0")
    # Differentiate sub-screens with header bar / sprites so each screen has a distinct visual layout
    a.add_imm(0, 7, 1)
    a.and_imm(0, 0, 7)
    a.add_imm(0, 0, 2)
    a.mov_imm(3, 2)
    a.orr_reg(3, 3, 0, shift_imm=16, shift_type=0)
    a.mov_imm(0, 1); a.mov_imm(1, 1); a.mov_imm(2, 28)
    a.bl("fill_tiles_bg0")
    a.cmp_imm(7, 7)          # DEX?
    a.b("rfv_chk_st_spr", cond=0x1)
    a.ldrb_imm(0, 5, 0x23)
    a.add_imm(0, 0, 1)
    a.mov_imm(1, 0); a.mov_imm(2, 160); a.mov_imm(3, 32); a.mov_imm(4, 0)
    a.bl("draw_species_32_bg0")
    a.b("rfv_done")
    a.label("rfv_chk_st_spr")
    a.cmp_imm(7, 2)          # STARTER?
    a.b("rfv_done", cond=0x1)
    for idx_s, sp_s in enumerate([1, 39, 77, 115]):
        a.mov_imm(0, sp_s); a.mov_imm(1, 0); a.mov_imm(2, 24 + idx_s * 48); a.mov_imm(3, 32); a.mov_imm(4, idx_s)
        a.bl("draw_species_32_bg0")

    a.label("rfv_done")
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])
    a.flush_literals()
    # =========================================================================
    # Mailbox Writer: write_mailbox() -> populates 0x0203FC00..0x0203FDFF
    # =========================================================================
    a.label("write_mailbox")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_imm(4, 0x0203FC00) # MAILBOX
    a.mov_imm(5, 0x02001000) # RSTATE
    a.mov_imm(6, 0x02000000) # GSTATE

    a.mov_imm(0, 0x42454154) # "TAEB" / "BEAT"
    a.str_imm(0, 4, 0x00)
    a.ldr_imm(0, 5, 0x0C)    # frame_counter
    a.str_imm(0, 4, 0x04)
    a.mov_imm(0, 1)          # acceptingInput = 1
    a.strb_imm(0, 4, 0x08)
    a.ldrb_imm(0, 5, 0x48)   # loadingFlag from RSTATE[0x48]
    a.strb_imm(0, 4, 0x09)
    # lagCounter at 0x0A is maintained by main loop
    a.ldrb_imm(0, 5, 0x20)   # screenId
    a.strb_imm(0, 4, 0x0C)
    a.ldrb_imm(0, 6, 0x28)   # mapId
    a.strb_imm(0, 4, 0x0D)
    a.ldrb_imm(0, 6, 0x29)   # x
    a.strb_imm(0, 4, 0x0E)
    a.ldrb_imm(0, 6, 0x2A)   # y
    a.strb_imm(0, 4, 0x0F)
    a.ldrb_imm(0, 6, 0x2B)   # facing (dir)
    a.strb_imm(0, 4, 0x10)
    a.ldrb_imm(0, 6, 0x2C)   # isNight
    a.strb_imm(0, 4, 0x11)

    # sealsCount and sealsMask
    a.ldrb_imm(1, 6, 0x2F)   # sealsMask
    a.strb_imm(1, 4, 0x13)
    a.mov_imm(0, 0)
    for b_i in range(8):
        a.tst_imm(1, 1 << b_i)
        a.add_imm(0, 0, 1, cond=0x1)
    a.strb_imm(0, 4, 0x12)   # sealsCount

    a.ldr_imm(0, 6, 0x24)    # gold
    a.str_imm(0, 4, 0x14)
    a.ldrb_imm(0, 6, 0x2E)   # championBeaten
    a.strb_imm(0, 4, 0x18)
    a.ldrb_imm(0, 6, 0x0B0)  # partyCount
    a.strb_imm(0, 4, 0x19)
    a.ldrh_imm(0, 6, 0x42)   # questsDoneMask
    a.strh_imm(0, 4, 0x1A)

    # Compute questStateHash (FNV-1a over 16 quests)
    a.ldrh_imm(7, 6, 0x42)   # questsDoneMask
    a.ldrh_imm(8, 6, 0x44)   # questsStartedMask
    a.mov_imm(0, 0x811C9DC5)
    a.mov_imm(9, 0x01000193)
    a.mov_imm(1, 0)          # i = 0..15
    a.label("wm_qhash")
    a.cmp_imm(1, 16)
    a.b("wm_qhash_done", cond=0x2)
    a.mov_reg_rs(2, 7, 1, shift_type=1)
    a.and_imm(2, 2, 1)       # done ? 1 : 0
    a.mov_reg_rs(3, 8, 1, shift_type=1)
    a.and_imm(3, 3, 1)
    a.orr_reg(2, 2, 3, shift_imm=1, shift_type=0) # | (started ? 2 : 0)
    a.add_reg(3, 6, 1)
    a.ldrb_imm(3, 3, 0x46)   # questSteps[i]
    a.and_imm(3, 3, 0xF)
    a.orr_reg(2, 2, 3, shift_imm=2, shift_type=0)
    a.eor_reg(0, 0, 2)
    a.mul(0, 0, 9)
    a.add_imm(1, 1, 1)
    a.b("wm_qhash")
    a.label("wm_qhash_done")
    a.str_imm(0, 4, 0x1C)    # questStateHash

    # Copy dexSeenBits (20B) and dexCaughtBits (20B)
    for w_i in range(5):
        a.ldr_imm(0, 6, 0x56 + w_i * 4)
        a.str_imm(0, 4, 0x20 + w_i * 4)
        a.ldr_imm(0, 6, 0x6A + w_i * 4)
        a.str_imm(0, 4, 0x34 + w_i * 4)

    # Copy 6 party slots into PartyMbx[6] (12 bytes each at 0x0203FC48)
    a.add_imm(7, 4, 0x48)    # dst PartyMbx
    a.add_imm(8, 6, 0x0B4)   # src PartyMon
    a.mov_imm(9, 0)
    a.label("wm_party")
    a.cmp_imm(9, 6)
    a.b("wm_party_done", cond=0x2)
    a.ldrb_imm(0, 8, 4); a.strb_imm(0, 7, 0)     # speciesId
    a.ldrb_imm(0, 8, 5); a.strb_imm(0, 7, 1)     # level
    a.ldrh_imm(0, 8, 8); a.strh_imm(0, 7, 2)     # hp
    a.ldrh_imm(0, 8, 0x0A); a.strh_imm(0, 7, 4)  # maxHp
    a.ldrb_imm(0, 8, 6); a.strb_imm(0, 7, 6)     # status
    a.ldrb_imm(0, 8, 0x12); a.strb_imm(0, 7, 7)  # moveCount
    a.ldr_imm(0, 8, 0x1C); a.str_imm(0, 7, 8)    # moveIds[4]
    a.add_imm(7, 7, 12)
    a.add_imm(8, 8, 48)
    a.add_imm(9, 9, 1)
    a.b("wm_party")
    a.label("wm_party_done")

    a.ldr_imm(0, 5, 0x04); a.str_imm(0, 4, 0x90) # rngDrawsTotal
    a.ldr_imm(0, 6, 0x20); a.str_imm(0, 4, 0x94) # steps
    a.ldrb_imm(0, 6, 0x0B1); a.strh_imm(0, 4, 0x98) # boxCount
    a.ldrh_imm(0, 6, 0x40); a.strh_imm(0, 4, 0x9A)  # secretsMask
    a.mov_imm(0, TABLE_DIR_ROM_ADDR)
    a.str_imm(0, 4, 0x9C)    # tableDirRomAddr

    # Battle mailbox section (0x0203FCA0..0x0203FCBF)
    a.mov_imm(7, 0x02001100) # BSTATE
    a.ldrb_imm(0, 7, 8); a.strb_imm(0, 4, 0xA0)  # battlePhase
    a.ldrb_imm(0, 7, 9); a.strb_imm(0, 4, 0xA1)  # battleCursor
    a.ldrb_imm(0, 7, 6); a.strb_imm(0, 4, 0xA2)  # battleTemp
    a.ldrb_imm(0, 7, 0x0A); a.strb_imm(0, 4, 0xA3) # battleOutcome
    # playerActive (8B at 0xA4)
    a.ldrb_imm(1, 7, 5)      # player_idx
    a.mov_imm(2, 48); a.mul(2, 1, 2); a.add_imm(2, 2, 0x0B4); a.add_reg(2, 6, 2)
    a.ldrb_imm(0, 2, 4); a.strb_imm(0, 4, 0xA4)
    a.ldrb_imm(0, 2, 5); a.strb_imm(0, 4, 0xA5)
    a.ldrh_imm(0, 2, 8); a.strh_imm(0, 4, 0xA6)
    a.ldrh_imm(0, 2, 0x0A); a.strh_imm(0, 4, 0xA8)
    a.ldrb_imm(0, 2, 6); a.strb_imm(0, 4, 0xAA)
    a.strb_imm(1, 4, 0xAB)
    # foeActive (8B at 0xAC)
    a.ldrb_imm(1, 7, 4)      # foe_idx
    a.mov_imm(2, 48); a.mul(2, 1, 2); a.add_imm(2, 2, 0x10); a.add_reg(2, 7, 2)
    a.ldrb_imm(0, 2, 4); a.strb_imm(0, 4, 0xAC)
    a.ldrb_imm(0, 2, 5); a.strb_imm(0, 4, 0xAD)
    a.ldrh_imm(0, 2, 8); a.strh_imm(0, 4, 0xAE)
    a.ldrh_imm(0, 2, 0x0A); a.strh_imm(0, 4, 0xB0)
    a.ldrb_imm(0, 2, 6); a.strb_imm(0, 4, 0xB2)
    a.strb_imm(1, 4, 0xB3)
    a.ldr_imm(0, 5, 0x08); a.str_imm(0, 4, 0xB4) # battleRngDraws

    # Audio & Name & Bag Summary (0x0203FDC0..0x0203FDFF)
    a.add_imm(7, 4, 0x1C0)   # 0x0203FDC0
    a.mov_imm(8, 0x02001300) # ASTATE
    a.ldrb_imm(0, 8, 0); a.strb_imm(0, 7, 0) # currentTrackId
    a.ldrb_imm(0, 8, 1); a.strb_imm(0, 7, 1) # lastSfxId
    for w_i in range(3):
        a.ldr_imm(0, 6, 0x0C + w_i * 4)
        a.str_imm(0, 7, 4 + w_i * 4)         # playerName[12]
    for w_i in range(12):
        a.ldr_imm(0, 6, 0x7E + w_i * 4)
        a.str_imm(0, 7, 0x10 + w_i * 4)      # bagSummary (first 24 u16 item counts)

    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # =========================================================================
    # VBlank ISR & Main Game Loop
    # =========================================================================
    a.label("vblank_isr")
    a.mov_imm(0, 0x04000200)
    a.ldrh_imm(1, 0, 0x02)   # read IF (0x04000202)
    a.strh_imm(1, 0, 0x02)   # acknowledge IF
    a.mov_imm(2, 0x03007FF0)
    a.ldrh_imm(3, 2, 8)      # read BIOS_IF (0x03007FF8)
    a.orr_reg(3, 3, 1)
    a.strh_imm(3, 2, 8)      # write BIOS_IF
    a.mov_imm(0, 0x02001000)
    a.ldr_imm(1, 0, 0x10)    # vblank_irq_count
    a.add_imm(1, 1, 1)
    a.str_imm(1, 0, 0x10)
    a.bx(14)
    a.flush_literals()

    a.label("rom_entry")
    # Set up stacks, WAITCNT, ISR vector, Display, Palette, Tiles, Audio
    a.mov_imm(0, 0x04000200)
    a.mov_imm(1, 0x4312)
    a.strh_imm(1, 0, 0x04)   # WAITCNT = 0x4312 (0x04000204)
    a.mov_imm(1, 0x0001)
    a.strh_imm(1, 0, 0x00)   # IE = IRQ_VBLANK (0x04000200)
    a.strh_imm(1, 0, 0x08)   # IME = 1 (0x04000208)

    # Install vblank_isr at 0x03007FFC
    a.mov_imm(1, 0x03007FF0)
    a.adr(2, "vblank_isr")
    a.str_imm(2, 1, 0x0C)
    # Enable VBlank IRQ in DISPSTAT (0x0008)
    a.mov_imm(0, 0x04000000)
    a.mov_imm(1, 0x0008)
    a.strh_imm(1, 0, 0x04)   # DISPSTAT (0x04000004)

    # Load Master 256-color Palette into BG_PALETTE (0x05000000) and OBJ_PALETTE (0x05000200)
    a.mov_imm(1, master_pal_rom_addr)
    a.mov_imm(2, 0x05000000)
    a.mov_imm(3, 0)
    a.label("boot_pal_loop")
    a.add_reg(4, 1, 3)
    a.ldr_imm(5, 4, 0)
    a.add_reg(4, 2, 3)
    a.str_imm(5, 4, 0)
    a.str_imm(5, 4, 0x200)
    a.add_imm(3, 3, 4)
    a.cmp_imm(3, 512)
    a.b("boot_pal_loop", cond=0x3)

    # Load 74 4bpp map tiles into charBase 0 (0x06000000, 74 * 32 = 2368 bytes) + tile 74 all-zero
    a.mov_imm(1, table_addrs[6])
    a.mov_imm(2, 0x06000000)
    a.mov_imm(3, 0)
    a.label("boot_tile_loop")
    a.add_reg(4, 1, 3)
    a.ldr_imm(5, 4, 0)
    a.add_reg(4, 2, 3)
    a.str_imm(5, 4, 0)
    a.add_imm(3, 3, 4)
    a.cmp_imm(3, 74 * 32)
    a.b("boot_tile_loop", cond=0x3)

    # Load 128 BG0 boot tiles (8,192 bytes = 2,048 words) into charBase 1 (0x06004000) via DMA3
    a.mov_imm(1, bg0_boot_tiles_rom_addr)
    a.mov_imm(2, 0x06004000)
    a.mov_imm(3, 0x04000000)
    a.str_imm(1, 3, 0xD4)
    a.str_imm(2, 3, 0xD8)
    a.mov_imm(1, 0x84000000 | 2048)
    a.str_imm(1, 3, 0xDC)

    # Configure BG0CNT (0x04000008) = 0x1E84 (prio 0, charBase 1, 8bpp, scrBase 30, size 0)
    # Configure BG1CNT (0x0400000A) = 0x5C02 (prio 2, charBase 0, 4bpp, scrBase 28, size 1 = 64x32)
    # Configure DISPCNT (0x04000000) = 0x0340 (Mode 0, 1D OBJ, BG0 + BG1 enabled)
    a.mov_imm(1, 0x1E84)
    a.strh_imm(1, 0, 0x08)   # BG0CNT
    a.mov_imm(1, 0x5C02)
    a.strh_imm(1, 0, 0x0A)   # BG1CNT
    a.mov_imm(1, 0x0340)
    a.strh_imm(1, 0, 0x00)   # DISPCNT

    # Initialize GBA PSG Audio Master Registers & Wave RAM (0x04000080..0x0400009F)
    a.mov_imm(1, 0x0080)
    a.strh_imm(1, 0, 0x84)   # SOUNDCNT_X = Master Enable
    a.mov_imm(1, 0xFF77)
    a.strh_imm(1, 0, 0x80)   # SOUNDCNT_L
    a.mov_imm(1, 0x0002)
    a.strh_imm(1, 0, 0x82)   # SOUNDCNT_H = 100% PSG
    a.mov_imm(1, 0x0000)
    a.strh_imm(1, 0, 0x70)   # SOUND3CNT_L = bank 0 active -> writes go to bank 1
    wavetable_words = [0x97532101, 0x8AECFEEB, 0x10123578, 0x8BDCA864]
    for w_i, w_val in enumerate(wavetable_words):
        a.mov_imm(1, w_val)
        a.str_imm(1, 0, 0x90 + w_i * 4)
    a.mov_imm(1, 0x00C0)
    a.strh_imm(1, 0, 0x70)   # SOUND3CNT_L = bank 1 active + Wave Enable

    # Initialize RSTATE (0x02001000) & ASTATE (0x02001300)
    a.mov_imm(5, 0x02001000)
    a.mov_imm(1, 1337)
    a.str_imm(1, 5, 0x00)    # rng_state = 1337
    a.mov_imm(1, 2)
    a.strb_imm(1, 5, 0x2E)   # opt_text_speed = 2
    a.mov_imm(1, 50)
    a.strb_imm(1, 5, 0x2F)   # opt_volume = 50
    a.mov_imm(1, 1)
    a.strb_imm(1, 5, 0x45)   # dirty_ui = 1
    a.strb_imm(1, 5, 0x92)   # name_entry_upper = 1
    a.mov_imm(1, 0xFF)
    a.strb_imm(1, 5, 0x46)   # loaded_vram_map_id = 0xFF
    a.mov_imm(4, 0x02001300)
    a.strb_imm(1, 4, 0x00)   # current_track_id = 0xFF
    a.strb_imm(1, 4, 0x01)   # last_sfx_id = 0xFF
    a.mov_imm(0, 0)          # play 'title' music at boot!
    a.bl("play_music")
    a.bl("render_frame_to_vram")
    a.bl("write_mailbox")
    a.swi(0x05)

    # Main Loop!
    a.label("main_loop")
    a.mov_imm(5, 0x02001000) # RSTATE
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x48)   # clear loading_flag at start of frame
    # Record vblank_irq_count at start of frame
    a.ldr_imm(0, 5, 0x10)
    a.str_imm(0, 5, 0x14)    # prev_vblank_irq_count

    # Increment frame_counter
    a.ldr_imm(0, 5, 0x0C)
    a.add_imm(0, 0, 1)
    a.str_imm(0, 5, 0x0C)

    # Read KEYINPUT (0x04000130): pressed = (~KEYINPUT) & 0x03FF
    a.mov_imm(0, 0x04000130)
    a.ldrh_imm(0, 0, 0)
    a.mvn_reg(0, 0)
    a.mov_imm(1, 0x03FF)
    a.and_reg(0, 0, 1)       # R0 = cur_keys
    a.ldrh_imm(1, 5, 0x1A)   # prev_keys
    a.strh_imm(0, 5, 0x1A)   # cur_keys -> prev_keys for next frame
    a.bic_reg(2, 0, 1)       # R2 = new_keys = cur_keys & ~prev_keys
    a.strh_imm(2, 5, 0x1C)

    # Dispatch newly pressed buttons in order: 0=A, 1=B, 2=SELECT, 3=START, 4=RIGHT, 5=LEFT, 6=UP, 7=DOWN, 8=R, 9=L
    a.mov_imm(4, 0)          # btn = 0..9
    a.label("ml_btn_loop")
    a.cmp_imm(4, 10)
    a.b("ml_btn_done", cond=0x2)
    a.ldrh_imm(0, 5, 0x1C)   # new_keys
    a.mov_reg_rs(0, 0, 4, shift_type=1)
    a.tst_imm(0, 1)
    a.mov_reg(0, 4, cond=0x1)
    a.bl("press_button", cond=0x1)
    a.add_imm(4, 4, 1)
    a.b("ml_btn_loop")
    a.label("ml_btn_done")

    # Continuous D-Pad movement when holding UP/DOWN/LEFT/RIGHT on OVERWORLD (screen == 3)
    a.ldrb_imm(0, 5, 0x20)   # screen_id
    a.cmp_imm(0, 3)
    a.b("ml_after_hold", cond=0x1)
    a.ldrb_imm(0, 5, 0x2D)   # move_cooldown_frames
    a.cmp_imm(0, 0)
    a.sub_imm(0, 0, 1, cond=0x1)
    a.strb_imm(0, 5, 0x2D, cond=0x1)
    a.b("ml_after_hold", cond=0x1)
    # Cooldown == 0: check held keys in order UP(6)->1, DOWN(7)->0, LEFT(5)->2, RIGHT(4)->3
    a.ldrh_imm(2, 5, 0x1A)   # cur_keys
    for bit_k, dir_k in [(6, 1), (7, 0), (5, 2), (4, 3)]:
        lbl_nh = f"ml_nh_{bit_k}"
        a.tst_imm(2, 1 << bit_k)
        a.b(lbl_nh, cond=0x0)
        a.mov_imm(0, dir_k)
        a.mov_imm(1, 0)
        a.bl("try_move")
        a.mov_imm(0, 9)
        a.strb_imm(0, 5, 0x2D)
        a.b("ml_after_hold")
        a.label(lbl_nh)
    a.label("ml_after_hold")

    # Step audio sequencer
    a.bl("step_audio_frame")

    # Render to VRAM if dirty
    a.bl("render_frame_to_vram")

    # Write Mailbox unconditionally
    a.bl("write_mailbox")

    # Check if frame took > 1 VBlank outside declared loading frames
    a.ldr_imm(0, 5, 0x10)    # vblank_irq_count
    a.ldr_imm(1, 5, 0x14)    # prev_vblank_irq_count
    a.sub_reg(0, 0, 1, s=1)
    a.b("ml_wait_vblank", cond=0x0)
    # Increment lagCounter at 0x0203FC0A if loadingFlag == 0
    a.mov_imm(2, 0x0203FC00)
    a.ldrb_imm(1, 2, 0x09)
    a.cmp_imm(1, 0)
    a.ldrh_imm(1, 2, 0x0A, cond=0x0)
    a.add_imm(1, 1, 1, cond=0x0)
    a.strh_imm(1, 2, 0x0A, cond=0x0)

    a.label("ml_wait_vblank")
    a.swi(0x05)              # VBlankIntrWait (ONLY SWI 0x05 is ever called!)
    a.b("main_loop")
    a.resolve()

    if len(a.code) > TABLE_DIR_ROM_ADDR - 0x08000000:
        raise RuntimeError(f"Code size {len(a.code)} exceeded table directory offset!")

    rom_size = off_cur - 0x08000000
    rom_buf = bytearray(rom_size)
    rom_buf[:len(a.code)] = a.code

    # Populate GBA Cartridge Header (0x04..0xBF) and compute header checksum at 0xBD
    rom_buf[0x04:0xA0] = NINTENDO_LOGO
    title_bytes = b"BEATSTS22\x00\x00\x00"
    rom_buf[0xA0:0xAC] = title_bytes
    rom_buf[0xAC:0xB0] = b"ABEE"
    rom_buf[0xB0:0xB2] = b"CN"
    rom_buf[0xB2] = 0x96
    rom_buf[0xB3] = 0x00
    rom_buf[0xBC] = 0x00
    chk = 0
    for b_val in rom_buf[0xA0:0xBD]:
        chk = (chk - b_val) & 0xFF
    rom_buf[0xBD] = (chk - 0x19) & 0xFF

    # Write Table Directory at 0x08020000 (offset 0x20000)
    tdir_off = TABLE_DIR_ROM_ADDR - 0x08000000
    struct.pack_into("<II", rom_buf, tdir_off, 0x52494454, len(tables))
    for idx_t, k in enumerate(sorted(tables.keys())):
        name, b_data, cnt = tables[k]
        rom_off = table_addrs[k] - 0x08000000
        struct.pack_into("<IIII", rom_buf, tdir_off + 8 + idx_t * 16, k, rom_off, len(b_data), cnt)
        rom_buf[rom_off:rom_off + len(b_data)] = b_data

    # Write master palette, species palette map, and MIDI frequency lookup tables
    mp_off = master_pal_rom_addr - 0x08000000
    rom_buf[mp_off:mp_off + len(master_pal_bytes)] = master_pal_bytes
    spm_off = sp_pal_map_rom_addr - 0x08000000
    rom_buf[spm_off:spm_off + len(sp_pal_map_bytes)] = sp_pal_map_bytes
    mpf_off = midi_pulse_rom_addr - 0x08000000
    rom_buf[mpf_off:mpf_off + 256] = midi_pulse_freq
    mwf_off = midi_wave_rom_addr - 0x08000000
    rom_buf[mwf_off:mwf_off + 256] = midi_wave_freq
    inpc_off = init_npc_xy_rom_addr - 0x08000000
    rom_buf[inpc_off:inpc_off + 624] = init_npc_xy_bytes
    bgt_off = bg0_boot_tiles_rom_addr - 0x08000000
    rom_buf[bgt_off:bgt_off + len(bg0_boot_tiles)] = bg0_boot_tiles

    with open(out_path, "wb") as f:
        f.write(rom_buf)

    crc32 = zlib.crc32(rom_buf) & 0xFFFFFFFF
    sha256 = hashlib.sha256(rom_buf).hexdigest()
    print(f"[build.py] Built {out_path}: {len(rom_buf)} bytes ({len(rom_buf)/1024:.1f} KB)")
    print(f"  Code size: {len(a.code)} bytes, Header checksum: 0x{rom_buf[0xBD]:02X}")
    print(f"  CRC32: 0x{crc32:08X}, SHA-256: {sha256}")
    return rom_buf, a.labels, table_addrs


def build_all_controls():
    ctrl_dir = os.path.join(ROOT_DIR, "tests", "controls")
    os.makedirs(ctrl_dir, exist_ok=True)
    controls = [
        ("control_move_power.gba", "move_power"),
        ("control_stab_14.gba", "stab_14"),
        ("control_rng_skip.gba", "rng_skip"),
        ("control_9_seals.gba", "9_seals"),
        ("control_tile_offset.gba", "tile_offset"),
        ("control_transposed_track.gba", "transposed_track"),
    ]
    for fname, mode in controls:
        build_rom(os.path.join(ctrl_dir, fname), control_mode=mode)

if __name__ == "__main__":
    build_rom(OUT_ROM_PATH, control_mode=None)
    if "--build-controls" in sys.argv:
        build_all_controls()
