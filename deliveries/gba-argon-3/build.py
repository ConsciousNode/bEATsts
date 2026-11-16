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
    def _multi_dp_imm(self, op, rd, rn, val, s=0, cond=0xE):
        val &= 0xFFFFFFFF
        if val == 0:
            self.emit32(self.dp_imm(op, s, rn, rd, 0, cond))
            return
        try:
            self.emit32(self.dp_imm(op, s, rn, rd, val, cond))
        except ValueError:
            cur_rn = rn
            for shift in (0, 8, 16, 24):
                chunk = val & (0xFF << shift)
                if chunk:
                    self.emit32(self.dp_imm(op, s, cur_rn, rd, chunk, cond))
                    cur_rn = rd
    def add_imm(self, rd, rn, val, s=0, cond=0xE): self._multi_dp_imm(0x4, rd, rn, val, s, cond)
    def adc_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x5, s, rn, rd, val, cond))
    def sub_imm(self, rd, rn, val, s=0, cond=0xE): self._multi_dp_imm(0x2, rd, rn, val, s, cond)
    def sbc_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x6, s, rn, rd, val, cond))
    def rsb_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x3, s, rn, rd, val, cond))
    def and_imm(self, rd, rn, val, s=0, cond=0xE): self.emit32(self.dp_imm(0x0, s, rn, rd, val, cond))
    def orr_imm(self, rd, rn, val, s=0, cond=0xE): self._multi_dp_imm(0xC, rd, rn, val, s, cond)
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
        assert abs(offset) <= 255, f"Halfword offset {offset} > 255!"
        off = abs(offset) & 0xFF
        self.emit32((cond << 28) | (p << 24) | (u << 23) | (1 << 22) | (w << 21) | (1 << 20) | (rn << 16) | (rd << 12) | ((off >> 4) << 8) | 0xB0 | (off & 0xF))

    def strh_imm(self, rd, rn, offset=0, p=1, w=0, cond=0xE):
        u = 1 if offset >= 0 else 0
        assert abs(offset) <= 255, f"Halfword offset {offset} > 255!"
        off = abs(offset) & 0xFF
        self.emit32((cond << 28) | (p << 24) | (u << 23) | (1 << 22) | (w << 21) | (0 << 20) | (rn << 16) | (rd << 12) | ((off >> 4) << 8) | 0xB0 | (off & 0xF))

    def ldrsb_imm(self, rd, rn, offset=0, p=1, w=0, cond=0xE):
        u = 1 if offset >= 0 else 0
        assert abs(offset) <= 255, f"Halfword offset {offset} > 255!"
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

class UIStringPool:
    def __init__(self):
        self.buf = bytearray()
        self.offsets = {}

    def add(self, s):
        s = str(s)
        if s in self.offsets:
            return self.offsets[s]
        off = len(self.buf)
        self.buf.extend(s.encode("utf-8") + b"\x00")
        self.offsets[s] = off
        return off


def emit_core_and_battle(a: ArmAsm, tables_rom_addrs: dict, ui_str_rom_addr: int, ui_pool: UIStringPool, control_mode=None):
    def ui_off(s):
        return ui_str_rom_addr + ui_pool.add(s)

    # =========================================================================
    # String Formatting Helpers (target buffer at 0x02003610, len at 0x02003604)
    # =========================================================================
    # fmt_clear() -> R0 = 0x02003610
    a.label("fmt_clear")
    a.mov_imm(0, 0x02003600)
    a.mov_imm(1, 0)
    a.strh_imm(1, 0, 4)      # len = 0
    a.strb_imm(1, 0, 0x10)   # buf[0] = 0
    a.add_imm(0, 0, 0x10)
    a.bx(14)

    # fmt_putc(R0=byte)
    a.label("fmt_putc")
    a.push([1, 2, 3, 14])
    a.mov_imm(1, 0x02003600)
    a.ldrh_imm(2, 1, 4)
    a.cmp_imm(2, 238)
    a.b("fpc_done", cond=0x2)
    a.add_imm(3, 1, 0x10)
    a.add_reg(3, 3, 2)
    a.strb_imm(0, 3, 0)
    a.mov_imm(0, 0)
    a.strb_imm(0, 3, 1)
    a.add_imm(2, 2, 1)
    a.strh_imm(2, 1, 4)
    a.label("fpc_done")
    a.pop([1, 2, 3, 15])

    # fmt_str_n(R0=str_ptr, R1=max_chars)
    a.label("fmt_str_n")
    a.push([4, 5, 6, 14])
    a.mov_reg(4, 0) # src_ptr
    a.mov_reg(5, 1) # max_chars
    a.label("fsn_loop")
    a.cmp_imm(5, 0)
    a.b("fsn_done", cond=0x0)
    a.ldrb_imm(0, 4, 0)
    a.cmp_imm(0, 0)
    a.b("fsn_done", cond=0x0)
    # Check UTF-8 em-dash \xE2\x80\x94 -> '-' (45)
    a.cmp_imm(0, 0xE2)
    a.b("fsn_norm", cond=0x1)
    a.add_imm(4, 4, 3)
    a.mov_imm(0, 45)
    a.b("fsn_emit")
    a.label("fsn_norm")
    a.add_imm(4, 4, 1)
    a.label("fsn_emit")
    a.bl("fmt_putc")
    a.sub_imm(5, 5, 1)
    a.b("fsn_loop")
    a.label("fsn_done")
    a.pop([4, 5, 6, 15])

    # fmt_str(R0=str_ptr)
    a.label("fmt_str")
    a.push([1, 14])
    a.mov_imm(1, 255)
    a.bl("fmt_str_n")
    a.pop([1, 15])

    # fmt_rom_off_n(R0=pool_off, R1=max_chars)
    a.label("fmt_rom_off_n")
    a.push([2, 14])
    a.cmn_imm(0, 1) # 0xFFFFFFFF?
    a.b("fron_done", cond=0x0)
    a.mov_imm(2, tables_rom_addrs[16])
    a.add_reg(0, 2, 0)
    a.bl("fmt_str_n")
    a.label("fron_done")
    a.pop([2, 15])

    # fmt_rom_off(R0=pool_off)
    a.label("fmt_rom_off")
    a.push([1, 14])
    a.mov_imm(1, 255)
    a.bl("fmt_rom_off_n")
    a.pop([1, 15])

    # fmt_u32(R0=val)
    a.label("fmt_u32")
    a.push([4, 5, 6, 14])
    a.sub_imm(13, 13, 16)
    a.cmp_imm(0, 0)
    a.b("fu32_non_zero", cond=0x1)
    a.mov_imm(0, 48)
    a.bl("fmt_putc")
    a.b("fu32_done")
    a.label("fu32_non_zero")
    a.mov_imm(4, 0) # digit_count
    a.mov_reg(5, 0) # val
    a.label("fu32_div_loop")
    a.cmp_imm(5, 0)
    a.b("fu32_emit_loop", cond=0x0)
    a.mov_reg(0, 5)
    a.mov_imm(1, 10)
    a.bl("udiv32")
    a.mov_reg(5, 0)
    a.add_imm(1, 1, 48)
    a.add_reg(2, 13, 4)
    a.strb_imm(1, 2, 0)
    a.add_imm(4, 4, 1)
    a.b("fu32_div_loop")
    a.label("fu32_emit_loop")
    a.cmp_imm(4, 0)
    a.b("fu32_done", cond=0x0)
    a.sub_imm(4, 4, 1)
    a.add_reg(2, 13, 4)
    a.ldrb_imm(0, 2, 0)
    a.bl("fmt_putc")
    a.b("fu32_emit_loop")
    a.label("fu32_done")
    a.add_imm(13, 13, 16)
    a.pop([4, 5, 6, 15])

    # fmt_u32_pad3(R0=val 1..999)
    a.label("fmt_u32_pad3")
    a.push([4, 14])
    a.mov_reg(4, 0)
    a.cmp_imm(4, 100)
    a.mov_imm(0, 48, cond=0x3)
    a.bl("fmt_putc", cond=0x3)
    a.cmp_imm(4, 10)
    a.mov_imm(0, 48, cond=0x3)
    a.bl("fmt_putc", cond=0x3)
    a.mov_reg(0, 4)
    a.bl("fmt_u32")
    a.pop([4, 15])

    # fmt_sp_name_n(R0=speciesId 1..151, R1=max_chars)
    a.label("fmt_sp_name_n")
    a.push([2, 3, 14])
    a.sub_imm(0, 0, 1)
    a.cmp_imm(0, 151)
    a.mov_imm(0, 0, cond=0x2)
    a.mov_imm(2, 56)
    a.mul(0, 0, 2)
    a.mov_imm(3, tables_rom_addrs[4])
    a.add_reg(0, 3, 0)
    a.ldr_imm(0, 0, 32) # name str_off
    a.bl("fmt_rom_off_n")
    a.pop([2, 3, 15])

    # fmt_mv_name_n(R0=moveId 0..123, R1=max_chars)
    a.label("fmt_mv_name_n")
    a.push([2, 3, 14])
    a.cmp_imm(0, 124)
    a.mov_imm(0, 0, cond=0x2)
    a.mov_imm(2, 36)
    a.mul(0, 0, 2)
    a.mov_imm(3, tables_rom_addrs[3])
    a.add_reg(0, 3, 0)
    a.ldr_imm(0, 0, 12) # name str_off
    a.bl("fmt_rom_off_n")
    a.pop([2, 3, 15])

    # fmt_it_name_n(R0=item_idx 0..24, R1=max_chars)
    a.label("fmt_it_name_n")
    a.push([2, 3, 14])
    a.cmp_imm(0, 25)
    a.mov_imm(0, 0, cond=0x2)
    a.mov_imm(2, 28)
    a.mul(0, 0, 2)
    a.mov_imm(3, tables_rom_addrs[8])
    a.add_reg(0, 3, 0)
    a.ldr_imm(0, 0, 12) # name str_off
    a.bl("fmt_rom_off_n")
    a.pop([2, 3, 15])

    # fmt_tr_name(R0=trainer_idx 0..32)
    a.label("fmt_tr_name")
    a.push([1, 2, 3, 14])
    a.cmp_imm(0, 33)
    a.mov_imm(0, 0, cond=0x2)
    a.mov_imm(2, 48)
    a.mul(0, 0, 2)
    a.mov_imm(3, tables_rom_addrs[11])
    a.add_reg(0, 3, 0)
    a.ldr_imm(0, 0, 4) # name str_off
    a.mov_imm(1, 255)
    a.bl("fmt_rom_off_n")
    a.pop([1, 2, 3, 15])

    # fmt_copy_to_dialog(R0=line_idx 0..3)
    a.label("fmt_copy_to_dialog")
    a.push([1, 2, 3, 14])
    a.and_imm(0, 0, 3)
    a.mov_imm(1, 0x02002800)
    a.add_reg(1, 1, 0, shift_imm=8, shift_type=0) # + line_idx * 256
    a.mov_imm(2, 0x02003610)
    a.label("fctd_lp")
    a.ldrb_imm(3, 2, 0)
    a.strb_imm(3, 1, 0)
    a.add_imm(1, 1, 1)
    a.add_imm(2, 2, 1)
    a.cmp_imm(3, 0)
    a.b("fctd_lp", cond=0x1)
    a.pop([1, 2, 3, 15])

    # blog_clear()
    a.label("blog_clear")
    a.push([0, 1, 14])
    a.mov_imm(0, 0x02003400)
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 0)
    a.mov_imm(0, 0x02003600)
    a.strh_imm(1, 0, 0)
    a.pop([0, 1, 15])

    # fmt_append_to_blog()
    a.label("fmt_append_to_blog")
    a.push([0, 1, 2, 3, 4, 14])
    a.mov_imm(0, 0x02003400)
    a.mov_imm(1, 0x02003600)
    a.ldrh_imm(1, 1, 0)
    a.add_reg(2, 0, 1)      # dst
    a.mov_imm(3, 0x02003610) # src
    a.label("fatb_lp")
    a.ldrb_imm(4, 3, 0)
    a.cmp_imm(4, 0)
    a.b("fatb_dn", cond=0x0)
    a.cmp_imm(1, 500)
    a.b("fatb_dn", cond=0x2)
    a.strb_imm(4, 2, 0)
    a.add_imm(2, 2, 1)
    a.add_imm(3, 3, 1)
    a.add_imm(1, 1, 1)
    a.b("fatb_lp")
    a.label("fatb_dn")
    a.mov_imm(4, 0)
    a.strb_imm(4, 2, 0)
    a.mov_imm(0, 0x02003600)
    a.strh_imm(1, 0, 0)
    a.pop([0, 1, 2, 3, 4, 15])
    a.flush_literals()

    # f64_round_pct(R0=chance_lo, R1=chance_hi) -> R0 = Math.round(chance * 100) = Math.floor(chance * 100.0 + 0.5)
    a.label("f64_round_pct")
    a.push([2, 3, 14])
    a.mov_imm(2, 0)
    a.mov_imm(3, 0x40590000) # 100.0
    a.bl("f64_mul")
    a.mov_imm(2, 0)
    a.mov_imm(3, 0x3FE00000) # 0.5
    a.bl("f64_add_pos")
    a.bl("f64_to_u32_floor")
    a.pop([2, 3, 15])
    a.flush_literals()

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
    a.b("ms_done", cond=0x2)
    a.mov_reg(2, 1, shift_imm=3, shift_type=1)
    a.and_imm(3, 1, 7)
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 3, shift_type=0)
    a.mov_imm(3, 0x02000056)
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
    a.mov_imm(3, 0x0200006A)
    a.add_reg(3, 3, 2)
    a.ldrb_imm(2, 3, 0)
    a.orr_reg(2, 2, 1)
    a.strb_imm(2, 3, 0)
    a.label("mc_done")
    a.pop([1, 2, 3, 15])

    # Helper: bag_add(R0=item_idx 0..24, R1=delta_s32)
    a.label("bag_add")
    a.push([2, 3, 4, 5, 14])
    a.mov_imm(2, 0x0200007E)
    a.add_reg(2, 2, 0, shift_imm=1, shift_type=0)
    a.ldrh_imm(3, 2, 0)
    a.add_reg(3, 3, 1, s=1)
    a.mov_imm(3, 0, cond=0x4)
    a.strh_imm(3, 2, 0)
    a.mov_imm(2, 0x02001072)
    a.add_reg(4, 2, 0)
    a.ldrb_imm(5, 4, 0)
    a.cmp_imm(5, 0)
    a.b("bag_add_done", cond=0x1)
    a.mov_imm(5, 1)
    a.strb_imm(5, 4, 0)
    a.mov_imm(2, 0x02001058)
    a.ldrb_imm(5, 2, 25)
    a.add_reg(4, 2, 5)
    a.strb_imm(0, 4, 0)
    a.add_imm(5, 5, 1)
    a.strb_imm(5, 2, 25)
    a.label("bag_add_done")
    a.pop([2, 3, 4, 5, 15])
    a.flush_literals()

    # Helper: log_battle_event(R0=kind, R1=id, R2=dmg_u16, R3=flags_and_hp)
    a.label("log_battle_event")
    a.push([4, 5, 6, 14])
    a.mov_imm(4, 0x0203FC00)
    a.ldrh_imm(5, 4, 0x0B8)
    a.and_imm(6, 5, 31)
    a.add_imm(5, 5, 1)
    a.strh_imm(5, 4, 0x0B8)
    a.add_reg(6, 4, 6, shift_imm=3, shift_type=0)
    a.add_imm(6, 6, 0x0C0)
    a.strb_imm(0, 6, 0)
    a.strb_imm(1, 6, 1)
    a.strh_imm(2, 6, 2)
    a.strh_imm(3, 6, 4)
    a.mov_imm(4, 0x02001000)
    a.ldr_imm(5, 4, 8)
    a.strh_imm(5, 6, 6)
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
    a.mov_reg(8, 0, shift_imm=29, shift_type=1)

    a.bl("game_rng_next")
    a.mov_imm(1, 1000000000)
    a.umull(2, 3, 0, 1)
    a.str_imm(3, 6, 0x00)
    a.strb_imm(4, 6, 0x04)
    a.strb_imm(5, 6, 0x05)
    a.mov_imm(0, 0)
    a.strb_imm(0, 6, 0x06)
    a.mov_imm(0, 0xFF)
    a.strb_imm(0, 6, 0x07)

    a.mul(0, 5, 5)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.str_imm(0, 6, 0x14)
    a.add_imm(1, 5, 1)
    a.mul(0, 1, 1)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.str_imm(0, 6, 0x18)

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
    a.mov_reg(4, 0)
    a.ldrb_imm(0, 4, 4)
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(5, 0, 1)
    a.mov_imm(0, tables_rom_addrs[4])
    a.add_reg(5, 0, 5)
    a.ldrb_imm(6, 4, 5)
    a.ldrh_imm(7, 4, 0x0A)

    a.ldrb_imm(0, 5, 4)
    a.add_reg(0, 0, 0)
    a.mul(0, 0, 6)
    a.mov_imm(1, 100)
    a.bl("udiv32")
    a.add_reg(0, 0, 6)
    a.add_imm(0, 0, 12)
    a.strh_imm(0, 4, 0x0A)
    a.sub_reg(1, 0, 7, s=1)
    a.mov_imm(1, 0, cond=0x4)
    a.ldrh_imm(2, 4, 0x08)
    a.add_reg(2, 2, 1)
    a.cmp_reg(2, 0)
    a.mov_reg(2, 0, cond=0x8)
    a.strh_imm(2, 4, 0x08)

    for idx_stat, off_mon in [(5, 0x0C), (6, 0x0E), (7, 0x10)]:
        a.ldrb_imm(0, 5, idx_stat)
        a.add_reg(0, 0, 0)
        a.mul(0, 0, 6)
        a.mov_imm(1, 100)
        a.bl("udiv32")
        a.add_imm(0, 0, 6)
        a.strh_imm(0, 4, off_mon)

    a.add_imm(0, 6, 1)
    a.mul(0, 0, 0)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.str_imm(0, 4, 0x18)
    a.pop([4, 5, 6, 7, 8, 15])
    a.flush_literals()

    # grant_xp(R0=mon_ptr, R1=xp_gain) -> also appends level-up/learn/evo messages to battle_log_buf!
    a.label("grant_xp")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(4, 0)
    a.ldr_imm(2, 4, 0x14)
    a.add_reg(2, 2, 1)
    a.str_imm(2, 4, 0x14)

    a.label("gx_lv_loop")
    a.ldr_imm(2, 4, 0x14)
    a.ldr_imm(3, 4, 0x18)
    a.cmp_reg(2, 3)
    a.b("gx_done", cond=0x3)
    a.ldrb_imm(5, 4, 5)
    a.cmp_imm(5, 100)
    a.b("gx_done", cond=0x2)
    a.add_imm(5, 5, 1)
    a.strb_imm(5, 4, 5)
    a.mov_reg(0, 4)
    a.bl("recalc_stats")

    # Append "${mon.nickname} reached Lv.${mon.level}! " to battle_log_buf
    a.bl("fmt_clear")
    a.ldrb_imm(0, 4, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" reached Lv."))
    a.bl("fmt_str")
    a.mov_reg(0, 5)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off("! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.ldrb_imm(0, 4, 4)
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(6, 0, 1)
    a.mov_imm(0, tables_rom_addrs[4])
    a.add_reg(6, 0, 6)

    a.mov_imm(7, 0)
    a.label("gx_ls_loop")
    a.add_reg(0, 6, 7, shift_imm=1, shift_type=0)
    a.ldrb_imm(1, 0, 40)
    a.ldrb_imm(8, 0, 41)
    a.cmp_reg(1, 5)
    a.b("gx_ls_next", cond=0x1)
    a.ldrh_imm(9, 4, 0x12)
    a.mov_imm(10, 0)
    a.label("gx_chk_known")
    a.cmp_reg(10, 9)
    a.b("gx_not_known", cond=0x2)
    a.add_reg(0, 4, 10)
    a.ldrb_imm(1, 0, 0x1C)
    a.cmp_reg(1, 8)
    a.b("gx_ls_next", cond=0x0)
    a.add_imm(10, 10, 1)
    a.b("gx_chk_known")

    a.label("gx_not_known")
    a.mov_imm(0, 36)
    a.mul(10, 8, 0)
    a.mov_imm(0, tables_rom_addrs[3])
    a.add_reg(10, 0, 10)
    a.ldrb_imm(11, 10, 4)

    a.cmp_imm(9, 4)
    a.b("gx_replace_mv", cond=0x2)
    a.add_reg(0, 4, 9)
    a.strb_imm(8, 0, 0x1C)
    a.strb_imm(11, 0, 0x20)
    a.strb_imm(11, 0, 0x24)
    a.add_imm(9, 9, 1)
    a.strh_imm(9, 4, 0x12)
    a.b("gx_log_learned")

    a.label("gx_replace_mv")
    a.mov_imm(9, 0)
    a.ldrb_imm(0, 4, 0x1C)
    a.mov_imm(1, 36)
    a.mul(0, 0, 1)
    a.mov_imm(2, tables_rom_addrs[3])
    a.add_reg(0, 2, 0)
    a.ldrb_imm(3, 0, 2)

    for slot_i in (1, 2, 3):
        a.ldrb_imm(0, 4, 0x1C + slot_i)
        a.mul(0, 0, 1)
        a.add_reg(0, 2, 0)
        a.ldrb_imm(0, 0, 2)
        a.cmp_reg(0, 3)
        a.mov_reg(3, 0, cond=0x3)
        a.mov_imm(9, slot_i, cond=0x3)

    a.ldrb_imm(0, 10, 2)
    a.cmp_reg(0, 3)
    a.b("gx_ls_next", cond=0x9)
    a.add_reg(0, 4, 9)
    a.strb_imm(8, 0, 0x1C)
    a.strb_imm(11, 0, 0x20)
    a.strb_imm(11, 0, 0x24)

    a.label("gx_log_learned")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Learned "))
    a.bl("fmt_str")
    a.mov_reg(0, 8)
    a.mov_imm(1, 255)
    a.bl("fmt_mv_name_n")
    a.mov_imm(0, ui_off("! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.label("gx_ls_next")
    a.add_imm(7, 7, 1)
    a.cmp_imm(7, 8)
    a.b("gx_ls_loop", cond=0x3)

    a.ldrb_imm(0, 6, 8)
    a.cmp_imm(0, 0)
    a.b("gx_lv_loop", cond=0x0)
    a.ldrb_imm(1, 6, 9)
    a.cmp_reg(5, 1)
    a.b("gx_lv_loop", cond=0x3)
    # Evolve!
    a.strb_imm(0, 4, 4)
    a.mov_reg(7, 0)
    a.mov_reg(0, 4)
    a.bl("recalc_stats")
    a.mov_reg(0, 7)
    a.bl("mark_caught")
    a.mov_imm(0, 16) # 'evolution' music track!
    a.bl("play_music")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Evolved into "))
    a.bl("fmt_str")
    a.mov_reg(0, 7)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off("! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
    a.b("gx_lv_loop")

    a.label("gx_done")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # compute_damage(R0=attacker_ptr, R1=defender_ptr, R2=moveId, R3=battleTemp_s32)
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
    a.add_reg(8, 0, 8)
    a.ldrb_imm(0, 8, 6)
    a.cmp_imm(0, 2)
    a.b("cd_zero_dmg", cond=0x0)
    a.ldrb_imm(0, 8, 2)
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

    a.ldrb_imm(0, 8, 1)
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
    a.mov_imm(1, 0)
    a.mov_imm(2, 0)
    a.add_imm(13, 13, 32)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # do_foe_attack(R0=foe_ptr, R1=player_ptr) -> appends foe attack string to battle_log_buf!
    a.label("do_foe_attack")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
    a.ldrh_imm(0, 4, 0x08)
    a.cmp_imm(0, 0)
    a.b("dfa_done", cond=0x0)
    a.ldrh_imm(0, 5, 0x08)
    a.cmp_imm(0, 0)
    a.b("dfa_done", cond=0x0)

    a.bl("game_rng_next")
    a.ldrh_imm(1, 4, 0x12)
    a.umull(2, 3, 0, 1)
    a.add_reg(0, 4, 3)
    a.ldrb_imm(6, 0, 0x1C)

    a.mov_imm(0, 36)
    a.mul(7, 6, 0)
    a.mov_imm(0, tables_rom_addrs[3])
    a.add_reg(7, 0, 7)

    a.mov_imm(8, 0x02001100)
    a.ldrsb_imm(0, 8, 6)
    a.ldrsb_imm(1, 7, 5)
    a.add_reg(0, 0, 1)
    a.cmn_imm(0, 2)
    a.mvn_imm(0, 1, cond=0xB)
    a.cmp_imm(0, 2)
    a.mov_imm(0, 2, cond=0xC)
    a.strb_imm(0, 8, 6)

    a.mov_reg(3, 0)
    a.mov_reg(0, 4)
    a.mov_reg(1, 5)
    a.mov_reg(2, 6)
    a.bl("compute_damage")
    a.mov_reg(9, 0) # R9 = res.dmg

    a.ldrb_imm(3, 7, 1)
    a.strb_imm(3, 4, 7)

    a.ldrh_imm(3, 5, 0x08)
    a.sub_reg(3, 3, 9, s=1)
    a.mov_imm(3, 0, cond=0x4)
    a.strh_imm(3, 5, 0x08)

    a.cmp_imm(2, 0)
    a.orr_imm(1, 1, 0x08, cond=0x1)
    a.cmp_imm(3, 0)
    a.orr_imm(1, 1, 0x40, cond=0x0)
    a.and_imm(3, 3, 0xFF)
    a.orr_reg(3, 1, 3, shift_imm=8, shift_type=0)
    a.mov_reg(2, 9)
    a.mov_reg(1, 6)
    a.mov_imm(0, 2)
    a.bl("log_battle_event")

    # Append "${foe.nickname} used ${mv.name} (-${res.dmg} HP)!" to battle_log_buf
    a.bl("fmt_clear")
    a.ldrb_imm(0, 4, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" used "))
    a.bl("fmt_str")
    a.mov_reg(0, 6)
    a.mov_imm(1, 255)
    a.bl("fmt_mv_name_n")
    a.mov_imm(0, ui_off(" (-"))
    a.bl("fmt_str")
    a.mov_reg(0, 9)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off(" HP)!"))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.label("dfa_done")
    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # execute_battle_turn(R0=moveId)
    a.label("execute_battle_turn")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(6, 0)
    a.mov_imm(8, 0x02001100)
    a.ldrb_imm(0, 8, 5)
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.mov_imm(2, 0x020000B4)
    a.add_reg(4, 2, 0)

    a.ldrb_imm(0, 8, 4)
    a.mul(0, 0, 1)
    a.add_imm(5, 8, 0x10)
    a.add_reg(5, 5, 0)

    a.mov_imm(0, 36)
    a.mul(7, 6, 0)
    a.mov_imm(0, tables_rom_addrs[3])
    a.add_reg(7, 0, 7)

    a.ldrsb_imm(0, 8, 6)
    a.ldrsb_imm(1, 7, 5)
    a.add_reg(0, 0, 1)
    a.cmn_imm(0, 2)
    a.mvn_imm(0, 1, cond=0xB)
    a.cmp_imm(0, 2)
    a.mov_imm(0, 2, cond=0xC)
    a.strb_imm(0, 8, 6)

    a.mov_reg(3, 0)
    a.mov_reg(0, 4)
    a.mov_reg(1, 5)
    a.mov_reg(2, 6)
    a.bl("compute_damage")
    a.mov_reg(9, 0)  # res.dmg
    a.mov_reg(10, 1) # eff_code (1..5, or 0)
    a.mov_reg(11, 2) # combo_ptr

    a.ldrb_imm(0, 7, 1)
    a.strb_imm(0, 4, 7)
    if control_mode != "no_flash":
        a.ldrb_imm(0, 7, 7) # mv.anim (0..7)
        a.mov_imm(1, 0x02001000)
        a.strb_imm(0, 1, 0x3B) # anim_type
        a.mov_imm(0, 21)
        a.strb_imm(0, 1, 0x3A) # anim_timer_frames = 21
        a.ldr_imm(0, 1, 0x0C)  # frame_counter (= F_prev + 1)
        a.add_imm(0, 0, 20)    # anim_end_fc = frame_counter + 20 (= F_prev + 21 -> flash for dFc <= 20)
        a.str_imm(0, 1, 0x54)

    # Start battle_log_buf: "${player.nickname} used ${mv.name}! "
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.ldrb_imm(0, 4, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" used "))
    a.bl("fmt_str")
    a.mov_reg(0, 6)
    a.mov_imm(1, 255)
    a.bl("fmt_mv_name_n")
    a.mov_imm(0, ui_off("! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.cmp_imm(9, 0)
    a.b("ebt_after_dmg", cond=0x0)
    a.ldrh_imm(0, 5, 0x08)
    a.sub_reg(0, 0, 9, s=1)
    a.mov_imm(0, 0, cond=0x4)
    a.strh_imm(0, 5, 0x08)

    # Check eff_code > 3 ("Super tasty! ") or eff_code < 3 ("Not very savory... ")
    a.cmp_imm(10, 3)
    a.b("ebt_chk_combo_msg", cond=0x0)
    a.b("ebt_weak_msg", cond=0x3)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Super tasty! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
    a.b("ebt_chk_combo_msg")
    a.label("ebt_weak_msg")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Not very savory... "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.label("ebt_chk_combo_msg")
    a.cmp_imm(11, 0)
    a.b("ebt_chk_drain", cond=0x0)
    a.orr_imm(10, 10, 0x08)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("FLAVOR COMBO ("))
    a.bl("fmt_str")
    a.ldr_imm(0, 11, 0) # combo.name str_off
    a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(")! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.ldrh_imm(0, 4, 0x0A)
    a.bl("f64_from_u32")
    a.ldr_imm(2, 11, 12)
    a.ldr_imm(3, 11, 16)
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
    a.ldrb_imm(0, 7, 10)
    a.cmp_imm(0, 0)
    a.b("ebt_after_dmg", cond=0x0)
    a.mov_reg(0, 9)
    a.bl("f64_from_u32")
    a.ldr_imm(2, 7, 20)
    a.ldr_imm(3, 7, 24)
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
    a.ldrb_imm(0, 7, 8)
    a.cmp_imm(0, 0)
    a.b("ebt_after_status", cond=0x0)
    a.bl("game_rng_next")
    a.ldrb_imm(1, 7, 9)
    a.cmp_imm(1, 0)
    a.b("ebt_inflict_status", cond=0x0)
    a.ldr_imm(1, 7, 28)
    a.cmn_imm(1, 1)
    a.b("ebt_inflict_status", cond=0x0)
    a.cmp_reg(0, 1)
    a.b("ebt_after_status", cond=0x2)
    a.label("ebt_inflict_status")
    a.ldrb_imm(0, 7, 8)
    a.strb_imm(0, 5, 6)
    a.orr_imm(10, 10, 0x10)
    # Append "${foe.nickname} is ${mv.status}! "
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" is "))
    a.bl("fmt_str")
    a.ldrb_imm(1, 7, 8)
    for st_i, st_s in [(1, "Sizzling"), (2, "Brined"), (3, "Drowsy"), (4, "Seasoned"), (5, "Appetized")]:
        a.cmp_imm(1, st_i)
        a.mov_imm(0, ui_off(st_s + "! "), cond=0x0)
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.label("ebt_after_status")
    a.ldrh_imm(3, 5, 0x08)
    a.cmp_imm(3, 0)
    a.orr_imm(10, 10, 0x40, cond=0x0)
    a.and_imm(0, 3, 0xFF)
    a.orr_reg(3, 10, 0, shift_imm=8, shift_type=0)
    a.mov_imm(0, 1)
    a.mov_reg(1, 6)
    a.mov_reg(2, 9)
    a.bl("log_battle_event")

    a.ldrh_imm(0, 5, 0x08)
    a.cmp_imm(0, 0)
    a.b("ebt_foe_alive", cond=0x1)

    a.ldrb_imm(0, 5, 5)
    a.mov_reg(0, 0, shift_imm=4, shift_type=0)
    a.ldrb_imm(1, 8, 1)
    a.cmp_imm(1, 0)
    a.b("ebt_xp_wild", cond=0x1)
    a.bl("f64_from_u32")
    a.mov_imm(2, 0x66666666)
    a.mov_imm(3, 0x3FF66666)
    a.bl("f64_mul")
    a.bl("f64_to_u32_floor")
    a.label("ebt_xp_wild")
    a.mov_reg(9, 0) # R9 = xpGain
    # Append "${foe.nickname} fainted! +${xpGain} XP! "
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" fainted! +"))
    a.bl("fmt_str")
    a.mov_reg(0, 9)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off(" XP! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.mov_reg(1, 9)
    a.mov_reg(0, 4)
    a.bl("grant_xp")

    a.ldrb_imm(0, 8, 4)
    a.ldrb_imm(1, 8, 3)
    a.add_imm(0, 0, 1)
    a.cmp_reg(0, 1)
    a.b("ebt_win_battle", cond=0x2)
    a.strb_imm(0, 8, 4) # foe_idx++
    # Append "${b.trainer.name} sent out ${b.foeParty[b.foeIdx].nickname}!"
    a.mov_reg(9, 0)
    a.bl("fmt_clear")
    a.ldrb_imm(0, 8, 2) # trainer_idx
    a.bl("fmt_tr_name")
    a.mov_imm(0, ui_off(" sent out "))
    a.bl("fmt_str")
    a.mov_imm(1, 48)
    a.mul(1, 9, 1)
    a.add_imm(1, 1, 0x10)
    a.add_reg(1, 8, 1)
    a.ldrb_imm(0, 1, 4) # next foe speciesId
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, 33) # '!'
    a.bl("fmt_putc")
    a.bl("fmt_append_to_blog")
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("ebt_win_battle")
    a.mov_imm(0, 1)
    a.strb_imm(0, 8, 0x0A)
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])

    a.label("ebt_foe_alive")
    a.mov_reg(0, 5)
    a.mov_reg(1, 4)
    a.bl("do_foe_attack")
    a.ldrh_imm(0, 4, 0x08)
    a.cmp_imm(0, 0)
    a.b("ebt_turn_end", cond=0x1)
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(1, 0, 0x0B0)
    a.add_imm(2, 0, 0x0B4)
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
    a.strb_imm(3, 8, 5)
    a.mov_reg(9, 2) # next mon ptr
    a.bl("fmt_clear")
    a.mov_imm(0, 32)
    a.bl("fmt_putc")
    a.ldrb_imm(0, 4, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" fainted! Go, "))
    a.bl("fmt_str")
    a.ldrb_imm(0, 9, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, 33)
    a.bl("fmt_putc")
    a.bl("fmt_append_to_blog")
    a.b("ebt_turn_end")

    a.label("ebt_all_fainted")
    a.mov_imm(0, 2)
    a.strb_imm(0, 8, 0x0A)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off(" All your bEATsts fainted! Rushing back to Simmer Inn..."))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.label("ebt_turn_end")
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # calc_plating_chance(R0=foe_ptr, R1=item_idx) -> R0:R1 = chance_f64
    a.label("calc_plating_chance")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)

    a.mov_imm(0, 28)
    a.mul(6, 5, 0)
    a.mov_imm(0, tables_rom_addrs[8])
    a.add_reg(6, 0, 6)
    a.ldrb_imm(0, 6, 0)
    a.cmp_imm(0, 0)
    a.b("cpc_zero", cond=0x1)

    a.ldrb_imm(0, 4, 4)
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(7, 0, 1)
    a.mov_imm(0, tables_rom_addrs[4])
    a.add_reg(7, 0, 7)

    a.mov_imm(8, 0x02000000)
    a.ldrb_imm(0, 7, 10)
    a.ldrb_imm(1, 8, 0x2C)
    a.cmp_imm(0, 0)
    a.b("cpc_chk_tier", cond=0x0)
    a.cmp_imm(1, 0)
    a.b("cpc_zero", cond=0x0)

    a.label("cpc_chk_tier")
    a.ldrb_imm(0, 7, 11)
    a.cmp_imm(0, 0)
    a.b("cpc_calc", cond=0x0)
    a.ldrb_imm(1, 6, 1)
    a.cmp_reg(1, 0)
    a.b("cpc_zero", cond=0x3)

    a.label("cpc_calc")
    a.ldrh_imm(0, 4, 0x0A)
    a.add_reg(8, 0, 0, shift_imm=1, shift_type=0)
    a.ldrh_imm(1, 4, 0x08)
    a.sub_reg(0, 8, 1, shift_imm=1, shift_type=0)
    a.bl("f64_from_u32")
    a.mov_reg(9, 0); a.mov_reg(10, 1)
    a.mov_reg(0, 8)
    a.bl("f64_from_u32")
    a.mov_reg(2, 0); a.mov_reg(3, 1)
    a.mov_reg(0, 9); a.mov_reg(1, 10)
    a.bl("f64_div")
    a.mov_imm(2, 0x9999999A)
    a.mov_imm(3, 0x3FB99999)
    a.cmp_reg(1, 3)
    a.cmp_reg(0, 2, cond=0x0)
    a.mov_reg(0, 2, cond=0x3)
    a.mov_reg(1, 3, cond=0x3)
    a.mov_reg(9, 0); a.mov_reg(10, 1)

    a.ldr_imm(0, 7, 24)
    a.ldr_imm(1, 7, 28)
    a.ldr_imm(2, 6, 20)
    a.ldr_imm(3, 6, 24)
    a.bl("f64_mul")
    a.mov_reg(2, 9); a.mov_reg(3, 10)
    a.bl("f64_mul")

    a.ldrb_imm(4, 4, 6)
    a.mov_imm(2, 0)
    a.mov_imm(3, 0x3FF00000)
    a.cmp_imm(4, 0)
    a.mov_imm(2, 0xCCCCCCCD, cond=0x1)
    a.mov_imm(3, 0x3FF4CCCC, cond=0x1)
    a.cmp_imm(4, 5)
    a.mov_imm(2, 0, cond=0x0)
    a.mov_imm(3, 0x3FF80000, cond=0x0)
    a.bl("f64_mul")

    a.mov_imm(4, 0x02001100)
    a.ldrb_imm(4, 4, 7)
    a.cmp_imm(4, 0)
    a.mov_imm(2, 0, cond=0x0); a.mov_imm(3, 0x3FF00000, cond=0x0)
    a.mov_imm(2, 0x9999999A, cond=0x1); a.mov_imm(3, 0x3FF99999, cond=0x1)
    a.bl("f64_mul")

    a.ldrb_imm(4, 7, 10)
    a.mov_imm(5, 0x02000000)
    a.ldrb_imm(5, 5, 0x2C)
    a.and_reg(4, 4, 5, s=1)
    a.mov_imm(2, 0, cond=0x0); a.mov_imm(3, 0x3FF00000, cond=0x0)
    a.mov_imm(2, 0x9999999A, cond=0x1); a.mov_imm(3, 0x3FF59999, cond=0x1)
    a.bl("f64_mul")

    a.mov_imm(2, 0x66666666)
    a.mov_imm(3, 0x3FEE6666)
    a.cmp_reg(1, 3)
    a.cmp_reg(0, 2, cond=0x0)
    a.mov_reg(0, 2, cond=0x8)
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
    a.mov_reg(6, 0)
    a.mvn_imm(1, 0)
    a.bl("bag_add")

    a.mov_imm(8, 0x02001100)
    a.ldrb_imm(0, 8, 5)
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.mov_imm(2, 0x020000B4)
    a.add_reg(4, 2, 0)
    a.ldrb_imm(0, 8, 4)
    a.mul(0, 0, 1)
    a.add_imm(5, 8, 0x10)
    a.add_reg(5, 5, 0)

    a.mov_imm(0, 28)
    a.mul(7, 6, 0)
    a.mov_imm(0, tables_rom_addrs[8])
    a.add_reg(7, 0, 7)
    a.ldrb_imm(0, 7, 0)
    a.cmp_imm(0, 4)
    a.b("upi_plate", cond=0x1)
    a.mov_imm(0, 1)
    a.strb_imm(0, 8, 7)
    a.ldrh_imm(3, 5, 0x08)
    a.and_imm(3, 3, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.mov_imm(0, 4)
    a.mov_reg(1, 6)
    a.mov_imm(2, 0)
    a.bl("log_battle_event")
    # Log: "Sprinkled ${it.name}! ${foe.nickname} looks delighted! ${foeMsg}"
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Sprinkled "))
    a.bl("fmt_str")
    a.mov_reg(0, 6)
    a.mov_imm(1, 255)
    a.bl("fmt_it_name_n")
    a.mov_imm(0, ui_off("! "))
    a.bl("fmt_str")
    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" looks delighted! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
    a.mov_reg(0, 5)
    a.mov_reg(1, 4)
    a.bl("do_foe_attack")
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])

    a.label("upi_plate")
    a.mov_reg(0, 5)
    a.mov_reg(1, 6)
    a.bl("calc_plating_chance")
    a.orr_reg(2, 0, 1, s=1)
    a.b("upi_zero_chance", cond=0x0)
    a.mov_reg(9, 0); a.mov_reg(10, 1)
    a.bl("game_rng_next")
    a.bl("f64_from_mulberry")
    a.cmp_reg(1, 10)
    a.cmp_reg(0, 9, cond=0x0)
    a.b("upi_plate_fail", cond=0x2)

    a.ldrb_imm(0, 5, 4)
    a.bl("mark_caught")
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(1, 0, 0x0B0)
    a.cmp_imm(1, 6)
    a.b("upi_to_box", cond=0x2)
    a.mov_imm(2, 48)
    a.mul(2, 1, 2)
    a.add_imm(1, 1, 1)
    a.strb_imm(1, 0, 0x0B0)
    a.add_imm(0, 0, 0x0B4)
    a.add_reg(0, 0, 2)
    for off in range(0, 48, 4):
        a.ldr_imm(3, 5, off)
        a.str_imm(3, 0, off)
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" sat down at your "))
    a.bl("fmt_str")
    a.mov_reg(0, 6)
    a.mov_imm(1, 255)
    a.bl("fmt_it_name_n")
    a.mov_imm(0, ui_off(" and joined your party!"))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
    a.b("upi_caught_log")

    a.label("upi_to_box")
    a.ldrb_imm(1, 0, 0x0B1)
    a.cmp_imm(1, 151)
    a.b("upi_box_msg", cond=0x2)
    a.mov_imm(2, 24)
    a.mul(2, 1, 2)
    a.add_imm(1, 1, 1)
    a.strb_imm(1, 0, 0x0B1)
    a.mov_imm(3, 0x020001D4)
    a.add_reg(0, 3, 2)
    a.ldr_imm(1, 5, 0x00); a.str_imm(1, 0, 0x00)
    a.ldr_imm(1, 5, 0x04); a.str_imm(1, 0, 0x04)
    a.ldrb_imm(1, 5, 0x12); a.strb_imm(1, 0, 0x07)
    a.ldr_imm(1, 5, 0x08); a.str_imm(1, 0, 0x08)
    a.ldr_imm(1, 5, 0x0C); a.str_imm(1, 0, 0x0C)
    a.ldrh_imm(1, 5, 0x10); a.strh_imm(1, 0, 0x10)
    a.ldr_imm(1, 5, 0x14)
    a.mov_reg(1, 1, shift_imm=3, shift_type=1)
    a.strh_imm(1, 0, 0x12)
    a.ldr_imm(1, 5, 0x1C); a.str_imm(1, 0, 0x14)
    a.label("upi_box_msg")
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" sat down at your "))
    a.bl("fmt_str")
    a.mov_reg(0, 6)
    a.mov_imm(1, 255)
    a.bl("fmt_it_name_n")
    a.mov_imm(0, ui_off(" and hopped into your Box!"))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.label("upi_caught_log")
    a.ldrh_imm(3, 5, 0x08)
    a.and_imm(3, 3, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.orr_imm(3, 3, 0x20)
    a.mov_imm(0, 3)
    a.mov_reg(1, 6)
    a.mov_imm(2, 0)
    a.bl("log_battle_event")
    a.mov_imm(0, 4)
    a.strb_imm(0, 8, 0x0A)
    a.mov_imm(0, 6)
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
    # Check if nightOnly && !isNight vs minTier
    a.ldrb_imm(0, 5, 4)
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(0, 0, 1)
    a.mov_imm(1, tables_rom_addrs[4])
    a.add_reg(9, 1, 0) # sp_ptr
    a.ldrb_imm(0, 9, 10) # nightOnly
    a.mov_imm(1, 0x02000000)
    a.ldrb_imm(1, 1, 0x2C) # isNight
    a.cmp_imm(0, 0)
    a.b("upi_zc_tier", cond=0x0)
    a.cmp_imm(1, 0)
    a.b("upi_zc_tier", cond=0x1)
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" only sits down at Night!"))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])

    a.label("upi_zc_tier")
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" insists on a Tier "))
    a.bl("fmt_str")
    a.ldrb_imm(0, 9, 11) # minTier
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off("+ setting!"))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
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
    # Log: "${foe.nickname} sniffed the ${it.name} (${Math.round(chance*100)}%) and stepped back! ${foeMsg}"
    a.mov_reg(0, 9); a.mov_reg(1, 10)
    a.bl("f64_round_pct")
    a.mov_reg(9, 0) # pct
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" sniffed the "))
    a.bl("fmt_str")
    a.mov_reg(0, 6)
    a.mov_imm(1, 255)
    a.bl("fmt_it_name_n")
    a.mov_imm(0, ui_off(" ("))
    a.bl("fmt_str")
    a.mov_reg(0, 9)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off("%) and stepped back! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
    a.mov_reg(0, 5)
    a.mov_reg(1, 4)
    a.bl("do_foe_attack")
    a.mov_imm(0, 6)
    a.strb_imm(0, 8, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])
    a.flush_literals()

    # Helper: build_bag_filter(R0=mode, R1=dst_u8_array) -> R0=count
    a.label("build_bag_filter")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
    a.mov_imm(6, 0)
    a.mov_imm(7, 0x02001058)
    a.ldrb_imm(8, 7, 25)
    a.mov_imm(9, 0)
    a.label("bbf_loop")
    a.cmp_reg(9, 8)
    a.b("bbf_done", cond=0x2)
    a.add_reg(0, 7, 9)
    a.ldrb_imm(0, 0, 0)
    a.mov_imm(1, 0x0200007E)
    a.add_reg(1, 1, 0, shift_imm=1, shift_type=0)
    a.ldrh_imm(1, 1, 0)
    a.cmp_imm(1, 0)
    a.b("bbf_next", cond=0x0)
    a.cmp_imm(4, 0)
    a.b("bbf_match", cond=0x0)
    a.mov_imm(2, 28)
    a.mul(2, 0, 2)
    a.mov_imm(3, tables_rom_addrs[8])
    a.add_reg(2, 3, 2)
    a.ldrb_imm(2, 2, 0)
    a.cmp_imm(4, 1)
    a.b("bbf_chk_hcr", cond=0x1)
    a.cmp_imm(2, 0)
    a.cmp_imm(2, 4, cond=0x1)
    a.b("bbf_match", cond=0x0)
    a.b("bbf_next")
    a.label("bbf_chk_hcr")
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

    # handle_battle_input(R0=btn)
    a.label("handle_battle_input")
    a.push([4, 5, 6, 7, 8, 9, 10, 14])
    a.sub_imm(13, 13, 32)
    a.mov_reg(4, 0)
    a.mov_imm(5, 0x02001100)
    a.ldrb_imm(6, 5, 8)
    a.ldrb_imm(7, 5, 9)

    # Phase 6: LOG
    a.cmp_imm(6, 6)
    a.b("hbi_chk_main", cond=0x1)
    a.cmp_imm(4, 0)
    a.cmp_imm(4, 1, cond=0x1)
    a.b("hbi_ret", cond=0x1)
    a.ldrb_imm(0, 5, 0x0A)
    a.cmp_imm(0, 0)
    a.b("hbi_log_to_main", cond=0x0)
    a.cmp_imm(0, 2)
    a.bl("heal_party", cond=0x0)
    a.mov_imm(1, 0)
    a.strb_imm(1, 5, 0)
    a.strb_imm(1, 5, 8)
    a.mov_imm(1, 0x02001000)
    a.mov_imm(2, 3)
    a.strb_imm(2, 1, 0x20)
    a.b("hbi_ret")
    a.label("hbi_log_to_main")
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 8)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 9)
    a.b("hbi_ret")

    # Phase 1: MAIN
    a.label("hbi_chk_main")
    a.cmp_imm(6, 1)
    a.b("hbi_chk_fight", cond=0x1)
    a.cmp_imm(4, 1)
    a.b("hbi_main_not_b", cond=0x1)
    a.ldrb_imm(0, 5, 1)
    a.cmp_imm(0, 0)
    a.b("hbi_ret", cond=0x0)
    a.mov_imm(0, 7)
    a.mov_imm(1, 0)
    a.mov_imm(2, 0)
    a.mov_imm(3, 0)
    a.bl("log_battle_event")
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Got away safely!"))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
    a.mov_imm(0, 3)
    a.strb_imm(0, 5, 0x0A)
    a.mov_imm(0, 6)
    a.strb_imm(0, 5, 8)
    a.b("hbi_ret")

    a.label("hbi_main_not_b")
    a.cmp_imm(4, 4); a.cmp_imm(4, 5, cond=0x1)
    a.eor_imm(7, 7, 1, cond=0x0)
    a.strb_imm(7, 5, 9, cond=0x0)
    a.b("hbi_ret", cond=0x0)
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1)
    a.eor_imm(7, 7, 2, cond=0x0)
    a.strb_imm(7, 5, 9, cond=0x0)
    a.b("hbi_ret", cond=0x0)
    a.cmp_imm(4, 0)
    a.b("hbi_ret", cond=0x1)
    a.cmp_imm(7, 0)
    a.mov_imm(0, 2, cond=0x0)
    a.b("hbi_set_phase", cond=0x0)
    a.cmp_imm(7, 1)
    a.b("hbi_main_c2", cond=0x1)
    a.ldrb_imm(0, 5, 1)
    a.cmp_imm(0, 0)
    a.b("hbi_main_plate_wild", cond=0x1)
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Cannot plate another chef bEATst!"))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")
    a.mov_imm(0, 6)
    a.strb_imm(0, 5, 8)
    a.b("hbi_ret")
    a.label("hbi_main_plate_wild")
    a.mov_imm(0, 3)
    a.b("hbi_set_phase")
    a.label("hbi_main_c2")
    a.cmp_imm(7, 2)
    a.mov_imm(0, 4, cond=0x0)
    a.mov_imm(0, 5, cond=0x1)
    a.label("hbi_set_phase")
    a.strb_imm(0, 5, 8)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 9)
    a.b("hbi_ret")

    # Phase 2: FIGHT
    a.label("hbi_chk_fight")
    a.cmp_imm(6, 2)
    a.b("hbi_chk_plate", cond=0x1)
    a.ldrb_imm(0, 5, 5)
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.mov_imm(1, 0x020000B4)
    a.add_reg(8, 1, 0)
    a.ldrh_imm(9, 8, 0x12)

    a.cmp_imm(4, 1)
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(4, 4); a.cmp_imm(4, 7, cond=0x1)
    a.b("hbi_fight_ul", cond=0x1)
    a.add_imm(0, 7, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_fight_ul")
    a.cmp_imm(4, 5); a.cmp_imm(4, 6, cond=0x1)
    a.b("hbi_fight_a", cond=0x1)
    a.add_reg(0, 7, 9)
    a.sub_imm(0, 0, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_fight_a")
    a.cmp_imm(4, 0)
    a.b("hbi_ret", cond=0x1)
    a.add_reg(0, 8, 7)
    a.ldrb_imm(1, 0, 0x20)
    a.cmp_imm(1, 0)
    a.b("hbi_fight_no_pp", cond=0x0)
    a.sub_imm(1, 1, 1)
    a.strb_imm(1, 0, 0x20)
    a.ldrb_imm(0, 0, 0x1C)
    a.bl("execute_battle_turn")
    a.b("hbi_ret")
    a.label("hbi_fight_no_pp")
    a.mov_imm(0, 0)
    a.label("hbi_chk_all_pp")
    a.cmp_reg(0, 9)
    a.b("hbi_struggle", cond=0x2)
    a.add_reg(1, 8, 0)
    a.ldrb_imm(1, 1, 0x20)
    a.cmp_imm(1, 0)
    a.b("hbi_ret", cond=0x1)
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
    a.mov_reg(9, 0)
    a.cmp_imm(4, 1)
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(9, 0)
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(4, 7)
    a.b("hbi_plate_up", cond=0x1)
    a.add_imm(0, 7, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_plate_up")
    a.cmp_imm(4, 6)
    a.b("hbi_plate_a", cond=0x1)
    a.add_reg(0, 7, 9)
    a.sub_imm(0, 0, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_plate_a")
    a.cmp_imm(4, 0)
    a.b("hbi_ret", cond=0x1)
    a.add_reg(0, 13, 7)
    a.ldrb_imm(0, 0, 0)
    a.bl("use_plating_item")
    a.b("hbi_ret")

    # Phase 4: BAG
    a.label("hbi_chk_bag")
    a.cmp_imm(6, 4)
    a.b("hbi_chk_party", cond=0x1)
    a.mov_imm(0, 2)
    a.mov_reg(1, 13)
    a.bl("build_bag_filter")
    a.mov_reg(9, 0)
    a.cmp_imm(4, 1)
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(9, 0)
    a.b("hbi_to_main", cond=0x0)
    a.cmp_imm(4, 7)
    a.b("hbi_bag_up", cond=0x1)
    a.add_imm(0, 7, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_bag_up")
    a.cmp_imm(4, 6)
    a.b("hbi_bag_a", cond=0x1)
    a.add_reg(0, 7, 9)
    a.sub_imm(0, 0, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_bag_a")
    a.cmp_imm(4, 0)
    a.b("hbi_ret", cond=0x1)
    a.add_reg(0, 13, 7)
    a.ldrb_imm(8, 0, 0) # itemId
    a.mov_imm(0, 28)
    a.mul(9, 8, 0)
    a.mov_imm(0, tables_rom_addrs[8])
    a.add_reg(9, 0, 9)

    a.ldrb_imm(0, 5, 5)
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.mov_imm(1, 0x020000B4)
    a.add_reg(10, 1, 0)

    a.ldrb_imm(0, 9, 0)
    a.cmp_imm(0, 1)
    a.b("hbi_bag_cure", cond=0x1)
    a.ldrh_imm(1, 10, 0x08)
    a.ldrh_imm(2, 10, 0x0A)
    a.ldrh_imm(3, 9, 2)
    a.add_reg(1, 1, 3)
    a.cmp_reg(1, 2)
    a.mov_reg(1, 2, cond=0x8)
    a.strh_imm(1, 10, 0x08)
    a.cmp_imm(8, 7)
    a.mov_imm(1, 0, cond=0x0)
    a.strb_imm(1, 10, 0x06, cond=0x0)
    a.b("hbi_bag_consume")

    a.label("hbi_bag_cure")
    a.cmp_imm(0, 2)
    a.b("hbi_bag_revive", cond=0x1)
    a.mov_imm(1, 0)
    a.strb_imm(1, 10, 0x06)
    a.b("hbi_bag_consume")

    a.label("hbi_bag_revive")
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(1, 0, 0x0B0)
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
    a.ldrh_imm(0, 2, 0x0A)
    a.mov_reg(0, 0, shift_imm=1, shift_type=1)
    a.strh_imm(0, 2, 0x08)

    a.label("hbi_bag_consume")
    a.mov_reg(0, 8)
    a.mvn_imm(1, 0)
    a.bl("bag_add")
    a.ldrh_imm(3, 10, 0x08)
    a.and_imm(3, 3, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.mov_imm(0, 5)
    a.mov_reg(1, 8)
    a.ldrh_imm(2, 9, 2)
    a.bl("log_battle_event")
    # Log: "Used ${it.name}! ${foeMsg}"
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Used "))
    a.bl("fmt_str")
    a.mov_reg(0, 8)
    a.mov_imm(1, 255)
    a.bl("fmt_it_name_n")
    a.mov_imm(0, ui_off("! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.add_imm(0, 0, 0x10)
    a.add_reg(0, 5, 0)
    a.mov_reg(1, 10)
    a.bl("do_foe_attack")
    a.mov_imm(0, 6)
    a.strb_imm(0, 5, 8)
    a.b("hbi_ret")

    # Phase 5: PARTY
    a.label("hbi_chk_party")
    a.cmp_imm(6, 5)
    a.b("hbi_ret", cond=0x1)
    a.cmp_imm(4, 1)
    a.b("hbi_to_main", cond=0x0)
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(9, 0, 0x0B0)
    a.cmp_imm(4, 7)
    a.b("hbi_party_up", cond=0x1)
    a.add_imm(0, 7, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_party_up")
    a.cmp_imm(4, 6)
    a.b("hbi_party_a", cond=0x1)
    a.add_reg(0, 7, 9)
    a.sub_imm(0, 0, 1)
    a.mov_reg(1, 9)
    a.bl("udiv32")
    a.strb_imm(1, 5, 9)
    a.b("hbi_ret")
    a.label("hbi_party_a")
    a.cmp_imm(4, 0)
    a.b("hbi_ret", cond=0x1)
    a.cmp_reg(7, 9)
    a.b("hbi_ret", cond=0x2)
    a.ldrb_imm(0, 5, 5)
    a.cmp_reg(7, 0)
    a.b("hbi_ret", cond=0x0)
    a.mov_imm(1, 48)
    a.mul(2, 7, 1)
    a.mov_imm(3, 0x020000B4)
    a.add_reg(8, 3, 2)
    a.ldrh_imm(0, 8, 0x08)
    a.cmp_imm(0, 0)
    a.b("hbi_ret", cond=0x0)
    a.strb_imm(7, 5, 5)
    a.and_imm(3, 0, 0xFF)
    a.mov_reg(3, 3, shift_imm=8, shift_type=0)
    a.mov_imm(0, 6)
    a.mov_reg(1, 7)
    a.mov_imm(2, 0)
    a.bl("log_battle_event")
    # Log: "Go, ${target.nickname}! ${foeMsg}"
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Go, "))
    a.bl("fmt_str")
    a.ldrb_imm(0, 8, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off("! "))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.ldrb_imm(0, 5, 4)
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.add_imm(0, 0, 0x10)
    a.add_reg(0, 5, 0)
    a.mov_reg(1, 8)
    a.bl("do_foe_attack")
    a.mov_imm(0, 6)
    a.strb_imm(0, 5, 8)
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

    # Master 256-color BGR555 Palette:
    # Indices 0..15: BG1 4bpp Map Tile Palette (swapped dynamically for day / night / dark_day / dark_night)
    # Indices 16..126: BG0 & OBJ 8bpp UI, Fonts, Species, and Character Colors (never altered by night tint!)
    # Index 127: Pure Black 0x0000 (for dark-cave 56x56 clearRect cutout on BG0)
    tile_pal_hex = ['#101420', '#181820', '#58a848', '#408830', '#78c860', '#d8b880', '#b89860', '#4888c8', '#70b0e8', '#c85838', '#e8e0d0', '#885030', '#386830', '#f0c040', '#a0a8b0', '#f8f8f0']
    master_cols = [c.lower() for c in tile_pal_hex] # 0..15
    ui_and_spr_hex = [
        "#101420", "#181820", "#58a848", "#408830", "#78c860", "#d8b880", "#b89860", "#4888c8",
        "#70b0e8", "#c85838", "#e8e0d0", "#885030", "#386830", "#f0c040", "#a0a8b0", "#f8f8f0",
        "#182030", "#f8e888", "#a8dadc", "#98d830", "#c0c8d0",
        "#708090", "#506070", "#e63946", "#52b788", "#4cc9f0", "#e8a850", "#60c8f8",
        "#1a1e34", "#141c2c", "#283854", "#182234", "#304060", "#1a2438", "#243448", "#385068", "#404858", "#101824", "#101424"
    ]
    col_idx_of = {}
    for c in ui_and_spr_hex:
        cl = c.lower()
        if cl not in col_idx_of:
            col_idx_of[cl] = len(master_cols)
            master_cols.append(cl)
    for sp in ext_dict["beatsts_py"]:
        for c in sp["palette"]:
            if c and c.lower() not in col_idx_of:
                col_idx_of[c.lower()] = len(master_cols)
                master_cols.append(c.lower())
    for k in ext_dict["char_sprites"]:
        for d in ("down", "up", "left", "right"):
            for f in range(3):
                for c in ext_dict["char_grids_py"][k][d][f]:
                    if c and c.lower() not in col_idx_of:
                        col_idx_of[c.lower()] = len(master_cols)
                        master_cols.append(c.lower())

    master_pal_bytes = bytearray(512)
    for idx, c in enumerate(master_cols[:124]):
        struct.pack_into("<H", master_pal_bytes, idx * 2, to_bgr555(c))
    # Indices 124..126: dedicated map-entry banner colors (#141c2c, #f0c040, #f8e888) faded by transitionTimer
    struct.pack_into("<H", master_pal_bytes, 124 * 2, to_bgr555("#141c2c"))
    struct.pack_into("<H", master_pal_bytes, 125 * 2, to_bgr555("#f0c040"))
    struct.pack_into("<H", master_pal_bytes, 126 * 2, to_bgr555("#f8e888"))
    # Index 127 = 0x0000 (pure black for map.dark clearRect cutout, also faded by transitionTimer)
    struct.pack_into("<H", master_pal_bytes, 127 * 2, 0x0000)

    # 15 fade levels (0..14) x 2 OBJ dark modes (0=normal, 1=dark) -> 30 x 256B (128 halfwords each)
    obj_fade_modes_555 = [[4162, 4195, 9899, 6696, 13103, 17147, 12919, 26153, 30414, 7545, 27549, 6481, 6567, 8990, 23220, 31743, 4162, 4195, 9899, 6696, 13103, 17147, 12919, 26153, 30414, 7545, 27549, 6481, 6567, 8990, 23220, 31743, 6275, 18367, 28533, 7027, 27448, 18958, 14730, 8444, 18122, 31529, 10941, 32556, 6243, 5218, 10469, 6275, 12550, 7299, 9412, 13639, 11560, 4194, 4162, 4535, 19327, 14142, 7450, 9962, 22111, 9653, 4333, 17083, 16172, 9733, 24534, 3659, 17402, 24127, 16697, 30559, 29109, 19661, 32475, 3608, 21471, 12903, 7523, 21393, 6430, 3189, 10879, 32620, 25157, 32762, 32766, 29559, 32767, 26186, 17765, 32629, 23423, 19944, 9637, 29043, 22111, 20959, 9585, 5659, 4913, 5820, 8389, 9415, 9385], [2081, 2081, 4291, 3235, 5348, 6376, 5319, 8355, 9444, 3175, 8456, 3173, 3202, 3305, 7366, 10537, 2081, 2081, 4291, 3235, 5348, 6376, 5319, 8355, 9444, 3175, 8456, 3173, 3202, 3305, 7366, 10537, 3137, 6441, 9478, 3334, 8423, 6308, 5251, 4168, 6371, 10467, 4296, 10468, 3105, 3105, 4162, 3137, 5218, 3137, 4162, 5218, 4195, 2081, 2081, 2183, 6409, 5353, 3176, 4323, 7337, 4230, 2116, 6344, 5348, 4258, 8486, 2211, 6440, 8361, 6247, 9481, 9350, 6212, 10472, 2215, 7465, 5314, 3169, 7429, 3177, 2086, 4297, 10500, 8354, 10536, 10537, 9479, 10537, 8355, 6242, 10502, 7433, 7331, 4226, 9350, 7337, 7305, 4229, 3240, 2277, 3304, 3138, 4162, 4163], [3137, 3138, 8842, 5639, 12046, 16090, 11862, 25096, 29357, 6488, 26492, 5424, 5510, 7933, 22163, 30686, 3137, 3138, 8842, 5639, 12046, 16090, 11862, 25096, 29357, 6488, 26492, 5424, 5510, 7933, 22163, 30686, 5218, 17310, 28500, 5970, 26391, 17901, 13673, 8444, 17098, 30473, 9884, 31499, 6243, 5218, 10436, 6274, 11493, 6275, 8388, 12582, 10503, 4161, 4161, 3478, 18270, 13085, 6393, 8905, 21054, 8596, 3276, 16026, 15115, 8676, 23477, 2602, 16345, 23070, 15640, 29502, 28052, 18604, 31418, 2551, 20414, 11846, 6466, 20336, 5373, 2132, 9822, 31563, 24100, 31705, 31709, 28502, 31710, 25129, 16708, 31572, 22366, 19944, 9637, 29043, 21055, 20927, 9585, 5658, 4881, 5820, 7332, 8358, 8328], [2081, 2081, 4291, 3234, 4324, 6376, 4295, 8355, 9412, 3175, 8456, 3173, 3202, 3305, 7366, 9513, 2081, 2081, 4291, 3234, 4324, 6376, 4295, 8355, 9412, 3175, 8456, 3173, 3202, 3305, 7366, 9513, 3105, 6409, 9478, 3333, 8423, 6308, 5251, 3144, 6371, 9443, 4296, 10468, 3105, 3105, 4162, 3105, 4194, 3137, 4161, 5218, 4194, 2081, 2081, 2183, 6409, 5353, 3175, 4323, 7337, 4230, 2116, 6344, 5348, 4258, 7462, 2211, 6439, 7337, 6247, 9481, 9350, 6212, 10440, 2215, 7465, 4290, 3169, 7429, 3177, 2086, 4297, 10500, 8354, 10535, 10537, 9479, 10537, 8355, 6242, 10502, 7433, 7331, 4226, 9350, 7337, 7305, 4197, 3240, 2277, 3272, 3138, 4162, 4163], [3137, 3138, 8810, 5607, 12013, 16057, 11829, 24040, 27277, 6487, 25402, 5423, 5510, 7899, 21106, 28572, 3137, 3138, 8810, 5607, 12013, 16057, 11829, 24040, 27277, 6487, 25402, 5423, 5510, 7899, 21106, 28572, 5218, 16220, 26419, 5937, 25334, 16845, 13673, 8410, 16041, 28392, 9850, 29419, 6243, 5218, 9412, 6274, 11493, 6275, 8388, 12582, 10503, 4161, 4161, 3477, 17212, 13051, 6392, 8873, 19996, 8595, 3276, 15993, 15083, 8644, 22388, 3594, 16280, 22012, 15639, 27420, 27027, 17580, 29337, 3542, 19324, 11814, 6466, 19247, 5371, 3155, 9788, 29483, 23044, 29592, 29595, 27445, 29596, 24073, 15684, 29491, 21308, 18888, 9605, 26961, 19997, 19901, 9552, 5625, 4848, 5786, 7332, 8358, 8328], [2081, 2081, 4291, 3234, 4324, 5319, 4262, 8355, 9412, 3175, 8456, 3173, 3202, 3304, 7366, 9480, 2081, 2081, 4291, 3234, 4324, 5319, 4262, 8355, 9412, 3175, 8456, 3173, 3202, 3304, 7366, 9480, 3105, 6408, 8422, 3301, 8423, 6308, 5251, 3144, 6339, 9443, 4296, 9443, 3105, 3105, 4162, 3105, 4194, 3137, 4161, 5218, 4194, 2081, 2081, 2182, 6376, 5352, 3175, 4291, 7336, 4230, 2116, 5319, 5347, 4258, 7430, 2211, 5383, 7336, 5223, 9448, 9350, 6212, 9415, 2215, 6408, 4258, 3169, 6405, 3176, 2086, 4264, 9443, 7330, 9479, 9480, 9446, 9480, 8355, 6242, 9446, 7400, 6275, 4226, 9317, 7336, 7304, 4197, 3239, 2277, 3272, 3138, 4162, 4163], [3137, 3138, 8777, 5574, 10924, 14967, 10771, 21959, 26220, 6453, 23320, 5390, 5478, 7833, 20049, 27482, 3137, 3138, 8777, 5574, 10924, 14967, 10771, 21959, 26220, 6453, 23320, 5390, 5478, 7833, 20049, 27482, 5218, 15162, 24306, 5872, 23220, 15788, 12616, 7384, 14952, 27304, 8792, 27306, 5218, 5218, 9412, 5218, 10469, 6274, 8355, 11526, 9446, 4161, 4161, 3443, 16122, 11961, 6390, 8808, 18938, 8562, 3275, 14935, 13994, 8612, 21298, 2537, 15190, 20954, 14581, 26330, 24946, 16555, 27255, 2484, 18234, 10758, 6434, 18190, 5369, 2130, 8730, 27370, 20964, 27478, 27481, 25331, 27482, 21992, 14628, 27378, 20218, 17831, 8548, 24912, 18939, 18843, 8495, 4567, 4782, 5720, 7332, 8358, 8327], [2081, 2081, 3267, 3234, 4292, 5319, 4262, 7330, 8388, 3174, 7399, 3172, 3202, 3271, 7365, 8456, 2081, 2081, 3267, 3234, 4292, 5319, 4262, 7330, 8388, 3174, 7399, 3172, 3202, 3271, 7365, 8456, 3105, 5352, 8421, 3301, 7366, 6276, 5219, 3143, 5315, 8387, 4295, 9411, 3105, 3105, 4161, 3105, 4162, 3137, 3137, 4194, 4194, 2081, 2081, 2182, 6376, 4295, 3142, 3267, 6312, 3205, 2115, 5319, 5315, 3201, 7430, 2211, 5382, 7336, 5222, 8424, 8325, 6211, 9415, 2182, 6408, 4258, 3169, 6372, 3143, 2085, 4264, 9443, 7329, 9478, 9479, 8422, 9480, 7331, 5217, 9445, 7400, 6274, 4226, 8293, 6312, 6280, 4196, 3207, 2244, 3271, 3137, 3138, 3138], [3137, 3138, 7688, 5542, 9868, 13909, 9714, 20903, 24107, 6451, 22231, 5389, 5445, 6775, 17936, 25368, 3137, 3138, 7688, 5542, 9868, 13909, 9714, 20903, 24107, 6451, 22231, 5389, 5445, 6775, 17936, 25368, 5218, 14072, 23216, 5807, 22163, 14763, 11560, 7350, 13896, 25223, 8727, 25225, 5218, 4194, 8356, 5218, 9412, 6242, 7331, 10501, 9446, 4161, 4161, 3410, 15032, 10903, 6356, 7752, 17880, 7504, 3242, 13845, 12937, 7588, 19217, 2504, 14100, 18872, 13555, 24216, 22864, 15530, 25141, 2483, 17176, 9701, 6434, 17101, 5335, 2128, 8696, 25257, 19908, 25364, 25367, 23218, 25368, 20936, 13604, 25264, 18104, 15751, 8516, 23855, 17881, 16761, 7470, 4533, 4749, 5686, 6308, 7333, 7303], [2081, 2081, 3235, 3202, 4292, 5318, 4261, 7298, 8355, 3174, 7399, 3172, 3170, 3271, 6309, 8423, 2081, 2081, 3235, 3202, 4292, 5318, 4261, 7298, 8355, 3174, 7399, 3172, 3170, 3271, 6309, 8423, 3105, 5351, 7397, 3268, 7366, 5251, 4195, 3143, 5315, 8386, 3239, 8387, 3105, 2081, 4161, 3105, 4162, 3137, 3137, 4194, 4194, 2081, 2081, 2149, 5319, 4295, 3142, 3267, 6311, 3173, 2115, 5286, 5315, 3201, 6373, 2211, 5350, 6279, 5222, 8391, 7269, 5187, 8358, 2182, 6375, 4258, 3169, 6372, 3143, 2085, 3239, 8387, 7329, 8422, 8423, 7365, 8423, 7331, 5217, 8389, 6343, 6274, 3170, 8293, 6311, 6279, 3172, 2182, 2244, 2215, 3137, 3138, 3138], [3137, 3138, 7656, 5510, 9803, 12819, 9680, 18822, 22026, 5394, 20117, 5356, 5413, 6710, 16878, 23254, 3137, 3138, 7656, 5510, 9803, 12819, 9680, 18822, 22026, 5394, 20117, 5356, 5413, 6710, 16878, 23254, 5218, 14006, 21135, 5742, 20049, 13674, 10535, 7349, 13831, 23111, 7669, 24137, 5218, 4162, 8355, 5218, 9412, 5218, 7331, 10469, 8390, 4161, 4161, 3376, 13942, 10838, 5331, 7687, 15798, 7471, 3241, 12787, 11849, 7523, 18128, 2472, 13011, 17814, 12498, 22134, 20783, 14473, 24083, 2417, 16086, 9669, 5378, 16012, 5334, 2127, 7638, 24169, 18851, 24275, 24278, 21104, 24278, 18855, 13571, 24175, 17014, 14694, 7460, 21774, 15799, 15703, 7437, 4499, 4684, 4629, 6275, 7301, 7270], [2081, 2081, 3235, 3202, 4291, 5286, 4229, 6274, 7331, 3173, 7366, 3140, 3170, 3238, 6308, 7399, 2081, 2081, 3235, 3202, 4291, 5286, 4229, 6274, 7331, 3173, 7366, 3140, 3170, 3238, 6308, 7399, 3105, 5319, 7365, 3268, 7365, 5251, 4194, 3142, 5282, 7362, 3238, 8387, 3105, 3105, 4161, 3105, 4162, 3105, 3137, 4162, 4162, 2081, 2081, 2149, 5319, 4294, 3142, 3234, 6279, 3173, 2115, 5286, 4291, 3201, 6373, 2179, 5350, 6279, 5189, 7367, 7269, 5187, 8358, 2181, 5351, 4226, 3169, 5316, 3142, 2085, 3207, 8387, 6273, 8422, 8422, 7365, 8423, 6274, 5217, 8389, 6343, 5250, 3170, 7268, 6279, 6247, 3172, 3206, 2244, 3238, 3137, 3138, 3138], [3137, 3138, 6599, 4453, 8714, 11762, 8591, 17766, 19913, 5360, 18003, 4331, 4388, 6676, 15821, 21140, 3137, 3138, 6599, 4453, 8714, 11762, 8591, 17766, 19913, 5360, 18003, 4331, 4388, 6676, 15821, 21140, 4194, 12916, 19022, 4684, 17936, 12649, 10502, 6323, 12775, 20998, 7635, 22024, 5186, 4162, 7331, 5218, 8356, 5218, 6275, 9444, 8389, 3137, 3137, 3375, 12884, 9748, 5297, 6630, 14740, 6446, 3240, 11730, 10760, 6499, 16014, 2439, 11921, 15732, 11472, 20020, 19758, 13448, 21970, 2416, 14996, 8580, 5346, 14923, 4276, 2126, 7572, 22088, 16771, 22161, 22164, 20047, 22164, 17798, 12515, 22094, 15956, 13638, 7460, 19725, 14741, 14645, 7403, 4466, 3595, 4563, 6275, 6276, 6246], [2081, 2081, 3202, 3202, 4259, 4261, 4229, 6274, 7331, 3173, 6342, 3139, 3170, 3238, 5252, 7366, 2081, 2081, 3202, 3202, 4259, 4261, 4229, 6274, 7331, 3173, 6342, 3139, 3170, 3238, 5252, 7366, 3105, 5318, 6340, 3236, 6309, 5251, 4194, 3142, 5282, 7330, 3206, 7331, 3105, 2081, 3137, 3105, 4161, 3105, 3137, 4162, 3138, 2081, 2081, 2149, 5286, 4262, 3141, 3234, 5254, 3172, 2115, 4229, 4259, 3201, 6340, 2178, 4293, 6278, 4165, 7334, 7268, 5187, 7333, 2181, 5318, 4226, 3169, 5315, 3142, 2084, 3206, 7331, 6273, 7365, 7366, 7333, 7366, 6274, 5217, 7332, 5286, 5218, 3169, 7268, 5254, 5222, 3172, 2181, 2211, 2214, 3137, 3138, 3106], [3137, 3138, 6566, 4421, 8681, 10704, 8558, 15685, 18856, 5359, 16945, 4298, 4356, 5586, 13740, 19026, 3137, 3138, 6566, 4421, 8681, 10704, 8558, 15685, 18856, 5359, 16945, 4298, 4356, 5586, 13740, 19026, 4162, 11826, 17932, 4619, 16878, 11592, 9446, 6289, 11718, 18918, 6577, 19943, 4162, 4161, 7299, 4194, 8356, 5218, 6275, 8388, 7333, 3137, 3137, 3342, 11794, 8690, 5295, 6598, 13682, 6412, 3208, 10672, 9703, 6467, 14925, 2406, 10831, 14674, 10415, 18930, 17676, 12424, 19888, 2382, 12882, 8548, 5346, 12842, 4274, 2124, 6514, 19975, 15715, 20047, 20050, 17934, 20050, 15718, 11491, 19980, 13842, 12581, 6403, 17643, 13683, 13587, 6378, 4432, 3562, 4529, 5251, 6276, 6245], [2081, 2081, 3202, 2146, 3235, 4229, 3204, 6242, 6275, 3141, 6309, 2115, 2146, 3237, 5252, 6342, 2081, 2081, 3202, 2146, 3235, 4229, 3204, 6242, 6275, 3141, 6309, 2115, 2146, 3237, 5252, 6342, 2081, 4262, 6308, 2212, 6308, 4195, 4194, 3141, 4226, 6306, 3205, 7330, 2081, 2081, 3137, 2081, 3137, 3105, 3137, 4162, 3138, 2081, 2081, 2148, 4262, 4261, 3141, 3202, 5254, 3172, 2115, 4229, 4258, 3169, 5316, 2178, 4293, 5222, 4165, 6310, 6244, 5187, 7301, 2148, 5318, 3202, 3137, 5283, 2117, 2084, 3206, 7330, 5249, 7365, 7365, 6308, 7366, 6274, 4161, 7332, 5286, 5218, 3169, 6244, 5254, 5222, 3139, 2149, 2211, 2181, 3137, 3138, 3106], [3137, 3138, 5478, 4388, 7592, 9614, 7500, 14629, 16775, 4301, 14831, 4265, 4324, 5552, 12651, 16912, 3137, 3138, 5478, 4388, 7592, 9614, 7500, 14629, 16775, 4301, 14831, 4265, 4324, 5552, 12651, 16912, 4162, 10736, 15851, 4554, 14765, 10535, 8421, 5263, 10629, 16805, 6511, 17830, 4162, 4161, 6275, 4162, 7299, 4194, 5250, 8356, 7332, 3137, 3137, 3308, 10704, 8624, 4238, 5509, 12624, 5355, 3207, 9582, 9638, 5411, 13836, 2374, 9742, 13616, 9389, 16848, 15595, 11367, 17806, 2349, 11792, 7492, 4290, 11753, 4240, 2123, 6480, 17862, 13635, 17934, 17936, 15820, 17936, 14661, 10435, 17867, 12752, 11525, 6371, 16586, 12625, 12561, 6345, 4398, 3497, 4495, 5219, 5220, 5221], [2081, 2081, 3202, 2146, 3203, 4228, 3172, 5218, 6275, 3140, 5285, 2115, 2145, 3205, 5251, 6309, 2081, 2081, 3202, 2146, 3203, 4228, 3172, 5218, 6275, 3140, 5285, 2115, 2145, 3205, 5251, 6309, 2081, 4261, 6308, 2211, 5252, 4195, 4162, 3141, 4226, 6274, 3205, 6274, 3105, 2081, 3137, 3105, 3137, 3105, 3137, 3137, 3138, 2081, 2081, 2148, 4261, 3205, 3140, 3202, 5221, 3172, 2114, 4228, 4226, 3169, 5284, 2146, 4260, 5221, 4164, 6309, 6244, 4162, 6276, 2148, 5285, 3169, 3137, 5283, 2117, 2084, 3173, 6306, 5217, 6308, 6309, 6308, 6309, 5218, 4161, 6308, 5285, 4194, 3169, 6211, 5221, 5221, 3139, 2149, 2179, 2181, 3137, 3137, 3106], [3137, 3137, 5445, 4356, 6535, 8556, 6443, 12548, 14663, 4268, 13741, 4264, 4291, 5486, 11593, 15854, 3137, 3137, 5445, 4356, 6535, 8556, 6443, 12548, 14663, 4268, 13741, 4264, 4291, 5486, 11593, 15854, 4161, 9678, 13738, 4521, 13707, 9479, 7365, 5261, 9573, 15748, 5453, 15750, 4162, 3137, 6274, 4161, 6275, 4162, 5218, 7331, 6276, 3137, 3137, 3275, 9646, 7566, 4236, 5477, 10542, 5322, 3206, 8524, 8582, 5378, 11722, 2341, 8684, 11534, 8332, 14734, 14538, 10342, 15692, 2315, 10702, 6435, 4257, 10664, 4238, 2122, 5422, 15782, 12578, 15852, 15854, 14763, 15854, 12581, 9378, 15786, 11694, 10468, 5315, 14537, 10543, 10479, 5320, 3341, 3464, 4429, 5218, 5219, 5220], [2081, 2081, 3170, 2145, 3202, 4228, 3171, 5218, 5250, 2116, 5252, 2115, 2113, 3204, 4195, 5284, 2081, 2081, 3170, 2145, 3202, 4228, 3171, 5218, 5250, 2116, 5252, 2115, 2113, 3204, 4195, 5284, 2081, 4228, 5251, 2179, 5252, 4194, 3138, 3140, 4226, 5250, 3172, 6274, 2081, 2081, 3137, 2081, 3137, 2081, 3137, 3137, 3137, 2081, 2081, 2115, 4228, 3204, 2116, 3202, 4196, 3139, 2114, 4196, 4226, 3169, 5283, 2146, 4260, 5220, 4164, 5252, 5187, 4162, 6276, 2148, 4260, 3169, 2113, 4227, 2116, 2083, 3172, 6274, 5217, 6308, 6308, 5251, 6308, 5218, 4161, 6275, 4228, 4194, 3137, 5187, 4197, 4197, 3139, 2148, 2179, 2180, 3137, 3137, 3106], [3105, 3137, 5413, 3299, 6470, 7467, 6409, 11492, 12582, 4266, 11628, 3207, 3235, 4428, 10536, 13708, 3105, 3137, 5413, 3299, 6470, 7467, 6409, 11492, 12582, 4266, 11628, 3207, 3235, 4428, 10536, 13708, 3137, 8588, 12648, 3432, 11594, 8422, 6308, 4203, 8484, 13636, 5420, 13637, 4162, 3137, 5218, 4161, 6275, 4162, 5218, 6275, 5251, 3137, 3105, 3241, 8556, 6476, 4234, 5412, 9452, 5288, 3173, 7467, 7493, 5346, 10633, 2277, 7562, 10476, 7306, 12652, 12456, 8293, 13611, 2282, 9612, 6403, 4257, 9575, 3212, 2120, 5388, 13669, 10466, 13706, 13708, 12649, 13708, 11492, 8354, 13672, 10604, 9412, 5314, 12456, 9453, 9421, 5287, 3307, 3399, 3371, 4194, 5219, 5188], [2081, 2081, 3170, 2145, 3170, 3171, 3171, 4194, 5218, 2115, 4228, 2114, 2113, 3172, 4195, 5252, 2081, 2081, 3170, 2145, 3170, 3171, 3171, 4194, 5218, 2115, 4228, 2114, 2113, 3172, 4195, 5252, 2081, 3204, 5251, 2179, 4195, 4162, 3138, 3108, 3170, 5218, 3172, 5218, 2081, 2081, 3105, 2081, 3137, 2081, 3105, 3137, 3137, 2081, 2081, 2115, 4228, 3172, 2115, 3170, 4196, 3139, 2082, 3171, 3170, 3137, 4227, 2146, 3203, 4196, 3139, 5252, 5187, 4130, 5219, 2115, 4228, 3169, 2113, 4226, 2116, 2083, 3172, 5250, 4193, 5251, 5252, 5251, 5252, 4194, 3137, 5251, 4228, 4161, 3137, 5187, 4196, 4164, 3138, 2116, 2146, 2148, 3105, 3105, 3106], [3105, 3105, 4324, 3267, 5413, 6409, 5352, 9411, 11525, 4232, 10570, 3206, 3235, 4362, 8423, 11626, 3105, 3105, 4324, 3267, 5413, 6409, 5352, 9411, 11525, 4232, 10570, 3206, 3235, 4362, 8423, 11626, 3137, 7498, 10535, 3367, 10536, 7365, 6276, 4202, 7428, 11555, 4330, 11556, 3137, 3137, 5218, 3137, 5218, 4161, 4194, 5251, 5219, 3105, 3105, 3240, 7466, 5418, 4201, 4356, 8394, 4263, 3173, 6377, 6436, 4290, 9544, 2244, 6505, 9418, 6248, 11562, 10407, 7237, 11529, 2248, 8522, 5347, 4225, 8518, 3178, 2087, 4330, 11556, 9410, 11625, 11626, 10536, 11626, 9412, 7298, 11559, 8490, 8355, 4258, 11399, 8395, 8363, 4230, 3273, 3366, 3338, 4162, 4163, 4163], [2081, 2081, 3170, 2113, 3170, 3171, 3139, 4161, 4194, 2115, 4195, 2114, 2113, 3171, 4194, 4227, 2081, 2081, 3170, 2113, 3170, 3171, 3139, 4161, 4194, 2115, 4195, 2114, 2113, 3171, 4194, 4227, 2081, 3171, 4195, 2146, 4195, 3138, 3138, 3107, 3170, 4193, 3171, 5218, 2081, 2081, 3105, 2081, 3137, 2081, 3105, 3137, 3137, 2081, 2081, 2115, 3171, 3171, 2115, 3170, 4163, 3139, 2082, 3171, 3170, 3137, 4195, 2114, 3203, 4163, 3139, 4195, 4163, 3106, 5219, 2115, 4195, 3137, 2113, 4194, 2115, 2083, 3139, 5218, 4161, 5251, 5251, 4195, 5251, 4162, 3137, 5219, 4195, 4161, 3137, 4162, 4163, 4163, 3138, 2115, 2146, 2147, 3105, 3105, 3105], [2081, 2081, 4291, 3234, 4324, 6375, 4294, 8355, 9412, 3175, 8456, 3173, 3202, 3304, 7366, 9512, 2081, 2081, 4291, 3234, 4324, 6375, 4294, 8355, 9412, 3175, 8456, 3173, 3202, 3304, 7366, 9512, 3137, 6408, 8454, 3333, 8423, 6308, 5251, 4168, 6371, 9443, 4296, 9443, 3137, 3137, 4162, 3137, 4194, 3137, 4162, 5218, 4194, 3105, 3105, 2182, 6408, 5352, 3175, 4323, 7336, 4230, 2116, 6343, 5347, 4258, 7430, 2211, 6439, 7336, 6247, 9448, 9350, 6212, 9415, 2215, 7432, 4290, 3169, 7429, 3176, 2086, 4296, 9475, 8354, 9511, 9512, 9478, 9512, 8355, 6242, 9478, 7432, 6307, 4226, 9349, 7337, 7305, 4229, 3239, 3301, 3272, 3138, 4162, 4163], [2081, 2081, 2113, 2113, 3170, 3139, 3138, 4161, 4162, 2114, 4195, 2114, 2113, 2147, 3138, 4195, 2081, 2081, 2113, 2113, 3170, 3139, 3138, 4161, 4162, 2114, 4195, 2114, 2113, 2147, 3138, 4195, 2081, 3171, 4194, 2146, 4194, 3138, 3137, 2083, 3137, 4193, 3139, 4193, 2081, 2081, 3105, 2081, 3105, 2081, 2081, 3137, 3105, 2081, 2081, 2114, 3171, 3171, 2082, 2113, 3139, 2114, 2082, 3139, 3169, 2113, 3170, 2113, 3170, 3139, 3106, 4195, 4162, 3106, 4163, 2114, 3171, 3137, 2113, 3170, 2083, 2082, 3139, 4193, 4161, 4194, 4195, 4194, 4195, 4161, 3137, 4194, 3171, 3137, 3137, 4162, 3139, 3139, 2114, 2115, 2146, 2115, 2081, 2081, 2081], [2081, 2081, 3235, 3202, 4291, 5286, 4229, 6274, 7331, 3173, 6342, 3172, 3170, 3238, 6308, 7398, 2081, 2081, 3235, 3202, 4291, 5286, 4229, 6274, 7331, 3173, 6342, 3172, 3170, 3238, 6308, 7398, 3137, 5318, 7365, 3268, 6341, 5251, 4194, 3142, 5282, 7362, 3238, 7363, 3105, 3105, 4161, 3137, 4162, 3137, 3137, 4194, 4162, 2081, 2081, 2149, 5318, 4294, 3141, 3234, 6278, 3173, 2115, 5286, 4291, 3201, 6341, 2179, 5349, 6278, 5189, 7366, 7269, 5187, 7334, 2181, 5318, 4226, 3169, 5316, 3142, 2085, 3206, 7363, 6273, 7397, 7398, 7365, 7398, 6274, 5217, 7365, 6342, 5250, 3170, 7268, 6279, 5223, 3172, 3206, 2244, 3238, 3137, 3138, 3138], [2081, 2081, 2113, 2113, 2113, 3138, 2114, 3137, 3137, 2082, 3138, 2082, 2113, 2114, 3138, 3170, 2081, 2081, 2113, 2113, 2113, 3138, 2114, 3137, 3137, 2082, 3138, 2082, 2113, 2114, 3138, 3170, 2081, 3138, 3138, 2114, 3138, 3137, 3137, 2082, 3137, 3137, 2114, 3137, 2081, 2081, 2081, 2081, 2081, 2081, 2081, 3105, 2081, 2081, 2081, 2114, 3138, 3138, 2082, 2113, 3138, 2114, 2081, 3138, 3137, 2113, 3170, 2113, 3170, 3138, 3106, 3138, 3138, 3105, 3138, 2114, 3170, 2113, 2081, 3138, 2082, 2082, 2114, 3137, 3137, 3170, 3170, 3138, 3170, 3137, 3105, 3138, 3138, 3137, 2113, 3138, 3138, 3138, 2114, 2114, 2114, 2114, 2081, 2081, 2081], [2081, 2081, 3202, 3170, 3203, 4228, 3172, 5218, 5250, 3140, 5252, 3139, 3170, 3204, 5251, 6309, 2081, 2081, 3202, 3170, 3203, 4228, 3172, 5218, 5250, 3140, 5252, 3139, 3170, 3204, 5251, 6309, 3105, 4261, 5251, 3203, 5252, 4194, 4162, 3140, 4226, 6274, 3204, 6274, 3105, 2081, 3137, 3105, 3137, 3105, 3137, 3138, 3138, 2081, 2081, 2148, 4229, 3204, 3140, 3202, 4197, 3171, 2114, 4228, 4226, 3169, 5283, 2146, 4260, 5221, 4164, 5253, 5219, 4162, 6276, 2148, 4261, 3170, 3137, 4227, 3140, 2083, 3173, 6274, 5217, 6308, 6308, 5252, 6309, 5218, 4161, 6275, 5253, 4194, 3169, 5187, 4197, 4197, 3139, 2148, 2179, 2180, 3137, 3138, 3138], [2081, 2081, 2113, 2113, 2113, 3138, 2114, 3137, 3137, 2082, 3138, 2081, 2081, 2114, 3137, 3138, 2081, 2081, 2113, 2113, 2113, 3138, 2114, 3137, 3137, 2082, 3138, 2081, 2081, 2114, 3137, 3138, 2081, 3138, 3137, 2113, 3138, 3137, 2081, 2082, 3137, 3137, 2114, 3137, 2081, 2081, 2081, 2081, 2081, 2081, 2081, 2081, 2081, 2081, 2081, 2082, 3138, 2114, 2082, 2113, 3138, 2081, 2081, 3138, 2113, 2113, 3137, 2113, 3138, 3138, 3106, 3138, 3105, 3105, 3138, 2114, 3138, 2113, 2081, 3137, 2082, 2081, 2114, 3137, 3137, 3138, 3138, 3138, 3138, 3137, 3105, 3137, 3138, 3137, 2081, 3105, 3138, 3106, 2081, 2114, 2113, 2114, 2081, 2081, 2081]]
    dark_obj_pal_bytes = bytearray(30 * 256)
    for m_i, arr555 in enumerate(obj_fade_modes_555):
        for c_i, val555 in enumerate(arr555):
            struct.pack_into("<H", dark_obj_pal_bytes, m_i * 256 + c_i * 2, val555)

    # 15 fade levels (0..14) x 4 BG map modes (day, night, dark_day, dark_night) -> 60 x 40B (16 tile + 4 banner/cutout halfwords)
    tile_pal_modes_555 = [[4162, 4195, 9899, 6696, 13103, 17147, 12919, 26153, 30414, 7545, 27549, 6481, 6567, 8990, 23220, 31743, 5218, 8990, 18367, 0], [5186, 5186, 8647, 6533, 10794, 12818, 10671, 18822, 21993, 7441, 20083, 6379, 6437, 7700, 16845, 23220, 5218, 8990, 18367, 0], [2081, 2081, 4291, 3235, 5348, 6376, 5319, 8355, 9444, 3175, 8456, 3173, 3202, 3305, 7366, 10537, 5218, 8990, 18367, 0], [3105, 3105, 3202, 3202, 4259, 5285, 4229, 6274, 7331, 3173, 7366, 3140, 3170, 3238, 6276, 7366, 5218, 8990, 18367, 0], [3137, 3138, 8842, 5639, 12046, 16090, 11862, 25096, 29357, 6488, 26492, 5424, 5510, 7933, 22163, 30686, 5218, 7933, 17310, 0], [4161, 4162, 8647, 6501, 10794, 12786, 10671, 18790, 21993, 6416, 20083, 6379, 6437, 7700, 16845, 22164, 5218, 7933, 17310, 0], [2081, 2081, 4291, 3234, 4324, 6376, 4295, 8355, 9412, 3175, 8456, 3173, 3202, 3305, 7366, 9513, 5218, 7933, 17310, 0], [2081, 2081, 3202, 3202, 4259, 5285, 4229, 6274, 7331, 3173, 6342, 3139, 3170, 3238, 6276, 7366, 5218, 7933, 17310, 0], [3137, 3138, 8810, 5607, 12013, 16057, 11829, 24040, 27277, 6487, 25402, 5423, 5510, 7899, 21106, 28572, 5218, 7899, 16220, 3105], [4161, 4162, 7591, 6501, 9737, 12752, 9614, 17766, 19913, 6383, 18994, 6378, 6404, 7666, 15788, 21107, 5218, 7899, 16220, 3105], [2081, 2081, 4291, 3234, 4324, 5319, 4262, 8355, 9412, 3175, 8456, 3173, 3202, 3304, 7366, 9480, 5218, 7899, 16220, 3105], [3105, 3105, 3202, 3202, 4259, 4261, 4228, 6274, 7299, 3173, 6309, 3139, 3170, 3238, 6276, 7366, 5218, 7899, 16220, 3105], [3137, 3138, 8777, 5574, 10924, 14967, 10771, 21959, 26220, 6453, 23320, 5390, 5478, 7833, 20049, 27482, 5218, 7833, 15162, 2080], [4161, 4162, 7558, 5445, 9705, 11695, 9581, 16709, 18856, 6382, 16912, 5322, 5380, 6609, 14731, 20049, 5218, 7833, 15162, 2080], [2081, 2081, 3267, 3234, 4292, 5319, 4262, 7330, 8388, 3174, 7399, 3172, 3202, 3271, 7365, 8456, 5218, 7833, 15162, 2080], [2081, 2081, 3202, 3170, 4259, 4229, 4228, 6242, 6275, 3140, 6309, 3139, 3169, 3205, 5251, 7365, 5218, 7833, 15162, 2080], [3137, 3138, 7688, 5542, 9868, 13909, 9714, 20903, 24107, 6451, 22231, 5389, 5445, 6775, 17936, 25368, 4194, 6775, 14072, 2081], [4161, 4162, 7526, 5412, 8616, 10670, 8524, 15653, 17800, 6349, 15855, 5321, 5348, 6576, 13675, 17968, 4194, 6775, 14072, 2081], [2081, 2081, 3235, 3202, 4292, 5318, 4261, 7298, 8355, 3174, 7399, 3172, 3170, 3271, 6309, 8423, 4194, 6775, 14072, 2081], [2081, 2081, 3202, 3170, 4227, 4228, 4228, 5218, 6275, 3140, 6309, 3139, 3169, 3205, 5251, 6309, 4194, 6775, 14072, 2081], [3137, 3138, 7656, 5510, 9803, 12819, 9680, 18822, 22026, 5394, 20117, 5356, 5413, 6710, 16878, 23254, 4162, 6710, 14006, 2081], [4161, 4162, 6470, 5412, 8583, 10605, 8523, 14629, 16743, 5324, 14798, 5288, 5348, 6543, 12618, 16879, 4162, 6710, 14006, 2081], [2081, 2081, 3235, 3202, 4291, 5286, 4229, 6274, 7331, 3173, 7366, 3140, 3170, 3238, 6308, 7399, 4162, 6710, 14006, 2081], [2081, 2081, 3170, 3170, 4226, 4228, 4196, 5218, 6274, 3140, 5252, 3139, 3137, 3204, 5219, 6309, 4162, 6710, 14006, 2081], [3137, 3138, 6599, 4453, 8714, 11762, 8591, 17766, 19913, 5360, 18003, 4331, 4388, 6676, 15821, 21140, 4162, 6676, 12916, 2081], [4161, 4162, 6469, 5380, 7527, 9580, 7466, 13572, 14662, 5291, 13741, 5288, 5315, 5485, 11593, 15822, 4162, 6676, 12916, 2081], [2081, 2081, 3202, 3202, 4259, 4261, 4229, 6274, 7331, 3173, 6342, 3139, 3170, 3238, 5252, 7366, 4162, 6676, 12916, 2081], [2081, 2081, 3170, 3169, 3202, 4228, 3171, 5218, 5218, 3139, 5252, 3139, 3137, 3204, 4195, 5252, 4162, 6676, 12916, 2081], [3137, 3138, 6566, 4421, 8681, 10704, 8558, 15685, 18856, 5359, 16945, 4298, 4356, 5586, 13740, 19026, 4161, 5586, 11826, 2081], [3137, 3138, 5413, 4323, 7494, 8523, 7433, 12516, 13606, 5290, 12652, 4263, 4291, 5452, 10536, 13740, 4161, 5586, 11826, 2081], [2081, 2081, 3202, 2146, 3235, 4229, 3204, 6242, 6275, 3141, 6309, 2115, 2146, 3237, 5252, 6342, 4161, 5586, 11826, 2081], [2081, 2081, 3170, 2145, 3170, 4195, 3171, 5217, 5218, 3139, 5252, 2114, 2113, 3172, 4195, 5252, 4161, 5586, 11826, 2081], [3137, 3138, 5478, 4388, 7592, 9614, 7500, 14629, 16775, 4301, 14831, 4265, 4324, 5552, 12651, 16912, 4161, 5552, 10736, 2081], [3137, 3137, 5380, 4323, 6438, 7466, 6376, 11492, 12549, 4265, 11594, 4230, 4259, 5419, 10503, 12651, 4161, 5552, 10736, 2081], [2081, 2081, 3202, 2146, 3203, 4228, 3172, 5218, 6275, 3140, 5285, 2115, 2145, 3205, 5251, 6309, 4161, 5552, 10736, 2081], [2081, 2081, 3170, 3137, 3170, 3171, 3171, 4161, 5218, 3139, 4227, 3138, 3137, 3171, 4194, 5252, 4161, 5552, 10736, 2081], [3137, 3137, 5445, 4356, 6535, 8556, 6443, 12548, 14663, 4268, 13741, 4264, 4291, 5486, 11593, 15854, 3137, 5486, 9678, 2081], [3137, 3137, 5348, 4291, 6405, 7432, 6343, 9411, 11493, 4232, 10537, 4229, 4259, 4361, 9446, 11594, 3137, 5486, 9678, 2081], [2081, 2081, 3170, 2145, 3202, 4228, 3171, 5218, 5250, 2116, 5252, 2115, 2113, 3204, 4195, 5284, 3137, 5486, 9678, 2081], [2081, 2081, 3169, 2113, 3170, 3171, 3138, 4161, 4194, 2115, 4195, 2114, 2113, 3171, 4194, 4195, 3137, 5486, 9678, 2081], [3105, 3137, 5413, 3299, 6470, 7467, 6409, 11492, 12582, 4266, 11628, 3207, 3235, 4428, 10536, 13708, 3137, 4428, 8588, 2081], [3105, 3105, 4291, 3235, 5348, 6375, 5318, 8355, 9412, 4231, 9480, 3173, 3202, 4328, 8390, 10536, 3137, 4428, 8588, 2081], [2081, 2081, 3170, 2145, 3170, 3171, 3171, 4194, 5218, 2115, 4228, 2114, 2113, 3172, 4195, 5252, 3137, 4428, 8588, 2081], [2081, 2081, 3137, 2113, 3170, 3139, 3138, 4161, 4162, 2114, 4195, 2082, 2113, 2147, 3138, 4195, 3137, 4428, 8588, 2081], [3105, 3105, 4324, 3267, 5413, 6409, 5352, 9411, 11525, 4232, 10570, 3206, 3235, 4362, 8423, 11626, 3137, 4362, 7498, 2081], [3105, 3105, 4259, 3202, 5316, 5318, 5285, 7298, 8356, 4198, 8423, 3172, 3202, 4295, 7333, 8423, 3137, 4362, 7498, 2081], [2081, 2081, 3170, 2113, 3170, 3171, 3139, 4161, 4194, 2115, 4195, 2114, 2113, 3171, 4194, 4227, 3137, 4362, 7498, 2081], [2081, 2081, 3137, 2113, 3138, 3138, 3138, 3137, 4162, 2114, 4194, 2082, 2113, 2114, 3138, 4194, 3137, 4362, 7498, 2081], [2081, 2081, 4291, 3234, 4324, 6375, 4294, 8355, 9412, 3175, 8456, 3173, 3202, 3304, 7366, 9512, 3137, 3304, 6408, 2081], [3105, 3105, 4226, 3202, 4259, 5285, 4228, 6274, 7331, 3173, 6341, 3171, 3170, 3238, 6276, 7366, 3137, 3304, 6408, 2081], [2081, 2081, 2113, 2113, 3170, 3139, 3138, 4161, 4162, 2114, 4195, 2114, 2113, 2147, 3138, 4195, 3137, 3304, 6408, 2081], [2081, 2081, 2113, 2113, 3137, 3138, 3138, 3137, 3137, 2082, 3138, 2081, 2113, 2114, 3138, 3138, 3137, 3304, 6408, 2081], [2081, 2081, 3235, 3202, 4291, 5286, 4229, 6274, 7331, 3173, 6342, 3172, 3170, 3238, 6308, 7398, 3105, 3238, 5318, 2081], [2081, 2081, 3202, 3170, 3203, 4228, 3172, 5218, 6274, 3140, 5252, 3139, 3170, 3204, 5251, 6308, 3105, 3238, 5318, 2081], [2081, 2081, 2113, 2113, 2113, 3138, 2114, 3137, 3137, 2082, 3138, 2082, 2113, 2114, 3138, 3170, 3105, 3238, 5318, 2081], [2081, 2081, 2113, 2113, 2113, 2114, 2113, 3137, 3137, 2082, 3138, 2081, 2081, 2114, 3137, 3138, 3105, 3238, 5318, 2081], [2081, 2081, 3202, 3170, 3203, 4228, 3172, 5218, 5250, 3140, 5252, 3139, 3170, 3204, 5251, 6309, 2081, 3204, 4261, 2081], [2081, 2081, 3170, 3137, 3170, 3171, 3171, 4161, 4194, 3139, 4195, 3138, 3137, 3171, 4194, 5251, 2081, 3204, 4261, 2081], [2081, 2081, 2113, 2113, 2113, 3138, 2114, 3137, 3137, 2082, 3138, 2081, 2081, 2114, 3137, 3138, 2081, 3204, 4261, 2081], [2081, 2081, 2081, 2081, 2113, 2113, 2081, 3105, 3137, 2081, 3137, 2081, 2081, 2113, 3105, 3137, 2081, 3204, 4261, 2081]]
    tile_pal_modes_bytes = bytearray(60 * 40)
    for m_i, arr555 in enumerate(tile_pal_modes_555):
        for c_i, val555 in enumerate(arr555):
            struct.pack_into("<H", tile_pal_modes_bytes, m_i * 40 + c_i * 2, val555)

    # 3 battle move flash palettes (0=default, 1=flame, 2=chill) -> 3 x 256B (128 halfwords each for BG_PALETTE[128..255])
    battle_flash_pals_555 = [[9679, 9679, 13076, 10962, 15190, 17212, 15098, 22226, 24373, 11899, 22429, 10839, 10897, 13150, 20249, 25567, 9679, 9679, 13076, 10962, 15190, 17212, 15098, 22226, 24373, 11899, 22429, 10839, 10897, 13150, 20249, 25567, 10735, 17343, 23449, 11128, 22363, 18101, 15987, 12861, 17203, 25427, 14109, 25428, 11759, 10735, 13840, 11759, 14897, 11759, 12816, 14929, 13906, 10703, 10703, 9882, 18303, 15198, 11836, 13107, 20223, 12953, 9749, 17180, 16212, 12976, 21434, 9972, 17372, 21215, 16987, 24447, 24217, 18965, 25404, 9915, 19391, 15089, 11887, 19351, 10814, 9689, 14079, 25460, 21232, 25564, 25566, 24442, 25567, 22259, 17008, 25465, 20351, 19122, 13969, 24184, 20223, 20127, 12919, 10972, 11095, 11069, 12816, 12817, 12786], [6286, 6286, 8659, 7569, 10805, 12795, 10681, 17809, 19956, 7482, 19036, 7446, 7504, 8733, 16856, 21150, 6286, 6286, 8659, 7569, 10805, 12795, 10681, 17809, 19956, 7482, 19036, 7446, 7504, 8733, 16856, 21150, 7342, 13950, 20056, 7767, 19002, 13716, 11570, 8444, 13810, 21042, 9692, 22067, 7342, 7342, 9455, 7342, 10480, 7342, 8399, 11536, 10513, 6286, 6286, 6489, 13918, 11837, 7419, 8690, 15806, 8536, 6388, 12763, 12851, 8591, 17017, 5555, 12955, 16798, 12570, 20030, 19800, 14548, 22011, 5530, 15998, 10672, 7470, 15958, 7421, 5272, 9662, 22099, 17839, 22171, 22173, 20057, 22174, 17842, 13615, 22104, 16990, 14705, 9552, 19767, 15806, 15710, 9526, 6555, 6710, 7676, 8399, 8400, 8401], [15749, 15781, 19146, 17032, 21292, 23315, 21168, 28297, 30443, 17970, 28500, 16909, 16968, 18196, 26319, 31637, 15749, 15781, 19146, 17032, 21292, 23315, 21168, 28297, 30443, 17970, 28500, 16909, 16968, 18196, 26319, 31637, 16805, 23413, 29519, 17230, 28465, 24203, 22057, 18932, 23273, 31529, 20180, 31530, 17830, 16805, 19943, 17829, 20967, 17830, 18886, 21000, 19976, 15781, 15749, 15952, 24405, 21300, 17906, 19209, 26293, 19023, 15851, 23251, 22314, 19079, 27504, 16042, 23442, 27285, 23058, 30517, 29263, 24011, 31475, 16017, 25461, 21160, 17957, 25421, 16884, 15791, 20149, 31562, 27303, 31634, 31636, 29520, 31637, 28329, 23079, 31567, 26453, 25193, 19015, 30254, 26293, 25205, 18989, 17043, 17197, 17140, 17863, 18888, 18889]]
    battle_flash_pals_bytes = bytearray(3 * 256)
    for k_i, arr555 in enumerate(battle_flash_pals_555):
        for c_i, val555 in enumerate(arr555):
            struct.pack_into("<H", battle_flash_pals_bytes, k_i * 256 + c_i * 2, val555)

    # Precompute 2 animated 4bpp map tile sets (animTick = 0 and animTick = 1, 74 * 32 = 2,368 bytes each)
    tiles_anim0_bytes = bytearray()
    tiles_anim1_bytes = bytearray()
    for tid in range(74):
        g0 = list(ext_dict["tiles_py"][tid])
        g1 = list(ext_dict["tiles_py"][tid])
        if tid in (13, 25, 37, 49):
            # Water shimmer: fillStyle = '#F8F8F0' (15), fillRect(sx + (animTick ? 2 : 5), sy + 3, 2, 1)
            g0[3 * 8 + 5] = 15; g0[3 * 8 + 6] = 15
            g1[3 * 8 + 2] = 15; g1[3 * 8 + 3] = 15
        elif tid in (11, 23, 35, 47, 62):
            # Tall grass sway when animTick == 1: fillStyle = '#78C860' (4), fillRect(sx + 1, sy + 1, 2, 2)
            g1[1 * 8 + 1] = 4; g1[1 * 8 + 2] = 4
            g1[2 * 8 + 1] = 4; g1[2 * 8 + 2] = 4
        for i in range(0, 64, 2):
            tiles_anim0_bytes.append((g0[i] & 0xF) | ((g0[i + 1] & 0xF) << 4))
            tiles_anim1_bytes.append((g1[i] & 0xF) | ((g1[i + 1] & 0xF) << 4))

    # Pre-indexed linear 32x32 8bpp species front/back sprites (151 * 2 * 1024 = 309,248 B), index 0 = 0 (transparent!)
    sp_pal_map_bytes = bytearray()
    for sp in ext_dict["beatsts_py"]:
        pmap = [0] + [col_idx_of[c.lower()] for c in sp["palette"][1:]]
        for grid in (sp["front"], sp["back"]):
            for i in range(1024):
                sp_pal_map_bytes.append(pmap[grid[i] & 0xF])

    # Pre-tiled 16x32 8bpp 1D hardware OBJ sprites for all 47 CHAR_SPRITES x 4 dirs x 3 walkFrames (47 * 4 * 3 * 512 = 288,768 B)
    char_keys = list(ext_dict["char_sprites"].keys())
    char_obj_bytes = bytearray()
    for k in char_keys:
        for d in ("down", "up", "left", "right"):
            for wf in range(3):
                grid = ext_dict["char_grids_py"][k][d][wf] # 16x24
                for ty in range(4): # 4 tile rows (32px tall; rows 24..31 are transparent 0)
                    for tx in range(2): # 2 tile cols (16px wide)
                        for py in range(8):
                            ry = ty * 8 + py
                            for px in range(8):
                                rx = tx * 8 + px
                                if ry < 24:
                                    c = grid[ry * 16 + rx]
                                    char_obj_bytes.append(col_idx_of[c.lower()] if c else 0)
                                else:
                                    char_obj_bytes.append(0)

    # 624-byte initial_npc_xy table
    init_npc_xy_bytes = bytearray(624)
    g_idx = 0
    for mid in list(ext_dict["maps"].keys()):
        for n in ext_dict["maps"][mid].get("npcs", []):
            init_npc_xy_bytes[g_idx * 2] = n["x"] & 0xFF
            init_npc_xy_bytes[g_idx * 2 + 1] = n["y"] & 0xFF
            g_idx += 1

    # Pre-register all UI & Engine strings in UIStringPool so their offsets are known during assembly
    ui_pool = UIStringPool()
    for s in [
        " reached Lv.", "! ", "Learned ", "Evolved into ", " used ", " (-", " HP)!",
        "Super tasty! ", "Not very savory... ", "FLAVOR COMBO (", ")! ", " is ",
        "Sizzling! ", "Brined! ", "Drowsy! ", "Seasoned! ", "Appetized! ",
        " fainted! +", " XP! ", " sent out ", " fainted! Go, ",
        " All your bEATsts fainted! Rushing back to Simmer Inn...",
        "Sprinkled ", " looks delighted! ", " sat down at your ",
        " and joined your party!", " and hopped into your Box!",
        " only sits down at Night!", " insists on a Tier ", "+ setting!",
        " sniffed the ", " (", "%) and stepped back! ",
        "Got away safely!", "Cannot plate another chef bEATst!", "Used ", "Go, ",
        "Welcome to Pantrylia, ", "Your ", " is eager to battle and meet wild dishes!",
        "Tip: In wild battles, use PLATE to set a table and befriend bEATsts!",
        "Time shifted to Nighttime (Starlight)!", "Time shifted to Daytime (Sunny)!",
        "Saved Slot ", ")!", "This path requires ", " Kitchen Seals! You have ", ".",
        "Only the Grand Champion may enter the Eternal Pantry!",
        "Click! A locked gate clicked open nearby!", " - Welcome to ",
        "You dipped the Soup Ladle into the shimmering water...",
        "All your bEATsts are simmering at 100% HP and PP!",
        "Simmered Broth Cup + Garnish Treat into a fresh Hearty Stew!",
        "Stove Chef: Bring 1 Broth Cup and 1 Garnish Treat to cook a Hearty Stew!",
        "bEATst Cafe: Your stored bEATsts will relax here once your party is full!",
        "bEATst Cafe (", " resting): ", ", ", " are happily nibbling crumbs!",
        "The Secret Pantry shimmers with golden steam...",
        "A luminous aroma unites Sandwich, Dumpling, Noodle, and Soup!",
        "The mythical #151 Consommyth emerges!",
        'A locked golden pantry door. Inscription: "Only a Champion at Night bearing all 4 Food Families and a Royal Banquet Setting may enter."',
        ": Thank you again for your help!", ": That quest is already complete!",
        ": You haven't started this errand yet!", ": You missed an earlier stop on this quest!",
        ": Someone is looking for this, but you haven't taken their request yet!",
        ": You haven't completed all the earlier steps yet!", ": ",
        "Chef Brotholomew: 151/151!! You have befriended every bEATst in Pantrylia!",
        "Accept the Grand Culinary Diploma of ConsciousNode!",
        "Welcome to the Hall of Flavor! The Eternal Pantry is now open!",
        "A wild ", " (Lv.", ") popped out!",
        "bEATsts", "ConsciousNode SoftWorks", "> PLAY / SAVE SLOTS", "  PLAY / SAVE SLOTS",
        "> OPTIONS", "  OPTIONS", "> CONTROLS", "  CONTROLS", "Press Z / Enter / A",
        "SELECT SAVE SLOT", "SLOT ", ": [ NEW GAME ]", "Seals:", "/8 Dex:", "m",
        "CHOOSE YOUR bEATst!", "Sandw", "Dumpl", "Noodl", "Soup", "L/R:Dish U/D:Look A:Go",
        "OPTIONS", "> Text : < ", "  Text : < ", "Slow >", "Normal >", "Fast >",
        "> Vol  : < ", "  Vol  : < ", "% >", "> Back", "  Back",
        "CONTROLS", "Move : Arrows / WASD / DPad", "A    : Z / Enter / Space",
        "B    : X / Esc / Backspace", "Menu : M (Start)", "Time : N (Select Day/Night)",
        "Press A or B to return", "Night Seals:", "Day Seals:", "/8 ", "G", "v",
        "TEMP:CHILL -2", "TEMP:COOL -1", "TEMP:ROOM 0", "TEMP:WARM +1", "TEMP:SEAR +2",
        " L", "Sizzling", "Brined", "Drowsy", "Seasoned", "Appetized", "HP ", "/",
        "> FIGHT", "  FIGHT", "> PLATE", "  PLATE", "> BAG", "  BAG", "> PARTY", "  PARTY",
        "No plates/treats! (B)", " x", "%", " TRT", "No healing items! (B)",
        ">PARTY", " PARTY", ">bEATdex", " bEATdex", ">BOX", " BOX", ">BAG", " BAG",
        ">SAVE", " SAVE", ">OPTIONS", " OPTIONS", ">CONTROLS", " CONTROLS", ">CLOSE", " CLOSE",
        "bEATdex ", "COMPLETE!", "???", "Not seen yet",
        "PARTY (A:Lead B:Back)", "BOX (", ") A:ToParty", "Box is empty!",
        "BAG (", "G) A:Use", "MART (", "G) A:Buy",
        "Teach ", "?", "Replace which move:", "> ", "  ", "> Cancel / Skip", "  Cancel / Skip",
        "CONSCIOUSNODE SOFTWORKS", "MIT License", "GRAND CHEF-TAMER:", "CHAMPION PARTY:",
        "Thank you for playing!", "Press A or B to continue",
        "ENTER CHEF NAME:", "Brie", "OK", "A:Type B:Del L:Case START:OK"
    ]:
        ui_pool.add(s)
    while len(ui_pool.buf) % 4 != 0:
        ui_pool.buf.append(0)

    a = ArmAsm(0x08000000)
    a.b("rom_entry")
    a.emit_bytes(b"\x00" * (0xC0 - 4))
    TABLE_DIR_ROM_ADDR = 0x08020000
    a.emit32(0x42454154)
    a.emit32(TABLE_DIR_ROM_ADDR)
    a.emit_bytes(b"SRAM_V113\x00\x00\x00")
    a.align(4)

    table_addrs = {}
    off_cur = TABLE_DIR_ROM_ADDR + 8 + len(tables) * 16
    off_cur = (off_cur + 15) & ~15
    for k in sorted(tables.keys()):
        name, b_data, cnt = tables[k]
        table_addrs[k] = off_cur
        off_cur = (off_cur + len(b_data) + 3) & ~3

    master_pal_rom_addr = off_cur
    off_cur = (off_cur + len(master_pal_bytes) + 3) & ~3
    dark_obj_pal_rom_addr = off_cur
    off_cur = (off_cur + len(dark_obj_pal_bytes) + 3) & ~3
    tile_pal_modes_rom_addr = off_cur
    off_cur = (off_cur + len(tile_pal_modes_bytes) + 3) & ~3
    battle_flash_pals_rom_addr = off_cur
    off_cur = (off_cur + len(battle_flash_pals_bytes) + 3) & ~3
    tiles_anim0_rom_addr = off_cur
    off_cur = (off_cur + len(tiles_anim0_bytes) + 3) & ~3
    tiles_anim1_rom_addr = off_cur
    off_cur = (off_cur + len(tiles_anim1_bytes) + 3) & ~3
    sp_pal_map_rom_addr = off_cur
    off_cur = (off_cur + len(sp_pal_map_bytes) + 3) & ~3
    char_obj_rom_addr = off_cur
    off_cur = (off_cur + len(char_obj_bytes) + 3) & ~3
    init_npc_xy_rom_addr = off_cur
    off_cur = (off_cur + len(init_npc_xy_bytes) + 3) & ~3
    ui_str_rom_addr = off_cur
    off_cur = (off_cur + len(ui_pool.buf) + 3) & ~3

    def ui_off(s):
        return ui_str_rom_addr + ui_pool.add(s)

    def col(hex_s):
        return col_idx_of[hex_s.lower()]

    emit_softfloat(a)
    emit_core_and_battle(a, table_addrs, ui_str_rom_addr, ui_pool, control_mode=control_mode)

    # fnv1a_32(R0=ptr_aligned4, R1=len_mult4) -> R0=hash
    a.label("fnv1a_32")
    a.push([2, 3, 4, 5, 14])
    a.mov_reg(2, 0)
    a.mov_reg(3, 1)
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

    a.str_imm(0, 5, 0x08)
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

    # init_all_npc_xy()
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

    a.mov_imm(5, 0x02001000)
    a.strb_imm(4, 5, 0x1F)
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x1E)
    a.ldr_imm(0, 6, 0x1C)
    a.str_imm(0, 5, 0x00)
    a.mov_imm(0, 3)
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x45)
    a.strb_imm(0, 5, 0x4B) # force full BG0 clear on load
    a.mov_imm(0, 0xFF)
    a.strb_imm(0, 5, 0x46)

    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x71)
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

    # Audio Engine
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
    a.mov_imm(5, 0x02001300)
    a.ldrb_imm(1, 5, 0)
    a.cmp_reg(1, 4)
    a.b("pm_done", cond=0x0)
    a.strb_imm(4, 5, 0)
    a.mov_imm(0, 0)
    a.strh_imm(0, 5, 2)
    a.mov_imm(0, 32)
    a.mul(6, 4, 0)
    a.mov_imm(0, table_addrs[14])
    a.add_reg(6, 0, 6)
    a.ldrh_imm(1, 6, 4)
    a.strh_imm(1, 5, 6)
    a.mov_imm(1, 1800)
    a.strh_imm(1, 5, 4)
    a.ldrb_imm(1, 6, 6)
    a.strb_imm(1, 5, 8)
    for c_i in range(4):
        a.mov_imm(1, 0)
        a.strh_imm(1, 5, 0x0C + c_i * 2)
        a.strh_imm(1, 5, 0x14 + c_i * 2)
        a.ldrb_imm(1, 6, 8 + c_i)
        a.strh_imm(1, 5, 0x1C + c_i * 2)
        a.ldr_imm(1, 6, 12 + c_i * 4)
        a.add_reg(1, 0, 1)
        a.str_imm(1, 5, 0x24 + c_i * 4)
    a.label("pm_done")
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    a.label("play_map_music")
    a.push([4, 14])
    a.mov_imm(0, 0x02000000)
    a.ldrb_imm(0, 0, 0x28)
    a.mov_imm(1, 40)
    a.mul(0, 0, 1)
    a.mov_imm(1, table_addrs[10])
    a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 15)
    a.bl("play_music")
    a.pop([4, 15])
    a.flush_literals()

    a.label("play_sfx")
    a.push([4, 14])
    a.mov_imm(4, 0x02001300)
    a.strb_imm(0, 4, 1)
    a.pop([4, 15])
    a.flush_literals()

    a.label("step_audio_frame")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_imm(4, 0x02001300)
    a.ldrb_imm(5, 4, 0)
    a.cmp_imm(5, 18)
    a.b("saf_done", cond=0x2)
    a.ldrh_imm(6, 4, 2)
    a.ldrh_imm(0, 4, 4)
    a.ldrh_imm(1, 4, 6)
    a.add_reg(0, 0, 1)
    a.mov_imm(2, 1800)
    a.cmp_reg(0, 2)
    a.strh_imm(0, 4, 4, cond=0x3)
    a.b("saf_inc_frame", cond=0x3)
    a.sub_reg(0, 0, 2)
    a.strh_imm(0, 4, 4)

    a.mov_imm(7, 0)
    a.label("saf_ch_loop")
    a.cmp_imm(7, 4)
    a.b("saf_inc_frame", cond=0x2)
    a.add_reg(8, 4, 7, shift_imm=1, shift_type=0)
    a.ldrh_imm(0, 8, 0x14)
    a.cmp_imm(0, 0)
    a.b("saf_trigger_note", cond=0x0)
    a.sub_imm(0, 0, 1)
    a.strh_imm(0, 8, 0x14)
    a.b("saf_ch_next")

    a.label("saf_trigger_note")
    a.ldrh_imm(9, 8, 0x0C)
    a.ldrh_imm(10, 8, 0x1C)
    a.cmp_imm(10, 0)
    a.b("saf_ch_next", cond=0x0)
    a.cmp_reg(9, 10)
    a.b("saf_idx_ok", cond=0x3)
    a.ldrb_imm(0, 4, 8)
    a.cmp_imm(0, 0)
    a.b("saf_ch_next", cond=0x0)
    a.mov_imm(9, 0)
    a.label("saf_idx_ok")
    a.add_reg(0, 4, 7, shift_imm=2, shift_type=0)
    a.ldr_imm(0, 0, 0x24)
    a.add_reg(0, 0, 9, shift_imm=1, shift_type=0)
    a.ldrb_imm(10, 0, 0)
    a.ldrb_imm(11, 0, 1)

    a.add_imm(0, 9, 1)
    a.strh_imm(0, 8, 0x0C)
    a.sub_imm(0, 11, 1, s=1)
    a.mov_imm(0, 0, cond=0x4)
    a.strh_imm(0, 8, 0x14)

    a.mov_imm(0, 0x0203FC00)
    a.add_imm(1, 0, 0x1C0)
    a.ldrh_imm(2, 1, 2)
    a.and_imm(3, 2, 63)
    a.add_imm(2, 2, 1)
    a.strh_imm(2, 1, 2)
    a.add_imm(1, 0, 0x200)
    a.add_reg(1, 1, 3, shift_imm=3, shift_type=0)
    a.strb_imm(5, 1, 0)
    a.strb_imm(7, 1, 1)
    a.strb_imm(10, 1, 2)
    a.strb_imm(11, 1, 3)
    a.strh_imm(9, 1, 4)
    a.strh_imm(6, 1, 6)

    a.mov_imm(0, 0x04000000)
    a.cmp_imm(7, 0)
    a.b("saf_psg_ch1", cond=0x1)
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
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
    a.mov_reg(6, 2)

    a.mov_imm(7, 0x02000000)
    a.mov_imm(0, 0)
    a.mov_imm(1, 0)
    a.label("sng_clr")
    a.add_reg(2, 7, 1)
    a.str_imm(0, 2, 0)
    a.add_imm(1, 1, 4)
    a.cmp_imm(1, 0x1000)
    a.b("sng_clr", cond=0x3)

    a.mov_imm(0, 0x02001000)
    a.str_imm(6, 0, 0x00)
    a.mov_imm(1, 0)
    a.str_imm(1, 0, 0x04)
    a.str_imm(1, 0, 0x08)
    a.strb_imm(4, 0, 0x1F)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x1E)

    a.add_imm(1, 0, 0x94)
    a.ldrb_imm(2, 1, 0)
    a.cmp_imm(2, 0)
    a.b("sng_copy_custom_name", cond=0x1)
    a.mov_imm(2, 0x65697242)
    a.str_imm(2, 7, 0x0C)
    a.b("sng_name_done")
    a.label("sng_copy_custom_name")
    for w_i in range(3):
        a.ldr_imm(2, 1, w_i * 4)
        a.str_imm(2, 7, 0x0C + w_i * 4)
    a.label("sng_name_done")

    a.mov_reg(0, 5)
    a.mov_imm(1, 5)
    a.mov_imm(2, 0x020000B4)
    a.bl("create_mon")
    a.mov_imm(0, 1)
    a.strb_imm(0, 7, 0x0B0)
    a.mov_reg(0, 5)
    a.bl("mark_caught")

    a.str_imm(6, 7, 0x1C)
    a.mov_imm(0, 500)
    a.str_imm(0, 7, 0x24)
    a.mov_imm(0, 0)
    a.strb_imm(0, 7, 0x28)
    a.mov_imm(0, 14)
    a.strb_imm(0, 7, 0x29)
    a.mov_imm(0, 12)
    a.strb_imm(0, 7, 0x2A)
    a.mov_imm(0, 1)
    a.strb_imm(0, 7, 0x2B)
    a.mov_imm(0, 0x02001000)
    a.ldrb_imm(1, 0, 0x2B)
    a.strb_imm(1, 7, 0x2D)

    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 0x71)
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

    # Populate 3 welcome dialog lines into dialog_buf[0..2]
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Welcome to Pantrylia, "))
    a.bl("fmt_str")
    a.add_imm(0, 7, 0x0C) # state.name
    a.bl("fmt_str")
    a.mov_imm(0, 33)
    a.bl("fmt_putc")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")

    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Your "))
    a.bl("fmt_str")
    a.mov_reg(0, 5)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" is eager to battle and meet wild dishes!"))
    a.bl("fmt_str")
    a.mov_imm(0, 1)
    a.bl("fmt_copy_to_dialog")

    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Tip: In wild battles, use PLATE to set a table and befriend bEATsts!"))
    a.bl("fmt_str")
    a.mov_imm(0, 2)
    a.bl("fmt_copy_to_dialog")

    a.mov_imm(0, 3)
    a.mov_imm(1, 0)
    a.mov_imm(2, 0)
    a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 0xFF)
    a.strb_imm(1, 0, 0x46)
    a.pop([4, 5, 6, 7, 15])
    a.flush_literals()

    # Helper: show_dialog_n(R0=raw_count 1..4, R1=cb_kind, R2=cb_arg0, R3=cb_arg1)
    # Paginates each raw entry in 0x02002800 + raw_i*256 into 4-line pages (<=27 chars/line)
    # in 0x02003000 + page_idx*128, matching Game.paginateDialog / Game.showDialog in 07_game_engine.js!
    a.label("show_dialog_n")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_imm(4, 0x02001000)
    a.mov_imm(5, 0)
    a.strb_imm(5, 4, 0x41) # dialog_idx = 0
    a.strb_imm(1, 4, 0x42) # cb_kind
    a.strb_imm(2, 4, 0x43) # cb_arg0
    a.strb_imm(3, 4, 0x44) # cb_arg1
    a.mov_imm(1, 4)
    a.strb_imm(1, 4, 0x20) # screen = DIALOG (4)
    a.mov_imm(1, 1)
    a.strb_imm(1, 4, 0x45) # dirty_ui = 1

    a.mov_reg(4, 0) # raw_count
    a.mov_imm(5, 0) # raw_i = 0
    a.mov_imm(6, 0) # page_idx = 0

    a.label("sdn_raw_loop")
    a.cmp_reg(5, 4)
    a.b("sdn_all_done", cond=0x2)
    a.mov_imm(7, 0x02002800)
    a.add_reg(7, 7, 5, shift_imm=8, shift_type=0) # src_ptr
    a.mov_imm(8, 0x02003000)
    a.add_reg(8, 8, 6, shift_imm=7, shift_type=0) # dst_page_ptr
    a.mov_imm(0, 0)
    a.strb_imm(0, 8, 0)
    a.mov_imm(9, 0)  # cur_page_len = 0
    a.mov_imm(10, 0) # line_len = 0
    a.mov_imm(11, 0) # rows_in_page = 0

    a.label("sdn_word_loop")
    a.mov_imm(12, 0) # w_len = 0
    a.label("sdn_scan_w")
    a.add_reg(0, 7, 12)
    a.ldrb_imm(1, 0, 0) # delim (0 or 32)
    a.cmp_imm(1, 0)
    a.cmp_imm(1, 32, cond=0x1)
    a.b("sdn_scan_done", cond=0x0)
    a.add_imm(12, 12, 1)
    a.b("sdn_scan_w")
    a.label("sdn_scan_done")

    a.add_reg(0, 10, 12)
    a.cmp_imm(0, 27)
    a.b("sdn_same_line", cond=0x9) # <= 27
    a.add_imm(11, 11, 1) # rows_in_page++
    a.cmp_imm(11, 4)
    a.b("sdn_row_ok", cond=0x3)
    a.add_imm(6, 6, 1) # page_idx++
    a.mov_imm(8, 0x02003000)
    a.add_reg(8, 8, 6, shift_imm=7, shift_type=0)
    a.mov_imm(0, 0)
    a.strb_imm(0, 8, 0)
    a.mov_imm(9, 0)  # cur_page_len = 0
    a.mov_imm(11, 0) # rows_in_page = 0
    a.label("sdn_row_ok")
    a.add_imm(10, 12, 1) # line_len = w_len + 1
    a.b("sdn_emit_w")

    a.label("sdn_same_line")
    a.add_reg(10, 10, 12)
    a.add_imm(10, 10, 1) # line_len += w_len + 1

    a.label("sdn_emit_w")
    a.cmp_imm(12, 0)
    a.b("sdn_do_append", cond=0x1)
    a.cmp_imm(1, 32)
    a.b("sdn_after_append", cond=0x1)
    a.label("sdn_do_append")
    a.cmp_imm(9, 0)
    a.b("sdn_copy_chars", cond=0x0)
    a.add_reg(0, 8, 9)
    a.mov_imm(2, 32)
    a.strb_imm(2, 0, 0)
    a.add_imm(9, 9, 1)
    a.label("sdn_copy_chars")
    a.mov_imm(2, 0)
    a.label("sdn_cp_lp")
    a.cmp_reg(2, 12)
    a.b("sdn_cp_done", cond=0x2)
    a.add_reg(0, 7, 2)
    a.ldrb_imm(3, 0, 0)
    a.add_reg(0, 8, 9)
    a.strb_imm(3, 0, 0)
    a.add_imm(9, 9, 1)
    a.add_imm(2, 2, 1)
    a.b("sdn_cp_lp")
    a.label("sdn_cp_done")
    a.add_reg(0, 8, 9)
    a.mov_imm(2, 0)
    a.strb_imm(2, 0, 0)

    a.label("sdn_after_append")
    a.cmp_imm(1, 32)
    a.add_reg(7, 7, 12, cond=0x0)
    a.add_imm(7, 7, 1, cond=0x0)
    a.b("sdn_word_loop", cond=0x0)

    a.add_imm(6, 6, 1)
    a.add_imm(5, 5, 1)
    a.b("sdn_raw_loop")

    a.label("sdn_all_done")
    a.cmp_imm(6, 0)
    a.mov_imm(6, 1, cond=0x0)
    a.mov_imm(4, 0x02001000)
    a.strb_imm(6, 4, 0x40) # dialog_count = total_pages
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # Helper: copy_npc_lines_to_dialog(R0=npc_rom_ptr, R1=arr_off (32, 44, 56, 68), R2=count, R3=with_name_prefix 0..1)
    a.label("copy_npc_lines_to_dialog")
    a.push([4, 5, 6, 7, 8, 14])
    a.mov_reg(4, 0) # npc_rom_ptr
    a.add_reg(5, 0, 1) # arr_ptr
    a.mov_reg(6, 2) # count
    a.mov_reg(7, 3) # with_name_prefix
    a.mov_imm(8, 0) # i = 0
    a.mov_imm(0, 0x02002800)
    a.strb_imm(8, 0, 0) # Clear raw dialog slot 0 in case count == 0
    a.label("cnl_loop")
    a.cmp_reg(8, 6)
    a.b("cnl_done", cond=0x2)
    a.bl("fmt_clear")
    a.cmp_imm(7, 0)
    a.b("cnl_no_pref", cond=0x0)
    a.ldr_imm(0, 4, 4) # npc.name str_off
    a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": "))
    a.bl("fmt_str")
    a.label("cnl_no_pref")
    a.add_reg(0, 5, 8, shift_imm=2, shift_type=0)
    a.ldr_imm(0, 0, 0)
    a.bl("fmt_rom_off")
    a.mov_reg(0, 8)
    a.bl("fmt_copy_to_dialog")
    a.add_imm(8, 8, 1)
    a.b("cnl_loop")
    a.label("cnl_done")
    a.pop([4, 5, 6, 7, 8, 15])
    a.flush_literals()

    # Helper: is_npc_hidden(R0=npc_rom_ptr) -> R0=1 if hidden else 0
    a.label("is_npc_hidden")
    a.push([1, 2, 3, 14])
    a.mov_reg(1, 0)
    a.mov_imm(2, 0x02000000)
    a.ldrb_imm(0, 1, 17)
    a.cmp_imm(0, 0xFF)
    a.b("inh_chk_sec", cond=0x0)
    a.ldrh_imm(3, 2, 0x42)
    a.mov_reg_rs(3, 3, 0, shift_type=1)
    a.tst_imm(3, 1)
    a.mov_imm(0, 1, cond=0x1)
    a.b("inh_done", cond=0x1)
    a.label("inh_chk_sec")
    a.ldrb_imm(0, 1, 18)
    a.cmp_imm(0, 0xFF)
    a.b("inh_vis", cond=0x0)
    a.ldrh_imm(3, 2, 0x40)
    a.mov_reg_rs(3, 3, 0, shift_type=1)
    a.tst_imm(3, 1)
    a.mov_imm(0, 1, cond=0x1)
    a.b("inh_done", cond=0x1)
    a.label("inh_vis")
    a.mov_imm(0, 0)
    a.label("inh_done")
    a.pop([1, 2, 3, 15])
    a.flush_literals()

    # Helper: find_visible_npc_at(R0=map_hdr_ptr, R1=tx, R2=ty) -> R0=npc_rom_ptr (or 0)
    a.label("find_visible_npc_at")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
    a.mov_reg(6, 2)
    a.ldrb_imm(7, 4, 18)
    a.ldr_imm(8, 4, 32)
    a.mov_imm(0, table_addrs[10])
    a.add_reg(8, 0, 8)
    a.mov_imm(9, 0)
    a.label("fvn_loop")
    a.cmp_reg(9, 7)
    a.b("fvn_none", cond=0x2)
    a.ldrh_imm(0, 8, 24)
    a.mov_imm(1, 0x02001800)
    a.add_reg(1, 1, 0, shift_imm=1, shift_type=0)
    a.ldrb_imm(2, 1, 0)
    a.ldrb_imm(3, 1, 1)
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
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
    a.mov_imm(6, 0x02000000)
    a.strb_imm(4, 6, 0x2B)

    a.mov_imm(7, 0)
    a.mov_imm(8, 0)
    a.cmp_imm(4, 0); a.mov_imm(8, 1, cond=0x0)
    a.cmp_imm(4, 1); a.mvn_imm(8, 0, cond=0x0)
    a.cmp_imm(4, 2); a.mvn_imm(7, 0, cond=0x0)
    a.cmp_imm(4, 3); a.mov_imm(7, 1, cond=0x0)

    a.ldrb_imm(0, 6, 0x29)
    a.add_reg(7, 0, 7)
    a.ldrb_imm(0, 6, 0x2A)
    a.add_reg(8, 0, 8)

    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40)
    a.mul(0, 0, 1)
    a.mov_imm(9, table_addrs[10])
    a.add_reg(9, 9, 0)

    a.ldrb_imm(10, 9, 17)
    a.ldr_imm(11, 9, 28)
    a.mov_imm(0, table_addrs[10])
    a.add_reg(11, 0, 11)
    a.mov_imm(2, 0)
    a.label("tm_port_loop")
    a.cmp_reg(2, 10)
    a.b("tm_no_portal", cond=0x2)
    a.ldrb_imm(0, 11, 0)
    a.ldrb_imm(1, 11, 1)
    a.cmp_reg(0, 7)
    a.cmp_reg(1, 8, cond=0x0)
    a.b("tm_port_found", cond=0x0)
    a.add_imm(11, 11, 8)
    a.add_imm(2, 2, 1)
    a.b("tm_port_loop")

    a.label("tm_port_found")
    a.ldrb_imm(0, 11, 5) # reqSeals
    a.cmp_imm(0, 0)
    a.b("tm_port_chk_champ", cond=0x0)
    a.ldrb_imm(1, 6, 0x2F)
    a.mov_imm(2, 0)
    for b_i in range(8):
        a.tst_imm(1, 1 << b_i)
        a.add_imm(2, 2, 1, cond=0x1)
    a.cmp_reg(2, 0)
    a.b("tm_port_chk_champ", cond=0x2)
    # Blocked by reqSeals: "This path requires ${portal.reqSeals} Kitchen Seals! You have ${this.state.seals.length}."
    a.mov_reg(7, 0) # reqSeals
    a.mov_reg(8, 2) # sealsCount
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("This path requires "))
    a.bl("fmt_str")
    a.mov_reg(0, 7)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off(" Kitchen Seals! You have "))
    a.bl("fmt_str")
    a.mov_reg(0, 8)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off("."))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("tm_ret")

    a.label("tm_port_chk_champ")
    a.ldrh_imm(0, 11, 6)
    a.cmp_imm(0, 0)
    a.b("tm_port_warp", cond=0x0)
    a.ldrb_imm(1, 6, 0x2E)
    a.cmp_imm(1, 0)
    a.b("tm_port_warp", cond=0x1)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Only the Grand Champion may enter the Eternal Pantry!"))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("tm_ret")

    a.label("tm_port_warp")
    a.mov_imm(0, 11)
    a.bl("play_sfx")
    a.ldrb_imm(0, 11, 2) # to_idx
    a.ldrb_imm(1, 11, 3) # tx
    a.ldrb_imm(2, 11, 4) # ty
    a.strb_imm(0, 6, 0x28)
    a.strb_imm(1, 6, 0x29)
    a.strb_imm(2, 6, 0x2A)
    a.mov_imm(3, 0x02001000)
    a.strb_imm(0, 3, 0x34) # banner_map_id = to_idx
    a.mov_imm(1, 120)
    a.strh_imm(1, 3, 0x30) # banner_timer_frames = 120
    if control_mode == "no_fade":
        a.mov_imm(1, 0)
    else:
        a.mov_imm(1, 13)
    a.strh_imm(1, 3, 0x32) # transition_timer_frames = 13
    a.mov_imm(1, 1)
    a.strb_imm(1, 3, 0x45) # dirty_ui = 1
    a.bl("play_map_music")
    a.b("tm_ret")

    a.label("tm_no_portal")
    a.ldrb_imm(10, 9, 12)
    a.ldrb_imm(11, 9, 13)
    a.cmp_imm(7, 0); a.b("tm_ret", cond=0xB)
    a.cmp_reg(7, 10); a.b("tm_ret", cond=0x2)
    a.cmp_imm(8, 0); a.b("tm_ret", cond=0xB)
    a.cmp_reg(8, 11); a.b("tm_ret", cond=0x2)

    a.ldr_imm(2, 9, 20)
    a.mov_imm(0, table_addrs[10])
    a.add_reg(2, 0, 2)
    a.mul(0, 8, 10)
    a.add_reg(0, 0, 7)
    a.add_reg(0, 2, 0)
    a.ldrb_imm(3, 0, 0)

    a.cmp_imm(3, 65)
    a.b("tm_chk_gate", cond=0x1)
    a.cmp_imm(4, 0)
    a.b("tm_ret", cond=0x1)
    a.add_imm(1, 8, 1)
    a.cmp_reg(1, 11)
    a.b("tm_ret", cond=0x2)
    a.mul(0, 1, 10)
    a.add_reg(0, 0, 7)
    a.add_reg(0, 2, 0)
    a.ldrb_imm(0, 0, 0)
    a.push([0, 1, 2])
    a.bl("is_tile_solid")
    a.mov_reg(3, 0)
    a.pop([0, 1, 2])
    a.cmp_imm(3, 0)
    a.b("tm_ret", cond=0x1)
    a.mov_reg(8, 1)
    a.mov_reg(3, 0)

    a.label("tm_chk_gate")
    a.cmp_imm(3, 73)
    a.b("tm_chk_solid", cond=0x1)
    a.ldrb_imm(0, 6, 0x28)
    a.mov_reg(1, 0, shift_imm=3, shift_type=1)
    a.and_imm(0, 0, 7)
    a.add_reg(1, 6, 1)
    a.ldrb_imm(1, 1, 0x30)
    a.mov_reg_rs(1, 1, 0, shift_type=1)
    a.tst_imm(1, 1)
    a.b("tm_ret", cond=0x0)
    a.b("tm_chk_npc")

    a.label("tm_chk_solid")
    a.push([3])
    a.mov_reg(0, 3)
    a.bl("is_tile_solid")
    a.cmp_imm(0, 0)
    a.pop([3])
    a.b("tm_ret", cond=0x1)

    a.label("tm_chk_npc")
    a.push([3])
    a.mov_reg(0, 9)
    a.mov_reg(1, 7)
    a.mov_reg(2, 8)
    a.bl("find_visible_npc_at")
    a.pop([3])
    a.cmp_imm(0, 0)
    a.b("tm_do_step", cond=0x0)
    a.ldrb_imm(1, 0, 13)
    a.cmp_imm(1, 0)
    a.b("tm_ret", cond=0x0)
    a.mov_reg(1, 7)
    a.mov_reg(2, 8)
    a.cmp_imm(4, 0); a.add_imm(2, 2, 1, cond=0x0)
    a.cmp_imm(4, 1); a.sub_imm(2, 2, 1, cond=0x0)
    a.cmp_imm(4, 2); a.sub_imm(1, 1, 1, cond=0x0)
    a.cmp_imm(4, 3); a.add_imm(1, 1, 1, cond=0x0)
    a.cmp_imm(1, 0); a.b("tm_ret", cond=0xB)
    a.cmp_reg(1, 10); a.b("tm_ret", cond=0x2)
    a.cmp_imm(2, 0); a.b("tm_ret", cond=0xB)
    a.cmp_reg(2, 11); a.b("tm_ret", cond=0x2)

    a.push([0, 1, 2, 3])
    a.ldr_imm(3, 9, 20)
    a.mov_imm(0, table_addrs[10])
    a.add_reg(3, 0, 3)
    a.mul(0, 2, 10)
    a.add_reg(0, 0, 1)
    a.add_reg(0, 3, 0)
    a.ldrb_imm(0, 0, 0)
    a.cmp_imm(0, 73)
    a.b("tm_push_fail", cond=0x0)
    a.bl("is_tile_solid")
    a.cmp_imm(0, 0)
    a.b("tm_push_fail", cond=0x1)
    a.ldr_imm(1, 13, 4)
    a.ldr_imm(2, 13, 8)
    a.mov_reg(0, 9)
    a.bl("find_visible_npc_at")
    a.cmp_imm(0, 0)
    a.b("tm_push_fail", cond=0x1)
    a.pop([0, 1, 2, 3])
    a.ldrh_imm(0, 0, 24)
    a.mov_imm(10, 0x02001800)
    a.add_reg(10, 10, 0, shift_imm=1, shift_type=0)
    a.strb_imm(1, 10, 0)
    a.strb_imm(2, 10, 1)
    a.b("tm_do_step")

    a.label("tm_push_fail")
    a.pop([0, 1, 2, 3])
    a.b("tm_ret")

    a.label("tm_do_step")
    a.strb_imm(7, 6, 0x29)
    a.strb_imm(8, 6, 0x2A)
    a.ldr_imm(0, 6, 0x20)
    a.add_imm(0, 0, 1)
    a.str_imm(0, 6, 0x20)
    a.mov_imm(1, 0x02001000)
    a.ldrb_imm(2, 1, 0x2C)
    a.cmp_imm(2, 1)
    a.mov_imm(2, 2, cond=0x0)
    a.mov_imm(2, 1, cond=0x1)
    a.strb_imm(2, 1, 0x2C)
    a.mov_imm(2, 1)
    a.strb_imm(2, 1, 0x45)

    a.push([3])
    a.mov_imm(1, 40)
    a.bl("udiv32")
    a.pop([3])
    a.cmp_imm(1, 0)
    a.b("tm_chk_switch", cond=0x1)
    a.ldrb_imm(0, 6, 0x2C)
    a.eor_imm(0, 0, 1)
    a.strb_imm(0, 6, 0x2C)

    a.label("tm_chk_switch")
    a.cmp_imm(3, 9)
    a.b("tm_chk_slide", cond=0x1)
    a.ldrb_imm(0, 6, 0x28)
    a.mov_reg(1, 0, shift_imm=3, shift_type=1)
    a.and_imm(0, 0, 7)
    a.mov_imm(2, 1)
    a.mov_reg_rs(2, 2, 0, shift_type=0)
    a.add_reg(1, 6, 1)
    a.ldrb_imm(0, 1, 0x30)
    a.tst_reg(0, 2)
    a.b("tm_chk_slide", cond=0x1)
    a.orr_reg(0, 0, 2)
    a.strb_imm(0, 1, 0x30)
    a.mov_imm(0, 9)
    a.bl("play_sfx")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Click! A locked gate clicked open nearby!"))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("tm_ret")

    a.label("tm_chk_slide")
    a.cmp_imm(5, 0)
    a.b("tm_chk_grass", cond=0x1)
    a.mov_imm(10, 0)
    a.label("tm_slide_loop")
    a.cmp_imm(10, 12)
    a.b("tm_chk_grass", cond=0x2)
    a.add_imm(10, 10, 1)
    a.ldrb_imm(0, 6, 0x29)
    a.ldrb_imm(1, 6, 0x2A)
    a.ldrb_imm(2, 9, 12)
    a.mul(1, 1, 2)
    a.add_reg(0, 1, 0)
    a.ldr_imm(1, 9, 20)
    a.mov_imm(2, table_addrs[10])
    a.add_reg(1, 2, 1)
    a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 0)
    a.cmp_imm(0, 67); a.mov_imm(0, 3, cond=0x0); a.b("tm_do_slide", cond=0x0)
    a.cmp_imm(0, 68); a.mov_imm(0, 2, cond=0x0); a.b("tm_do_slide", cond=0x0)
    a.cmp_imm(0, 69); a.mov_imm(0, 1, cond=0x0); a.b("tm_do_slide", cond=0x0)
    a.cmp_imm(0, 70); a.mov_imm(0, 0, cond=0x0); a.b("tm_do_slide", cond=0x0)
    a.cmp_imm(0, 66); a.ldrb_imm(0, 6, 0x2B, cond=0x0); a.b("tm_do_slide", cond=0x0)
    a.b("tm_chk_grass")

    a.label("tm_do_slide")
    a.push([3, 10])
    a.mov_imm(1, 1)
    a.bl("try_move")
    a.pop([3, 10])
    a.b("tm_slide_loop")

    a.label("tm_chk_grass")
    a.cmp_imm(3, 11)
    a.cmp_imm(3, 23, cond=0x1)
    a.cmp_imm(3, 35, cond=0x1)
    a.cmp_imm(3, 47, cond=0x1)
    a.cmp_imm(3, 62, cond=0x1)
    a.b("tm_ret", cond=0x1)
    a.ldrb_imm(10, 9, 16)
    a.cmp_imm(10, 0)
    a.b("tm_ret", cond=0x0)

    a.bl("game_rng_next")
    a.mov_imm(1, 0x28F5C290)
    a.cmp_reg(0, 1)
    a.b("tm_ret", cond=0x2)

    a.sub_imm(13, 13, 64)
    a.ldr_imm(8, 9, 24)
    a.mov_imm(0, table_addrs[10])
    a.add_reg(8, 0, 8)
    a.mov_imm(7, 0)
    a.mov_imm(11, 0)
    a.label("tm_wp_filter")
    a.cmp_reg(11, 10)
    a.b("tm_wp_filtered", cond=0x2)
    a.add_reg(0, 8, 11, shift_imm=2, shift_type=0)
    a.ldr_imm(4, 0, 0)
    a.and_imm(0, 4, 0xFF)
    a.sub_imm(0, 0, 1)
    a.mov_imm(1, 56)
    a.mul(0, 0, 1)
    a.mov_imm(1, table_addrs[4])
    a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 10)
    a.cmp_imm(0, 0)
    a.b("tm_wp_keep", cond=0x0)
    a.ldrb_imm(0, 6, 0x2C)
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
    a.bl("game_rng_next")
    a.cmp_imm(7, 0)
    a.ldr_imm(4, 8, 0, cond=0x0)
    a.b("tm_wp_picked", cond=0x0)
    a.umull(2, 3, 0, 7)
    a.add_reg(0, 13, 3, shift_imm=2, shift_type=0)
    a.ldr_imm(4, 0, 0)
    a.label("tm_wp_picked")
    a.add_imm(13, 13, 64)

    a.bl("game_rng_next")
    a.mov_reg(1, 4, shift_imm=8, shift_type=1)
    a.and_imm(1, 1, 0xFF)
    a.mov_reg(2, 4, shift_imm=16, shift_type=1)
    a.and_imm(2, 2, 0xFF)
    a.sub_reg(2, 2, 1)
    a.add_imm(2, 2, 1)
    a.umull(3, 5, 0, 2)
    a.add_reg(1, 1, 5)
    a.and_imm(0, 4, 0xFF)
    a.bl("start_wild_battle")

    a.label("tm_ret")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # start_wild_battle(R0=speciesId, R1=level)
    a.label("start_wild_battle")
    a.push([4, 5, 6, 14])
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
    a.bl("mark_seen")
    a.mov_reg(0, 4)
    a.mov_reg(1, 5)
    a.mov_imm(2, 0x02001110)
    a.bl("create_mon")

    # Log: "A wild ${foe.nickname} (Lv.${foe.level}) popped out!"
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("A wild "))
    a.bl("fmt_str")
    a.mov_reg(0, 4)
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" (Lv."))
    a.bl("fmt_str")
    a.mov_reg(0, 5)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off(") popped out!"))
    a.bl("fmt_str")
    a.bl("fmt_append_to_blog")

    a.mov_imm(6, 0x02000000)
    a.ldrb_imm(1, 6, 0x0B0)
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

    a.mov_imm(4, 0x02001100)
    a.mov_imm(0, 1)
    a.strb_imm(0, 4, 0)
    a.strb_imm(0, 4, 1)
    a.mov_imm(0, 0xFF)
    a.strb_imm(0, 4, 2)
    a.mov_imm(0, 1)
    a.strb_imm(0, 4, 3)
    a.mov_imm(0, 0)
    a.strb_imm(0, 4, 4)
    a.strb_imm(3, 4, 5)
    a.strb_imm(0, 4, 6)
    a.strb_imm(0, 4, 7)
    a.mov_imm(0, 1)
    a.strb_imm(0, 4, 8)
    a.mov_imm(0, 0)
    a.strb_imm(0, 4, 9)
    a.strb_imm(0, 4, 0x0A)

    a.mov_imm(0, 9)
    a.bl("play_music")
    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 5)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45)
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    # start_trainer_battle(R0=trainer_idx 0..32)
    a.label("start_trainer_battle")
    a.push([4, 5, 6, 7, 8, 14])
    a.mov_reg(4, 0)
    a.mov_imm(0, 48)
    a.mul(5, 4, 0)
    a.mov_imm(0, table_addrs[11])
    a.add_reg(5, 0, 5)
    a.ldrb_imm(6, 5, 28)

    a.mov_imm(7, 0)
    a.mov_imm(8, 0x02001110)
    a.label("stb_foe_loop")
    a.cmp_reg(7, 6)
    a.b("stb_foe_done", cond=0x2)
    a.add_reg(0, 5, 7, shift_imm=1, shift_type=0)
    a.ldrb_imm(0, 0, 36)
    a.bl("mark_seen")
    a.add_reg(0, 5, 7, shift_imm=1, shift_type=0)
    a.ldrb_imm(1, 0, 37)
    a.ldrb_imm(0, 0, 36)
    a.mov_reg(2, 8)
    a.bl("create_mon")
    a.add_imm(8, 8, 48)
    a.add_imm(7, 7, 1)
    a.b("stb_foe_loop")
    a.label("stb_foe_done")

    # Log: "${trainer.name} sent out ${foeParty[0].nickname}!"
    a.bl("blog_clear")
    a.bl("fmt_clear")
    a.mov_reg(0, 4)
    a.bl("fmt_tr_name")
    a.mov_imm(0, ui_off(" sent out "))
    a.bl("fmt_str")
    a.ldrb_imm(0, 5, 36) # foeParty[0].id
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.mov_imm(0, 33)
    a.bl("fmt_putc")
    a.bl("fmt_append_to_blog")

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
    a.strb_imm(0, 7, 0)
    a.mov_imm(0, 0)
    a.strb_imm(0, 7, 1)
    a.strb_imm(4, 7, 2)
    a.strb_imm(6, 7, 3)
    a.strb_imm(0, 7, 4)
    a.strb_imm(3, 7, 5)
    a.strb_imm(0, 7, 6)
    a.strb_imm(0, 7, 7)
    a.mov_imm(0, 1)
    a.strb_imm(0, 7, 8)
    a.mov_imm(0, 0)
    a.strb_imm(0, 7, 9)
    a.strb_imm(0, 7, 0x0A)

    a.mov_imm(0, 10)
    a.cmp_imm(4, 17)
    a.b("stb_music_set", cond=0x3)
    a.cmp_imm(4, 28)
    a.mov_imm(0, 11, cond=0x9)
    a.cmp_imm(4, 32)
    a.mov_imm(0, 12, cond=0x0)
    a.label("stb_music_set")
    a.bl("play_music")

    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 5)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45)
    a.pop([4, 5, 6, 7, 8, 15])
    a.flush_literals()

    # heal_party()
    a.label("heal_party")
    a.push([4, 5, 6, 14])
    a.mov_imm(4, 0x02000000)
    a.ldrb_imm(5, 4, 0x0B0)
    a.add_imm(4, 4, 0x0B4)
    a.mov_imm(6, 0)
    a.label("hp_loop")
    a.cmp_reg(6, 5)
    a.b("hp_done", cond=0x2)
    a.ldrh_imm(0, 4, 0x0A)
    a.strh_imm(0, 4, 0x08)
    a.mov_imm(0, 0)
    a.strb_imm(0, 4, 0x06)
    a.ldr_imm(0, 4, 0x24)
    a.str_imm(0, 4, 0x20)
    a.add_imm(4, 4, 48)
    a.add_imm(6, 6, 1)
    a.b("hp_loop")
    a.label("hp_done")
    a.pop([4, 5, 6, 15])
    a.flush_literals()

    # finish_battle_full(R0=outcome)
    a.label("finish_battle_full")
    a.push([4, 5, 6, 7, 8, 14])
    a.mov_reg(4, 0)
    a.mov_imm(5, 0x02001100)
    a.ldrb_imm(6, 5, 1)
    a.ldrb_imm(7, 5, 2)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0)
    a.strb_imm(0, 5, 8)

    a.cmp_imm(4, 1)
    a.b("fbf_chk_lose", cond=0x1)
    a.cmp_imm(6, 0)
    a.b("fbf_to_ow", cond=0x1)
    a.mov_imm(5, 0x02000000)
    a.mov_imm(0, 48)
    a.mul(8, 7, 0)
    a.mov_imm(1, table_addrs[11])
    a.add_reg(8, 1, 8) # R8 = trainer_rom_ptr

    a.mov_reg(0, 7, shift_imm=3, shift_type=1)
    a.and_imm(1, 7, 7)
    a.mov_imm(2, 1)
    a.mov_reg_rs(2, 2, 1, shift_type=0)
    a.add_reg(0, 5, 0)
    a.ldrb_imm(1, 0, 0x38)
    a.tst_reg(1, 2)
    a.b("fbf_already_def", cond=0x1)
    a.orr_reg(1, 1, 2)
    a.strb_imm(1, 0, 0x38)
    a.ldrh_imm(1, 8, 24)
    a.cmp_imm(1, 0)
    a.mov_imm(1, 200, cond=0x0)
    a.ldr_imm(2, 5, 0x24)
    a.add_reg(2, 2, 1)
    a.str_imm(2, 5, 0x24)
    a.ldrb_imm(1, 8, 27)
    a.cmp_imm(1, 0)
    a.b("fbf_already_def", cond=0x0)
    a.ldrb_imm(1, 8, 26)
    a.mov_imm(2, 1)
    a.mov_reg_rs(2, 2, 1, shift_type=0)
    a.ldrb_imm(1, 5, 0x2F)
    a.orr_reg(1, 1, 2)
    a.strb_imm(1, 5, 0x2F)

    a.label("fbf_already_def")
    a.mov_imm(0, 14)
    a.bl("play_music")
    a.cmp_imm(7, 32)
    a.mov_imm(0, 1, cond=0x0)
    a.strb_imm(0, 5, 0x2E, cond=0x0)
    a.mov_imm(0, 0x02001000)
    a.ldrb_imm(0, 0, 0x1F)
    a.bl("save_to_slot")

    # Populate dialog_buf[0] = tr.win
    a.bl("fmt_clear")
    a.ldr_imm(0, 8, 16) # tr.win str_off
    a.bl("fmt_rom_off")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")

    a.cmp_imm(7, 32)
    a.b("fbf_normal_tr_win", cond=0x1)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Welcome to the Hall of Flavor! The Eternal Pantry is now open!"))
    a.bl("fmt_str")
    a.mov_imm(0, 1)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 2); a.mov_imm(1, 4); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.pop([4, 5, 6, 7, 8, 15])

    a.label("fbf_normal_tr_win")
    a.mov_imm(0, 1); a.mov_imm(1, 1); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.pop([4, 5, 6, 7, 8, 15])

    a.label("fbf_chk_lose")
    a.cmp_imm(4, 2)
    a.b("fbf_to_ow", cond=0x1)
    a.bl("heal_party")
    a.mov_imm(5, 0x02000000)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x28)
    a.mov_imm(0, 11)
    a.strb_imm(0, 5, 0x29)
    a.mov_imm(0, 12)
    a.strb_imm(0, 5, 0x2A)

    a.label("fbf_to_ow")
    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 3)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45)
    a.bl("play_map_music")
    a.pop([4, 5, 6, 7, 8, 15])
    a.flush_literals()

    # grant_quest_reward(R0=qid 0..15)
    a.label("grant_quest_reward")
    a.push([4, 5, 14])
    a.mov_reg(4, 0)
    a.mov_imm(5, 0x02000000)
    rewards = [
        (0, 2, 3, 0),
        (1, 3, 2, 300),
        (2, None, 0, 500),
        (3, 4, 1, 0),
        (4, 18, 1, 400),
        (5, 6, 2, 350),
        (6, 15, 1, 500),
        (7, 7, 1, 600),
        (8, 4, 1, 0),
        (9, 5, 2, 0),
        (10, 10, 3, 0),
        (11, 1, 2, 0),
        (12, 16, 1, 0),
        (13, 8, 3, 0),
        (14, 9, 2, 0),
        (15, 7, 2, 2000),
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
    a.mov_imm(6, 0x02000000)
    a.ldrb_imm(4, 6, 0x2B)
    a.mov_imm(7, 0)
    a.mov_imm(8, 0)
    a.cmp_imm(4, 0); a.mov_imm(8, 1, cond=0x0)
    a.cmp_imm(4, 1); a.mvn_imm(8, 0, cond=0x0)
    a.cmp_imm(4, 2); a.mvn_imm(7, 0, cond=0x0)
    a.cmp_imm(4, 3); a.mov_imm(7, 1, cond=0x0)
    a.ldrb_imm(0, 6, 0x29)
    a.add_reg(7, 0, 7)
    a.ldrb_imm(0, 6, 0x2A)
    a.add_reg(8, 0, 8)

    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40)
    a.mul(0, 0, 1)
    a.mov_imm(9, table_addrs[10])
    a.add_reg(9, 9, 0)

    a.mov_reg(0, 9)
    a.mov_reg(1, 7)
    a.mov_reg(2, 8)
    a.bl("find_visible_npc_at")
    a.mov_reg(10, 0)
    a.cmp_imm(10, 0)
    a.b("ia_found_npc", cond=0x1)

    a.ldrb_imm(0, 9, 12)
    a.ldrb_imm(1, 9, 13)
    a.cmp_imm(7, 0); a.b("ia_ret", cond=0xB)
    a.cmp_reg(7, 0); a.b("ia_ret", cond=0x2)
    a.cmp_imm(8, 0); a.b("ia_ret", cond=0xB)
    a.cmp_reg(8, 1); a.b("ia_ret", cond=0x2)

    a.ldr_imm(2, 9, 20)
    a.mov_imm(3, table_addrs[10])
    a.add_reg(2, 3, 2)
    a.mul(0, 8, 0)
    a.add_reg(0, 0, 7)
    a.add_reg(0, 2, 0)
    a.ldrb_imm(4, 0, 0)
    a.cmp_imm(4, 3) # sign?
    a.b("ia_chk_water", cond=0x1)
    # Find sign at (tx=R7, ty=R8) in map.signs
    a.ldrb_imm(1, 9, 19) # signCount
    a.ldr_imm(2, 9, 36)  # sign_off
    a.mov_imm(3, table_addrs[10])
    a.add_reg(2, 3, 2)
    a.mov_imm(3, 0)
    a.label("ia_sign_loop")
    a.cmp_reg(3, 1)
    a.b("ia_sign_fallback", cond=0x2)
    a.ldrb_imm(0, 2, 0)
    a.ldrb_imm(4, 2, 1)
    a.cmp_reg(0, 7)
    a.cmp_reg(4, 8, cond=0x0)
    a.b("ia_sign_found", cond=0x0)
    a.add_imm(2, 2, 8)
    a.add_imm(3, 3, 1)
    a.b("ia_sign_loop")
    a.label("ia_sign_found")
    a.bl("fmt_clear")
    a.ldr_imm(0, 2, 4) # sign.text str_off
    a.bl("fmt_rom_off")
    a.b("ia_sign_show")
    a.label("ia_sign_fallback")
    a.bl("fmt_clear")
    a.ldr_imm(0, 9, 4) # map.name
    a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(" - Welcome to "))
    a.bl("fmt_str")
    a.ldr_imm(0, 9, 8) # map.region
    a.bl("fmt_rom_off")
    a.mov_imm(0, 33)
    a.bl("fmt_putc")
    a.label("ia_sign_show")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_water")
    a.cmp_imm(4, 13)
    a.cmp_imm(4, 25, cond=0x1)
    a.cmp_imm(4, 37, cond=0x1)
    a.cmp_imm(4, 49, cond=0x1)
    a.b("ia_ret", cond=0x1)
    a.ldrh_imm(0, 6, 0x7E + 23 * 2)
    a.cmp_imm(0, 0)
    a.b("ia_ret", cond=0x0)
    a.ldrb_imm(5, 9, 16)
    a.cmp_imm(5, 0)
    a.b("ia_ret", cond=0x0)
    a.bl("game_rng_next")
    a.umull(2, 3, 0, 5)
    a.ldr_imm(0, 9, 24)
    a.mov_imm(1, table_addrs[10])
    a.add_reg(0, 1, 0)
    a.add_reg(0, 0, 3, shift_imm=2, shift_type=0)
    a.ldr_imm(4, 0, 0)
    a.bl("game_rng_next")
    a.mov_reg(1, 4, shift_imm=8, shift_type=1); a.and_imm(1, 1, 0xFF)
    a.mov_reg(2, 4, shift_imm=16, shift_type=1); a.and_imm(2, 2, 0xFF)
    a.sub_reg(2, 2, 1); a.add_imm(2, 2, 1)
    a.umull(3, 5, 0, 2)
    a.add_reg(5, 1, 5)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("You dipped the Soup Ladle into the shimmering water..."))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_reg(3, 5)          # lv
    a.and_imm(2, 4, 0xFF)    # spId
    a.mov_imm(0, 1)
    a.mov_imm(1, 2)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_found_npc")
    a.ldrb_imm(0, 10, 12)
    a.cmp_imm(0, 1) # heal
    a.b("ia_act_shop", cond=0x1)
    a.bl("heal_party")
    a.mov_imm(0, 15)
    a.bl("play_music")
    a.ldrb_imm(4, 10, 20) # len(npc.lines)
    a.mov_reg(0, 10)
    a.mov_imm(1, 32)
    a.mov_reg(2, 4)
    a.mov_imm(3, 0)
    a.bl("copy_npc_lines_to_dialog")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("All your bEATsts are simmering at 100% HP and PP!"))
    a.bl("fmt_str")
    a.mov_reg(0, 4)
    a.bl("fmt_copy_to_dialog")
    a.add_imm(0, 4, 1)
    a.mov_imm(1, 1)
    a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_act_shop")
    a.cmp_imm(0, 2) # shop
    a.b("ia_act_cook", cond=0x1)
    a.mov_imm(0, 0x02001000)
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 0x28)
    a.mov_imm(1, 11)
    a.strb_imm(1, 0, 0x20)
    a.mov_imm(1, 1)
    a.strb_imm(1, 0, 0x45)
    a.b("ia_ret")

    a.label("ia_act_cook")
    a.cmp_imm(0, 3) # cook
    a.b("ia_act_cafe", cond=0x1)
    a.ldrh_imm(0, 6, 0x7E + 5 * 2)
    a.ldrh_imm(1, 6, 0x7E + 10 * 2)
    a.cmp_imm(0, 0)
    a.b("ia_cook_fail", cond=0x0)
    a.cmp_imm(1, 0)
    a.b("ia_cook_fail", cond=0x0)
    a.mov_imm(0, 5); a.mvn_imm(1, 0); a.bl("bag_add")
    a.mov_imm(0, 10); a.mvn_imm(1, 0); a.bl("bag_add")
    a.mov_imm(0, 6); a.mov_imm(1, 1); a.bl("bag_add")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Simmered Broth Cup + Garnish Treat into a fresh Hearty Stew!"))
    a.bl("fmt_str")
    a.b("ia_cook_show")
    a.label("ia_cook_fail")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Stove Chef: Bring 1 Broth Cup and 1 Garnish Treat to cook a Hearty Stew!"))
    a.bl("fmt_str")
    a.label("ia_cook_show")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_act_cafe")
    a.cmp_imm(0, 4) # cafe
    a.b("ia_act_sec151", cond=0x1)
    a.ldrb_imm(4, 6, 0x0B1) # boxCount
    a.cmp_imm(4, 0)
    a.b("ia_cafe_nonempty", cond=0x1)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("bEATst Cafe: Your stored bEATsts will relax here once your party is full!"))
    a.bl("fmt_str")
    a.b("ia_cafe_show")
    a.label("ia_cafe_nonempty")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("bEATst Cafe ("))
    a.bl("fmt_str")
    a.mov_reg(0, 4)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off(" resting): "))
    a.bl("fmt_str")
    a.cmp_imm(4, 4)
    a.mov_imm(5, 4, cond=0x8)
    a.mov_reg(5, 4, cond=0x9) # min(4, boxCount)
    a.mov_imm(7, 0)
    a.label("ia_cafe_lp")
    a.cmp_reg(7, 5)
    a.b("ia_cafe_lp_dn", cond=0x2)
    a.cmp_imm(7, 0)
    a.mov_imm(0, ui_off(", "), cond=0x1)
    a.bl("fmt_str", cond=0x1)
    a.mov_imm(0, 24)
    a.mul(0, 7, 0)
    a.mov_imm(1, 0x020001D4)
    a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 4) # BoxMon speciesId
    a.mov_imm(1, 255)
    a.bl("fmt_sp_name_n")
    a.add_imm(7, 7, 1)
    a.b("ia_cafe_lp")
    a.label("ia_cafe_lp_dn")
    a.mov_imm(0, ui_off(" are happily nibbling crumbs!"))
    a.bl("fmt_str")
    a.label("ia_cafe_show")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_act_sec151")
    a.cmp_imm(0, 5) # secret151
    a.b("ia_chk_qgive", cond=0x1)
    a.ldrb_imm(0, 6, 0x2E)
    a.ldrb_imm(1, 6, 0x2C)
    a.and_reg(0, 0, 1, s=1)
    a.b("ia_sec151_locked", cond=0x0)
    a.ldrh_imm(0, 6, 0x7E + 4 * 2)
    a.cmp_imm(0, 0)
    a.b("ia_sec151_locked", cond=0x0)
    a.ldrb_imm(0, 6, 0x6A + 18)
    a.tst_imm(0, 1 << 6)
    a.b("ia_sec151_locked", cond=0x1)
    a.ldrb_imm(1, 6, 0x0B0)
    a.add_imm(2, 6, 0x0B4)
    a.mov_imm(3, 0)
    a.mov_imm(4, 0)
    a.label("ia_fam_loop")
    a.cmp_reg(4, 1)
    a.b("ia_fam_done", cond=0x2)
    a.ldrb_imm(0, 2, 4)
    a.sub_imm(0, 0, 1)
    a.mov_imm(5, 56)
    a.mul(0, 0, 5)
    a.mov_imm(5, table_addrs[4])
    a.add_reg(0, 5, 0)
    a.ldrb_imm(0, 0, 1)
    a.mov_imm(5, 1)
    a.mov_reg_rs(5, 5, 0, shift_type=0)
    a.orr_reg(3, 3, 5)
    a.add_imm(2, 2, 48)
    a.add_imm(4, 4, 1)
    a.b("ia_fam_loop")
    a.label("ia_fam_done")
    a.cmp_imm(3, 0xF)
    a.b("ia_sec151_locked", cond=0x1)
    a.ldrh_imm(0, 6, 0x40)
    a.orr_imm(0, 0, 1)
    a.strh_imm(0, 6, 0x40)
    for l_i, s_txt in enumerate([
        "The Secret Pantry shimmers with golden steam...",
        "A luminous aroma unites Sandwich, Dumpling, Noodle, and Soup!",
        "The mythical #151 Consommyth emerges!"
    ]):
        a.bl("fmt_clear")
        a.mov_imm(0, ui_off(s_txt))
        a.bl("fmt_str")
        a.mov_imm(0, l_i)
        a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 3)
    a.mov_imm(1, 2)
    a.mov_imm(2, 151)
    a.mov_imm(3, 55)
    a.bl("show_dialog_n")
    a.b("ia_ret")
    a.label("ia_sec151_locked")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off('A locked golden pantry door. Inscription: "Only a Champion at Night bearing all 4 Food Families and a Royal Banquet Setting may enter."'))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_qgive")
    a.ldrb_imm(4, 10, 14)
    a.cmp_imm(4, 0xFF)
    a.b("ia_chk_qstep", cond=0x0)
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 4, shift_type=0)
    a.ldrh_imm(0, 6, 0x42)
    a.tst_reg(0, 1)
    a.b("ia_qgive_not_done", cond=0x0)
    a.bl("fmt_clear")
    a.ldr_imm(0, 10, 4) # npc.name
    a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": Thank you again for your help!"))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1)
    a.b("ia_qgive_show")
    a.label("ia_qgive_not_done")
    a.ldrh_imm(0, 6, 0x44)
    a.tst_reg(0, 1)
    a.b("ia_qgive_already_started", cond=0x1)
    a.orr_reg(0, 0, 1)
    a.strh_imm(0, 6, 0x44)
    a.add_reg(2, 6, 4)
    a.mov_imm(0, 0)
    a.strb_imm(0, 2, 0x46)
    a.label("ia_qgive_already_started")
    a.ldrb_imm(4, 10, 20)
    a.mov_reg(0, 10)
    a.mov_imm(1, 32)
    a.mov_reg(2, 4)
    a.mov_imm(3, 0)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4)
    a.label("ia_qgive_show")
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_qstep")
    a.ldrb_imm(4, 10, 15)
    a.cmp_imm(4, 0xFF)
    a.b("ia_chk_qcomp", cond=0x0)
    a.ldrb_imm(5, 10, 16)
    a.cmp_imm(5, 0)
    a.mov_imm(5, 1, cond=0x0)
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 4, shift_type=0)
    a.ldrh_imm(0, 6, 0x42)
    a.tst_reg(0, 1)
    a.b("ia_qstep_not_done", cond=0x0)
    a.bl("fmt_clear")
    a.ldr_imm(0, 10, 4)
    a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": That quest is already complete!"))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1)
    a.b("ia_qstep_show")
    a.label("ia_qstep_not_done")
    a.ldrh_imm(0, 6, 0x44)
    a.tst_reg(0, 1)
    a.b("ia_qstep_not_started", cond=0x0)
    a.add_reg(2, 6, 4)
    a.ldrb_imm(0, 2, 0x46)
    a.sub_imm(3, 5, 1)
    a.cmp_reg(0, 3)
    a.b("ia_qstep_missed", cond=0x3)
    a.strb_imm(5, 2, 0x46, cond=0x0)
    a.ldrb_imm(4, 10, 20)
    a.mov_reg(0, 10); a.mov_imm(1, 32); a.mov_reg(2, 4); a.mov_imm(3, 0)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4)
    a.b("ia_qstep_show")

    a.label("ia_qstep_not_started")
    a.ldrb_imm(4, 10, 23)
    a.and_imm(4, 4, 0xF)
    a.cmp_imm(4, 0)
    a.b("ia_qstep_has_nr", cond=0x1)
    a.bl("fmt_clear")
    a.ldr_imm(0, 10, 4); a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": You haven't started this errand yet!")); a.bl("fmt_str")
    a.mov_imm(0, 0); a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.b("ia_qstep_show")

    a.label("ia_qstep_missed")
    a.ldrb_imm(4, 10, 23)
    a.and_imm(4, 4, 0xF)
    a.cmp_imm(4, 0)
    a.b("ia_qstep_has_nr", cond=0x1)
    a.bl("fmt_clear")
    a.ldr_imm(0, 10, 4); a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": You missed an earlier stop on this quest!")); a.bl("fmt_str")
    a.mov_imm(0, 0); a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.b("ia_qstep_show")

    a.label("ia_qstep_has_nr")
    a.mov_reg(0, 10); a.mov_imm(1, 68); a.mov_reg(2, 4); a.mov_imm(3, 0)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4)
    a.label("ia_qstep_show")
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_qcomp")
    a.ldrb_imm(4, 10, 17)
    a.cmp_imm(4, 0xFF)
    a.b("ia_chk_sec", cond=0x0)
    a.mov_imm(0, 20)
    a.mul(0, 4, 0)
    a.mov_imm(1, table_addrs[12])
    a.add_reg(0, 1, 0)
    a.ldr_imm(5, 0, 8)
    a.sub_imm(5, 5, 1, s=1)
    a.mov_imm(5, 0, cond=0x4)

    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 4, shift_type=0)
    a.ldrh_imm(0, 6, 0x44)
    a.tst_reg(0, 1)
    a.b("ia_qcomp_not_started", cond=0x0)
    a.add_reg(2, 6, 4)
    a.ldrb_imm(0, 2, 0x46)
    a.cmp_reg(0, 5)
    a.b("ia_qcomp_not_ready", cond=0x3)
    a.ldrh_imm(0, 6, 0x42)
    a.orr_reg(0, 0, 1)
    a.strh_imm(0, 6, 0x42)
    a.mov_reg(0, 4)
    a.bl("grant_quest_reward")
    a.ldrb_imm(4, 10, 20)
    a.mov_reg(0, 10); a.mov_imm(1, 32); a.mov_reg(2, 4); a.mov_imm(3, 0)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_qcomp_not_started")
    a.ldrb_imm(4, 10, 22) # notStartedLines
    a.and_imm(4, 4, 0xF)
    a.cmp_imm(4, 0)
    a.b("ia_qcomp_use_ns", cond=0x1)
    a.ldrb_imm(4, 10, 23) # notReadyLines
    a.and_imm(4, 4, 0xF)
    a.cmp_imm(4, 0)
    a.b("ia_qcomp_use_nr", cond=0x1)
    a.bl("fmt_clear")
    a.ldr_imm(0, 10, 4); a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": Someone is looking for this, but you haven't taken their request yet!")); a.bl("fmt_str")
    a.mov_imm(0, 0); a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.b("ia_qcomp_show")

    a.label("ia_qcomp_use_ns")
    a.mov_reg(0, 10); a.mov_imm(1, 56); a.mov_reg(2, 4); a.mov_imm(3, 0)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4); a.b("ia_qcomp_show")

    a.label("ia_qcomp_not_ready")
    a.ldrb_imm(4, 10, 23)
    a.and_imm(4, 4, 0xF)
    a.cmp_imm(4, 0)
    a.b("ia_qcomp_use_nr", cond=0x1)
    a.bl("fmt_clear")
    a.ldr_imm(0, 10, 4); a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": You haven't completed all the earlier steps yet!")); a.bl("fmt_str")
    a.mov_imm(0, 0); a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.b("ia_qcomp_show")

    a.label("ia_qcomp_use_nr")
    a.mov_reg(0, 10); a.mov_imm(1, 68); a.mov_reg(2, 4); a.mov_imm(3, 0)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4)
    a.label("ia_qcomp_show")
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_sec")
    a.ldrb_imm(4, 10, 18)
    a.cmp_imm(4, 0xFF)
    a.b("ia_chk_trainer", cond=0x0)
    a.mov_imm(1, 1)
    a.mov_reg_rs(1, 1, 4, shift_type=0)
    a.ldrh_imm(0, 6, 0x40)
    a.tst_reg(0, 1)
    a.b("ia_sec_show", cond=0x1)
    a.orr_reg(0, 0, 1)
    a.strh_imm(0, 6, 0x40)
    a.ldr_imm(0, 6, 0x24)
    a.add_imm(0, 0, 150)
    a.str_imm(0, 6, 0x24)
    a.label("ia_sec_show")
    a.ldrb_imm(4, 10, 20)
    a.mov_reg(0, 10); a.mov_imm(1, 32); a.mov_reg(2, 4); a.mov_imm(3, 0)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_chk_trainer")
    a.ldrb_imm(4, 10, 19)
    a.cmp_imm(4, 0xFF)
    a.b("ia_normal_npc", cond=0x0)
    a.mov_imm(0, 48)
    a.mul(5, 4, 0)
    a.mov_imm(0, table_addrs[11])
    a.add_reg(5, 0, 5) # R5 = trainer_rom_ptr
    a.mov_reg(0, 4, shift_imm=3, shift_type=1)
    a.and_imm(1, 4, 7)
    a.mov_imm(2, 1)
    a.mov_reg_rs(2, 2, 1, shift_type=0)
    a.add_reg(0, 6, 0)
    a.ldrb_imm(0, 0, 0x38)
    a.tst_reg(0, 2)
    a.b("ia_tr_defeated", cond=0x1)
    # Not defeated: "${tr.name}: ${tr.intro}"
    a.bl("fmt_clear")
    a.ldr_imm(0, 5, 4) # tr.name
    a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": "))
    a.bl("fmt_str")
    a.ldr_imm(0, 5, 12) # tr.intro
    a.bl("fmt_rom_off")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 3); a.mov_reg(2, 4); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")
    a.label("ia_tr_defeated")
    # Defeated: "${tr.name}: ${tr.after || tr.win}"
    a.bl("fmt_clear")
    a.ldr_imm(0, 5, 4)
    a.bl("fmt_rom_off")
    a.mov_imm(0, ui_off(": "))
    a.bl("fmt_str")
    a.ldr_imm(0, 5, 20) # tr.after
    a.cmn_imm(0, 1)
    a.ldr_imm(0, 5, 16, cond=0x0) # fallback tr.win
    a.bl("fmt_rom_off")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_normal_npc")
    # Check if Brotholomew (npc_global_idx == 256) and all 151 caught using ONLY byte access (ldrb_imm)!
    a.ldrh_imm(0, 10, 24)
    a.cmp_imm(0, 256)
    a.b("ia_not_broth_151", cond=0x1)
    a.mov_imm(1, 0)
    a.label("ia_broth_loop")
    a.add_reg(2, 6, 1)
    a.ldrb_imm(0, 2, 0x6A)
    a.cmp_imm(0, 0xFF)
    a.b("ia_not_broth_151", cond=0x1)
    a.add_imm(1, 1, 1)
    a.cmp_imm(1, 18)
    a.b("ia_broth_loop", cond=0x3)
    a.ldrb_imm(0, 6, 0x6A + 18)
    a.and_imm(0, 0, 0x7F)
    a.cmp_imm(0, 0x7F)
    a.b("ia_not_broth_151", cond=0x1)
    # Brotholomew 151/151 2-line diploma dialogue!
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Chef Brotholomew: 151/151!! You have befriended every bEATst in Pantrylia!"))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Accept the Grand Culinary Diploma of ConsciousNode!"))
    a.bl("fmt_str")
    a.mov_imm(0, 1)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 2); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("ia_ret")

    a.label("ia_not_broth_151")
    a.ldrb_imm(0, 6, 0x2C) # isNight
    a.ldrb_imm(1, 10, 21)  # len(nlines) | (has_nlines << 4)
    a.cmp_imm(0, 0)
    a.b("ia_use_day_lines", cond=0x0)
    a.tst_imm(1, 0x10)
    a.b("ia_use_day_lines", cond=0x0)
    a.and_imm(4, 1, 0xF)
    a.mov_reg(0, 10); a.mov_imm(1, 44); a.mov_reg(2, 4); a.mov_imm(3, 1)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4)
    a.b("ia_show_norm")
    a.label("ia_use_day_lines")
    a.ldrb_imm(4, 10, 20)
    a.mov_reg(0, 10); a.mov_imm(1, 32); a.mov_reg(2, 4); a.mov_imm(3, 1)
    a.bl("copy_npc_lines_to_dialog")
    a.mov_reg(0, 4)
    a.label("ia_show_norm")
    a.cmp_imm(0, 0)
    a.mov_imm(0, 1, cond=0x0)
    a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")

    a.label("ia_ret")
    a.pop([4, 5, 6, 7, 8, 9, 10, 15])
    a.flush_literals()

    # press_button(R0=btn: 0=A, 1=B, 2=SELECT, 3=START, 4=RIGHT, 5=LEFT, 6=UP, 7=DOWN, 8=R, 9=L)
    a.label("press_button")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.sub_imm(13, 13, 32)
    a.mov_reg(4, 0)
    a.mov_imm(5, 0x02001000)
    a.mov_imm(6, 0x02000000)
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x45)
    a.ldrb_imm(7, 5, 0x20)

    # Screen 0: TITLE
    a.cmp_imm(7, 0)
    a.b("pb_chk_slots", cond=0x1)
    a.mov_imm(0, 0); a.bl("play_music")
    a.ldrb_imm(8, 5, 0x21)
    a.cmp_imm(4, 6)
    a.add_imm(8, 8, 2, cond=0x0); a.b("pb_title_mod", cond=0x0)
    a.cmp_imm(4, 7)
    a.add_imm(8, 8, 1, cond=0x0); a.b("pb_title_mod", cond=0x0)
    a.cmp_imm(4, 0); a.cmp_imm(4, 3, cond=0x1)
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(8, 0); a.mov_imm(0, 1, cond=0x0)
    a.cmp_imm(8, 1); a.mov_imm(0, 13, cond=0x0)
    a.cmp_imm(8, 2); a.mov_imm(0, 14, cond=0x0)
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
    a.ldrb_imm(8, 5, 0x21)
    a.cmp_imm(4, 6)
    a.add_imm(8, 8, 2, cond=0x0); a.b("pb_title_mod", cond=0x0)
    a.cmp_imm(4, 7)
    a.add_imm(8, 8, 1, cond=0x0); a.b("pb_title_mod", cond=0x0)
    a.cmp_imm(4, 1)
    a.mov_imm(0, 0, cond=0x0)
    a.strb_imm(0, 5, 0x20, cond=0x0)
    a.strb_imm(0, 5, 0x21, cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 0); a.cmp_imm(4, 3, cond=0x1)
    a.b("pb_ret", cond=0x1)
    a.mov_reg(0, 8)
    a.bl("load_from_slot")
    a.cmp_imm(0, 0)
    a.b("pb_ret", cond=0x1)
    a.strb_imm(8, 5, 0x1F)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x2A)
    a.mov_imm(0, 2)
    a.strb_imm(0, 5, 0x20)
    a.b("pb_ret")

    # Screen 2: STARTER
    a.label("pb_chk_starter")
    a.cmp_imm(7, 2)
    a.b("pb_chk_name_entry", cond=0x1)
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1)
    a.b("pb_st_lr", cond=0x1)
    a.ldrb_imm(0, 5, 0x2B)
    a.cmp_imm(4, 7)
    a.add_imm(0, 0, 1, cond=0x0)
    a.add_imm(0, 0, 2, cond=0x1)
    a.mov_imm(1, 3); a.bl("udiv32")
    a.strb_imm(1, 5, 0x2B)
    a.b("pb_ret")
    a.label("pb_st_lr")
    a.cmp_imm(4, 4); a.cmp_imm(4, 5, cond=0x1)
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
    a.cmp_imm(4, 3); a.cmp_imm(4, 2, cond=0x1)
    a.b("pb_st_ab", cond=0x1)
    a.mov_imm(0, 16)
    a.strb_imm(0, 5, 0x20)
    a.b("pb_ret")
    a.label("pb_st_ab")
    a.cmp_imm(4, 1)
    a.mov_imm(0, 1, cond=0x0)
    a.strb_imm(0, 5, 0x20, cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 0)
    a.b("pb_ret", cond=0x1)
    a.ldrb_imm(1, 5, 0x2A)
    a.mov_imm(2, 38)
    a.mul(1, 1, 2)
    a.add_imm(1, 1, 1)
    a.ldrb_imm(0, 5, 0x1F)
    a.mov_imm(2, 4242)
    a.bl("start_new_game")
    a.b("pb_ret")

    # Screen 16: NAME_ENTRY
    a.label("pb_chk_name_entry")
    a.cmp_imm(7, 16)
    a.b("pb_chk_dialog", cond=0x1)
    a.add_imm(8, 5, 0x90)
    a.ldrb_imm(0, 8, 0)
    a.ldrb_imm(1, 8, 1)
    a.cmp_imm(4, 4)
    a.add_imm(0, 0, 1, cond=0x0); a.cmp_imm(0, 10, cond=0x0); a.mov_imm(0, 0, cond=0x2); a.strb_imm(0, 8, 0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 5)
    a.sub_imm(0, 0, 1, s=1, cond=0x0); a.mov_imm(0, 9, cond=0x4); a.strb_imm(0, 8, 0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 7)
    a.add_imm(1, 1, 1, cond=0x0); a.and_imm(1, 1, 3, cond=0x0); a.strb_imm(1, 8, 1); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 6)
    a.sub_imm(1, 1, 1, cond=0x0); a.and_imm(1, 1, 3, cond=0x0); a.strb_imm(1, 8, 1); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 9)
    a.ldrb_imm(2, 8, 2, cond=0x0); a.eor_imm(2, 2, 1, cond=0x0); a.strb_imm(2, 8, 2, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 3); a.cmp_imm(4, 8, cond=0x1)
    a.mov_imm(0, 2, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 1)
    a.b("pb_ne_a", cond=0x1)
    a.ldrb_imm(2, 8, 3)
    a.cmp_imm(2, 0)
    a.b("pb_ret", cond=0x0)
    a.sub_imm(2, 2, 1)
    a.strb_imm(2, 8, 3)
    a.add_reg(3, 8, 2)
    a.mov_imm(0, 0)
    a.strb_imm(0, 3, 4)
    a.b("pb_ret")
    a.label("pb_ne_a")
    a.cmp_imm(4, 0)
    a.b("pb_ret", cond=0x1)
    a.mov_imm(2, 10)
    a.mul(2, 1, 2)
    a.add_reg(2, 2, 0)
    a.cmp_imm(2, 39)
    a.mov_imm(0, 2, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.ldrb_imm(3, 8, 3)
    a.cmp_imm(3, 10)
    a.b("pb_ret", cond=0x2)
    a.mov_imm(0, 32)
    a.cmp_imm(2, 26)
    a.b("pb_ne_digit", cond=0x2)
    a.ldrb_imm(1, 8, 2)
    a.cmp_imm(1, 0)
    a.add_imm(0, 2, 97, cond=0x0)
    a.add_imm(0, 2, 65, cond=0x1)
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
    a.cmp_imm(4, 0); a.cmp_imm(4, 1, cond=0x1)
    a.b("pb_ret", cond=0x1)
    a.ldrb_imm(0, 5, 0x41)
    a.ldrb_imm(1, 5, 0x40)
    a.add_imm(0, 0, 1)
    a.cmp_reg(0, 1)
    a.strb_imm(0, 5, 0x41, cond=0x3)
    a.b("pb_ret", cond=0x3)
    a.mov_imm(0, 3)
    a.strb_imm(0, 5, 0x20)
    a.ldrb_imm(1, 5, 0x42)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x42)
    a.cmp_imm(1, 1)
    a.bl("play_map_music", cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(1, 2)
    a.b("pb_dlg_cb3", cond=0x1)
    a.ldrb_imm(0, 5, 0x43)
    a.ldrb_imm(1, 5, 0x44)
    a.bl("start_wild_battle")
    a.b("pb_ret")
    a.label("pb_dlg_cb3")
    a.cmp_imm(1, 3)
    a.b("pb_dlg_cb4", cond=0x1)
    a.ldrb_imm(0, 5, 0x43)
    a.bl("start_trainer_battle")
    a.b("pb_ret")
    a.label("pb_dlg_cb4")
    a.cmp_imm(1, 4)
    a.b("pb_ret", cond=0x1)
    a.mov_imm(0, 0)
    a.strh_imm(0, 5, 0x36) # credits_scroll_sub = 0
    a.strh_imm(0, 5, 0x38) # credits_scroll_px = 0
    a.mov_imm(0, 15)
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 17)
    a.bl("play_music")
    a.b("pb_ret")

    # Screen 12: LEARN_MOVE
    a.label("pb_chk_learn")
    a.cmp_imm(7, 12)
    a.b("pb_chk_ow", cond=0x1)
    a.ldrb_imm(8, 5, 0x29)
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1)
    a.b("pb_lm_ab", cond=0x1)
    a.cmp_imm(4, 7)
    a.add_imm(0, 8, 1, cond=0x0)
    a.add_imm(0, 8, 4, cond=0x1)
    a.mov_imm(1, 5); a.bl("udiv32")
    a.strb_imm(1, 5, 0x29)
    a.b("pb_ret")
    a.label("pb_lm_ab")
    a.cmp_imm(4, 1)
    a.b("pb_lm_a", cond=0x1)
    a.ldrb_imm(0, 5, 0x3F)
    a.strb_imm(0, 5, 0x20)
    a.mov_imm(0, 0); a.strb_imm(0, 5, 0x3C)
    a.b("pb_ret")
    a.label("pb_lm_a")
    a.cmp_imm(4, 0)
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(8, 4)
    a.b("pb_lm_done", cond=0x2)
    a.ldrb_imm(0, 5, 0x3D)
    a.mov_imm(1, 48)
    a.mul(0, 0, 1)
    a.add_imm(0, 6, 0x0B4)
    a.add_reg(0, 0, 8)
    a.ldrb_imm(1, 5, 0x3E)
    a.strb_imm(1, 0, 0x1C)
    a.mov_imm(2, 36)
    a.mul(2, 1, 2)
    a.mov_imm(3, table_addrs[3])
    a.add_reg(2, 3, 2)
    a.ldrb_imm(2, 2, 4)
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
    a.cmp_imm(4, 2) # SELECT -> toggle Day/Night
    a.b("pb_ow_a", cond=0x1)
    a.ldrb_imm(8, 6, 0x2C)
    a.eor_imm(8, 8, 1)
    a.strb_imm(8, 6, 0x2C)
    a.bl("fmt_clear")
    a.cmp_imm(8, 0)
    a.mov_imm(0, ui_off("Time shifted to Daytime (Sunny)!"), cond=0x0)
    a.mov_imm(0, ui_off("Time shifted to Nighttime (Starlight)!"), cond=0x1)
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
    a.mov_imm(0, 1); a.mov_imm(1, 0); a.mov_imm(2, 0); a.mov_imm(3, 0)
    a.bl("show_dialog_n")
    a.b("pb_ret")
    a.label("pb_ow_a")
    a.cmp_imm(4, 0)
    a.bl("interact_ahead", cond=0x0)
    a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 6); a.mov_imm(0, 1, cond=0x0); a.b("pb_ow_move", cond=0x0)
    a.cmp_imm(4, 7); a.mov_imm(0, 0, cond=0x0); a.b("pb_ow_move", cond=0x0)
    a.cmp_imm(4, 5); a.mov_imm(0, 2, cond=0x0); a.b("pb_ow_move", cond=0x0)
    a.cmp_imm(4, 4); a.mov_imm(0, 3, cond=0x0); a.b("pb_ow_move", cond=0x0)
    a.b("pb_ret")
    a.label("pb_ow_move")
    a.mov_imm(1, 0)
    a.bl("try_move")
    a.ldrb_imm(1, 5, 0x20)
    a.cmp_imm(1, 3)
    a.mov_imm(0, 8, cond=0x0)
    a.mov_imm(0, 9, cond=0x1)
    a.strb_imm(0, 5, 0x2D)
    a.mov_imm(0, 9)
    a.strb_imm(0, 5, 0x50)
    a.b("pb_ret")

    # Screen 6: MENU
    a.label("pb_chk_menu")
    a.cmp_imm(7, 6)
    a.b("pb_chk_dex", cond=0x1)
    a.ldrb_imm(8, 5, 0x22)
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1)
    a.b("pb_menu_bs", cond=0x1)
    a.cmp_imm(4, 7)
    a.add_imm(8, 8, 1, cond=0x0)
    a.add_imm(8, 8, 7, cond=0x1)
    a.and_imm(8, 8, 7)
    a.strb_imm(8, 5, 0x22)
    a.b("pb_ret")
    a.label("pb_menu_bs")
    a.cmp_imm(4, 1); a.cmp_imm(4, 3, cond=0x1)
    a.mov_imm(0, 3, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 0)
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(8, 0); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x25, cond=0x0); a.mov_imm(0, 8, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 1); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x23, cond=0x0); a.strb_imm(0, 5, 0x24, cond=0x0); a.mov_imm(0, 7, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 2); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x26, cond=0x0); a.mov_imm(0, 9, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 3); a.mov_imm(0, 0, cond=0x0); a.strb_imm(0, 5, 0x27, cond=0x0); a.mov_imm(0, 10, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.cmp_imm(8, 4)
    a.b("pb_menu_opt", cond=0x1)
    a.ldrb_imm(8, 5, 0x1F)
    a.mov_reg(0, 8)
    a.bl("save_to_slot")
    # "Saved Slot ${this.activeSlot + 1} (${this.state.name})!"
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Saved Slot "))
    a.bl("fmt_str")
    a.add_imm(0, 8, 1)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off(" ("))
    a.bl("fmt_str")
    a.add_imm(0, 6, 0x0C) # state.name
    a.bl("fmt_str")
    a.mov_imm(0, ui_off(")!"))
    a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.bl("fmt_copy_to_dialog")
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
    a.cmp_imm(4, 1)
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.ldrb_imm(0, 6, 0x56 + 18)
    a.ldrb_imm(1, 6, 0x6A + 18)
    a.orr_reg(0, 0, 1)
    a.tst_imm(0, 1 << 6)
    a.mov_imm(9, 150, cond=0x0)
    a.mov_imm(9, 151, cond=0x1)
    a.sub_imm(9, 9, 1)
    a.ldrb_imm(8, 5, 0x23)
    a.cmp_imm(4, 6) # UP (-1)
    a.b("pb_dex_not_up", cond=0x1)
    a.sub_imm(8, 8, 1, s=1)
    a.mov_imm(8, 0, cond=0x4)
    a.b("pb_dex_clamp")
    a.label("pb_dex_not_up")
    a.cmp_imm(4, 7) # DOWN (+1)
    a.add_imm(8, 8, 1, cond=0x0)
    a.b("pb_dex_clamp", cond=0x0)
    a.cmp_imm(4, 5) # LEFT (-10)
    a.cmp_imm(4, 9, cond=0x1) # or L (-10)
    a.b("pb_dex_not_left", cond=0x1)
    a.sub_imm(8, 8, 10, s=1)
    a.mov_imm(8, 0, cond=0x4)
    a.b("pb_dex_clamp")
    a.label("pb_dex_not_left")
    if control_mode != "no_dex_page":
        a.cmp_imm(4, 4) # RIGHT (+10)
        a.cmp_imm(4, 8, cond=0x1) # or R (+10)
        a.add_imm(8, 8, 10, cond=0x0)
    a.label("pb_dex_clamp")
    a.cmp_reg(8, 9)
    a.mov_reg(8, 9, cond=0x8)
    a.strb_imm(8, 5, 0x23)
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
    a.cmp_imm(4, 1)
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.ldrb_imm(8, 5, 0x25)
    a.ldrb_imm(9, 6, 0x0B0)
    a.sub_imm(9, 9, 1)
    a.cmp_imm(4, 6)
    a.sub_imm(8, 8, 1, s=1, cond=0x0); a.mov_imm(8, 0, cond=0x4); a.strb_imm(8, 5, 0x25); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 7)
    a.add_imm(8, 8, 1, cond=0x0); a.cmp_reg(8, 9, cond=0x0); a.mov_reg(8, 9, cond=0x8); a.strb_imm(8, 5, 0x25); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 0)
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(8, 0)
    a.b("pb_ret", cond=0x0)
    a.mov_imm(0, 48)
    a.mul(0, 8, 0)
    a.add_imm(1, 6, 0x0B4)
    a.add_reg(2, 1, 0)
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
    a.cmp_imm(4, 1)
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.ldrb_imm(8, 5, 0x26)
    a.ldrb_imm(9, 6, 0x0B1)
    a.cmp_imm(4, 6)
    a.sub_imm(8, 8, 1, s=1, cond=0x0); a.mov_imm(8, 0, cond=0x4); a.strb_imm(8, 5, 0x26); a.b("pb_ret", cond=0x0)
    a.cmp_imm(4, 7)
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
    a.cmp_imm(4, 0)
    a.b("pb_ret", cond=0x1)
    a.cmp_imm(9, 0)
    a.b("pb_ret", cond=0x0)
    a.ldrb_imm(0, 6, 0x0B0)
    a.cmp_imm(0, 6)
    a.b("pb_ret", cond=0x2)
    a.mov_imm(1, 48)
    a.mul(1, 0, 1)
    a.add_imm(0, 0, 1)
    a.strb_imm(0, 6, 0x0B0)
    a.add_imm(1, 1, 0x0B4)
    a.add_reg(1, 6, 1)
    a.mov_imm(2, 24)
    a.mul(2, 8, 2)
    a.mov_imm(3, 0x020001D4)
    a.add_reg(2, 3, 2)

    a.mov_imm(0, 0)
    for off in range(0, 48, 4):
        a.str_imm(0, 1, off)
    a.ldr_imm(0, 2, 0x00); a.str_imm(0, 1, 0x00)
    a.ldr_imm(0, 2, 0x04); a.str_imm(0, 1, 0x04)
    a.mov_imm(0, 0xFF); a.strb_imm(0, 1, 0x07)
    a.ldrb_imm(0, 2, 0x07); a.strh_imm(0, 1, 0x12)
    a.ldr_imm(0, 2, 0x08); a.str_imm(0, 1, 0x08)
    a.ldr_imm(0, 2, 0x0C); a.str_imm(0, 1, 0x0C)
    a.ldrh_imm(0, 2, 0x10); a.strh_imm(0, 1, 0x10)
    a.ldrh_imm(0, 2, 0x12); a.mov_reg(0, 0, shift_imm=3, shift_type=0); a.str_imm(0, 1, 0x14)
    a.ldrb_imm(0, 2, 0x05); a.add_imm(0, 0, 1); a.mul(0, 0, 0); a.mov_reg(0, 0, shift_imm=3, shift_type=0); a.str_imm(0, 1, 0x18)
    a.ldr_imm(0, 2, 0x14); a.str_imm(0, 1, 0x1C)
    for m_i in range(4):
        a.ldrb_imm(0, 1, 0x1C + m_i)
        a.cmp_imm(0, 0xFF)
        a.b(f"pb_box_mv_{m_i}", cond=0x0)
        a.mov_imm(3, 36)
        a.mul(0, 0, 3)
        a.mov_imm(3, table_addrs[3])
        a.add_reg(0, 3, 0)
        a.ldrb_imm(0, 0, 4)
        a.strb_imm(0, 1, 0x20 + m_i)
        a.strb_imm(0, 1, 0x24 + m_i)
        a.label(f"pb_box_mv_{m_i}")

    a.sub_imm(9, 9, 1)
    a.strb_imm(9, 6, 0x0B1)
    a.mov_reg(0, 8)
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
    a.cmp_imm(4, 1)
    a.mov_imm(0, 6, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.mov_imm(0, 0)
    a.mov_reg(1, 13)
    a.bl("build_bag_filter")
    a.mov_reg(9, 0)
    a.cmp_imm(9, 0)
    a.b("pb_ret", cond=0x0)
    a.ldrb_imm(8, 5, 0x27)
    a.cmp_imm(4, 6); a.cmp_imm(4, 7, cond=0x1)
    a.b("pb_bag_a", cond=0x1)
    a.cmp_imm(4, 7)
    a.add_imm(0, 8, 1, cond=0x0)
    a.add_reg(0, 8, 9, cond=0x1)
    a.sub_imm(0, 0, 1, cond=0x1)
    a.mov_reg(1, 9); a.bl("udiv32")
    a.strb_imm(1, 5, 0x27)
    a.b("pb_ret")
    a.label("pb_bag_a")
    a.cmp_imm(4, 0)
    a.b("pb_ret", cond=0x1)
    a.add_reg(0, 13, 8)
    a.ldrb_imm(7, 0, 0)
    a.mov_imm(0, 28)
    a.mul(0, 7, 0)
    a.mov_imm(1, table_addrs[8])
    a.add_reg(8, 1, 0)
    a.add_imm(9, 6, 0x0B4)
    a.ldrb_imm(0, 8, 0)
    a.cmp_imm(0, 1); a.cmp_imm(0, 2, cond=0x1)
    a.b("pb_bag_recipe", cond=0x1)
    a.ldrh_imm(1, 9, 0x08)
    a.cmp_imm(1, 0)
    a.b("pb_ret", cond=0x0)
    a.ldrh_imm(2, 9, 0x0A)
    a.ldrh_imm(3, 8, 2)
    a.add_reg(1, 1, 3)
    a.cmp_reg(1, 2)
    a.mov_reg(1, 2, cond=0x8)
    a.strh_imm(1, 9, 0x08)
    a.cmp_imm(0, 2)
    a.cmp_imm(7, 7, cond=0x1)
    a.mov_imm(1, 0, cond=0x0)
    a.strb_imm(1, 9, 0x06, cond=0x0)
    a.mov_reg(0, 7); a.mvn_imm(1, 0); a.bl("bag_add")
    a.b("pb_ret")

    a.label("pb_bag_recipe")
    a.cmp_imm(0, 5)
    a.b("pb_ret", cond=0x1)
    a.mov_reg(0, 7); a.mvn_imm(1, 0); a.bl("bag_add")
    a.ldrh_imm(7, 8, 4)
    a.ldrh_imm(1, 9, 0x12)
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
    a.mov_imm(0, 1); a.strb_imm(0, 5, 0x3C)
    a.mov_imm(0, 0); a.strb_imm(0, 5, 0x3D)
    a.strb_imm(7, 5, 0x3E)
    a.mov_imm(0, 10); a.strb_imm(0, 5, 0x3F)
    a.mov_imm(0, 0); a.strb_imm(0, 5, 0x29)
    a.mov_imm(0, 12); a.strb_imm(0, 5, 0x20)
    a.b("pb_ret")

    # Screen 11: SHOP
    a.label("pb_chk_shop")
    a.cmp_imm(7, 11)
    a.b("pb_chk_battle", cond=0x1)
    a.cmp_imm(4, 1)
    a.mov_imm(0, 3, cond=0x0); a.strb_imm(0, 5, 0x20, cond=0x0); a.b("pb_ret", cond=0x0)
    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(0, 1, 0)
    a.ldr_imm(2, 0, 8)
    a.mov_imm(7, table_addrs[9])
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
    a.ldr_imm(9, 7, 8)
    a.ldrb_imm(8, 5, 0x28)
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
    a.cmp_imm(4, 0)
    a.b("pb_ret", cond=0x1)
    a.add_reg(0, 7, 8)
    a.ldrb_imm(7, 0, 12)
    a.mov_imm(0, 28); a.mul(0, 7, 0); a.mov_imm(1, table_addrs[8]); a.add_reg(0, 1, 0)
    a.ldrh_imm(1, 0, 6)
    a.ldr_imm(2, 6, 0x24)
    a.cmp_reg(2, 1)
    a.b("pb_ret", cond=0x3)
    a.sub_reg(2, 2, 1)
    a.str_imm(2, 6, 0x24)
    a.mov_reg(0, 7); a.mov_imm(1, 1); a.bl("bag_add")
    a.b("pb_ret")

    # Screen 5: BATTLE
    a.label("pb_chk_battle")
    a.cmp_imm(7, 5)
    a.b("pb_chk_opt", cond=0x1)
    a.mov_imm(8, 0x02001100)
    a.ldrb_imm(0, 8, 8)
    a.ldrb_imm(1, 8, 0x0A)
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
    a.ldrb_imm(8, 5, 0x21)
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
    a.ldrb_imm(0, 5, 0x2E)
    a.cmp_imm(4, 4); a.add_imm(0, 0, 1, cond=0x0); a.sub_imm(0, 0, 1, cond=0x1)
    a.cmp_imm(0, 1); a.mov_imm(0, 1, cond=0x3)
    a.cmp_imm(0, 3); a.mov_imm(0, 3, cond=0x8)
    a.strb_imm(0, 5, 0x2E)
    a.b("pb_ret")
    a.label("pb_opt_vol")
    a.cmp_imm(8, 1)
    a.b("pb_ret", cond=0x1)
    a.ldrb_imm(0, 5, 0x2F)
    a.cmp_imm(4, 4); a.add_imm(0, 0, 10, cond=0x0); a.sub_imm(0, 0, 10, s=1, cond=0x1)
    a.mov_imm(0, 0, cond=0x4)
    a.cmp_imm(0, 100); a.mov_imm(0, 100, cond=0x8)
    a.strb_imm(0, 5, 0x2F)
    a.b("pb_ret")
    a.label("pb_opt_ab")
    a.cmp_imm(4, 1)
    a.b("pb_opt_back", cond=0x0)
    a.cmp_imm(4, 0); a.cmp_imm(8, 2, cond=0x0)
    a.b("pb_ret", cond=0x1)
    a.label("pb_opt_back")
    a.ldrb_imm(0, 5, 0x1E)
    a.cmp_imm(0, 0)
    a.mov_imm(0, 0, cond=0x0)
    a.mov_imm(0, 6, cond=0x1)
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
    a.mov_imm(0, 3)
    a.strb_imm(0, 5, 0x20)
    a.bl("play_map_music")

    a.label("pb_ret")
    a.add_imm(13, 13, 32)
    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # =========================================================================
    # Full Pixel-Exact GBA Hardware Renderer (BG0 8bpp Canvas + OBJs + BG1 Map)
    # =========================================================================
    # set_px_vram(R0=x, R1=y, R2=col)
    a.label("iwram_code_start")
    # get_row_base_vram(R1=y) -> R6 = 0x06000040 + (y>>3)*1920 + (y&7)*8 (clobbers R0)
    a.label("iw_get_row_base_vram")
    a.mov_reg(0, 1, shift_imm=3, shift_type=1)
    a.mov_reg(6, 0, shift_imm=11, shift_type=0)
    a.sub_reg(6, 6, 0, shift_imm=7, shift_type=0)
    a.and_imm(0, 1, 7)
    a.add_reg(6, 6, 0, shift_imm=3, shift_type=0)
    a.add_imm(6, 6, 0x40)
    a.add_imm(6, 6, 0x06000000)
    a.bx(14)

    # set_px_on_row_vram(R0=x, R2=col, R6=row_base) (clobbers R1, R12)
    a.label("iw_set_px_on_row_vram")
    a.cmp_imm(0, 240); a.bx(14, cond=0x2)
    a.bic_imm(12, 0, 7)
    a.and_imm(1, 0, 6)
    a.add_reg(1, 1, 12, shift_imm=3, shift_type=0)
    a.add_reg(1, 6, 1)
    a.ldrh_imm(12, 1, 0)
    a.tst_imm(0, 1)
    a.bic_imm(12, 12, 0x00FF, cond=0x0)
    a.orr_reg(12, 12, 2, cond=0x0)
    a.and_imm(12, 12, 0x00FF, cond=0x1)
    a.orr_reg(12, 12, 2, shift_imm=8, shift_type=0, cond=0x1)
    a.strh_imm(12, 1, 0)
    a.bx(14)

    a.label("iw_set_px_vram")
    a.cmp_imm(0, 240)
    a.bx(14, cond=0x2)
    a.cmp_imm(1, 160)
    a.bx(14, cond=0x2)
    a.push([3, 4, 14])
    a.mov_reg(3, 1, shift_imm=3, shift_type=1) # ty = y >> 3
    a.mov_reg(4, 3, shift_imm=11, shift_type=0)
    a.sub_reg(4, 4, 3, shift_imm=7, shift_type=0) # ty * 1920
    a.and_imm(3, 1, 7)
    a.add_reg(4, 4, 3, shift_imm=3, shift_type=0)
    a.bic_imm(3, 0, 7)
    a.add_reg(4, 4, 3, shift_imm=3, shift_type=0)
    a.and_imm(3, 0, 6)
    a.add_reg(4, 4, 3)
    a.add_imm(4, 4, 0x40)
    a.add_imm(4, 4, 0x06000000)
    a.ldrh_imm(3, 4, 0)
    a.tst_imm(0, 1)
    a.bic_imm(3, 3, 0xFF, cond=0x0)
    a.orr_reg(3, 3, 2, cond=0x0)
    a.and_imm(3, 3, 0xFF, cond=0x1)
    a.orr_reg(3, 3, 2, shift_imm=8, shift_type=0, cond=0x1)
    a.strh_imm(3, 4, 0)
    a.pop([3, 4, 15])

    # fill_rect_vram(R0=x, R1=y, R2=w, R3=h, R4=col)
    a.label("iw_fill_rect_vram")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.sub_imm(13, 13, 8)
    a.cmp_imm(2, 0)
    a.b("frv_done", cond=0xD) # BLE
    a.cmp_imm(3, 0)
    a.b("frv_done", cond=0xD)
    a.mov_reg(8, 0)          # x0
    a.mov_reg(9, 1)          # ry = y0
    a.add_reg(10, 0, 2)      # x_end
    a.add_reg(11, 1, 3)      # y_end
    a.cmp_imm(8, 0); a.mov_imm(8, 0, cond=0xB)
    a.cmp_imm(9, 0); a.mov_imm(9, 0, cond=0xB)
    a.cmp_imm(10, 240); a.mov_imm(10, 240, cond=0xC)
    a.cmp_imm(11, 160); a.mov_imm(11, 160, cond=0xC)
    a.and_imm(4, 4, 0xFF)
    a.orr_reg(7, 4, 4, shift_imm=8, shift_type=0)  # col16
    a.orr_reg(7, 7, 7, shift_imm=16, shift_type=0) # col32
    a.mov_imm(0, 0)
    a.str_imm(0, 13, 0) # [SP+0] = dma_strip_active = 0
    a.str_imm(7, 13, 4) # [SP+4] = col32 for DMA3 source

    # Fast path: full screen (0, 0, 240, 160) -> single DMA3 transfer of 9600 words!
    a.cmp_imm(8, 0)
    a.cmp_imm(9, 0, cond=0x0)
    a.b("frv_y_loop", cond=0x1)
    a.cmp_imm(10, 240)
    a.cmp_imm(11, 160, cond=0x0)
    a.b("frv_y_loop", cond=0x1)
    a.add_imm(0, 13, 4)
    a.mov_imm(1, 0x040000D4)
    a.str_imm(0, 1, 0)
    a.mov_imm(0, 0x06000040)
    a.str_imm(0, 1, 4)
    a.mov_imm(0, 0x85000000 | 9600)
    a.str_imm(0, 1, 8)
    a.b("frv_done")

    a.label("frv_y_loop")
    a.cmp_reg(9, 11)
    a.b("frv_done", cond=0xA) # BGE
    a.mov_reg(1, 9)
    a.bl("iw_get_row_base_vram") # R6 = row_base

    a.mov_reg(5, 8) # rx = x0
    a.tst_imm(5, 1)
    a.b("frv_align8_loop", cond=0x0)
    a.mov_reg(0, 5)
    a.mov_reg(2, 4)
    a.bl("iw_set_px_on_row_vram")
    a.add_imm(5, 5, 1)

    # Even-aligned up to 8-pixel tile boundary
    a.label("frv_align8_loop")
    a.tst_imm(5, 7)
    a.b("frv_tile8_loop", cond=0x0)
    a.add_imm(0, 5, 2)
    a.cmp_reg(0, 10)
    a.b("frv_tail", cond=0xC)
    a.bic_imm(0, 5, 7)
    a.and_imm(1, 5, 6)
    a.add_reg(1, 1, 0, shift_imm=3, shift_type=0)
    a.add_reg(1, 6, 1)
    a.strh_imm(7, 1, 0)
    a.add_imm(5, 5, 2)
    a.b("frv_align8_loop")

    # 8-pixel tile-aligned fast path: DMA3 full 8x8 tiles on (ry & 7) == 0 when ry + 8 <= y_end!
    a.label("frv_tile8_loop")
    a.bic_imm(0, 10, 7) # R0 = x_tile_end
    a.cmp_reg(0, 5)
    a.b("frv_even_rem_loop", cond=0x9)
    a.tst_imm(9, 7)
    a.b("frv_t8_not_top", cond=0x1)
    a.add_imm(1, 9, 8)
    a.cmp_reg(1, 11)
    a.b("frv_t8_no_dma", cond=0xC)
    a.sub_reg(1, 0, 5)
    a.mov_reg(1, 1, shift_imm=1, shift_type=0) # word_count = (x_tile_end - R5) * 2
    a.orr_imm(1, 1, 0x85000000)
    a.add_reg(2, 6, 5, shift_imm=3, shift_type=0) # dst = row_base + R5 * 8
    a.add_imm(3, 13, 4) # src = SP + 4
    a.mov_imm(12, 0x040000D4)
    a.str_imm(3, 12, 0)
    a.str_imm(2, 12, 4)
    a.str_imm(1, 12, 8)
    a.mov_imm(1, 1)
    a.str_imm(1, 13, 0) # dma_strip_active = 1
    a.mov_reg(5, 0)
    a.b("frv_even_rem_loop")

    a.label("frv_t8_no_dma")
    a.mov_imm(1, 0)
    a.str_imm(1, 13, 0)
    a.b("frv_t8_sw_loop")

    a.label("frv_t8_not_top")
    a.ldr_imm(1, 13, 0)
    a.cmp_imm(1, 0)
    a.mov_reg(5, 0, cond=0x1)
    a.b("frv_even_rem_loop", cond=0x1)

    a.label("frv_t8_sw_loop")
    a.add_imm(0, 5, 8)
    a.cmp_reg(0, 10)
    a.b("frv_even_rem_loop", cond=0xC)
    a.add_reg(1, 6, 5, shift_imm=3, shift_type=0)
    a.str_imm(7, 1, 0)
    a.str_imm(7, 1, 4)
    a.add_imm(5, 5, 8)
    a.b("frv_t8_sw_loop")

    # Remaining even pairs (< 8 pixels)
    a.label("frv_even_rem_loop")
    a.add_imm(0, 5, 2)
    a.cmp_reg(0, 10)
    a.b("frv_tail", cond=0xC)
    a.bic_imm(0, 5, 7)
    a.and_imm(1, 5, 6)
    a.add_reg(1, 1, 0, shift_imm=3, shift_type=0)
    a.add_reg(1, 6, 1)
    a.strh_imm(7, 1, 0)
    a.add_imm(5, 5, 2)
    a.b("frv_even_rem_loop")

    a.label("frv_tail")
    a.cmp_reg(5, 10)
    a.b("frv_next_y", cond=0xA)
    a.mov_reg(0, 5)
    a.mov_reg(2, 4)
    a.bl("iw_set_px_on_row_vram")

    a.label("frv_next_y")
    a.add_imm(9, 9, 1)
    a.b("frv_y_loop")
    a.label("frv_done")
    a.add_imm(13, 13, 8)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # draw_box_vram(R0=x, R1=y, R2=w, R3=h, R4=bg_col, R5=border_col)
    a.label("iw_draw_box_vram")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_reg(6, 0) # x
    a.mov_reg(7, 1) # y
    a.mov_reg(8, 2) # w
    a.mov_reg(9, 3) # h
    # Fill full rect (x, y, w, h, bg_col) so (0, 0, 240, 160) hits the 9600-word DMA3 fast path!
    a.bl("iw_fill_rect_vram")
    # Top border (x, y, w, 1, border_col)
    a.mov_reg(0, 6); a.mov_reg(1, 7); a.mov_reg(2, 8); a.mov_imm(3, 1); a.mov_reg(4, 5)
    a.bl("iw_fill_rect_vram")
    # Bottom border (x, y + h - 1, w, 1, border_col)
    a.mov_reg(0, 6); a.add_reg(1, 7, 9); a.sub_imm(1, 1, 1); a.mov_reg(2, 8); a.mov_imm(3, 1); a.mov_reg(4, 5)
    a.bl("iw_fill_rect_vram")
    # Left border (x, y, 1, h, border_col)
    a.mov_reg(0, 6); a.mov_reg(1, 7); a.mov_imm(2, 1); a.mov_reg(3, 9); a.mov_reg(4, 5)
    a.bl("iw_fill_rect_vram")
    # Right border (x + w - 1, y, 1, h, border_col)
    a.add_reg(0, 6, 8); a.sub_imm(0, 0, 1); a.mov_reg(1, 7); a.mov_imm(2, 1); a.mov_reg(3, 9); a.mov_reg(4, 5)
    a.bl("iw_fill_rect_vram")
    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # draw_text_vram(R0=str_ptr, R1=x, R2=y, R3=col, R4=use_serif)
    a.label("iw_draw_text_vram")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(5, 0) # str_ptr
    a.mov_reg(6, 1) # gx
    a.mov_reg(7, 2) # y
    a.mov_reg(8, 3) # col
    a.cmp_imm(4, 0)
    a.mov_imm(9, 8, cond=0x0)
    a.mov_imm(9, 16, cond=0x1) # h
    a.mov_imm(10, table_addrs[0], cond=0x0)
    a.mov_imm(10, table_addrs[1], cond=0x1) # font_base

    a.label("dtv_char_loop")
    a.ldrb_imm(0, 5, 0)
    a.cmp_imm(0, 0)
    a.b("dtv_done", cond=0x0)
    a.cmp_imm(0, 0xE2)
    a.b("dtv_ascii", cond=0x1)
    a.add_imm(5, 5, 3)
    a.mov_imm(0, 45)
    a.b("dtv_got_code")
    a.label("dtv_ascii")
    a.add_imm(5, 5, 1)
    a.label("dtv_got_code")
    a.cmp_imm(0, 32); a.mov_imm(0, 63, cond=0x3)
    a.cmp_imm(0, 127); a.mov_imm(0, 63, cond=0x8)
    a.sub_imm(0, 0, 32) # gi = code - 32
    if control_mode == "font_shift":
        a.add_imm(0, 0, 1)
        a.cmp_imm(0, 96)
        a.mov_imm(0, 0, cond=0x2)
    a.mul(0, 0, 9) # gi * h
    a.add_reg(11, 10, 0) # glyph_ptr

    a.mov_imm(4, 0) # r = 0..h-1
    a.label("dtv_row_loop")
    a.cmp_reg(4, 9)
    a.b("dtv_next_char", cond=0x2)
    a.add_reg(0, 11, 4)
    a.ldrb_imm(3, 0, 0) # row_byte
    a.cmp_imm(3, 0)
    a.b("dtv_next_row", cond=0x0)
    a.add_reg(1, 7, 4)   # ry = y + r
    a.cmp_imm(1, 160)
    a.b("dtv_next_row", cond=0x2)
    a.push([6])
    a.bl("iw_get_row_base_vram") # R6 = row_base
    a.ldr_imm(0, 13, 0)       # R0 = px = gx
    a.mov_imm(1, 0x80)        # R1 = bit mask
    a.label("dtv_bit_loop")
    a.tst_reg(3, 1)
    a.b("dtv_bit_next", cond=0x0)
    a.cmp_imm(0, 240)
    a.b("dtv_bit_next", cond=0x2)
    a.bic_imm(12, 0, 7)
    a.and_imm(2, 0, 6)
    a.add_reg(2, 2, 12, shift_imm=3, shift_type=0)
    a.add_reg(2, 6, 2)
    a.ldrh_imm(12, 2, 0)
    a.tst_imm(0, 1)
    a.bic_imm(12, 12, 0x00FF, cond=0x0)
    a.orr_reg(12, 12, 8, cond=0x0)
    a.and_imm(12, 12, 0x00FF, cond=0x1)
    a.orr_reg(12, 12, 8, shift_imm=8, shift_type=0, cond=0x1)
    a.strh_imm(12, 2, 0)
    a.label("dtv_bit_next")
    a.add_imm(0, 0, 1)
    a.mov_reg(1, 1, shift_imm=1, shift_type=1, s=1)
    a.b("dtv_bit_loop", cond=0x1)
    a.pop([6])
    a.label("dtv_next_row")
    a.add_imm(4, 4, 1)
    a.b("dtv_row_loop")

    a.label("dtv_next_char")
    a.add_imm(6, 6, 8)
    a.b("dtv_char_loop")

    a.label("dtv_done")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # draw_wrapped_text_vram(R0=txt_ptr, R1=x, R2=y, R3=max_y)
    # Exact reproduction of:
    #   const words = txt.split(' ');
    #   let line = '', y = y0;
    #   for (const w of words) {
    #     if ((line + w).length > 27) { drawText(line, x, y, '#F8F8F0'); line = w + ' '; y += 10; }
    #     else line += w + ' ';
    #   }
    #   if (line && y < max_y) drawText(line, x, y, '#F8F8F0');
    a.label("iw_draw_wrapped_text_vram")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.sub_imm(13, 13, 64) # line_buf[64] at SP
    a.mov_reg(5, 0)       # R5 = txt_ptr
    a.mov_reg(8, 1)       # R8 = x
    a.mov_reg(7, 2)       # R7 = cur_y
    a.mov_reg(9, 3)       # R9 = max_y
    a.mov_imm(6, 0)       # R6 = line_len = 0

    a.label("dwt_word_loop")
    # Scan word length R10 until R5[R10] == 0 or R5[R10] == 32
    a.mov_imm(10, 0)
    a.label("dwt_scan_w")
    a.add_reg(0, 5, 10)
    a.ldrb_imm(11, 0, 0) # delim byte
    a.cmp_imm(11, 0)
    a.cmp_imm(11, 32, cond=0x1)
    a.b("dwt_scan_done", cond=0x0)
    a.add_imm(10, 10, 1)
    a.b("dwt_scan_w")
    a.label("dwt_scan_done")

    # Check if line_len + w_len > 27
    a.add_reg(0, 6, 10)
    a.cmp_imm(0, 27)
    a.b("dwt_append_w", cond=0x9) # <= 27
    # Flush current line unconditionally inside loop (matching 07_game_engine.js lines 1505 & 1563)
    a.add_reg(0, 13, 6)
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 0)
    a.mov_reg(0, 13)
    a.mov_reg(1, 8)
    a.mov_reg(2, 7)
    a.mov_imm(3, col("#f8f8f0"))
    a.mov_imm(4, 0)
    a.bl("iw_draw_text_vram")
    a.add_imm(7, 7, 10)
    a.mov_imm(6, 0)

    a.label("dwt_append_w")
    a.mov_imm(4, 0)
    a.label("dwt_copy_w")
    a.cmp_reg(4, 10)
    a.b("dwt_copy_w_done", cond=0x2)
    a.add_reg(0, 5, 4)
    a.ldrb_imm(0, 0, 0)
    a.add_reg(1, 13, 6)
    a.strb_imm(0, 1, 0)
    a.add_imm(6, 6, 1)
    a.add_imm(4, 4, 1)
    a.b("dwt_copy_w")
    a.label("dwt_copy_w_done")
    a.add_reg(1, 13, 6)
    a.mov_imm(0, 32)
    a.strb_imm(0, 1, 0)
    a.add_imm(6, 6, 1)

    a.cmp_imm(11, 32)
    a.add_reg(5, 5, 10, cond=0x0)
    a.add_imm(5, 5, 1, cond=0x0)
    a.b("dwt_word_loop", cond=0x0)

    # End of string: if line_len > 0 and cur_y < max_y, draw final line
    a.cmp_imm(6, 0)
    a.b("dwt_done", cond=0x0)
    a.cmp_reg(7, 9)
    a.b("dwt_done", cond=0x2)
    a.add_reg(0, 13, 6)
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 0)
    a.mov_reg(0, 13)
    a.mov_reg(1, 8)
    a.mov_reg(2, 7)
    a.mov_imm(3, col("#f8f8f0"))
    a.mov_imm(4, 0)
    a.bl("iw_draw_text_vram")

    a.label("dwt_done")
    a.add_imm(13, 13, 64)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # draw_sprite32_vram(R0=speciesId 1..151, R1=isBack 0..1, R2=dx, R3=dy, R4=scale 1..2)
    a.label("iw_draw_sprite32_vram")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.mov_reg(8, 4)    # R8 = scale
    a.mov_reg(4, 2)    # R4 = dx (always even!)
    a.mov_reg(7, 3)    # R7 = dy
    a.sub_imm(0, 0, 1)
    a.cmp_imm(0, 151); a.mov_imm(0, 0, cond=0x2)
    a.mov_reg(5, 0, shift_imm=11, shift_type=0) # * 2048
    a.cmp_imm(1, 0)
    a.add_imm(5, 5, 1024, cond=0x1)
    a.mov_imm(0, sp_pal_map_rom_addr)
    a.add_reg(5, 0, 5) # R5 = src 32x32 byte array in ROM

    a.mov_imm(9, 0)    # sy = 0..31
    a.label("ds32_y")
    a.cmp_imm(9, 32)
    a.b("ds32_done", cond=0x2)
    a.cmp_imm(8, 2)
    a.b("ds32_y_scale2", cond=0x0)

    # scale == 1: precompute row_base in R6 once per row sy, works for any dx (even or odd)!
    a.add_reg(1, 7, 9) # y = dy + sy
    a.bl("iw_get_row_base_vram") # R6 = row_base
    a.mov_imm(10, 0)   # sx = 0..31
    a.label("ds32_x1")
    a.cmp_imm(10, 32)
    a.b("ds32_next_y", cond=0x2)
    a.ldrb_imm(2, 5, 0)
    a.add_imm(5, 5, 1)
    a.cmp_imm(2, 0)
    a.b("ds32_x1_next", cond=0x0)
    a.add_reg(0, 4, 10) # x = dx + sx
    a.bic_imm(12, 0, 7)
    a.and_imm(1, 0, 6)
    a.add_reg(1, 1, 12, shift_imm=3, shift_type=0)
    a.add_reg(1, 6, 1)
    a.ldrh_imm(12, 1, 0)
    a.tst_imm(0, 1)
    a.bic_imm(12, 12, 0x00FF, cond=0x0)
    a.orr_reg(12, 12, 2, cond=0x0)
    a.and_imm(12, 12, 0x00FF, cond=0x1)
    a.orr_reg(12, 12, 2, shift_imm=8, shift_type=0, cond=0x1)
    a.strh_imm(12, 1, 0)
    a.label("ds32_x1_next")
    a.add_imm(10, 10, 1)
    a.b("ds32_x1")

    a.label("ds32_y_scale2")
    # scale == 2: precompute row0_base (R11) and row1_base (R6) once per row sy!
    a.add_reg(1, 7, 9, shift_imm=1, shift_type=0)
    a.bl("iw_get_row_base_vram")
    a.mov_reg(11, 6) # R11 = row0_base
    a.add_reg(1, 7, 9, shift_imm=1, shift_type=0)
    a.add_imm(1, 1, 1)
    a.bl("iw_get_row_base_vram") # R6 = row1_base
    a.mov_imm(10, 0) # sx = 0..31
    a.label("ds32_x2")
    a.cmp_imm(10, 32)
    a.b("ds32_next_y", cond=0x2)
    a.tst_imm(10, 3)
    a.ldr_imm(0, 5, 0, cond=0x0)
    a.cmp_imm(0, 0, cond=0x0)
    a.add_imm(5, 5, 4, cond=0x0)
    a.add_imm(10, 10, 4, cond=0x0)
    a.b("ds32_x2", cond=0x0)
    a.ldrb_imm(2, 5, 0)
    a.add_imm(5, 5, 1)
    a.cmp_imm(2, 0)
    a.b("ds32_x2_next", cond=0x0)
    a.orr_reg(2, 2, 2, shift_imm=8, shift_type=0) # c16
    a.add_reg(3, 4, 10, shift_imm=1, shift_type=0) # x = dx + sx*2 (even)
    a.bic_imm(0, 3, 7)
    a.and_imm(1, 3, 6)
    a.add_reg(1, 1, 0, shift_imm=3, shift_type=0) # tile_x_off
    a.add_reg(0, 11, 1)
    a.strh_imm(2, 0, 0)
    a.add_reg(0, 6, 1)
    a.strh_imm(2, 0, 0)
    a.label("ds32_x2_next")
    a.add_imm(10, 10, 1)
    a.b("ds32_x2")

    a.label("ds32_next_y")
    a.add_imm(9, 9, 1)
    a.b("ds32_y")
    a.label("ds32_done")
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # iw_apply_battle_flash_vram(): ORRs 0x8080 into 68x68 box at (150, 18) in BG0 VRAM
    a.label("iw_apply_battle_flash_vram")
    a.push([4, 5, 6, 7, 14])
    a.mov_imm(7, 0x8080)
    a.mov_imm(4, 18) # ry = 18..85
    a.label("abf_y_loop")
    a.cmp_imm(4, 86)
    a.b("abf_done", cond=0x2)
    a.mov_reg(1, 4)
    a.bl("iw_get_row_base_vram") # R6 = row_base
    a.mov_imm(5, 150) # rx = 150..216
    a.label("abf_x_loop")
    a.bic_imm(0, 5, 7)
    a.and_imm(1, 5, 6)
    a.add_reg(1, 1, 0, shift_imm=3, shift_type=0)
    a.add_reg(1, 6, 1)
    a.ldrh_imm(0, 1, 0)
    a.orr_reg(0, 0, 7)
    a.strh_imm(0, 1, 0)
    a.add_imm(5, 5, 2)
    a.cmp_imm(5, 218)
    a.b("abf_x_loop", cond=0x3)
    a.add_imm(4, 4, 1)
    a.b("abf_y_loop")
    a.label("abf_done")
    a.pop([4, 5, 6, 7, 15])
    a.flush_literals()

    a.label("iwram_code_end")

    # ROM -> IWRAM trampolines (jump to 0x03000000 + offset in 1-cycle IWRAM)
    a.label("set_px_vram")
    a.mov_imm(12, 0x03001000 + (a.labels["iw_set_px_vram"] - a.labels["iwram_code_start"]))
    a.bx(12)
    a.label("fill_rect_vram")
    a.mov_imm(12, 0x03001000 + (a.labels["iw_fill_rect_vram"] - a.labels["iwram_code_start"]))
    a.bx(12)
    a.label("draw_box_vram")
    a.mov_imm(12, 0x03001000 + (a.labels["iw_draw_box_vram"] - a.labels["iwram_code_start"]))
    a.bx(12)
    a.label("draw_text_vram")
    a.mov_imm(12, 0x03001000 + (a.labels["iw_draw_text_vram"] - a.labels["iwram_code_start"]))
    a.bx(12)
    a.label("draw_wrapped_text_vram")
    a.mov_imm(12, 0x03001000 + (a.labels["iw_draw_wrapped_text_vram"] - a.labels["iwram_code_start"]))
    a.bx(12)
    a.label("draw_sprite32_vram")
    a.mov_imm(12, 0x03001000 + (a.labels["iw_draw_sprite32_vram"] - a.labels["iwram_code_start"]))
    a.bx(12)
    a.label("apply_battle_flash_vram")
    a.mov_imm(12, 0x03001000 + (a.labels["iw_apply_battle_flash_vram"] - a.labels["iwram_code_start"]))
    a.bx(12)

    # place_char_obj(R0=oam_slot 0..31, R1=char_idx 0..46, R2=dir_idx 0..3, R3=wf 0..2, R4=sx_s32, R5=sy_s32, R6=prio 0..3)
    a.label("place_char_obj")
    a.push([4, 5, 6, 7, 8, 14])
    # Compute ROM offset: char_obj_rom_addr + ((char_idx * 12) + (dir_idx * 3) + wf) * 512
    a.mov_imm(7, 12)
    a.mul(1, 1, 7)
    a.mov_imm(7, 3)
    a.mul(2, 2, 7)
    a.add_reg(1, 1, 2)
    a.add_reg(1, 1, 3)
    a.mov_reg(1, 1, shift_imm=9, shift_type=0) # * 512
    a.mov_imm(2, char_obj_rom_addr)
    a.add_reg(1, 2, 1) # src in ROM
    a.mov_reg(2, 0, shift_imm=9, shift_type=0) # slot * 512
    a.add_imm(2, 2, 0x06010000) # dst in OBJ VRAM
    a.mov_imm(3, 0x04000000)
    a.str_imm(1, 3, 0xD4)
    a.str_imm(2, 3, 0xD8)
    a.mov_imm(1, 0x84000000 | 128)
    a.str_imm(1, 3, 0xDC)

    # Write OAM entry at 0x07000000 + oam_slot * 8
    a.mov_imm(1, 0x07000000)
    a.add_reg(1, 1, 0, shift_imm=3, shift_type=0)
    a.and_imm(2, 5, 0xFF)
    a.orr_imm(2, 2, 0xA000) # Attr0: Tall (2<<14) | 8bpp (1<<13) | (sy & 0xFF)
    a.strh_imm(2, 1, 0)
    a.mov_imm(3, 0x1FF)
    a.and_reg(2, 4, 3)
    a.orr_imm(2, 2, 0x8000) # Attr1: Size 2 (16x32) | (sx & 0x1FF)
    a.strh_imm(2, 1, 2)
    a.mov_reg(2, 0, shift_imm=4, shift_type=0) # tileBase = oam_slot * 16
    a.orr_reg(2, 2, 6, shift_imm=10, shift_type=0) # Attr2: (prio << 10) | tileBase
    a.strh_imm(2, 1, 4)
    a.pop([4, 5, 6, 7, 8, 15])
    a.flush_literals()

    # hide_all_objs()
    a.label("hide_all_objs")
    a.push([0, 1, 2, 14])
    a.mov_imm(0, 0x07000000)
    a.mov_imm(1, 0x0200) # Attr0 = 0x0200 (disabled)
    a.mov_imm(2, 128)
    a.label("hao_lp")
    a.str_imm(1, 0, 0)
    a.add_imm(0, 0, 8)
    a.sub_imm(2, 2, 1, s=1)
    a.b("hao_lp", cond=0x1)
    a.pop([0, 1, 2, 15])

    # clear_bg0_vram(R0=fill_byte, R1=word_count)
    a.label("clear_bg0_vram")
    a.push([2, 3, 14])
    a.and_imm(0, 0, 0xFF)
    a.orr_reg(0, 0, 0, shift_imm=8, shift_type=0)
    a.orr_reg(0, 0, 0, shift_imm=16, shift_type=0)
    a.mov_imm(2, 0x03000000)
    a.str_imm(0, 2, 0)
    a.mov_imm(3, 0x04000000)
    a.str_imm(2, 3, 0xD4)
    a.mov_imm(2, 0x06000040)
    a.str_imm(2, 3, 0xD8)
    a.orr_imm(1, 1, 0x85000000)
    a.str_imm(1, 3, 0xDC)
    a.pop([2, 3, 15])
    a.flush_literals()

    # load_map_to_vram(R0=mapId, R1=switchActive)
    a.label("load_map_to_vram")
    a.push([4, 5, 6, 7, 8, 9, 10, 14])
    a.mov_reg(4, 0)
    a.mov_reg(5, 1)
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
    a.ldrb_imm(8, 0, 12)
    a.ldrb_imm(9, 0, 13)
    a.ldr_imm(1, 0, 20)
    a.add_reg(7, 7, 1)

    a.mov_imm(10, 0)
    a.label("lmv_y")
    a.cmp_reg(10, 9)
    a.b("lmv_done", cond=0x2)
    a.mov_imm(1, 0)
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

    # render_overworld_hud_and_banner(R0=map_hdr_ptr, R1=camX_s32, R2=camY_s32)
    a.label("render_overworld_hud_and_banner")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_reg(4, 0) # map_hdr_ptr
    a.mov_reg(7, 1) # camX
    a.mov_reg(8, 2) # camY
    a.mov_imm(5, 0x02001000)
    a.mov_imm(6, 0x02000000)

    # Top HUD: DMA3 fill y=0..15 (960 words at 0x06000040) + fill_rect_vram(0, 16, 240, 4, '#182030')
    a.mov_imm(0, col("#182030"))
    a.orr_reg(0, 0, 0, shift_imm=8, shift_type=0)
    a.orr_reg(0, 0, 0, shift_imm=16, shift_type=0)
    a.mov_imm(1, 0x03000000)
    a.str_imm(0, 1, 0)
    a.mov_imm(2, 0x040000D4)
    a.str_imm(1, 2, 0)
    a.mov_imm(0, 0x06000040)
    a.str_imm(0, 2, 4)
    a.mov_imm(0, 0x85000000 | 960)
    a.str_imm(0, 2, 8)
    a.mov_imm(0, 0); a.mov_imm(1, 16); a.mov_imm(2, 240); a.mov_imm(3, 4); a.mov_imm(4, col("#182030"))
    a.bl("fill_rect_vram")
    # Restore R4 = map_hdr_ptr
    a.ldrb_imm(0, 6, 0x28); a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(4, 1, 0)

    # drawText(map.name.slice(0, 29), 2, 2, '#F8E888')
    a.bl("fmt_clear")
    a.ldr_imm(0, 4, 4) # map.name str_off
    a.mov_imm(1, 29)
    a.bl("fmt_rom_off_n")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 2); a.mov_imm(2, 2); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.ldrb_imm(0, 6, 0x28); a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(4, 1, 0)

    # drawText(`${isNight ? 'Night' : 'Day'} Seals:${seals.length}/8 ${gold}G`, 2, 11, '#A8DADC')
    a.bl("fmt_clear")
    a.ldrb_imm(0, 6, 0x2C)
    a.cmp_imm(0, 0)
    a.mov_imm(0, ui_off("Day Seals:"), cond=0x0)
    a.mov_imm(0, ui_off("Night Seals:"), cond=0x1)
    a.bl("fmt_str")
    a.ldrb_imm(1, 6, 0x2F)
    a.mov_imm(0, 0)
    for b_i in range(8):
        a.tst_imm(1, 1 << b_i)
        a.add_imm(0, 0, 1, cond=0x1)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off("/8 "))
    a.bl("fmt_str")
    a.ldr_imm(0, 6, 0x24)
    a.bl("fmt_u32")
    a.mov_imm(0, 71) # 'G'
    a.bl("fmt_putc")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 2); a.mov_imm(2, 11); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.ldrb_imm(0, 6, 0x28); a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(4, 1, 0)

    # Dark cave 56x56 clearRect cutout on BG0 (if map.dark == 1)
    a.ldrb_imm(0, 4, 14) # dark
    a.cmp_imm(0, 0)
    a.b("rohb_chk_banner", cond=0x0)
    # px = state.x * 8 + 4 - camX, py = 20 + state.y * 8 + 4 - camY
    a.ldrb_imm(0, 6, 0x29)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.add_imm(0, 0, 4)
    a.sub_reg(0, 0, 7) # px
    a.sub_imm(0, 0, 28) # x0 = px - 28
    a.ldrb_imm(1, 6, 0x2A)
    a.mov_reg(1, 1, shift_imm=3, shift_type=0)
    a.add_imm(1, 1, 24)
    a.sub_reg(1, 1, 8) # py
    a.sub_imm(1, 1, 28) # y0 = py - 28
    a.mov_imm(3, 56)
    a.cmp_imm(1, 20)
    a.b("rohb_dark_y_ok", cond=0xA)
    a.rsb_imm(2, 1, 20)
    a.sub_reg(3, 3, 2)
    a.mov_imm(1, 20)
    a.label("rohb_dark_y_ok")
    a.mov_imm(2, 56)
    a.mov_imm(4, 127) # pure black 0x0000
    a.bl("fill_rect_vram")

    a.label("rohb_chk_banner")
    a.ldrh_imm(0, 5, 0x30) # banner_timer_frames
    a.cmp_imm(0, 0)
    a.b("rohb_done", cond=0x0)
    a.ldrb_imm(0, 5, 0x34) # banner_map_id
    a.cmp_imm(0, 56)
    a.b("rohb_done", cond=0x2)
    a.mov_imm(0, 16); a.mov_imm(1, 26); a.mov_imm(2, 208); a.mov_imm(3, 18)
    a.mov_imm(4, 124); a.mov_imm(5, 125)
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(0, 5, 0x34)
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(0, 1, 0)
    a.ldr_imm(4, 0, 4) # destMap.name str_off
    a.bl("fmt_clear")
    a.mov_reg(0, 4); a.mov_imm(1, 24); a.bl("fmt_rom_off_n")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 22); a.mov_imm(2, 31); a.mov_imm(3, 126); a.mov_imm(4, 0)
    a.bl("draw_text_vram")

    a.label("rohb_done")
    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # render_frame_to_vram()
    a.label("render_frame_to_vram")
    a.push([4, 5, 6, 7, 8, 9, 10, 11, 14])
    a.sub_imm(13, 13, 32)
    a.mov_imm(5, 0x02001000) # RSTATE
    a.mov_imm(6, 0x02000000) # GSTATE

    # 1. Check if current map / switch state needs loading into BG1 Screenblocks 28..29
    a.ldrb_imm(0, 6, 0x28)
    a.mov_reg(1, 0, shift_imm=3, shift_type=1)
    a.and_imm(2, 0, 7)
    a.add_reg(1, 6, 1)
    a.ldrb_imm(1, 1, 0x30)
    a.mov_reg_rs(1, 1, 2, shift_type=1)
    a.and_imm(1, 1, 1)
    a.ldrb_imm(2, 5, 0x46)
    a.ldrb_imm(3, 5, 0x47)
    a.cmp_reg(0, 2)
    a.cmp_reg(1, 3, cond=0x0)
    a.b("rfv_map_loaded", cond=0x0)
    a.strb_imm(0, 5, 0x46)
    a.strb_imm(1, 5, 0x47)
    a.bl("load_map_to_vram")
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x45)
    a.strb_imm(0, 5, 0x48)
    a.label("rfv_map_loaded")

    # Step 2 (animTick DMA) moved to rfv_done so it uses post-render frame_counter

    # 3. Compute camX (R8) and camY (R9) and update BG1HOFS / BG1VOFS
    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(4, 1, 0) # R4 = map_hdr_ptr
    a.ldrb_imm(0, 4, 12)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.cmp_imm(0, 240)
    a.b("rfv_camx_scroll", cond=0x8)
    a.rsb_imm(8, 0, 240)
    a.mov_reg(8, 8, shift_imm=1, shift_type=1)
    a.rsb_imm(8, 8, 0)
    a.b("rfv_camx_done")
    a.label("rfv_camx_scroll")
    a.ldrb_imm(8, 6, 0x29)
    a.mov_reg(8, 8, shift_imm=3, shift_type=0)
    a.sub_imm(8, 8, 116, s=1)
    a.mov_imm(8, 0, cond=0x4)
    a.sub_imm(2, 0, 240)
    a.cmp_reg(8, 2)
    a.mov_reg(8, 2, cond=0x8)
    a.label("rfv_camx_done")

    a.ldrb_imm(0, 4, 13)
    a.mov_reg(0, 0, shift_imm=3, shift_type=0)
    a.cmp_imm(0, 140)
    a.b("rfv_camy_scroll", cond=0x8)
    a.rsb_imm(9, 0, 140)
    a.mov_reg(9, 9, shift_imm=1, shift_type=1)
    a.rsb_imm(9, 9, 0)
    a.b("rfv_camy_done")
    a.label("rfv_camy_scroll")
    a.ldrb_imm(9, 6, 0x2A)
    a.mov_reg(9, 9, shift_imm=3, shift_type=0)
    a.sub_imm(9, 9, 66, s=1)
    a.mov_imm(9, 0, cond=0x4)
    a.sub_imm(3, 0, 140)
    a.cmp_reg(9, 3)
    a.mov_reg(9, 3, cond=0x8)
    a.label("rfv_camy_done")

    a.mov_imm(0, 0x04000000)
    a.strh_imm(8, 0, 0x14) # BG1HOFS = camX
    a.sub_imm(2, 9, 20)
    a.strh_imm(2, 0, 0x16) # BG1VOFS = camY - 20

    a.ldrb_imm(7, 5, 0x20) # screen_id

    # 5. Update Hardware OAM Sprites (every frame!)
    a.bl("hide_all_objs")
    a.cmp_imm(7, 2) # STARTER screen?
    a.b("rfv_obj_chk_ow", cond=0x1)
    # On STARTER: OAM slot 0 = player_{look_idx}, dir='down'(0), wf=0, sx=206, sy=98, prio=0
    a.ldrb_imm(1, 5, 0x2B) # look_idx (0..2 = char_idx 0..2)
    a.mov_imm(0, 0); a.mov_imm(2, 0); a.mov_imm(3, 0); a.mov_imm(4, 206); a.mov_imm(5, 98); a.mov_imm(6, 0)
    a.bl("place_char_obj")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)
    a.b("rfv_objs_done")

    a.label("rfv_obj_chk_ow")
    a.cmp_imm(7, 3); a.cmp_imm(7, 4, cond=0x1); a.cmp_imm(7, 6, cond=0x1)
    a.cmp_imm(7, 7, cond=0x1); a.cmp_imm(7, 8, cond=0x1); a.cmp_imm(7, 9, cond=0x1)
    a.cmp_imm(7, 10, cond=0x1); a.cmp_imm(7, 11, cond=0x1); a.cmp_imm(7, 12, cond=0x1)
    a.b("rfv_objs_done", cond=0x1)

    # OAM Slot 0: Player sprite (prio = 1)
    a.ldrb_imm(1, 6, 0x2D) # playerLook (0..2)
    a.ldrb_imm(2, 6, 0x2B) # state.dir (0..3)
    a.cmp_imm(7, 3)
    a.ldrb_imm(0, 5, 0x2D, cond=0x0) # move_cooldown_frames on OVERWORLD
    a.ldrb_imm(0, 5, 0x50, cond=0x1) # ref_move_cooldown_frames on DIALOG/MENU overlays
    a.cmp_imm(0, 0)
    a.mov_imm(3, 0, cond=0x0)
    a.ldrb_imm(3, 5, 0x2C, cond=0x1) # walk_frame
    a.ldrb_imm(4, 6, 0x29)
    a.mov_reg(4, 4, shift_imm=3, shift_type=0)
    a.sub_imm(4, 4, 4)
    a.sub_reg(4, 4, 8) # sx = state.x * 8 - 4 - camX
    a.ldrb_imm(5, 6, 0x2A)
    a.mov_reg(5, 5, shift_imm=3, shift_type=0)
    a.add_imm(5, 5, 4)
    a.sub_reg(5, 5, 9) # sy = 20 + state.y * 8 - 16 - camY = state.y * 8 + 4 - camY
    a.mov_imm(0, 0)
    a.mov_imm(6, 1)    # prio = 1
    a.bl("place_char_obj")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)

    # OAM Slots 1..N: Visible NPCs on current map (in reverse order so later NPCs win OAM priority)
    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(4, 1, 0)
    a.ldrb_imm(10, 4, 18) # npcCount
    a.ldr_imm(11, 4, 32)  # npc_off
    a.mov_imm(0, table_addrs[10])
    a.add_reg(11, 0, 11)  # npc_rom_base
    a.mov_imm(0, 1)       # cur_oam_slot = 1
    a.str_imm(0, 13, 0)   # [SP+0] = cur_oam_slot
    a.sub_imm(10, 10, 1, s=1) # i = npcCount - 1
    a.label("rfv_npc_obj_loop")
    a.b("rfv_objs_done", cond=0x4) # BMI (i < 0)
    a.mov_imm(0, 80)
    a.mul(0, 10, 0)
    a.add_reg(4, 11, 0)   # npc_ptr = npc_rom_base + i * 80
    a.mov_reg(0, 4)
    a.bl("is_npc_hidden")
    a.cmp_imm(0, 0)
    a.b("rfv_npc_obj_next", cond=0x1)
    a.ldrh_imm(0, 4, 24)  # npc_global_idx
    a.mov_imm(1, 0x02001800)
    a.add_reg(1, 1, 0, shift_imm=1, shift_type=0)
    a.ldrb_imm(2, 1, 0)   # npc.x
    a.ldrb_imm(3, 1, 1)   # npc.y
    a.mov_reg(2, 2, shift_imm=3, shift_type=0)
    a.sub_imm(2, 2, 4)
    a.sub_reg(2, 2, 8)    # sx = npc.x * 8 - 4 - camX
    a.mov_reg(3, 3, shift_imm=3, shift_type=0)
    a.add_imm(3, 3, 4)
    a.sub_reg(3, 3, 9)    # sy = 20 + npc.y * 8 - 16 - camY
    # Check screen bounds: -15 <= sx < 240 and -23 <= sy < 160
    a.cmn_imm(2, 15); a.b("rfv_npc_obj_next", cond=0xB)
    a.cmp_imm(2, 240); a.b("rfv_npc_obj_next", cond=0xA)
    a.cmn_imm(3, 23); a.b("rfv_npc_obj_next", cond=0xB)
    a.cmp_imm(3, 160); a.b("rfv_npc_obj_next", cond=0xA)

    a.ldr_imm(0, 13, 0)   # cur_oam_slot
    a.add_imm(1, 0, 1)
    a.str_imm(1, 13, 0)
    a.ldrb_imm(1, 4, 10)  # spr_idx
    a.mov_reg(4, 2)       # sx -> R4
    a.mov_reg(5, 3)       # sy -> R5
    a.mov_imm(2, 80); a.mul(2, 10, 2); a.add_reg(2, 11, 2)
    a.ldrb_imm(2, 2, 11)  # dir_idx -> R2
    a.mov_imm(3, 0)       # wf = 0 -> R3
    a.mov_imm(6, 1)       # prio = 1 -> R6
    a.bl("place_char_obj")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)

    a.label("rfv_npc_obj_next")
    a.sub_imm(10, 10, 1, s=1)
    a.b("rfv_npc_obj_loop")

    a.label("rfv_objs_done")
    # 6. Check if BG0 UI canvas needs redrawing (dirty_ui != 0)
    a.ldrb_imm(0, 5, 0x45)
    a.strb_imm(0, 5, 0x4D) # did_redraw = dirty_ui
    a.cmp_imm(0, 0)
    a.b("rfv_done", cond=0x0)
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x48) # loading_flag = 1 during full BG0 UI/map transition frame (<= 2 frames, well under 30-frame limit)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x45)

    a.ldrb_imm(7, 5, 0x20) # R7 = screen_id

    # Check if screen is an overworld-based screen: 3(OVERWORLD), 4(DIALOG), 6(MENU), 7(DEX), 8(PARTY), 9(BOX), 10(BAG), 11(SHOP), 12(LEARN_MOVE)
    a.cmp_imm(7, 3); a.cmp_imm(7, 4, cond=0x1); a.cmp_imm(7, 6, cond=0x1)
    a.cmp_imm(7, 7, cond=0x1); a.cmp_imm(7, 8, cond=0x1); a.cmp_imm(7, 9, cond=0x1)
    a.cmp_imm(7, 10, cond=0x1); a.cmp_imm(7, 11, cond=0x1); a.cmp_imm(7, 12, cond=0x1)
    a.b("rfv_full_screen", cond=0x1)

    # Clear BG0 to 0 (transparent): if screen == 3 && !map.dark && !prev_full_bg0, only clear top 6 tile rows (2880 words)!
    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(4, 1, 0)
    a.cmp_imm(7, 3)
    a.b("rfv_clr_full_trans", cond=0x1)
    a.ldrb_imm(0, 4, 14) # map.dark
    a.ldrb_imm(1, 5, 0x4B) # prev_full_bg0
    a.orr_reg(0, 0, 1, s=1)
    a.b("rfv_clr_full_trans_ow", cond=0x1)
    a.mov_imm(0, 0)
    a.mov_imm(1, 2880)
    a.bl("clear_bg0_vram")
    a.b("rfv_draw_ow_base")
    a.label("rfv_clr_full_trans_ow")
    a.ldrb_imm(0, 4, 14)
    a.strb_imm(0, 5, 0x4B)
    a.mov_imm(0, 0)
    a.mov_imm(1, 9600)
    a.bl("clear_bg0_vram")
    a.b("rfv_draw_ow_base")

    a.label("rfv_clr_full_trans")
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x4B)
    a.mov_imm(0, 0)
    a.mov_imm(1, 9600)
    a.bl("clear_bg0_vram")

    a.label("rfv_draw_ow_base")
    a.mov_reg(0, 4)
    a.mov_reg(1, 8)
    a.mov_reg(2, 9)
    a.bl("render_overworld_hud_and_banner")

    a.cmp_imm(7, 3) # pure OVERWORLD?
    a.b("rfv_done", cond=0x0)

    # Overlay Screen 4: DIALOG
    a.cmp_imm(7, 4)
    a.b("rfv_ov_menu", cond=0x1)
    a.mov_imm(0, 4); a.mov_imm(1, 108); a.mov_imm(2, 232); a.mov_imm(3, 48)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(0, 5, 0x41) # dialog_idx
    a.mov_imm(1, 0x02003000)
    a.add_reg(0, 1, 0, shift_imm=7, shift_type=0)
    a.mov_imm(1, 10); a.mov_imm(2, 114); a.mov_imm(3, 148)
    a.bl("draw_wrapped_text_vram")
    a.mov_imm(0, ui_off("v")); a.mov_imm(1, 224); a.mov_imm(2, 144); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # Overlay Screen 6: MENU
    a.label("rfv_ov_menu")
    a.cmp_imm(7, 6)
    a.b("rfv_ov_dex", cond=0x1)
    a.mov_imm(0, 132); a.mov_imm(1, 16); a.mov_imm(2, 104); a.mov_imm(3, 138)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(8, 5, 0x22) # menu_cursor
    menu_items = ["PARTY", "bEATdex", "BOX", "BAG", "SAVE", "OPTIONS", "CONTROLS", "CLOSE"]
    for m_i, m_str in enumerate(menu_items):
        a.cmp_imm(8, m_i)
        a.mov_imm(0, ui_off(">" + m_str), cond=0x0)
        a.mov_imm(3, col("#f8e888"), cond=0x0)
        a.mov_imm(0, ui_off(" " + m_str), cond=0x1)
        a.mov_imm(3, col("#f8f8f0"), cond=0x1)
        a.mov_imm(1, 138); a.mov_imm(2, 24 + m_i * 15); a.mov_imm(4, 0)
        a.bl("draw_text_vram")
    a.b("rfv_done")

    # Overlay Screen 7: DEX
    a.label("rfv_ov_dex")
    a.cmp_imm(7, 7)
    a.b("rfv_ov_party", cond=0x1)
    a.mov_imm(0, 4); a.mov_imm(1, 4); a.mov_imm(2, 232); a.mov_imm(3, 152)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f0c040"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)
    # Count caught bits across 20 bytes at 0x0200006A
    a.mov_imm(8, 0) # caughtCount
    a.mov_imm(1, 0)
    a.label("rfv_dex_cnt_lp")
    a.add_reg(2, 6, 1)
    a.ldrb_imm(0, 2, 0x6A)
    for b_i in range(8):
        a.tst_imm(0, 1 << b_i)
        a.add_imm(8, 8, 1, cond=0x1)
    a.add_imm(1, 1, 1)
    a.cmp_imm(1, 20)
    a.b("rfv_dex_cnt_lp", cond=0x3)
    # maxEntries = (seen(151) || caught(151)) ? 151 : 150
    a.ldrb_imm(0, 6, 0x56 + 18)
    a.ldrb_imm(1, 6, 0x6A + 18)
    a.orr_reg(0, 0, 1)
    a.tst_imm(0, 1 << 6)
    a.mov_imm(9, 150, cond=0x0)
    a.mov_imm(9, 151, cond=0x1) # R9 = maxEntries
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("bEATdex "))
    a.bl("fmt_str")
    a.mov_reg(0, 8)
    a.bl("fmt_u32")
    a.mov_imm(0, 47) # '/'
    a.bl("fmt_putc")
    a.mov_reg(0, 9)
    a.bl("fmt_u32")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 10); a.mov_imm(2, 10); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.cmp_imm(8, 151)
    a.b("rfv_dex_list", cond=0x3)
    a.mov_imm(0, ui_off("COMPLETE!")); a.mov_imm(1, 154); a.mov_imm(2, 10); a.mov_imm(3, col("#98d830")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")

    a.label("rfv_dex_list")
    a.mov_imm(10, 0) # i = 0..6
    a.label("rfv_dex_row_lp")
    a.cmp_imm(10, 7)
    a.b("rfv_dex_cur", cond=0x2)
    a.ldrb_imm(0, 5, 0x24) # dex_scroll
    a.add_reg(11, 0, 10)   # idx = dexScroll + i
    a.cmp_reg(11, 9)
    a.b("rfv_dex_cur", cond=0x2)
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 0x23) # dex_cursor
    a.cmp_reg(11, 0)
    a.mov_imm(0, 62, cond=0x0) # '>'
    a.mov_imm(0, 32, cond=0x1) # ' '
    a.bl("fmt_putc")
    a.add_imm(0, 11, 1)    # sp.id = idx + 1
    a.bl("fmt_u32_pad3")
    a.mov_imm(0, 32)
    a.bl("fmt_putc")
    # Check seen(idx + 1)
    a.mov_reg(1, 11, shift_imm=3, shift_type=1)
    a.and_imm(2, 11, 7)
    a.add_reg(3, 6, 1)
    a.ldrb_imm(0, 3, 0x56)
    a.mov_reg_rs(0, 0, 2, shift_type=1)
    a.tst_imm(0, 1)
    a.b("rfv_dex_unseen", cond=0x0)
    a.add_imm(0, 11, 1)
    a.mov_imm(1, 10)
    a.bl("fmt_sp_name_n")
    a.b("rfv_dex_chk_star")
    a.label("rfv_dex_unseen")
    a.mov_imm(0, ui_off("???"))
    a.bl("fmt_str")
    a.label("rfv_dex_chk_star")
    a.mov_reg(1, 11, shift_imm=3, shift_type=1)
    a.and_imm(2, 11, 7)
    a.add_reg(3, 6, 1)
    a.ldrb_imm(0, 3, 0x6A)
    a.mov_reg_rs(0, 0, 2, shift_type=1)
    a.tst_imm(0, 1)
    a.mov_imm(0, 42, cond=0x1) # '*'
    a.bl("fmt_putc", cond=0x1)
    a.ldrb_imm(0, 5, 0x23)
    a.cmp_reg(11, 0)
    a.mov_imm(3, col("#f8e888"), cond=0x0)
    a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 13); a.mul(2, 10, 0); a.add_imm(2, 2, 26)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 8); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(10, 10, 1)
    a.b("rfv_dex_row_lp")

    a.label("rfv_dex_cur")
    a.ldrb_imm(11, 5, 0x23) # dex_cursor
    a.mov_reg(1, 11, shift_imm=3, shift_type=1)
    a.and_imm(2, 11, 7)
    a.add_reg(3, 6, 1)
    a.ldrb_imm(0, 3, 0x56)
    a.mov_reg_rs(0, 0, 2, shift_type=1)
    a.tst_imm(0, 1)
    a.b("rfv_dex_not_seen_panel", cond=0x0)
    a.add_imm(0, 11, 1)
    a.mov_imm(1, 0); a.mov_imm(2, 154); a.mov_imm(3, 24); a.mov_imm(4, 2)
    a.bl("draw_sprite32_vram")
    # curSp ptr in R8
    a.mov_imm(0, 56); a.mul(8, 11, 0); a.mov_imm(0, table_addrs[4]); a.add_reg(8, 0, 8)
    # curSp.types.join('/').slice(0, 12) at (140, 92, '#A8DADC')
    a.bl("fmt_clear")
    a.ldrb_imm(0, 8, 2) # t0
    a.mov_imm(1, table_addrs[2])
    a.add_reg(0, 1, 0, shift_imm=3, shift_type=0)
    a.ldr_imm(0, 0, 0)
    a.bl("fmt_rom_off")
    a.ldrb_imm(0, 8, 3) # t1
    a.cmp_imm(0, 0xFF)
    a.b("rfv_dex_t1_done", cond=0x0)
    a.mov_imm(0, 47); a.bl("fmt_putc")
    a.ldrb_imm(0, 8, 3)
    a.mov_imm(1, table_addrs[2])
    a.add_reg(0, 1, 0, shift_imm=3, shift_type=0)
    a.ldr_imm(0, 0, 0)
    a.bl("fmt_rom_off")
    a.label("rfv_dex_t1_done")
    # Truncate fmt_buf at 12 chars
    a.mov_imm(0, 0x02003610)
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 12)
    a.mov_imm(1, 140); a.mov_imm(2, 92); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # curSp.dex.slice(0, 27) at (10, 126) and slice(27, 54) at (10, 138)
    a.bl("fmt_clear")
    a.ldr_imm(0, 8, 36) # dex str_off
    a.mov_imm(1, 54)
    a.bl("fmt_rom_off_n")
    # Draw slice(27, 54) if len > 27
    a.mov_imm(0, 0x02003600)
    a.ldrh_imm(1, 0, 4) # len
    a.cmp_imm(1, 27)
    a.b("rfv_dex_line1_only", cond=0x9)
    a.add_imm(0, 0, 0x10 + 27)
    a.mov_imm(1, 10); a.mov_imm(2, 138); a.mov_imm(3, col("#c0c8d0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.label("rfv_dex_line1_only")
    a.mov_imm(0, 0x02003610)
    a.mov_imm(1, 0)
    a.strb_imm(1, 0, 27)
    a.mov_imm(1, 10); a.mov_imm(2, 126); a.mov_imm(3, col("#c0c8d0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    a.label("rfv_dex_not_seen_panel")
    a.mov_imm(0, ui_off("Not seen yet")); a.mov_imm(1, 132); a.mov_imm(2, 56); a.mov_imm(3, col("#708090")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # Overlay Screen 8: PARTY
    a.label("rfv_ov_party")
    a.cmp_imm(7, 8)
    a.b("rfv_ov_box", cond=0x1)
    a.mov_imm(0, 6); a.mov_imm(1, 6); a.mov_imm(2, 228); a.mov_imm(3, 148)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(0, ui_off("PARTY (A:Lead B:Back)")); a.mov_imm(1, 12); a.mov_imm(2, 12); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)
    a.ldrb_imm(8, 6, 0x0B0) # partyCount
    a.mov_imm(9, 0)         # i = 0
    a.label("rfv_pty_lp")
    a.cmp_reg(9, 8)
    a.b("rfv_done", cond=0x2)
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 0x25) # party_cursor
    a.cmp_reg(9, 0)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.mov_imm(0, 48); a.mul(10, 9, 0); a.add_imm(10, 10, 0x0B4); a.add_reg(10, 6, 10)
    a.ldrb_imm(0, 10, 4); a.mov_imm(1, 11); a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" L")); a.bl("fmt_str")
    a.ldrb_imm(0, 10, 5); a.bl("fmt_u32")
    a.mov_imm(0, 32); a.bl("fmt_putc")
    a.ldrh_imm(0, 10, 8); a.bl("fmt_u32")
    a.mov_imm(0, 47); a.bl("fmt_putc")
    a.ldrh_imm(0, 10, 0x0A); a.bl("fmt_u32")
    a.ldrb_imm(0, 5, 0x25)
    a.cmp_reg(9, 0)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 19); a.mul(2, 9, 0); a.add_imm(2, 2, 30)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 10); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(9, 9, 1)
    a.b("rfv_pty_lp")

    # Overlay Screen 9: BOX
    a.label("rfv_ov_box")
    a.cmp_imm(7, 9)
    a.b("rfv_ov_bag", cond=0x1)
    a.mov_imm(0, 6); a.mov_imm(1, 6); a.mov_imm(2, 228); a.mov_imm(3, 148)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)
    a.ldrb_imm(8, 6, 0x0B1) # boxCount
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("BOX (")); a.bl("fmt_str")
    a.mov_reg(0, 8); a.bl("fmt_u32")
    a.mov_imm(0, ui_off(") A:ToParty")); a.bl("fmt_str")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 12); a.mov_imm(2, 12); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.cmp_imm(8, 0)
    a.b("rfv_box_nonempty", cond=0x1)
    a.mov_imm(0, ui_off("Box is empty!")); a.mov_imm(1, 20); a.mov_imm(2, 40); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")
    a.label("rfv_box_nonempty")
    a.cmp_imm(8, 7); a.mov_imm(8, 7, cond=0x8)
    a.mov_imm(9, 0)
    a.label("rfv_box_lp")
    a.cmp_reg(9, 8)
    a.b("rfv_done", cond=0x2)
    a.bl("fmt_clear")
    a.ldrb_imm(0, 5, 0x26) # box_cursor
    a.cmp_reg(9, 0)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.mov_imm(0, 24); a.mul(10, 9, 0); a.mov_imm(0, 0x020001D4); a.add_reg(10, 0, 10)
    a.ldrb_imm(0, 10, 4); a.mov_imm(1, 14); a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" L")); a.bl("fmt_str")
    a.ldrb_imm(0, 10, 5); a.bl("fmt_u32")
    a.ldrb_imm(0, 5, 0x26)
    a.cmp_reg(9, 0)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 15); a.mul(2, 9, 0); a.add_imm(2, 2, 30)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 12); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(9, 9, 1)
    a.b("rfv_box_lp")

    # Overlay Screen 10: BAG
    a.label("rfv_ov_bag")
    a.cmp_imm(7, 10)
    a.b("rfv_ov_shop", cond=0x1)
    a.mov_imm(0, 6); a.mov_imm(1, 6); a.mov_imm(2, 228); a.mov_imm(3, 148)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("BAG (")); a.bl("fmt_str")
    a.ldr_imm(0, 6, 0x24); a.bl("fmt_u32")
    a.mov_imm(0, ui_off("G) A:Use")); a.bl("fmt_str")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 12); a.mov_imm(2, 12); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(0, 0); a.mov_reg(1, 13); a.bl("build_bag_filter")
    a.mov_reg(8, 0) # keys.length
    a.ldrb_imm(9, 5, 0x27) # bag_cursor
    a.sub_imm(10, 9, 4, s=1)
    a.mov_imm(10, 0, cond=0x4) # start = max(0, bagCursor - 4)
    a.mov_imm(11, 0) # idx = 0..6
    a.label("rfv_bag_lp")
    a.cmp_imm(11, 7)
    a.b("rfv_done", cond=0x2)
    a.add_reg(0, 10, 11) # realIdx
    a.cmp_reg(0, 8)
    a.b("rfv_done", cond=0x2)
    a.bl("fmt_clear")
    a.add_reg(0, 10, 11)
    a.cmp_reg(0, 9)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.add_reg(0, 10, 11)
    a.add_reg(0, 13, 0)
    a.ldrb_imm(4, 0, 0) # item_idx
    a.mov_reg(0, 4); a.mov_imm(1, 18); a.bl("fmt_it_name_n")
    a.mov_imm(0, ui_off(" x")); a.bl("fmt_str")
    a.mov_imm(0, 0x0200007E); a.add_reg(0, 0, 4, shift_imm=1, shift_type=0); a.ldrh_imm(0, 0, 0)
    a.bl("fmt_u32")
    a.add_reg(0, 10, 11)
    a.cmp_reg(0, 9)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 14); a.mul(2, 11, 0); a.add_imm(2, 2, 30)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 12); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(11, 11, 1)
    a.b("rfv_bag_lp")

    # Overlay Screen 11: SHOP
    a.label("rfv_ov_shop")
    a.cmp_imm(7, 11)
    a.b("rfv_ov_learn", cond=0x1)
    a.mov_imm(0, 6); a.mov_imm(1, 6); a.mov_imm(2, 228); a.mov_imm(3, 148)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#60c8f8"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("MART (")); a.bl("fmt_str")
    a.ldr_imm(0, 6, 0x24); a.bl("fmt_u32")
    a.mov_imm(0, ui_off("G) A:Buy")); a.bl("fmt_str")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 12); a.mov_imm(2, 12); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Find current shop in Table 9
    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(0, 1, 0)
    a.ldr_imm(2, 0, 8)
    a.mov_imm(7, table_addrs[9])
    a.mov_imm(0, 0)
    a.label("rfv_shop_find")
    a.cmp_imm(0, 5); a.b("rfv_shop_found", cond=0x2)
    a.ldr_imm(1, 7, 0); a.cmp_reg(1, 2); a.b("rfv_shop_found", cond=0x0)
    a.add_imm(7, 7, 36); a.add_imm(0, 0, 1); a.b("rfv_shop_find")
    a.label("rfv_shop_found")
    a.ldr_imm(8, 7, 8)     # stock_len
    a.ldrb_imm(9, 5, 0x28) # shop_cursor
    a.sub_imm(10, 9, 4, s=1)
    a.mov_imm(10, 0, cond=0x4)
    a.mov_imm(11, 0)
    a.label("rfv_shop_lp")
    a.cmp_imm(11, 7)
    a.b("rfv_shop_desc", cond=0x2)
    a.add_reg(0, 10, 11)
    a.cmp_reg(0, 8)
    a.b("rfv_shop_desc", cond=0x2)
    a.bl("fmt_clear")
    a.add_reg(0, 10, 11)
    a.cmp_reg(0, 9)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.add_reg(0, 10, 11)
    a.add_reg(0, 7, 0)
    a.ldrb_imm(4, 0, 12) # item_idx
    a.mov_reg(0, 4); a.mov_imm(1, 17); a.bl("fmt_it_name_n")
    a.mov_imm(0, 32); a.bl("fmt_putc")
    a.mov_imm(0, 28); a.mul(0, 4, 0); a.mov_imm(1, table_addrs[8]); a.add_reg(0, 1, 0)
    a.ldrh_imm(0, 0, 6) # price
    a.bl("fmt_u32")
    a.mov_imm(0, 71); a.bl("fmt_putc")
    a.add_reg(0, 10, 11)
    a.cmp_reg(0, 9)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 14); a.mul(2, 11, 0); a.add_imm(2, 2, 30)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 12); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(11, 11, 1)
    a.b("rfv_shop_lp")
    a.label("rfv_shop_desc")
    a.add_reg(0, 7, 9)
    a.ldrb_imm(4, 0, 12)
    a.mov_imm(0, 28); a.mul(0, 4, 0); a.mov_imm(1, table_addrs[8]); a.add_reg(0, 1, 0)
    a.ldr_imm(4, 0, 16) # desc str_off
    a.bl("fmt_clear")
    a.mov_reg(0, 4); a.mov_imm(1, 27); a.bl("fmt_rom_off_n")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 12); a.mov_imm(2, 138); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # Overlay Screen 12: LEARN_MOVE
    a.label("rfv_ov_learn")
    a.mov_imm(0, 8); a.mov_imm(1, 8); a.mov_imm(2, 224); a.mov_imm(3, 144)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f0c040"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Teach ")); a.bl("fmt_str")
    a.ldrb_imm(0, 5, 0x3E); a.mov_imm(1, 255); a.bl("fmt_mv_name_n")
    a.mov_imm(0, 63); a.bl("fmt_putc")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 16); a.mov_imm(2, 16); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(0, ui_off("Replace which move:")); a.mov_imm(1, 16); a.mov_imm(2, 30); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.ldrb_imm(0, 5, 0x3D); a.mov_imm(1, 48); a.mul(8, 0, 1); a.add_imm(8, 8, 0x0B4); a.add_reg(8, 6, 8)
    a.ldrh_imm(9, 8, 0x12) # moveCount
    a.ldrb_imm(10, 5, 0x29) # learn_cursor
    a.mov_imm(11, 0)
    a.label("rfv_lm_lp")
    a.cmp_reg(11, 9)
    a.b("rfv_lm_cancel", cond=0x2)
    a.bl("fmt_clear")
    a.cmp_reg(11, 10)
    a.mov_imm(0, ui_off("> "), cond=0x0); a.mov_imm(0, ui_off("  "), cond=0x1)
    a.bl("fmt_str")
    a.add_reg(0, 8, 11); a.ldrb_imm(0, 0, 0x1C); a.mov_imm(1, 255); a.bl("fmt_mv_name_n")
    a.cmp_reg(11, 10)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 15); a.mul(2, 11, 0); a.add_imm(2, 2, 50)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 16); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(11, 11, 1)
    a.b("rfv_lm_lp")
    a.label("rfv_lm_cancel")
    a.cmp_imm(10, 4)
    a.mov_imm(0, ui_off("> Cancel / Skip"), cond=0x0); a.mov_imm(3, col("#f8e888"), cond=0x0)
    a.mov_imm(0, ui_off("  Cancel / Skip"), cond=0x1); a.mov_imm(3, col("#e63946"), cond=0x1)
    a.mov_imm(1, 16); a.mov_imm(2, 114); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # =========================================================================
    # Full-Screen Non-Overworld Screens (0, 1, 2, 5, 13, 14, 15, 16)
    # =========================================================================
    a.label("rfv_full_screen")
    a.mov_imm(0, 1)
    a.strb_imm(0, 5, 0x4B) # prev_full_bg0 = 1
    a.cmp_imm(7, 15) # CREDITS fills (0,0,240,160) via draw_box_vram
    a.b("rfv_fs_credits", cond=0x0)
    a.cmp_imm(7, 5)  # BATTLE fills y=0..159 directly via 3 DMA3 transfers
    a.b("rfv_fs_battle", cond=0x0)
    a.mov_imm(0, col("#101420"))
    a.mov_imm(1, 9600)
    a.bl("clear_bg0_vram")

    # Screen 0: TITLE
    a.cmp_imm(7, 0)
    a.b("rfv_fs_slots", cond=0x1)
    a.mov_imm(0, 4); a.mov_imm(1, 4); a.mov_imm(2, 232); a.mov_imm(3, 152)
    a.mov_imm(4, col("#1a1e34")); a.mov_imm(5, col("#f0c040"))
    a.bl("draw_box_vram")
    a.mov_imm(0, ui_off("bEATsts")); a.mov_imm(1, 92); a.mov_imm(2, 12); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 1)
    a.bl("draw_text_vram")
    a.mov_imm(0, ui_off("ConsciousNode SoftWorks")); a.mov_imm(1, 28); a.mov_imm(2, 32); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    for idx_s, sp_s in enumerate([1, 39, 77, 115]):
        a.mov_imm(0, sp_s); a.mov_imm(1, 0); a.mov_imm(2, 22 + idx_s * 52); a.mov_imm(3, 48); a.mov_imm(4, 1)
        a.bl("draw_sprite32_vram")
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(8, 5, 0x21) # cursor
    title_opts = ["PLAY / SAVE SLOTS", "OPTIONS", "CONTROLS"]
    for o_i, o_s in enumerate(title_opts):
        a.cmp_imm(8, o_i)
        a.mov_imm(0, ui_off("> " + o_s), cond=0x0); a.mov_imm(3, col("#f8e888"), cond=0x0)
        a.mov_imm(0, ui_off("  " + o_s), cond=0x1); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
        a.mov_imm(1, 44); a.mov_imm(2, 94 + o_i * 14); a.mov_imm(4, 0)
        a.bl("draw_text_vram")
    a.mov_imm(0, ui_off("Press Z / Enter / A")); a.mov_imm(1, 44); a.mov_imm(2, 140); a.mov_imm(3, col("#98d830")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # Screen 1: SLOTS
    a.label("rfv_fs_slots")
    a.cmp_imm(7, 1)
    a.b("rfv_fs_starter", cond=0x1)
    a.mov_imm(0, 6); a.mov_imm(1, 6); a.mov_imm(2, 228); a.mov_imm(3, 148)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(0, ui_off("SELECT SAVE SLOT")); a.mov_imm(1, 16); a.mov_imm(2, 12); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(8, 5, 0x21) # cursor
    a.mov_imm(9, 0)        # i = 0..2
    a.label("rfv_slots_lp")
    a.cmp_imm(9, 3)
    a.b("rfv_done", cond=0x2)
    a.mov_imm(0, 38); a.mul(10, 9, 0); a.add_imm(10, 10, 30) # y = 30 + i * 38
    a.cmp_reg(9, 8)
    a.mov_imm(4, col("#283854"), cond=0x0); a.mov_imm(5, col("#f8e888"), cond=0x0)
    a.mov_imm(4, col("#182234"), cond=0x1); a.mov_imm(5, col("#708090"), cond=0x1)
    a.mov_imm(0, 14); a.mov_reg(1, 10); a.mov_imm(2, 212); a.mov_imm(3, 32)
    a.bl("draw_box_vram")
    a.mov_reg(0, 9)
    a.bl("check_slot_valid")
    a.cmp_imm(0, 0)
    a.b("rfv_slot_empty", cond=0x0)
    # Valid slot in 0x02002000!
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("SLOT ")); a.bl("fmt_str")
    a.add_imm(0, 9, 1); a.bl("fmt_u32")
    a.mov_imm(0, ui_off(": ")); a.bl("fmt_str")
    a.mov_imm(0, 0x0200200C); a.bl("fmt_str")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 20); a.add_imm(2, 10, 5); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Line 2: "Seals:${badges}/8 Dex:${caught} ${mins}m"
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("Seals:")); a.bl("fmt_str")
    a.mov_imm(11, 0x02002000)
    a.ldrb_imm(1, 11, 0x2F)
    a.mov_imm(0, 0)
    for b_i in range(8):
        a.tst_imm(1, 1 << b_i)
        a.add_imm(0, 0, 1, cond=0x1)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off("/8 Dex:")); a.bl("fmt_str")
    a.mov_imm(0, 0)
    a.mov_imm(1, 0)
    a.label("rfv_sl_dex")
    a.add_reg(2, 11, 1)
    a.ldrb_imm(3, 2, 0x6A)
    for b_i in range(8):
        a.tst_imm(3, 1 << b_i)
        a.add_imm(0, 0, 1, cond=0x1)
    a.add_imm(1, 1, 1)
    a.cmp_imm(1, 20)
    a.b("rfv_sl_dex", cond=0x3)
    a.bl("fmt_u32")
    a.mov_imm(0, 32); a.bl("fmt_putc")
    a.ldr_imm(0, 11, 0x18) # playTimeFrames
    a.mov_imm(1, 3600)
    a.bl("udiv32")
    a.bl("fmt_u32")
    a.mov_imm(0, 109) # 'm'
    a.bl("fmt_putc")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 20); a.add_imm(2, 10, 17); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_slot_next")

    a.label("rfv_slot_empty")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("SLOT ")); a.bl("fmt_str")
    a.add_imm(0, 9, 1); a.bl("fmt_u32")
    a.mov_imm(0, ui_off(": [ NEW GAME ]")); a.bl("fmt_str")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 20); a.add_imm(2, 10, 11); a.mov_imm(3, col("#98d830")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")

    a.label("rfv_slot_next")
    a.add_imm(9, 9, 1)
    a.b("rfv_slots_lp")

    # Screen 2: STARTER
    a.label("rfv_fs_starter")
    a.cmp_imm(7, 2)
    a.b("rfv_fs_battle", cond=0x1)
    a.mov_imm(0, 6); a.mov_imm(1, 6); a.mov_imm(2, 228); a.mov_imm(3, 148)
    a.mov_imm(4, col("#182030")); a.mov_imm(5, col("#f0c040"))
    a.bl("draw_box_vram")
    a.mov_imm(0, ui_off("CHOOSE YOUR bEATst!")); a.mov_imm(1, 40); a.mov_imm(2, 12); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(8, 5, 0x2A) # starter_idx
    st_fams = [(1, "Sandw"), (39, "Dumpl"), (77, "Noodl"), (115, "Soup")]
    for s_i, (sp_id, fam_s) in enumerate(st_fams):
        x_card = 14 + s_i * 54
        a.cmp_imm(8, s_i)
        a.mov_imm(4, col("#304060"), cond=0x0); a.mov_imm(5, col("#f8e888"), cond=0x0)
        a.mov_imm(4, col("#1a2438"), cond=0x1); a.mov_imm(5, col("#506070"), cond=0x1)
        a.mov_imm(0, x_card); a.mov_imm(1, 28); a.mov_imm(2, 50); a.mov_imm(3, 62)
        a.bl("draw_box_vram")
        a.mov_imm(0, sp_id); a.mov_imm(1, 0); a.mov_imm(2, x_card + 9); a.mov_imm(3, 34); a.mov_imm(4, 1)
        a.bl("draw_sprite32_vram")
        a.mov_imm(0, ui_off(fam_s)); a.mov_imm(1, x_card + 5); a.mov_imm(2, 72); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
        a.bl("draw_text_vram")
    # Selected starter details
    a.mov_imm(0, 38); a.mul(9, 8, 0) # sp_idx = starter_idx * 38 (0, 38, 76, 114)
    a.mov_imm(0, 56); a.mul(10, 9, 0); a.mov_imm(0, table_addrs[4]); a.add_reg(10, 0, 10)
    a.bl("fmt_clear"); a.ldr_imm(0, 10, 32); a.bl("fmt_rom_off")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 14); a.mov_imm(2, 98); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.bl("fmt_clear")
    a.ldrb_imm(0, 10, 2); a.mov_imm(1, table_addrs[2]); a.add_reg(0, 1, 0, shift_imm=3, shift_type=0); a.ldr_imm(0, 0, 0); a.bl("fmt_rom_off")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 14); a.mov_imm(2, 110); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.bl("fmt_clear"); a.ldr_imm(0, 10, 36); a.mov_imm(1, 26); a.bl("fmt_rom_off_n")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 14); a.mov_imm(2, 124); a.mov_imm(3, col("#c0c8d0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(0, ui_off("L/R:Dish U/D:Look A:Go")); a.mov_imm(1, 14); a.mov_imm(2, 140); a.mov_imm(3, col("#98d830")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # Screen 5: BATTLE
    a.label("rfv_fs_battle")
    a.cmp_imm(7, 5)
    a.b("rfv_fs_options", cond=0x1)
    # Fast DMA3 fill of y=0..72 (4320 words at 0x06000040) with #243448, y=72..104 (1920 words at 0x060043C0) with #385068
    a.mov_imm(0, col("#243448"))
    a.orr_reg(0, 0, 0, shift_imm=8, shift_type=0)
    a.orr_reg(0, 0, 0, shift_imm=16, shift_type=0)
    a.mov_imm(1, 0x03000000)
    a.str_imm(0, 1, 0)
    a.mov_imm(2, 0x040000D4)
    a.str_imm(1, 2, 0)
    a.mov_imm(0, 0x06000040)
    a.str_imm(0, 2, 4)
    a.mov_imm(0, 0x85000000 | 4320)
    a.str_imm(0, 2, 8)
    a.mov_imm(0, col("#385068"))
    a.orr_reg(0, 0, 0, shift_imm=8, shift_type=0)
    a.orr_reg(0, 0, 0, shift_imm=16, shift_type=0)
    a.str_imm(0, 1, 0)
    a.str_imm(1, 2, 0)
    a.mov_imm(0, 0x060043C0)
    a.str_imm(0, 2, 4)
    a.mov_imm(0, 0x85000000 | 1920)
    a.str_imm(0, 2, 8)
    # DMA3 fill y=104..159 (3360 words at 0x060061C0) with #101420
    a.mov_imm(0, col("#101420"))
    a.orr_reg(0, 0, 0, shift_imm=8, shift_type=0)
    a.orr_reg(0, 0, 0, shift_imm=16, shift_type=0)
    a.str_imm(0, 1, 0)
    a.str_imm(1, 2, 0)
    a.mov_imm(0, 0x060061C0)
    a.str_imm(0, 2, 4)
    a.mov_imm(0, 0x85000000 | 3360)
    a.str_imm(0, 2, 8)
    a.mov_imm(0, 0); a.mov_imm(1, 72); a.mov_imm(2, 240); a.mov_imm(3, 4); a.mov_imm(4, col("#243448"))
    a.bl("fill_rect_vram")
    a.mov_imm(0, 0); a.mov_imm(1, 104); a.mov_imm(2, 240); a.mov_imm(3, 4); a.mov_imm(4, col("#385068"))
    a.bl("fill_rect_vram")
    a.mov_imm(8, 0x02001100)
    a.ldrsb_imm(9, 8, 6) # b.temp (-2..+2)
    temp_cfg = [
        (-2, "TEMP:CHILL -2", "#4cc9f0"),
        (-1, "TEMP:COOL -1", "#a8dadc"),
        (0,  "TEMP:ROOM 0",  "#f8f8f0"),
        (1,  "TEMP:WARM +1", "#e8a850"),
        (2,  "TEMP:SEAR +2", "#e63946"),
    ]
    for t_val, t_str, t_col in temp_cfg:
        if t_val < 0:
            a.cmn_imm(9, -t_val)
        else:
            a.cmp_imm(9, t_val)
        a.mov_imm(10, ui_off(t_str), cond=0x0)
        a.mov_imm(11, col(t_col), cond=0x0)
    a.mov_imm(0, 24); a.mov_imm(1, 2); a.mov_imm(2, 114); a.mov_imm(3, 12); a.mov_imm(4, col("#101824")); a.mov_reg(5, 11)
    a.bl("draw_box_vram")
    a.mov_reg(0, 10); a.mov_imm(1, 28); a.mov_imm(2, 4); a.mov_reg(3, 11); a.mov_imm(4, 0)
    a.bl("draw_text_vram")

    # Foe HUD & sprite
    a.mov_imm(0, 4); a.mov_imm(1, 16); a.mov_imm(2, 126); a.mov_imm(3, 28); a.mov_imm(4, col("#182030")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.ldrb_imm(0, 8, 4); a.mov_imm(1, 48); a.mul(9, 0, 1); a.add_imm(9, 9, 0x10); a.add_reg(9, 8, 9) # R9 = foe_ptr
    a.bl("fmt_clear")
    a.ldrb_imm(0, 9, 4); a.mov_imm(1, 10); a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" L")); a.bl("fmt_str")
    a.ldrb_imm(0, 9, 5); a.bl("fmt_u32")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 8); a.mov_imm(2, 19); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Foe HP bar
    a.mov_imm(0, 8); a.mov_imm(1, 30); a.mov_imm(2, 114); a.mov_imm(3, 5); a.mov_imm(4, col("#404858"))
    a.bl("fill_rect_vram")
    a.ldrh_imm(0, 9, 8)    # foe.hp
    a.ldrh_imm(1, 9, 0x0A) # foe.maxHp
    a.mov_imm(2, 10); a.mul(2, 0, 2)
    a.mov_imm(3, 3);  a.mul(3, 1, 3)
    a.cmp_reg(2, 3)
    a.mov_imm(10, col("#52b788"), cond=0x8)
    a.mov_imm(10, col("#e63946"), cond=0x9)
    a.mov_imm(2, 114); a.mul(0, 0, 2)
    a.bl("udiv32") # R0 = (114 * hp) // maxHp
    if control_mode == "hp_short":
        a.sub_imm(0, 0, 1, s=1)
        a.mov_imm(0, 0, cond=0x4)
    a.mov_reg(2, 0); a.mov_imm(0, 8); a.mov_imm(1, 30); a.mov_imm(3, 5); a.mov_reg(4, 10)
    a.bl("fill_rect_vram")
    # Foe status
    a.ldrb_imm(1, 9, 6)
    a.cmp_imm(1, 0)
    a.b("rfv_bat_foe_spr", cond=0x0)
    for st_i, st_s in [(1, "Sizzling"), (2, "Brined"), (3, "Drowsy"), (4, "Seasoned"), (5, "Appetized")]:
        a.cmp_imm(1, st_i)
        a.mov_imm(0, ui_off(st_s), cond=0x0)
    a.mov_imm(1, 8); a.mov_imm(2, 36); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.label("rfv_bat_foe_spr")
    a.ldrb_imm(0, 9, 4); a.mov_imm(1, 0); a.mov_imm(2, 164); a.mov_imm(3, 4); a.mov_imm(4, 2)
    a.bl("draw_sprite32_vram")

    # Player sprite & HUD
    a.mov_imm(6, 0x02000000)
    a.ldrb_imm(0, 8, 5); a.mov_imm(1, 48); a.mul(9, 0, 1); a.add_imm(9, 9, 0x0B4); a.add_reg(9, 6, 9) # R9 = player_ptr
    a.ldrb_imm(0, 9, 4); a.mov_imm(1, 1); a.mov_imm(2, 14); a.mov_imm(3, 44); a.mov_imm(4, 2)
    a.bl("draw_sprite32_vram")
    a.mov_imm(0, 100); a.mov_imm(1, 70); a.mov_imm(2, 136); a.mov_imm(3, 36); a.mov_imm(4, col("#182030")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.bl("fmt_clear")
    a.ldrb_imm(0, 9, 4); a.mov_imm(1, 10); a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" L")); a.bl("fmt_str")
    a.ldrb_imm(0, 9, 5); a.bl("fmt_u32")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 104); a.mov_imm(2, 73); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(0, 104); a.mov_imm(1, 84); a.mov_imm(2, 120); a.mov_imm(3, 5); a.mov_imm(4, col("#404858"))
    a.bl("fill_rect_vram")
    a.ldrh_imm(0, 9, 8)
    a.ldrh_imm(1, 9, 0x0A)
    a.mov_imm(2, 10); a.mul(2, 0, 2)
    a.mov_imm(3, 3);  a.mul(3, 1, 3)
    a.cmp_reg(2, 3)
    a.mov_imm(10, col("#52b788"), cond=0x8)
    a.mov_imm(10, col("#e63946"), cond=0x9)
    a.mov_imm(2, 120); a.mul(0, 0, 2)
    a.bl("udiv32")
    if control_mode == "hp_short":
        a.sub_imm(0, 0, 1, s=1)
        a.mov_imm(0, 0, cond=0x4)
    a.mov_reg(2, 0); a.mov_imm(0, 104); a.mov_imm(1, 84); a.mov_imm(3, 5); a.mov_reg(4, 10)
    a.bl("fill_rect_vram")
    a.bl("fmt_clear")
    a.mov_imm(0, ui_off("HP ")); a.bl("fmt_str")
    a.ldrh_imm(0, 9, 8); a.bl("fmt_u32")
    a.mov_imm(0, 47); a.bl("fmt_putc")
    a.ldrh_imm(0, 9, 0x0A); a.bl("fmt_u32")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 104); a.mov_imm(2, 93); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")

    # Battle Move Flash: mark 68x68 box at (150, 18) with +128 palette offset; rfv_done DMAs flash vs normal palette
    a.bl("apply_battle_flash_vram")

    # Bottom panel: drawBox(2, 108, 236, 50, '#141C2C', '#F8F8F0')
    a.mov_imm(0, 2); a.mov_imm(1, 108); a.mov_imm(2, 236); a.mov_imm(3, 50); a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.ldrb_imm(10, 8, 8) # b.phase
    a.ldrb_imm(11, 8, 9) # b.cursor

    # Phase 6: LOG
    a.cmp_imm(10, 6)
    a.b("rfv_bat_p_main", cond=0x1)
    a.mov_imm(0, 0x02003400); a.mov_imm(1, 8); a.mov_imm(2, 113); a.mov_imm(3, 150)
    a.bl("draw_wrapped_text_vram")
    a.b("rfv_done")

    # Phase 1: MAIN
    a.label("rfv_bat_p_main")
    a.cmp_imm(10, 1)
    a.b("rfv_bat_p_fight", cond=0x1)
    a.bl("fmt_clear")
    a.mov_imm(0, 0x02003400); a.mov_imm(1, 27); a.bl("fmt_str_n")
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 8); a.mov_imm(2, 113); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    bat_opts = [("FIGHT", 16, 128), ("PLATE", 126, 128), ("BAG", 16, 141), ("PARTY", 126, 141)]
    for o_i, (o_s, o_x, o_y) in enumerate(bat_opts):
        a.cmp_imm(11, o_i)
        a.mov_imm(0, ui_off("> " + o_s), cond=0x0); a.mov_imm(3, col("#f8e888"), cond=0x0)
        a.mov_imm(0, ui_off("  " + o_s), cond=0x1); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
        a.mov_imm(1, o_x); a.mov_imm(2, o_y); a.mov_imm(4, 0)
        a.bl("draw_text_vram")
    a.b("rfv_done")

    # Phase 2: FIGHT
    a.label("rfv_bat_p_fight")
    a.cmp_imm(10, 2)
    a.b("rfv_bat_p_plate", cond=0x1)
    a.ldrh_imm(6, 9, 0x12) # player.moveCount
    a.mov_imm(7, 0)        # i = 0
    a.label("rfv_bf_lp")
    a.cmp_reg(7, 6)
    a.b("rfv_done", cond=0x2)
    a.bl("fmt_clear")
    a.cmp_reg(7, 11)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.add_reg(0, 9, 7); a.ldrb_imm(4, 0, 0x1C) # moveId
    a.mov_reg(0, 4); a.mov_imm(1, 12); a.bl("fmt_mv_name_n")
    a.and_imm(1, 7, 1); a.mov_imm(2, 118); a.mul(1, 1, 2); a.add_imm(1, 1, 6) # x
    a.mov_reg(2, 7, shift_imm=1, shift_type=1); a.mov_imm(3, 21); a.mul(2, 2, 3); a.add_imm(2, 2, 113) # y
    a.cmp_reg(7, 11)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.push([1, 2, 4])
    a.mov_imm(0, 0x02003610); a.mov_imm(4, 0); a.bl("draw_text_vram")
    a.pop([1, 2, 4])
    # Line 2: "${mv.type.slice(0,5)} ${ms.pp}/${ms.maxPp}" at (x + 8, y + 10)
    a.push([1, 2])
    a.bl("fmt_clear")
    a.mov_imm(0, 36); a.mul(0, 4, 0); a.mov_imm(1, table_addrs[3]); a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 1) # t_idx
    a.mov_imm(1, table_addrs[2]); a.add_reg(0, 1, 0, shift_imm=3, shift_type=0); a.ldr_imm(0, 0, 0)
    a.mov_imm(1, 5); a.bl("fmt_rom_off_n")
    a.mov_imm(0, 32); a.bl("fmt_putc")
    a.add_reg(0, 9, 7); a.ldrb_imm(0, 0, 0x20); a.bl("fmt_u32")
    a.mov_imm(0, 47); a.bl("fmt_putc")
    a.add_reg(0, 9, 7); a.ldrb_imm(0, 0, 0x24); a.bl("fmt_u32")
    a.pop([1, 2])
    a.add_imm(1, 1, 8); a.add_imm(2, 2, 10)
    a.mov_imm(0, 0x02003610); a.mov_imm(3, col("#a8dadc")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(7, 7, 1)
    a.b("rfv_bf_lp")

    # Phase 3: PLATE
    a.label("rfv_bat_p_plate")
    a.cmp_imm(10, 3)
    a.b("rfv_bat_p_bag", cond=0x1)
    a.mov_imm(0, 1); a.mov_reg(1, 13); a.bl("build_bag_filter")
    a.mov_reg(6, 0)
    a.cmp_imm(6, 0)
    a.b("rfv_bp_list", cond=0x1)
    a.mov_imm(0, ui_off("No plates/treats! (B)")); a.mov_imm(1, 10); a.mov_imm(2, 122); a.mov_imm(3, col("#e63946")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")
    a.label("rfv_bp_list")
    a.cmp_imm(6, 4); a.mov_imm(6, 4, cond=0x8)
    a.mov_imm(7, 0)
    a.label("rfv_bp_lp")
    a.cmp_reg(7, 6)
    a.b("rfv_done", cond=0x2)
    a.bl("fmt_clear")
    a.cmp_reg(7, 11)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.add_reg(0, 13, 7); a.ldrb_imm(4, 0, 0) # item_idx
    a.mov_reg(0, 4); a.mov_imm(1, 15); a.bl("fmt_it_name_n")
    a.mov_imm(0, ui_off(" x")); a.bl("fmt_str")
    a.mov_imm(0, 0x0200007E); a.add_reg(0, 0, 4, shift_imm=1, shift_type=0); a.ldrh_imm(0, 0, 0)
    a.bl("fmt_u32")
    # Check if item is plate (0) vs treat (4)
    a.mov_imm(0, 28); a.mul(0, 4, 0); a.mov_imm(1, table_addrs[8]); a.add_reg(0, 1, 0)
    a.ldrb_imm(0, 0, 0)
    a.cmp_imm(0, 0)
    a.b("rfv_bp_trt", cond=0x1)
    a.mov_imm(0, 32); a.bl("fmt_putc")
    a.ldrb_imm(0, 8, 4); a.mov_imm(1, 48); a.mul(0, 0, 1); a.add_imm(0, 0, 0x10); a.add_reg(0, 8, 0) # foe_ptr
    a.mov_reg(1, 4)
    a.bl("calc_plating_chance")
    a.bl("f64_round_pct")
    a.bl("fmt_u32")
    a.mov_imm(0, 37); a.bl("fmt_putc") # '%'
    a.b("rfv_bp_draw")
    a.label("rfv_bp_trt")
    a.mov_imm(0, ui_off(" TRT")); a.bl("fmt_str")
    a.label("rfv_bp_draw")
    a.cmp_reg(7, 11)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 11); a.mul(2, 7, 0); a.add_imm(2, 2, 113)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 6); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(7, 7, 1)
    a.b("rfv_bp_lp")

    # Phase 4: BAG
    a.label("rfv_bat_p_bag")
    a.cmp_imm(10, 4)
    a.b("rfv_bat_p_party", cond=0x1)
    a.mov_imm(0, 2); a.mov_reg(1, 13); a.bl("build_bag_filter")
    a.mov_reg(6, 0)
    a.cmp_imm(6, 0)
    a.b("rfv_bb_list", cond=0x1)
    a.mov_imm(0, ui_off("No healing items! (B)")); a.mov_imm(1, 10); a.mov_imm(2, 122); a.mov_imm(3, col("#e63946")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")
    a.label("rfv_bb_list")
    a.cmp_imm(6, 4); a.mov_imm(6, 4, cond=0x8)
    a.mov_imm(7, 0)
    a.label("rfv_bb_lp")
    a.cmp_reg(7, 6)
    a.b("rfv_done", cond=0x2)
    a.bl("fmt_clear")
    a.cmp_reg(7, 11)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.add_reg(0, 13, 7); a.ldrb_imm(4, 0, 0)
    a.mov_reg(0, 4); a.mov_imm(1, 18); a.bl("fmt_it_name_n")
    a.mov_imm(0, ui_off(" x")); a.bl("fmt_str")
    a.mov_imm(0, 0x0200007E); a.add_reg(0, 0, 4, shift_imm=1, shift_type=0); a.ldrh_imm(0, 0, 0)
    a.bl("fmt_u32")
    a.cmp_reg(7, 11)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 11); a.mul(2, 7, 0); a.add_imm(2, 2, 113)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 6); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(7, 7, 1)
    a.b("rfv_bb_lp")

    # Phase 5: PARTY
    a.label("rfv_bat_p_party")
    a.mov_imm(6, 0x02000000)
    a.ldrb_imm(6, 6, 0x0B0)
    a.cmp_imm(6, 4); a.mov_imm(6, 4, cond=0x8)
    a.mov_imm(7, 0)
    a.label("rfv_bpty_lp")
    a.cmp_reg(7, 6)
    a.b("rfv_done", cond=0x2)
    a.bl("fmt_clear")
    a.cmp_reg(7, 11)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.mov_imm(0, 48); a.mul(4, 7, 0); a.add_imm(4, 4, 0x0B4); a.add_imm(4, 4, 0x02000000)
    a.ldrb_imm(0, 4, 4); a.mov_imm(1, 12); a.bl("fmt_sp_name_n")
    a.mov_imm(0, 32); a.bl("fmt_putc")
    a.ldrh_imm(0, 4, 8); a.bl("fmt_u32")
    a.mov_imm(0, 47); a.bl("fmt_putc")
    a.ldrh_imm(0, 4, 0x0A); a.bl("fmt_u32")
    a.cmp_reg(7, 11)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 11); a.mul(2, 7, 0); a.add_imm(2, 2, 113)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 6); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(7, 7, 1)
    a.b("rfv_bpty_lp")

    # Screen 13: OPTIONS
    a.label("rfv_fs_options")
    a.cmp_imm(7, 13)
    a.b("rfv_fs_controls", cond=0x1)
    a.mov_imm(0, 12); a.mov_imm(1, 12); a.mov_imm(2, 216); a.mov_imm(3, 136)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(0, ui_off("OPTIONS")); a.mov_imm(1, 92); a.mov_imm(2, 20); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 1)
    a.bl("draw_text_vram")
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(8, 5, 0x21) # cursor
    # Row 0: Text speed
    a.bl("fmt_clear")
    a.cmp_imm(8, 0)
    a.mov_imm(0, ui_off("> Text : < "), cond=0x0); a.mov_imm(0, ui_off("  Text : < "), cond=0x1)
    a.bl("fmt_str")
    a.ldrb_imm(1, 5, 0x2E) # textSpeed (1..3)
    a.cmp_imm(1, 1); a.mov_imm(0, ui_off("Slow >"), cond=0x0)
    a.cmp_imm(1, 2); a.mov_imm(0, ui_off("Normal >"), cond=0x0)
    a.cmp_imm(1, 3); a.mov_imm(0, ui_off("Fast >"), cond=0x0)
    a.bl("fmt_str")
    a.cmp_imm(8, 0)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 28); a.mov_imm(2, 54); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Row 1: Volume
    a.bl("fmt_clear")
    a.cmp_imm(8, 1)
    a.mov_imm(0, ui_off("> Vol  : < "), cond=0x0); a.mov_imm(0, ui_off("  Vol  : < "), cond=0x1)
    a.bl("fmt_str")
    a.ldrb_imm(0, 5, 0x2F)
    a.bl("fmt_u32")
    a.mov_imm(0, ui_off("% >"))
    a.bl("fmt_str")
    a.cmp_imm(8, 1)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 28); a.mov_imm(2, 72); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Row 2: Back
    a.cmp_imm(8, 2)
    a.mov_imm(0, ui_off("> Back"), cond=0x0); a.mov_imm(3, col("#f8e888"), cond=0x0)
    a.mov_imm(0, ui_off("  Back"), cond=0x1); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(1, 28); a.mov_imm(2, 90); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # Screen 14: CONTROLS
    a.label("rfv_fs_controls")
    a.cmp_imm(7, 14)
    a.b("rfv_fs_credits", cond=0x1)
    a.mov_imm(0, 8); a.mov_imm(1, 8); a.mov_imm(2, 224); a.mov_imm(3, 144)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(0, ui_off("CONTROLS")); a.mov_imm(1, 88); a.mov_imm(2, 14); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 1)
    a.bl("draw_text_vram")
    ctrl_lines = [
        "Move : Arrows / WASD / DPad",
        "A    : Z / Enter / Space",
        "B    : X / Esc / Backspace",
        "Menu : M (Start)",
        "Time : N (Select Day/Night)",
    ]
    for c_i, c_s in enumerate(ctrl_lines):
        a.mov_imm(0, ui_off(c_s)); a.mov_imm(1, 14); a.mov_imm(2, 42 + c_i * 15); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
        a.bl("draw_text_vram")
    a.mov_imm(0, ui_off("Press A or B to return")); a.mov_imm(1, 32); a.mov_imm(2, 132); a.mov_imm(3, col("#98d830")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # Screen 15: CREDITS
    a.label("rfv_fs_credits")
    a.cmp_imm(7, 15)
    a.b("rfv_fs_name_entry", cond=0x1)
    a.mov_imm(0, 0); a.mov_imm(1, 0); a.mov_imm(2, 240); a.mov_imm(3, 160)
    a.mov_imm(4, col("#101424")); a.mov_imm(5, col("#f0c040"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000); a.mov_imm(6, 0x02000000)
    a.ldrh_imm(8, 5, 0x38) # credits_scroll_px
    a.rsb_imm(8, 8, 160)   # R8 = base_y = 160 - creditsScroll
    # Line 0: 'bEATsts' (Serif, '#F8E888')
    a.mov_imm(0, ui_off("bEATsts")); a.mov_imm(1, 20); a.mov_reg(2, 8); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 1)
    a.bl("draw_text_vram")
    # Line 1: 'CONSCIOUSNODE SOFTWORKS' ('#F8E888')
    a.mov_imm(0, ui_off("CONSCIOUSNODE SOFTWORKS")); a.mov_imm(1, 20); a.add_imm(2, 8, 16); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Line 2: 'MIT License' ('#F8E888')
    a.mov_imm(0, ui_off("MIT License")); a.mov_imm(1, 20); a.add_imm(2, 8, 32); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Line 4: 'GRAND CHEF-TAMER:'
    a.mov_imm(0, ui_off("GRAND CHEF-TAMER:")); a.mov_imm(1, 20); a.add_imm(2, 8, 64); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Line 5: state.name
    a.add_imm(0, 6, 0x0C); a.mov_imm(1, 20); a.add_imm(2, 8, 80); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Line 7: 'CHAMPION PARTY:'
    a.mov_imm(0, ui_off("CHAMPION PARTY:")); a.mov_imm(1, 20); a.add_imm(2, 8, 112); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.ldrb_imm(9, 6, 0x0B0) # partyCount
    a.mov_imm(10, 0)
    a.label("rfv_cred_pty")
    a.cmp_reg(10, 9)
    a.b("rfv_cred_footer", cond=0x2)
    a.bl("fmt_clear")
    a.mov_imm(0, 48); a.mul(11, 10, 0); a.add_imm(11, 11, 0x0B4); a.add_reg(11, 6, 11)
    a.ldrb_imm(0, 11, 4); a.mov_imm(1, 255); a.bl("fmt_sp_name_n")
    a.mov_imm(0, ui_off(" L")); a.bl("fmt_str")
    a.ldrb_imm(0, 11, 5); a.bl("fmt_u32")
    a.add_imm(2, 10, 8)
    a.mov_reg(2, 2, shift_imm=4, shift_type=0)
    a.add_reg(2, 8, 2)
    a.mov_imm(0, 0x02003610); a.mov_imm(1, 20); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(10, 10, 1)
    a.b("rfv_cred_pty")
    a.label("rfv_cred_footer")
    a.add_imm(9, 9, 9)
    a.mov_reg(9, 9, shift_imm=4, shift_type=0)
    a.add_reg(9, 8, 9)
    a.mov_imm(0, ui_off("Thank you for playing!")); a.mov_imm(1, 20); a.mov_reg(2, 9); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(0, ui_off("Press A or B to continue")); a.mov_imm(1, 20); a.add_imm(2, 9, 16); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.b("rfv_done")

    # Screen 16: NAME_ENTRY
    a.label("rfv_fs_name_entry")
    a.mov_imm(0, 6); a.mov_imm(1, 6); a.mov_imm(2, 228); a.mov_imm(3, 148)
    a.mov_imm(4, col("#141c2c")); a.mov_imm(5, col("#f0c040"))
    a.bl("draw_box_vram")
    a.mov_imm(0, ui_off("ENTER CHEF NAME:")); a.mov_imm(1, 16); a.mov_imm(2, 12); a.mov_imm(3, col("#f8e888")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.mov_imm(0, 16); a.mov_imm(1, 24); a.mov_imm(2, 208); a.mov_imm(3, 18)
    a.mov_imm(4, col("#182030")); a.mov_imm(5, col("#f8f8f0"))
    a.bl("draw_box_vram")
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(0, 5, 0x94)
    a.cmp_imm(0, 0)
    a.mov_imm(0, ui_off("Brie"), cond=0x0)
    a.add_imm(0, 5, 0x94, cond=0x1)
    a.mov_imm(1, 22); a.mov_imm(2, 29); a.mov_imm(3, col("#f8f8f0")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    # Draw 10x4 character grid
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(8, 5, 0x90) # cx
    a.ldrb_imm(9, 5, 0x91) # cy
    a.mov_imm(0, 10); a.mul(9, 9, 0); a.add_reg(9, 9, 8) # sel_idx = cy * 10 + cx
    a.ldrb_imm(10, 5, 0x92) # upper
    a.mov_imm(11, 0) # idx = 0..39
    a.label("rfv_ne_lp")
    a.cmp_imm(11, 40)
    a.b("rfv_ne_footer", cond=0x2)
    a.bl("fmt_clear")
    a.cmp_reg(11, 9)
    a.mov_imm(0, 62, cond=0x0); a.mov_imm(0, 32, cond=0x1)
    a.bl("fmt_putc")
    a.cmp_imm(11, 39)
    a.b("rfv_ne_not_ok", cond=0x1)
    a.mov_imm(0, ui_off("OK")); a.bl("fmt_str")
    a.b("rfv_ne_draw_cell")
    a.label("rfv_ne_not_ok")
    a.mov_imm(0, 95) # '_' for space cells 36..38
    a.cmp_imm(11, 26)
    a.b("rfv_ne_dig", cond=0x2)
    a.cmp_imm(10, 0)
    a.add_imm(0, 11, 97, cond=0x0)
    a.add_imm(0, 11, 65, cond=0x1)
    a.b("rfv_ne_put")
    a.label("rfv_ne_dig")
    a.cmp_imm(11, 36)
    a.add_imm(0, 11, 48 - 26, cond=0x3)
    a.label("rfv_ne_put")
    a.bl("fmt_putc")
    a.label("rfv_ne_draw_cell")
    a.mov_reg(0, 11); a.mov_imm(1, 10); a.bl("udiv32") # R0 = row, R1 = col
    a.mov_imm(2, 18); a.mul(2, 0, 2); a.add_imm(2, 2, 50) # y = 50 + row * 18
    a.mov_imm(0, 20); a.mul(1, 1, 0); a.add_imm(1, 1, 14) # x = 14 + col * 20
    a.cmp_reg(11, 9)
    a.mov_imm(3, col("#f8e888"), cond=0x0); a.mov_imm(3, col("#f8f8f0"), cond=0x1)
    a.mov_imm(0, 0x02003610); a.mov_imm(4, 0)
    a.bl("draw_text_vram")
    a.add_imm(11, 11, 1)
    a.b("rfv_ne_lp")
    a.label("rfv_ne_footer")
    a.mov_imm(0, ui_off("A:Type B:Del L:Case START:OK")); a.mov_imm(1, 12); a.mov_imm(2, 138); a.mov_imm(3, col("#98d830")); a.mov_imm(4, 0)
    a.bl("draw_text_vram")

    a.label("rfv_done")
    a.mov_imm(5, 0x02001000)
    a.mov_imm(6, 0x02000000)
    # Catch up tick_frame_timers for any VBlank that elapsed during heavy VRAM rendering
    a.label("rfv_catchup_loop")
    a.ldr_imm(0, 5, 0x10) # vblank_count
    a.ldr_imm(1, 5, 0x14) # vblank_start
    a.cmp_reg(1, 0)
    a.b("rfv_catchup_done", cond=0x2)
    a.add_imm(1, 1, 1)
    a.str_imm(1, 5, 0x14)
    a.bl("tick_frame_timers")
    a.b("rfv_catchup_loop")
    a.label("rfv_catchup_done")

    # Update BG_PALETTE[0..15, 124..127] & OBJ_PALETTE for day/night/dark + post-catchup transitionTimer fade
    a.ldrb_imm(7, 5, 0x20) # screen_id
    a.mov_imm(0, 0) # pal_key = 0 on non-overworld full screens
    a.cmp_imm(7, 3); a.cmp_imm(7, 4, cond=0x1); a.cmp_imm(7, 6, cond=0x1)
    a.cmp_imm(7, 7, cond=0x1); a.cmp_imm(7, 8, cond=0x1); a.cmp_imm(7, 9, cond=0x1)
    a.cmp_imm(7, 10, cond=0x1); a.cmp_imm(7, 11, cond=0x1); a.cmp_imm(7, 12, cond=0x1)
    a.b("rfv_pal_set", cond=0x1)
    a.ldrb_imm(0, 6, 0x28)
    a.mov_imm(1, 40); a.mul(0, 0, 1); a.mov_imm(1, table_addrs[10]); a.add_reg(4, 1, 0)
    a.ldrb_imm(0, 6, 0x2C) # isNight (0..1)
    a.ldrb_imm(1, 4, 14)   # map.dark (0..1)
    a.orr_reg(0, 0, 1, shift_imm=1, shift_type=0)
    a.ldrh_imm(1, 5, 0x32) # transition_timer_frames (0..14)
    a.orr_reg(0, 0, 1, shift_imm=2, shift_type=0)
    a.label("rfv_pal_set")
    a.ldrb_imm(1, 5, 0x4A) # loaded_pal_mode
    a.cmp_reg(0, 1)
    a.b("rfv_pal_ok", cond=0x0)
    a.strb_imm(0, 5, 0x4A)
    a.mov_imm(1, 40)
    a.mul(1, 0, 1)
    a.mov_imm(2, tile_pal_modes_rom_addr)
    a.add_reg(1, 2, 1)
    a.mov_imm(2, 0x05000000)
    for w_i in range(8):
        a.ldr_imm(3, 1, w_i * 4)
        a.str_imm(3, 2, w_i * 4)
    a.ldr_imm(3, 1, 32)
    a.str_imm(3, 2, 0xF8)
    a.ldr_imm(3, 1, 36)
    a.str_imm(3, 2, 0xFC)
    a.mov_reg(1, 0, shift_imm=1, shift_type=1)
    a.mov_reg(1, 1, shift_imm=8, shift_type=0)
    a.mov_imm(2, dark_obj_pal_rom_addr)
    a.add_reg(1, 2, 1)
    a.mov_imm(2, 0x05000200)
    a.mov_imm(3, 0x04000000)
    a.str_imm(1, 3, 0xD4)
    a.str_imm(2, 3, 0xD8)
    a.mov_imm(1, 0x84000000 | 64)
    a.str_imm(1, 3, 0xDC)
    a.label("rfv_pal_ok")

    # On BATTLE (screen == 5), keep BG_PALETTE[128..255] (0x05000100) synced with frame_counter < anim_end_fc
    a.ldrb_imm(7, 5, 0x20)
    a.cmp_imm(7, 5)
    a.b("rfv_bflash_pal_ok", cond=0x1)
    a.ldr_imm(0, 5, 0x0C) # frame_counter (== romFc at rfv_done)
    a.ldr_imm(1, 5, 0x54) # anim_end_fc
    a.cmp_reg(0, 1)
    a.mov_imm(1, master_pal_rom_addr, cond=0x2)
    a.b("rfv_bflash_do_dma", cond=0x2)
    a.ldrb_imm(0, 5, 0x3B) # anim_type
    a.mov_imm(1, 0)
    a.cmp_imm(0, 1); a.mov_imm(1, 1, cond=0x0)
    a.cmp_imm(0, 7); a.mov_imm(1, 2, cond=0x0)
    a.mov_reg(1, 1, shift_imm=8, shift_type=0)
    a.mov_imm(2, battle_flash_pals_rom_addr)
    a.add_reg(1, 2, 1)
    a.label("rfv_bflash_do_dma")
    a.mov_imm(2, 0x05000100)
    a.mov_imm(3, 0x04000000)
    a.str_imm(1, 3, 0xD4)
    a.str_imm(2, 3, 0xD8)
    a.mov_imm(1, 0x84000000 | 64)
    a.str_imm(1, 3, 0xDC)
    a.label("rfv_bflash_pal_ok")

    # Update water/grass animTick = ((frame_counter + 1) // 18) % 2 at the END of render_frame_to_vram
    a.mov_imm(5, 0x02001000)
    a.ldr_imm(0, 5, 0x0C) # frame_counter
    a.add_imm(0, 0, 1)    # + 1 so VBlank of (romFc - 1) prepares exact animTick for VDraw of romFc!
    a.mov_imm(1, 18)
    a.bl("udiv32")
    a.and_imm(0, 0, 1) # animTick (0 or 1)
    a.ldrb_imm(1, 5, 0x49) # loaded_anim_tick
    a.cmp_reg(0, 1)
    a.b("rfv_anim_ok", cond=0x0)
    a.strb_imm(0, 5, 0x49)
    a.cmp_imm(0, 0)
    a.mov_imm(1, tiles_anim0_rom_addr, cond=0x0)
    a.mov_imm(1, tiles_anim1_rom_addr, cond=0x1)
    a.mov_imm(2, 0x0600C000)
    a.mov_imm(3, 0x04000000)
    a.str_imm(1, 3, 0xD4)
    a.str_imm(2, 3, 0xD8)
    a.mov_imm(1, 0x84000000 | 592)
    a.str_imm(1, 3, 0xDC)
    a.label("rfv_anim_ok")
    a.add_imm(13, 13, 32)
    a.pop([4, 5, 6, 7, 8, 9, 10, 11, 15])
    a.flush_literals()

    # =========================================================================
    # Mailbox Writer: write_mailbox() -> populates 0x0203FC00..0x0203FDFF
    # =========================================================================
    a.label("write_mailbox")
    a.push([4, 5, 6, 7, 8, 9, 14])
    a.mov_imm(4, 0x0203FC00)
    a.mov_imm(5, 0x02001000)
    a.mov_imm(6, 0x02000000)

    a.mov_imm(0, 0x42454154)
    a.str_imm(0, 4, 0x00)
    a.ldr_imm(0, 5, 0x0C)
    a.str_imm(0, 4, 0x04)
    # Only set acceptingInput = 1 when prev_keys == 0 (all buttons released) and clean_vdraw_countdown == 0
    a.ldrh_imm(0, 5, 0x1A) # prev_keys
    a.ldrb_imm(1, 5, 0x4C) # clean_vdraw_countdown
    a.orr_reg(0, 0, 1, s=1)
    a.mov_imm(0, 1, cond=0x0)
    a.mov_imm(0, 0, cond=0x1)
    a.strb_imm(0, 4, 0x08)
    a.cmp_imm(1, 0)
    a.sub_imm(1, 1, 1, cond=0x1)
    a.strb_imm(1, 5, 0x4C, cond=0x1)
    a.ldrb_imm(0, 5, 0x48)
    a.strb_imm(0, 4, 0x09)
    a.ldrb_imm(0, 5, 0x20)
    a.strb_imm(0, 4, 0x0C)
    a.ldrb_imm(0, 6, 0x28)
    a.strb_imm(0, 4, 0x0D)
    a.ldrb_imm(0, 6, 0x29)
    a.strb_imm(0, 4, 0x0E)
    a.ldrb_imm(0, 6, 0x2A)
    a.strb_imm(0, 4, 0x0F)
    a.ldrb_imm(0, 6, 0x2B)
    a.strb_imm(0, 4, 0x10)
    a.ldrb_imm(0, 6, 0x2C)
    a.strb_imm(0, 4, 0x11)

    a.ldrb_imm(1, 6, 0x2F)
    a.strb_imm(1, 4, 0x13)
    a.mov_imm(0, 0)
    for b_i in range(8):
        a.tst_imm(1, 1 << b_i)
        a.add_imm(0, 0, 1, cond=0x1)
    a.strb_imm(0, 4, 0x12)

    a.ldr_imm(0, 6, 0x24)
    a.str_imm(0, 4, 0x14)
    a.ldrb_imm(0, 6, 0x2E)
    a.strb_imm(0, 4, 0x18)
    a.ldrb_imm(0, 6, 0x0B0)
    a.strb_imm(0, 4, 0x19)
    a.ldrh_imm(0, 6, 0x42)
    a.strh_imm(0, 4, 0x1A)

    a.ldrh_imm(7, 6, 0x42)
    a.ldrh_imm(8, 6, 0x44)
    a.mov_imm(0, 0x811C9DC5)
    a.mov_imm(9, 0x01000193)
    a.mov_imm(1, 0)
    a.label("wm_qhash")
    a.cmp_imm(1, 16)
    a.b("wm_qhash_done", cond=0x2)
    a.mov_reg_rs(2, 7, 1, shift_type=1)
    a.and_imm(2, 2, 1)
    a.mov_reg_rs(3, 8, 1, shift_type=1)
    a.and_imm(3, 3, 1)
    a.orr_reg(2, 2, 3, shift_imm=1, shift_type=0)
    a.add_reg(3, 6, 1)
    a.ldrb_imm(3, 3, 0x46)
    a.and_imm(3, 3, 0xF)
    a.orr_reg(2, 2, 3, shift_imm=2, shift_type=0)
    a.eor_reg(0, 0, 2)
    a.mul(0, 0, 9)
    a.add_imm(1, 1, 1)
    a.b("wm_qhash")
    a.label("wm_qhash_done")
    a.str_imm(0, 4, 0x1C)

    # Copy dexSeenBits (20B at 0x02000056) and dexCaughtBits (20B at 0x0200006A) using ONLY byte access (ldrb/strb)!
    for b_i in range(20):
        a.ldrb_imm(0, 6, 0x56 + b_i)
        a.strb_imm(0, 4, 0x20 + b_i)
        a.ldrb_imm(0, 6, 0x6A + b_i)
        a.strb_imm(0, 4, 0x34 + b_i)

    a.add_imm(7, 4, 0x48)
    a.add_imm(8, 6, 0x0B4)
    a.mov_imm(9, 0)
    a.label("wm_party")
    a.cmp_imm(9, 6)
    a.b("wm_party_done", cond=0x2)
    a.ldrb_imm(0, 8, 4); a.strb_imm(0, 7, 0)
    a.ldrb_imm(0, 8, 5); a.strb_imm(0, 7, 1)
    a.ldrh_imm(0, 8, 8); a.strh_imm(0, 7, 2)
    a.ldrh_imm(0, 8, 0x0A); a.strh_imm(0, 7, 4)
    a.ldrb_imm(0, 8, 6); a.strb_imm(0, 7, 6)
    a.ldrb_imm(0, 8, 0x12); a.strb_imm(0, 7, 7)
    a.ldr_imm(0, 8, 0x1C); a.str_imm(0, 7, 8)
    a.add_imm(7, 7, 12)
    a.add_imm(8, 8, 48)
    a.add_imm(9, 9, 1)
    a.b("wm_party")
    a.label("wm_party_done")

    a.ldr_imm(0, 5, 0x04); a.str_imm(0, 4, 0x90)
    a.ldr_imm(0, 6, 0x20); a.str_imm(0, 4, 0x94)
    a.ldrb_imm(0, 6, 0x0B1); a.strh_imm(0, 4, 0x98)
    a.ldrh_imm(0, 6, 0x40); a.strh_imm(0, 4, 0x9A)
    a.mov_imm(0, TABLE_DIR_ROM_ADDR)
    a.str_imm(0, 4, 0x9C)

    a.mov_imm(7, 0x02001100)
    a.ldrb_imm(0, 7, 8); a.strb_imm(0, 4, 0xA0)
    a.ldrb_imm(0, 7, 9); a.strb_imm(0, 4, 0xA1)
    a.ldrb_imm(0, 7, 6); a.strb_imm(0, 4, 0xA2)
    a.ldrb_imm(0, 7, 0x0A); a.strb_imm(0, 4, 0xA3)
    a.ldrb_imm(1, 7, 5)
    a.mov_imm(2, 48); a.mul(2, 1, 2); a.add_imm(2, 2, 0x0B4); a.add_reg(2, 6, 2)
    a.ldrb_imm(0, 2, 4); a.strb_imm(0, 4, 0xA4)
    a.ldrb_imm(0, 2, 5); a.strb_imm(0, 4, 0xA5)
    a.ldrh_imm(0, 2, 8); a.strh_imm(0, 4, 0xA6)
    a.ldrh_imm(0, 2, 0x0A); a.strh_imm(0, 4, 0xA8)
    a.ldrb_imm(0, 2, 6); a.strb_imm(0, 4, 0xAA)
    a.strb_imm(1, 4, 0xAB)
    a.ldrb_imm(1, 7, 4)
    a.mov_imm(2, 48); a.mul(2, 1, 2); a.add_imm(2, 2, 0x10); a.add_reg(2, 7, 2)
    a.ldrb_imm(0, 2, 4); a.strb_imm(0, 4, 0xAC)
    a.ldrb_imm(0, 2, 5); a.strb_imm(0, 4, 0xAD)
    a.ldrh_imm(0, 2, 8); a.strh_imm(0, 4, 0xAE)
    a.ldrh_imm(0, 2, 0x0A); a.strh_imm(0, 4, 0xB0)
    a.ldrb_imm(0, 2, 6); a.strb_imm(0, 4, 0xB2)
    a.strb_imm(1, 4, 0xB3)
    a.ldr_imm(0, 5, 0x08); a.str_imm(0, 4, 0xB4)

    a.add_imm(7, 4, 0x1C0)
    a.mov_imm(8, 0x02001300)
    a.ldrb_imm(0, 8, 0); a.strb_imm(0, 7, 0)
    a.ldrb_imm(0, 8, 1); a.strb_imm(0, 7, 1)
    for w_i in range(3):
        a.ldr_imm(0, 6, 0x0C + w_i * 4)
        a.str_imm(0, 7, 4 + w_i * 4)
    for w_i in range(12):
        a.ldr_imm(0, 6, 0x7E + w_i * 4)
        a.str_imm(0, 7, 0x10 + w_i * 4)

    a.pop([4, 5, 6, 7, 8, 9, 15])
    a.flush_literals()

    # =========================================================================
    # Timer Update Subroutine: tick_frame_timers()
    # =========================================================================
    a.label("tick_frame_timers")
    a.push([4, 5, 14])
    a.mov_imm(5, 0x02001000)
    a.ldrb_imm(0, 5, 0x1E) # has_state
    a.cmp_imm(0, 0)
    a.b("ml_after_playtime", cond=0x0)
    a.ldrb_imm(0, 5, 0x20) # screen_id
    a.cmp_imm(0, 3); a.cmp_imm(0, 5, cond=0x1); a.cmp_imm(0, 6, cond=0x1)
    a.cmp_imm(0, 7, cond=0x1); a.cmp_imm(0, 8, cond=0x1); a.cmp_imm(0, 9, cond=0x1)
    a.cmp_imm(0, 10, cond=0x1); a.cmp_imm(0, 11, cond=0x1); a.cmp_imm(0, 12, cond=0x1)
    a.b("ml_after_playtime", cond=0x1)
    a.mov_imm(1, 0x02000000)
    a.ldr_imm(2, 1, 0x18)
    a.add_imm(2, 2, 1)
    a.str_imm(2, 1, 0x18)
    a.label("ml_after_playtime")

    a.ldrh_imm(0, 5, 0x30) # banner_timer_frames
    a.cmp_imm(0, 0)
    a.b("ml_after_banner_t", cond=0x0)
    a.sub_imm(0, 0, 1, s=1)
    a.strh_imm(0, 5, 0x30)
    a.b("ml_after_banner_t", cond=0x1)
    a.ldrb_imm(1, 5, 0x20)
    a.cmp_imm(1, 3)
    a.mov_imm(1, 1, cond=0x0)
    a.strb_imm(1, 5, 0x45, cond=0x0)
    a.label("ml_after_banner_t")

    a.ldrh_imm(0, 5, 0x32) # transition_timer_frames
    a.cmp_imm(0, 0)
    a.sub_imm(0, 0, 1, cond=0x1)
    a.strh_imm(0, 5, 0x32, cond=0x1)

    a.ldrb_imm(0, 5, 0x3A) # anim_timer_frames
    a.cmp_imm(0, 0)
    a.sub_imm(0, 0, 1, cond=0x1)
    a.strb_imm(0, 5, 0x3A, cond=0x1)

    a.ldrb_imm(0, 5, 0x20) # screen_id
    a.cmp_imm(0, 15) # CREDITS?
    a.b("ml_after_cred_t", cond=0x1)
    a.ldrh_imm(0, 5, 0x36) # credits_scroll_sub
    a.add_imm(0, 0, 18)
    a.strh_imm(0, 5, 0x36)
    a.mov_imm(1, 60)
    a.bl("udiv32")
    a.ldrh_imm(2, 5, 0x38)
    a.cmp_reg(0, 2)
    a.strh_imm(0, 5, 0x38, cond=0x1)
    a.mov_imm(1, 1, cond=0x1)
    a.strb_imm(1, 5, 0x45, cond=0x1)
    a.label("ml_after_cred_t")

    a.ldrb_imm(0, 5, 0x20)
    a.cmp_imm(0, 3)
    a.b("ml_after_hold", cond=0x1)
    a.ldrb_imm(0, 5, 0x50)
    a.cmp_imm(0, 0)
    a.sub_imm(0, 0, 1, cond=0x1)
    a.strb_imm(0, 5, 0x50, cond=0x1)
    a.ldrb_imm(0, 5, 0x2D)
    a.cmp_imm(0, 0)
    a.sub_imm(0, 0, 1, cond=0x1)
    a.strb_imm(0, 5, 0x2D, cond=0x1)
    a.b("ml_after_hold", cond=0x1)
    a.ldrh_imm(2, 5, 0x1A)
    for bit_k, dir_k in [(6, 1), (7, 0), (5, 2), (4, 3)]:
        lbl_nh = f"ml_nh_{bit_k}"
        a.tst_imm(2, 1 << bit_k)
        a.b(lbl_nh, cond=0x0)
        a.mov_imm(0, dir_k)
        a.mov_imm(1, 0)
        a.bl("try_move")
        a.mov_imm(0, 9)
        a.strb_imm(0, 5, 0x2D)
        a.strb_imm(0, 5, 0x50)
        a.b("ml_after_hold")
        a.label(lbl_nh)
    a.label("ml_after_hold")
    a.pop([4, 5, 15])
    a.flush_literals()

    # =========================================================================
    # VBlank ISR & Main Game Loop
    # =========================================================================
    a.label("vblank_isr")
    a.mov_imm(0, 0x04000200)
    a.ldrh_imm(1, 0, 0x02)
    a.strh_imm(1, 0, 0x02)
    a.mov_imm(2, 0x03007FF0)
    a.ldrh_imm(3, 2, 8)
    a.orr_reg(3, 3, 1)
    a.strh_imm(3, 2, 8)
    a.mov_imm(0, 0x02001000)
    a.ldr_imm(1, 0, 0x10)
    a.add_imm(1, 1, 1)
    a.str_imm(1, 0, 0x10)
    a.ldr_imm(1, 0, 0x0C)
    a.add_imm(1, 1, 1)
    a.str_imm(1, 0, 0x0C)
    # Also sample KEYINPUT on every VBlank so a 1-frame release during a multi-frame render is never missed
    a.mov_imm(1, 0x04000130)
    a.ldrh_imm(1, 1, 0)
    a.mvn_reg(1, 1)
    a.ldrh_imm(2, 0, 0x1A)
    a.and_reg(2, 2, 1)
    a.strh_imm(2, 0, 0x1A)
    a.bx(14)
    a.flush_literals()

    a.label("rom_entry")
    a.mov_imm(0, 0x04000200)
    a.mov_imm(1, 0x431A)
    a.strh_imm(1, 0, 0x04) # WAITCNT = 0x431A
    a.mov_imm(1, 0x0001)
    a.strh_imm(1, 0, 0x00) # IE = IRQ_VBLANK
    a.strh_imm(1, 0, 0x08) # IME = 1

    a.mov_imm(1, 0x03007FF0)
    a.adr(2, "vblank_isr")
    a.str_imm(2, 1, 0x0C)
    a.mov_imm(0, 0x04000000)
    a.mov_imm(1, 0x0008)
    a.strh_imm(1, 0, 0x04) # DISPSTAT

    # Copy hot rendering routines (iwram_code_start..iwram_code_end) to 0x03001000 (1-cycle 32-bit IWRAM)
    a.mov_imm(1, a.labels["iwram_code_start"])
    a.mov_imm(2, 0x03001000)
    a.mov_imm(3, 0x84000000 | ((a.labels["iwram_code_end"] - a.labels["iwram_code_start"]) // 4))
    a.mov_imm(4, 0x040000D4)
    a.str_imm(1, 4, 0)
    a.str_imm(2, 4, 4)
    a.str_imm(3, 4, 8)

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

    # Initialize BG0 Screenblock 30 (0x0600F000): tile (tx, ty) = 1 + ty * 30 + tx for ty=0..19, tx=0..29
    # and clear BG0 tile 0 (0x06000000..0x0600003F) to 0
    a.mov_imm(1, 0x06000000)
    a.mov_imm(2, 0)
    for w_i in range(0, 64, 4):
        a.str_imm(2, 1, w_i)
    a.mov_imm(1, 0x0600F000)
    a.mov_imm(2, 1) # tileNum = 1..600
    a.mov_imm(3, 0) # ty = 0..19
    a.label("boot_bg0_sb_y")
    a.cmp_imm(3, 20)
    a.b("boot_bg0_sb_done", cond=0x2)
    a.add_reg(4, 1, 3, shift_imm=6, shift_type=0) # + ty * 64
    a.mov_imm(5, 0) # tx = 0..29
    a.label("boot_bg0_sb_x")
    a.cmp_imm(5, 30)
    a.b("boot_bg0_sb_ny", cond=0x2)
    a.add_reg(6, 4, 5, shift_imm=1, shift_type=0)
    a.strh_imm(2, 6, 0)
    a.add_imm(2, 2, 1)
    a.add_imm(5, 5, 1)
    a.b("boot_bg0_sb_x")
    a.label("boot_bg0_sb_ny")
    a.add_imm(3, 3, 1)
    a.b("boot_bg0_sb_y")
    a.label("boot_bg0_sb_done")

    # Configure BG0CNT (0x04000008) = 0x1E80 (prio 0, charBase 0, 8bpp, scrBase 30, size 0)
    # Configure BG1CNT (0x0400000A) = 0x5C0E (prio 2, charBase 3, 4bpp, scrBase 28, size 1 = 64x32)
    # Configure DISPCNT (0x04000000) = 0x1340 (Mode 0, 1D OBJ, BG0 + BG1 + OBJ enabled) or 0x0340 for control_no_obj
    a.mov_imm(0, 0x04000000)
    a.mov_imm(1, 0x1E80)
    a.strh_imm(1, 0, 0x08) # BG0CNT
    a.mov_imm(1, 0x5C0E)
    a.strh_imm(1, 0, 0x0A) # BG1CNT
    if control_mode == "no_obj":
        a.mov_imm(1, 0x0340) # OBJ layer disabled!
    else:
        a.mov_imm(1, 0x1340) # OBJ layer enabled!
    a.strh_imm(1, 0, 0x00) # DISPCNT

    # Initialize GBA PSG Audio Master Registers & Wave RAM
    a.mov_imm(1, 0x0080)
    a.strh_imm(1, 0, 0x84)
    a.mov_imm(1, 0xFF77)
    a.strh_imm(1, 0, 0x80)
    a.mov_imm(1, 0x0002)
    a.strh_imm(1, 0, 0x82)
    a.mov_imm(1, 0x0000)
    a.strh_imm(1, 0, 0x70)
    wavetable_words = [0x97532101, 0x8AECFEEB, 0x10123578, 0x8BDCA864]
    for w_i, w_val in enumerate(wavetable_words):
        a.mov_imm(1, w_val)
        a.str_imm(1, 0, 0x90 + w_i * 4)
    a.mov_imm(1, 0x00C0)
    a.strh_imm(1, 0, 0x70)

    # Initialize RSTATE (0x02001000) & ASTATE (0x02001300)
    a.mov_imm(5, 0x02001000)
    a.mov_imm(1, 1337)
    a.str_imm(1, 5, 0x00)
    a.mov_imm(1, 2)
    a.strb_imm(1, 5, 0x2E)
    a.mov_imm(1, 50)
    a.strb_imm(1, 5, 0x2F)
    a.mov_imm(1, 1)
    a.strb_imm(1, 5, 0x45)
    a.strb_imm(1, 5, 0x92)
    a.mov_imm(1, 0xFF)
    a.strb_imm(1, 5, 0x34) # banner_map_id = 0xFF
    a.strb_imm(1, 5, 0x46) # loaded_vram_map_id = 0xFF
    a.strb_imm(1, 5, 0x49) # loaded_anim_tick = 0xFF
    a.strb_imm(1, 5, 0x4A) # loaded_pal_mode = 0xFF
    a.mov_imm(4, 0x02001300)
    a.strb_imm(1, 4, 0x00)
    a.strb_imm(1, 4, 0x01)
    a.mov_imm(0, 0)
    a.bl("play_music")
    a.bl("render_frame_to_vram")
    a.bl("write_mailbox")
    a.swi(0x05)

    # Main Loop!
    a.label("main_loop")
    a.mov_imm(5, 0x02001000)
    a.mov_imm(0, 0)
    a.strb_imm(0, 5, 0x48)
    a.mov_imm(1, 0x0203FC00)
    a.strb_imm(0, 1, 0x08) # acceptingInput = 0 while frame logic/rendering is in progress
    a.ldr_imm(0, 5, 0x10)
    a.str_imm(0, 5, 0x14)

    # frame_counter (0x0C) is incremented in vblank_isr on every VBlank

    # Read KEYINPUT (0x04000130)
    a.mov_imm(0, 0x04000130)
    a.ldrh_imm(0, 0, 0)
    a.mvn_reg(0, 0)
    a.mov_imm(1, 0x03FF)
    a.and_reg(0, 0, 1)
    a.ldrh_imm(1, 5, 0x1A)
    a.strh_imm(0, 5, 0x1A)
    a.bic_reg(2, 0, 1)
    a.strh_imm(2, 5, 0x1C)

    a.mov_imm(4, 0)
    a.label("ml_btn_loop")
    a.cmp_imm(4, 10)
    a.b("ml_btn_done", cond=0x2)
    a.ldrh_imm(0, 5, 0x1C)
    a.mov_reg_rs(0, 0, 4, shift_type=1)
    a.tst_imm(0, 1)
    a.mov_reg(0, 4, cond=0x1)
    a.bl("press_button", cond=0x1)
    a.add_imm(4, 4, 1)
    a.b("ml_btn_loop")
    a.label("ml_btn_done")

    a.bl("tick_frame_timers")
    a.bl("step_audio_frame")
    a.bl("render_frame_to_vram")



    # If did_redraw (0x4D) != 0 or new_keys (0x1C) != 0, require clean VDraw scanout before acceptingInput = 1:
    #   if VCOUNT >= 160 (in VBlank): clean_vdraw_countdown = 1 (next VDraw will be clean)
    #   if VCOUNT < 160  (in VDraw) : clean_vdraw_countdown = 2 (current VDraw is torn; wait for next VDraw)
    a.ldrb_imm(0, 5, 0x4D)
    a.ldrh_imm(1, 5, 0x1C)
    a.orr_reg(0, 0, 1, s=1)
    a.b("ml_no_redraw_cd", cond=0x0)
    a.mov_imm(0, 0x04000000)
    a.ldrh_imm(0, 0, 0x06) # VCOUNT
    a.cmp_imm(0, 160)
    a.mov_imm(0, 2, cond=0x3) # VCOUNT < 160 -> 2
    a.mov_imm(0, 1, cond=0x2) # VCOUNT >= 160 -> 1
    a.strb_imm(0, 5, 0x4C)
    a.label("ml_no_redraw_cd")
    a.bl("write_mailbox")

    a.ldr_imm(0, 5, 0x10)
    a.ldr_imm(1, 5, 0x14)
    a.sub_reg(0, 0, 1, s=1)
    a.b("ml_wait_vblank", cond=0x0)
    a.mov_imm(2, 0x0203FC00)
    a.ldrb_imm(1, 2, 0x09)
    a.cmp_imm(1, 0)
    a.ldrh_imm(1, 2, 0x0A, cond=0x0)
    a.add_imm(1, 1, 1, cond=0x0)
    a.strh_imm(1, 2, 0x0A, cond=0x0)

    a.label("ml_wait_vblank")
    a.swi(0x05)
    a.b("main_loop")
    a.resolve()

    if len(a.code) > TABLE_DIR_ROM_ADDR - 0x08000000:
        raise RuntimeError(f"Code size {len(a.code)} exceeded table directory offset!")

    rom_size = off_cur - 0x08000000
    rom_buf = bytearray(rom_size)
    rom_buf[:len(a.code)] = a.code

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

    tdir_off = TABLE_DIR_ROM_ADDR - 0x08000000
    struct.pack_into("<II", rom_buf, tdir_off, 0x52494454, len(tables))
    for idx_t, k in enumerate(sorted(tables.keys())):
        name, b_data, cnt = tables[k]
        rom_off = table_addrs[k] - 0x08000000
        struct.pack_into("<IIII", rom_buf, tdir_off + 8 + idx_t * 16, k, rom_off, len(b_data), cnt)
        rom_buf[rom_off:rom_off + len(b_data)] = b_data

    def write_chunk(rom_addr, data_bytes):
        off = rom_addr - 0x08000000
        rom_buf[off:off + len(data_bytes)] = data_bytes

    write_chunk(master_pal_rom_addr, master_pal_bytes)
    write_chunk(dark_obj_pal_rom_addr, dark_obj_pal_bytes)
    write_chunk(tile_pal_modes_rom_addr, tile_pal_modes_bytes)
    write_chunk(battle_flash_pals_rom_addr, battle_flash_pals_bytes)
    write_chunk(tiles_anim0_rom_addr, tiles_anim0_bytes)
    write_chunk(tiles_anim1_rom_addr, tiles_anim1_bytes)
    write_chunk(sp_pal_map_rom_addr, sp_pal_map_bytes)
    write_chunk(char_obj_rom_addr, char_obj_bytes)
    write_chunk(init_npc_xy_rom_addr, init_npc_xy_bytes)
    write_chunk(ui_str_rom_addr, ui_pool.buf)
    write_chunk(midi_pulse_rom_addr, midi_pulse_freq)
    write_chunk(midi_wave_rom_addr, midi_wave_freq)

    with open(out_path, "wb") as f:
        f.write(rom_buf)

    crc32 = zlib.crc32(rom_buf) & 0xFFFFFFFF
    sha256 = hashlib.sha256(rom_buf).hexdigest()
    print(f"[build.py] Built {out_path}: {len(rom_buf)} bytes ({len(rom_buf)/1024:.1f} KB)")
    print(f"  Code size: {len(a.code)} bytes, Header checksum: 0x{rom_buf[0xBD]:02X}")
    print(f"  CRC32: 0x{crc32:08X}, SHA-256: {sha256}")
    a.labels["_code_end_off"] = len(a.code)
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
        ("control_font_shift.gba", "font_shift"),
        ("control_no_obj.gba", "no_obj"),
        ("control_hp_short.gba", "hp_short"),
        ("control_no_fade.gba", "no_fade"),
        ("control_no_flash.gba", "no_flash"),
        ("control_no_dex_page.gba", "no_dex_page"),
    ]
    for fname, mode in controls:
        build_rom(os.path.join(ctrl_dir, fname), control_mode=mode)

if __name__ == "__main__":
    build_rom(OUT_ROM_PATH, control_mode=None)
    if "--build-controls" in sys.argv:
        build_all_controls()
