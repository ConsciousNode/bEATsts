// 02_beatsts_data.js - All 151 bEATsts with 8-move level-up learnsets and authored per-species shape parameters
// PROVENANCE: Species names, families, types, base stats, and dex entries lifted/extended from beatsts-v1/src/02_beatsts_data.js;
//             upgraded with 8-move level-up learnsets and per-species 32x32 shape parameters (no ID arithmetic).

function toGba15(hex) {
  const r = parseInt(hex.slice(1,3), 16) & 0xF8;
  const g = parseInt(hex.slice(3,5), 16) & 0xF8;
  const b = parseInt(hex.slice(5,7), 16) & 0xF8;
  return '#' + [r,g,b].map(v => v.toString(16).padStart(2,'0')).join('');
}

// Type-based 8-move level-up learnset builder from authored primary/secondary types + signature moves
const TYPE_MOVE_POOLS = {
  Toasted:   [0, 51, 3, 52, 1, 56, 53, 2, 4, 54],
  Steamed:   [5, 61, 57, 62, 6, 58, 7, 59, 8, 60],
  Fried:     [10, 66, 13, 63, 68, 11, 64, 65, 12, 67],
  Pickled:   [14, 69, 70, 15, 73, 74, 71, 16, 72, 17],
  Spicy:     [18, 75, 80, 21, 78, 19, 77, 76, 20, 79],
  Brothy:    [22, 81, 85, 25, 83, 23, 86, 82, 24, 84],
  Raw:       [26, 87, 89, 28, 88, 27, 91, 29, 90, 92],
  Fermented: [30, 93, 33, 96, 95, 31, 94, 32, 97, 98],
  Sweet:     [34, 99, 36, 100, 35, 101, 104, 37, 102, 103],
  Savory:    [38, 105, 106, 39, 110, 107, 108, 40, 41, 109],
  Chilled:   [42, 111, 45, 116, 43, 113, 112, 44, 114, 115],
  Herbal:    [46, 117, 122, 118, 47, 120, 119, 48, 123, 50, 121]
};

function buildLearnset(types, baseMoves) {
  const seen = new Set(baseMoves);
  const pool = [...baseMoves];
  for (const t of types) {
    for (const m of (TYPE_MOVE_POOLS[t] || [])) {
      if (!seen.has(m)) { seen.add(m); pool.push(m); }
    }
  }
  // Ensure at least 8 moves with progressive levels: 1, 1, 5, 9, 14, 20, 27, 35
  const levels = [1, 1, 5, 9, 14, 20, 27, 35, 42, 48, 'lean_l', 'sleepy'];
  return pool.slice(0, 8).map((id, i) => [levels[i], id]);
}

// Per-species shape archetypes (32x32):
// Bread/Sandwiches: 'slice', 'club', 'sub', 'burger', 'croissant', 'pita', 'waffle', 'bagel', 'scone', 'pretzel', 'muffin', 'taco_open'
// Dumplings: 'bao', 'gyoza', 'shumai', 'onigiri', 'ravioli', 'empanada', 'mochi', 'khinkali', 'takoyaki', 'burek'
// Noodles: 'ramen', 'pho', 'pasta_nest', 'wok_pan', 'lasagna', 'noodle_drake', 'mac_cup', 'soba_mat'
// Soup: 'teacup', 'cauldron', 'bread_bowl', 'tureen', 'clay_pot', 'chili_pot', 'myth_bowl'
const FAMILY_ARCHETYPES = {
  Sandwiches: ['slice','club','sub','burger','croissant','pita','waffle','bagel','scone','pretzel','muffin','taco_open'],
  Dumplings:  ['bao','gyoza','shumai','onigiri','ravioli','empanada','mochi','khinkali','takoyaki','burek'],
  Noodles:    ['ramen','pho','pasta_nest','wok_pan','lasagna','noodle_drake','mac_cup','soba_mat'],
  Soup:       ['teacup','cauldron','bread_bowl','tureen','clay_pot','chili_pot']
};

