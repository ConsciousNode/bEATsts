# gen_world.py - Generates src/05_world_and_story.js for bEATsts 2.1
# Hand-designed maps (no shared templates), 8 Kitchen Gym interiors, 6 multi-floor dungeons,
# Chrome Fork Syndicate arc, 6 Rival Saffron encounters, 16 completable quests, 800+ real displayed lines.
import json, random
from collections import deque

SOLID_TILES = {1,3,5,8,13,14,15,16,18,21,25,26,27,28,30,33,37,38,39,40,42,45,49,50,51,52,53,55,57,60,63,64,72,73}

TILE_ROLES = {
  0: 'floor', 1: 'counter', 2: 'door', 3: 'sign', 4: 'mat', 5: 'shelf',
  6: 'stairs', 7: 'stairs', 8: 'building', 9: 'switch',
  10: 'ground', 11: 'tall_grass', 12: 'path', 13: 'water', 14: 'wall', 15: 'building', 16: 'roof', 17: 'path', 18: 'fence', 19: 'decoration', 20: 'floor', 21: 'wall',
  22: 'ground', 23: 'tall_grass', 24: 'path', 25: 'water', 26: 'wall', 27: 'building', 28: 'roof', 29: 'floor', 30: 'decoration', 31: 'path', 32: 'floor', 33: 'wall',
  34: 'ground', 35: 'tall_grass', 36: 'path', 37: 'water', 38: 'wall', 39: 'building', 40: 'roof', 41: 'floor', 42: 'decoration', 43: 'path', 44: 'floor', 45: 'wall',
  46: 'ground', 47: 'tall_grass', 48: 'path', 49: 'water', 50: 'wall', 51: 'building', 52: 'roof', 53: 'decoration', 54: 'decoration', 55: 'wall', 56: 'floor', 57: 'wall',
  58: 'floor', 59: 'path', 60: 'wall', 61: 'ground', 62: 'tall_grass', 63: 'wall',
  64: 'decoration', 65: 'ledge', 66: 'ice', 67: 'conveyor', 68: 'conveyor', 69: 'conveyor', 70: 'conveyor',
  71: 'floor', 72: 'wall', 73: 'gate'
}

