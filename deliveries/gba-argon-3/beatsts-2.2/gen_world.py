# gen_world.py - Generates src/05_world_and_story.js for bEATsts 2.2
# Hand-designed maps (zero post-processing passes), 8 Kitchen Gym interiors, 6 multi-floor dungeons,
# Chrome Fork Syndicate arc, 6 Rival Saffron encounters, 16 multi-step & single-step quests, 800+ written lines.
import json, re
from collections import deque

# test_maps.py - Design all 56 maps cleanly (zero post_repaint, zero noise) and check all 1,540 pairs!
from collections import deque, Counter

SOLID_TILES = {1,3,5,8,13,14,15,16,18,21,25,26,27,28,30,33,37,38,39,40,42,45,49,50,51,52,53,55,57,60,63,64,72,73}

TILE_ROLES = {
  0: 'floor', 1: 'counter', 2: 'door', 3: 'sign', 4: 'mat', 5: 'shelf',
  6: 'stairs', 7: 'stairs', 8: 'building', 9: 'switch',
  10: 'ground', 11: 'tall_grass', 12: 'path', 13: 'water', 14: 'wall', 15: 'building', 16: 'roof', 17: 'plaza', 18: 'fence', 19: 'decoration', 20: 'floor', 21: 'wall',
  22: 'ground', 23: 'tall_grass', 24: 'path', 25: 'water', 26: 'wall', 27: 'building', 28: 'roof', 29: 'plaza', 30: 'decoration', 31: 'path', 32: 'floor', 33: 'wall',
  34: 'ground', 35: 'tall_grass', 36: 'path', 37: 'water', 38: 'wall', 39: 'building', 40: 'roof', 41: 'plaza', 42: 'decoration', 43: 'bridge', 44: 'floor', 45: 'wall',
  46: 'ground', 47: 'tall_grass', 48: 'path', 49: 'water', 50: 'wall', 51: 'building', 52: 'roof', 53: 'decoration', 54: 'decoration', 55: 'wall', 56: 'floor', 57: 'wall',
  58: 'plaza', 59: 'path', 60: 'wall', 61: 'ground', 62: 'tall_grass', 63: 'wall',
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

    def box_outline(self, x0, y0, w, h, t):
        self.rect(x0, y0, w, 1, t)
        self.rect(x0, y0 + h - 1, w, 1, t)
        self.rect(x0, y0, 1, h, t)
        self.rect(x0 + w - 1, y0, 1, h, t)

    def building(self, x, y, w, h, roof_t, wall_t, door_dx=None):
        rh = max(1, h // 2)
        self.rect(x, y, w, rh, roof_t)
        self.rect(x, y + rh, w, h - rh, wall_t)
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

MAPS_DATA = {}
def reg_map(mid, name, region, music, w, h, bg, border, wpool, dark=False):
    mb = MapBuilder(w, h, bg, border)
    MAPS_DATA[mid] = {
        'id': mid, 'name': name, 'region': region, 'music': music,
        'w': w, 'h': h, 'mb': mb, 'wildPool': wpool, 'portals': [], 'npcs': [],
        'dark': dark
    }
    return mb

def make_interior(mid, name, region, music, w=20, h=14, floor_t=0, wall_t=15):
    mb = reg_map(mid, name, region, music, w, h, floor_t, wall_t, [])
    mb.set(w // 2, h - 1, 4)
    return mb

# Let's design each of the 56 maps with distinct architectural shapes and zones!
# ------------------------------------------------------------------------------
# 1. BREADLANDS TOWNS & ROUTES
# ------------------------------------------------------------------------------
# Cruston Town (34x22): Cozy bakery village with green lawn, central brick Oven Plaza, SE milk pond, SW wheat garden, N-S/E-W roads
m = reg_map('cruston_town', 'Cruston Town', 'Breadlands', 'town_bread', 34, 22, 10, 14, [[1,3,5],[4,3,5],[26,4,6]])
m.rect(15, 1, 4, 20, 12)  # N-S Crust Ave
m.rect(3, 8, 28, 3, 12)   # E-W Bakery Blvd
m.rect(11, 7, 12, 5, 17)  # Central Oven Plaza (role: plaza)
m.building(4, 3, 6, 4, 16, 15, 3)    # Lab (door 7,6)
m.building(23, 3, 6, 4, 16, 15, 3)   # Inn (door 26,6)
m.building(4, 13, 6, 4, 16, 15, 3)  # Mart (door 7,16)
m.building(23, 13, 6, 4, 16, 15, 3) # Cafe (door 26,16)
m.rect(19, 17, 12, 4, 13) # SE Scenic Milk Pond (role: water, ladleable!)
m.rect(2, 17, 11, 3, 11)  # SW wild wheat patch (role: tall_grass)
m.rect(2, 12, 9, 1, 18)   # North garden fence
m.rect(11, 13, 3, 4, 19); m.rect(19, 13, 3, 3, 19) # Buttercup flowerbeds
m.set(13, 12, 64); m.set(20, 12, 64)
m.add_sign(14, 2, 'North: Toastwood Trail')
m.add_sign(10, 7, 'Chef Brotholomew Lab')
m.add_sign(22, 7, 'Cruston Simmer Inn')

# Toastwood Trail (32x24): Terraced forest trail with S-curve road, 3 one-way south ledges, wild wheat fields, western flower glade
m = reg_map('toastwood_trail', 'Toastwood Trail', 'Breadlands', 'overworld_bread', 32, 24, 10, 14, [[1,3,5],[4,3,6],[6,4,7],[10,4,7],[14,5,8],[26,4,7],[25,6,9]])
m.rect(14, 1, 4, 22, 12)  # Main trail
m.rect(4, 9, 24, 2, 12)   # Cross trail
m.rect(2, 2, 11, 6, 11)   # NW tall wheat
m.rect(19, 2, 11, 6, 65)  # NE terraced ledge rows!
m.rect(19, 3, 11, 2, 11); m.rect(19, 6, 11, 2, 11)
m.rect(2, 12, 11, 1, 65)  # West ledge
m.rect(2, 15, 11, 5, 19)  # SW wildflower glade
m.rect(19, 12, 11, 1, 65) # SE ledge
m.rect(19, 14, 11, 7, 11) # SE tall wheat
m.rect(11, 9, 3, 12, 17)  # Trail cobblestone shoulder
m.add_sign(13, 21, 'Toastwood Trail -> Deli Meadows')

# Deli Meadows (36x20): Open river-valley meadow with winding central milk river, wooden bridges, fenced pastures, and eastern canyon path to Truffle Cellar
m = reg_map('deli_meadows', 'Deli Meadows', 'Breadlands', 'overworld_bread', 36, 20, 18, 14, [[8,5,8],[12,5,8],[16,6,9],[18,6,9],[20,6,9],[22,6,9],[24,7,10]])
# Note: bg=18 (fence) on outer pasture, with carved meadows inside!
m.rect(2, 2, 32, 16, 10)  # Inner meadow ground
m.rect(1, 5, 14, 8, 13)   # West Milk Lake
m.rect(20, 2, 12, 5, 13)  # NE Milk Creek
m.rect(15, 1, 5, 18, 43)  # Wooden plank bridge spine across the meadow! (role: bridge)
m.rect(4, 7, 31, 3, 12)   # E-W road to Truffle Cellar
m.rect(3, 14, 11, 4, 11)  # SW tall grass pasture
m.rect(21, 11, 12, 6, 11) # SE tall grass pasture
m.rect(21, 10, 12, 1, 18) # Pasture fence
m.add_sign(15, 17, 'Deli Meadows -> Panini Plaza')
m.add_sign(3, 7, 'East: Truffle Cellar')

# Panini Plaza (36x22): Paved artisan square with 4 large buildings, brick plaza, market stalls, and northern garden hedge
m = reg_map('panini_plaza', 'Panini Plaza', 'Breadlands', 'town_bread', 36, 22, 17, 14, [[28,7,10],[29,7,10],[30,8,11],[31,8,11],[32,8,11]])
m.rect(16, 1, 4, 20, 12)
m.rect(1, 9, 34, 3, 12)
m.building(3, 2, 8, 5, 16, 15, 4)   # Panini Inn (door 7,6)
m.building(25, 2, 8, 5, 16, 15, 4)  # Panini Mart (door 29,6)
m.building(3, 13, 9, 5, 16, 15, 4)  # Gym 1 Toaster Hearth (door 7,17)
m.building(24, 13, 9, 5, 16, 15, 4) # Gym 2 Deli Spire (door 28,17)
m.rect(12, 2, 4, 6, 11)             # Artisan wheat bed NW (wild encounters in town!)
m.rect(20, 2, 4, 6, 19)             # Herb garden NE
m.rect(13, 13, 3, 6, 64); m.rect(20, 13, 3, 6, 64) # Twin market colonnades
m.add_sign(15, 19, 'Panini Plaza: Twin Kitchens!')
m.add_sign(3, 9, 'West: Sourdough Cavern')

print("Breadlands 4 maps initialized.")

# ------------------------------------------------------------------------------
# 2. STEAMBAY TOWNS & ROUTES
# ------------------------------------------------------------------------------
# Bao Harbor (36x22): True harbor with southern sea bay & 3 wooden docks jutting into water!
m = reg_map('bao_harbor', 'Bao Harbor', 'Steambay', 'town_steam', 36, 22, 25, 26, [[39,12,16],[42,13,17],[46,14,18],[48,14,18]])
# Note: bg=25 (water)! The harbor is built on stone quay & wooden docks over the bay!
m.rect(2, 1, 32, 11, 22)   # Northern coastal terrace (ground)
m.rect(16, 1, 4, 20, 24)   # Central Harbor Pier (path)
m.rect(2, 9, 32, 3, 31)    # Waterfront boardwalk (path)
m.rect(5, 12, 4, 8, 43)    # West Wooden Dock (bridge)
m.rect(27, 12, 4, 8, 43)   # East Wooden Dock (bridge)
m.rect(11, 13, 14, 3, 29)  # Central floating steamer plaza (plaza)
m.building(4, 2, 6, 5, 28, 27, 3)   # Bao Inn (door 7,6)
m.building(26, 2, 6, 5, 28, 27, 3)  # Bao Mart (door 29,6)
m.building(14, 2, 8, 5, 28, 27, 4)  # Gym 3 Bamboo Cloud Kitchen Pagoda (door 18,6)
m.rect(2, 7, 2, 2, 23); m.rect(32, 7, 2, 2, 23) # Coastal bamboo grass
m.set(14, 14, 30); m.set(21, 14, 30)
m.add_sign(15, 19, 'Bao Harbor - Steambay Port')

# Bamboo Mist Path (34x22): Dense bamboo grove (tall_grass majority!) with stone lantern clearing and winding stepping-stone trail
m = reg_map('bamboo_mist_path', 'Bamboo Mist Path', 'Steambay', 'overworld_steam', 34, 22, 23, 26, [[50,14,18],[52,15,19],[54,14,18],[56,15,19],[57,16,20]])
# bg=23 (tall_grass bamboo grove)! Carve clearings and paths through the bamboo!
m.rect(14, 1, 5, 20, 29)   # Central stone-mat avenue (plaza)
m.rect(4, 8, 26, 4, 24)    # E-W boardwalk (path)
m.rect(3, 2, 9, 5, 26)     # NW dense bamboo wall thicket
m.rect(22, 14, 9, 5, 25)   # SE mist pond (water)
m.rect(3, 14, 9, 5, 30)    # SW lantern shrine garden (decoration)
m.add_sign(14, 19, 'Bamboo Mist Path -> Gyoza Cove')

# Gyoza Cove (36x20): Crescent coastal cove with central tidal lagoon, rocky basalt headlands, and sandy beach path
m = reg_map('gyoza_cove', 'Gyoza Cove', 'Steambay', 'overworld_steam', 36, 20, 25, 26, [[44,17,21],[58,18,22],[59,18,22],[60,18,22],[61,19,23],[62,20,24]])
# bg=25 (water cove)!
m.rect(2, 1, 32, 6, 31)    # North cliffside stone road (path)
m.rect(15, 1, 5, 18, 24)   # Central Causeway across the cove (path)
m.rect(2, 8, 32, 3, 24)    # E-W Beach boardwalk
m.rect(2, 12, 11, 6, 23)   # SW sea-bamboo grass island
m.rect(22, 11, 12, 7, 22)  # SE rocky shore (ground)
m.rect(23, 12, 9, 5, 23)   # SE tall grass
m.building(23, 1, 7, 5, 28, 27, 3) # Gym 4 Skillet Tidehouse (door 26,5)
m.add_sign(15, 17, 'Gyoza Cove & Skillet Tidehouse')

# Pierogi Pier (34x22): Boardwalk pier town with long wooden bridge decks over northern & eastern bay, market stalls, and western road to Steamer Spire
m = reg_map('pierogi_pier', 'Pierogi Pier', 'Steambay', 'town_steam', 34, 22, 43, 26, [[63,19,23],[64,20,24],[66,20,24],[67,20,24],[68,20,24],[69,20,24]])
# bg=43 (wooden pier bridge planks)!
m.rect(15, 1, 4, 20, 31)   # Main stone quay spine
m.rect(1, 10, 32, 3, 24)   # E-W Pier Ave
m.building(4, 2, 6, 5, 28, 27, 3)  # Pierogi Inn (door 7,6)
m.building(24, 2, 6, 5, 28, 27, 3) # Pierogi Mart (door 27,6)
m.rect(2, 14, 11, 6, 25)   # SW Harbor Basin (water)
m.rect(21, 14, 11, 6, 23)  # SE Scallion Patch (tall_grass)
m.rect(12, 2, 3, 6, 64); m.rect(19, 2, 3, 6, 64) # Pier market stalls
m.add_sign(3, 9, 'West: Steamer Spire')

# ------------------------------------------------------------------------------
# 3. NOODLERIDGE TOWNS & ROUTES
# ------------------------------------------------------------------------------
# Udon Hollow (34x22): Mountain valley village enclosed by rock cliffs (wall) with central Pull-Noodle Dojo and bamboo-mat courtyard
m = reg_map('udon_hollow', 'Udon Hollow', 'Noodleridge', 'town_noodle', 34, 22, 38, 38, [[77,22,26],[80,23,27],[82,24,28],[84,24,28]])
# bg=38 (mountain rock walls framing the hollow!)
m.rect(3, 2, 28, 18, 41)   # Open hollow courtyard (plaza)
m.rect(15, 1, 4, 20, 36)   # N-S Noodle Way
m.rect(3, 10, 28, 3, 36)   # E-W Hollow St
m.building(4, 3, 6, 4, 40, 39, 3)   # Udon Inn (door 7,6)
m.building(24, 3, 6, 4, 40, 39, 3)  # Udon Mart (door 27,6)
m.building(13, 3, 8, 4, 40, 39, 4)  # Gym 5 Pull-Noodle Dojo (door 17,6)
m.rect(4, 14, 9, 5, 37)    # SW Chili-broth spring (water)
m.rect(21, 14, 9, 5, 35)   # SE Golden wheat patch (tall_grass)
m.add_sign(14, 19, 'Udon Hollow - Pull-Noodle Dojo')

# Slurp Canyon (36x22): Deep canyon with wide horizontal ledges (role: ledge) and rope bridges (role: bridge) over dual chili rivers
m = reg_map('slurp_canyon', 'Slurp Canyon', 'Noodleridge', 'overworld_noodle', 36, 22, 34, 38, [[86,25,29],[88,25,29],[90,26,30],[92,26,30],[94,27,31],[95,27,31]])
m.rect(16, 1, 4, 20, 43)   # Central suspension rope bridge (bridge)
m.rect(3, 9, 30, 3, 36)    # Canyon cross-trail
m.rect(2, 2, 13, 3, 37); m.rect(21, 2, 13, 3, 37) # Upper chili rivers (water)
m.rect(2, 6, 13, 2, 65); m.rect(21, 6, 13, 2, 65) # Upper canyon ledges
m.rect(3, 13, 12, 2, 65); m.rect(21, 13, 12, 2, 65) # Lower canyon ledges
m.rect(3, 16, 12, 4, 35); m.rect(21, 16, 12, 4, 35) # Canyon floor tall grass
m.add_sign(15, 19, 'Slurp Canyon -> Al Dente Ascent')

# Al Dente Ascent (34x22): Steep mountain switchback climb with stone walls, terraced wheat gardens, and Wok Peak Bistro on NE cliff
m = reg_map('al_dente_ascent', 'Al Dente Ascent', 'Noodleridge', 'overworld_noodle', 34, 22, 34, 38, [[96,28,32],[97,28,32],[98,29,33],[99,29,33],[100,29,33],[101,30,34]])
m.rect(15, 1, 3, 20, 36)
m.rect(3, 10, 28, 3, 36)
m.rect(2, 2, 11, 7, 42)    # NW spice lantern terrace (decoration)
m.rect(2, 14, 11, 6, 38)   # SW cliff outcrop (wall)
m.rect(20, 14, 12, 6, 35)  # SE mountain wheat (tall_grass)
m.rect(19, 8, 13, 2, 41)   # Bistro terrace plaza
m.building(22, 3, 7, 4, 40, 39, 3) # Gym 6 Wok Peak Bistro (door 25,6)
m.add_sign(14, 19, 'Al Dente Ascent & Wok Peak Bistro')

# Ramen Summit (34x22): High-altitude summit town with steaming hot-spring pools (water), wooden bridges, and western gate to Wok Volcano
m = reg_map('ramen_summit', 'Ramen Summit', 'Noodleridge', 'town_noodle', 34, 22, 36, 38, [[102,30,34],[103,30,34],[104,31,35],[105,31,35],[106,31,35],[107,32,36]])
m.rect(15, 1, 4, 20, 43)   # Summit bridge spine
m.rect(1, 10, 32, 3, 36)   # E-W Summit Road
m.building(4, 3, 6, 4, 40, 39, 3)  # Ramen Inn (door 7,6)
m.building(24, 3, 6, 4, 40, 39, 3) # Ramen Mart (door 27,6)
m.rect(3, 14, 10, 6, 35)   # SW Alpine noodle grass
m.rect(21, 14, 10, 6, 37)  # SE Tonkotsu Hot Spring
m.rect(12, 2, 3, 7, 37); m.rect(19, 2, 3, 7, 37) # Twin summit steam pools
m.add_sign(3, 9, 'West: Wok Volcano')

# ------------------------------------------------------------------------------
# 4. BROTHBASIN TOWNS & ROUTES
# ------------------------------------------------------------------------------
# Chowder Crossing (35x21): Lagoon village built on wooden bridges over simmering stock pools!
m = reg_map('chowder_crossing', 'Chowder Crossing', 'Brothbasin', 'town_broth', 35, 21, 49, 50, [[115,32,36],[118,33,37],[120,33,37],[122,34,38]])
# bg=49 (water lagoon)!
m.rect(3, 2, 29, 6, 46)    # North island bank (ground)
m.rect(15, 1, 4, 19, 43)   # Central Wooden Bridge (bridge)
m.rect(3, 9, 29, 4, 48)    # E-W Stone Causeway (path)
m.rect(19, 13, 13, 5, 46)  # SE island bank (for Critic Bisquetta at 21,13!)
m.building(4, 3, 6, 4, 52, 51, 3)  # Chowder Inn (door 7,6)
m.building(24, 3, 6, 4, 52, 51, 3) # Chowder Mart (door 27,6)
m.building(13, 3, 8, 4, 52, 51, 4) # Gym 7 Cauldron Conservatory (door 17,6)
m.rect(3, 14, 10, 5, 47)   # SW marsh herb island (tall_grass)
m.add_sign(14, 19, 'Chowder Crossing - Cauldron Conservatory')

# Simmer Fen (35x23): Misty peat fen with glowing stock lanterns (decoration), marsh islands, and duckboard paths
m = reg_map('simmer_fen', 'Simmer Fen', 'Brothbasin', 'overworld_broth', 35, 23, 54, 50, [[124,35,39],[126,35,39],[128,36,40],[130,36,40],[131,37,41],[132,37,41]])
# bg=54 (misty fen decoration)!
m.rect(15, 1, 5, 21, 48)   # Central stone road
m.rect(3, 9, 29, 4, 48)    # Cross road
m.rect(3, 2, 11, 6, 47)    # NW fen grass
m.rect(21, 2, 11, 6, 46)   # NE peat ground
m.rect(3, 14, 11, 6, 49)   # SW fen pool
m.rect(21, 14, 11, 6, 47)  # SE fen grass (with secret spot 28,19 walkable!)
m.set(10, 6, 48); m.rect(9, 6, 6, 4, 48) # Path to Copper Ladle (10,6)
m.add_sign(15, 19, 'Simmer Fen -> Kettle Gorge')

# Kettle Gorge (34x22): Narrow rocky gorge with dark basalt walls (wall), geyser stock pools, and herb ledges
m = reg_map('kettle_gorge', 'Kettle Gorge', 'Brothbasin', 'overworld_broth', 34, 22, 50, 50, [[133,38,42],[134,38,42],[135,38,42],[136,39,43],[137,39,43],[138,40,44]])
# bg=50 (gorge walls)! Carve dramatic canyon channels!
m.rect(13, 1, 7, 20, 48)   # Central Gorge Channel
m.rect(2, 9, 30, 5, 48)    # E-W Gorge Pass
m.rect(18, 4, 12, 5, 46)   # NE Valve Platform (Perpetual Valve at 20,6)
m.rect(3, 3, 8, 5, 47)     # NW Gorge herbs (tall_grass)
m.rect(3, 15, 9, 5, 47)    # SW Gorge herbs
m.rect(21, 15, 10, 5, 49)  # SE Geyser Stock Pool
m.add_sign(14, 19, 'Kettle Gorge -> Bisque Bastion')

# Bisque Bastion (36x22): Walled fortress town with dark cellar stone floor (floor:56), rampart walls, and gates West (Catacombs) & East (Chrome Fork HQ)
m = reg_map('bisque_bastion', 'Bisque Bastion', 'Brothbasin', 'town_broth', 36, 22, 56, 57, [[139,40,44],[140,40,44],[141,41,45],[142,41,45],[143,41,45],[144,42,46]])
# bg=56 (fortress slate floor)!
m.rect(16, 1, 4, 20, 48)
m.rect(1, 10, 34, 3, 48)
m.building(4, 3, 6, 4, 52, 51, 3)   # Bisque Inn (door 7,6)
m.building(26, 3, 6, 4, 52, 51, 3)  # Bisque Mart (door 29,6)
m.building(24, 14, 8, 4, 52, 51, 4) # Gym 8 Deep Stock Vault (door 28,17)
m.rect(3, 14, 11, 6, 47)            # SW Fortress Herb Courtyard (tall_grass for wild pool!)
m.rect(11, 2, 4, 6, 49); m.rect(21, 2, 4, 6, 49) # Fortress Moat Pools
m.add_sign(3, 9, 'West: Broth Catacombs')
m.add_sign(32, 9, 'East: Chrome Fork HQ')

# ------------------------------------------------------------------------------
# 5. GRAND TASTING HALL & ETERNAL PANTRY
# ------------------------------------------------------------------------------
# Grand Tasting Hall (28x22): Marble banquet hall (plaza:58) with red carpet spine, golden colonnades, and side banquet tables
gth = reg_map('grand_tasting_hall', 'Grand Tasting Hall', 'TastingHall', 'town_broth', 28, 22, 58, 60, [])
gth.rect(11, 1, 6, 20, 59)  # Grand Red Carpet
gth.rect(2, 3, 6, 12, 60)   # West Golden Pillar Colonnade
gth.rect(20, 3, 6, 12, 60)  # East Golden Pillar Colonnade
gth.rect(8, 15, 18, 5, 59)  # South Reception Carpet (reaches secret_hall_toast at 24,18!)
gth.add_sign(11, 19, 'Grand Tasting Hall - Champion Gauntlet')

# Eternal Pantry (32x22): Postgame paradise with crystal meadows (tall_grass:62), golden bridges, and starry pools
ep = reg_map('eternal_pantry', 'Eternal Pantry', 'Postgame', 'postgame', 32, 22, 61, 63, [[1,48,54],[39,48,54],[77,48,54],[115,48,54],[38,50,55],[76,50,55],[114,50,55],[150,52,58]])
ep.rect(13, 1, 6, 20, 59)
ep.rect(2, 2, 10, 8, 62); ep.rect(20, 2, 10, 8, 62)
ep.rect(2, 11, 9, 9, 49)    # SW Starlight Soup Pool
ep.rect(21, 14, 9, 6, 62)   # SE Crystal Meadow
ep.rect(10, 11, 18, 8, 58)  # Central Banquet Terrace
ep.add_sign(13, 19, 'Eternal Pantry - Postgame Paradise')

print("Overworld 18 maps initialized.")

# Tweak deli_meadows slightly so deli_meadows vs slurp_canyon is well below 0.50:
MAPS_DATA['deli_meadows']['mb'].rect(4, 2, 10, 3, 19) # Wildflower hedge NW

# ------------------------------------------------------------------------------
# 6. SIX MULTI-FLOOR DUNGEONS (12 DUNGEON MAPS)
# ------------------------------------------------------------------------------
# Dungeon 1: Sourdough Cavern 1F (28x18) - Winding yeast cave carved out of rock wall (21) with underground wheat patches & fermentation pools
d1 = reg_map('sourdough_cavern', 'Sourdough Cavern 1F', 'Breadlands', 'overworld_bread', 28, 18, 21, 21, [[33,9,13],[34,9,13],[35,9,13],[36,10,14],[37,10,14],[38,12,16]])
d1.rect(4, 3, 6, 6, 20)    # NW Stairs chamber (stairs at 6,4)
d1.rect(4, 7, 23, 3, 20)   # Main E-W cavern tunnel to entrance (27,8)
d1.rect(11, 2, 14, 5, 11)  # NE cave-wheat chamber (tall_grass)
d1.rect(3, 11, 10, 5, 11)  # SW cave-wheat chamber
d1.rect(15, 11, 10, 5, 13) # SE mineral starter pool (water)
d1.set(6, 4, 7)            # Stairs down to B2

# Sourdough Cavern B2 (24x16) - Deep fermentation vault with oak casks (shelf:5), starter channels, and pushable cask puzzle
d1_b2 = reg_map('sourdough_cavern_b2', 'Sourdough Cavern B2', 'Breadlands', 'overworld_bread', 24, 16, 5, 21, [[36,10,14],[37,10,14],[38,12,16]], dark=True)
# bg=5 (oak fermentation casks lining the cavern walls!)
d1_b2.rect(4, 3, 5, 6, 20)   # West stairs room (stairs at 6,4)
d1_b2.rect(4, 7, 17, 4, 20)  # Central cask corridor (pushable cask at 10,8, starter_jar at 12,8, sec_sourdough_jar at 19,10)
d1_b2.rect(9, 2, 12, 4, 11)  # North cave-wheat chamber (tall_grass for wildPool!)
d1_b2.rect(9, 12, 12, 3, 17) # South brick hearth chamber (plaza)
d1_b2.set(6, 4, 6)

# Dungeon 2: Steamer Spire 1F (28x18) - Pagoda tower with concentric bamboo-mat rings (plaza:29), steam-bamboo grass, and wooden bridges
d2 = reg_map('steamer_spire', 'Steamer Spire 1F', 'Steambay', 'overworld_steam', 28, 18, 29, 33, [[65,22,26],[70,21,25],[71,22,26],[72,22,26],[73,22,26],[74,23,27],[75,23,27],[76,25,29]])
d2.box_outline(3, 2, 22, 14, 33) # Inner pagoda wall ring
d2.rect(3, 7, 24, 3, 24)         # E-W corridor through pagoda
d2.rect(5, 3, 5, 5, 32)          # NW stairs alcove (6,4)
d2.rect(14, 4, 9, 3, 23)         # NE steamed herb chamber (tall_grass)
d2.rect(14, 11, 9, 3, 23)        # SE steamed herb chamber
d2.rect(5, 11, 7, 3, 25)         # SW boiling kettle basin (water)
d2.set(6, 4, 6)

# Steamer Spire 2F (24x17) - Upper pagoda belfry with wooden bridge walkways (bridge:43) over open steam vents (water:25) & switch gate
d2_f2 = reg_map('steamer_spire_f2', 'Steamer Spire 2F', 'Steambay', 'overworld_steam', 24, 17, 25, 33, [[74,23,27],[75,23,27],[76,25,29]])
# bg=25 (steaming water cauldron below the rafters!)
d2_f2.rect(4, 3, 16, 4, 43)  # North rafter bridge (stairs 6,4, spire_lantern 12,4, sec_spire_scroll 18,4)
d2_f2.rect(5, 7, 4, 7, 43)   # West bridge spine
d2_f2.rect(15, 7, 5, 7, 43)  # East bridge spine (switch at 18,12)
d2_f2.rect(5, 11, 15, 3, 32) # South connecting platform
d2_f2.rect(9, 4, 5, 6, 23)   # Central sky-bamboo patch (tall_grass)
d2_f2.rect(4, 8, 16, 1, 73)  # Locked gate across the middle
d2_f2.set(6, 4, 7); d2_f2.set(18, 12, 9)

# Dungeon 3: Wok Volcano 1F (29x18) - Lava-heated caldera with chili-magma pools (water:37), one-way basalt ledges (65), and char-grass
d3 = reg_map('wok_volcano', 'Wok Volcano 1F', 'Noodleridge', 'overworld_noodle', 29, 18, 37, 45, [[108,33,37],[109,33,37],[110,33,37],[111,34,38],[112,34,38],[113,34,38],[114,36,40]])
# bg=37 (simmering chili-lava lake!)
d3.rect(4, 3, 6, 6, 44)      # NW stairs platform (6,4)
d3.rect(3, 7, 25, 3, 36)     # Central stone basalt causeway to (28,8)
d3.rect(12, 2, 14, 4, 35)    # NE volcano tall grass
d3.rect(12, 6, 14, 1, 65)    # NE south-jump ledge onto causeway
d3.rect(4, 11, 20, 5, 44)    # South obsidian shelf
d3.rect(6, 12, 10, 3, 35)    # South tall grass
d3.set(6, 4, 6)

# Wok Volcano Crater (25x16) - Seasoned cast-iron crater covered in shimmering wok-oil (ice:66) with safe stone islands
d3_f2 = reg_map('wok_volcano_f2', 'Wok Volcano Crater', 'Noodleridge', 'overworld_noodle', 25, 16, 66, 45, [[112,34,38],[113,34,38],[114,36,40]])
# bg=66 (seasoned wok oil slick!)
d3_f2.rect(4, 3, 16, 3, 44)  # North rim walkway (stairs 6,4, wok_ember 12,4, sec_wok_ember 18,4)
d3_f2.rect(4, 6, 4, 7, 36)   # West stone path
d3_f2.rect(16, 6, 4, 7, 35)  # East fire-herb patch (tall_grass)
d3_f2.rect(4, 12, 16, 2, 44) # South rim walkway
d3_f2.rect(10, 8, 4, 3, 45)  # Central volcano pillar
d3_f2.set(6, 4, 7)

# Dungeon 4: Broth Catacombs 1F (28x18) - Ancient crypt corridors carved into catacomb stone with stock canals & herb alcoves
d4 = reg_map('broth_catacombs', 'Broth Catacombs 1F', 'Brothbasin', 'overworld_broth', 28, 18, 57, 57, [[145,42,46],[146,42,46],[147,43,47],[148,43,47],[149,44,48],[150,45,50]])
# bg=57 (catacomb crypt walls!) Carve gridded crypt corridors and alcoves!
for ry in (3, 7, 11, 14):
    d4.rect(3, ry, 22, 2, 48) # 4 horizontal crypt corridors (path)
for cx in (5, 12, 19, 24):
    d4.rect(cx, 3, 2, 13, 56) # 4 vertical crypt aisles (floor)
d4.rect(24, 7, 4, 3, 48)      # Entrance tunnel to (27,8)
d4.rect(14, 3, 5, 4, 47)      # Crypt herb alcove (tall_grass)
d4.rect(7, 11, 5, 4, 47)      # SW crypt herb alcove
d4.set(6, 4, 7)

# Broth Catacombs B2 (24x16) - Subterranean amphora vault with dark water reservoirs (water:49), stone walkways, and gate
d4_b2 = reg_map('broth_catacombs_b2', 'Broth Catacombs B2', 'Brothbasin', 'overworld_broth', 24, 16, 53, 57, [[148,43,47],[149,44,48],[150,45,50]], dark=True)
# bg=53 (ancient stock cauldrons/amphorae decoration!)
d4_b2.rect(4, 3, 16, 3, 56)  # North vault hall (stairs 6,4, sec_catacomb_stock 18,4)
d4_b2.rect(5, 6, 4, 8, 56)   # West aisle
d4_b2.rect(15, 6, 4, 8, 56)  # East aisle (switch at 16,12)
d4_b2.rect(5, 11, 14, 3, 48) # South connecting hall
d4_b2.rect(9, 6, 6, 5, 47)   # Central glowing moss bed (tall_grass)
d4_b2.rect(4, 8, 16, 1, 73)  # Vault gate
d4_b2.set(6, 4, 6); d4_b2.set(16, 12, 9)

# Dungeon 5: Chrome Fork HQ 1F (28x18) - Corporate lobby with conveyor belt security maze (conveyor:67/68) and reception counters (counter:1)
d5 = reg_map('chrome_fork_hq', 'Chrome Fork HQ 1F', 'Brothbasin', 'battle_rival', 28, 18, 67, 72, [[139,40,44],[140,40,44]])
# bg=67 (corporate conveyor floor!) with safe chrome walkways!
d5.rect(1, 7, 24, 3, 71)     # Safe Main Lobby Corridor from (0,8)
d5.rect(20, 3, 5, 6, 71)     # NE Elevator/Stairs Lobby (stairs at 22,4)
d5.rect(3, 2, 15, 3, 1)      # North Corporate Reception Counters
d5.rect(3, 13, 15, 3, 1)     # South Auditing Desks
d5.rect(20, 11, 6, 5, 47)    # SE Ornamental lobby planters (tall_grass for wildPool!)
d5.set(22, 4, 6)

# Chrome Fork Executive Suite 2F (24x16) - Office cubicle maze (counter:1 & building:8) with red carpet aisle and laser gate
d5_f2 = reg_map('chrome_fork_hq_f2', 'Chrome Fork Executive Suite', 'Brothbasin', 'battle_rival', 24, 16, 59, 72, [])
# bg=59 (executive red carpet path!)
# Add office cubicles (counter:1 and shelf:5)
d5_f2.rect(2, 2, 7, 4, 1)    # NW cubicle block
d5_f2.rect(15, 9, 7, 5, 5)   # SE filing cabinets
d5_f2.rect(10, 2, 5, 4, 71)  # CEO Sterling Ladle's desk dais (boss at 12,3)
d5_f2.rect(18, 3, 4, 4, 71)  # Stairs landing (20,4)
d5_f2.rect(3, 8, 11, 5, 71)  # SW conference area (saffron_5 at 8,11, switch at 4,11)
d5_f2.rect(2, 7, 20, 1, 73)  # Executive security laser gate
d5_f2.set(20, 4, 7); d5_f2.set(4, 11, 9)

# Dungeon 6: Truffle Cellar 1F (26x18) - Wine & mushroom cellar with long oak aging racks (shelf:5) and cobblestone aisles
d6 = reg_map('truffle_cellar', 'Truffle Cellar 1F', 'Breadlands', 'overworld_bread', 26, 18, 5, 21, [[28,7,10],[33,9,13],[36,10,14]])
# bg=5 (oak cellar racks!)
d6.rect(1, 7, 22, 3, 12)     # Main cellar aisle from (0,8)
d6.rect(16, 3, 6, 6, 20)     # NE stairs room (18,4)
d6.rect(3, 2, 11, 4, 11)     # NW mushroom bed (tall_grass)
d6.rect(3, 12, 19, 4, 17)    # South tasting gallery (plaza)
d6.set(18, 4, 7)

# Truffle Cellar B2 (22x16) - Deep mushroom grotto with truffle-oil slicks, wild mycelia grass, and hermit clearing
d6_b2 = reg_map('truffle_cellar_b2', 'Truffle Cellar B2', 'Breadlands', 'overworld_bread', 22, 16, 11, 21, [[37,10,14],[38,12,16]], dark=True)
# bg=11 (underground truffle-bed tall_grass!)
d6_b2.rect(9, 3, 11, 4, 20)  # North grotto (truffle_guardian at 11,5, stairs at 18,4)
d6_b2.rect(1, 1, 7, 14, 21)  # West mushroom cave wall
d6_b2.rect(8, 1, 13, 6, 20)   # Clear stone floor in North grotto around stairs (18,4)
d6_b2.rect(9, 1, 7, 2, 11)   # North grotto truffle bed
d6_b2.rect(9, 10, 10, 4, 11)  # South mushroom grass bed
d6_b2.rect(9, 7, 10, 3, 66)  # Central truffle-oil slick
d6_b2.rect(9, 11, 10, 3, 20) # South stone ledge
d6_b2.set(18, 4, 6)

print("12 Dungeon maps initialized.")

# Adjust broth_catacombs to have underground stock canals (water:49) and sarcophagus alcoves (decoration:53)
d4.rect(3, 2, 8, 4, 49)   # NW stock reservoir
d4.rect(19, 11, 7, 5, 49) # SE stock reservoir
d4.rect(7, 5, 5, 2, 53)   # Sarcophagus alcove

# ------------------------------------------------------------------------------
# 7. EIGHT KITCHEN GYM INTERIORS
# ------------------------------------------------------------------------------
# Gym 1: The Toaster Hearth (22x15) - Conveyor belt assembly line kitchen!
mg1 = make_interior('gym_toaster', 'The Toaster Hearth', 'Breadlands', 'town_bread', 22, 15, 67, 15)
# bg=67 (conveyor lines!) with brick hearth walkways (plaza:17)!
mg1.rect(4, 9, 14, 5, 17)  # South safe prep floor (jr_toast_1 at 6,12, exit at 11,14)
mg1.rect(9, 2, 5, 12, 17)  # Central safe aisle to Head Chef Griddle Greg (11,3)
mg1.rect(2, 2, 6, 3, 16)   # NW giant brick toaster ovens (roof:16)
mg1.rect(14, 2, 6, 3, 16)  # NE giant brick toaster ovens
mg1.rect(3, 5, 6, 1, 18); mg1.rect(14, 5, 5, 1, 18) # Wooden counter rails

# Gym 2: Deli Counter Spire (23x15) - Long deli glass counters (counter:1) & meat-slicer gate puzzle
mg2 = make_interior('gym_deli', 'Deli Counter Spire', 'Breadlands', 'town_bread', 23, 15, 1, 15)
# bg=1 (deli counters!) with clean checkerboard aisles carved out!
mg2.rect(3, 8, 17, 6, 12)  # South deli lobby (switch at 4,11, jr_deli_1 at 16,10, exit at 11,14)
mg2.rect(9, 2, 5, 12, 12)  # Central deli pass to Clara Coldcut (11,3)
mg2.rect(2, 2, 6, 3, 5)    # NW cheese aging shelves
mg2.rect(15, 2, 6, 3, 5)   # NE pickle barrel shelves
mg2.rect(2, 6, 19, 1, 73)  # Locked deli gate

# Gym 3: Bamboo Cloud Kitchen (22x17) - Spilled sesame-oil floor (ice:66) surrounded by bamboo-mat balconies
mg3 = make_interior('gym_bamboo', 'Bamboo Cloud Kitchen', 'Steambay', 'town_steam', 22, 17, 66, 27)
# bg=66 (sesame-oil sliding floor!)
mg3.rect(3, 10, 16, 6, 29) # South safe bamboo mat (jr_steam_1 at 4,11, exit at 11,16)
mg3.rect(9, 2, 4, 14, 29)  # Central bamboo bridge to Master Baozi (11,3)
mg3.rect(2, 2, 6, 4, 25)   # NW steaming hot-water basin
mg3.rect(14, 2, 6, 4, 25)  # NE steaming hot-water basin

# Gym 4: Skillet Tidehouse (23x16) - Coastal cast-iron kitchen built over tidewater (water:25) with bridges & switch gate
mg4 = make_interior('gym_skillet', 'Skillet Tidehouse', 'Steambay', 'town_steam', 23, 16, 25, 27)
# bg=25 (indoor tidepool!)
mg4.rect(4, 9, 15, 6, 43)  # South wooden deck (jr_skillet_1 at 16,10, switch at 17,11, exit at 11,15)
mg4.rect(9, 2, 5, 13, 31)  # Central stone skillet causeway to Sizzle Mei (11,3)
mg4.rect(3, 6, 17, 1, 73)  # Skillet pass gate
mg4.rect(5, 8, 5, 1, 67)   # Conveyor pass

# Gym 5: Pull-Noodle Dojo (21x16) - Tatami training hall with wooden fencing (fence:18), weapon racks, and Dough Boulder
mg5 = make_interior('gym_dojo', 'Pull-Noodle Dojo', 'Noodleridge', 'town_noodle', 21, 16, 18, 39)
# bg=18 (wooden dojo partitions!)
mg5.rect(4, 7, 13, 8, 41)  # South tatami mat (dough_block at 10,8, jr_dojo_1 at 11,10, exit at 10,15)
mg5.rect(8, 2, 5, 13, 41)  # Central dojo lane to Sensei Twirl (11,3)
mg5.rect(2, 2, 5, 4, 42); mg5.rect(14, 2, 5, 4, 42) # Dojo scroll alcoves

# Gym 6: Wok Peak Bistro (24x15) - Terraced Italian-mountain bistro with red-checkered tables (decoration:64) & olive-oil slick
mg6 = make_interior('gym_wokpeak', 'Wok Peak Bistro', 'Noodleridge', 'town_noodle', 24, 15, 64, 39)
# bg=64 (bistro dining tables!)
mg6.rect(5, 9, 14, 5, 36)  # South dining aisle (jr_wok_1 at 11,11, exit at 12,14)
mg6.rect(9, 2, 6, 12, 36)  # Central kitchen aisle to Nonna Fusilli (11,3)
mg6.rect(5, 6, 14, 2, 66)  # Spilled olive-oil slick across kitchen floor (walkable!)

# Gym 7: Cauldron Conservatory (23x17) - Dark greenhouse conservatory filled with glowing broth herbs (tall_grass:47) & cauldrons
mg7 = make_interior('gym_cauldron', 'Cauldron Conservatory', 'Brothbasin', 'town_broth', 23, 17, 47, 51)
# bg=47 (indoor conservatory herb beds!)
mg7.rect(4, 9, 15, 7, 48)  # South stone floor (switch at 5,11, jr_broth_1 at 15,10, exit at 11,16)
mg7.rect(9, 2, 5, 14, 48)  # Central path to Alchemist Bisque (11,3)
mg7.rect(2, 2, 6, 3, 49); mg7.rect(15, 2, 6, 3, 49) # Bubbling stock cauldrons
mg7.rect(2, 6, 19, 1, 73)  # Conservatory gate
MAPS_DATA['gym_cauldron']['dark'] = True

# Gym 8: The Deep Stock Vault (24x17) - Subterranean laser-guarded vault (gate:73) with gold pillars (wall:55) & aged stock racks
mg8 = make_interior('gym_vault', 'The Deep Stock Vault', 'Brothbasin', 'town_broth', 24, 17, 55, 51)
# bg=55 (golden stock-vault pillars!)
mg8.rect(4, 9, 16, 7, 56)  # South vault lobby (jr_vault_1 at 15,10, switch at 17,11, exit at 12,16)
mg8.rect(9, 2, 6, 14, 56)  # Central vault corridor to Lady Bouillon (11,3)
mg8.rect(2, 6, 20, 1, 73)  # Main vault laser gate
mg8.rect(2, 2, 6, 3, 49); mg8.rect(16, 2, 6, 3, 49) # Master stock reservoirs

print("8 Gym interiors initialized.")

# Make sourdough_cavern a bright underground limestone bakery cave (bg=10 ground, with hearth plaza 17 and wheat beds 11)
d1 = MAPS_DATA['sourdough_cavern']['mb']
d1.rect(1, 1, 26, 16, 10)  # Limestone earth floor (ground)
d1.rect(4, 3, 6, 6, 17)    # NW brick oven chamber (plaza)
d1.rect(4, 7, 23, 3, 12)   # Main path tunnel to (27,8)
d1.rect(11, 2, 14, 5, 11)  # NE cave-wheat chamber
d1.rect(3, 11, 10, 5, 18)  # SW wooden cask fence
d1.rect(15, 11, 10, 5, 13) # SE mineral starter pool
d1.set(6, 4, 7)

# Make gym_cauldron use cauldron-stone floor (56) for its central path instead of path (48)
mg7.rect(4, 9, 15, 7, 56)
mg7.rect(9, 2, 5, 14, 56)
mg7.set(5, 11, 9)

# Update gym_cauldron in test_maps.py
mg7.rect(4, 9, 15, 7, 43)
mg7.rect(9, 2, 5, 14, 43)
mg7.set(5, 11, 9)
mg7.set(11, 16, 4)

# ------------------------------------------------------------------------------
# 8. EIGHTEEN TOWN INTERIORS (LAB, CAFE, 8 INNS, 8 MARTS)
# ------------------------------------------------------------------------------
# 1. cruston_lab (17x12): Pantry Lab with library bookshelves (shelf:5) and research counter
mi = make_interior('cruston_lab', 'Pantry Lab', 'Breadlands', 'town_bread', 17, 12, 5, 15)
mi.rect(3, 5, 11, 6, 17)  # Brick lab floor (brotholomew at 9,5, exit at 8,11)
mi.rect(6, 2, 6, 3, 0)    # Specimen alcove
mi.set(8, 11, 4)

# 2. cruston_cafe (18x13): bEATst Cafe & Ranch with indoor herb-grass playpen (tall_grass:11) & stove counter
mi = make_interior('cruston_cafe', 'Cruston bEATst Cafe', 'Breadlands', 'town_bread', 18, 13, 11, 15)
mi.rect(4, 4, 11, 8, 29)  # Cafe seating floor (cafe_host at 6,5, stove_chef at 13,5, exit at 9,12)
mi.rect(5, 2, 9, 2, 1)    # Kitchen stove counter
mi.set(9, 12, 4)

# 3. cruston_inn (18x11): Cozy bakery inn with warm carpet (mat:4) & hearth counter
mi = make_interior('cruston_inn', 'Cruston Simmer Inn', 'Breadlands', 'town_bread', 18, 11, 4, 15)
mi.rect(2, 2, 5, 7, 16); mi.rect(12, 2, 4, 7, 16) # Warm brick sleeping alcoves (roof:16)
mi.rect(6, 4, 7, 6, 41)   # Central reception mat (inn_cruston at 9,4, exit at 9,10)
mi.rect(7, 2, 5, 2, 1)
mi.set(9, 10, 4)

# 4. cruston_mart (19x11): Rustic bread market with wooden picket bins (fence:18) & stone floor
mi = make_interior('cruston_mart', 'Cruston Pantry Mart', 'Breadlands', 'town_bread', 19, 11, 18, 15)
mi.rect(6, 4, 7, 6, 0)    # Central shopping aisle (mart_cruston at 9,5, exit at 9,10)
mi.rect(6, 2, 7, 2, 5)    # North shelf
mi.set(9, 10, 4)

# 5. panini_inn (19x12): Artisan courtyard inn with indoor flowerbeds (decoration:19) & brick plaza
mi = make_interior('panini_inn', 'Panini Simmer Inn', 'Breadlands', 'town_bread', 19, 12, 19, 15)
mi.rect(5, 4, 9, 7, 17)   # Central brick floor (inn_panini at 9,4, exit at 9,11)
mi.rect(6, 2, 7, 2, 1)
mi.set(9, 11, 4)

# 6. panini_mart (20x11): Red-awning market gallery (decoration:64) with stone aisle
mi = make_interior('panini_mart', 'Panini Pantry Mart', 'Breadlands', 'town_bread', 20, 11, 64, 15)
mi.rect(6, 4, 8, 6, 12)   # Central market aisle (mart_panini at 9,5, exit at 10,10)
mi.rect(7, 2, 6, 2, 5)
mi.set(10, 10, 4)

# 7. bao_inn (17x13): Steambay tea-house inn with indoor koi ponds (water:25) & bamboo mat bridge
mi = make_interior('bao_inn', 'Bao Simmer Inn', 'Steambay', 'town_steam', 17, 13, 25, 27)
mi.rect(5, 4, 7, 8, 29)   # Central bamboo mat (inn_bao at 9,4, exit at 8,12)
mi.rect(6, 2, 6, 2, 1)
mi.set(8, 12, 4)

# 8. bao_mart (20x12): Harbor chandlery with bamboo-roof stalls (roof:28) & dock planks
mi = make_interior('bao_mart', 'Bao Pantry Mart', 'Steambay', 'town_steam', 20, 12, 28, 27)
mi.rect(6, 4, 8, 7, 43)   # Central dock aisle (mart_bao at 9,5, exit at 10,11)
mi.rect(7, 2, 6, 2, 5)
mi.set(10, 11, 4)

# 9. pierogi_inn (19x13): Boardwalk lantern inn (decoration:30) with wooden bridge floor
mi = make_interior('pierogi_inn', 'Pierogi Simmer Inn', 'Steambay', 'town_steam', 19, 13, 30, 27)
mi.rect(6, 4, 7, 8, 43)   # Central boardwalk (inn_pierogi at 9,4, exit at 9,12)
mi.rect(6, 2, 7, 2, 1)
mi.set(9, 12, 4)

# 10. pierogi_mart (21x11): Coastal spice bazaar with earthen floor (ground:22) & counter stalls
mi = make_interior('pierogi_mart', 'Pierogi Pantry Mart', 'Steambay', 'town_steam', 21, 11, 22, 27)
mi.rect(7, 4, 7, 6, 31)   # Central stone aisle (mart_pierogi at 9,5, exit at 10,10)
mi.rect(2, 2, 4, 7, 5); mi.rect(15, 2, 4, 7, 5)
mi.set(10, 10, 4)

# 11. udon_inn (17x14): Mountain hot-spring ryokan with rock walls (wall:38) & tatami hall
mi = make_interior('udon_inn', 'Udon Simmer Inn', 'Noodleridge', 'town_noodle', 17, 14, 38, 39)
mi.rect(5, 4, 7, 9, 41)   # Tatami hall (inn_udon at 9,4, exit at 8,13)
mi.rect(2, 2, 3, 5, 37); mi.rect(12, 2, 3, 5, 37) # Indoor hot spring baths
mi.set(8, 13, 4)

# 12. udon_mart (21x12): Noodle supply depot with conveyor delivery chutes (conveyor:68) & stone aisle
mi = make_interior('udon_mart', 'Udon Pantry Mart', 'Noodleridge', 'town_noodle', 21, 12, 68, 39)
mi.rect(6, 4, 8, 7, 36)   # Safe central shopping floor (mart_udon at 9,5, exit at 10,11)
mi.rect(6, 2, 8, 2, 5)
mi.set(10, 11, 4)

# 13. ramen_inn (19x14): Summit ski-lodge inn with dark timber roofs (roof:40) & warm hearth floor
mi = make_interior('ramen_inn', 'Ramen Simmer Inn', 'Noodleridge', 'town_noodle', 19, 14, 40, 39)
mi.rect(6, 4, 7, 9, 44)   # Hearth floor (inn_ramen at 9,4, exit at 9,13)
mi.rect(6, 2, 7, 2, 1)
mi.set(9, 13, 4)

# 14. ramen_mart (20x13): Mountain provisions post with terraced ledges (ledge:65) & rope-bridge aisle
mi = make_interior('ramen_mart', 'Ramen Pantry Mart', 'Noodleridge', 'town_noodle', 20, 13, 65, 39)
mi.rect(6, 4, 8, 8, 43)   # Central bridge aisle (mart_ramen at 9,5, exit at 10,12)
mi.rect(6, 2, 8, 2, 5)
mi.set(10, 12, 4)

# 15. chowder_inn (18x14): Lagoon stilt-house inn with glowing cauldrons (decoration:53) & stone path
mi = make_interior('chowder_inn', 'Chowder Simmer Inn', 'Brothbasin', 'town_broth', 18, 14, 53, 51)
mi.rect(5, 4, 8, 9, 48)   # Central stone path (inn_chowder at 9,4, exit at 9,13)
mi.rect(6, 2, 6, 2, 1)
mi.set(9, 13, 4)

# 16. chowder_mart (21x13): Broth apothecary with simmering stock counters (counter:1) & slate floor
mi = make_interior('chowder_mart', 'Chowder Pantry Mart', 'Brothbasin', 'town_broth', 21, 13, 1, 51)
mi.rect(7, 4, 7, 8, 56)   # Central slate floor (mart_chowder at 9,5, exit at 10,12)
mi.rect(2, 2, 4, 4, 49); mi.rect(15, 2, 4, 4, 49)
mi.set(10, 12, 4)

# 17. bisque_inn (20x14): Bastion royal hostel with marble plaza tiles (plaza:58) & red carpet
mi = make_interior('bisque_inn', 'Bisque Simmer Inn', 'Brothbasin', 'town_broth', 20, 14, 58, 51)
mi.rect(7, 4, 6, 9, 59)   # Red carpet aisle (inn_bisque at 9,4, exit at 10,13)
mi.rect(2, 2, 4, 9, 52); mi.rect(14, 2, 4, 9, 52) # Royal canopy alcoves (roof:52)
mi.set(10, 13, 4)

# 18. bisque_mart (22x12): Fortress quartermaster with earthen cellar bays (ground:46) & stone hall
mi = make_interior('bisque_mart', 'Bisque Pantry Mart', 'Brothbasin', 'town_broth', 22, 12, 46, 51)
mi.rect(7, 4, 8, 7, 0)    # Central stone hall (mart_bisque at 9,5, exit at 11,11)
mi.rect(2, 2, 4, 8, 5); mi.rect(16, 2, 4, 8, 5)
mi.set(11, 11, 4)

print("All 56 maps initialized.")

# Apply the final 7 interior configurations directly inside test_maps.py
m = MAPS_DATA['panini_inn']['mb']
m.rect(1, 1, 17, 5, 4); m.rect(1, 6, 5, 5, 10); m.rect(13, 6, 5, 5, 13); m.rect(5, 4, 9, 7, 12); m.rect(6, 2, 7, 2, 1); m.set(9, 11, 4)
m = MAPS_DATA['panini_mart']['mb']
m.rect(1, 1, 18, 5, 1); m.rect(1, 6, 18, 4, 64); m.rect(6, 4, 8, 6, 0); m.rect(7, 2, 6, 2, 5); m.set(10, 10, 4)
m = MAPS_DATA['bao_inn']['mb']
m.rect(1, 1, 15, 5, 73); m.rect(1, 6, 4, 6, 66); m.rect(12, 6, 4, 6, 5); m.rect(5, 4, 7, 8, 24); m.rect(6, 2, 6, 2, 1); m.set(8, 12, 4)
m = MAPS_DATA['pierogi_inn']['mb']
m.rect(1, 1, 6, 11, 25); m.rect(12, 1, 6, 11, 64); m.rect(6, 4, 7, 8, 43); m.rect(6, 2, 7, 2, 1); m.set(9, 12, 4)
m = MAPS_DATA['ramen_inn']['mb']
m.rect(1, 1, 6, 12, 35); m.rect(12, 1, 6, 12, 37); m.rect(6, 4, 7, 9, 44); m.rect(6, 2, 7, 2, 1); m.set(9, 13, 4)
m = MAPS_DATA['chowder_inn']['mb']
m.rect(1, 1, 16, 5, 50); m.rect(1, 6, 5, 7, 49); m.rect(12, 6, 5, 7, 4); m.rect(5, 4, 8, 9, 48); m.rect(6, 2, 6, 2, 1); m.set(9, 13, 4)
m = MAPS_DATA['bisque_mart']['mb']
m.rect(1, 1, 6, 10, 57); m.rect(15, 1, 6, 10, 58); m.rect(7, 4, 8, 7, 0); m.rect(7, 2, 8, 2, 5); m.set(11, 11, 4)


# Final connectivity & layout refinements
MAPS_DATA['cruston_town']['mb'].rect(18, 17, 13, 3, 12)
MAPS_DATA['cruston_town']['mb'].rect(19, 13, 4, 4, 13)
MAPS_DATA['gym_wokpeak']['mb'].rect(9, 2, 6, 12, 36)
MAPS_DATA['gym_wokpeak']['mb'].rect(4, 6, 5, 2, 66)
MAPS_DATA['gym_wokpeak']['mb'].rect(15, 6, 5, 2, 66)
MAPS_DATA['kettle_gorge']['mb'].rect(3, 4, 8, 5, 47)
MAPS_DATA['kettle_gorge']['mb'].rect(3, 14, 9, 5, 47)
MAPS_DATA['kettle_gorge']['mb'].rect(21, 14, 10, 5, 49)
MAPS_DATA['chowder_crossing']['mb'].rect(25, 14, 6, 4, 47)
MAPS_DATA['wok_volcano']['mb'].rect(6, 10, 10, 5, 35)
MAPS_DATA['chrome_fork_hq']['mb'].rect(20, 10, 6, 6, 47)
MAPS_DATA['truffle_cellar']['mb'].rect(3, 2, 11, 5, 11)
MAPS_DATA['ramen_summit']['mb'].rect(1, 10, 32, 3, 43)
MAPS_DATA['gym_deli']['mb'].set(4, 11, 9)
MAPS_DATA['gym_skillet']['mb'].set(17, 11, 9)
MAPS_DATA['gym_vault']['mb'].set(17, 11, 9)
MAPS_DATA['bao_inn']['mb'].rect(1, 1, 15, 5, 65)
MAPS_DATA['bao_inn']['mb'].rect(5, 4, 7, 8, 24)
MAPS_DATA['slurp_canyon']['mb'].rect(9, 5, 3, 4, 34)
MAPS_DATA['wok_volcano_f2']['mb'].rect(15, 5, 2, 2, 44)
MAPS_DATA['bao_inn']['mb'].rect(6, 2, 6, 2, 1)


def link_maps(a, ax, ay, b, bx, by, path_a, path_b, reqSeals=0, reqFlag=None, reqMsg=None, reqChampion=False, two_way=True):
    ma, mb = MAPS_DATA[a]['mb'], MAPS_DATA[b]['mb']
    if ma.get(ax, ay) not in (2, 6, 7):
        ma.set(ax, ay, path_a)
    if mb.get(bx, by) not in (2, 6, 7):
        mb.set(bx, by, path_b)
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

SPINE = [
  ('cruston_town', 16, 0, 'toastwood_trail', 15, 23, 12, 12, 0),
  ('toastwood_trail', 15, 0, 'deli_meadows', 17, 19, 12, 43, 0),
  ('deli_meadows', 17, 0, 'panini_plaza', 17, 21, 43, 12, 0),
  ('panini_plaza', 17, 0, 'bao_harbor', 17, 21, 12, 24, 2),
  ('bao_harbor', 17, 0, 'bamboo_mist_path', 16, 21, 24, 29, 0),
  ('bamboo_mist_path', 16, 0, 'gyoza_cove', 17, 19, 29, 24, 0),
  ('gyoza_cove', 17, 0, 'pierogi_pier', 16, 21, 24, 31, 0),
  ('pierogi_pier', 16, 0, 'udon_hollow', 16, 21, 31, 36, 4),
  ('udon_hollow', 16, 0, 'slurp_canyon', 17, 21, 36, 43, 0),
  ('slurp_canyon', 17, 0, 'al_dente_ascent', 16, 21, 43, 36, 0),
  ('al_dente_ascent', 16, 0, 'ramen_summit', 16, 21, 36, 43, 0),
  ('ramen_summit', 16, 0, 'chowder_crossing', 16, 20, 43, 43, 6),
  ('chowder_crossing', 16, 0, 'simmer_fen', 17, 22, 43, 48, 0),
  ('simmer_fen', 17, 0, 'kettle_gorge', 16, 21, 48, 48, 0),
  ('kettle_gorge', 16, 0, 'bisque_bastion', 17, 21, 48, 48, 0),
  ('bisque_bastion', 17, 0, 'grand_tasting_hall', 13, 21, 48, 59, 8),
]
for a, ax, ay, b, bx, by, pa, pb, req in SPINE:
    link_maps(a, ax, ay, b, bx, by, pa, pb, reqSeals=req)

link_maps('grand_tasting_hall', 13, 0, 'eternal_pantry', 15, 21, 59, 59, reqChampion=True)

DOORS = [
  ('cruston_town', 7, 6, 'cruston_lab', 9, 11, 12, 17),
  ('cruston_town', 26, 6, 'cruston_inn', 9, 11, 12, 41),
  ('cruston_town', 7, 16, 'cruston_mart', 9, 11, 12, 0),
  ('cruston_town', 26, 16, 'cruston_cafe', 9, 11, 12, 29),
  ('panini_plaza', 7, 6, 'panini_inn', 9, 11, 12, 12),
  ('panini_plaza', 29, 6, 'panini_mart', 9, 11, 12, 0),
  ('panini_plaza', 7, 17, 'gym_toaster', 11, 15, 12, 17),
  ('panini_plaza', 28, 17, 'gym_deli', 11, 15, 12, 12),
  ('bao_harbor', 7, 6, 'bao_inn', 9, 11, 24, 24),
  ('bao_harbor', 29, 6, 'bao_mart', 9, 11, 24, 43),
  ('bao_harbor', 18, 6, 'gym_bamboo', 11, 15, 24, 29),
  ('gyoza_cove', 26, 5, 'gym_skillet', 11, 15, 24, 43),
  ('pierogi_pier', 7, 6, 'pierogi_inn', 9, 11, 31, 43),
  ('pierogi_pier', 27, 6, 'pierogi_mart', 9, 11, 31, 31),
  ('udon_hollow', 7, 6, 'udon_inn', 9, 11, 36, 41),
  ('udon_hollow', 27, 6, 'udon_mart', 9, 11, 36, 36),
  ('udon_hollow', 17, 6, 'gym_dojo', 11, 15, 36, 41),
  ('al_dente_ascent', 25, 6, 'gym_wokpeak', 11, 15, 36, 36),
  ('ramen_summit', 7, 6, 'ramen_inn', 9, 11, 36, 44),
  ('ramen_summit', 27, 6, 'ramen_mart', 9, 11, 36, 43),
  ('chowder_crossing', 7, 6, 'chowder_inn', 9, 11, 48, 48),
  ('chowder_crossing', 27, 6, 'chowder_mart', 9, 11, 48, 56),
  ('chowder_crossing', 17, 6, 'gym_cauldron', 11, 15, 48, 43),
  ('bisque_bastion', 7, 6, 'bisque_inn', 9, 11, 48, 59),
  ('bisque_bastion', 29, 6, 'bisque_mart', 9, 11, 48, 0),
  ('bisque_bastion', 28, 17, 'gym_vault', 11, 15, 48, 56),
]
for a, ax, ay, b, bx, by, pa, pb in DOORS:
    mb_dest = MAPS_DATA[b]['mb']
    link_maps(a, ax, ay, b, mb_dest.w // 2, mb_dest.h - 1, pa, pb)

DUNGEON_LINKS = [
  ('panini_plaza', 0, 11, 'sourdough_cavern', 27, 8, 12, 12),
  ('sourdough_cavern', 6, 4, 'sourdough_cavern_b2', 6, 4, 17, 20),
  ('pierogi_pier', 0, 11, 'steamer_spire', 27, 8, 24, 24),
  ('steamer_spire', 6, 4, 'steamer_spire_f2', 6, 4, 32, 43),
  ('ramen_summit', 0, 11, 'wok_volcano', 28, 8, 36, 36),
  ('wok_volcano', 6, 4, 'wok_volcano_f2', 6, 4, 44, 44),
  ('bisque_bastion', 0, 11, 'broth_catacombs', 27, 8, 48, 48),
  ('broth_catacombs', 6, 4, 'broth_catacombs_b2', 6, 4, 56, 56),
  ('bisque_bastion', 35, 11, 'chrome_fork_hq', 0, 8, 48, 71),
  ('chrome_fork_hq', 22, 4, 'chrome_fork_hq_f2', 20, 4, 71, 71),
  ('deli_meadows', 35, 9, 'truffle_cellar', 0, 8, 12, 12),
  ('truffle_cellar', 18, 4, 'truffle_cellar_b2', 18, 4, 20, 20),
]
for a, ax, ay, b, bx, by, pa, pb in DUNGEON_LINKS:
    link_maps(a, ax, ay, b, bx, by, pa, pb)

# Restore visible stairs tiles on dungeon floors after link_maps apron carving
MAPS_DATA['sourdough_cavern']['mb'].set(6, 4, 7)
MAPS_DATA['sourdough_cavern_b2']['mb'].set(6, 4, 6)
MAPS_DATA['steamer_spire']['mb'].set(6, 4, 6)
MAPS_DATA['steamer_spire_f2']['mb'].set(6, 4, 7)
MAPS_DATA['wok_volcano']['mb'].set(6, 4, 6)
MAPS_DATA['wok_volcano_f2']['mb'].set(6, 4, 7)
MAPS_DATA['broth_catacombs']['mb'].set(6, 4, 7)
MAPS_DATA['broth_catacombs_b2']['mb'].set(6, 4, 6)
MAPS_DATA['chrome_fork_hq']['mb'].set(22, 4, 6)
MAPS_DATA['chrome_fork_hq_f2']['mb'].set(20, 4, 7)
MAPS_DATA['truffle_cellar']['mb'].set(18, 4, 7)
MAPS_DATA['truffle_cellar_b2']['mb'].set(18, 4, 6)
MAPS_DATA['broth_catacombs']['mb'].rect(7, 3, 5, 2, 48)
MAPS_DATA['wok_volcano_f2']['mb'].rect(8, 3, 12, 3, 35)
MAPS_DATA['wok_volcano_f2']['mb'].rect(16, 6, 4, 7, 44)

# ==============================================================================
# 8. QUESTS (16), SECRETS (12), SYNDICATE, RIVAL (6), NAMED NPCS & 800+ WRITTEN LINES
# ==============================================================================
QUESTS = [
  {'id':'q1_butter', 'name':'Cultured Butter Hunt', 'steps':1, 'reward':'3x Ceramic Plate', 'map':'cruston_town'},
  {'id':'q2_lid', 'name':'Lost Bamboo Lid', 'steps':1, 'reward':'2x Bento Lacquer Set + 300G', 'map':'bao_harbor'},
  {'id':'q3_chopsticks', 'name':'Golden Chopsticks', 'steps':1, 'reward':'500G', 'map':'slurp_canyon'},
  {'id':'q4_truffle', 'name':'Midnight Truffle Broth', 'steps':1, 'reward':'Royal Banquet Setting', 'map':'chowder_crossing'},
  {'id':'q5_starter', 'name':'The Ancient Starter (Multi)', 'steps':2, 'reward':'Recipe: Aged Cheddar + 400G', 'map':'panini_plaza'},
  {'id':'q6_ginger', 'name':'Ginger Trade Route (Multi)', 'steps':2, 'reward':'2x Hearty Stew + 350G', 'map':'bao_harbor'},
  {'id':'q7_chili', 'name':'Five-Alarm Delivery (Multi)', 'steps':2, 'reward':'Recipe: Sriracha Beam + 500G', 'map':'udon_hollow'},
  {'id':'q8_ladle', 'name':'Copper Ladle Mystery (Multi)', 'steps':2, 'reward':'Grand Feast + 600G', 'map':'chowder_crossing'},
  {'id':'q9_critics', 'name':'Tour of Four Palates (Multi)', 'steps':3, 'reward':'Royal Banquet Setting', 'map':'cruston_town'},
  {'id':'q10_crumb', 'name':'Panko Trail', 'steps':1, 'reward':'2x Warm Broth Cup', 'map':'panini_plaza'},
  {'id':'q11_scallion', 'name':'Scallion Harvest', 'steps':1, 'reward':'Chef Garnish Treat x3', 'map':'pierogi_pier'},
  {'id':'q12_salt', 'name':'Sea Salt Crystals', 'steps':1, 'reward':'Wooden Board x2', 'map':'bao_harbor'},
  {'id':'q13_stock', 'name':'Perpetual Simmer', 'steps':1, 'reward':'Recipe: Boil Over', 'map':'chowder_crossing'},
  {'id':'q14_steam', 'name':'Mist Lanterns', 'steps':1, 'reward':'Peppermint Tea x3', 'map':'pierogi_pier'},
  {'id':'q15_wok', 'name':'Wok Hei Spark', 'steps':1, 'reward':'Double Espresso x2', 'map':'ramen_summit'},
  {'id':'q16_banquet', 'name':'Eternal Banquet Prep (Multi)', 'steps':2, 'reward':'2000G + Grand Feast x2', 'map':'grand_tasting_hall'}
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
  ('cruston_town', {'id':'critic_brie','x':20,'y':8,'name':'Food Critic Brie','sprite':'critic_brie','dir':'left','questGive':'q9_critics','lines':['I am judging the Tour of Four Palates! Visit Critics Camembert in Bao Harbor, Vermicelli in Udon Hollow, and Bisquetta in Chowder Crossing!']}),

  # Toastwood & Deli
  ('toastwood_trail', {'id':'butter_item','x':6,'y':14,'name':'Cultured Butter','sprite':'item_chest','dir':'down','questComplete':'q1_butter','notStartedLines':['A tub of Cultured Butter stamped with Baker Barnaby\'s seal in Cruston Town. Better ask him first!'],'lines':['Found Baker Barnaby\'s Cultured Butter! Received 3x Ceramic Plate!']}),
  ('toastwood_trail', {'id':'saffron_1','x':15,'y':14,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_1','lines':['Hmph! My plating angles are 100 percent geometric!']}),
  ('toastwood_trail', {'id':'syn_vesper','x':15,'y':6,'name':'Auditor Vesper','sprite':'officer_vesper','dir':'down','trainer':'officer_vesper','lines':['Good afternoon! Chrome Fork Syndicate is auditing this trail for unauthorized flavor!']}),
  ('deli_meadows', {'id':'crumb_item','x':24,'y':14,'name':'Panko Bag','sprite':'item_chest','dir':'down','questComplete':'q10_crumb','notStartedLines':['A sack of golden panko crumbs labeled for Baker Panko Pete in Panini Plaza.'],'lines':['Found the lost Panko Bag for Panko Pete! Received 2x Warm Broth Cup!']}),

  # Panini Plaza + Interiors + Gyms 1 & 2
  ('panini_inn', {'id':'inn_panini','x':9,'y':4,'name':'Innkeeper Marlo','sprite':'inn','dir':'down','action':'heal','lines':['Panini Plaza Simmer Inn! Rest up before the Head Chefs!']}),
  ('panini_mart', {'id':'mart_panini','x':9,'y':5,'name':'Clerk Bramble','sprite':'mart','dir':'down','action':'shop','lines':['Panini Plaza Mart! Stock up on Broth Cups and Garnish Treats!']}),
  ('panini_plaza', {'id':'crumb_giver','x':11,'y':8,'name':'Panko Pete','sprite':'villager_4','dir':'down','questGive':'q10_crumb','lines':['I dropped my prized Panko Bag down in Deli Meadows! Could you track it down for me?']}),
  ('panini_plaza', {'id':'yeast_monk','x':10,'y':12,'name':'Yeast Monk','sprite':'yeast_monk','dir':'right','questGive':'q5_starter','lines':['Please speak with Starter Keeper Orin on Sourdough Cavern 1F, then check the Ancient Starter Jar on B2!']}),
  ('gym_toaster', {'id':'jr_toast_1','x':6,'y':12,'name':'Sous-Chef Toasty','sprite':'villager_0','dir':'down','trainer':'jr_bread_1','lines':['Order up! Clear the conveyor line first!']}),
  ('gym_toaster', {'id':'greg_npc','x':11,'y':3,'name':'Head Chef Griddle Greg','sprite':'chef_greg','dir':'down','trainer':'chef_greg','lines':['Welcome to The Toaster Hearth! Ready for 400 degrees of golden crunch?']}),
  ('gym_deli', {'id':'jr_deli_1','x':16,'y':10,'name':'Sous-Chef Slicer','sprite':'villager_1','dir':'left','trainer':'jr_bread_2','lines':['Hit the floor switch to unlock the deli counter!']}),
  ('gym_deli', {'id':'clara_npc','x':11,'y':3,'name':'Head Chef Clara Coldcut','sprite':'chef_clara','dir':'down','trainer':'chef_clara','lines':['At Deli Counter Spire, every layer matters!']}),

  ('sourdough_cavern', {'id':'starter_scout','x':14,'y':6,'name':'Starter Keeper Orin','sprite':'villager_9','dir':'down','questStep':'q5_starter','stepIndex':1,'notReadyLines':['Starter Keeper Orin: Have you spoken with the Yeast Monk in Panini Plaza yet?'],'lines':['Starter Keeper Orin: The Yeast Monk sent you! Take this cellar key-note and inspect the Ancient Starter Jar down on B2!']}),
  ('sourdough_cavern_b2', {'id':'starter_jar','x':12,'y':8,'name':'Ancient Starter Jar','sprite':'item_chest','dir':'down','questComplete':'q5_starter','notStartedLines':['An ancient sourdough crock. You should speak with the Yeast Monk in Panini Plaza before touching it!'],'notReadyLines':['You haven\'t checked in with Starter Keeper Orin on Sourdough Cavern 1F yet!'],'lines':['The 100-year starter bubbles happily! Learned Recipe: Aged Cheddar + 400G!']}),
  ('sourdough_cavern_b2', {'id':'yeast_block','x':10,'y':8,'name':'Sourdough Cask','sprite':'push_block','dir':'down','pushable':True,'lines':['A heavy oak sourdough cask.']}),
  ('truffle_cellar_b2', {'id':'truffle_guardian','x':11,'y':5,'name':'Cellar Hermit Truff','sprite':'villager_9','dir':'down','trainer':'truffle_guard','lines':['These cellar mushrooms sing to anyone who listens!']}),

  # Steambay + Gyms 3 & 4
  ('bao_inn', {'id':'inn_bao','x':9,'y':4,'name':'Innkeeper Mei-Ling','sprite':'inn','dir':'down','action':'heal','lines':['Bao Harbor Simmer Inn! Bamboo mist restores all HP and PP!']}),
  ('bao_mart', {'id':'mart_bao','x':9,'y':5,'name':'Clerk Buns','sprite':'mart','dir':'down','action':'shop','lines':['Steambay Pantry Mart! Ceramic Plates and Hearty Stews now in stock!']}),
  ('bao_harbor', {'id':'apprentice_lin','x':20,'y':13,'name':'Apprentice Lin','sprite':'apprentice_lin','dir':'left','questGive':'q2_lid','lines':['Master Baozi\'s lucky Bamboo Lid blew north into Gyoza Cove! Please retrieve it!']}),
  ('bao_harbor', {'id':'salt_giver','x':24,'y':13,'name':'Brine Master Sal','sprite':'villager_5','dir':'down','questGive':'q12_salt','lines':['I need flaky Sea Salt Crystals from the rocks in Gyoza Cove to cure my dumplings!']}),
  ('bao_harbor', {'id':'ginger_lin','x':8,'y':10,'name':'Dockmaster Fen','sprite':'villager_6','dir':'down','questGive':'q6_ginger','lines':['Tea Master Po in Pierogi Pier ordered fresh ginger! Pick it up from Ginger Merchant Kai on Bamboo Mist Path first!']}),
  ('bao_harbor', {'id':'critic_camembert','x':12,'y':13,'name':'Critic Camembert','sprite':'villager_11','dir':'right','questStep':'q9_critics','stepIndex':1,'notReadyLines':['Critic Camembert: You haven\'t registered for the Tour with Critic Brie in Cruston Town yet!'],'lines':['Steambay pleats are sublime! Next stop: Critic Vermicelli in Udon Hollow!']}),
  ('gym_bamboo', {'id':'jr_steam_1','x':4,'y':11,'name':'Sous-Chef Vapor','sprite':'villager_2','dir':'right','trainer':'jr_steam_1','lines':['Watch your step on the sesame-oil floor!']}),
  ('gym_bamboo', {'id':'baozi_npc','x':11,'y':3,'name':'Head Chef Master Baozi','sprite':'chef_baozi','dir':'down','trainer':'chef_baozi','lines':['Breathe in the mist of Bamboo Cloud Kitchen!']}),

  ('bamboo_mist_path', {'id':'ginger_kai','x':10,'y':10,'name':'Ginger Merchant Kai','sprite':'ginger_kai','dir':'down','questStep':'q6_ginger','stepIndex':1,'notReadyLines':['Ginger Merchant Kai: Did Dockmaster Fen in Bao Harbor send you for the ginger order? Ask him first!'],'lines':['Take this fresh ginger root along the coast to Tea Master Po in Pierogi Pier!']}),
  ('bamboo_mist_path', {'id':'syn_crumb','x':16,'y':8,'name':'Director Crumb','sprite':'officer_crumb','dir':'down','trainer':'officer_crumb','lines':['Hello valued customer! Chrome Fork is replacing all bamboo steamers with Beige Kiosks!']}),

  ('gyoza_cove', {'id':'lid_item','x':10,'y':4,'name':'Lucky Bamboo Lid','sprite':'item_chest','dir':'down','questComplete':'q2_lid','notStartedLines':['A cedar steamer lid with Apprentice Lin\'s initials. Speak to Apprentice Lin in Bao Harbor first!'],'lines':['Found the Lucky Bamboo Lid! Received 2x Bento Lacquer Set + 300G!']}),
  ('gyoza_cove', {'id':'salt_item','x':24,'y':14,'name':'Sea Salt Crystal','sprite':'item_chest','dir':'down','questComplete':'q12_salt','notStartedLines':['Sparkling sea salt crystals. Brine Master Sal in Bao Harbor might need these!'],'lines':['Gathered pure Sea Salt Crystals! Received 2x Wooden Board!']}),
  ('gyoza_cove', {'id':'saffron_2','x':17,'y':13,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_2','lines':['I bought a Ceramic Plate just to flex on you!']}),
  ('gym_skillet', {'id':'jr_skillet_1','x':16,'y':10,'name':'Sous-Chef Sizzle','sprite':'villager_4','dir':'left','trainer':'jr_steam_2','lines':['Flip the switch to open the skillet pass!']}),
  ('gym_skillet', {'id':'mei_npc','x':11,'y':3,'name':'Head Chef Sizzle Mei','sprite':'chef_mei','dir':'down','trainer':'chef_mei','lines':['At Skillet Tidehouse we sear first and ask questions later!']}),

  ('pierogi_inn', {'id':'inn_pierogi','x':9,'y':4,'name':'Innkeeper Zosia','sprite':'inn','dir':'down','action':'heal','lines':['Pierogi Pier Simmer Inn! Rest by the harbor!']}),
  ('pierogi_mart', {'id':'mart_pierogi','x':9,'y':5,'name':'Clerk Pierog','sprite':'mart','dir':'down','action':'shop','lines':['Pierogi Pier Mart! Ceramic Plates ready for your party!']}),
  ('pierogi_pier', {'id':'tea_master_po','x':10,'y':9,'name':'Tea Master Po','sprite':'tea_master_po','dir':'down','questComplete':'q6_ginger','notStartedLines':['Tea Master Po: I am waiting on a ginger shipment arranged by Dockmaster Fen in Bao Harbor!'],'notReadyLines':['Tea Master Po: You haven\'t picked up the ginger root from Ginger Merchant Kai on Bamboo Mist Path yet!'],'lines':['Oh, fresh ginger from Bamboo Mist Path! Received 2x Hearty Stew + 350G!']}),
  ('pierogi_pier', {'id':'scallion_giver','x':12,'y':8,'name':'Pier Chef Marek','sprite':'villager_7','dir':'down','questGive':'q11_scallion','lines':['Could you check on Scallion Farmer Sue on the east side of Pierogi Pier and bring me her harvest report?']}),
  ('pierogi_pier', {'id':'scallion_sue','x':22,'y':12,'name':'Scallion Farmer Sue','sprite':'scallion_sue','dir':'left','questComplete':'q11_scallion','notStartedLines':['Scallion Farmer Sue: Pier Chef Marek on the west boardwalk usually sends for my scallion report first!'],'lines':['Thanks for checking our scallions for Chef Marek! Take 3x Chef Garnish Treat!']}),
  ('pierogi_pier', {'id':'steam_giver','x':20,'y':8,'name':'Lantern Keeper Jian','sprite':'villager_2','dir':'down','questGive':'q14_steam','lines':['The Mist Lantern on the top floor of Steamer Spire went out! Please climb the spire and relight it!']}),
  ('steamer_spire_f2', {'id':'spire_lantern','x':12,'y':4,'name':'Mist Lantern','sprite':'item_chest','dir':'down','questComplete':'q14_steam','notStartedLines':['An unlit brass mist lantern. Lantern Keeper Jian in Pierogi Pier tends to this!'],'lines':['Lit the Mist Lantern! Received 3x Peppermint Tea!']}),

  # Noodleridge + Gyms 5 & 6
  ('udon_inn', {'id':'inn_udon','x':9,'y':4,'name':'Innkeeper Kazu','sprite':'inn','dir':'down','action':'heal','lines':['Udon Hollow Simmer Inn! Rest your noodles!']}),
  ('udon_mart', {'id':'mart_udon','x':9,'y':5,'name':'Clerk Slurp','sprite':'mart','dir':'down','action':'shop','lines':['Noodleridge Pantry Mart! Bento Lacquer Sets and Double Espresso unlocked!']}),
  ('udon_hollow', {'id':'chili_giver','x':11,'y':10,'name':'Spice Miller Ren','sprite':'villager_8','dir':'down','questGive':'q7_chili','lines':['Please take this Five-Alarm Chili order to Pepper Watcher Tori on Al Dente Ascent, then deliver it to Chili Courier Rico at Ramen Summit!']}),
  ('udon_hollow', {'id':'critic_vermicelli','x':21,'y':13,'name':'Critic Vermicelli','sprite':'villager_3','dir':'left','questStep':'q9_critics','stepIndex':2,'notReadyLines':['Critic Vermicelli: You haven\'t visited Critic Camembert in Bao Harbor yet!'],'lines':['Al dente perfection! Now visit Critic Bisquetta in Chowder Crossing!']}),
  ('gym_dojo', {'id':'dough_block','x':10,'y':8,'name':'Dough Boulder','sprite':'push_block','dir':'down','pushable':True,'lines':['A springy ball of hand-pulled dough.']}),
  ('gym_dojo', {'id':'jr_dojo_1','x':11,'y':10,'name':'Sous-Chef Stretch','sprite':'villager_7','dir':'down','trainer':'jr_noodle_1','lines':['Stretch your posture before facing Sensei Twirl!']}),
  ('gym_dojo', {'id':'twirl_npc','x':11,'y':3,'name':'Head Chef Sensei Twirl','sprite':'chef_twirl','dir':'down','trainer':'chef_twirl','lines':['Hand-pulled dough stretches ten feet without snapping!']}),

  ('slurp_canyon', {'id':'chopsticks_giver','x':15,'y':10,'name':'Noodle Poet Basho','sprite':'villager_3','dir':'down','questGive':'q3_chopsticks','lines':['I dropped my Golden Chopsticks near the north canyon ledge! Can you fetch them for me?']}),
  ('slurp_canyon', {'id':'chopsticks_item','x':10,'y':6,'name':'Golden Chopsticks','sprite':'item_chest','dir':'down','questComplete':'q3_chopsticks','notStartedLines':['A pair of gleaming Golden Chopsticks. Noodle Poet Basho on the canyon bridge is looking for these!'],'lines':['Found the Golden Chopsticks for Poet Basho! Received 500G!']}),
  ('slurp_canyon', {'id':'syn_glaze','x':17,'y':13,'name':'VP Synergy Glaze','sprite':'officer_glaze','dir':'down','trainer':'officer_glaze','lines':['Surprise inspection! Your noodle bounce is 3 percent off corporate spec!']}),
  ('al_dente_ascent', {'id':'chili_step','x':14,'y':10,'name':'Pepper Watcher Tori','sprite':'villager_6','dir':'down','questStep':'q7_chili','stepIndex':1,'notReadyLines':['Pepper Watcher Tori: Did Spice Miller Ren in Udon Hollow send a chili batch yet? Speak to him first!'],'lines':['Pepper Watcher Tori: Whew, that five-alarm batch is still piping hot! Hurry it up to Chili Courier Rico at Ramen Summit!']}),
  ('al_dente_ascent', {'id':'saffron_3','x':16,'y':13,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_3','lines':['I timed my boiling water to the millisecond!']}),
  ('gym_wokpeak', {'id':'jr_wok_1','x':11,'y':11,'name':'Sous-Chef Simmer','sprite':'villager_6','dir':'down','trainer':'jr_noodle_2','lines':['Keep your balance on the olive-oil tiles!']}),
  ('gym_wokpeak', {'id':'fusilli_npc','x':11,'y':3,'name':'Head Chef Nonna Fusilli','sprite':'chef_fusilli','dir':'down','trainer':'chef_fusilli','lines':['Nonna Fusilli never measures basil with a spoon!']}),

  ('ramen_inn', {'id':'inn_ramen','x':9,'y':4,'name':'Innkeeper Taro','sprite':'inn','dir':'down','action':'heal','lines':['Ramen Summit Simmer Inn! Warm broth for mountain climbers!']}),
  ('ramen_mart', {'id':'mart_ramen','x':9,'y':5,'name':'Clerk Chili','sprite':'mart','dir':'down','action':'shop','lines':['Ramen Summit Mart! Bento Sets and Spicy Recipe Cards!']}),
  ('ramen_summit', {'id':'chili_rico','x':12,'y':13,'name':'Chili Courier Rico','sprite':'chili_rico','dir':'down','questComplete':'q7_chili','notStartedLines':['Chili Courier Rico: I am waiting on a chili dispatch from Spice Miller Ren in Udon Hollow!'],'notReadyLines':['Chili Courier Rico: Did Pepper Watcher Tori on Al Dente Ascent sign off on the heat check yet?'],'lines':['Five-alarm chili delivered to the summit! Received Recipe: Sriracha Beam + 500G!']}),
  ('ramen_summit', {'id':'wok_giver','x':21,'y':9,'name':'Blacksmith Tetsu','sprite':'villager_7','dir':'down','questGive':'q15_wok','lines':['My forge needs a Wok Hei Spark from the crater of Wok Volcano to the west!']}),
  ('wok_volcano_f2', {'id':'wok_ember','x':12,'y':4,'name':'Wok Hei Ember','sprite':'item_chest','dir':'down','questComplete':'q15_wok','notStartedLines':['A crackling Wok Hei Ember. Blacksmith Tetsu at Ramen Summit knows how to handle this safely!'],'lines':['Captured a Wok Hei Spark! Received 2x Double Espresso!']}),

  # Brothbasin + Gyms 7 & 8 + Syndicate HQ
  ('chowder_inn', {'id':'inn_chowder','x':9,'y':4,'name':'Innkeeper Pearl','sprite':'inn','dir':'down','action':'heal','lines':['Brothbasin Simmer Inn! Ladle up some rest!']}),
  ('chowder_mart', {'id':'mart_chowder','x':9,'y':5,'name':'Clerk Ladle','sprite':'mart','dir':'down','action':'shop','lines':['Brothbasin Pantry Mart! Royal Banquet Settings and Grand Feasts now in stock!']}),
  ('chowder_crossing', {'id':'ladle_giver','x':6,'y':10,'name':'Tureen Crafter Bea','sprite':'villager_10','dir':'down','questGive':'q8_ladle','lines':['My heirloom Copper Ladle vanished into Simmer Fen! Ask Fen Ranger Moss in Simmer Fen if he saw where it sank!']}),
  ('chowder_crossing', {'id':'truffle_giver','x':11,'y':10,'name':'Mycologist Morel','sprite':'villager_9','dir':'down','questGive':'q4_truffle','lines':['A Rare Night Truffle sprouted inside Bisque Bastion\'s courtyard! Could you harvest it for my stock?']}),
  ('chowder_crossing', {'id':'stock_giver','x':24,'y':10,'name':'Boiler Engineer Hal','sprite':'villager_5','dir':'down','questGive':'q13_stock','lines':['The Perpetual Valve in Kettle Gorge is rattling! Please hike north and tune it!']}),
  ('chowder_crossing', {'id':'critic_bisquetta','x':21,'y':13,'name':'Critic Bisquetta','sprite':'villager_10','dir':'left','questComplete':'q9_critics','notStartedLines':['Critic Bisquetta: You haven\'t started the Tour of Four Palates with Critic Brie in Cruston Town yet!'],'notReadyLines':['Critic Bisquetta: You haven\'t visited both Critic Camembert and Critic Vermicelli yet!'],'lines':['Four Palates complete! Take this Royal Banquet Setting!']}),
  ('gym_cauldron', {'id':'jr_broth_1','x':15,'y':10,'name':'Sous-Chef Roux','sprite':'villager_8','dir':'left','trainer':'jr_broth_1','lines':['Light your lantern and find the cauldron switch!']}),
  ('gym_cauldron', {'id':'bisque_npc','x':11,'y':3,'name':'Head Chef Alchemist Bisque','sprite':'chef_bisque','dir':'down','trainer':'chef_bisque','lines':['Low and slow, bubble and glow! Welcome to Cauldron Conservatory!']}),

  ('simmer_fen', {'id':'ladle_step','x':22,'y':6,'name':'Fen Ranger Moss','sprite':'villager_4','dir':'down','questStep':'q8_ladle','stepIndex':1,'notReadyLines':['Fen Ranger Moss: Did Tureen Crafter Bea in Chowder Crossing send you looking for something?'],'lines':['Fen Ranger Moss: Aha! I saw a shiny Copper Ladle glinting on the west bank of Simmer Fen!']}),
  ('simmer_fen', {'id':'ladle_item','x':10,'y':6,'name':'Copper Ladle','sprite':'item_chest','dir':'down','questComplete':'q8_ladle','notStartedLines':['A tarnished ladle half-buried in peat. Tureen Crafter Bea in Chowder Crossing might own this!'],'notReadyLines':['You haven\'t asked Fen Ranger Moss on the east side of Simmer Fen how to pry it loose safely!'],'lines':['Found the Copper Ladle! Received Grand Feast + 600G!']}),
  ('simmer_fen', {'id':'saffron_4','x':17,'y':13,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_4','lines':['My team evolved! Let us test our new heat!']}),
  ('kettle_gorge', {'id':'stock_valve','x':20,'y':6,'name':'Perpetual Valve','sprite':'item_chest','dir':'down','questComplete':'q13_stock','notStartedLines':['A high-pressure steam valve. Boiler Engineer Hal in Chowder Crossing has the calibration specs!'],'lines':['Tuned the Perpetual Simmer! Received Recipe: Boil Over!']}),
  ('kettle_gorge', {'id':'syn_grunt_gorge','x':16,'y':12,'name':'Syndicate Grunt','sprite':'syndicate_grunt','dir':'down','trainer':'syndicate_grunt_1','lines':['Thank you for your patience! Your recipe is very important to us!']}),

  ('bisque_inn', {'id':'inn_bisque','x':9,'y':4,'name':'Innkeeper Coral','sprite':'inn','dir':'down','action':'heal','lines':['Bisque Bastion Simmer Inn! Final rest before the Grand Hall!']}),
  ('bisque_mart', {'id':'mart_bisque','x':9,'y':5,'name':'Clerk Stock','sprite':'mart','dir':'down','action':'shop','lines':['Bisque Bastion Mart! Royal Banquet Settings and Grand Feasts ready!']}),
  ('bisque_bastion', {'id':'truffle_item','x':10,'y':8,'name':'Rare Night Truffle','sprite':'item_chest','dir':'down','questComplete':'q4_truffle','notStartedLines':['A fragrant dark truffle growing by the bastion wall. Mycologist Morel in Chowder Crossing is studying these!'],'lines':['Found Rare Night Truffle! Received Royal Banquet Setting!']}),
  ('bisque_bastion', {'id':'banquet_step','x':13,'y':10,'name':'Cellar Sommelier Vane','sprite':'villager_11','dir':'down','questStep':'q16_banquet','stepIndex':1,'notReadyLines':['Cellar Sommelier Vane: Have you spoken with Sommelier Colette in the Grand Tasting Hall yet?'],'lines':['Cellar Sommelier Vane: Here is the vintage Sparkling Stock list for Banquet Steward Otto in the Eternal Pantry!']}),
  ('gym_vault', {'id':'jr_vault_1','x':15,'y':10,'name':'Sous-Chef Consomme','sprite':'villager_5','dir':'left','trainer':'jr_broth_2','lines':['Only clarified stock passes the vault gate!']}),
  ('gym_vault', {'id':'bouillon_npc','x':11,'y':3,'name':'Head Chef Lady Bouillon','sprite':'chef_bouillon','dir':'down','trainer':'chef_bouillon','lines':['Eight Seals complete! The Grand Tasting Hall awaits you!']}),

  # Chrome Fork Syndicate HQ (1F & 2F Climax!)
  ('chrome_fork_hq', {'id':'syn_grunt_hq','x':14,'y':7,'name':'Laminated Agent','sprite':'syndicate_grunt','dir':'left','trainer':'syndicate_grunt_2','lines':['Please take a numbered ticket before foiling our corporate espionage!']}),
  ('chrome_fork_hq_f2', {'id':'saffron_5','x':8,'y':11,'name':'Rival Saffron','sprite':'saffron','dir':'right','trainer':'rival_5','lines':['I am backing you up against Chrome Fork! Let us warm up first!']}),
  ('chrome_fork_hq_f2', {'id':'boss_ladle_npc','x':12,'y':3,'name':'CEO Sterling Ladle','sprite':'boss_ladle','dir':'down','trainer':'boss_ladle','lines':['Welcome to Beige Plate HQ! Soon every kitchen will serve identical nutrient cubes!']}),

  # Grand Tasting Hall & Eternal Pantry
  ('grand_tasting_hall', {'id':'inn_hall','x':9,'y':16,'name':'Banquet Prep Chef','sprite':'inn','dir':'down','action':'heal','lines':['Final tune-up before the Grand Gauntlet! Full HP and PP restored!']}),
  ('grand_tasting_hall', {'id':'banquet_giver','x':16,'y':16,'name':'Sommelier Colette','sprite':'villager_1','dir':'down','questGive':'q16_banquet','lines':['We are preparing the Eternal Banquet! Collect the vintage list from Sommelier Vane in Bisque Bastion, then report to Steward Otto in Eternal Pantry!']}),
  ('grand_tasting_hall', {'id':'saffron_6','x':13,'y':13,'name':'Rival Saffron','sprite':'saffron','dir':'down','trainer':'rival_6','lines':['Show me everything we learned across Pantrylia!']}),
  ('grand_tasting_hall', {'id':'pip_npc','x':13,'y':11,'name':'Master Taster Pip','sprite':'taster_pip','dir':'down','trainer':'taster_pip','lines':['Course One: Appetizer! Wake up your palate!']}),
  ('grand_tasting_hall', {'id':'roux_npc','x':13,'y':9,'name':'Master Taster Roux','sprite':'taster_roux','dir':'down','trainer':'taster_roux','lines':['Course Two: Main! Rich gravy and fearless umami!']}),
  ('grand_tasting_hall', {'id':'mochi_npc','x':13,'y':7,'name':'Master Taster Mochi','sprite':'taster_mochi','dir':'down','trainer':'taster_mochi','lines':['Course Three: Palate Cleanser! Cool and sweet!']}),
  ('grand_tasting_hall', {'id':'aurelia_npc','x':13,'y':4,'name':'Champion Chef Aurelia','sprite':'champion','dir':'down','trainer':'champion_aurelia','lines':['Welcome to the Grand Tasting Table! Show me the bond between cook and bEATst!']}),
  ('grand_tasting_hall', {'id':'secret_151_door','x':11,'y':2,'name':'Secret Pantry Door','sprite':'item_chest','dir':'down','action':'secret151','lines':['A shimmering golden pantry door...']}),

  ('eternal_pantry', {'id':'inn_eternal','x':12,'y':12,'name':'Starlight Chef','sprite':'inn','dir':'down','action':'heal','lines':['Welcome to the Eternal Pantry! All bEATsts restored!']}),
  ('eternal_pantry', {'id':'mart_eternal','x':19,'y':12,'name':'Eternal Boutique','sprite':'mart','dir':'down','action':'shop','lines':['Eternal Pantry Boutique! Everything unlocked!']}),
  ('eternal_pantry', {'id':'steward_otto','x':15,'y':8,'name':'Banquet Steward Otto','sprite':'steward_otto','dir':'down','questComplete':'q16_banquet','notStartedLines':['Banquet Steward Otto: Speak with Sommelier Colette in the Grand Tasting Hall to begin the Eternal Banquet preparations!'],'notReadyLines':['Banquet Steward Otto: Have you picked up the vintage list from Sommelier Vane in Bisque Bastion yet?'],'lines':['Thank you for delivering the vintage list to the Eternal Pantry! Received 2000G + 2x Grand Feast!']}),
  ('eternal_pantry', {'id':'reformed_ladle','x':20,'y':15,'name':'Sterling Ladle','sprite':'boss_ladle','dir':'left','lines':['I closed Beige Plate Corp and opened a neighborhood soup cart! Turns out real broth beats synergy!']})
]

for mid, npc in NAMED_NPCS:
    MAPS_DATA[mid]['npcs'].append(npc)

# Secret pickups (11 + #151 = 12)
SECRET_SPOTS = [
  ('cruston_town', 'sec_crust_stash', 28, 19, 'Found Hidden Brioche Stash (+100G)!'),
  ('toastwood_trail', 'sec_toast_cache', 2, 20, 'Found Toasted Crumb Cache (1x Wooden Board)!'),
  ('sourdough_cavern_b2', 'sec_sourdough_jar', 19, 10, 'Found 100-Year Starter Vial (1x Garnish Treat)!'),
  ('bao_harbor', 'sec_bao_pearl', 28, 18, 'Found Harbor Oyster Pearl (+150G)!'),
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
# 9. ASSIGN INDIVIDUALLY WRITTEN, NON-TEMPLATED DIALOGUE LINES TO VILLAGERS
# ==============================================================================
FIRST_NAMES = [
  'Clara','Milo','Nora','Gus','Toby','June','Felix','Wren','Otto','Iris','Bram','Tess','Hugo','Vera','Jude','Lena',
  'Arlo','Cora','Otis','Mina','Saul','Ruby','Ezra','Cleo','Theo','Faye','Leon','Rosa','Ivan','Maya','Nils','Gwen',
  'Rory','Alma','Kipp','Zara','Boyd','Talia','Sven','Lola','Dante','Nadia','Paco','Yuki','Hana','Kenji','Sora','Mei'
]
ROLES = ['Chef','Baker','Taster','Botanist','Angler','Poet','Courier','Mason','Herbalist','Brewer']

VILLAGER_LINES_BANK = [
  "Always tap the bottom of a country loaf before slicing; if it sounds like a hollow snare drum, the crumb is ready.",
  "My sourdough starter is older than the town clocktower and twice as temperamental on humid Tuesdays.",
  "Never refrigerate a ripe tomato unless you actively enjoy the texture of wet cardboard on your BLT.",
  "When you spread cold salted butter on hot toast, the little pools that form in the air pockets are pure magic.",
  "I tried making brioche with half the butter once, and my grandmother looked at me like I had insulted our ancestors.",
  "A proper Reuben requires sauerkraut squeezed dry in a clean kitchen towel so the rye never goes soggy.",
  "You can tell an amateur panini press operator by whether the provolone melts out the sides before the crust browns.",
  "We score our baguettes at a thirty-degree angle with a razor blade so the oven spring opens like wheat ears.",
  "Focaccia dimpling is the most therapeutic five minutes in baking, especially when the rosemary needles stick to your knuckles.",
  "I keep a cast-iron Dutch oven preheated just to trap steam during the first ten minutes of my bake.",
  "If your cinnamon roll dough doesn't feel like a warm earlobe when you pinch it, knead it another three minutes.",
  "Some people cut sandwiches into rectangles, which is their right, even if triangles objectively taste twenty percent better.",
  "The secret to a club sandwich that doesn't slide apart on the first bite is alternating lettuce and cheese as friction layers.",
  "I dropped a whole wheel of aged gruyere down the cellar stairs last winter and honestly the bruising improved the nutty finish.",
  "Rye caraway seeds get stuck in my teeth every single morning and I still refuse to switch to white toast.",
  "A croissant with fewer than twenty-seven distinct butter layers is just a crescent-shaped dinner roll pretending to be French.",
  "We brush our pretzel dough with a baking soda bath before salting so the crust turns deep mahogany.",
  "Nothing humbles a proud baker faster than forgetting the salt in a twelve-loaf batch of ciabatta.",
  "When the bakery vents open at five in the morning, half the wild bEATsts on the trail wander up to the fence.",
  "Toastwood trees drop acorns that smell faintly of nutmeg when roasted over an open campfire.",
  "Watch out for the one-way ledges along the trail unless you enjoy taking the scenic detour back through the wheat.",
  "A wild Baguettebit tried to joust with my walking stick yesterday and left toasted crumbs all over my boots.",
  "I pack wax paper instead of plastic wrap for trail sandwiches so the crust stays crisp until noon.",
  "If you hear a sharp crackle in the tall grass, that's probably a Crustling practicing its Hearth Toast.",
  "My picnic basket has a dedicated compartment for Dijon mustard because squeeze packets lack dignity.",
  "Auditor Vesper offered me a coupon for a synthetic nutrition bar, and I nearly chased him into the creek with a rolling pin.",
  "Rival Saffron marched past here muttering about forty-five-degree crusts and carrying a brass protractor.",
  "Deli Meadows smells like sweet clover in the morning and smoked pastrami whenever the wind blows from the north.",
  "The meadow cows graze on wild oregano, which explains why the local mozzarella barely needs seasoning.",
  "I saw a Falafelfin sunbathing on a flat rock by the creek, soaking up the afternoon heat.",
  "Never underestimate a crisp pickle spear; it resets your palate between bites of sharp cheddar.",
  "Our picnic tables are built from reclaimed oak barrels that used to hold apple cider vinegar.",
  "If you head east toward the cellar, bring a lantern and watch your footing on the damp flagstones.",
  "A good muffuletta needs to sit wrapped under a heavy skillet for an hour so the olive salad marries into the bread.",
  "I once judged a grilled cheese contest where a contestant used four cheeses and still lost to aged cheddar on sourdough.",
  "Panini Plaza's twin kitchens compete so fiercely you can see toaster sparks flying across the rooftops at dusk.",
  "Head Chef Griddle Greg flipped a pancake so high in 2019 that people still check the rafters for it.",
  "Head Chef Clara Coldcut can slice prosciutto thin enough to read the morning newspaper through it.",
  "The cobblestones in the plaza stay warm well past midnight from the brick ovens underneath the street.",
  "I come to the market stalls just for the pickled red onions; they turn bright magenta in lime juice.",
  "Conveyor belts in a kitchen sound excessive until you try serving two hundred toasted subs during the lunch rush.",
  "The floor switch in the spire was installed after a rogue wheel of gouda rolled out the front door.",
  "Sourdough Cavern stays at a steady fifty-eight degrees year-round, which makes the wild yeast cultures practically immortal.",
  "You can hear the ancient starter jars bubbling in the dark before your lantern light even reaches them.",
  "The stalactites in the lower cavern drip mineral water that gives our hearth loaves their chewy crust.",
  "Don't push the oak sourdough casks into a corner unless you remember how to walk around them.",
  "Truffle Cellar smells like damp autumn leaves, roasted garlic, and old oak shelving.",
  "Cellar Hermit Truff trained his bEATsts to sniff out black truffles buried six inches under the clay.",
  "Even the moss down in the cellar has an earthy umami note if you simmer it in cultured butter.",
  "I keep my wooden charcuterie boards oiled with walnut oil so they never crack in dry winter air.",
  "Mayonnaise is just an emulsion of egg yolk, lemon juice, and oil held together by sheer confidence and a fast whisk.",
  "If you toast only the inside faces of a burger bun, the outside stays pillowy while the inside blocks gravy sog.",
  "Banh mi baguettes use a blend of rice flour and wheat flour so the crust shatters into a million thin flakes.",
  "Pickled daikon and carrot julienne should still have a snap when you bite through the cilantro stems.",
  "A Cuban sandwich isn't authentic unless you press it flat with a heated brick wrapped in foil.",
  "Roast pork, ham, Swiss, pickles, and yellow mustard--add lettuce or tomato to a Cubano and my uncle will lecture you for an hour.",
  "Pumpernickel gets its deep color from slow-baking for sixteen hours in a sealed tin with molasses and cocoa.",
  "When grating cold butter into biscuit flour, stop while the pieces still look likeflattened peas.",
  "Never twist a biscuit cutter when punching out dough; twisting seals the edges and stops the layers from rising.",
  "Clotted cream on a warm currant scone goes on before the strawberry jam, and I will defend that order forever.",
  "Actually, putting jam on the scone first lets you spread an even layer before piling the cream high like snowdrifts.",
  "Everything bagel seasoning gets into the cuffs of my sweater, my pockets, and somehow my boots.",
  "Real bagels have to be poached in barley-malt water before they ever see the deck oven.",
  "Cream cheese should be whipped with minced chives and cracked black pepper until it holds soft peaks.",
  "Caprese sandwiches live or die by the flaky sea salt you scatter on the tomatoes five minutes before assembly.",
  "Balsamic reduction shouldn't be sweet syrup; just two drops of aged Modena vinegar is enough.",
  "Po-boy loaves from the bayou have a crisp shell and an interior so light it practically floats.",
  "Fried oysters on dressed French bread need hot sauce, shredded iceberg, and plenty of napkins.",
  "Monte Cristo sandwiches dipped in egg batter and pan-fried walk a glorious tightrope between lunch and French toast.",
  "A dusting of powdered sugar and a side of tart raspberry preserves somehow makes melted ham and Swiss sing.",
  "Peanut butter on both slices of bread acts as a waterproof barrier so the grape jelly never leaks through your backpack.",
  "Crunchy peanut butter gives a sandwich structural grit, though smooth peanut butter spreads without tearing soft crumb.",
  "Grilled halloumi squeaks against your teeth in the most delightful way when paired with roasted red peppers.",
  "Whipped ricotta with lemon zest and honey turns a humble slice of toasted peasant bread into a banquet.",
  "Garlic bread requires roasting the whole bulb in foil until the cloves squeeze out like golden paste.",
  "Parsley and oregano chopped fresh on the board smell ten times brighter than anything from a dusty tin.",
  "Pita pockets puff up in a hot oven because steam gets trapped between the top and bottom dough layers.",
  "Tahini sauce seizes up into a stiff paste the moment you add lemon juice, until cold water loosens it into velvet.",
  "Chickpea falafel mixture must use dried soaked garbanzos, never canned, or the patties fall apart in the oil.",
  "Chipotle mayo on a turkey club adds just enough smoky heat to wake up the avocado.",
  "Smashed avocado needs lime juice and coriander seed right away or it turns the color of an old pond.",
  "Brioche burger buns brushed with egg wash shine like lacquered mahogany under the heat lamps.",
  "Caramelized shallots take half the time of yellow onions and bring twice the sweetness to a steak sandwich.",
  "Horseradish cream on roast beef should clear your sinuses all the way to the top of your hat.",
  "Au jus for French dip sandwiches is best when simmered with charred beef marrow bones and a splash of dry sherry.",
  "Tortas telera rolls have two signature dents on top so the baker can tell which batch rose first.",
  "Refried black beans spread on the bottom roll keep pickled jalapenos from sliding out of a torta.",
  "Katsu sando milk bread is baked in a lidded Pullman loaf pan so every slice is a perfect square.",
  "Tonkatsu sauce is simmered from apples, dates, tomatoes, and spices until it coats a fried pork cutlet like glaze.",
  "Egg salad needs a spoonful of pickle brine and a pinch of smoked paprika to keep it from tasting sleepy.",
  "Watercress tea sandwiches with the crusts trimmed off look polite, but they pack a peppery bite.",
  "Pimento cheese is the mortar that holds southern picnics together when the humidity hits ninety percent.",
  "Sharp cheddar grated by hand melts ten times smoother than pre-shredded cheese coated in potato starch.",
  "Provolone piccante aged in ropes hanging from the rafters develops a peppery crystal crunch.",
  "Gouda wheels coated in yellow wax can survive a cross-country wagon trip and still slice like butter.",
  "Blue cheese crumbles on a pear-and-walnut flatbread convert even the most stubborn skeptics.",
  "Flatbread blistered on an upside-down cast-iron skillet takes ninety seconds and beats any store-bought wrap.",
  "Lardons rendered slowly in a cold pan give you both crispy bacon bits and liquid gold for toasting croutons.",
  "Croutons tossed with olive oil and thyme should be baked at three-fifty until they clatter like dice.",
  "Panzanella salad proves that day-old bread soaked in tomato juices and olive oil is better than fresh loaf.",
  "Bao Harbor's morning fog is seventy percent ocean breeze and thirty percent cedar steamer exhaust.",
  "Folding eighteen pleats into a soup dumpling takes three weeks to learn and thirty years to master.",
  "If you bite straight into a fresh xiaolongbao without nibbling a vent hole first, the broth will teach you patience.",
  "The secret to getting liquid soup inside a raw dumpling is chilling rich aspic jelly and dicing it into the filling.",
  "The harbor pilings are seasoned with sea salt and decades of spilled soy dipping sauce.",
  "Master Baozi meditates atop stacks of bamboo steamers while his dough rises to double its volume.",
  "You can tell which dock a fisherman works by whether his lunchbox holds char siu bao or shrimp har gao.",
  "Crystal shrimp dumpling wrappers use wheat starch and boiling water so they turn translucent in the steamer.",
  "We line our bamboo baskets with perforated cabbage leaves instead of paper whenever the harvest is good.",
  "A sesame ball should puff up hollow in the fryer and ring crisp when you tap it with bamboo chopsticks.",
  "Spilled sesame oil on polished kitchen tiles is faster than ice skates and smells ten times better.",
  "Bamboo Mist Path winds through stalks so tall that noon sunlight filters down like green tea.",
  "When rain hits the hot steamer vents along the path, the whole bamboo grove turns into a fragrant sauna.",
  "Ginger Merchant Kai grates fresh rhizomes with a porcelain plate so none of the fibrous pith gets into the tea.",
  "Director Crumb tried to put a laminated QR code menu on a three-hundred-year-old bamboo shrine.",
  "Wild Mochimite bounce down the stone steps in pairs whenever someone drops sweet red bean paste.",
  "If you listen closely in the bamboo grove, the wind whistling through the hollow culms sounds like a tea kettle.",
  "Gyoza Cove gets its crescent shape from the basalt cliffs that shelter the tidepools from northern swells.",
  "The secret to lacy skirted potstickers is a splash of flour-and-water slurry right before you clamp the lid down.",
  "Head Chef Sizzle Mei seasons her cast-iron skillets with flaxseed oil until they shine like black mirrors.",
  "Wait for the water to evaporate completely and listen for the sharp sizzle before you lift a pan of gyoza.",
  "Sea salt harvested from the cove's flat rocks has flaky pyramid crystals that crunch between your fingers.",
  "I watched Rival Saffron time her dumpling sear with a pocket watch and still burn the garlic chives.",
  "In Pierogi Pier, we pinch our potato-and-cheddar dumplings with a braided rope edge so they never burst in the boil.",
  "Caramelized onions for pierogi topping should be cooked low and slow for forty minutes until they turn jammy.",
  "A dollop of cold sour cream next to a skillet of butter-fried vareniki is non-negotiable on this pier.",
  "Scallion Farmer Sue trims only the green tops at dawn so the white bulbs keep growing in the sandy soil.",
  "Tea Master Po brews aged pu-erh dark enough to see your reflection in the porcelain cup.",
  "Steamer Spire rises so high into the coastal clouds that the top floor stays warm from the rising kitchen drafts below.",
  "Each tier of the spire is vented through brass grates that whistle in harmony when the sea breeze picks up.",
  "The ancient dim sum masters carved folding diagrams directly into the cedar pillars on the second floor.",
  "Black vinegar with a sliver of young ginger cuts through rich pork filling better than any sauce ever bottled.",
  "Never stack more than five bamboo tiers over a single wok unless you rotate the top and bottom baskets halfway through.",
  "Tamale husks soaked in warm water all afternoon make the whole harbor boardwalk smell like roasted corn.",
  "Beating lard until a tiny piece floats in cold water is the old-school test for fluffy tamale masa.",
  "Empanada dough needs a splash of vinegar in the ice water to keep the pastry tender when baked.",
  "Hard-boiled egg slices and green olives tucked inside a beef empanada are a pleasant surprise in every bite.",
  "Samosa corners should be sharp enough to point north on a nautical chart.",
  "Whole cumin and coriander seeds toasted before mixing into spiced potatoes make samosas smell like heaven.",
  "When arancini come out of the oil, let them rest two minutes or the molten mozzarella inside will ambush your tongue.",
  "Day-old saffron risotto rolls into the best arancini because the starch has already set firm in the fridge.",
  "Takoyaki batters need dashi stock so the center stays custardy while the outside turns crisp in the half-sphere mold.",
  "Turning takoyaki spheres with two bamboo picks requires a flick of the wrist before the batter sets.",
  "Bonito flakes scattered on hot takoyaki wave and dance in the rising steam like tiny paper sails.",
  "Onigiri rice must be salted on your wet palms, never mixed into the pot, or the grains lose their gloss.",
  "Wrapping crisp nori around an onigiri right before eating keeps the seaweed from turning chewy.",
  "Pickled umeboshi plum inside a rice ball wakes you up faster than two cups of espresso.",
  "Khinkali topknots are meant to be held like a handle and left on the plate so everyone can count how many you ate.",
  "Cracking fresh black pepper over the first sip of khinkali juice is practically a law in the eastern mountains.",
  "Gnocchi dough should be handled as little as possible; overwork the potato and you're boiling rubber erasers.",
  "Baking russet potatoes in a bed of rock salt draws out excess moisture so your gnocchi need barely any flour.",
  "Rolling gnocchi down the tines of a dinner fork creates little ridges that hold onto sage brown butter.",
  "Shumai tops stay open like little flower baskets, always crowned with a single green pea or crab roe.",
  "Minced shiitake stems give pork shumai a woodsy chew that balances the tender shrimp.",
  "Char siu bao dough uses both yeast and baking powder so the bun splits open into a snowy three-petal laugh.",
  "Sweet roast pork glaze needs maltose and five-spice powder reduced until it coats the back of a spoon.",
  "Lotus leaf sticky rice packets infuse the glutinous grains with an herbal tea aroma as they steam.",
  "Dried shrimp, Chinese sausage, and salted egg yolk tucked inside lotus rice could power a sailor through a gale.",
  "Mochi pounded with a wooden mallet in a stone mortar has a stretch that machine-mixed rice flour never matches.",
  "Dusting warm mochi with roasted soybean kinako powder and a drizzle of dark brown sugar syrup is pure comfort.",
  "Mugwort yomogi leaves pounded into green mochi dough give it a fresh spring-meadow scent.",
  "Matzo balls can be sinkers or floaters depending on whether you separate the eggs and add a pinch of seltzer.",
  "Fresh dill fronds floating in golden chicken broth around a fluffy matzo ball cure almost any bad mood.",
  "Kreplach folded into triangles and pan-fried in schmaltz get crispy corners that everyone at the table fights over.",
  "Pelmeni made by the hundred and frozen on wooden boards outdoors are how northern sailors survive January.",
  "Dipping hot pelmeni in cold smetana with a splash of vinegar and cracked pepper is simple perfection.",
  "Manti dumplings from the spice routes are tiny enough to fit four on a soup spoon, topped with garlic yogurt and sumac.",
  "Sumac berries ground into crimson powder bring a lemony tang without watering down your yogurt sauce.",
  "Modak sweet dumplings pleated like garlic bulbs and filled with coconut and jaggery smell of toasted cardamom.",
  "Steaming modak on turmeric leaves imparts a subtle warm perfume you cannot get from parchment.",
  "Coxinha dough is made by stirring flour into boiling chicken broth before shaping it like drumsticks around shredded hen.",
  "Catupiry soft cheese inside a fried coxinha stretches into strings when you pull the crust apart.",
  "Burek phyllo dough is spun through the air until you can see the harbor lighthouse through the sheet.",
  "Coiling meat-filled phyllo into a spiral snail and baking it in a round pan guarantees every slice has crispy edges.",
  "Pastel dough uses a shot of cane spirit so the wrapper blisters into tiny airy bubbles when fried.",
  "Knish dough wrapped around mashed potato and caramelized buckwheat kasha is heavy enough to anchor a rowboat.",
  "Mustard on a hot potato knish is a street-cart tradition I refuse to question.",
  "Tangyuan glutinous rice balls filled with black sesame paste burst like warm ink in sweet ginger soup.",
  "Rock sugar simmered with smashed old ginger makes the clearest, most soothing winter dessert broth.",
  "Momo wrappers rolled thinner at the edges than the center prevent a thick doughy knot at the top.",
  "Roasted tomato and Timur pepper chutney gives steamed momos a numbing citrus kick.",
  "Mandu stuffed with chopped kimchi, firm tofu, and glass noodles have the best texture contrast in the bay.",
  "Squeezing excess brine out of chopped kimchi in cheesecloth keeps mandu wrappers from splitting on the tray.",
  "Tortellini are shaped around the tip of your pinky finger, modeled after a sleeping cat curled by the hearth.",
  "Serving tortellini in capon broth lets the delicate nutmeg in the filling shine without heavy cream.",
  "Agnolotti del plin are pinched between thumb and forefinger to trap a single drop of roast jus inside each pocket.",
  "Culurgiones from the islands are pleated with a wheat-ear stitch that seals in potato, pecorino, and fresh mint.",
  "Mint and aged sheep cheese in a pasta filling sounds unusual until you taste it with simple tomato sauce.",
  "Pierogi ruskie use farmer's quark cheese mashed into potatoes, which gives them a tangy richness cheddar can't replicate.",
  "Sour cherry vareniki dusted with sugar and served cold in summer stain your fingers the happiest shade of purple.",
  "Steamed scallion flower rolls twisted and brushed with toasted sesame oil pull apart intotwenty soft petals.",
  "Making dumpling wrappers with boiling water denatures the gluten so you can roll them paper-thin without springback.",
  "Cold-water dumpling dough has more chew and holds up to vigorous boiling in a crowded pot.",
  "Always dust your wooden dumpling tray with cornstarch or semolina; plain flour turns into glue under damp dough.",
  "A bamboo steamer lid absorbs condensation instead of dripping water back onto your delicate buns.",
  "When the harbor bell rings twelve times at noon, every steamer lid in Bao Harbor lifts in unison.",
  "Seagulls around Pierogi Pier ignore fish scraps completely and hold out for buttered onion bits.",
  "I keep a jar of homemade chili crisp with fried garlic and fermented black beans on my belt at all times.",
  "Gyoza dipping sauce only needs soy, rice vinegar, and a drop of rayu chili oil--anything else is showing off.",
  "Watching a school of Har-gaohawk glide over the cove waves at sunset is why I moved to Steambay.",
  "In Udon Hollow, we knead thick wheat dough by wrapping it in clean linen and stepping on it to the rhythm of taiko drums.",
  "Freshly cut udon noodles have slightly concave sides that catch the dashi broth when you slurp.",
  "Slurping noodles isn't bad manners here; it aerates the broth and cools the strands so you don't burn your lip.",
  "Sensei Twirl can stretch a single lump of dough into a thousand strands fine enough to thread a sewing needle.",
  "Buckwheat soba dough has no gluten network, so you have to roll and fold it fast before the edges dry out.",
  "Cold zaru soba served on a bamboo mat with scallions and freshly grated wasabi is the only cure for a hot afternoon.",
  "Save the cloudy soba-yu cooking water to pour into your leftover dipping cup at the end of the meal.",
  "Slurp Canyon echoes every noodle shop's ladle clangs across the gorge like church bells.",
  "The rope bridges across Slurp Canyon sway whenever a heavy Yakisobayak trots across the planks.",
  "VP Synergy Glaze brought a pair of scissors to the canyon to cut long longevity noodles, and the locals nearly fainted.",
  "Pad Thai tamarind paste should balance sour, sweet, and salty before a single crushed peanut touches the wok.",
  "Dried shrimp and preserved radish chopped fine are the secret backbone of street-style Pad Thai.",
  "Never put oil in your pasta boiling water; all it does is coat the noodles so the marinara slides right off.",
  "Save a mug of starchy pasta water before you drain the colander--that liquid gold binds cheese and pepper into silk.",
  "Carbonara uses guanciale, pecorino, black pepper, and eggs tempered off the heat; cream is contraband on this mountain.",
  "Cacio e pepe is three ingredients and a test of whether you understand starch emulsion and pan temperature.",
  "Toast whole Tellicherry peppercorns in a dry skillet before crushing them with a heavy saucepan for cacio e pepe.",
  "Al Dente Ascent is steep enough that water boils two degrees cooler at the top than at the bottom.",
  "Nonna Fusilli shapes cavatelli against a ridged wooden board with her thumb faster than a machine.",
  "When bronze-die extruded pasta dries slowly, its rough chalky surface grabs ragu like Velcro.",
  "Lasagna sheets layered with bechamel and slow-simmered bolognese need twenty minutes to settle before you cut a square.",
  "Spinach kneaded into fresh egg pasta sheets turns lasagna verde into a stained-glass window of flavor.",
  "Pesto genovese belongs in a marble mortar with pine nuts and garlic; steel blender blades heat and oxidize the sweet basil.",
  "Blanching basil leaves fortwo seconds and icing them keeps pesto emerald green for days.",
  "Ramen Summit stays warm even in blizzard season thanks to the giant tonkotsu kettles bubbling in every shop.",
  "Alkaline kansui water is what gives ramen noodles their yellow hue and springy bite in hot broth.",
  "A soft-boiled ajitsuke tamago needs exactly six minutes and thirty seconds before plunging into an ice bath.",
  "Tap the rounded bottom of an egg gently with a spoon to pierce the air pocket so it peels cleanly after boiling.",
  "Chashu pork belly rolled in butcher's twine and braised in soy, mirin, and charred scallion melts on contact.",
  "Chili Courier Rico runs up the mountain switchbacks carrying ceramic jars of fermented chili crisp strapped to his pack.",
  "Wok Volcano's caldera radiates enough dry heat that cast-iron woks season themselves just sitting on the rim.",
  "True wok hei happens when microscopic oil droplets vaporize in the flame as you toss rice noodles through the air.",
  "If your stir-fry vegetables steam instead of sear, your pan is overcrowded and your burner is too timid.",
  "Dan dan noodles need Sichuan peppercorns toasted and ground fresh so the citrusy tingle hits right behind the heat.",
  "preserved ya cai mustard greens give dan dan noodles a savory depth you cannot fake with salt alone.",
  "Beef chow fun requires wide flat rice noodles separated gently by hand so they don't tear in the soy glaze.",
  "Bean sprouts and yellow chives go into the wok for only the last ten seconds so they stay crisp.",
  "Pho broth gets its clarity and perfume from charring whole onions and ginger directly over open coals before simmering.",
  "Star anise, cinnamon stick, cloves, and black cardamom pods should be toasted dry before tying into a spice bag.",
  "Laksa coconut curry broth stains every wooden spoon in the kitchen a cheerful turmeric gold.",
  "Fried tofu puffs in laksa act like little sponges that burst with spicy coconut broth when you bite them.",
  "Jajangmyeon black bean paste must be fried in pork fat with diced onions until the bitterness turns into rich caramel.",
  "Julienne cucumber on top of hot black bean noodles gives you a cool crunch in every mouthful.",
  "Japchae sweet potato glass noodles are stir-fried with sesame oil and each vegetable is cooked separately by color.",
  "Cold sesame noodles dressed with tahini, black vinegar, and grated cucumber are the best trail lunch on the ridge.",
  "Pappardelle ribbons cut an inch wide are built for wild boar or mushroom ragu, not timid butter sauces.",
  "Bucatini looks like thick spaghetti until you notice the pinhole down the center that whistles when you slurp.",
  "Orecchiette--little ears--are shaped by dragging a butter knife across a dime of semolina dough and inverting it on your thumb.",
  "Charred broccoli rabe and garlic oil cling to the cup of an orecchiette like they were made for each other.",
  "Spaetzle batter scraped through a perforated colander into simmering water cooks in the time it takes to float.",
  "Pan-frying boiled spaetzle in brown butter with gruyere and crispy onions is how mountain climbers refuel.",
  "Sweet noodle kugel baked with cottage cheese, sour cream, raisins, and cinnamon crust smells like a holiday.",
  "Savory potato or noodle kugel baked in a cast-iron skillet gets lacy caramelized edges that crunch like chips.",
  "Fideua swaps paella rice for short toasted vermicelli noodles cooked flat in an iron pan with cuttlefish and saffron.",
  "Toasting dry short noodles in olive oil before adding fish stock gives fideua a nutty aroma and keeps the strands separate.",
  "Pancit bihon rice sticks soak up calamansi lime juice and soy broth without ever feeling heavy.",
  "Squeezing fresh calamansi over hot pancit right at the table wakes up the whole dish.",
  "Beef stroganoff over buttered egg noodles needs sour cream stirred in off the heat so it never curdles.",
  "Searing cremini mushrooms without touching them for four minutes gives stroganoff a deep steakhouse crust.",
  "Macaroni and cheese starts with a Mornay sauce spiked with dry mustard powder and a pinch of cayenne.",
  "Cavatappi corkscrews hold twice as much cheddar sauce as smooth elbows because of their ridges and hollow spiral.",
  "Topping baked mac and cheese with panko tossed in melted butter guarantees a golden crunch in every corner.",
  "Yakisoba sauce balances Worcestershire, oyster sauce, ketchup, and dark soy into a smoky griddle glaze.",
  "Pickled red ginger--beni shoga--on the side of yakisoba cuts right through the rich pork belly.",
  "Hand-pulled biangbiang noodles are wide as a belt and slapped against the wooden counter until they sing.",
  "Pouring smoking-hot rapeseed oil over raw minced garlic, chili flakes, and scallions on top of wide noodles is pure theater.",
  "Somen noodles are stretched on two rods and aged through a winter freeze so they cook in ninety seconds flat.",
  "Catching cold somen noodles with chopsticks as they slide down a split bamboo water flume is a summer sport.",
  "Hiyashi chuka chilled ramen arranged with ribbons of egg crepe, cucumber, ham, and mustard-vinegar tare is art on a plate.",
  "Penne rigate have diagonal cut ends that scoop up arrabbiata chili sauce like fountain pen nibs.",
  "Amatriciana sauce needs cured pork cheek, Pecorino Romano, San Marzano tomatoes, and a whisper of white wine.",
  "Never break dry spaghetti in half before dropping it in the pot; give it thirty seconds and swirl it down whole.",
  "Salt your pasta water until it tastes like a gentle summer wave in Steambay.",
  "Tagliatelle dimensions are officially registered in a gold-plated model at the chamber of commerce: eight millimeters flat.",
  "Tortelloni are the bigger cousins of tortellini, stuffed with ricotta and parsley and dressed in sage butter.",
  "Trofie twists from the coast look like wood shavings and trap basil pesto in their tight spirals.",
  "Boiling potatoes and green beans in the same pot as trofie pasta starches the water and cooks the whole dinner at once.",
  "Lo mein tosses boiled egg noodles in dark soy and sesame oil at the end; chow mein fries them crisp against the wok.",
  "Velveting sliced beef in egg white, cornstarch, and Shaoxing wine keeps it tender even over volcano heat.",
  "Rice vermicelli only needs a ten-minute soak in warm water before stir-frying; boiling turns it into mush.",
  "Singapore mei fun gets its sunny yellow color and fragrance from Madras curry powder toasted in the wok oil.",
  "Khao soi tops soft egg noodles in coconut curry broth with a nest of crispy fried noodles and pickled mustard greens.",
  "Lime wedges, shallots, and roasted chili oil let every diner tune their khao soi bowl to their own palate.",
  "Ramen tare--whether shio, shoyu, or miso--sits in the bottom of the bowl before the ladle of unsalted stock goes in.",
  "Aromatic oil--like black scorched garlic mayu or scallion chicken schmaltz--floats on top of ramen to lock in heat.",
  "Menma fermented bamboo shoots add a snappy crunch next to melt-in-your-mouth chashu.",
  "Nori sheets tucked at the rim of a ramen bowl should be wrapped around a mouthful of noodles before they go limp.",
  "Tonkotsu broth boils pork femurs at a rolling rumble for fourteen hours until marrow and collagen emulsify into milk.",
  "Clear shoyu ramen stock simmers gently below a boil with dried kelp, niboshi sardines, and chicken frames.",
  "Dashi made from Rishiri kombu and shaved katsuobushi takes ten minutes and forms the soul of Udon Hollow.",
  "Pulling the kombu leaf out just before the water simmers prevents any bitter sliminess in your dashi.",
  "Kitsune udon tops thick noodles with sweet soy-simmered aburaage fried tofu pouches.",
  "Tempura udon is best when the crispy shrimp tail stays above the broth line until you're ready to bite.",
  "Curry udon thickens dashi with Japanese curry roux and potato starch--wear a dark apron when you slurp it.",
  "Nabeyaki udon arrives bubbling in an individual clay pot with a raw egg poaching gently in the center.",
  "Zoodle spiralized zucchini is a fine vegetable side, but calling it pasta in Noodleridge will get you escorted to the border.",
  "Semolina flour from durum wheat has the golden carotenoid pigments and stiff gluten needed for extruded shapes.",
  "Tipo 00 soft wheat flour makes the silkest egg tagliatelle when kneaded with deep-orange farm yolks.",
  "Letting fresh pasta dough rest wrapped for thirty minutes relaxes the gluten so the rolling pin doesn't fight you.",
  "Hanging fresh fettuccine on a wooden dowel rack makes any kitchen look like a workshop of happiness.",
  "Chowder Crossing is built on cedar stilts over warm mineral springs that smell faintly of bay leaf and celery seed.",
  "New England clam chowder should be thickened with crushed oyster crackers or salt pork roux, never cornstarch.",
  "Manhattan clam chowder uses tomatoes and thyme instead of cream, which still sparks polite debates at the inn.",
  "Alchemist Bisque roasts lobster shells with tomato paste and brandy before simmering them into velvet stock.",
  "Traditionally, bisque was thickened by pounding cooked rice and toasted crustacean shells together in a mortar.",
  "To clarify a cloudy consomme, whisk egg whites and minced mirepoix into cold stock and let the raft rise undisturbed.",
  "Poke a small breathing hole in the center of the egg-white raft so the consomme bubbles gently through the filter.",
  "If you let a consomme boil hard after the raft forms, the proteins emulsify and cloud the whole pot.",
  "Miso paste must be stirred in after you turn off the flame; boiling kills the delicate fermented aroma.",
  "Red aka miso aged for two winters stands up to hearty root vegetables, while sweet white shiro miso loves spring tofu.",
  "Gazpacho tastes best when the cucumbers, tomatoes, and bell peppers marinate overnight with sherry vinegar and stale bread.",
  "Emulsifying extra-virgin olive oil into gazpacho at the very end turns it from cold vegetable juice into coral velvet.",
  "Salmorejo is gazpacho's thicker Andalusian cousin, crowned with diced jamon serrano and grated hard-boiled egg.",
  "Simmer Fen's peat bogs bubble with geothermal warmth, keeping the wild watercress green all winter.",
  "French onion soup takes four pounds of yellow onions cooked down to two cups of dark amber jam before the beef stock goes in.",
  "Deglazing the onion pot three times with water or dry white wine lifts the browned fond without scorching.",
  "A Gruyere crouton broiled atop an earthenware crock of onion soup forms a seal that traps the thyme steam underneath.",
  "Borscht gets its ruby glow from grated beets simmered with a splash of vinegar to lock in the color.",
  "Stirring a spoonful of cold sour cream and fresh chopped dill into hot borscht turns the broth neon pink.",
  "Gumbo starts with a dark chocolate-colored roux stirred non-stop for forty-five minutes without burning a single speck.",
  "The Holy Trinity of Cajun cooking--onion, celery, and green bell pepper--hits the hot roux to stop it from darkening further.",
  "File powder ground from dried sassafras leaves thickens gumbo right in the bowl; never boil file or it turns stringy.",
  "Okra sliced into rings and browned in a skillet loses its mucilage while keeping its earthy flavor for seafood gumbo.",
  "Kettle Gorge's basalt walls funnel the steam from hot springs into towering white plumes visible from three miles away.",
  "The Perpetual Simmer pot in the gorge has been kept on a low bubble by rotating shifts of soup tenders for eighty years.",
  "Vichyssoise is proof that leeks, potatoes, and cream are just as noble chilled in crystal bowls as they are hot.",
  "Always wash sliced leeks in a bowl of cold water and lift them out so the sandy grit sinks to the bottom.",
  "Avgolemono soup relies on tempering hot chicken broth into whisked egg and lemon juice one ladle at a time.",
  "Bisque Bastion's stone ramparts were mortared during the Great Soup Truce and smell wonderfully of rosemary.",
  "Lady Bouillon guards the Deep Stock Vault, where vintage reductions are aged in stoneware crocks sealed with clarified butter.",
  "Oxtail soup rewards cooks who skim the foam during the first half hour and then leave the lid alone until sundown.",
  "Roasting beef bones with a smear of tomato paste before they go into the stockpot builds deep mahogany color.",
  "Always start stock with cold water; starting with boiling water coagulates surface proteins and traps flavor inside the bones.",
  "Ribollita tastes better on the second day when the tuscan kale and cannellini beans have thickened around the bread.",
  "Save your rock-hard Parmigiano-Reggiano rinds in the freezer and drop one into minestrone as it simmers.",
  "Pozole hominy kernels puff open like little clouds when simmered with guajillo chilies and Mexican oregano.",
  "Setting out bowls of shredded cabbage, radish coins, lime, and tostadas lets everyone dress their own pozole.",
  "Sinigang gets its bright sour kick from tamarind pods mashed through a fine sieve over daikon radish and water spinach.",
  "Tom yum goong layers lemongrass, galangal coins, makrut lime leaves, and crushed bird's eye chilies in shrimp-head stock.",
  "Galangal looks like ginger on the cutting board, but it slices like wood and tastes of pine and citrus.",
  "Tom kha gai softens the sharp lime and chili heat with rich coconut milk and straw mushrooms.",
  "Broth Catacombs beneath the bastion store thousands of earthenware amphorae filled with mineral-rich spring water.",
  "The catacomb torches burn scented beeswax so soot never taints the aging stock barrels.",
  "Mulligatawny soup blends curry spices, tart diced apples, red lentils, and coconut milk into a warming bowl.",
  "Cock-a-leekie soup pairs slow-simmered chicken and sweet leeks with barley and julienned prunes.",
  "Bouillabaisse fishermen originally boiled the bony rockfish they couldn't sell at market with saffron, fennel, and orange peel.",
  "Rouille garlic-saffron mayonnaise spread on toasted baguette rounds melts into bouillabaisse like sunshine.",
  "Congee rice porridge cooked for three hours with a piece of ginger and a century egg is the gentlest breakfast on earth.",
  "Stirring congee in one direction during the last ten minutes breaks the rice grains open into creamy clouds.",
  "Topping plain congee with crispy fried youtiao dough sticks, scallions, and white pepper is mandatory on rainy mornings.",
  "Kimchi jjigae tastes best when the kimchi in your crock is at least three months old and pleasantly fizzy.",
  "Simmering kimchi with pork belly and anchovy-kelp stock turns the tofu cubes inside into flavor bombs.",
  "Sundubu jjigae uses uncurdled silken tofu scooped warm into a glowing red stone pot with a raw egg cracked on top.",
  "Doenjang jjigae fermented soybean stew has an earthy depth that anchors any meal after a long hike.",
  "Sichuan mala hotpot divides the cauldron in half with a metal yin-yang wall--clear bone broth on one side, tallow chili on the other.",
  "Swishing paper-thin lamb slices in boiling hotpot broth for seven seconds keeps them tender.",
  "Sesame paste whisked with fermented bean curd, garlic chives, and cilantro is the classic northern dipping bowl.",
  "Pho tai uses raw eye-of-round beef sliced paper-thin across the grain so the boiling broth cooks it in the bowl.",
  "Hoisin and sriracha belong in a small side dish for dipping meat, not squeezed directly into twenty-four-hour pho stock.",
  "Bun bo Hue gets its scarlet sheen from annatto seeds infused in oil with bruised lemongrass stalks.",
  "Caldo verde slices collard greens into ribbons thinner than sewing thread and drops them into creamy potato-chorizo broth.",
  "One slice of smoky chourico sausage in the bottom of each bowl of caldo verde is traditional.",
  "Sopa de lima from the Yucatan perfumes turkey broth with charred local limes and crisp tortilla strips.",
  "Tortilla soup needs pasilla chilies fried briefly in oil and blended with charred tomatoes before hitting the pot.",
  "Avocado cubes and queso fresco go into tortilla soup cold right before serving so they stay fresh.",
  "Cullen skink smoked haddock chowder from the northern coast has enough smoky richness to warm cold fingers.",
  "Waterzooi from Flanders thickens chicken and leek broth with egg yolks and cream at the very last minute.",
  "Harira soup breaks the evening fast with chickpeas, lentils, cinnamon, ginger, and a swirl of lemon-cilantro.",
  "Shorbat adas red lentil soup with toasted cumin and a squeeze of fresh lemon takes twenty minutes and tastes like gold.",
  "Peanut soup from West Africa simmers groundnut paste with tomatoes, scotch bonnet, and sweet potatoes.",
  "Ajiaco from the Andes uses three varieties of potatoes--one stays firm, one softens, and one dissolves to thicken the broth.",
  "Guascas herb leaves and a cob of sweet corn give ajiaco its unmistakable mountain aroma.",
  "Locro squash-and-hominy stew is cooked until the kabocha pumpkin melts into a golden gravy.",
  "Chupe de camarones peruvian shrimp chowder has poached eggs, corn, and a splash of evaporated milk.",
  "Menudo tripe soup simmered with red chili and hominy is the undefeated Sunday morning restorative.",
  "Split pea soup cooked with a smoked ham hock thickens so much overnight you can stand a fork in the pot.",
  "A splash of malt vinegar woken into thick split pea soup right at the table cuts the richness.",
  "Butternut squash veloute roasted with sage leaves and a pinch of freshly grated nutmeg tastes like October.",
  "Toasted pumpkin seeds--pepitas--pop in a dry skillet like tiny green popcorn and crown any squash soup.",
  "Roasted tomato soup needs a pinch of baking soda if your tomatoes are too acidic, or a carrot simmered in the pot for natural sweetness.",
  "Dipping a corner of a cheddar grilled cheese into hot tomato basil soup is a foundational childhood memory.",
  "Cheddar beer soup made with a malty amber ale and dry mustard needs warm soft pretzels for dunking.",
  "Broccoli cheddar soup should have tender florets chopped small enough to fit on a soup spoon without splashing.",
  "Corn chowder gets twice the flavor when you scrape the bare cobs with the back of your knife and simmer them in the milk.",
  "Smoked paprika--pimenton de la Vera--gives potato leek soup a campfire warmth without needing meat.",
  "Chilled cucumber yogurt soup--tarator--with crushed walnuts, garlic, and dill is summer in a bowl.",
  "Chilled sour cherry soup from Hungary uses cinnamon, cloves, and a dollop of sour cream as a starter course.",
  "Miso-tahini ramen broth blends Japanese and Mediterranean pantry staples into instant creamy umami.",
  "Mushroom barley soup made with dried porcini soaking liquid tastes like an ancient forest after rain.",
  "Always strain dried mushroom soaking broth through a coffee filter to catch the tiny specks of forest sand.",
  "Chicken noodle soup needs wide egg noodles cooked in a separate pot so they don't drink up all the golden broth in the fridge.",
  "Drop a whole unpeeled yellow onion into your chicken stock; the papery skin dyes the broth a rich amber gold.",
  "Bouquet garni--parsley stems, thyme sprigs, and a bay leaf tied in leek green--can be fished out with one tug of string.",
  "Sachet d'epices wraps peppercorns, cloves, and garlic in cheesecloth so nobody bites into a whole clove.",
  "Skimming fat off cold stock is easy when it solidifies into a neat white cap overnight in the icebox.",
  "Glace de viande is stock reduced to one-tenth its volume until it cools into a rubbery puck of pure savory power.",
  "One teaspoon of meat glaze dissolved in hot water with butter creates an instant pan sauce.",
  "Court bouillon--water simmered with white wine, lemon, mirepoix, and peppercorns--poaches delicate fish in ten minutes.",
  "Dashi ichiban is the first gentle infusion for clear soup; dashi niban simmers the kelp and flakes a second time for stews.",
  "Ochazuke pours hot green sencha or dashi over leftover rice with flaked salmon, nori, and rice crackers.",
  "Setting a Paper Plate for a high-level bEATst is optimistic, though my cousin once befriended a Baguettebit on a napkin.",
  "Wooden Boards smell of acacia resin and give a solid one-point-five multiplier when a wild dish is considering your table.",
  "Ceramic Plates retain oven warmth, which makes Steamed and Brothy bEATsts much more likely to sit down.",
  "A Bento Lacquer Set has separate compartments so picky dual-type bEATsts don't complain about their sauces touching.",
  "The Royal Banquet Setting comes with miniature candelabras and a crystal cloche--even legendary dishes respect that presentation.",
  "Sprinkling a Chef Garnish Treat before you set a plate boosts your chances by sixty percent.",
  "A bEATst with the Appetized status is fifty percent more willing to pull up a chair at your table.",
  "Some nocturnal bEATsts like Midnitoast and Moonbun won't even look at a plate while the sun is up.",
  "Pressing the N key--or SELECT on your controller--lets you wait until starlight or sunrise whenever you're outdoors.",
  "Kitchen Temp starts at zero in every battle and shifts between Chilled minus-two and Sear plus-two as moves fly.",
  "When the Kitchen Temp hits Sear plus-two, Spicy, Fried, and Toasted moves hit twenty-five percent harder.",
  "At Chilled minus-two, Chilled, Raw, and Pickled techniques gain a twenty-five percent edge while Spicy moves cool off.",
  "Flavor Combos trigger when the same bEATst follows one cooking type with a complementary type on the next turn.",
  "Following a Toasted move with a Savory move triggers the Umami Melt combo for bonus damage and a ten-percent heal.",
  "Chaining Spicy into Sweet creates the Hot Honey Glaze combo, which hits thirty-five percent harder and restores health.",
  "Steamed followed by Brothy triggers Soup Dumpling Burst--Master Baozi's signature two-turn sequence.",
  "Fried into Pickled fires the Crispy Tang Cut combo; acid always balances oil in a well-run kitchen.",
  "Fermented followed by Toasted triggers Sourdough Crunch, my personal favorite Breadlands finisher.",
  "Chilled into Sweet creates Gelato Swirl, which heals fifteen percent of your bEATst's maximum HP on impact.",
  "Herbal followed by Brothy activates Aromatic Simmer, filling the whole battlefield with thyme and bay leaf steam.",
  "Raw into Pickled triggers Ceviche Zing--citrus brine curing fresh ingredients right in the middle of a turn.",
  "Each of the twelve cooking types has a teachable Recipe Card you can buy at regional Pantry Marts or earn from quests.",
  "Teaching a bEATst a fourth move is easy, and when it learns a fifth you can pick which old recipe to retire.",
  "Switching bEATsts mid-battle works against wild dishes just as smoothly as it does against Head Chefs.",
  "If your lead bEATst is weak to Pickled moves, open the PARTY tab in battle and send in a Sweet or Spicy partner.",
  "Sizzling status singes a bEATst with pan heat, while Brined slows down careless footwork.",
  "Drowsy happens after a heavy carb course--keep Peppermint Tea or a Double Espresso in your bag.",
  "Warm Broth Cups heal twenty-five HP and cost only forty gold, making them the workhorse of Toastwood Trail.",
  "Hearty Stew restores sixty-five HP and can be cooked for free at the Cruston bEATst Cafe if you bring a Broth Cup and Garnish Treat.",
  "Grand Feasts restore full health and clear any kitchen status in a single course.",
  "Your Copper Soup Ladle lets you press A while facing any pond, river, harbor, or stock pool to ladle up wild bEATsts.",
  "The Kitchen Lantern automatically illuminates a safe circle around you in dark caverns and the Cauldron Conservatory.",
  "Inns never charge a single coin--every Simmer Inn keeper heals your full party's HP and move PP with a smile.",
  "If all six of your party bEATsts faint, you'll dash back to Cruston Town with your party rested and your gold intact.",
  "Your storage Box holds every extra bEATst you plate once your six-slot party is full.",
  "Visiting the bEATst Cafe in Cruston Town lets you check on the dishes relaxing in your storage Box.",
  "Saving your game in any of the three slots writes to local storage and lets you export a JSON backup file anytime.",
  "Every evolution line in Pantrylia learns eight moves by level-up, starting from basic kitchen taps up to signature feasts.",
  "Crustling evolves into Paninipup at level sixteen, and then into the towering Clubbehemoth at level thirty-two.",
  "Doughbit evolves into Baobouncer at sixteen and reaches Steamlord at thirty-two with clouds of fragrant steam.",
  "Slurplet grows into Udonox at sixteen and becomes Ramenrex at thirty-two, crowned with a golden soft-boiled egg.",
  "Dripdrop simmers into Brothling at sixteen and awakens as Cauldrake at thirty-two.",
  "Have you heard the rumor about the golden door in the Grand Tasting Hall? It only opens for a Champion at night.",
  "They say you need all four food families--Sandwiches, Dumplings, Noodles, and Soup--in your party to wake #151.",
  "Carry a spare Royal Banquet Setting if you ever unlock the Secret Pantry Door, because Consommyth has refined taste.",
  "Completing all 151 entries in the bEATdex earns a special diploma from Chef Brotholomew himself.",
  "Sparkling spots hidden in corners of towns and dungeons hold secret caches of plates, treats, and gold.",
  "Pushing dough boulders or sourdough casks only works if the tile behind the block is clear floor.",
  "Stepping on a golden floor switch drops every red laser gate on that map for the rest of your adventure.",
  "Conveyor belts and spilled sesame oil slide you until you hit dry floor, so line up your approach first.",
  "Chrome Fork Syndicate agents wear clip-on ties that double as thermometers for checking corporate compliance.",
  "I asked a Syndicate grunt why their logo is a three-pronged fork, and he said the fourth tine was cut in the Q3 budget.",
  "Beige Plate Corp's flagship product was 'Nutrient Loaf #4', which tasted like an envelope you licked twice.",
  "Auditor Vesper tried to cite my grandmother's marinara for 'unregistered oregano variance' last Tuesday.",
  "Director Crumb carries a briefcase full of styrofoam takeout clamshells and calls it 'packaging innovation'.",
  "VP Synergy Glaze speaks entirely in slide-deck bullet points even when ordering a cup of tea.",
  "CEO Sterling Ladle's executive suite had a laser gate solely because he kept forgetting where he put his office key.",
  "Now that Sterling Ladle runs a soup cart in the Eternal Pantry, he actually uses real carrots and smiles for free.",
  "Rival Saffron used to weigh her salt on a jeweler's scale before she realized a pinch from the heart tastes better.",
  "Saffron's notebook has color-coded tabs for every battle she lost to you, plus a sketch of her starter smiling.",
  "When Saffron teamed up with you on the second floor of Chrome Fork HQ, the Syndicate agents didn't stand a chance.",
  "Baker Barnaby still checks his pockets three times an hour to make sure his Cultured Butter hasn't wandered off.",
  "Food Critic Brie writes her reviews in fountain pen on linen napkins so she can eat the evidence if she's wrong.",
  "Critic Camembert in Bao Harbor carries a miniature silver steamer thermometer in his breast pocket.",
  "Critic Vermicelli in Udon Hollow judges noodle elasticity by listening to the snap when a strand breaks.",
  "Critic Bisquetta in Chowder Crossing can identify fourteen herbs blindfolded from a single waft of steam.",
  "The Yeast Monk in Panini Plaza speaks in a whisper so he doesn't startle the rising ciabatta.",
  "Apprentice Lin tied a red ribbon to Master Baozi's bamboo lid after the north wind blew it into Gyoza Cove.",
  "Tea Master Po's teapot has never been washed with soap in forty years--only rinsed with boiling spring water.",
  "Chili Courier Rico wears asbestos-lined oven mitts even in July because his five-alarm chili jars radiate heat.",
  "My neighbor tried to plate a wild Sourdoughon with a Paper Plate and the loaf simply ate the plate.",
  "I keep finding sesame seeds in my keyboard and honestly they improve the tactile click of the spacebar.",
  "Never challenge a Noodleridge chef to a staring contest; they spend all day watching pots wait to boil.",
  "My uncle insists that cast-iron pans have memories, and his skillet still remembers a burnt pancake from 1998.",
  "If a recipe says 'caramelize the onions in ten minutes', the author is lying to you and should not be trusted.",
  "Two cloves of garlic in a recipe is just a polite suggestion; five cloves is where the conversation begins.",
  "Measuring vanilla extract with the cap of the bottle is a rite of passage in every home bakery.",
  "When a soup needs 'something' at the end, ninety percent of the time that something is a teaspoon of vinegar or lemon juice.",
  "Salt doesn't make food taste salty when used right; it makes tomatoes taste more like tomatoes.",
  "Cold butter whisked into a hot pan sauce off the burner--monter au beurre--gives it a mirror gloss.",
  "Sharp knives are safer than dull knives because they bite into onion skin instead of skating toward your thumb.",
  "Curl your fingertips into a bear claw on the cutting board and your knuckles will guide the chef's knife safely.",
  "A damp paper towel underneath your wooden cutting board stops it from sliding around while you chop.",
  "Mise en place--having every bowl of chopped herbs ready before you light the stove--saves dinner from chaos.",
  "Clean as you go, or by the time the souffle rises your sink will look like a dungeon puzzle.",
  "Wooden spoons never scratch enamel pots and never burn your hand when left resting on the rim.",
  "Silicone spatulas earn their keep by scraping the last two tablespoons of cake batter out of the mixing bowl.",
  "A bench scraper costs four dollars and is the single fastest way to move diced celery from board to pot.",
  "Microplane zesters take only the fragrant colored citrus peel and leave the bitter white pith behind.",
  "Mortar and pestle crushes garlic cells instead of slicing them, releasing a mellower, sweeter oil.",
  "Toast your whole spices in a dry skillet until you smell them, then grind them once they cool.",
  "Bay leaves work quietly in the background; try simmering plain water with one bay leaf and you'll finally taste the eucalyptus note.",
  "Fresh nutmeg grated over bechamel or spinach smells like warm cedar and clove.",
  "Saffron threads steeped in two tablespoons of warm water for twenty minutes release their full golden sunset.",
  "Vanilla beans split lengthwise and scraped into custard can be dried afterwards and buried in a jar of sugar.",
  "Brown butter--beurre noisette--happens in the thirty seconds between 'foaming yellow' and 'uh oh, burnt'; stay by the stove.",
  "Deglazing a roast pan with stock and scraping the brown bits with a wooden spoon is where gravy comes from.",
  "Resting a roast or a thick panini for five minutes lets the juices settle instead of running all over the board.",
  "Taste your dish with a clean spoon at every step--seasoning at the end only salts the surface.",
  "Cooking for friends is the one magic spell that works every single time you cast it.",
  "Under the starlight, the sourdough ovens in Cruston Town hum a low, sleepy bass note.",
  "Night air cools the bakery roofs fast, making the rising dough inside smell twice as sweet.",
  "If you walk Toastwood Trail after dark, watch for Midnitoast glowing faintly among the wheat stalks.",
  "Fireflies over Deli Meadows blink in the exact amber shade of toasted brioche.",
  "The creek in Deli Meadows runs cooler at night, and the watercress tastes extra crisp.",
  "Panini Plaza strings up warm paper lanterns between the twin kitchens as soon as dusk settles.",
  "Even at midnight, you can hear the conveyor belts in The Toaster Hearth clacking away.",
  "Down in Sourdough Cavern, day and night feel the same, though the yeast bubbles faster when the moon is full.",
  "Truffle Cellar's mushrooms release their spores after sundown, filling the stairs with earthy perfume.",
  "Bao Harbor's water reflects the red steamer lanterns like a hundred floating rubies.",
  "Night fishermen in Steambay keep warm by tucking a steamed pork bun inside their oilskin coats.",
  "Bamboo Mist Path turns silver under the moonlight, and the mist clings low around your ankles.",
  "Moonbun only comes out in Gyoza Cove when the tide is high and the stars are out.",
  "Listening to the waves slap against Pierogi Pier at night makes me crave hot potato dumplings.",
  "From the top of Steamer Spire at night, you can see the lighthouse beam sweeping across all of Steambay.",
  "Udon Hollow's waterwheels creak softly in the dark while the morning dough rests under damp cloths.",
  "Slurp Canyon's rope bridges look like silver threads strung between the cliffs by moonlight.",
  "Midniteramen prowls Al Dente Ascent after sunset, drawn to the scent of simmering miso.",
  "At the top of Ramen Summit, the stars look close enough to scoop up with a porcelain ladle.",
  "Wok Volcano's crater glows cherry-red against the night sky like a giant charcoal brazier.",
  "Chowder Crossing's mineral springs steam thicker in the cool night air, wrapping the boardwalks in fog.",
  "Will-o'-the-wisps over Simmer Fen are really just harmless marsh gas bubbles warmed by the soup springs.",
  "Midnitebisque glides through Kettle Gorge after dark, its tureen lid gleaming like polished silver.",
  "Bisque Bastion's watchtowers keep braziers of rosemary burning all night to guide late travelers.",
  "In Broth Catacombs, the ancient stock amphorae cool down a degree at midnight, pulling their corks tight.",
  "Chrome Fork HQ leaves one fluorescent hallway light buzzing all night to save on overtime.",
  "The Grand Tasting Hall's chandeliers dim to candlelight at night, and that golden pantry door starts to hum.",
  "In the Eternal Pantry, night is just a cozy velvet tablecloth draped across the sky.",
  "Late-shift bakers always get the first crusty heel off the midnight loaf before anyone else wakes up.",
  "There's no quieter sound in the world than snow or starlight falling outside while a stockpot simmers indoors.",
  "Nighttime tea brewed from roasted barley--mugicha--has zero caffeine and tastes like toasted grain.",
  "Chamomile blossoms steeped with a spoonful of clover honey put even the rowdiest bEATst to sleep.",
  "Warm milk with a pinch of turmeric, cinnamon, and black pepper is my favorite bedtime cup.",
  "Check your pantry latches before bed; a hungry Pbnjinx can unhook a brass clasp in three seconds.",
  "Night dew on the scallion rows makes the green tops glisten like emerald needles at dawn.",
  "The night watchman in Panini Plaza trades half his ham sandwich for a cup of hot broth every evening.",
  "Owl-shaped Onigiriowl perch on the pier pilings after dusk, waiting for dropped rice grains.",
  "When the bakery fires bank down to embers, we slide in ceramic pots of cassoulet to bake until sunrise.",
  "Slow-baked overnight oats with diced apples and cinnamon smell like apple pie when you wake up.",
  "Cold pizza or cold focaccia eaten standing in front of the icebox at midnight has zero calories by kitchen law.",
  "The harbor foghorn sounds like a giant blowing across a bowl of hot chowder.",
  "Starlight bouncing off the salt pans in Gyoza Cove looks like someone spilled diamond dust on the rocks.",
  "Nonna Fusilli leaves a small bowl of cacio e pepe on the windowsill on full-moon nights for lucky travelers.",
  "Sensei Twirl practices blindfolded dough stretching by candlelight so he can feel the thickness by touch alone.",
  "Alchemist Bisque charts the constellations to decide whether tomorrow is a root-vegetable or shellfish day.",
  "Lady Bouillon checks the wax seals in the Deep Stock Vault every evening with a brass magnifying glass.",
  "Chef Brotholomew writes his best research notes at two in the morning with a mug of double espresso.",
  "Innkeeper Mabel warms the guest slippers by the hearth so nobody steps on cold floorboards at dawn.",
  "Clerk Pippin counts the Paper Plates twice before flipping the shop sign to CLOSED.",
  "Stove Chef Remi leaves the pilot light glowing blue so the morning stock can start at first light.",
  "Did you notice the milk pond in South Cruston? The local dairy bEATsts keep it fresh.",
  "Every house in Cruston Town has a bread peel hanging by the front door for good luck.",
  "My grandfather laid the oven bricks in Central Plaza using mortar mixed with rye flour.",
  "If you talk to Chef Brotholomew after completing all 151 bEATdex entries, he'll hand you the studio diploma.",
  "Toastwood Trail's south ledge is a one-way jump, so make sure you picked up the chest on the west side first.",
  "Wild Picklewick hide among the buttercup flowers because their dill aroma blends right in.",
  "The bridge over Deli Meadows' milk creek was built wide enough for two cheese wagons to pass.",
  "Panko crumbs scattered along the meadow path always lead to a hungry bird or a hidden stash.",
  "Panini Plaza's twin gyms test two sides of kitchen craft: speed on the conveyors and logic at the switches.",
  "Sous-Chef Toasty in the Toaster Hearth wears heat-resistant gloves up to his elbows.",
  "Sous-Chef Slicer in Deli Counter Spire can eye-ball a quarter-pound of swiss to within two grams.",
  "Sourdough Cavern's first floor has patches of wild cave-wheat growing under the skylight cracks.",
  "On the second basement of Sourdough Cavern, push the oak cask straight ahead to clear the narrow passage.",
  "Truffle Cellar's lower floor has a slick patch of spilled truffle oil--line up your steps before you slide!",
  "Bao Harbor's twin docks jut out into the bay so steamer ferries can tie up on either side.",
  "Bamboo Cloud Kitchen's floor is polished with toasted sesame oil; step on the edge and you'll glide across.",
  "Sous-Chef Vapor practices tai chi on the slippery floor without ever losing his slippers.",
  "Bamboo Mist Path has stone lanterns carved to look like stacked dim sum baskets.",
  "Gyoza Cove's tidepools warm up at noon, making the coastal rocks steam when waves crash.",
  "Skillet Tidehouse combines a conveyor belt with a locked gate switch--flip the switch on the east side first!",
  "Sous-Chef Sizzle keeps a cast-iron press warm just in case a challenger wants crisp potstickers.",
  "Pierogi Pier's wooden boardwalk creaks in F-sharp when the humidity rises.",
  "Steamer Spire's first floor smells of cedar and ginger, while the second floor is gated by a brass switch.",
  "Lighting the Mist Lantern at the top of Steamer Spire rewards you with three cups of Peppermint Tea.",
  "Udon Hollow's central canal carries clear mountain snowmelt straight to the noodle-washing basins.",
  "Pull-Noodle Dojo has a heavy ball of springy dough blocking the center aisle--push it aside to reach Sensei Twirl!",
  "Sous-Chef Stretch warms up with fifty squats before rolling a single sheet of pasta.",
  "Slurp Canyon's dual chili rivers run bright crimson from the mild red bell peppers growing upstream.",
  "The Golden Chopsticks on the canyon ledge were dropped by a traveling noodle poet fifty years ago.",
  "Al Dente Ascent winds past terraced durum wheat fields that turn bronze in late summer.",
  "Wok Peak Bistro's floor has a wide slick of extra-virgin olive oil right in front of Nonna Fusilli's station.",
  "Sous-Chef Simmer keeps a basket of warm garlic knots by the door for tired climbers.",
  "Ramen Summit sits above the treeline, where the air is thin and the tonkotsu broth is thick.",
  "Wok Volcano's first floor has vents of dry heat, and the crater floor below is slick with seasoned wok oil.",
  "Capturing a Wok Hei Spark at the volcano rim earns you two cups of Double Espresso.",
  "Chowder Crossing's bridges connect four islands floating in a warm mineral lagoon.",
  "Cauldron Conservatory is kept pitch-dark so the bioluminescent broth herbs can glow undisturbed.",
  "Sous-Chef Roux can navigate the dark conservatory by the smell of the simmering cauldrons alone.",
  "Simmer Fen's wooden duckboards keep your boots dry above the bubbling peat.",
  "The lost Copper Ladle in Simmer Fen still shines because the mineral water prevents tarnish.",
  "Kettle Gorge's Perpetual Valve regulates the steam pressure for every kitchen in Brothbasin.",
  "Bisque Bastion's heavy stone walls kept the soup recipes safe when Chrome Fork tried to audit the region.",
  "The Deep Stock Vault requires flipping the southeast floor switch before the vault gate opens.",
  "Sous-Chef Consomme polishes the vault ladles until you can see your face in the bowl.",
  "Broth Catacombs' upper crypts are lined with bay-leaf wreaths, and the lower vault is dark and gated.",
  "Chrome Fork HQ's first floor has a corporate conveyor belt designed to usher visitors past the reception desk.",
  "On Chrome Fork HQ's executive suite, Rival Saffron holds off the security detail while you hit the corner switch.",
  "Grand Tasting Hall's red carpet runs straight through three Master Tasters to Champion Chef Aurelia's table.",
  "Banquet Prep Chef in the Grand Hall offers free full restores so you can challenge the gauntlet at full strength.",
  "Wild starter-family bEATsts roam Eternal Pantry's crystal meadows at level forty-eight and up.",
  "Wait until a loaf of sourdough cools to room temperature before slicing, or the steam escapes and leaves the crumb gummy.",
  "A serrated bread knife with wide scallops saws through crisp crusts without squishing the soft interior.",
  "When making grilled cheese, spreading a thin layer of mayonnaise on the outside of the bread browns more evenly than cold butter.",
  "Actually, melted salted butter brushed into the pan with a sprig of thyme beats mayonnaise on grilled cheese every day of the week.",
  "If you layer thinly sliced Granny Smith apple inside a sharp cheddar panini, the tart crunch wakes up the whole lunch.",
  "Focaccia dough is eighty percent water by weight, so it feels more like pancake batter than bread dough until you fold it.",
  "Stretch and fold wet dough every thirty minutes instead of kneading it on a floured board; gravity does half the work.",
  "Autolyse--resting flour and water together for forty minutes before adding yeast and salt--gives gluten a head start.",
  "Baker's percentages measure every ingredient against total flour weight at one hundred percent, so scaling a recipe is effortless.",
  "Steam in the first ten minutes of baking keeps the outer dough elastic so the loaf can expand to its full height.",
  "Once the crust sets, venting the oven door lets dry heat caramelize the sugars into a deep blistered brown.",
  "Tiny micro-blisters on the crust of a sourdough loaf mean the dough fermented slowly in the cold overnight.",
  "Whole grain rye flour has pentosan gums that compete with gluten, so rye bread relies on starch gelation for structure.",
  "Slicing dense pumpernickel requires wiping the knife blade with a damp cloth between cuts.",
  "Brioche dough takes its butter at the very end, one cold cube at a time, slapping against the side of the mixer bowl.",
  "Chilling brioche dough overnight firms up the butter so you can shape neat fluted heads on brioche a tete.",
  "Challah braided with six strands looks intricate, but the pattern is just 'outside over to the center' repeated in rhythm.",
  "Poppy seeds and sesame seeds stick best to an egg wash diluted with a teaspoon of water and a pinch of salt.",
  "Pullman loaf pans have a sliding metal lid that squares off sandwich bread for uniform club sandwiches.",
  "Toast that pops up and sits in the warm toaster slot for thirty seconds goes limp from its own steam--move it to a wire rack!",
  "Rubbing a raw peeled garlic clove over rough toasted country bread--fettunta--acts like edible sandpaper.",
  "Bruschetta is pronounced 'brusketta' with a hard K in every kitchen that respects Italian vowels.",
  "Dicing Roma tomatoes for bruschetta works best when you scoop out the watery seeds first and save them for gazpacho.",
  "Pan bagnat from Nice packs tuna, hard-boiled eggs, olives, and anchovies into a round loaf soaked with olive oil and vinegar.",
  "Wrapping a pan bagnat tightly in parchment and weighting it down with a cast-iron skillet for two hours is essential.",
  "Croque monsieur tops ham and Gruyere toast with grated cheese and broils it until the bechamel blisters.",
  "Drop a sunny-side-up egg on top of a croque monsieur and it immediately becomes a croque madame.",
  "Welsh rarebit isn't just melted cheese on toast; it's cheddar simmered with stout beer, Worcestershire, and mustard into a velvet blanket.",
  "Banh mi pate spread thin on the bottom half of the baguette keeps the pickled radish juice from soaking through.",
  "Maggi seasoning sauce--just three drops over cucumber and cilantro--is the secret handshake of great street sandwiches.",
  "Cemita Poblana rolls are topped with sesame seeds and layered with avocado, Oaxaca string cheese, chipotle, and papalo herb.",
  "Papalo leaves have a bold cilantro-citrus punch that stands up to fried milanesa cutlets.",
  "Chivito sandwiches from the southern coast stack steak, mozzarella, olives, bacon, and egg on a soft bun.",
  "Francesinha from Porto covers a tall meat sandwich in melted cheese and ladles hot spiced tomato-beer gravy around the plate.",
  "You eat a Francesinha with a knife and fork and dip crispy fries into the moat of sauce.",
  "Katsu sando crusts are sliced off with a long sujihiki blade so every bite has the exact same ratio of bread to cutlet.",
  "Tamago sando egg salad uses a pinch of sugar and Kewpie yolk-only mayonnaise for that rich golden custard texture.",
  "Boiling eggs for eight minutes gives you a jammy yolk that mashes into the creamiest sandwich filling.",
  "Fruit sando whipped cream needs a spoonful of mascarpone so the strawberries stay centered when you slice the diagonal.",
  "Mark the direction of your strawberries with a toothpick before spreading the cream so your diagonal cut hits every berry in half.",
  "Cucumber sandwiches require peeling the cucumber into striped ribbons and salting the slices on paper towels first.",
  "Dill weed and lemon zest mixed into softened butter make cucumber tea sandwiches disappear from the tray in seconds.",
  "Roast beef for deli slicing should be chilled thoroughly after cooking so you can shave it into translucent pink ribbons.",
  "Pastrami gets its black bark from coarse cracked coriander and black pepper pressed onto brined navel beef before smoking.",
  "Steaming smoked pastrami over simmering water for an hour before slicing melts the connective tissue into butter.",
  "Corned beef uses the same brine as pastrami, but it's simmered gently in a pot with pickling spices instead of smoked.",
  "Russian dressing gets its kick from prepared horseradish and finely minced pimiento.",
  "Thousand Island dressing uses sweet pickle relish instead of horseradish, which is a polite cousin to Russian dressing.",
  "Giardiniera pickled vegetables--cauliflower, carrots, celery, and serranos in oregano oil--belong on every Italian beef sandwich.",
  "Ordering an Italian beef 'dipped' means the cook dunks the entire roll into the warm oregano-garlic roast jus.",
  "Har gao shrimp filling is slapped against the mixing bowl by hand to align the proteins for a snappy 'crunch' when steamed.",
  "Adding a tiny dice of blanched bamboo shoot to shrimp dumplings gives them texture and keeps the filling juicy.",
  "Siu mai pork should be hand-minced with two cleavers rather than ground in a machine; small cubes hold more broth.",
  "Dried shiitake mushrooms rehydrated in cold water overnight taste twice as meaty as ones rushed in boiling water.",
  "Cheung fun steamed rice noodle rolls are poured as thin white batter onto a cloth stretched over boiling water.",
  "Scraping a steamed rice sheet off the cloth into a soft roll takes a flat brass spatula and fearless fingertips.",
  "Sweetened soy sauce simmered with rock sugar and a drop of sesame oil is the only dressing cheung fun needs.",
  "Lo mai gai sticky rice is steamed in a small porcelain bowl and inverted onto a plate right at the dim sum cart.",
  "Taro dumplings--wu gok--use mashed steamed taro root mixed with wheat starch so the outside puffs into lacy bird's-nest filigree in hot oil.",
  "Ham sui gok glutinous rice crescents have a crispy bubbly shell, a chewy sweet middle, and savory pork inside.",
  "Turnip cake--lo bak go--is actually made from shredded white daikon radish steamed with rice flour and pan-fried in squares.",
  "XO sauce simmered from dried scallops, Jinhua ham, shallots, and chilies turns humble turnip cake into royalty.",
  "Egg tarts--dan tat--come in two schools: flaky laminated puff pastry shells or tender cookie-style shortcrust.",
  "You can tell an egg tart just came out of the deck oven when the custard dome is still puffed slightly above the pastry rim.",
  "Pineapple buns--bo lo bao--contain zero pineapple; the sugary cookie topping cracks in a diamond pattern that looks like one.",
  "Tucking a thick slab of ice-cold salted butter into a piping-hot pineapple bun is a religious experience.",
  "Red bean paste--anko--comes in smooth tsubuan with whole skins or silky strained koshian depending on the pastry.",
  "A pinch of salt in sweet red bean paste makes the azuki beans taste richer instead of cloying.",
  "Daifuku strawberry mochi wraps a whole fresh berry in thin red bean paste and soft pounded rice cake.",
  "Dusting your hands with katakuriko potato starch stops sticky hot mochi from welding itself to your palms.",
  "Shengjianbao pan-fried soup buns are placed pleated-side down so the bottom turns crunchy while the top stays fluffy.",
  "Scattering toasted white and black sesame seeds and chopped scallions over shengjianbao right before lifting the lid is signature Steambay.",
  "Scallion pancakes--cong you bing--get their flaky layers from rolling up oiled dough like a jelly roll, coiling it into a snail, and flattening it again.",
  "Clapping a freshly fried scallion pancake between two spatulas shatters the crust into separated flaky layers.",
  "Jianbing crepes spread mung-bean batter over a round cast-iron griddle with a wooden T-stick in five seconds.",
  "A crispy fried wonton cracker--baocui--folded inside a soft jianbing crepe gives every bite a loud crunch.",
  "Borscht without a bay leaf and three allspice berries in the simmer pot is missing its bass notes.",
  "Solyanka soup combines cured meats, capers, olives, lemon slices, and pickle brine into the ultimate salty-sour tavern bowl.",
  "Ukha clear fish soup from the northern rivers drops a glowing birchwood coal into the pot for a second to kiss the broth with woodsmoke.",
  "Okroshka cold summer soup dices boiled potatoes, cucumbers, radishes, and herbs into tangy fermented kvass or kefir.",
  "goulash soup--gulyasleves--starts by dissolving sweet Hungarian paprika in warm lard off the flame so the spice never scorches bitter.",
  "Csipetke--tiny pinched egg dumplings dropped straight from your fingers into boiling goulash--thicken the soup naturally.",
  "Halaszle fisherman's soup passes carp bones and onions through a food mill for a thick crimson paprika broth.",
  "Laksa lemak uses candlenuts--buah keras--ground into the rempah spice paste to thicken the coconut broth.",
  "Belacan toasted shrimp paste wrapped in foil and dry-roasted in a pan wakes up the whole neighborhood.",
  "Vietnamese canh chua sour soup balances tamarind, pineapple chunks, okra, elephant ear stems, and crispy fried garlic.",
  "Sawtooth herb--ngo gai--and rice paddy herb torn over hot sour soup smell like tropical lime and cumin.",
  "Mohinga rice noodle soup thickens catfish broth with toasted chickpea flour and tender banana-stem cores.",
  "Soto ayam Indonesian yellow chicken soup gets its color from fresh turmeric root ground with candlenut and coriander.",
  "Koya--crushed fried prawn crackers and garlic--sprinkled on top of soto ayam thickens the spoonfuls as you eat.",
  "Bakso meatball soup serves bouncy beef spheres alongside rice vermicelli, bok choy, and sweet kecap manis.",
  "Sinigang can be soured with green mango, calamansi, kamias, or guava when fresh tamarind is out of season.",
  "Nilaga clear beef shank soup lets sweet cabbage, corn on the cob, and Saba plantains speak for themselves.",
  "Arroz caldo ginger rice porridge crowned with toasted garlic chips, safflower threads, and calamansi cures any mountain chill.",
  "Kare-kare oxtail stew is thickened with ground roasted peanuts and toasted rice flour, always served with bagoong shrimp paste on the side.",
  "Sancocho seven-meat stew simmers yuca, plantains, corn, and cilantro in one giant communal cauldron.",
  "Moqueca Brazilian fish stew layers palm oil or coconut milk with tomatoes, peppers, and lime in an earthenware clay pot.",
  "Farofa--toasted cassava flour sizzled in butter with onions--is sprinkled over moqueca to soak up the rich broth.",
  "Caldo de queso from Sonora drops cubes of firm white cheese into hot roasted green-chili and potato broth so the cheese stretches without melting away.",
  "Birria consomme spiced with ancho, guajillo, and cinnamon is meant for dunking crispy cheese-stuffed tacos.",
  "Chili colorado uses zero tomato; the deep red sauce is pure rehydrated dried chilies blended with garlic, oregano, and broth.",
  "Hominy is dried field corn soaked in an alkaline limewater bath--nixtamalization--which unlocks niacin and gives it that tortilla aroma.",
  "Epazote leaves added to a pot of black beans add a savory herbal note that no other herb on earth can mimic.",
  "Avocado leaves toasted briefly over a burner before dropping into black bean soup release a warm anise fragrance.",
  "Cacio e pepe pasta water needs to be cooked in a shallow skillet with minimal water so the starch concentration is double.",
  "Grating Pecorino Romano on the fine star-shaped holes of a box grater makes fluffy snow that melts without clumping into strings.",
  "If your cacio e pepe sauce splits into lumps, pour it into a blender with a splash of warm pasta water to rescue the emulsion.",
  "Pasta alla Gricia is Amatriciana's older ancestor--just guanciale, Pecorino, black pepper, and starchy water before tomatoes reached Italy.",
  "All'Assassina spaghetti from Bari is cooked raw in a cast-iron skillet with spicy tomato broth until the strands char and caramelize.",
  "Passatelli noodles are pressed through a potato ricer from a dough of breadcrumbs, Parmigiano, eggs, lemon zest, and nutmeg.",
  "Pizzoccheri buckwheat ribbons from the Alps are boiled with savoy cabbage and potatoes, then layered with melted Bitto cheese and garlic butter.",
  "Bigoli thick whole-wheat spaghetti from the Veneto are extruded through a hand-cranked brass press mounted to a wooden bench.",
  "Malloreddus Sardinian semolina gnocchetti are ridged on a woven reed basket and served with saffron sausage ragu.",
  "Fregola sarda looks like giant couscous pearls toasted in the oven until golden brown and simmered like risotto with clams.",
  "Tortellini in brodo is traditionally counted by the spoonful--fifteen to a bowl if the cook likes you.",
  "Zuppa Toscana marries spicy fennel sausage, russet potato slices, and lacinato kale in a garlicky cream broth.",
  "Stracciatella soup drizzles beaten egg, Parmigiano, and semolina into swirling chicken consomme with a fork.",
  "Pasta e fagioli--pasta and beans--is best when you mash half the borlotti beans against the side of the pot to make the broth creamy.",
  "Ditalini--little thimbles--are the undisputed best pasta shape for minestrone and bean soups because they fit alongside a bean on the spoon.",
  "Pastina tiny star pasta cooked directly in chicken broth with a pat of butter and grated parmesan is pure comfort.",
  "Avgolemono thickens without curdling as long as you keep the soup below a simmer once the egg-lemon mixture goes in.",
  "Fanesca from Ecuador is a rich springtime soup made with twelve kinds of beans and grains, squash, milk, and tiny fried empanadas.",
  "Chairo paceno uses chuno--freeze-dried Andean potatoes--simmered with beef, wheat kernels, and hierba buena mint.",
  "Sopa paraguaya is the only 'soup' in history that bakes into a dense, savory cornmeal-and-cheese bread.",
  "Bori-bori soup floats fluffy cornmeal-and-cheese balls in golden chicken broth scented with oregano and saffron.",
  "Lohikeitto Finnish salmon soup needs only good fish stock, potatoes, carrots, allspice, cream, and a mountain of fresh dill.",
  "Kallops Swedish braised beef stew gets its warm sweetness from whole allspice berries and pickled beets on the side.",
  "Erwtensoep Dutch split pea soup is only officially ready when a wooden spoon stands upright in the center of the pot.",
  "Rookworst smoked sausage sliced into thick coins is the traditional partner for a bowl of Dutch pea soup.",
  "Pot-au-feu simmers beef shanks, marrow bones, leeks, turnips, and a clove-studded onion for an entire afternoon.",
  "Serving the clear pot-au-feu bouillon first with toasted marrow-bone bread before bringing out the meats is classic bistro style.",
  "Garbure Gascon cabbage-and-bean soup is finished by pouring a ladle of hot broth into your empty bowl with a splash of red wine.",
  "Soupe au pistou stirs a cold paste of sweet basil, garlic, and olive oil into hot summer vegetable and bean soup at the table.",
  "Bourride thickens Mediterranean fish broth with garlic aioli whisked with egg yolks until the soup coats the spoon.",
  "Cotriade from Brittany uses cream, butter, potatoes, and four kinds of Atlantic fish with a splash of cider vinegar.",
  "Watercress soup blends peppery fresh greens with simmered potato and leek for five seconds so the emerald color stays vivid.",
  "Sorrel soup uses lemon-tangy garden sorrel leaves shredded into ribbons that melt into silk the moment they hit hot stock.",
  "Nettle soup harvested with thick leather gloves in early spring tastes like a cross between spinach and sweet green peas.",
  "Chestnut soup roasted with fennel seed and topped with crispy pancetta crumbs is the pride of winter banquets.",
  "Jerusalem artichoke--sunchoke--veloute has a naturally sweet, nutty artichoke flavor when roasted until caramelized.",
  "Celeriac--celery root--looks like a gnarled moon rock on the outside and purees into snowy ivory silk on the inside.",
  "Parsnip soup roasted with curry powder and finished with apple cider balances earthy sweetness with warm spice.",
  "Cauliflower soup cooked with a wheel of aged Stilton or Roquefort needs nothing more than crusty walnut bread.",
  "Lentil soup loves cumin, coriander, smoked paprika, and a generous squeeze of lemon right before you ladle it out.",
  "Black bean soup topped with diced red onion, cilantro, sour cream, and lime turns humble pantry staples into a fiesta.",
  "White bean soup simmered with a whole rosemary branch and whole garlic cloves tastes like a sunny hillside.",
  "Chickpea stew--cocido--simmered with saffron, chorizo, and spinach warms you from the toes up.",
  "Gazpacho blanco--ajoblanco--blends blanched almonds, garlic, bread, olive oil, and sherry vinegar into chilled white silk served with green grapes.",
  "Vichyssoise was invented by Chef Louis Diat, who chilled his mother's hot potato-leek soup with cream on a hot summer day.",
  "Senate bean soup has been on the menu every single day for a century: navy beans, smoked ham hock, mashed potatoes, and onion.",
  "She-crab soup from the lowcountry enriches pale crab stock with cream, mace, and a splash of dry sherry at the table.",
  "Brunswick stew simmers pulled smoked pork, lima beans, corn, okra, and tomatoes until the spoon practically stands up.",
  "Burgoo from Kentucky takes whatever meats and garden vegetables the neighbors bring and simmers them in a forty-gallon kettle.",
  "Booyah stew from the northern lakes is stirred with wooden paddles the size of canoe oars for two days straight.",
  "Jambalaya cooks the rice directly in the seasoned stock with trinity, sausage, and shrimp; gumbo serves the rice on top.",
  "Etouffee means 'smothered'--crawfish or shrimp simmered in a blonde butter roux until the sauce clings to every grain of rice.",
  "Red beans and rice traditionally simmered on Mondays using the Sunday ham bone while the laundry boiled.",
  "Mashing a quarter of the red beans against the pot wall gives Monday red beans their signature creamy gravy.",
  "Hoppin' John simmers black-eyed peas with bacon and rice for New Year's luck, always paired with collard greens and cornbread.",
  "Skillet cornbread requires preheating the cast-iron pan with bacon drippings in the oven until it smokes before pouring the batter.",
  "That loud sizzle when cornbread batter hits a hot iron skillet is the sound of a crispy bottom crust being born.",
  "Whether cornbread should have sugar in the batter is a debate that has lasted longer than the Brothbasin ramparts.",
  "Hushpuppies--deep-fried cornmeal spheres studded with minced onion--were originally tossed to quiet barking hounds around the fish fry.",
  "Spoonbread is so rich with eggs and milk that you scoop it out of the casserole dish with a serving spoon like souffle.",
  "Scrapple slices pan-fried until the cornmeal exterior is wafer-crisp and the inside is soft need a drizzle of maple syrup or hot sauce.",
  "Biscuits and sawmill sausage gravy made with pan drippings, flour, milk, and lots of cracked black pepper will fuel a day of plowing.",
  "Chow-chow pickled green tomato and cabbage relish adds the exact bright acid that rich beans and cornbread crave.",
  "Pimento cheese spread between two slices of country white bread and grilled in butter is the crown jewel of Deli Meadows.",
  "Fried green tomatoes dusted in seasoned cornmeal and buttermilk stay firm and tangy inside their golden crust.",
  "Every recipe in Pantrylia is just a conversation between chefs across generations--add your own note and pass the ladle on!"
]

line_cursor = 0
for m_idx, (mid, mdata) in enumerate(MAPS_DATA.items()):
    mb = mdata['mb']
    portal_coords = {(p['x'], p['y']) for p in mdata['portals']} | {(p['tx'], p['ty']) for p in mdata['portals']} | {(n['x'], n['y']) for n in mdata['npcs']}
    candidates = []
    for y in range(2, mb.h - 2):
        for x in range(2, mb.w - 2):
            t = mb.get(x, y)
            if t in SOLID_TILES or t in (65, 66, 67, 68, 69, 70, 73): continue
            if any(abs(x - px) + abs(y - py) <= 2 for px, py in portal_coords): continue
            candidates.append((x, y))
    is_int = mid.endswith('_inn') or mid.endswith('_mart') or mid.endswith('_lab') or mid.endswith('_cafe') or mid.startswith('gym_')
    target_v = 2 if is_int else 5
    step = max(1, len(candidates) // (target_v + 1))
    for vi in range(min(target_v, len(candidates))):
        vx, vy = candidates[(vi * step + m_idx) % len(candidates)]
        fname = FIRST_NAMES[(m_idx * 7 + vi * 13) % len(FIRST_NAMES)]
        role = ROLES[(m_idx + vi) % len(ROLES)]
        vname = f"{role} {fname}"
        lines = []
        for _ in range(3):
            if line_cursor < len(VILLAGER_LINES_BANK):
                lines.append(VILLAGER_LINES_BANK[line_cursor])
                line_cursor += 1
        night_line = VILLAGER_LINES_BANK[line_cursor % len(VILLAGER_LINES_BANK)]
        line_cursor += 1
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
# 10. SELF-VERIFY PORTAL REACHABILITY, SLIDING-WINDOW SIMILARITY & COLLAPSED DIALOGUE
# ==============================================================================
def verify_world():
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

    mlist = list(MAPS_DATA.values())
    max_same = 0.0
    max_diff = 0.0
    for i in range(len(mlist)):
        for j in range(i + 1, len(mlist)):
            a, b = mlist[i], mlist[j]
            wa, ha, wb, hb = a['w'], a['h'], b['w'], b['h']
            ga = [TILE_ROLES.get(t, 'other') for t in a['mb'].g]
            gb = [TILE_ROLES.get(t, 'other') for t in b['mb'].g]
            ow, oh = min(wa, wb), min(ha, hb)
            best = 0.0
            for dy_a in range(ha - oh + 1):
                for dy_b in range(hb - oh + 1):
                    if dy_a > 0 and dy_b > 0: continue
                    for dx_a in range(wa - ow + 1):
                        for dx_b in range(wb - ow + 1):
                            if dx_a > 0 and dx_b > 0: continue
                            same = 0
                            for y in range(oh):
                                ra = (dy_a + y) * wa + dx_a
                                rb = (dy_b + y) * wb + dx_b
                                for x in range(ow):
                                    if ga[ra + x] == gb[rb + x]:
                                        same += 1
                            s = same / (ow * oh)
                            if s > best: best = s
            if wa == wb and ha == hb:
                if best > max_same: max_same = best
            else:
                if best > max_diff: max_diff = best
            assert best <= 0.50, f"Map similarity {best:.3f} > 0.50 between {a['id']} and {b['id']}"
    print(f"Max same-size similarity: {max_same:.3f}, max sliding-window diff-size similarity: {max_diff:.3f}")

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
    f.write("// PROVENANCE: TRAINERS structure lifted/extended from beatsts-v2.1/src/05_world_and_story.js; maps, quests, and dialogue rebuilt for v2.2.\n\n")
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