// [id, name, family, types, [hp,atk,def,spd], catchRate, evoTo, evoLv, baseMoves, dex, nightOnly, minTier, arch, sizeMod, limb, top, side]
const RAW_BEATSTS = [
  // === SANDWICHES (#1 - #38) ===
  [1,  'Crustling',     'Sandwiches', ['Toasted'],             [52,55,50,55], 0.42, 2,  16, [0,3,38,26],   'A cheerful heel of sourdough that refuses to be left in the bag.', false, 1, 'slice', 0, 'stub', 'flag', 'none', 'wide', 'happy'],
  [2,  'Paninipup',     'Sandwiches', ['Toasted','Savory'],    [72,78,70,72], 0.25, 3,  32, [0,1,38,39],   'Its grill marks glow warm when it hears a toaster ding.', false, 1, 'slice', 1, 'paws', 'grill', 'tail', 'high', 'wide'],
  [3,  'Clubbehemoth',  'Sandwiches', ['Toasted','Savory'],    [98,105,95,82],0.12, null,null,[1,2,39,41],  'Three stories of toasted brioche held together by a heroic toothpick.', false, 2, 'club', 2, 'heavy', 'skewer', 'cape', 'low', 'sleepy'],
  [4,  'Baguettebit',   'Sandwiches', ['Toasted','Raw'],       [48,60,45,68], 0.40, 5,  18, [0,26,28,3],   'Long, crunchy, and surprisingly aerodynamic when startled.', false, 1, 'sub', 0, 'stub', 'leaf', 'none', 'center', 'happy'],
  [5,  'Submariner',    'Sandwiches', ['Toasted','Pickled'],   [82,88,78,78], 0.20, null,null,[1,14,15,28], 'Patrols deli counters with a crew of crisp banana peppers.', false, 2, 'sub', 2, 'fins', 'periscope', 'fins', 'lean_l', 'wide'],
  [6,  'Pbnjinx',       'Sandwiches', ['Sweet','Savory'],      [55,52,55,60], 0.38, 7,  20, [34,36,38,0],  'Sticky on one side, nutty on the other, endlessly chaotic.', false, 1, 'slice', 0, 'arms', 'drip', 'wings', 'tall', 'fierce'],
  [7,  'Nutterstack',   'Sandwiches', ['Sweet','Toasted'],     [85,84,82,74], 0.18, null,null,[34,35,1,39],  'Can glue a runaway shopping cart to the floor with one paw.', false, 2, 'club', 1, 'heavy', 'drip', 'arms', 'right', 'round'],
  [8,  'Briekeeper',    'Sandwiches', ['Fermented','Toasted'], [60,54,70,48], 0.35, 9,  24, [30,32,0,38],  'Guards a warm wheel of melted cheese inside flaky ciabatta.', false, 1, 'muffin', 0, 'stub', 'crown', 'shield', 'low', 'wide'],
  [9,  'Fonduefort',    'Sandwiches', ['Fermented','Savory'],  [95,82,102,58],0.16, null,null,[32,33,39,4],  'An armored grilled-cheese bastion that oozes comforting cheddar.', false, 2, 'club', 2, 'heavy', 'crown', 'shield', 'high', 'fierce'],
  [10, 'Picklewick',    'Sandwiches', ['Pickled','Raw'],       [50,58,52,65], 0.40, 11, 19, [14,15,26,28], 'Smells faintly of dill and insists every sandwich needs crunch.', false, 1, 'scone', 0, 'bounce', 'dill', 'none', 'lean_r', 'round'],
  [11, 'Reubenrex',     'Sandwiches', ['Pickled','Fermented'], [90,94,85,68], 0.16, null,null,[15,16,31,41], 'Roars with tangy sauerkraut energy and marbled rye armor.', false, 2, 'burger', 2, 'heavy', 'horns', 'tail', 'left', 'sleepy'],
  [12, 'Croissnap',     'Sandwiches', ['Toasted','Sweet'],     [50,62,46,76], 0.36, 13, 22, [0,34,35,3],   'Sheds golden buttery flakes whenever it performs a backflip.', false, 1, 'croissant', 0, 'paws', 'sugar', 'wings', 'wide', 'happy'],
  [13, 'Briocheduke',   'Sandwiches', ['Toasted','Sweet'],     [80,90,74,92], 0.16, null,null,[1,4,35,37],   'Wears a powdered-sugar cape and bows to every bakery oven.', false, 2, 'croissant', 2, 'arms', 'crown', 'cape', 'high', 'round'],
  [14, 'Bltease',       'Sandwiches', ['Savory','Raw'],        [56,64,52,66], 0.35, 15, 22, [38,26,28,0],  'Its crispy bacon ears twitch at the sound of sizzling pans.', false, 1, 'slice', 0, 'paws', 'ears', 'none', 'right', 'sleepy'],
  [15, 'Deliknight',    'Sandwiches', ['Savory','Toasted'],    [86,96,86,76], 0.15, null,null,[39,41,1,2],   'Wields a giant wooden skewer and defends lunchtime honor.', false, 2, 'club', 2, 'arms', 'skewer', 'shield', 'center', 'happy'],
  [16, 'Falafelfin',    'Sandwiches', ['Fried','Herbal'],      [54,62,56,64], 0.36, 17, 23, [10,46,47,13], 'Tucked inside a warm pita pocket, smelling of parsley and cumin.', false, 1, 'pita', 0, 'fins', 'leaf', 'none', 'lean_l', 'wide'],
  [17, 'Pitapaladin',   'Sandwiches', ['Fried','Herbal'],      [84,90,88,78], 0.16, null,null,[11,12,47,50], 'Throws crispy chickpea shields that return like boomerangs.', false, 2, 'pita', 2, 'arms', 'leaf', 'shield', 'lean_r', 'fierce'],
  [18, 'Tostadito',     'Sandwiches', ['Fried','Spicy'],       [48,68,45,74], 0.38, 19, 21, [10,18,19,13], 'A crunchy open-faced tortilla creature with a jalapeno crest.', false, 1, 'taco_open', 0, 'stub', 'chili', 'none', 'right', 'happy'],
  [19, 'Tortatitan',    'Sandwiches', ['Fried','Spicy'],       [88,98,80,75], 0.15, null,null,[11,12,19,20], 'Stacked with avocado, beans, and a fiery salsa aura.', false, 2, 'burger', 2, 'heavy', 'chili', 'arms', 'low', 'wide'],
  [20, 'Sconeimp',      'Sandwiches', ['Sweet','Chilled'],     [58,50,60,56], 0.36, 21, 20, [34,42,45,36], 'Clotted cream and jam sit neatly atop its flaky little head.', false, 1, 'scone', 0, 'stub', 'cream', 'wings', 'center', 'fierce'],
  [21, 'Teatimearch',   'Sandwiches', ['Herbal','Chilled'],    [88,76,90,78], 0.16, null,null,[46,48,43,37], 'Crustless cucumber-mint royalty that insists on polite duels.', false, 2, 'scone', 2, 'arms', 'crown', 'cape', 'lean_r', 'round'],
  [22, 'Bagelboing',    'Sandwiches', ['Steamed','Toasted'],   [58,56,62,62], 0.35, 23, 24, [5,0,3,38],    'Boiled then baked, it bounces through towns like a chewy wheel.', false, 1, 'bagel', 0, 'bounce', 'seeds', 'none', 'tall', 'sleepy'],
  [23, 'Loxwarden',     'Sandwiches', ['Raw','Fermented'],     [84,88,80,84], 0.16, null,null,[27,28,30,15], 'Caper-studded guardian of Sunday brunch tables.', false, 2, 'bagel', 2, 'arms', 'dill', 'fins', 'low', 'fierce'],
  [24, 'Meltmoth',      'Sandwiches', ['Toasted','Spicy'],     [55,66,52,70], 0.32, null,null,[1,18,19,4],   'Flutters around heat lamps seeking gooey pepper-jack cheese.', false, 1, 'croissant', 1, 'none', 'antennae', 'wings', 'left', 'round'],
  [25, 'Midnitoast',    'Sandwiches', ['Toasted','Chilled'],   [75,85,72,88], 0.20, null,null,[2,4,42,45],   'Only appears after midnight when someone craves buttered toast.', true, 2, 'slice', 1, 'float', 'moon', 'aura', 'high', 'sleepy'],
  [26, 'Slidersprout',  'Sandwiches', ['Savory','Raw'],        [46,56,48,72], 0.42, 27, 17, [38,26,0,28],  'Tiny but mighty, three of them often travel in a cardboard box.', false, 1, 'burger', 0, 'stub', 'flag', 'none', 'lean_r', 'happy'],
  [27, 'Pattygoon',     'Sandwiches', ['Savory','Fried'],      [85,95,82,70], 0.18, null,null,[39,41,11,13], 'Double-seared smashburger spirit with melty cheddar eyebrows.', false, 2, 'burger', 2, 'heavy', 'grill', 'arms', 'lean_l', 'wide'],
  [28, 'Banhibun',      'Sandwiches', ['Pickled','Herbal'],    [64,74,60,92], 0.24, null,null,[15,16,46,47], 'Crackling baguette crust packed with pickled carrot and cilantro.', false, 2, 'sub', 1, 'paws', 'leaf', 'tail', 'high', 'sleepy'],
  [29, 'Cubanocrab',    'Sandwiches', ['Toasted','Pickled'],   [78,88,84,74], 0.20, null,null,[1,2,15,39],   'Pressed flat and crisp, snaps its mustard-coated claws.', false, 2, 'taco_open', 1, 'claws', 'grill', 'claws', 'left', 'happy'],
  [30, 'Wafflewisp',    'Sandwiches', ['Sweet','Fried'],       [68,80,64,82], 0.24, null,null,[34,35,10,11], 'Holds pools of maple syrup inside every square pocket.', false, 2, 'waffle', 1, 'float', 'drip', 'wings', 'low', 'wide'],
  [31, 'Avotoast',      'Sandwiches', ['Raw','Toasted'],       [70,74,72,76], 0.25, null,null,[26,29,0,46],  'Sprinkled with chili flakes and sea salt; surprisingly pricey.', false, 2, 'slice', 1, 'paws', 'chili', 'none', 'center', 'fierce'],
  [32, 'Pretzelbun',    'Sandwiches', ['Savory','Fermented'],  [76,80,86,62], 0.22, null,null,[38,30,32,1],  'Twisted, glossy, and studded with coarse salt crystals.', false, 2, 'pretzel', 1, 'stub', 'seeds', 'none', 'lean_l', 'round'],
  [33, 'Focacciafox',   'Sandwiches', ['Herbal','Toasted'],    [74,78,76,86], 0.22, null,null,[46,47,1,4],   'Dimpled with olive oil and rosemary sprigs along its tail.', false, 2, 'waffle', 1, 'paws', 'ears', 'tail', 'left', 'wide'],
  [34, 'Smoreling',     'Sandwiches', ['Sweet','Toasted'],     [62,72,58,74], 0.28, null,null,[34,35,36,4],  'Toasted marshmallow peeks out from two graham-cracker wings.', false, 1, 'waffle', 0, 'stub', 'cream', 'wings', 'right', 'fierce'],
  [35, 'Muffinmite',    'Sandwiches', ['Toasted','Savory'],    [58,64,66,58], 0.30, null,null,[0,3,38,39],   'An English muffin scout with a perfectly round egg hat.', false, 1, 'muffin', 0, 'paws', 'egg', 'none', 'low', 'round'],
  [36, 'Po-boyhopper',  'Sandwiches', ['Fried','Pickled'],     [78,86,74,80], 0.20, null,null,[11,12,15,16], 'Leaps across bayous carrying crispy shrimp and remoulade.', false, 2, 'sub', 1, 'bounce', 'dill', 'tail', 'high', 'sleepy'],
  [37, 'Monte-cristo',  'Sandwiches', ['Fried','Sweet'],       [82,86,78,80], 0.18, null,null,[11,35,37,1],  'Dusted in powdered sugar and dipped in berry jam.', false, 3, 'club', 1, 'arms', 'sugar', 'cape', 'lean_r', 'happy'],
  [38, 'Sourdoughon',   'Sandwiches', ['Fermented','Toasted'], [102,94,98,66],0.12, null,null,[32,33,4,41],  'Ancient starter spirit whose loaves have been baking for centuries.', false, 3, 'muffin', 2, 'heavy', 'horns', 'aura', 'lean_r', 'round'],

  // === DUMPLINGS (#39 - #76) ===
  [39, 'Doughbit',      'Dumplings',  ['Steamed'],             [54,50,55,54], 0.42, 40, 16, [5,6,9,38],    'A squishy pinched parcel that giggles when poked.', false, 1, 'bao', 0, 'stub', 'knot', 'none', 'high', 'sleepy'],
  [40, 'Baobouncer',    'Dumplings',  ['Steamed','Savory'],    [76,72,76,68], 0.25, 41, 32, [5,6,7,39],    'Bounces off bamboo walls with a fluffy char-siu heart.', false, 1, 'bao', 1, 'bounce', 'knot', 'arms', 'left', 'happy'],
  [41, 'Steamlord',     'Dumplings',  ['Steamed','Brothy'],    [104,92,98,76],0.12, null,null,[6,7,8,24],   'Wreathed in aromatic mist; a single sigh warms an entire kitchen.', false, 2, 'bao', 2, 'heavy', 'steam', 'aura', 'high', 'wide'],
  [42, 'Gyozapup',      'Dumplings',  ['Fried','Steamed'],     [50,62,48,68], 0.38, 43, 20, [10,13,5,6],   'Crispy skirt on the bottom, soft pleated hood on top.', false, 1, 'gyoza', 0, 'paws', 'pleat', 'tail', 'center', 'fierce'],
  [43, 'Potsticking',   'Dumplings',  ['Fried','Savory'],      [84,96,78,82], 0.16, null,null,[11,12,39,41], 'Skates across cast-iron skillets leaving golden lace trails.', false, 2, 'gyoza', 2, 'arms', 'horns', 'cape', 'lean_l', 'happy'],
  [44, 'Pierogipuff',   'Dumplings',  ['Steamed','Fried'],     [62,56,64,50], 0.36, 45, 22, [5,10,38,39],  'Stuffed with mashed potato and cheddar; loves caramelized onions.', false, 1, 'empanada', 0, 'stub', 'pleat', 'none', 'wide', 'wide'],
  [45, 'Varenikivalk',  'Dumplings',  ['Fried','Sweet'],       [90,88,86,68], 0.16, null,null,[11,35,37,41], 'Sings folk songs while sizzling gently in brown butter.', false, 2, 'empanada', 2, 'arms', 'crown', 'wings', 'lean_l', 'fierce'],
  [46, 'Xiaolongpop',   'Dumplings',  ['Brothy','Steamed'],    [52,58,50,64], 0.36, 47, 24, [22,23,5,6],   'Holds a tiny ocean of hot soup inside delicate 18-pleat skin.', false, 1, 'khinkali', 0, 'stub', 'knot', 'none', 'low', 'round'],
  [47, 'Soupbaoruler',  'Dumplings',  ['Brothy','Savory'],     [88,92,84,76], 0.15, null,null,[23,24,39,40], 'Commands respect and careful spoon-and-ginger technique.', false, 2, 'khinkali', 2, 'heavy', 'crown', 'aura', 'center', 'sleepy'],
  [48, 'Wontonwisp',    'Dumplings',  ['Brothy','Herbal'],     [48,56,46,78], 0.38, 49, 21, [22,25,46,47], 'Floats gracefully like a silk lantern in scallion broth.', false, 1, 'mochi', 0, 'float', 'leaf', 'wings', 'lean_r', 'fierce'],
  [49, 'Wontonwarden',  'Dumplings',  ['Brothy','Spicy'],      [78,88,72,92], 0.16, null,null,[23,24,19,20], 'Swims through chili-oil rapids without spilling a drop.', false, 2, 'mochi', 2, 'float', 'chili', 'cape', 'left', 'round'],
  [50, 'Raviolirook',   'Dumplings',  ['Savory','Herbal'],     [56,60,58,58], 0.36, 51, 23, [38,39,46,47], 'Square, ruffled, and stuffed with spinach and ricotta.', false, 1, 'ravioli', 0, 'stub', 'leaf', 'none', 'right', 'sleepy'],
  [51, 'Tortelliniking','Dumplings',  ['Savory','Brothy'],     [88,90,88,74], 0.16, null,null,[39,41,23,24], 'Wears a tiny pasta crown and rules the Sunday soup pot.', false, 2, 'ravioli', 2, 'arms', 'crown', 'shield', 'left', 'happy'],
  [52, 'Empanadash',    'Dumplings',  ['Fried','Spicy'],       [54,66,52,72], 0.35, 53, 23, [10,13,18,19], 'Crimped edges spin like a wheel as it dashes across sands.', false, 1, 'empanada', 1, 'bounce', 'chili', 'tail', 'high', 'wide'],
  [53, 'Samosasage',    'Dumplings',  ['Fried','Herbal'],      [84,94,82,80], 0.16, null,null,[11,12,47,50], 'Triangular philosopher filled with spiced peas and tamarind.', false, 2, 'onigiri', 2, 'arms', 'steam', 'aura', 'lean_r', 'sleepy'],
  [54, 'Mochimite',     'Dumplings',  ['Sweet','Steamed'],     [52,48,54,68], 0.40, 55, 18, [34,36,5,9],   'Squishy pounded-rice sprite that sticks to your cheek.', false, 1, 'mochi', 0, 'bounce', 'sugar', 'none', 'lean_l', 'happy'],
  [55, 'Daifukuduke',   'Dumplings',  ['Sweet','Chilled'],     [84,78,82,82], 0.18, null,null,[35,37,42,44], 'Hides a whole sweet strawberry inside cool snow-skin mochi.', false, 2, 'mochi', 1, 'arms', 'cream', 'cape', 'wide', 'wide'],
  [56, 'Momomaven',     'Dumplings',  ['Steamed','Spicy'],     [68,78,66,76], 0.25, null,null,[6,7,18,19],   'Twisted Himalayan dumpling with a fiery tomato-achar dip.', false, 2, 'khinkali', 1, 'paws', 'chili', 'none', 'left', 'fierce'],
  [57, 'Manduman',      'Dumplings',  ['Fermented','Steamed'], [74,80,74,70], 0.24, null,null,[30,31,6,7],   'Stuffed with tangy kimchi and glass noodles.', false, 2, 'gyoza', 1, 'heavy', 'pleat', 'arms', 'low', 'round'],
  [58, 'Har-gaohawk',   'Dumplings',  ['Steamed','Raw'],       [64,78,60,92], 0.24, null,null,[5,6,27,28],   'Translucent shrimp dumpling that darts like a crystal dart.', false, 2, 'empanada', 1, 'none', 'ears', 'wings', 'lean_r', 'wide'],
  [59, 'Shumaishire',   'Dumplings',  ['Steamed','Savory'],    [72,82,76,68], 0.24, null,null,[6,7,38,39],   'Open-topped golden basket crowned with a single bright pea.', false, 2, 'shumai', 1, 'stub', 'egg', 'none', 'lean_l', 'fierce'],
  [60, 'Gnocchigoblin', 'Dumplings',  ['Herbal','Fried'],      [66,76,68,78], 0.26, null,null,[46,47,10,11], 'Pillowy potato nugget that dances in crispy sage butter.', false, 2, 'takoyaki', 0, 'paws', 'ears', 'tail', 'tall', 'round'],
  [61, 'Matzoball',     'Dumplings',  ['Brothy','Steamed'],    [92,72,94,48], 0.22, null,null,[22,23,6,9],   'Either a dense sinker or a fluffy floater—nobody agrees.', false, 2, 'takoyaki', 2, 'float', 'steam', 'none', 'right', 'sleepy'],
  [62, 'Moonbun',       'Dumplings',  ['Sweet','Fermented'],   [78,82,80,84], 0.18, null,null,[35,37,30,32], 'Embossed with lunar patterns; emerges under starlight.', true, 2, 'burek', 1, 'float', 'moon', 'aura', 'tall', 'happy'],
  [63, 'Kreplachcub',   'Dumplings',  ['Brothy','Savory'],     [62,70,64,66], 0.28, null,null,[22,23,38,39], 'Three-cornered pocket of braised brisket and pepper.', false, 1, 'onigiri', 1, 'paws', 'ears', 'tail', 'high', 'round'],
  [64, 'Pelmenipack',   'Dumplings',  ['Chilled','Savory'],    [72,80,74,74], 0.24, null,null,[42,45,38,39], 'Swims in sour cream and dill; loves snowy winter routes.', false, 2, 'ravioli', 1, 'paws', 'dill', 'none', 'lean_r', 'sleepy'],
  [65, 'Khinkalikhan',  'Dumplings',  ['Brothy','Spicy'],      [88,92,82,72], 0.18, null,null,[23,24,18,21], 'Hold it by the topknot—never let the peppery broth escape!', false, 3, 'khinkali', 2, 'heavy', 'horns', 'cape', 'tall', 'happy'],
  [66, 'Tamaletoast',   'Dumplings',  ['Steamed','Spicy'],     [80,84,82,64], 0.22, null,null,[6,8,18,19],   'Wrapped snugly in a corn husk jacket, warm and masa-soft.', false, 2, 'shumai', 2, 'arms', 'leaf', 'cape', 'high', 'wide'],
  [67, 'Aranciniace',   'Dumplings',  ['Fried','Savory'],      [74,88,78,72], 0.22, null,null,[11,12,39,40], 'Golden risotto sphere hiding a molten mozzarella core.', false, 2, 'takoyaki', 1, 'arms', 'flag', 'shield', 'left', 'fierce'],
  [68, 'Takoyakitot',   'Dumplings',  ['Fried','Brothy'],      [68,78,66,82], 0.25, null,null,[10,13,22,25], 'Waves its bonito-flake plumes whenever brushed with sauce.', false, 2, 'takoyaki', 0, 'bounce', 'drip', 'fins', 'high', 'happy'],
  [69, 'Onigiriowl',    'Dumplings',  ['Raw','Pickled'],       [66,74,70,78], 0.26, null,null,[26,28,14,15], 'Crisp nori vest and a tart pickled-plum surprise inside.', false, 1, 'onigiri', 1, 'none', 'ears', 'wings', 'center', 'wide'],
  [70, 'Tangyuantiny',  'Dumplings',  ['Sweet','Brothy'],      [64,66,68,74], 0.28, null,null,[34,36,22,25], 'Glutinous rice pearl filled with warm black sesame paste.', false, 1, 'mochi', 0, 'float', 'steam', 'none', 'lean_l', 'fierce'],
  [71, 'Burekbeetle',   'Dumplings',  ['Toasted','Fermented'], [82,84,88,62], 0.20, null,null,[1,2,30,32],   'Spiraled phyllo shell stuffed with tangy feta and spinach.', false, 2, 'burek', 2, 'claws', 'horns', 'shield', 'wide', 'round'],
  [72, 'Pastelpip',     'Dumplings',  ['Fried','Pickled'],     [66,76,62,84], 0.26, null,null,[10,13,14,15], 'Blistered crispy pocket that pairs best with lime juice.', false, 2, 'ravioli', 1, 'bounce', 'dill', 'none', 'right', 'sleepy'],
  [73, 'Knishknight',   'Dumplings',  ['Toasted','Savory'],    [86,82,90,56], 0.20, null,null,[1,3,39,41],   'Dense baked potato-and-onion defender of the bakery.', false, 2, 'burek', 1, 'heavy', 'crown', 'shield', 'low', 'fierce'],
  [74, 'Modakmonk',     'Dumplings',  ['Sweet','Herbal'],      [72,74,76,78], 0.22, null,null,[35,36,46,48], 'Steamed coconut-jaggery dumpling scented with cardamom.', false, 2, 'bao', 1, 'float', 'leaf', 'aura', 'center', 'round'],
  [75, 'Coxinhacrest',  'Dumplings',  ['Fried','Savory'],      [74,86,72,82], 0.22, null,null,[11,13,38,39], 'Teardrop-shaped golden croquette with a creamy heart.', false, 2, 'khinkali', 1, 'paws', 'flag', 'tail', 'lean_r', 'sleepy'],
  [76, 'Dimpaledon',    'Dumplings',  ['Steamed','Fried'],     [100,98,94,74],0.12, null,null,[7,8,11,12],   'Commands a rolling dim-sum cart loaded with bamboo tiers.', false, 3, 'shumai', 2, 'heavy', 'crown', 'arms', 'tall', 'happy'],

  // === NOODLES (#77 - #114) ===
  [77, 'Slurplet',      'Noodles',    ['Brothy'],              [50,54,48,64], 0.42, 78, 16, [22,23,38,5],  'A wiggly wheat noodle that swims happily in soy-ginger stock.', false, 1, 'ramen', 0, 'stub', 'steam', 'none', 'right', 'wide'],
  [78, 'Udonox',        'Noodles',    ['Brothy','Savory'],     [78,76,74,70], 0.25, 79, 32, [22,23,39,41], 'Thick, bouncy, and proud of its chewy al-dente posture.', false, 1, 'ramen', 1, 'heavy', 'horns', 'arms', 'left', 'sleepy'],
  [79, 'Ramenrex',      'Noodles',    ['Brothy','Spicy'],      [98,104,88,88],0.12, null,null,[23,24,19,20], 'Crowned with chashu, ajitama egg, and roaring tonkotsu steam.', false, 2, 'ramen', 2, 'heavy', 'egg', 'tail', 'high', 'happy'],
  [80, 'Spaghettik',    'Noodles',    ['Herbal','Savory'],     [52,58,50,66], 0.40, 81, 18, [46,47,38,39], 'Twirls itself into neat nests atop a splash of marinara.', false, 1, 'pasta_nest', 0, 'stub', 'leaf', 'none', 'lean_r', 'wide'],
  [81, 'Bolognesaur',   'Noodles',    ['Savory','Herbal'],     [86,92,80,74], 0.18, null,null,[39,41,47,50], 'Simmered for six hours; its parmesan snow never melts.', false, 2, 'pasta_nest', 2, 'heavy', 'drip', 'tail', 'lean_l', 'fierce'],
  [82, 'Sobasprite',    'Noodles',    ['Chilled','Herbal'],    [50,56,52,78], 0.38, 83, 21, [42,45,46,48], 'Buckwheat strands resting on a cool bamboo mat.', false, 1, 'soba_mat', 0, 'float', 'leaf', 'none', 'wide', 'round'],
  [83, 'Zaruzephyr',    'Noodles',    ['Chilled','Pickled'],   [78,86,74,98], 0.16, null,null,[43,44,14,15], 'Dashes like a mountain breeze with wasabi and tsuyu.', false, 2, 'soba_mat', 2, 'float', 'dill', 'wings', 'left', 'wide'],
  [84, 'Phophantom',    'Noodles',    ['Brothy','Herbal'],     [56,58,54,72], 0.35, 85, 24, [22,25,46,47], 'Fragrant with star anise, cinnamon, and fresh Thai basil.', false, 1, 'pho', 0, 'float', 'leaf', 'aura', 'low', 'fierce'],
  [85, 'Phophenix',     'Noodles',    ['Brothy','Spicy'],      [88,94,80,90], 0.15, null,null,[23,24,19,50], 'Rises from simmering bone broth with lime and chili heat.', false, 2, 'pho', 2, 'none', 'chili', 'wings', 'center', 'round'],
  [86, 'Padthaitail',   'Noodles',    ['Fried','Sweet'],       [54,62,50,74], 0.36, 87, 22, [10,13,34,35], 'Tamarind-tangy rice noodles topped with crushed peanuts.', false, 1, 'wok_pan', 0, 'paws', 'seeds', 'tail', 'lean_l', 'sleepy'],
  [87, 'Wokwyvern',     'Noodles',    ['Fried','Spicy'],       [84,98,76,92], 0.15, null,null,[11,12,19,20], 'Breathes smoky wok-hei flames over screaming-hot skillets.', false, 2, 'wok_pan', 2, 'claws', 'horns', 'wings', 'left', 'happy'],
  [88, 'Macncheep',     'Noodles',    ['Savory','Toasted'],    [58,54,62,54], 0.38, 89, 20, [38,39,0,1],   'A bubbly elbow-pasta chick with a golden breadcrumb crest.', false, 1, 'mac_cup', 0, 'stub', 'drip', 'wings', 'right', 'round'],
  [89, 'Cheddargon',    'Noodles',    ['Toasted','Savory'],    [92,88,92,66], 0.16, null,null,[1,4,39,41],   'Baked in a cast-iron dish with three cheeses and crispy edges.', false, 2, 'mac_cup', 2, 'heavy', 'horns', 'tail', 'low', 'sleepy'],
  [90, 'Kimchiudon',    'Noodles',    ['Fermented','Spicy'],   [58,66,56,66], 0.34, 91, 24, [30,31,18,19], 'Tangy, fiery, and fueled by aged cabbage probiotics.', false, 1, 'ramen', 1, 'bounce', 'chili', 'none', 'high', 'happy'],
  [91, 'Jajanggiant',   'Noodles',    ['Fermented','Savory'],  [94,96,86,70], 0.15, null,null,[31,32,39,41], 'Coated in glossy black-bean sauce and diced crispy pork.', false, 2, 'pasta_nest', 2, 'heavy', 'drip', 'arms', 'lean_r', 'wide'],
  [92, 'Glassnood',     'Noodles',    ['Raw','Pickled'],       [50,58,48,80], 0.36, 93, 21, [26,28,14,15], 'Nearly invisible sweet-potato noodles tossed in sesame oil.', false, 1, 'soba_mat', 0, 'float', 'seeds', 'tail', 'tall', 'fierce'],
  [93, 'Japchaejay',    'Noodles',    ['Savory','Raw'],        [80,88,76,92], 0.16, null,null,[39,40,27,29], 'Sparkles with colorful bell peppers, shiitake, and spinach.', false, 2, 'wok_pan', 1, 'none', 'leaf', 'wings', 'wide', 'happy'],
  [94, 'Pestopixie',    'Noodles',    ['Herbal','Raw'],        [64,78,62,88], 0.24, null,null,[46,47,48,28], 'Bright emerald basil coats every corkscrew fusilli curl.', false, 2, 'pasta_nest', 0, 'float', 'leaf', 'wings', 'left', 'wide'],
  [95, 'Carbonarakid',  'Noodles',    ['Savory','Toasted'],    [74,88,76,78], 0.22, null,null,[38,39,40,1],  'Silky pecorino-and-egg emulsion with cracked black pepper.', false, 2, 'pasta_nest', 1, 'paws', 'egg', 'none', 'high', 'fierce'],
  [96, 'Lasagnalion',   'Noodles',    ['Toasted','Savory'],    [96,90,94,60], 0.16, null,null,[1,2,39,41],   'Seven proud layers of pasta, ragu, and bubbly bechamel.', false, 3, 'lasagna', 2, 'heavy', 'ears', 'tail', 'right', 'round'],
  [97, 'Dan-dan-dart',  'Noodles',    ['Spicy','Savory'],      [70,92,66,88], 0.22, null,null,[18,19,20,39], 'Numbs foes with Sichuan peppercorn and sesame-chili paste.', false, 2, 'pho', 1, 'paws', 'chili', 'tail', 'high', 'sleepy'],
  [98, 'Midniteramen',  'Noodles',    ['Brothy','Fermented'],  [82,88,78,86], 0.18, null,null,[23,24,30,32], 'Steams quietly under neon streetlamps at 2:00 AM.', true, 2, 'ramen', 1, 'float', 'moon', 'aura', 'left', 'fierce'],
  [99, 'Laksalynx',     'Noodles',    ['Spicy','Brothy'],      [76,88,72,88], 0.20, null,null,[19,20,23,24], 'Rich coconut-curry broth with puffy tofu and bean sprouts.', false, 2, 'pho', 1, 'paws', 'ears', 'tail', 'right', 'round'],
  [100,'Orzootter',     'Noodles',    ['Herbal','Chilled'],    [68,72,70,84], 0.26, null,null,[46,48,42,43], 'Tiny rice-shaped pasta that swims in lemon-dill salad.', false, 2, 'soba_mat', 1, 'fins', 'dill', 'tail', 'low', 'sleepy'],
  [101,'Yakisobayak',   'Noodles',    ['Fried','Pickled'],     [78,88,76,78], 0.22, null,null,[11,13,14,15], 'Sizzles on festival griddles with pickled red ginger horns.', false, 2, 'wok_pan', 2, 'heavy', 'horns', 'none', 'center', 'happy'],
  [102,'Pappardel',     'Noodles',    ['Savory','Herbal'],     [84,86,82,72], 0.20, null,null,[39,40,47,50], 'Wide ribbons draped in slow-braised wild mushroom ragu.', false, 2, 'lasagna', 1, 'arms', 'leaf', 'cape', 'lean_r', 'wide'],
  [103,'Vermicelif',    'Noodles',    ['Raw','Herbal'],        [62,74,60,90], 0.26, null,null,[26,28,46,47], 'Delicate rice threads topped with mint, cucumber, and lime.', false, 1, 'soba_mat', 1, 'float', 'leaf', 'wings', 'tall', 'sleepy'],
  [104,'Spaetzleimp',   'Noodles',    ['Toasted','Fermented'], [72,80,76,74], 0.24, null,null,[0,1,30,32],   'Nubby little dumplings-meets-noodles browned in butter.', false, 2, 'mac_cup', 1, 'bounce', 'ears', 'none', 'right', 'happy'],
  [105,'Cacioepepe',    'Noodles',    ['Savory','Spicy'],      [72,84,74,82], 0.24, null,null,[38,39,18,21], 'Proof that three ingredients—pasta, cheese, pepper—win wars.', false, 2, 'pasta_nest', 1, 'arms', 'seeds', 'shield', 'left', 'wide'],
  [106,'Lo-meinlemur',   'Noodles',    ['Fried','Savory'],      [74,84,70,86], 0.24, null,null,[10,13,38,39], 'Swings from scallion vines in a glossy soy-sesame coat.', false, 2, 'wok_pan', 1, 'paws', 'ears', 'tail', 'high', 'fierce'],
  [107,'Kugelkoala',    'Noodles',    ['Sweet','Toasted'],     [82,76,84,60], 0.22, null,null,[34,35,1,4],   'Baked egg-noodle pudding with cinnamon-raisin ears.', false, 2, 'lasagna', 1, 'stub', 'ears', 'none', 'lean_r', 'round'],
  [108,'Coldsesame',    'Noodles',    ['Chilled','Savory'],    [70,78,72,84], 0.24, null,null,[42,43,38,39], 'Nutty, cool, and topped with crisp julienned cucumber.', false, 2, 'soba_mat', 1, 'paws', 'seeds', 'none', 'lean_l', 'wide'],
  [109,'Chowfunfin',    'Noodles',    ['Fried','Brothy'],      [76,86,74,82], 0.22, null,null,[11,13,22,23], 'Wide rice ribbons seared in high-flame wok gravy.', false, 2, 'wok_pan', 1, 'fins', 'steam', 'fins', 'wide', 'fierce'],
  [110,'Penneporcup',   'Noodles',    ['Spicy','Toasted'],     [72,86,78,74], 0.24, null,null,[18,19,0,1],   'Tube-shaped arrabbiata warrior bristling with chili flakes.', false, 2, 'mac_cup', 1, 'paws', 'chili', 'tail', 'left', 'round'],
  [111,'Stroganowl',    'Noodles',    ['Savory','Fermented'],  [82,84,80,72], 0.20, null,null,[39,40,30,32], 'Egg noodles nestled in tangy sour-cream mushroom sauce.', false, 2, 'lasagna', 1, 'none', 'ears', 'wings', 'high', 'sleepy'],
  [112,'Fideuafin',     'Noodles',    ['Toasted','Brothy'],    [78,86,76,80], 0.20, null,null,[1,2,23,24],   'Short toasted pasta crisped in saffron seafood stock.', false, 2, 'wok_pan', 1, 'fins', 'grill', 'tail', 'center', 'happy'],
  [113,'Bihonbee',      'Noodles',    ['Raw','Fried'],         [66,78,64,90], 0.26, null,null,[26,28,10,13], 'Golden pancit threads zipping around with calamansi zest.', false, 2, 'noodle_drake', 0, 'none', 'antennae', 'wings', 'lean_l', 'round'],
  [114,'Noodledrake',   'Noodles',    ['Brothy','Fried'],      [96,100,88,92],0.12, null,null,[24,12,20,41], 'A colossal golden dragon woven from hand-pulled longevity noodles.', false, 3, 'noodle_drake', 2, 'claws', 'horns', 'wings', 'tall', 'sleepy'],

  // === SOUP (#115 - #150) ===
  [115,'Dripdrop',      'Soup',       ['Brothy'],              [54,48,54,56], 0.42, 116,16, [22,25,38,46], 'A polite teacup of clear consomme with a single parsley leaf.', false, 1, 'teacup', 0, 'stub', 'leaf', 'none', 'right', 'happy'],
  [116,'Brothling',     'Soup',       ['Brothy','Herbal'],     [78,70,76,68], 0.25, 117,32, [22,23,46,47], 'Simmers steadily at 195 degrees, soothing weary travelers.', false, 1, 'teacup', 1, 'arms', 'steam', 'aura', 'low', 'wide'],
  [117,'Cauldrake',     'Soup',       ['Brothy','Savory'],     [106,96,98,74],0.12, null,null,[23,24,39,41], 'An ancient copper pot whose perpetual stew never runs dry.', false, 2, 'cauldron', 2, 'heavy', 'horns', 'tail', 'right', 'fierce'],
  [118,'Misoimp',       'Soup',       ['Fermented','Brothy'],  [52,54,54,62], 0.40, 119,19, [30,33,22,25], 'Toots tiny bubbles around cubes of silken tofu and wakame.', false, 1, 'teacup', 0, 'bounce', 'steam', 'none', 'lean_r', 'happy'],
  [119,'Misomonarch',   'Soup',       ['Fermented','Herbal'],  [86,86,88,76], 0.16, null,null,[31,32,47,50], 'Aged red-and-white miso swirls in hypnotic umami clouds.', false, 2, 'tureen', 2, 'float', 'crown', 'cape', 'tall', 'wide'],
  [120,'Gazpachopup',   'Soup',       ['Chilled','Raw'],       [54,56,52,70], 0.38, 121,21, [42,43,26,28], 'Blended heirloom tomato and cucumber—never, ever heat it up.', false, 1, 'teacup', 0, 'paws', 'leaf', 'tail', 'wide', 'fierce'],
  [121,'Chilledchow',   'Soup',       ['Chilled','Pickled'],   [84,84,82,86], 0.16, null,null,[43,44,14,15], 'Ice-cold velvet soup topped with tangy pickled shallots.', false, 2, 'tureen', 1, 'paws', 'dill', 'aura', 'left', 'round'],
  [122,'Chowdercrab',   'Soup',       ['Savory','Brothy'],     [62,58,66,48], 0.36, 123,23, [38,39,22,23], 'Carries a crusty bread-bowl shell and oyster-cracker shields.', false, 1, 'bread_bowl', 0, 'claws', 'none', 'claws', 'high', 'sleepy'],
  [123,'Bisquebeast',   'Soup',       ['Savory','Toasted'],    [96,90,98,58], 0.15, null,null,[39,41,1,2],   'Rich, velvety lobster-stock titan with a toasted crouton crown.', false, 2, 'bread_bowl', 2, 'claws', 'crown', 'shield', 'left', 'fierce'],
  [124,'Tomatoteapot',  'Soup',       ['Herbal','Toasted'],    [56,58,56,60], 0.38, 125,20, [46,47,0,3],   'Best friends with grilled cheese; whistles when warm.', false, 1, 'teacup', 1, 'stub', 'steam', 'shield', 'lean_l', 'round'],
  [125,'Basiltureen',   'Soup',       ['Herbal','Brothy'],     [88,88,84,74], 0.16, null,null,[47,50,23,24], 'Pours sun-ripened tomato bisque topped with pesto swirls.', false, 2, 'tureen', 2, 'arms', 'leaf', 'cape', 'wide', 'sleepy'],
  [126,'Borschtbear',   'Soup',       ['Pickled','Brothy'],    [62,60,60,52], 0.35, 127,24, [14,15,22,23], 'Vibrant ruby-beet soup with a dollop of cool sour cream.', false, 1, 'clay_pot', 1, 'paws', 'cream', 'none', 'right', 'happy'],
  [127,'Rubykettler',   'Soup',       ['Pickled','Fermented'], [94,90,90,66], 0.15, null,null,[15,16,31,32], 'Earthy, tangy, and strong enough to warm a frozen tundra.', false, 2, 'cauldron', 2, 'heavy', 'cream', 'arms', 'low', 'wide'],
  [128,'Chilipepperpot','Soup',       ['Spicy','Savory'],      [58,68,54,60], 0.35, 129,24, [18,19,38,39], 'Simmers with smoky chipotle, kidney beans, and corn.', false, 1, 'chili_pot', 0, 'stub', 'chili', 'none', 'center', 'sleepy'],
  [129,'Volcanopot',    'Soup',       ['Spicy','Brothy'],      [90,102,82,70],0.14, null,null,[19,20,23,24], 'Erupts with five-alarm chili and melted cheddar lava.', false, 2, 'chili_pot', 2, 'heavy', 'flame', 'aura', 'lean_r', 'happy'],
  [130,'Minestronem',   'Soup',       ['Raw','Herbal'],        [68,72,72,72], 0.25, null,null,[26,28,46,47], 'Packed with beans, zucchini, pasta shells, and garden thyme.', false, 2, 'bread_bowl', 1, 'paws', 'leaf', 'none', 'tall', 'wide'],
  [131,'Tomyumtiger',   'Soup',       ['Spicy','Pickled'],     [74,90,68,92], 0.20, null,null,[18,19,14,15], 'Leaps with lemongrass, galangal, lime, and fiery bird-eye chili.', false, 2, 'clay_pot', 1, 'claws', 'ears', 'tail', 'right', 'fierce'],
  [132,'Frenchonion',   'Soup',       ['Toasted','Savory'],    [86,84,90,62], 0.20, null,null,[1,2,39,40],   'Wears a bubbling gruyere-and-baguette helmet over sweet onions.', false, 2, 'bread_bowl', 2, 'arms', 'grill', 'shield', 'high', 'round'],
  [133,'Congeecub',     'Soup',       ['Steamed','Brothy'],    [70,64,74,64], 0.28, null,null,[5,6,22,25],   'Gentle, soothing rice porridge topped with ginger and scallion.', false, 1, 'clay_pot', 0, 'paws', 'ears', 'none', 'high', 'wide'],
  [134,'Hotpotsalam',   'Soup',       ['Spicy','Fermented'],   [84,92,78,76], 0.18, null,null,[19,20,31,32], 'Split yin-yang cauldron: half mild mushroom, half numbing mala.', false, 2, 'cauldron', 1, 'paws', 'chili', 'tail', 'lean_r', 'fierce'],
  [135,'Gumbogator',    'Soup',       ['Savory','Spicy'],      [88,92,84,70], 0.18, null,null,[39,41,18,19], 'Built on a dark chocolate-colored roux and file powder.', false, 2, 'chili_pot', 2, 'claws', 'leaf', 'tail', 'lean_l', 'round'],
  [136,'Avgolemono',    'Soup',       ['Pickled','Brothy'],    [72,76,74,78], 0.24, null,null,[14,15,22,23], 'Silky Greek lemon-egg broth that glows like liquid sunshine.', false, 2, 'tureen', 1, 'float', 'egg', 'aura', 'wide', 'sleepy'],
  [137,'Vichyssoise',   'Soup',       ['Chilled','Savory'],    [76,74,80,74], 0.24, null,null,[42,43,38,39], 'Posh chilled leek-and-potato cream that refuses to be microwaved.', false, 2, 'tureen', 1, 'arms', 'crown', 'cape', 'right', 'happy'],
  [138,'Midnitebisque', 'Soup',       ['Brothy','Chilled'],    [84,88,82,82], 0.18, null,null,[23,24,43,44], 'Appears in moonlit kitchens smelling of roasted garlic.', true, 2, 'cauldron', 1, 'float', 'moon', 'aura', 'low', 'round'],
  [139,'Sweetcornowl',  'Soup',       ['Sweet','Brothy'],      [70,74,72,76], 0.26, null,null,[34,36,22,23], 'Velvety golden corn chowder with egg-drop ribbons.', false, 1, 'bread_bowl', 1, 'none', 'ears', 'wings', 'center', 'sleepy'],
  [140,'Mulligatawny',  'Soup',       ['Spicy','Sweet'],       [78,84,76,76], 0.22, null,null,[18,19,34,35], 'Curried apple-and-lentil soup with a warming peppery finish.', false, 2, 'clay_pot', 1, 'paws', 'chili', 'tail', 'lean_l', 'happy'],
  [141,'Pozolepuma',    'Soup',       ['Raw','Spicy'],         [80,88,76,84], 0.20, null,null,[26,28,18,19], 'Hominy-rich red broth topped with crisp radish and cabbage.', false, 2, 'chili_pot', 1, 'claws', 'ears', 'tail', 'tall', 'wide'],
  [142,'Sinigangseal',  'Soup',       ['Pickled','Brothy'],    [78,80,78,76], 0.22, null,null,[14,16,22,23], 'Tamarind-sour comfort soup that makes everyone say "ahh!"', false, 2, 'clay_pot', 1, 'fins', 'dill', 'fins', 'right', 'fierce'],
  [143,'Ribollitaram',  'Soup',       ['Toasted','Herbal'],    [84,82,88,64], 0.20, null,null,[1,3,46,47],   'Reboiled Tuscan bread-and-kale stew thicker than mortar.', false, 2, 'bread_bowl', 2, 'heavy', 'horns', 'none', 'lean_r', 'happy'],
  [144,'Oxtailox',      'Soup',       ['Savory','Brothy'],     [98,96,94,58], 0.16, null,null,[39,41,23,24], 'Slow-braised for twelve hours; its marrow is pure strength.', false, 3, 'clay_pot', 2, 'heavy', 'horns', 'tail', 'low', 'wide'],
  [145,'Matchabroth',   'Soup',       ['Herbal','Chilled'],    [72,78,74,88], 0.22, null,null,[46,48,42,44], 'Zen green-tea ochazuke pouring cool clarity over crispy rice.', false, 2, 'teacup', 1, 'float', 'leaf', 'aura', 'lean_r', 'fierce'],
  [146,'Pumpkinpot',    'Soup',       ['Sweet','Toasted'],     [80,78,82,66], 0.22, null,null,[34,35,0,4],   'Roasted nutmeg-pumpkin veloute crowned with toasted pepitas.', false, 2, 'chili_pot', 1, 'stub', 'seeds', 'none', 'tall', 'round'],
  [147,'Kimchijjigae',  'Soup',       ['Fermented','Spicy'],   [84,94,80,74], 0.18, null,null,[31,32,19,20], 'Bubbling clay pot of aged kimchi, tofu, and fearless heat.', false, 2, 'clay_pot', 2, 'arms', 'flame', 'aura', 'wide', 'sleepy'],
  [148,'Cockaleekie',   'Soup',       ['Herbal','Savory'],     [76,80,78,74], 0.22, null,null,[46,50,38,39], 'Scottish leek-and-barley broth with a surprising sweet prune.', false, 2, 'tureen', 1, 'paws', 'leaf', 'cape', 'left', 'fierce'],
  [149,'Bouillabais',   'Soup',       ['Brothy','Herbal'],     [92,94,88,78], 0.14, null,null,[23,24,47,50], 'Saffron-scented coastal feast with rouille-toasted croutons.', false, 3, 'tureen', 2, 'fins', 'crown', 'fins', 'high', 'round'],
  [150,'Grandstock',    'Soup',       ['Savory','Brothy'],     [110,102,102,80],0.10,null,null,[24,41,50,4],  'Legendary master-stock spirit simmering in the Deep Stock Vault.', false, 4, 'cauldron', 2, 'heavy', 'crown', 'wings', 'center', 'sleepy'],

  // === SECRET #151 ===
  [151,'Consommyth',    'Soup',       ['Brothy','Sweet'],      [115,110,105,105],0.08,null,null,[24,25,37,50], 'A mythical luminous broth-spirit uniting sandwich, dumpling, noodle, and soup.', true, 5, 'myth_bowl', 2, 'float', 'halo', 'wings', 'lean_l', 'happy']
];