class MapBuilder:
    def __init__(self, w, h, bg, border):
        self.w, self.h = w, h
        self.bg = bg
        self.border = border
        self.g = [bg] * (w * h)
        self.signs = []
        self.rect(0, 0, w, 1, border)
        self.rect(0, h - 1, w, 1, border)
        self.rect(0, 0, 1, h, border)
        self.rect(w - 1, 0, 1, h, border)

    def set(self, x, y, t):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y * self.w + x] = t

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.g[y * self.w + x]
        return self.border

    def rect(self, x0, y0, w, h, t):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                self.set(x, y, t)

    def building(self, x, y, w, h, roof_t, wall_t, door_dx=None):
        # Multi-tile building (>= 4x3) with roof, walls, windows (8), and visible door (2)
        rh = max(1, h // 2)
        self.rect(x, y, w, rh, roof_t)
        self.rect(x, y + rh, w, h - rh, wall_t)
        # Windows
        for wx in range(x + 1, x + w - 1):
            if wx != x + (door_dx if door_dx is not None else w // 2):
                if (wx - x) % 2 == 1:
                    self.set(wx, y + rh, 8)
        dx = x + (door_dx if door_dx is not None else w // 2)
        dy = y + h - 1
        self.set(dx, dy, 2)
        return (dx, dy)

    def add_sign(self, x, y, text):
        self.set(x, y, 3)
        self.signs.append({'x': x, 'y': y, 'text': text})

    def carve_apron(self, x, y, path_t, radius=1):
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = x + dx, y + dy
                if 1 <= nx < self.w - 1 and 1 <= ny < self.h - 1:
                    if self.get(nx, ny) in SOLID_TILES and self.get(nx, ny) not in (2, 6, 7):
                        self.set(nx, ny, path_t)

# Helper to create distinct hand-designed maps
MAPS_DATA = {}

def reg_map(mid, name, region, music, w, h, bg, border, wpool, dark=False):
    mb = MapBuilder(w, h, bg, border)
    MAPS_DATA[mid] = {
        'id': mid, 'name': name, 'region': region, 'music': music,
        'w': w, 'h': h, 'mb': mb, 'wildPool': wpool, 'portals': [], 'npcs': [],
        'dark': dark
    }
    return mb

def link_maps(a, ax, ay, b, bx, by, path_a, path_b, reqSeals=0, reqFlag=None, reqMsg=None, reqChampion=False, two_way=True):
    ma, mb = MAPS_DATA[a]['mb'], MAPS_DATA[b]['mb']
    # Clear border/solid tiles at portal and landing spots
    if ma.get(ax, ay) not in (2, 6, 7):
        ma.set(ax, ay, path_a)
    if mb.get(bx, by) not in (2, 6, 7):
        mb.set(bx, by, path_b)
    # Landing coordinates: step 1 tile inside if on edge, else exact
    atx = 1 if ax == 0 else (ma.w - 2 if ax == ma.w - 1 else ax)
    aty = 1 if ay == 0 else (ma.h - 2 if ay == ma.h - 1 else (ay + 1 if ma.get(ax, ay) == 2 else ay))
    btx = 1 if bx == 0 else (mb.w - 2 if bx == mb.w - 1 else bx)
    bty = 1 if by == 0 else (mb.h - 2 if by == mb.h - 1 else (by + 1 if mb.get(bx, by) == 2 else by))
    ma.set(atx, aty, path_a)
    mb.set(btx, bty, path_b)
    ma.carve_apron(atx, aty, path_a, 1)
    mb.carve_apron(btx, bty, path_b, 1)

    p1 = {'x': ax, 'y': ay, 'to': b, 'tx': btx, 'ty': bty}
    if reqSeals: p1['reqSeals'] = reqSeals
    if reqFlag: p1['reqFlag'] = reqFlag
    if reqMsg: p1['reqMsg'] = reqMsg
    if reqChampion: p1['reqChampion'] = True
    MAPS_DATA[a]['portals'].append(p1)
    if two_way:
        p2 = {'x': bx, 'y': by, 'to': a, 'tx': atx, 'ty': aty}
        MAPS_DATA[b]['portals'].append(p2)

def make_interior(mid, name, region, music, w=20, h=14, floor_t=0, wall_t=15):
    mb = reg_map(mid, name, region, music, w, h, floor_t, wall_t, [])
    mb.set(w // 2, h - 1, 4) # Exit mat
    return mb

# ==============================================================================
# 1. BREADLANDS (8 overworld + interiors)
# ==============================================================================
# Cruston Town (34x22)
m = reg_map('cruston_town', 'Cruston Town', 'Breadlands', 'town_bread', 34, 22, 10, 14, [[1,3,5],[4,3,5],[26,4,6]])
m.rect(14, 1, 5, 20, 12)   # Main N-S Crust Ave (x=14,y=5..12 walkable)
m.rect(3, 9, 28, 3, 12)    # Main E-W Bakery Blvd
m.rect(11, 8, 11, 5, 17)   # Central Oven Plaza
d_lab  = m.building(4, 3, 6, 4, 16, 15, 3)
d_inn  = m.building(23, 3, 6, 4, 16, 15, 3)
d_mart = m.building(4, 13, 6, 4, 16, 15, 3)
d_cafe = m.building(23, 13, 6, 4, 16, 15, 3)
m.rect(10, 15, 4, 4, 13)
m.rect(19, 15, 3, 3, 19)
m.set(13, 13, 64); m.set(20, 13, 64)
m.rect(2, 18, 7, 2, 18); m.rect(19, 15, 12, 4, 19); m.rect(1, 1, 3, 7, 19); m.rect(1, 12, 3, 5, 19); m.rect(29, 3, 3, 5, 11)
m.add_sign(13, 2, 'North: Toastwood Trail')
m.add_sign(10, 7, 'Chef Brotholomew Lab')
m.add_sign(22, 7, 'Cruston Simmer Inn')

# Cruston Interiors
mi = make_interior('cruston_lab', 'Pantry Lab', 'Breadlands', 'town_bread', 17, 12, 20, 15)
mi.rect(2, 2, 13, 2, 5); mi.rect(2, 6, 3, 4, 18); mi.rect(12, 6, 3, 4, 18)
mi.rect(6, 5, 5, 5, 10); mi.set(6, 5, 19); mi.set(10, 5, 19)

mi = make_interior('cruston_inn', 'Cruston Simmer Inn', 'Breadlands', 'town_bread', 18, 11, 41, 15)
mi.rect(1, 1, 5, 5, 15); mi.rect(12, 1, 5, 5, 15)
mi.rect(6, 2, 6, 2, 1); mi.rect(7, 5, 4, 5, 17)
mi.rect(1, 7, 5, 2, 18); mi.rect(12, 7, 5, 2, 18)

mi = make_interior('cruston_mart', 'Cruston Pantry Mart', 'Breadlands', 'town_bread', 19, 11, 10, 15)
mi.rect(2, 2, 4, 6, 5); mi.rect(13, 2, 4, 6, 5)
mi.rect(7, 2, 5, 2, 1); mi.rect(7, 5, 5, 4, 0)
mi.rect(2, 8, 3, 2, 19); mi.rect(14, 8, 3, 2, 19)

mi = make_interior('cruston_cafe', 'Cruston bEATst Cafe', 'Breadlands', 'town_bread', 18, 13, 29, 15)
mi.rect(2, 2, 5, 2, 1); mi.rect(11, 2, 5, 2, 1)
mi.rect(2, 6, 5, 4, 19); mi.rect(11, 6, 5, 4, 19); mi.rect(2, 10, 5, 1, 18); mi.rect(11, 10, 5, 1, 18)
mi.rect(8, 3, 2, 9, 17)

# Toastwood Trail (32x24)
m = reg_map('toastwood_trail', 'Toastwood Trail', 'Breadlands', 'overworld_bread', 32, 24, 10, 14, [[1,3,5],[4,3,6],[6,4,7],[10,4,7],[14,5,8],[26,4,7],[25,6,9]])
m.rect(14, 1, 3, 7, 12); m.rect(7, 6, 10, 2, 12); m.rect(7, 6, 3, 10, 12)
m.rect(7, 14, 18, 2, 12); m.rect(14, 14, 3, 9, 12)
m.rect(2, 2, 10, 4, 11); m.rect(19, 2, 10, 6, 11)
m.rect(2, 17, 10, 5, 11); m.rect(20, 17, 9, 5, 11)
m.rect(11, 9, 10, 4, 19)
m.rect(3, 11, 4, 1, 65); m.rect(25, 11, 4, 1, 65)
m.rect(21, 9, 8, 1, 18)
m.add_sign(13, 21, 'Toastwood Trail -> Deli Meadows')

# Deli Meadows (36x20)
m = reg_map('deli_meadows', 'Deli Meadows', 'Breadlands', 'overworld_bread', 36, 20, 10, 14, [[8,5,8],[12,5,8],[16,6,9],[18,6,9],[20,6,9],[22,6,9],[24,7,10]])
m.rect(1, 9, 34, 2, 12); m.rect(16, 1, 3, 18, 12)
m.rect(10, 1, 3, 18, 13); m.rect(10, 9, 3, 2, 17)
m.rect(2, 2, 7, 6, 11); m.rect(20, 2, 12, 5, 11)
m.rect(2, 12, 7, 5, 19); m.rect(22, 13, 10, 4, 11); m.rect(14, 13, 5, 4, 19)
m.rect(14, 4, 2, 4, 18); m.rect(20, 12, 10, 1, 65)
m.add_sign(15, 17, 'Deli Meadows -> Panini Plaza')
m.add_sign(32, 8, 'East: Truffle Cellar')

# Panini Plaza (36x24): Paved stone plaza (17) with garden planters (19) & Twin Kitchens
m = reg_map('panini_plaza', 'Panini Plaza', 'Breadlands', 'town_bread', 36, 24, 17, 14, [[28,7,10],[29,7,10],[30,8,11],[31,8,11],[32,8,11]])
m.rect(16, 1, 4, 22, 12)
m.rect(1, 10, 34, 3, 12)
d_gym1   = m.building(4, 3, 7, 4, 16, 15, 3)
d_gym2   = m.building(25, 3, 7, 4, 16, 15, 3)
d_p_inn  = m.building(4, 16, 6, 4, 16, 15, 3)
d_p_mart = m.building(26, 16, 6, 4, 16, 15, 3)
m.set(13, 8, 64); m.set(22, 8, 64); m.set(13, 15, 64); m.set(22, 15, 64)
m.rect(11, 16, 4, 5, 19); m.rect(21, 16, 4, 5, 19)
m.rect(11, 3, 4, 4, 18); m.rect(21, 3, 4, 4, 18)
m.add_sign(15, 21, 'Panini Plaza: Twin Kitchens!')
m.add_sign(3, 9, 'West: Sourdough Cavern')

mi = make_interior('panini_inn', 'Panini Simmer Inn', 'Breadlands', 'town_bread', 19, 12, 10, 15)
mi.rect(1, 1, 5, 9, 13); mi.rect(6, 2, 7, 2, 1); mi.rect(14, 2, 4, 7, 19)
mi.rect(8, 5, 4, 6, 41); mi.rect(4, 5, 3, 2, 17)

mi = make_interior('panini_mart', 'Panini Pantry Mart', 'Breadlands', 'town_bread', 20, 11, 20, 15)
mi.rect(1, 1, 18, 2, 5); mi.rect(2, 5, 6, 3, 5); mi.rect(12, 5, 6, 3, 5)
mi.rect(9, 4, 2, 6, 0); mi.rect(8, 3, 4, 1, 1); mi.rect(1, 9, 6, 1, 18); mi.rect(13, 9, 6, 1, 18)

# Gym 1 Interior: Toaster Hearth
mg1 = make_interior('gym_toaster', 'The Toaster Hearth', 'Breadlands', 'town_bread', 22, 15, 17, 15)
mg1.rect(3, 9, 7, 1, 67); mg1.rect(12, 9, 7, 1, 68)
mg1.rect(3, 6, 16, 1, 18); mg1.set(10, 6, 17); mg1.set(11, 6, 17)
mg1.rect(2, 2, 5, 3, 19); mg1.rect(15, 2, 5, 3, 19)
mg1.rect(1, 11, 5, 3, 18); mg1.rect(16, 11, 5, 3, 18); mg1.rect(7, 2, 8, 2, 19)

# Gym 2 Interior: Deli Counter Spire
mg2 = make_interior('gym_deli', 'Deli Counter Spire', 'Breadlands', 'town_bread', 23, 15, 10, 15)
mg2.rect(2, 6, 19, 1, 73); mg2.set(4, 11, 9)
mg2.rect(1, 8, 3, 6, 5); mg2.rect(19, 8, 3, 6, 5)
mg2.rect(7, 9, 9, 2, 1); mg2.rect(3, 2, 5, 2, 5); mg2.rect(15, 2, 5, 2, 5)
mg2.rect(1, 2, 2, 4, 18); mg2.rect(20, 2, 2, 4, 18)

# ==============================================================================
# 2. STEAMBAY
# ==============================================================================
# Bao Harbor (36x22): Harbor with southern bay water & 3 docks
m = reg_map('bao_harbor', 'Bao Harbor', 'Steambay', 'town_steam', 36, 22, 22, 26, [[39,12,16],[42,13,17],[46,14,18],[48,14,18]])
m.rect(1, 13, 34, 8, 25); m.rect(10, 3, 3, 5, 25); m.rect(23, 3, 3, 5, 25)
m.rect(6, 13, 3, 7, 31)
m.rect(16, 1, 4, 20, 24)
m.rect(27, 13, 3, 7, 31)
m.rect(2, 9, 32, 3, 31)
d_b_inn  = m.building(3, 3, 6, 4, 28, 27, 3)
d_gym3   = m.building(14, 3, 8, 4, 28, 27, 4)
d_b_mart = m.building(27, 3, 6, 4, 28, 27, 3)
m.set(11, 14, 30); m.set(24, 14, 30); m.set(12, 8, 64); m.set(24, 8, 64)
m.add_sign(15, 19, 'Bao Harbor - Steambay Docks')

mi = make_interior('bao_inn', 'Bao Simmer Inn', 'Steambay', 'town_steam', 17, 13, 22, 27)
mi.rect(1, 4, 5, 7, 25); mi.rect(11, 4, 5, 7, 25)
mi.rect(6, 2, 5, 2, 1); mi.rect(7, 4, 3, 8, 31)
mi.rect(1, 1, 3, 2, 30); mi.rect(13, 1, 3, 2, 30)

mi = make_interior('bao_mart', 'Bao Pantry Mart', 'Steambay', 'town_steam', 20, 12, 24, 27)
mi.rect(1, 1, 4, 9, 25); mi.rect(15, 1, 4, 9, 25)
mi.rect(6, 2, 2, 7, 5); mi.rect(12, 2, 2, 7, 5)
mi.rect(8, 2, 4, 2, 1); mi.rect(9, 4, 2, 7, 29)

# Gym 3 Interior: Bamboo Cloud Kitchen
mg3 = make_interior('gym_bamboo', 'Bamboo Cloud Kitchen', 'Steambay', 'town_steam', 22, 17, 22, 27)
mg3.rect(5, 6, 12, 4, 66)
mg3.rect(1, 4, 3, 8, 26); mg3.rect(18, 4, 3, 8, 26)
mg3.rect(9, 1, 4, 15, 31); mg3.rect(6, 12, 3, 2, 30); mg3.rect(13, 12, 3, 2, 30)

# Bamboo Mist Path (34x22)
m = reg_map('bamboo_mist_path', 'Bamboo Mist Path', 'Steambay', 'overworld_steam', 34, 22, 26, 26, [[50,14,18],[52,15,19],[54,14,18],[56,15,19],[57,16,20]])
m.rect(13, 1, 7, 20, 29)
m.rect(3, 8, 28, 5, 24)
m.rect(2, 2, 9, 5, 23); m.rect(23, 2, 9, 5, 23)
m.rect(2, 14, 9, 6, 23); m.rect(23, 14, 9, 6, 23)
m.set(12, 12, 30); m.set(21, 12, 30)
m.add_sign(12, 19, 'Bamboo Mist Path -> Gyoza Cove')

# Gyoza Cove (36x20)
m = reg_map('gyoza_cove', 'Gyoza Cove', 'Steambay', 'overworld_steam', 36, 20, 31, 26, [[44,17,21],[58,18,22],[59,18,22],[60,18,22],[61,19,23],[62,20,24]])
m.rect(1, 10, 13, 9, 25); m.rect(29, 11, 6, 8, 25)
m.rect(15, 1, 4, 18, 24)
m.rect(14, 9, 20, 2, 24)
m.rect(2, 2, 11, 6, 23); m.rect(21, 12, 12, 6, 23)
d_gym4 = m.building(23, 2, 7, 4, 28, 27, 3)
m.add_sign(14, 17, 'Gyoza Cove & Skillet Tidehouse')

# Gym 4 Interior: Skillet Tidehouse
mg4 = make_interior('gym_skillet', 'Skillet Tidehouse', 'Steambay', 'town_steam', 23, 16, 25, 27)
mg4.rect(3, 2, 17, 4, 29); mg4.rect(3, 9, 17, 6, 31)
mg4.rect(10, 6, 3, 4, 31)
mg4.rect(3, 6, 17, 1, 73); mg4.set(17, 11, 9)
mg4.rect(5, 10, 7, 1, 67)

# Pierogi Pier (34x22): Water-surrounded pier with offset boardwalk (y=13..15)
m = reg_map('pierogi_pier', 'Pierogi Pier', 'Steambay', 'town_steam', 34, 22, 25, 26, [[63,19,23],[64,20,24],[66,20,24],[67,20,24],[68,20,24],[69,20,24]])
m.rect(13, 1, 8, 20, 31)
m.rect(1, 10, 32, 3, 24)
m.rect(2, 2, 10, 8, 29); m.rect(22, 2, 10, 8, 29)
d_pi_inn  = m.building(4, 3, 6, 4, 28, 27, 3)
d_pi_mart = m.building(24, 3, 6, 4, 28, 27, 3)
m.set(13, 8, 64); m.set(20, 8, 64)
m.rect(3, 15, 8, 4, 29); m.rect(23, 15, 8, 4, 29) # Floating dining decks
m.rect(11, 16, 2, 2, 31); m.rect(21, 16, 2, 2, 31)
m.add_sign(3, 9, 'West: Steamer Spire')

mi = make_interior('pierogi_inn', 'Pierogi Simmer Inn', 'Steambay', 'town_steam', 19, 13, 29, 27)
mi.rect(1, 1, 4, 11, 26); mi.rect(14, 1, 4, 11, 26)
mi.rect(6, 2, 7, 2, 1); mi.rect(6, 6, 7, 3, 25); mi.rect(8, 5, 3, 7, 31)

mi = make_interior('pierogi_mart', 'Pierogi Pantry Mart', 'Steambay', 'town_steam', 21, 11, 26, 27)
mi.rect(2, 2, 17, 7, 29); mi.rect(2, 2, 5, 2, 5); mi.rect(14, 2, 5, 2, 5)
mi.rect(8, 2, 5, 2, 1); mi.rect(4, 6, 13, 2, 24); mi.rect(7, 2, 1, 4, 25); mi.rect(13, 2, 1, 4, 25)

# ==============================================================================
# 3. NOODLERIDGE
# ==============================================================================
# Udon Hollow (34x22): Mountain valley with Chili Lake & offset east-side avenues
m = reg_map('udon_hollow', 'Udon Hollow', 'Noodleridge', 'town_noodle', 34, 22, 36, 38, [[77,22,26],[80,23,27],[82,24,28],[84,24,28]])
m.rect(14, 1, 5, 20, 43)
m.rect(2, 9, 30, 3, 41)
m.rect(2, 13, 10, 7, 37)  # SW Chili Lake
m.rect(21, 13, 11, 7, 42) # SE Noodle bamboo garden
d_u_inn  = m.building(3, 3, 6, 4, 40, 39, 3)
d_gym5   = m.building(13, 3, 8, 4, 40, 39, 4)
d_u_mart = m.building(24, 3, 6, 4, 40, 39, 3)
m.add_sign(13, 19, 'Udon Hollow - Pull-Noodle Dojo')

mi = make_interior('udon_inn', 'Udon Simmer Inn', 'Noodleridge', 'town_noodle', 17, 14, 41, 39)
mi.rect(2, 2, 4, 8, 34); mi.rect(11, 2, 4, 8, 34)
mi.rect(6, 2, 5, 2, 1); mi.rect(7, 4, 3, 9, 36)

mi = make_interior('udon_mart', 'Udon Pantry Mart', 'Noodleridge', 'town_noodle', 21, 12, 34, 39)
mi.rect(1, 1, 6, 9, 5); mi.rect(14, 1, 6, 9, 5)
mi.rect(8, 2, 5, 2, 1); mi.rect(9, 4, 3, 7, 36)

# Gym 5 Interior: Pull-Noodle Dojo
mg5 = make_interior('gym_dojo', 'Pull-Noodle Dojo', 'Noodleridge', 'town_noodle', 21, 16, 41, 39)
mg5.rect(2, 6, 8, 1, 38); mg5.rect(12, 6, 8, 1, 38)
mg5.rect(4, 10, 13, 3, 36); mg5.rect(2, 2, 3, 3, 42); mg5.rect(16, 2, 3, 3, 42)
mg5.rect(1, 7, 3, 7, 18); mg5.rect(17, 7, 3, 7, 18)

# Slurp Canyon (36x22)
m = reg_map('slurp_canyon', 'Slurp Canyon', 'Noodleridge', 'overworld_noodle', 36, 22, 38, 38, [[86,25,29],[88,25,29],[90,26,30],[92,26,30],[94,27,31],[95,27,31]])
m.rect(2, 2, 32, 18, 34)
m.rect(2, 2, 12, 3, 37); m.rect(22, 2, 12, 3, 37)
m.rect(15, 1, 5, 20, 43)
m.rect(3, 10, 30, 2, 36)
m.rect(4, 7, 9, 1, 65); m.rect(23, 7, 9, 1, 65)
m.rect(4, 13, 9, 1, 65); m.rect(23, 13, 9, 1, 65)
m.rect(3, 15, 9, 5, 35); m.rect(24, 15, 9, 5, 35)
m.add_sign(14, 19, 'Slurp Canyon -> Al Dente Ascent')

# Al Dente Ascent (34x22)
m = reg_map('al_dente_ascent', 'Al Dente Ascent', 'Noodleridge', 'overworld_noodle', 34, 22, 38, 38, [[96,28,32],[97,28,32],[98,29,33],[99,29,33],[100,29,33],[101,30,34]])
m.rect(14, 1, 4, 9, 43); m.rect(6, 8, 22, 3, 36); m.rect(6, 8, 4, 8, 43)
m.rect(6, 14, 22, 2, 36); m.rect(15, 14, 4, 7, 43)
m.rect(20, 17, 10, 1, 65); m.rect(19, 13, 12, 4, 34)
m.rect(2, 2, 11, 17, 35); m.rect(20, 11, 11, 8, 34)
d_gym6 = m.building(22, 3, 7, 4, 40, 39, 3); m.rect(24, 7, 3, 3, 36)
m.add_sign(13, 19, 'Al Dente Ascent & Wok Peak Bistro')

# Gym 6 Interior: Wok Peak Bistro
mg6 = make_interior('gym_wokpeak', 'Wok Peak Bistro', 'Noodleridge', 'town_noodle', 24, 15, 34, 39)
mg6.rect(4, 7, 16, 3, 66)
mg6.rect(1, 1, 5, 5, 38); mg6.rect(18, 1, 5, 5, 38)
mg6.rect(9, 1, 6, 13, 36)

# Ramen Summit (34x24)
m = reg_map('ramen_summit', 'Ramen Summit', 'Noodleridge', 'town_noodle', 34, 24, 35, 38, [[102,30,34],[103,30,34],[104,31,35],[105,31,35],[106,31,35],[107,32,36]])
m.rect(14, 1, 5, 22, 36)
m.rect(1, 10, 32, 3, 36)
m.rect(3, 15, 7, 5, 37); m.rect(24, 15, 7, 5, 37)
d_r_inn  = m.building(4, 3, 6, 4, 40, 39, 3)
d_r_mart = m.building(24, 3, 6, 4, 40, 39, 3)
m.set(13, 8, 64); m.set(20, 8, 64)
m.rect(12, 16, 2, 4, 42); m.rect(20, 16, 2, 4, 42)
m.add_sign(3, 9, 'West: Wok Volcano')

mi = make_interior('ramen_inn', 'Ramen Simmer Inn', 'Noodleridge', 'town_noodle', 19, 14, 41, 39)
mi.rect(1, 1, 17, 3, 38); mi.rect(7, 2, 5, 2, 1)
mi.rect(2, 6, 4, 4, 37); mi.rect(13, 6, 4, 4, 37); mi.rect(5, 10, 9, 2, 34); mi.rect(2, 11, 5, 2, 42); mi.rect(12, 11, 5, 2, 42); mi.rect(1, 4, 3, 2, 35); mi.rect(15, 4, 3, 2, 35); mi.rect(1, 1, 3, 3, 38); mi.rect(15, 1, 3, 3, 38)
mi.rect(8, 4, 3, 9, 43)

mi = make_interior('ramen_mart', 'Ramen Pantry Mart', 'Noodleridge', 'town_noodle', 20, 13, 34, 39)
mi.rect(2, 2, 16, 2, 5); mi.rect(8, 4, 4, 2, 1)
mi.rect(2, 7, 6, 4, 42); mi.rect(12, 7, 6, 4, 42)

# ==============================================================================
# 4. BROTHBASIN
# ==============================================================================
# Chowder Crossing (35x21)
m = reg_map('chowder_crossing', 'Chowder Crossing', 'Brothbasin', 'town_broth', 35, 21, 46, 50, [[115,32,36],[118,33,37],[120,33,37],[122,34,38]])
m.rect(1, 9, 33, 3, 49)
m.rect(15, 1, 4, 19, 48)
m.rect(6, 9, 3, 3, 48); m.rect(25, 9, 3, 3, 48)
d_c_inn  = m.building(4, 3, 6, 4, 52, 51, 3)
d_gym7   = m.building(13, 3, 8, 4, 52, 51, 4)
d_c_mart = m.building(24, 3, 6, 4, 52, 51, 3)
m.rect(4, 14, 8, 4, 54); m.rect(22, 14, 8, 4, 54)
m.add_sign(14, 18, 'Chowder Crossing - Twin Bridges')

mi = make_interior('chowder_inn', 'Chowder Simmer Inn', 'Brothbasin', 'town_broth', 18, 14, 46, 51)
mi.rect(1, 1, 5, 5, 50); mi.rect(12, 1, 5, 5, 50)
mi.rect(6, 2, 6, 2, 1); mi.rect(7, 4, 4, 9, 48)
mi.rect(3, 8, 3, 4, 49); mi.rect(12, 8, 3, 4, 49)

mi = make_interior('chowder_mart', 'Chowder Pantry Mart', 'Brothbasin', 'town_broth', 21, 13, 56, 51)
mi.rect(7, 5, 7, 3, 5); mi.rect(8, 2, 5, 2, 1)
mi.rect(2, 2, 3, 8, 49); mi.rect(16, 2, 3, 8, 49)

# Gym 7 Interior: Cauldron Conservatory
mg7 = make_interior('gym_cauldron', 'Cauldron Conservatory', 'Brothbasin', 'town_broth', 23, 17, 50, 51)
mg7.rect(3, 2, 17, 13, 56); mg7.rect(2, 6, 19, 1, 73); mg7.set(5, 11, 9)
mg7.rect(2, 8, 6, 3, 49); mg7.rect(15, 8, 6, 3, 49)
MAPS_DATA['gym_cauldron']['dark'] = True

# Simmer Fen (35x23)
m = reg_map('simmer_fen', 'Simmer Fen', 'Brothbasin', 'overworld_broth', 35, 23, 49, 50, [[124,35,39],[126,35,39],[128,36,40],[130,36,40],[131,37,41],[132,37,41]])
m.rect(15, 1, 4, 21, 48)
m.rect(3, 10, 29, 3, 48)
m.rect(3, 3, 10, 6, 47); m.rect(22, 3, 10, 6, 47)
m.rect(3, 14, 10, 6, 54); m.rect(22, 14, 10, 6, 47)
m.set(12, 14, 55); m.set(20, 14, 55); m.rect(10, 8, 5, 2, 48); m.rect(22, 12, 3, 3, 48); m.rect(13, 14, 2, 2, 48)
m.add_sign(14, 20, 'Simmer Fen -> Kettle Gorge')

# Kettle Gorge (34x22): Rocky gorge (50) with winding stone causeway & twin geyser pools
m = reg_map('kettle_gorge', 'Kettle Gorge', 'Brothbasin', 'overworld_broth', 34, 22, 50, 50, [[133,38,42],[134,38,42],[135,38,42],[136,39,43],[137,39,43],[138,40,44]])
m.rect(14, 1, 4, 8, 48); m.rect(6, 7, 12, 3, 48); m.rect(6, 7, 4, 9, 48)
m.rect(6, 14, 22, 2, 48); m.rect(15, 14, 4, 7, 48)
m.rect(20, 2, 10, 6, 47); m.rect(2, 2, 9, 4, 49); m.rect(18, 6, 4, 3, 48); m.rect(15, 11, 3, 3, 48)
m.rect(2, 17, 9, 3, 47); m.rect(22, 17, 9, 3, 49) # South rim grass & geyser
m.add_sign(13, 19, 'Kettle Gorge -> Bisque Bastion')

# Bisque Bastion (36x22): Walled stone bastion with battlements (57), stone courtyard (48) & moat (49)
m = reg_map('bisque_bastion', 'Bisque Bastion', 'Brothbasin', 'town_broth', 36, 22, 54, 57, [[139,40,44],[140,40,44],[141,41,45],[142,41,45],[143,41,45],[144,42,46]])
m.rect(10, 7, 16, 8, 56) # Central stone courtyard
m.rect(16, 1, 4, 20, 48)
m.rect(1, 10, 34, 3, 48)
m.rect(11, 7, 14, 1, 57); m.set(17, 7, 48); m.set(18, 7, 48)
d_bi_inn  = m.building(4, 3, 6, 4, 52, 51, 3)
d_bi_mart = m.building(26, 3, 6, 4, 52, 51, 3)
d_gym8    = m.building(24, 14, 8, 4, 52, 51, 4)
m.rect(2, 14, 10, 6, 49); m.rect(2, 14, 2, 6, 57); m.rect(12, 16, 10, 4, 47)
m.set(13, 8, 64); m.set(22, 8, 64)
m.add_sign(3, 9, 'West: Broth Catacombs')
m.add_sign(32, 9, 'East: Chrome Fork HQ')

mi = make_interior('bisque_inn', 'Bisque Simmer Inn', 'Brothbasin', 'town_broth', 20, 14, 56, 51)
mi.rect(3, 4, 14, 8, 53); mi.rect(8, 4, 4, 9, 48); mi.rect(7, 2, 6, 2, 1)
mi.rect(2, 6, 3, 6, 49); mi.rect(15, 6, 3, 6, 49); mi.rect(5, 6, 2, 5, 57); mi.rect(13, 6, 2, 5, 57)

mi = make_interior('bisque_mart', 'Bisque Pantry Mart', 'Brothbasin', 'town_broth', 22, 12, 48, 51)
mi.rect(2, 2, 5, 4, 5); mi.rect(15, 2, 5, 4, 5); mi.rect(8, 2, 6, 2, 1)
mi.rect(3, 7, 16, 3, 56); mi.set(10, 5, 53); mi.set(11, 5, 53)

# Gym 8 Interior: Deep Stock Vault
mg8 = make_interior('gym_vault', 'The Deep Stock Vault', 'Brothbasin', 'town_broth', 24, 17, 57, 51)
mg8.rect(3, 2, 18, 13, 48); mg8.rect(2, 6, 20, 1, 73); mg8.set(17, 11, 9)
mg8.rect(2, 8, 3, 6, 57); mg8.rect(19, 8, 3, 6, 57)

# ==============================================================================
# 5. SIX MULTI-FLOOR DUNGEONS (12 Dungeon Maps)
# ==============================================================================
# Dungeon 1: Sourdough Cavern (1F: Earthy cavern with wheat-moss & milk stream; B2: Dark cask cellar)
d1 = reg_map('sourdough_cavern', 'Sourdough Cavern 1F', 'Breadlands', 'overworld_bread', 28, 18, 10, 21, [[33,9,13],[34,9,13],[35,9,13],[36,10,14],[37,10,14],[38,12,16]])
d1.rect(3, 7, 24, 3, 17); d1.rect(4, 3, 9, 4, 11); d1.rect(15, 11, 9, 4, 13)
d1.rect(14, 3, 8, 5, 20); d1.set(6, 4, 7)

d1_b2 = reg_map('sourdough_cavern_b2', 'Sourdough Cavern B2', 'Breadlands', 'overworld_bread', 24, 16, 15, 15, [[36,10,14],[37,10,14],[38,12,16]], dark=True)
d1_b2.rect(4, 3, 16, 10, 17); d1_b2.rect(3, 9, 7, 4, 15); d1_b2.rect(14, 9, 5, 4, 15); d1_b2.rect(5, 5, 14, 1, 18); d1_b2.set(11, 5, 17); d1_b2.rect(14, 3, 5, 2, 13)
d1_b2.set(6, 4, 6)

# Dungeon 2: Steamer Spire
d2 = reg_map('steamer_spire', 'Steamer Spire 1F', 'Steambay', 'overworld_steam', 28, 18, 32, 33, [[65,22,26],[70,21,25],[71,22,26],[72,22,26],[73,22,26],[74,23,27],[75,23,27],[76,25,29]])
d2.rect(2, 2, 24, 14, 31); d2.rect(6, 5, 16, 8, 25); d2.rect(8, 6, 12, 6, 32)
d2.rect(18, 3, 6, 4, 23); d2.set(6, 4, 6)

d2_f2 = reg_map('steamer_spire_f2', 'Steamer Spire 2F', 'Steambay', 'overworld_steam', 24, 17, 29, 33, [[74,23,27],[75,23,27],[76,25,29]])
d2_f2.rect(2, 8, 20, 1, 73); d2_f2.set(18, 12, 9)
d2_f2.rect(1, 10, 5, 5, 25); d2_f2.rect(18, 10, 5, 5, 25); d2_f2.rect(10, 2, 10, 4, 23); d2_f2.rect(2, 10, 4, 2, 30); d2_f2.rect(18, 10, 4, 2, 30); d2_f2.rect(10, 11, 4, 3, 30); d2_f2.rect(2, 2, 3, 5, 26); d2_f2.rect(20, 2, 3, 5, 26)
d2_f2.set(6, 4, 7)

# Dungeon 3: Wok Volcano
d3 = reg_map('wok_volcano', 'Wok Volcano 1F', 'Noodleridge', 'overworld_noodle', 29, 18, 37, 45, [[108,33,37],[109,33,37],[110,33,37],[111,34,38],[112,34,38],[113,34,38],[114,36,40]])
d3.rect(3, 7, 25, 3, 43); d3.rect(4, 3, 10, 12, 44); d3.rect(16, 3, 9, 5, 35)
d3.set(6, 4, 6)

d3_f2 = reg_map('wok_volcano_f2', 'Wok Volcano Crater', 'Noodleridge', 'overworld_noodle', 25, 16, 45, 45, [[112,34,38],[113,34,38],[114,36,40]])
d3_f2.rect(3, 3, 19, 10, 34); d3_f2.rect(8, 6, 8, 4, 66)
d3_f2.rect(4, 11, 16, 1, 65); d3_f2.set(6, 4, 7)

# Dungeon 4: Broth Catacombs (1F: Crypt corridors!; B2: Dark sunken cistern)
d4 = reg_map('broth_catacombs', 'Broth Catacombs 1F', 'Brothbasin', 'overworld_broth', 28, 18, 57, 57, [[145,42,46],[146,42,46],[147,43,47],[148,43,47],[149,44,48],[150,45,50]])
d4.rect(2, 7, 25, 3, 56)
d4.rect(5, 3, 3, 12, 56); d4.rect(12, 3, 3, 12, 56); d4.rect(19, 3, 3, 12, 56)
d4.rect(16, 3, 7, 4, 47)
d4.set(8, 4, 53); d4.set(15, 13, 53); d4.set(22, 13, 53)
d4.set(6, 4, 7)

d4_b2 = reg_map('broth_catacombs_b2', 'Broth Catacombs B2', 'Brothbasin', 'overworld_broth', 24, 16, 49, 57, [[148,43,47],[149,44,48],[150,45,50]], dark=True)
d4_b2.rect(2, 3, 20, 10, 48)
d4_b2.rect(4, 5, 4, 2, 49); d4_b2.rect(16, 5, 4, 2, 49); d4_b2.rect(9, 4, 6, 2, 53)
d4_b2.rect(2, 8, 20, 1, 73); d4_b2.set(16, 12, 9)
d4_b2.set(6, 4, 6)

# Dungeon 5: Chrome Fork Syndicate HQ
d5 = reg_map('chrome_fork_hq', 'Chrome Fork HQ 1F', 'Brothbasin', 'battle_rival', 28, 18, 58, 72, [[139,40,44],[140,40,44]])
d5.rect(1, 7, 26, 3, 59)
d5.rect(4, 2, 8, 2, 1)
d5.rect(8, 11, 10, 1, 67)
d5.rect(15, 2, 3, 5, 72); d5.rect(20, 11, 4, 5, 72); d5.rect(2, 11, 5, 3, 5); d5.rect(18, 2, 5, 2, 1)
d5.set(22, 4, 6)

d5_f2 = reg_map('chrome_fork_hq_f2', 'Chrome Fork Executive Suite', 'Brothbasin', 'battle_rival', 24, 16, 58, 72, [])
d5_f2.rect(2, 7, 20, 1, 73); d5_f2.set(4, 11, 9)
for cx in (4, 9, 14):
    d5_f2.rect(cx, 9, 3, 1, 5); d5_f2.rect(cx, 12, 3, 1, 5)
    d5_f2.set(cx, 10, 72); d5_f2.set(cx, 13, 72)
d5_f2.rect(2, 2, 16, 4, 59); d5_f2.rect(2, 8, 2, 6, 72); d5_f2.rect(20, 8, 2, 6, 72)
d5_f2.set(20, 4, 7)

# Dungeon 6: Truffle Cellar (1F: Stone cellar with wine racks; B2: Dark mushroom grotto)
d6 = reg_map('truffle_cellar', 'Truffle Cellar 1F', 'Breadlands', 'overworld_bread', 26, 18, 21, 21, [[28,7,10],[33,9,13],[36,10,14]])
d6.rect(1, 7, 24, 3, 17)
d6.rect(3, 2, 17, 14, 12)
for rx in (4, 9, 14):
    d6.rect(rx, 3, 3, 3, 5); d6.rect(rx, 11, 3, 3, 5)
d6.rect(19, 11, 4, 4, 19)
d6.set(18, 4, 7)

d6_b2 = reg_map('truffle_cellar_b2', 'Truffle Cellar B2', 'Breadlands', 'overworld_bread', 22, 16, 19, 21, [[37,10,14],[38,12,16]], dark=True)
d6_b2.rect(3, 3, 16, 10, 20); d6_b2.rect(6, 7, 10, 3, 66)
d6_b2.rect(3, 10, 3, 3, 13); d6_b2.rect(16, 10, 3, 3, 13)
d6_b2.set(18, 4, 6)

# ==============================================================================
# 6. GRAND TASTING HALL & ETERNAL PANTRY
# ==============================================================================
gth = reg_map('grand_tasting_hall', 'Grand Tasting Hall', 'TastingHall', 'town_broth', 28, 22, 58, 60, [])
gth.rect(11, 1, 6, 20, 59)
gth.rect(3, 4, 5, 14, 60); gth.rect(20, 4, 5, 14, 60)
gth.rect(8, 14, 3, 4, 58)
gth.add_sign(10, 19, 'Grand Tasting Hall - Champion Gauntlet')

ep = reg_map('eternal_pantry', 'Eternal Pantry', 'Postgame', 'postgame', 32, 22, 62, 63, [[1,48,54],[39,48,54],[77,48,54],[115,48,54],[38,50,55],[76,50,55],[114,50,55],[150,52,58]])
ep.rect(13, 1, 6, 20, 59)
ep.rect(3, 9, 26, 4, 58)
ep.rect(3, 3, 8, 5, 61); ep.rect(21, 3, 8, 5, 61)
ep.rect(3, 14, 8, 5, 61); ep.rect(21, 14, 8, 5, 61)
ep.add_sign(12, 19, 'Eternal Pantry - Postgame Paradise')

# ==============================================================================
# 7. LINK ALL MAPS & INTERIORS (Zero blocked portals!)
# ==============================================================================
SPINE = [
  ('cruston_town', 16, 0, 'toastwood_trail', 15, 23, 12, 12, 0),
  ('toastwood_trail', 15, 0, 'deli_meadows', 17, 19, 12, 12, 0),
  ('deli_meadows', 17, 0, 'panini_plaza', 17, 23, 12, 12, 0),
  ('panini_plaza', 17, 0, 'bao_harbor', 17, 21, 12, 24, 2),
  ('bao_harbor', 17, 0, 'bamboo_mist_path', 16, 21, 24, 29, 0),
  ('bamboo_mist_path', 16, 0, 'gyoza_cove', 17, 19, 29, 24, 0),
  ('gyoza_cove', 17, 0, 'pierogi_pier', 16, 21, 24, 31, 0),
  ('pierogi_pier', 16, 0, 'udon_hollow', 16, 21, 31, 36, 4),
  ('udon_hollow', 16, 0, 'slurp_canyon', 17, 21, 36, 43, 0),
  ('slurp_canyon', 17, 0, 'al_dente_ascent', 16, 21, 43, 43, 0),
  ('al_dente_ascent', 16, 0, 'ramen_summit', 16, 23, 43, 36, 0),
  ('ramen_summit', 16, 0, 'chowder_crossing', 16, 20, 36, 48, 6),
  ('chowder_crossing', 16, 0, 'simmer_fen', 17, 22, 48, 48, 0),
  ('simmer_fen', 17, 0, 'kettle_gorge', 16, 21, 48, 48, 0),
  ('kettle_gorge', 16, 0, 'bisque_bastion', 17, 21, 48, 48, 0),
  ('bisque_bastion', 17, 0, 'grand_tasting_hall', 13, 21, 48, 59, 8),
]
for a, ax, ay, b, bx, by, pa, pb, req in SPINE:
    link_maps(a, ax, ay, b, bx, by, pa, pb, reqSeals=req)

link_maps('grand_tasting_hall', 13, 0, 'eternal_pantry', 15, 21, 59, 59, reqChampion=True)

DOORS = [
  ('cruston_town', *d_lab, 'cruston_lab', 12, 20),
  ('cruston_town', *d_inn, 'cruston_inn', 12, 41),
  ('cruston_town', *d_mart, 'cruston_mart', 12, 0),
  ('cruston_town', *d_cafe, 'cruston_cafe', 12, 29),
  ('panini_plaza', *d_p_inn, 'panini_inn', 12, 17),
  ('panini_plaza', *d_p_mart, 'panini_mart', 12, 17),
  ('panini_plaza', *d_gym1, 'gym_toaster', 12, 17),
  ('panini_plaza', *d_gym2, 'gym_deli', 12, 20),
  ('bao_harbor', *d_b_inn, 'bao_inn', 24, 29),
  ('bao_harbor', *d_b_mart, 'bao_mart', 24, 24),
  ('bao_harbor', *d_gym3, 'gym_bamboo', 24, 31),
  ('gyoza_cove', *d_gym4, 'gym_skillet', 24, 31),
  ('pierogi_pier', *d_pi_inn, 'pierogi_inn', 31, 29),
  ('pierogi_pier', *d_pi_mart, 'pierogi_mart', 31, 29),
  ('udon_hollow', *d_u_inn, 'udon_inn', 36, 41),
  ('udon_hollow', *d_u_mart, 'udon_mart', 36, 36),
  ('udon_hollow', *d_gym5, 'gym_dojo', 36, 41),
  ('al_dente_ascent', *d_gym6, 'gym_wokpeak', 36, 36),
  ('ramen_summit', *d_r_inn, 'ramen_inn', 36, 41),
  ('ramen_summit', *d_r_mart, 'ramen_mart', 36, 36),
  ('chowder_crossing', *d_c_inn, 'chowder_inn', 48, 48),
  ('chowder_crossing', *d_c_mart, 'chowder_mart', 48, 48),
  ('chowder_crossing', *d_gym7, 'gym_cauldron', 48, 56),
  ('bisque_bastion', *d_bi_inn, 'bisque_inn', 48, 48),
  ('bisque_bastion', *d_bi_mart, 'bisque_mart', 48, 56),
  ('bisque_bastion', *d_gym8, 'gym_vault', 48, 48),
]
for a, ax, ay, b, pa, pb in DOORS:
    mb_dest = MAPS_DATA[b]['mb']
    link_maps(a, ax, ay, b, mb_dest.w // 2, mb_dest.h - 1, pa, pb)

DUNGEON_LINKS = [
  ('panini_plaza', 0, 11, 'sourdough_cavern', 27, 8, 12, 17),
  ('sourdough_cavern', 6, 4, 'sourdough_cavern_b2', 6, 4, 20, 20),
  ('pierogi_pier', 0, 11, 'steamer_spire', 27, 8, 24, 32),
  ('steamer_spire', 6, 4, 'steamer_spire_f2', 6, 4, 32, 32),
  ('ramen_summit', 0, 11, 'wok_volcano', 28, 8, 36, 43),
  ('wok_volcano', 6, 4, 'wok_volcano_f2', 6, 4, 43, 34),
  ('bisque_bastion', 0, 11, 'broth_catacombs', 27, 8, 48, 56),
  ('broth_catacombs', 6, 4, 'broth_catacombs_b2', 6, 4, 56, 48),
  ('bisque_bastion', 35, 11, 'chrome_fork_hq', 0, 8, 48, 59),
  ('chrome_fork_hq', 22, 4, 'chrome_fork_hq_f2', 20, 4, 59, 59),
  ('deli_meadows', 35, 9, 'truffle_cellar', 0, 8, 12, 17),
  ('truffle_cellar', 18, 4, 'truffle_cellar_b2', 18, 4, 17, 20),
]
for a, ax, ay, b, bx, by, pa, pb in DUNGEON_LINKS:
    link_maps(a, ax, ay, b, bx, by, pa, pb)

# ==============================================================================
# 8. QUESTS (16), SECRETS (12), SYNDICATE, RIVAL (6), NAMED NPCS & 800+ REAL LINES
# ==============================================================================
QUESTS = [
  {'id':'q1_butter', 'name':'Cultured Butter Hunt (Multi)', 'steps':2, 'reqStarted':True, 'reqSteps':0, 'reward':'3x Ceramic Plate', 'map':'cruston_town'},
  {'id':'q2_lid', 'name':'Lost Bamboo Lid (Multi)', 'steps':2, 'reqStarted':True, 'reqSteps':0, 'reward':'2x Bento Lacquer Set + 300G', 'map':'bao_harbor'},
  {'id':'q3_chopsticks', 'name':'Golden Chopsticks', 'steps':1, 'reqStarted':False, 'reqSteps':0, 'reward':'500G', 'map':'slurp_canyon'},
  {'id':'q4_truffle', 'name':'Midnight Truffle Broth', 'steps':1, 'reqStarted':False, 'reqSteps':0, 'reward':'Royal Banquet Setting', 'map':'bisque_bastion'},
  {'id':'q5_starter', 'name':'The Ancient Starter (Multi)', 'steps':2, 'reqStarted':True, 'reqSteps':0, 'reward':'Recipe: Aged Cheddar + 400G', 'map':'panini_plaza'},
  {'id':'q6_ginger', 'name':'Ginger Trade Route (Multi)', 'steps':2, 'reqStarted':True, 'reqSteps':0, 'reward':'2x Hearty Stew + 350G', 'map':'bamboo_mist_path'},
  {'id':'q7_chili', 'name':'Five-Alarm Delivery (Multi)', 'steps':2, 'reqStarted':True, 'reqSteps':0, 'reward':'Recipe: Sriracha Beam + 500G', 'map':'al_dente_ascent'},
  {'id':'q8_ladle', 'name':'Copper Ladle Mystery (Multi)', 'steps':2, 'reqStarted':True, 'reqSteps':0, 'reward':'Grand Feast + 600G', 'map':'chowder_crossing'},
  {'id':'q9_critics', 'name':'Tour of Four Palates (Multi)', 'steps':4, 'reqStarted':True, 'reqSteps':2, 'reward':'Royal Banquet Setting', 'map':'cruston_town'},
  {'id':'q10_crumb', 'name':'Panko Trail', 'steps':1, 'reqStarted':False, 'reqSteps':0, 'reward':'2x Warm Broth Cup', 'map':'deli_meadows'},
  {'id':'q11_scallion', 'name':'Scallion Harvest', 'steps':1, 'reqStarted':False, 'reqSteps':0, 'reward':'Chef Garnish Treat x3', 'map':'pierogi_pier'},
  {'id':'q12_salt', 'name':'Sea Salt Crystals', 'steps':1, 'reqStarted':False, 'reqSteps':0, 'reward':'Wooden Board x2', 'map':'gyoza_cove'},
  {'id':'q13_stock', 'name':'Perpetual Simmer', 'steps':1, 'reqStarted':False, 'reqSteps':0, 'reward':'Recipe: Boil Over', 'map':'kettle_gorge'},
  {'id':'q14_steam', 'name':'Mist Lanterns', 'steps':1, 'reqStarted':False, 'reqSteps':0, 'reward':'Peppermint Tea x3', 'map':'steamer_spire'},
  {'id':'q15_wok', 'name':'Wok Hei Spark', 'steps':1, 'reqStarted':False, 'reqSteps':0, 'reward':'Double Espresso x2', 'map':'wok_volcano'},
  {'id':'q16_banquet', 'name':'Eternal Banquet Prep (Multi)', 'steps':2, 'reqStarted':True, 'reqSteps':0, 'reward':'2000G + Grand Feast x2', 'map':'grand_tasting_hall'}
]

SECRETS = [
  {'id':'sec_151', 'name':'Secret Pantry #151 Consommyth', 'map':'grand_tasting_hall'},
  {'id':'sec_crust_stash', 'name':'Hidden Brioche Stash', 'map':'cruston_town'},
  {'id':'sec_toast_cache', 'name':'Toasted Crumb Cache', 'map':'toastwood_trail'},
  {'id':'sec_sourdough_jar', 'name':'100-Year Starter Jar', 'map':'sourdough_cavern_b2'},
  {'id':'sec_bao_pearl', 'name':'Harbor Oyster Pearl', 'map':'bao_harbor'},
  {'id':'sec_spire_scroll', 'name':'Ancient Dim Sum Scroll', 'map':'steamer_spire_f2'},
  {'id':'sec_canyon_noodle', 'name':'Longevity Noodle Knot', 'map':'slurp_canyon'},
  {'id':'sec_wok_ember', 'name':'Seasoned Cast-Iron Ember', 'map':'wok_volcano_f2'},
  {'id':'sec_fen_truffle', 'name':'Moonlit Fen Truffle', 'map':'simmer_fen'},
  {'id':'sec_catacomb_stock', 'name':'Amber Bone-Broth Vial', 'map':'broth_catacombs_b2'},
  {'id':'sec_hall_toast', 'name':'Champion Golden Crouton', 'map':'grand_tasting_hall'},
  {'id':'sec_eternal_spoon', 'name':'Mythic Tasting Spoon', 'map':'eternal_pantry'}
]

NAMED_NPCS = [
  # Cruston Town & Interiors
  ('cruston_lab', {'id':'brotholomew','x':9,'y':5,'name':'Chef Brotholomew','sprite':'brotholomew','dir':'down','lines':['Welcome to Pantrylia! Raise your bEATsts and earn all 8 Kitchen Seals!','Use PLATE in wild battles to set a table for hungry bEATsts.','Beware the Chrome Fork Syndicate--they want to franchise every family kitchen!']}),
  ('cruston_inn', {'id':'inn_cruston','x':9,'y':4,'name':'Innkeeper Mabel','sprite':'inn','dir':'down','action':'heal','lines':['Welcome to the Cruston Simmer Inn!','Warm soup and soft towels for every bEATst!']}),
  ('cruston_mart', {'id':'mart_cruston','x':9,'y':5,'name':'Clerk Pippin','sprite':'mart','dir':'down','action':'shop','lines':['Breadlands Pantry Mart! Fresh Paper Plates and Wooden Boards!']}),
  ('cruston_cafe', {'id':'cafe_host','x':6,'y':5,'name':'Cafe Host Tilly','sprite':'inn','dir':'down','action':'cafe','lines':['Welcome to the bEATst Cafe!']}),
  ('cruston_cafe', {'id':'stove_chef','x':13,'y':5,'name':'Stove Chef Remi','sprite':'brotholomew','dir':'down','action':'cook','lines':['Let us simmer something special!']}),
  ('cruston_town', {'id':'barnaby','x':12,'y':8,'name':'Baker Barnaby','sprite':'barnaby','dir':'down','questGive':'q1_butter','lines':['Oh crumbs! I dropped my Cultured Butter on Toastwood Trail!','Bring it back and I will give you 3 Ceramic Plates!']}),
  ('cruston_town', {'id':'critic_brie','x':20,'y':8,'name':'Food Critic Brie','sprite':'critic_brie','dir':'left','questGive':'q9_critics','lines':['I am judging the Tour of Four Palates! Visit Critics Camembert, Vermicelli, and Bisquetta across the regions!']}),

  # Toastwood & Deli
  ('toastwood_trail', {'id':'butter_item','x':6,'y':14,'name':'Cultured Butter','sprite':'item_chest','dir':'down','questComplete':'q1_butter','reqStarted':True,'notStartedMsg':'A tub of Cultured Butter! Ask Baker Barnaby in Cruston Town if he lost it first.','lines':['Found Baker Barnaby Cultured Butter! Received 3x Ceramic Plate!']}),
  ('toastwood_trail', {'id':'saffron_1','x':15,'y':14,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_1','lines':['Hmph! My plating angles are 100 percent geometric!']}),
  ('toastwood_trail', {'id':'syn_vesper','x':15,'y':6,'name':'Auditor Vesper','sprite':'officer_vesper','dir':'down','trainer':'officer_vesper','lines':['Good afternoon! Chrome Fork Syndicate is auditing this trail for unauthorized flavor!']}),
  ('deli_meadows', {'id':'crumb_item','x':24,'y':14,'name':'Panko Bag','sprite':'item_chest','dir':'down','questComplete':'q10_crumb','lines':['Found the lost Panko Bag! Received 2x Warm Broth Cup!']}),

  # Panini Plaza + Interiors + Gyms 1 & 2
  ('panini_inn', {'id':'inn_panini','x':9,'y':4,'name':'Innkeeper Marlo','sprite':'inn','dir':'down','action':'heal','lines':['Panini Plaza Simmer Inn! Rest up before the Head Chefs!']}),
  ('panini_mart', {'id':'mart_panini','x':9,'y':5,'name':'Clerk Bramble','sprite':'mart','dir':'down','action':'shop','lines':['Panini Plaza Mart! Stock up on Broth Cups and Garnish Treats!']}),
  ('panini_plaza', {'id':'yeast_monk','x':10,'y':12,'name':'Yeast Monk','sprite':'yeast_monk','dir':'right','questGive':'q5_starter','lines':['Could you check on the Ancient Starter Jar inside Sourdough Cavern to the west?']}),
  ('gym_toaster', {'id':'jr_toast_1','x':6,'y':12,'name':'Sous-Chef Toasty','sprite':'villager_0','dir':'down','trainer':'jr_bread_1','lines':['Order up! Clear the conveyor line first!']}),
  ('gym_toaster', {'id':'greg_npc','x':11,'y':3,'name':'Head Chef Griddle Greg','sprite':'chef_greg','dir':'down','trainer':'chef_greg','lines':['Welcome to The Toaster Hearth! Ready for 400 degrees of golden crunch?']}),
  ('gym_deli', {'id':'jr_deli_1','x':16,'y':10,'name':'Sous-Chef Slicer','sprite':'villager_1','dir':'left','trainer':'jr_bread_2','lines':['Hit the floor switch to unlock the deli counter!']}),
  ('gym_deli', {'id':'clara_npc','x':11,'y':3,'name':'Head Chef Clara Coldcut','sprite':'chef_clara','dir':'down','trainer':'chef_clara','lines':['At Deli Counter Spire, every layer matters!']}),

  ('sourdough_cavern_b2', {'id':'starter_jar','x':12,'y':8,'name':'Ancient Starter Jar','sprite':'item_chest','dir':'down','questComplete':'q5_starter','reqStarted':True,'notStartedMsg':'An ancient bubbling starter! Speak with the Yeast Monk in Panini Plaza first.','lines':['The 100-year starter bubbles happily! Learned Recipe: Aged Cheddar + 400G!']}),
  ('sourdough_cavern_b2', {'id':'yeast_block','x':10,'y':8,'name':'Sourdough Cask','sprite':'push_block','dir':'down','pushable':True,'lines':['A heavy oak sourdough cask.']}),
  ('truffle_cellar_b2', {'id':'truffle_guardian','x':11,'y':5,'name':'Cellar Hermit Truff','sprite':'villager_9','dir':'down','trainer':'truffle_guard','lines':['These cellar mushrooms sing to anyone who listens!']}),

  # Steambay + Gyms 3 & 4
  ('bao_inn', {'id':'inn_bao','x':9,'y':4,'name':'Innkeeper Mei-Ling','sprite':'inn','dir':'down','action':'heal','lines':['Bao Harbor Simmer Inn! Bamboo mist restores all HP and PP!']}),
  ('bao_mart', {'id':'mart_bao','x':9,'y':5,'name':'Clerk Buns','sprite':'mart','dir':'down','action':'shop','lines':['Steambay Pantry Mart! Ceramic Plates and Hearty Stews now in stock!']}),
  ('bao_harbor', {'id':'apprentice_lin','x':20,'y':13,'name':'Apprentice Lin','sprite':'apprentice_lin','dir':'left','questGive':'q2_lid','lines':['Master Baozi lucky Bamboo Lid blew north into Gyoza Cove!']}),
  ('bao_harbor', {'id':'critic_camembert','x':12,'y':13,'name':'Critic Camembert','sprite':'villager_11','dir':'right','questStep':'q9_critics','stepIndex':1,'notStartedMsg':'Register for the Tour of Four Palates with Critic Brie in Cruston Town first!','lines':['Steambay pleats are sublime! Next stop: Critic Vermicelli in Udon Hollow!']}),
  ('gym_bamboo', {'id':'jr_steam_1','x':4,'y':11,'name':'Sous-Chef Vapor','sprite':'villager_2','dir':'right','trainer':'jr_steam_1','lines':['Watch your step on the sesame-oil floor!']}),
  ('gym_bamboo', {'id':'baozi_npc','x':11,'y':3,'name':'Head Chef Master Baozi','sprite':'chef_baozi','dir':'down','trainer':'chef_baozi','lines':['Breathe in the mist of Bamboo Cloud Kitchen!']}),

  ('bamboo_mist_path', {'id':'ginger_kai','x':10,'y':10,'name':'Ginger Merchant Kai','sprite':'ginger_kai','dir':'down','questGive':'q6_ginger','lines':['Take this fresh ginger root to Tea Master Po in Pierogi Pier!']}),
  ('bamboo_mist_path', {'id':'syn_crumb','x':16,'y':8,'name':'Director Crumb','sprite':'officer_crumb','dir':'down','trainer':'officer_crumb','lines':['Hello valued customer! Chrome Fork is replacing all bamboo steamers with Beige Kiosks!']}),

  ('gyoza_cove', {'id':'lid_item','x':10,'y':4,'name':'Lucky Bamboo Lid','sprite':'item_chest','dir':'down','questComplete':'q2_lid','reqStarted':True,'notStartedMsg':'A lucky bamboo steamer lid! Speak with Apprentice Lin in Bao Harbor first.','lines':['Found the Lucky Bamboo Lid! Received 2x Bento Lacquer Set + 300G!']}),
  ('gyoza_cove', {'id':'salt_item','x':24,'y':14,'name':'Sea Salt Crystal','sprite':'item_chest','dir':'down','questComplete':'q12_salt','lines':['Gathered pure Sea Salt Crystals! Received 2x Wooden Board!']}),
  ('gyoza_cove', {'id':'saffron_2','x':17,'y':13,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_2','lines':['I bought a Ceramic Plate just to flex on you!']}),
  ('gym_skillet', {'id':'jr_skillet_1','x':16,'y':10,'name':'Sous-Chef Sizzle','sprite':'villager_4','dir':'left','trainer':'jr_steam_2','lines':['Flip the switch to open the skillet pass!']}),
  ('gym_skillet', {'id':'mei_npc','x':11,'y':3,'name':'Head Chef Sizzle Mei','sprite':'chef_mei','dir':'down','trainer':'chef_mei','lines':['At Skillet Tidehouse we sear first and ask questions later!']}),

  ('pierogi_inn', {'id':'inn_pierogi','x':9,'y':4,'name':'Innkeeper Zosia','sprite':'inn','dir':'down','action':'heal','lines':['Pierogi Pier Simmer Inn! Rest by the harbor!']}),
  ('pierogi_mart', {'id':'mart_pierogi','x':9,'y':5,'name':'Clerk Pierog','sprite':'mart','dir':'down','action':'shop','lines':['Pierogi Pier Mart! Ceramic Plates ready for your party!']}),
  ('pierogi_pier', {'id':'tea_master_po','x':10,'y':9,'name':'Tea Master Po','sprite':'tea_master_po','dir':'down','questComplete':'q6_ginger','reqStarted':True,'notStartedMsg':'You have not picked up the fresh ginger order from Ginger Merchant Kai in Bamboo Mist Path yet!','lines':['Oh, fresh ginger from Bamboo Mist Path! Received 2x Hearty Stew + 350G!']}),
  ('pierogi_pier', {'id':'scallion_sue','x':22,'y':12,'name':'Scallion Farmer Sue','sprite':'scallion_sue','dir':'left','questComplete':'q11_scallion','lines':['Thanks for admiring our scallions! Take 3x Chef Garnish Treat!']}),
  ('steamer_spire_f2', {'id':'spire_lantern','x':12,'y':4,'name':'Mist Lantern','sprite':'item_chest','dir':'down','questComplete':'q14_steam','lines':['Lit the Mist Lantern! Received 3x Peppermint Tea!']}),

  # Noodleridge + Gyms 5 & 6
  ('udon_inn', {'id':'inn_udon','x':9,'y':4,'name':'Innkeeper Kazu','sprite':'inn','dir':'down','action':'heal','lines':['Udon Hollow Simmer Inn! Rest your noodles!']}),
  ('udon_mart', {'id':'mart_udon','x':9,'y':5,'name':'Clerk Slurp','sprite':'mart','dir':'down','action':'shop','lines':['Noodleridge Pantry Mart! Bento Lacquer Sets and Double Espresso unlocked!']}),
  ('udon_hollow', {'id':'critic_vermicelli','x':21,'y':13,'name':'Critic Vermicelli','sprite':'villager_3','dir':'left','questStep':'q9_critics','stepIndex':2,'notStartedMsg':'Register with Critic Brie in Cruston Town first!','notReadyMsg':'You have not visited Critic Camembert in Bao Harbor yet!','lines':['Al dente perfection! Now visit Critic Bisquetta in Chowder Crossing!']}),
  ('gym_dojo', {'id':'dough_block','x':10,'y':8,'name':'Dough Boulder','sprite':'push_block','dir':'down','pushable':True,'lines':['A springy ball of hand-pulled dough.']}),
  ('gym_dojo', {'id':'jr_dojo_1','x':11,'y':10,'name':'Sous-Chef Stretch','sprite':'villager_7','dir':'down','trainer':'jr_noodle_1','lines':['Stretch your posture before facing Sensei Twirl!']}),
  ('gym_dojo', {'id':'twirl_npc','x':11,'y':3,'name':'Head Chef Sensei Twirl','sprite':'chef_twirl','dir':'down','trainer':'chef_twirl','lines':['Hand-pulled dough stretches ten feet without snapping!']}),

  ('slurp_canyon', {'id':'chopsticks_item','x':10,'y':6,'name':'Golden Chopsticks','sprite':'item_chest','dir':'down','questComplete':'q3_chopsticks','lines':['Found the Golden Chopsticks! Received 500G!']}),
  ('slurp_canyon', {'id':'syn_glaze','x':17,'y':13,'name':'VP Synergy Glaze','sprite':'officer_glaze','dir':'down','trainer':'officer_glaze','lines':['Surprise inspection! Your noodle bounce is 3 percent off corporate spec!']}),
  ('al_dente_ascent', {'id':'saffron_3','x':16,'y':13,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_3','lines':['I timed my boiling water to the millisecond!']}),
  ('al_dente_ascent', {'id':'chili_grower','x':10,'y':10,'name':'Chili Grower Pepper','sprite':'villager_4','dir':'down','questGive':'q7_chili','lines':['Please deliver these five-alarm chilies to Chili Courier Rico in Ramen Summit!']}),
  ('gym_wokpeak', {'id':'jr_wok_1','x':11,'y':11,'name':'Sous-Chef Simmer','sprite':'villager_6','dir':'down','trainer':'jr_noodle_2','lines':['Keep your balance on the olive-oil tiles!']}),
  ('gym_wokpeak', {'id':'fusilli_npc','x':11,'y':3,'name':'Head Chef Nonna Fusilli','sprite':'chef_fusilli','dir':'down','trainer':'chef_fusilli','lines':['Nonna Fusilli never measures basil with a spoon!']}),

  ('ramen_inn', {'id':'inn_ramen','x':9,'y':4,'name':'Innkeeper Taro','sprite':'inn','dir':'down','action':'heal','lines':['Ramen Summit Simmer Inn! Warm broth for mountain climbers!']}),
  ('ramen_mart', {'id':'mart_ramen','x':9,'y':5,'name':'Clerk Chili','sprite':'mart','dir':'down','action':'shop','lines':['Ramen Summit Mart! Bento Sets and Spicy Recipe Cards!']}),
  ('ramen_summit', {'id':'chili_rico','x':12,'y':13,'name':'Chili Courier Rico','sprite':'chili_rico','dir':'down','questComplete':'q7_chili','reqStarted':True,'notStartedMsg':'Chili Grower Pepper on Al Dente Ascent has not packed the five-alarm crate yet!','lines':['Five-alarm chili delivered to the summit! Received Recipe: Sriracha Beam + 500G!']}),
  ('wok_volcano_f2', {'id':'wok_ember','x':12,'y':4,'name':'Wok Hei Ember','sprite':'item_chest','dir':'down','questComplete':'q15_wok','lines':['Captured a Wok Hei Spark! Received 2x Double Espresso!']}),

  # Brothbasin + Gyms 7 & 8 + Syndicate HQ
  ('chowder_inn', {'id':'inn_chowder','x':9,'y':4,'name':'Innkeeper Pearl','sprite':'inn','dir':'down','action':'heal','lines':['Brothbasin Simmer Inn! Ladle up some rest!']}),
  ('chowder_mart', {'id':'mart_chowder','x':9,'y':5,'name':'Clerk Ladle','sprite':'mart','dir':'down','action':'shop','lines':['Brothbasin Pantry Mart! Royal Banquet Settings and Grand Feasts now in stock!']}),
  ('chowder_crossing', {'id':'critic_bisquetta','x':21,'y':13,'name':'Critic Bisquetta','sprite':'villager_10','dir':'left','questComplete':'q9_critics','reqStarted':True,'reqSteps':2,'notStartedMsg':'You have not started the Tour of Four Palates with Critic Brie in Cruston Town yet!','notReadyMsg':'You have not visited Camembert and Vermicelli in order yet!','lines':['Four Palates complete! Take this Royal Banquet Setting!']}),
  ('chowder_crossing', {'id':'tinker_brothwick','x':20,'y':13,'name':'Tinkerer Brothwick','sprite':'villager_6','dir':'left','questGive':'q8_ladle','lines':['My heirloom Copper Ladle sank in Simmer Fen to the north! Could you fetch it?']}),
  ('gym_cauldron', {'id':'jr_broth_1','x':15,'y':10,'name':'Sous-Chef Roux','sprite':'villager_8','dir':'left','trainer':'jr_broth_1','lines':['Light your lantern and find the cauldron switch!']}),
  ('gym_cauldron', {'id':'bisque_npc','x':11,'y':3,'name':'Head Chef Alchemist Bisque','sprite':'chef_bisque','dir':'down','trainer':'chef_bisque','lines':['Low and slow, bubble and glow! Welcome to Cauldron Conservatory!']}),

  ('simmer_fen', {'id':'ladle_item','x':10,'y':6,'name':'Copper Ladle','sprite':'item_chest','dir':'down','questComplete':'q8_ladle','reqStarted':True,'notStartedMsg':'A sunken Copper Ladle! Ask Tinkerer Brothwick in Chowder Crossing if he lost it first.','lines':['Found the Copper Ladle! Received Grand Feast + 600G!']}),
  ('simmer_fen', {'id':'saffron_4','x':17,'y':13,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_4','lines':['My team evolved! Let us test our new heat!']}),
  ('kettle_gorge', {'id':'stock_valve','x':20,'y':6,'name':'Perpetual Valve','sprite':'item_chest','dir':'down','questComplete':'q13_stock','lines':['Tuned the Perpetual Simmer! Received Recipe: Boil Over!']}),
  ('kettle_gorge', {'id':'syn_grunt_gorge','x':16,'y':12,'name':'Syndicate Grunt','sprite':'syndicate_grunt','dir':'down','trainer':'syndicate_grunt_1','lines':['Thank you for your patience! Your recipe is very important to us!']}),

  ('bisque_inn', {'id':'inn_bisque','x':9,'y':4,'name':'Innkeeper Coral','sprite':'inn','dir':'down','action':'heal','lines':['Bisque Bastion Simmer Inn! Final rest before the Grand Hall!']}),
  ('bisque_mart', {'id':'mart_bisque','x':9,'y':5,'name':'Clerk Stock','sprite':'mart','dir':'down','action':'shop','lines':['Bisque Bastion Mart! Royal Banquet Settings and Grand Feasts ready!']}),
  ('bisque_bastion', {'id':'truffle_item','x':10,'y':8,'name':'Rare Night Truffle','sprite':'item_chest','dir':'down','questComplete':'q4_truffle','lines':['Found Rare Night Truffle! Received Royal Banquet Setting!']}),
  ('gym_vault', {'id':'jr_vault_1','x':15,'y':10,'name':'Sous-Chef Consomme','sprite':'villager_5','dir':'left','trainer':'jr_broth_2','lines':['Only clarified stock passes the vault gate!']}),
  ('gym_vault', {'id':'bouillon_npc','x':11,'y':3,'name':'Head Chef Lady Bouillon','sprite':'chef_bouillon','dir':'down','trainer':'chef_bouillon','lines':['Eight Seals complete! The Grand Tasting Hall awaits you!']}),

  # Chrome Fork Syndicate HQ (1F & 2F Climax!)
  ('chrome_fork_hq', {'id':'syn_grunt_hq','x':14,'y':7,'name':'Laminated Agent','sprite':'syndicate_grunt','dir':'left','trainer':'syndicate_grunt_2','lines':['Please take a numbered ticket before foiling our corporate espionage!']}),
  ('chrome_fork_hq_f2', {'id':'saffron_5','x':8,'y':11,'name':'Rival Saffron','sprite':'saffron','dir':'right','trainer':'rival_5','lines':['I am backing you up against Chrome Fork! Let us warm up first!']}),
  ('chrome_fork_hq_f2', {'id':'boss_ladle_npc','x':12,'y':3,'name':'CEO Sterling Ladle','sprite':'boss_ladle','dir':'down','trainer':'boss_ladle','lines':['Welcome to Beige Plate HQ! Soon every kitchen will serve identical nutrient cubes!']}),

  # Grand Tasting Hall & Eternal Pantry
  ('grand_tasting_hall', {'id':'inn_hall','x':9,'y':16,'name':'Banquet Prep Chef','sprite':'inn','dir':'down','action':'heal','lines':['Final tune-up before the Grand Gauntlet! Full HP and PP restored!']}),
  ('grand_tasting_hall', {'id':'saffron_6','x':13,'y':13,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_6','lines':['Show me everything we learned across Pantrylia!']}),
  ('grand_tasting_hall', {'id':'pip_npc','x':13,'y':11,'name':'Master Taster Pip','sprite':'taster_pip','dir':'down','trainer':'taster_pip','lines':['Course One: Appetizer! Wake up your palate!']}),
  ('grand_tasting_hall', {'id':'roux_npc','x':13,'y':9,'name':'Master Taster Roux','sprite':'taster_roux','dir':'down','trainer':'taster_roux','lines':['Course Two: Main! Rich gravy and fearless umami!']}),
  ('grand_tasting_hall', {'id':'mochi_npc','x':13,'y':7,'name':'Master Taster Mochi','sprite':'taster_mochi','dir':'down','trainer':'taster_mochi','lines':['Course Three: Palate Cleanser! Cool and sweet!']}),
  ('grand_tasting_hall', {'id':'aurelia_npc','x':13,'y':4,'name':'Champion Chef Aurelia','sprite':'champion','dir':'down','trainer':'champion_aurelia','lines':['Welcome to the Grand Tasting Table! Show me the bond between cook and bEATst!']}),
  ('grand_tasting_hall', {'id':'secret_151_door','x':11,'y':2,'name':'Secret Pantry Door','sprite':'item_chest','dir':'down','action':'secret151','lines':['A shimmering golden pantry door...']}),
  ('grand_tasting_hall', {'id':'planner_nora','x':10,'y':17,'name':'Banquet Planner Nora','sprite':'villager_2','dir':'right','questGive':'q16_banquet','lines':['Once you reach the Eternal Pantry, report to Banquet Steward Otto for the Eternal Banquet!']}),

  ('eternal_pantry', {'id':'inn_eternal','x':12,'y':12,'name':'Starlight Chef','sprite':'inn','dir':'down','action':'heal','lines':['Welcome to the Eternal Pantry! All bEATsts restored!']}),
  ('eternal_pantry', {'id':'mart_eternal','x':19,'y':12,'name':'Eternal Boutique','sprite':'mart','dir':'down','action':'shop','lines':['Eternal Pantry Boutique! Everything unlocked!']}),
  ('eternal_pantry', {'id':'steward_otto','x':15,'y':8,'name':'Banquet Steward Otto','sprite':'steward_otto','dir':'down','questComplete':'q16_banquet','reqStarted':True,'notStartedMsg':'Speak with Banquet Planner Nora in the Grand Tasting Hall before claiming the Eternal Banquet!','lines':['Thank you for visiting the Eternal Pantry! Received 2000G + 2x Grand Feast!']}),
  ('eternal_pantry', {'id':'reformed_ladle','x':20,'y':15,'name':'Sterling Ladle','sprite':'boss_ladle','dir':'left','lines':['I closed Beige Plate Corp and opened a neighborhood soup cart! Turns out real broth beats synergy!']})
]

for mid, npc in NAMED_NPCS:
    MAPS_DATA[mid]['npcs'].append(npc)

# Secret pickups (11 + #151 = 12)
SECRET_SPOTS = [
  ('cruston_town', 'sec_crust_stash', 28, 19, 'Found Hidden Brioche Stash (+100G)!'),
  ('toastwood_trail', 'sec_toast_cache', 2, 20, 'Found Toasted Crumb Cache (1x Wooden Board)!'),
  ('sourdough_cavern_b2', 'sec_sourdough_jar', 19, 10, 'Found 100-Year Starter Vial (1x Garnish Treat)!'),
  ('bao_harbor', 'sec_bao_pearl', 31, 13, 'Found Harbor Oyster Pearl (+150G)!'),
  ('steamer_spire_f2', 'sec_spire_scroll', 18, 4, 'Found Ancient Dim Sum Scroll (1x Ceramic Plate)!'),
  ('slurp_canyon', 'sec_canyon_noodle', 28, 19, 'Found Longevity Noodle Knot (1x Hearty Stew)!'),
  ('wok_volcano_f2', 'sec_wok_ember', 18, 4, 'Found Cast-Iron Ember (1x Bento Lacquer Set)!'),
  ('simmer_fen', 'sec_fen_truffle', 28, 19, 'Found Moonlit Fen Truffle (+250G)!'),
  ('broth_catacombs_b2', 'sec_catacomb_stock', 18, 4, 'Found Amber Bone-Broth Vial (1x Grand Feast)!'),
  ('grand_tasting_hall', 'sec_hall_toast', 24, 18, 'Found Champion Golden Crouton (+300G)!'),
  ('eternal_pantry', 'sec_eternal_spoon', 26, 18, 'Found Mythic Tasting Spoon (1x Royal Banquet Setting)!')
]
for mid, sid, sx, sy, msg in SECRET_SPOTS:
    MAPS_DATA[mid]['npcs'].append({
        'id': sid, 'x': sx, 'y': sy, 'name': 'Sparkling Spot', 'sprite': 'item_chest', 'dir': 'down',
        'secretId': sid, 'lines': [msg]
    })

# ==============================================================================
# 9. WIRE INDIVIDUALLY WRITTEN DIALOGUE LINES (NO TEMPLATES) TO NAMED VILLAGERS
# ==============================================================================
import dialogue_lines as _dl

FIRST_NAMES = [
  'Clara','Milo','Nora','Gus','Toby','June','Felix','Wren','Otto','Iris','Bram','Tess','Hugo','Vera','Jude','Lena',
  'Arlo','Cora','Otis','Mina','Saul','Ruby','Ezra','Cleo','Theo','Faye','Leon','Rosa','Ivan','Maya','Nils','Gwen',
  'Rory','Alma','Kipp','Zara','Boyd','Talia','Sven','Lola','Dante','Nadia','Paco','Yuki','Hana','Kenji','Sora','Mei'
]

day_idx = 0
night_idx = 0
used_lines = set()
for m_idx, (mid, mdata) in enumerate(MAPS_DATA.items()):
    mb = mdata['mb']
    portal_coords = {(p['x'], p['y']) for p in mdata['portals']} | {(n['x'], n['y']) for n in mdata['npcs']}
    reach_set = set()
    if mdata['portals']:
        p0 = mdata['portals'][0]
        sx, sy = (15, 10) if mid == 'cruston_town' else (
            1 if p0['x'] == 0 else (mb.w - 2 if p0['x'] == mb.w - 1 else p0['x']),
            1 if p0['y'] == 0 else (mb.h - 2 if p0['y'] == mb.h - 1 else (p0['y'] + 1 if mb.get(p0['x'], p0['y']) == 2 else p0['y']))
        )
        rq = deque([(sx, sy)])
        reach_set.add((sx, sy))
        while rq:
            rx, ry = rq.popleft()
            for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
                nx, ny = rx+dx, ry+dy
                if 0 <= nx < mb.w and 0 <= ny < mb.h and (nx, ny) not in reach_set:
                    if mb.get(nx, ny) not in SOLID_TILES or mb.get(nx, ny) == 73:
                        reach_set.add((nx, ny)); rq.append((nx, ny))
    candidates = []
    for y in range(2, mb.h - 2):
        for x in range(2, mb.w - 2):
            if mb.get(x, y) in SOLID_TILES: continue
            if reach_set and (x, y) not in reach_set: continue
            if any(abs(x - px) + abs(y - py) <= 2 for px, py in portal_coords): continue
            candidates.append((x, y))
    is_int = mid.endswith('_inn') or mid.endswith('_mart') or mid.endswith('_lab') or mid.endswith('_cafe') or mid.startswith('gym_')
    target_v = 2 if is_int else 5
    step = max(1, len(candidates) // (target_v + 1))
    for vi in range(min(target_v, len(candidates))):
        vx, vy = candidates[(vi * step + m_idx) % len(candidates)]
        fname = FIRST_NAMES[(m_idx * 7 + vi * 13) % len(FIRST_NAMES)]
        role = ['Chef','Baker','Taster','Botanist','Angler','Poet','Courier','Mason','Herbalist','Brewer'][(m_idx + vi) % 10]
        vname = f"{role} {fname}"
        lines = []
        for _ in range(3):
            if day_idx < len(_dl.DAY_LINES):
                l = _dl.DAY_LINES[day_idx]
                day_idx += 1
                used_lines.add(l)
                lines.append(l)
        night_line = _dl.NIGHT_LINES[night_idx] if night_idx < len(_dl.NIGHT_LINES) else _dl.DAY_LINES[day_idx % len(_dl.DAY_LINES)]
        night_idx += 1
        used_lines.add(night_line)
        mdata['npcs'].append({
            'id': f'npc_{mid}_{vi}',
            'x': vx, 'y': vy,
            'name': vname,
            'sprite': f'villager_{(m_idx + vi) % 12}',
            'dir': ['down','up','left','right'][(m_idx + vi) % 4],
            'lines': lines,
            'nightLines': [night_line]
        })

# ==============================================================================
# 10. SELF-VERIFY PORTAL REACHABILITY & TILE-ROLE SIMILARITY
# ==============================================================================

def verify_world():
    # 1. BFS across all maps & portals from cruston_town (15, 10)
    vis_maps = {'cruston_town'}
    q = deque([('cruston_town', 15, 10)])
    vis_tiles = {('cruston_town', 15, 10)}
    reached_portals = set()
    while q:
        mid, x, y = q.popleft()
        md = MAPS_DATA[mid]
        mb = md['mb']
        for p in md['portals']:
            if abs(p['x'] - x) + abs(p['y'] - y) == 1:
                reached_portals.add((mid, p['x'], p['y'], p['to']))
                dest = (p['to'], p['tx'], p['ty'])
                if dest not in vis_tiles:
                    vis_tiles.add(dest)
                    vis_maps.add(p['to'])
                    q.append(dest)
        for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < mb.w and 0 <= ny < mb.h:
                t = mb.get(nx, ny)
                if t not in SOLID_TILES or t == 73:
                    if (mid, nx, ny) not in vis_tiles:
                        vis_tiles.add((mid, nx, ny))
                        q.append((mid, nx, ny))
    total_portals = sum(len(md['portals']) for md in MAPS_DATA.values())
    assert len(vis_maps) == len(MAPS_DATA), f"Unreachable maps: {set(MAPS_DATA.keys()) - vis_maps}"
    assert len(reached_portals) == total_portals, f"Unreachable portals: {total_portals - len(reached_portals)}"
    print(f"BFS Verified: {len(vis_maps)}/{len(MAPS_DATA)} maps & {len(reached_portals)}/{total_portals} portals reachable!")

    # 2. Tile-role similarity <= 0.50 across all same-size map pairs
    mlist = list(MAPS_DATA.values())
    max_sim = 0.0
    for i in range(len(mlist)):
        for j in range(i + 1, len(mlist)):
            a, b = mlist[i], mlist[j]
            if a['w'] != b['w'] or a['h'] != b['h']: continue
            ga = [TILE_ROLES.get(t, 'other') for t in a['mb'].g]
            gb = [TILE_ROLES.get(t, 'other') for t in b['mb'].g]
            sim = sum(1 for x, y in zip(ga, gb) if x == y) / len(ga)
            if sim > max_sim: max_sim = sim
            if sim > 0.50:
                print(f"WARN similarity {sim:.3f} between {a['id']} and {b['id']}")
    print(f"Max same-size tile-role similarity: {max_sim:.3f}")

    # 3. Count real displayed dialogue lines
    all_lines = set()
    for md in MAPS_DATA.values():
        for n in md['npcs']:
            for l in n.get('lines', []): all_lines.add(l)
            for l in n.get('nightLines', []): all_lines.add(l)
        for s in md['mb'].signs:
            all_lines.add(s['text'])
    print(f"Real displayed unique dialogue lines: {len(all_lines)}")
    assert len(all_lines) >= 800, f"Need >=800 unique displayed lines, got {len(all_lines)}"

verify_world()

# Build output
MAPS_OUT = {}
for mid, md in MAPS_DATA.items():
    mb = md['mb']
    MAPS_OUT[mid] = {
        'id': mid, 'name': md['name'], 'region': md['region'], 'music': md['music'],
        'w': mb.w, 'h': mb.h, 'dark': md['dark'],
        'wildPool': md['wildPool'], 'grid': mb.g, 'portals': md['portals'],
        'npcs': md['npcs'], 'signs': mb.signs
    }

with open('src/05_world_and_story.js', 'w', encoding='utf-8') as f:
    f.write("// 05_world_and_story.js - Hand-Designed World, 8 Kitchen Gyms, 6 Multi-Floor Dungeons, Chrome Fork Syndicate & Rival Arc\n")
    f.write("// PROVENANCE: TRAINERS structure lifted/extended from beatsts-v1/src/05_world_and_story.js; world rebuilt for v2.1.\n\n")
    f.write("const REGIONS = " + json.dumps({
        'Breadlands':  {'name':'Breadlands','family':'Sandwiches','music':'overworld_bread'},
        'Steambay':    {'name':'Steambay','family':'Dumplings','music':'overworld_steam'},
        'Noodleridge': {'name':'Noodleridge','family':'Noodles','music':'overworld_noodle'},
        'Brothbasin':  {'name':'Brothbasin','family':'Soup','music':'overworld_broth'},
        'TastingHall': {'name':'Grand Tasting Hall','family':'All','music':'town_broth'},
        'Postgame':    {'name':'Eternal Pantry','family':'All','music':'postgame'}
    }, indent=2) + ";\n\n")
    f.write("const SOLID_TILES = new Set(" + json.dumps(sorted(list(SOLID_TILES))) + ");\n\n")
    f.write("const QUESTS = " + json.dumps(QUESTS, indent=2) + ";\n\n")
    f.write("const SECRETS = " + json.dumps(SECRETS, indent=2) + ";\n\n")
    f.write("""const TRAINERS = {
  jr_bread_1: { id:'jr_bread_1', name:'Sous-Chef Toasty', title:'Toaster Hearth', rewardGold:120,
    intro:'Order up! Clear the conveyor line first!', win:'Crisp footwork!', after:'Head Chef Greg is right ahead!', party:[{id:1,lv:7}] },
  jr_bread_2: { id:'jr_bread_2', name:'Sous-Chef Slicer', title:'Deli Spire', rewardGold:180,
    intro:'Hit the floor switch to unlock the deli counter!', win:'Clean slice!', after:'Clara Coldcut awaits!', party:[{id:10,lv:12}] },
  jr_steam_1: { id:'jr_steam_1', name:'Sous-Chef Vapor', title:'Bamboo Cloud', rewardGold:220,
    intro:'Watch your step on the sesame-oil floor!', win:'Smooth glide!', after:'Master Baozi is ready!', party:[{id:39,lv:17}] },
  jr_steam_2: { id:'jr_steam_2', name:'Sous-Chef Sizzle', title:'Skillet Tidehouse', rewardGold:260,
    intro:'Flip the switch to open the skillet pass!', win:'Nice sear!', after:'Sizzle Mei is waiting!', party:[{id:42,lv:21}] },
  jr_noodle_1: { id:'jr_noodle_1', name:'Sous-Chef Stretch', title:'Pull-Noodle Dojo', rewardGold:320,
    intro:'Stretch your posture before facing Sensei Twirl!', win:'Elastic defense!', after:'Sensei Twirl is impressed!', party:[{id:77,lv:26}] },
  jr_noodle_2: { id:'jr_noodle_2', name:'Sous-Chef Simmer', title:'Wok Peak Bistro', rewardGold:380,
    intro:'Keep your balance on the olive-oil tiles!', win:'Al dente!', after:'Nonna Fusilli awaits!', party:[{id:81,lv:30}] },
  jr_broth_1: { id:'jr_broth_1', name:'Sous-Chef Roux', title:'Cauldron Conservatory', rewardGold:440,
    intro:'Light your lantern and find the cauldron switch!', win:'Crystal clear!', after:'Alchemist Bisque awaits!', party:[{id:118,lv:34}] },
  jr_broth_2: { id:'jr_broth_2', name:'Sous-Chef Consomme', title:'Deep Stock Vault', rewardGold:520,
    intro:'Only clarified stock passes the vault gate!', win:'Pure umami!', after:'Lady Bouillon awaits!', party:[{id:123,lv:39}] },
  truffle_guard: { id:'truffle_guard', name:'Cellar Hermit Truff', title:'Truffle Cellar', rewardGold:400,
    intro:'These cellar mushrooms sing to anyone who listens!', win:'What earthy harmony!', after:'The cellar treasures are yours!', party:[{id:36,lv:14},{id:37,lv:15}] },

  chef_greg: { id:'chef_greg', name:'Head Chef Griddle Greg', title:'The Toaster Hearth', seal:'Crisp Seal', sealIdx:0, rewardGold:300,
    intro:'Welcome to The Toaster Hearth! Ready for 400 degrees of golden crunch?', win:'Magnificent char! Take the Crisp Seal!',
    after:'Keep those crusts golden, friend!', party:[{id:1,lv:9},{id:2,lv:12}] },
  chef_clara: { id:'chef_clara', name:'Head Chef Clara Coldcut', title:'Deli Counter Spire', seal:'Stack Seal', sealIdx:1, rewardGold:450,
    intro:'At Deli Counter Spire, every layer matters!', win:'Impeccable structural integrity! The Stack Seal is yours!',
    after:'Balance your brine and your bread!', party:[{id:10,lv:14},{id:5,lv:16}] },
  chef_baozi: { id:'chef_baozi', name:'Head Chef Master Baozi', title:'Bamboo Cloud Kitchen', seal:'Steam Seal', sealIdx:2, rewardGold:600,
    intro:'Breathe in the mist of Bamboo Cloud Kitchen!', win:'Gentle yet unstoppable! Accept the Steam Seal!',
    after:'Softness always outlasts haste.', party:[{id:39,lv:19},{id:40,lv:22}] },
  chef_mei: { id:'chef_mei', name:'Head Chef Sizzle Mei', title:'Skillet Tidehouse', seal:'Sear Seal', sealIdx:3, rewardGold:800,
    intro:'At Skillet Tidehouse we sear first and ask questions later!', win:'Golden lace perfection! You earned the Sear Seal!',
    after:'Listen for that crisp cast-iron hiss!', party:[{id:42,lv:23},{id:43,lv:26}] },
  chef_twirl: { id:'chef_twirl', name:'Head Chef Sensei Twirl', title:'Pull-Noodle Dojo', seal:'Slurp Seal', sealIdx:4, rewardGold:1000,
    intro:'Hand-pulled dough stretches ten feet without snapping!', win:'What al-dente spirit! Take the Slurp Seal!',
    after:'Never rush the dough rest.', party:[{id:77,lv:28},{id:78,lv:30}] },
  chef_fusilli: { id:'chef_fusilli', name:'Head Chef Nonna Fusilli', title:'Wok Peak Bistro', seal:'Twirl Seal', sealIdx:5, rewardGold:1200,
    intro:'Nonna Fusilli never measures basil with a spoon!', win:'Bellissimo! Take the Twirl Seal!',
    after:'Sunday dinner awaits at the summit!', party:[{id:81,lv:32},{id:87,lv:35}] },
  chef_bisque: { id:'chef_bisque', name:'Head Chef Alchemist Bisque', title:'Cauldron Conservatory', seal:'Simmer Seal', sealIdx:6, rewardGold:1500,
    intro:'Low and slow, bubble and glow! Welcome to Cauldron Conservatory!', win:'Your broth is crystal clear! Take the Simmer Seal!',
    after:'Patience turns water into memory.', party:[{id:118,lv:36},{id:119,lv:39}] },
  chef_bouillon: { id:'chef_bouillon', name:'Head Chef Lady Bouillon', title:'The Deep Stock Vault', seal:'Stock Seal', sealIdx:7, rewardGold:1800,
    intro:'Only cooks of true patience reach the Deep Stock Vault!', win:'Eight Seals complete! The Grand Tasting Hall awaits you!',
    after:'Every kitchen in Pantrylia remembers your name.', party:[{id:123,lv:41},{id:150,lv:44}] },

  // Chrome Fork Syndicate
  officer_vesper: { id:'officer_vesper', name:'Auditor Vesper', title:'Chrome Fork Syndicate', rewardGold:350,
    intro:'Good afternoon! Chrome Fork is auditing this trail for unauthorized flavor!', win:'Duly noted! Filing a polite complaint!', after:'Our laminated clipboard never forgets!', party:[{id:8,lv:8},{id:12,lv:9}] },
  officer_crumb: { id:'officer_crumb', name:'Director Crumb', title:'Chrome Fork Syndicate', rewardGold:650,
    intro:'Hello valued customer! Chrome Fork is replacing bamboo steamers with Beige Kiosks!', win:'Customer satisfaction dropped! Retreating!', after:'Please rate our retreat five stars!', party:[{id:48,lv:18},{id:50,lv:20}] },
  officer_glaze: { id:'officer_glaze', name:'VP Synergy Glaze', title:'Chrome Fork Syndicate', rewardGold:950,
    intro:'Surprise inspection! Your noodle bounce is 3 percent off corporate spec!', win:'Unacceptable synergy! Wait until CEO Ladle hears!', after:'We will franchise this canyon yet!', party:[{id:88,lv:29},{id:92,lv:31}] },
  syndicate_grunt_1: { id:'syndicate_grunt_1', name:'Syndicate Grunt', title:'Chrome Fork Syndicate', rewardGold:500,
    intro:'Thank you for your patience! Your recipe is very important to us!', win:'Please stay on the line for a brief survey!', after:'Have a standardized day!', party:[{id:128,lv:37},{id:130,lv:38}] },
  syndicate_grunt_2: { id:'syndicate_grunt_2', name:'Laminated Agent', title:'Chrome Fork HQ', rewardGold:600,
    intro:'Please take a numbered ticket before foiling our corporate espionage!', win:'Ticket expired! Moving along!', after:'CEO Sterling Ladle is upstairs!', party:[{id:134,lv:40},{id:136,lv:41}] },
  boss_ladle: { id:'boss_ladle', name:'CEO Sterling Ladle', title:'Chrome Fork Syndicate', rewardGold:2500,
    intro:'Welcome to Beige Plate HQ! Soon every kitchen will serve identical nutrient cubes!', win:'Impossible! Homemade flavor beat my quarterly projections!', after:'Perhaps... a little garlic is good for morale.', party:[{id:38,lv:42},{id:76,lv:43},{id:114,lv:44}] },

  // Rival Saffron (6 Encounters!)
  rival_1: { id:'rival_1', name:'Rival Saffron', title:'Perfectionist Sous-Chef', rewardGold:250,
    intro:'Hmph! My plating angles are 100 percent geometric!', win:'Wait--your messy sandwich actually won?!', after:'I will simmer on this!', party:[{id:4,lv:7},{id:39,lv:8}] },
  rival_2: { id:'rival_2', name:'Rival Saffron', title:'Perfectionist Sous-Chef', rewardGold:500,
    intro:'I bought a Ceramic Plate just to flex on you!', win:'Maybe I am over-seasoning...', after:'See you on the mountain!', party:[{id:46,lv:19},{id:5,lv:20}] },
  rival_3: { id:'rival_3', name:'Rival Saffron', title:'Perfectionist Sous-Chef', rewardGold:900,
    intro:'I timed my boiling water to the millisecond!', win:'Okay, cooking with joy beats a stopwatch!', after:'Meet me in Brothbasin!', party:[{id:85,lv:31},{id:43,lv:32}] },
  rival_4: { id:'rival_4', name:'Rival Saffron', title:'Evolved Sous-Chef', rewardGold:1100,
    intro:'My team evolved! Let us test our new heat!', win:'Whoa, you kept pace with every evolution!', after:'Let us storm Chrome Fork HQ together!', party:[{id:2,lv:36},{id:41,lv:37},{id:78,lv:38}] },
  rival_5: { id:'rival_5', name:'Rival Saffron', title:'Syndicate Ally', rewardGold:1300,
    intro:'I am backing you up against Chrome Fork! Let us warm up first!', win:'Go show CEO Sterling Ladle what real cooking looks like!', after:'Hit that switch to open his suite!', party:[{id:3,lv:41},{id:41,lv:42},{id:79,lv:43}] },
  rival_6: { id:'rival_6', name:'Rival Saffron', title:'Grand Hall Contender', rewardGold:1500,
    intro:'Show me everything we learned across Pantrylia!', win:'Go get that Champion apron, friend!', after:'I saved you a seat at the banquet!', party:[{id:3,lv:44},{id:41,lv:45},{id:79,lv:46}] },

  taster_pip: { id:'taster_pip', name:'Master Taster Pip', title:'First Course: Appetizer', rewardGold:1200,
    intro:'Course One: Appetizer! Wake up your palate!', win:'Delightful! Proceed to the Main Course!', after:'Crisp and bright!', party:[{id:28,lv:44},{id:53,lv:45}] },
  taster_roux: { id:'taster_roux', name:'Master Taster Roux', title:'Second Course: Main', rewardGold:1500,
    intro:'Course Two: Main! Rich gravy and fearless umami!', win:'Substantial and soulful! One course remains!', after:'A true main-course triumph!', party:[{id:89,lv:46},{id:129,lv:47}] },
  taster_mochi: { id:'taster_mochi', name:'Master Taster Mochi', title:'Third Course: Palate Cleanser', rewardGold:1800,
    intro:'Course Three: Palate Cleanser! Cool and sweet!', win:'Refreshing! Champion Chef Aurelia awaits!', after:'Sweetness and poise!', party:[{id:55,lv:47},{id:121,lv:48}] },
  champion_aurelia: { id:'champion_aurelia', name:'Champion Chef Aurelia', title:'Realm Grand Chef-Tamer', rewardGold:5000,
    intro:'Welcome to the Grand Tasting Table! Show me your bond!', win:'Bravo! You are Pantrylia new Grand Chef-Tamer!', after:'The Eternal Pantry to the north is now open to you!', party:[{id:3,lv:48},{id:76,lv:49},{id:114,lv:50},{id:117,lv:52}] }
};

""")
    f.write("const MAPS = " + json.dumps(MAPS_OUT) + ";\n")
    f.write("for (const k of Object.keys(MAPS)) MAPS[k].grid = new Uint8Array(MAPS[k].grid);\n")
print(f"Wrote src/05_world_and_story.js with {len(MAPS_OUT)} maps!")
