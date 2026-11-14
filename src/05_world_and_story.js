// 05_world_and_story.js - 4 Regions, 10 Maps (30x18 8x8 tiles), 8 Head Chefs, Rival, Final Challenge, Side Quests, & Secret #151

const REGIONS = {
  Breadlands:  { name: 'Breadlands',  family: 'Sandwiches', music: 'overworld_bread',  sky: '#78C8E8' },
  Steambay:    { name: 'Steambay',    family: 'Dumplings',  music: 'overworld_steam',  sky: '#88C8C0' },
  Noodleridge: { name: 'Noodleridge', family: 'Noodles',    music: 'overworld_noodle', sky: '#E8B878' },
  Brothbasin:  { name: 'Brothbasin',  family: 'Soup',       music: 'overworld_broth',  sky: '#6888B8' },
  TastingHall: { name: 'Grand Tasting Hall', family: 'All', music: 'town',             sky: '#382848' }
};

// Map legend for 30x18 8x8 tile grids:
// '.' = 0 Grass, ',' = 1 Tall Herb Grass (encounters), '=' = 2 Path, '~' = 3 Water,
// '#' = 4 Tree/Wall, 'W' = 5 Building Wall, 'R' = 6 Roof, 'D' = 7 Door/Portal,
// '_' = 8 Cobble, 'H' = 9 Simmer Inn Counter, 'S' = 10 Sign, 'M' = 11 Kitchen Mat
const CHAR_TO_TILE = {
  '.':0, ',':1, '=':2, '~':3, '#':4, 'W':5, 'R':6, 'D':7, '_':8, 'H':9, 'S':10, 'M':11
};
const SOLID_TILES = new Set([3, 4, 5, 6, 9, 10]);

function parseMapGrid(rows) {
  const grid = new Uint8Array(30 * 18);
  for (let y = 0; y < 18; y++) {
    const row = (rows[y] || '').padEnd(30, '.');
    for (let x = 0; x < 30; x++) {
      grid[y * 30 + x] = CHAR_TO_TILE[row[x]] ?? 0;
    }
  }
  return grid;
}

const TRAINERS = {
  // 8 Head Chefs (Gyms)
  chef_greg: {
    id: 'chef_greg', name: 'Head Chef Griddle Greg', title: 'The Toaster Hearth',
    seal: 'Crisp Seal', sealIdx: 0, rewardGold: 300,
    intro: 'Welcome to The Toaster Hearth! Let us see if your bEATsts can handle 400 degrees of golden crunch!',
    win: 'Magnificent char! Take the Crisp Seal—may your crusts never go soggy!',
    party: [{ id: 1, lv: 9 }, { id: 2, lv: 12 }]
  },
  chef_clara: {
    id: 'chef_clara', name: 'Head Chef Clara Coldcut', title: 'Deli Counter Spire',
    seal: 'Stack Seal', sealIdx: 1, rewardGold: 450,
    intro: 'At Deli Counter Spire, every layer matters. Bread, brine, balance—show me your stack!',
    win: 'Impeccable structural integrity! The Stack Seal is yours!',
    party: [{ id: 10, lv: 14 }, { id: 5, lv: 16 }]
  },
  chef_baozi: {
    id: 'chef_baozi', name: 'Head Chef Master Baozi', title: 'Bamboo Cloud Kitchen',
    seal: 'Steam Seal', sealIdx: 2, rewardGold: 600,
    intro: 'Breathe in the mist of Bamboo Cloud Kitchen. Softness can defeat the hardest crust!',
    win: 'Gentle yet unstoppable! Accept the Steam Seal, young cook!',
    party: [{ id: 39, lv: 19 }, { id: 40, lv: 22 }]
  },
  chef_mei: {
    id: 'chef_mei', name: 'Head Chef Sizzle Mei', title: 'Skillet Tidehouse',
    seal: 'Sear Seal', sealIdx: 3, rewardGold: 800,
    intro: 'Hear that cast-iron hiss? At Skillet Tidehouse we sear first and ask questions later!',
    win: 'Golden lace perfection! You have earned the Sear Seal!',
    party: [{ id: 42, lv: 23 }, { id: 43, lv: 26 }]
  },
  chef_twirl: {
    id: 'chef_twirl', name: 'Head Chef Sensei Twirl', title: 'Pull-Noodle Dojo',
    seal: 'Slurp Seal', sealIdx: 4, rewardGold: 1000,
    intro: 'Hand-pulled dough stretches ten feet without snapping! Show me your elasticity!',
    win: 'What bounce! What al-dente spirit! Take the Slurp Seal!',
    party: [{ id: 77, lv: 28 }, { id: 78, lv: 30 }]
  },
  chef_fusilli: {
    id: 'chef_fusilli', name: 'Head Chef Nonna Fusilli', title: 'Wok Peak Bistro',
    seal: 'Twirl Seal', sealIdx: 5, rewardGold: 1200,
    intro: 'Nonna Fusilli never measures basil with a spoon—only with her heart!',
    win: 'Bellissimo! You battle like Sunday dinner! Take the Twirl Seal!',
    party: [{ id: 81, lv: 32 }, { id: 87, lv: 35 }]
  },
  chef_bisque: {
    id: 'chef_bisque', name: 'Head Chef Alchemist Bisque', title: 'Cauldron Conservatory',
    seal: 'Simmer Seal', sealIdx: 6, rewardGold: 1500,
    intro: 'Low and slow, bubble and glow! Welcome to Cauldron Conservatory!',
    win: 'Your broth is crystal clear and deeply savory! Take the Simmer Seal!',
    party: [{ id: 118, lv: 36 }, { id: 119, lv: 39 }]
  },
  chef_bouillon: {
    id: 'chef_bouillon', name: 'Head Chef Lady Bouillon', title: 'The Deep Stock Vault',
    seal: 'Stock Seal', sealIdx: 7, rewardGold: 1800,
    intro: 'Only cooks of true patience reach the Deep Stock Vault. Impress my cauldron!',
    win: 'Eight Seals complete! The Grand Tasting Hall awaits you!',
    party: [{ id: 123, lv: 41 }, { id: 150, lv: 44 }]
  },

  // Rival Saffron (4 encounters)
  rival_1: {
    id: 'rival_1', name: 'Rival Saffron', title: 'Perfectionist Sous-Chef', rewardGold: 250,
    intro: 'Hmph! Still using a Paper Plate? My plating angles are 100% geometric! En garde!',
    win: 'Wait—your messy sandwich bEATst actually won?! Fine, I will simmer on that!',
    party: [{ id: 4, lv: 7 }, { id: 39, lv: 8 }]
  },
  rival_2: {
    id: 'rival_2', name: 'Rival Saffron', title: 'Perfectionist Sous-Chef', rewardGold: 500,
    intro: 'We meet again in Steambay! I bought a Ceramic Plate just to flex on you!',
    win: 'Ugh, your team actually looks... happy? Maybe I am over-seasoning...',
    party: [{ id: 46, lv: 19 }, { id: 5, lv: 20 }]
  },
  rival_3: {
    id: 'rival_3', name: 'Rival Saffron', title: 'Perfectionist Sous-Chef', rewardGold: 900,
    intro: 'Noodleridge is mine! I timed my boiling water to the millisecond!',
    win: 'Okay, I admit it—cooking with joy beats cooking with a stopwatch!',
    party: [{ id: 85, lv: 31 }, { id: 43, lv: 32 }]
  },
  rival_4: {
    id: 'rival_4', name: 'Rival Saffron', title: 'Grand Hall Contender', rewardGold: 1500,
    intro: 'Before you face the Three-Course Gauntlet, show me everything we learned across Pantrylia!',
    win: 'Go get that Champion apron, friend. Save me a seat at the banquet!',
    party: [{ id: 3, lv: 43 }, { id: 41, lv: 44 }, { id: 79, lv: 45 }]
  },

  // Final Challenge (Three-Course Gauntlet) + Champion
  taster_pip: {
    id: 'taster_pip', name: 'Master Taster Pip', title: 'First Course: Appetizer', rewardGold: 1200,
    intro: 'Course One! Crisp, bright, and zesty—let us wake up your palate!',
    win: 'Delightful! Proceed to the Main Course!',
    party: [{ id: 28, lv: 44 }, { id: 53, lv: 45 }]
  },
  taster_roux: {
    id: 'taster_roux', name: 'Master Taster Roux', title: 'Second Course: Main', rewardGold: 1500,
    intro: 'Course Two! Rich gravy, deep sear, and fearless umami!',
    win: 'Substantial and soulful! One course remains!',
    party: [{ id: 89, lv: 46 }, { id: 129, lv: 47 }]
  },
  taster_mochi: {
    id: 'taster_mochi', name: 'Master Taster Mochi', title: 'Third Course: Palate Cleanser', rewardGold: 1800,
    intro: 'Course Three! Cool, sweet, and soothing before the Champion!',
    win: 'Refreshing! Grand Champion Chef Aurelia is ready for you!',
    party: [{ id: 55, lv: 47 }, { id: 121, lv: 48 }]
  },
  champion_aurelia: {
    id: 'champion_aurelia', name: 'Champion Chef Aurelia', title: 'Realm Grand Chef-Tamer', rewardGold: 5000,
    intro: 'Welcome to the Grand Tasting Table! Show me the bond between cook and bEATst!',
    win: 'Bravo! You are Pantrylia’s new Grand Chef-Tamer! Every kitchen sings your name!',
    party: [{ id: 3, lv: 48 }, { id: 76, lv: 49 }, { id: 114, lv: 50 }, { id: 117, lv: 52 }]
  }
};

const MAPS = {
  cruston_town: {
    id: 'cruston_town', name: 'Cruston Town', region: 'Breadlands', music: 'town',
    wildPool: [],
    grid: parseMapGrid([
      '##############==##############',
      '#............====............#',
      '#.RRRRR......====.....RRRRR..#',
      '#.WWWWW..S...====.....WWWWW..#',
      '#.WWDWW......====.....WWDWW..#',
      '#............====............#',
      '#....============............#',
      '#....=..........=............#',
      '#.RRRRR...SS....=.....RRRRR..#',
      '#.WWWWW.........======WWDWW..#',
      '#.WWDWW....H.........=WWWWW..#',
      '#.........._.........=.......#',
      '#.........._.........=.......#',
      '#..........===========.......#',
      '#............................#',
      '#.....~~~~..........~~~~.....#',
      '#.....~~~~..........~~~~.....#',
      '##############################'
    ]),
    portals: [
      { x: 14, y: 0, to: 'toastwood_trail', tx: 14, ty: 16 },
      { x: 15, y: 0, to: 'toastwood_trail', tx: 15, ty: 16 }
    ],
    npcs: [
      { id: 'brotholomew', x: 4, y: 5, name: 'Chef Brotholomew', color: '#E8E8F0',
        dialog: 'Welcome to Pantrylia! Raise your bEATsts, set fancy plates to befriend wild dishes, and earn all 8 Kitchen Seals!' },
      { id: 'inn_cruston', x: 11, y: 11, name: 'Simmer Inn Host', color: '#FF90A8', action: 'heal',
        dialog: 'Welcome to the Simmer Inn! Let us warm up your bEATsts to full HP and PP!' },
      { id: 'mart_cruston', x: 24, y: 11, name: 'Pantry Mart Clerk', color: '#60C8F8', action: 'shop',
        dialog: 'Welcome to Pantry Mart! Stock up on Plates, Broth Cups, and Garnish Treats!' },
      { id: 'barnaby', x: 9, y: 5, name: 'Baker Barnaby', color: '#F0C040', quest: 'q1_butter',
        dialog: 'Oh crumbs! I dropped my Cultured Butter on Toastwood Trail! Could you grab it for me?' }
    ]
  },

  toastwood_trail: {
    id: 'toastwood_trail', name: 'Toastwood Trail', region: 'Breadlands', music: 'overworld_bread',
    wildPool: [[1,3,5],[4,3,6],[6,4,7],[10,4,7],[14,5,8],[26,4,7],[25,6,9]],
    grid: parseMapGrid([
      '##############==##############',
      '#,,,,,,,,,,,,====,,,,,,,,,,,,#',
      '#,,,,,,,,,,,,====,,,,,,,,,,,,#',
      '#..####......====......####..#',
      '#..####......====......####..#',
      '#......==============........#',
      '#......=,,,,,,,,,,,,=........#',
      '#......=,,,,,,,,,,,,=........#',
      '#......=....====....=........#',
      '#..~~~~=....====....=~~~~....#',
      '#..~~~~=....====....=~~~~....#',
      '#......======..======........#',
      '#,,,,,,,,,,,,==,,,,,,,,,,,,,,#',
      '#,,,,,,,,,,,,==,,,,,,,,,,,,,,#',
      '#......==============........#',
      '#............==..............#',
      '#............==..............#',
      '##############==##############'
    ]),
    portals: [
      { x: 14, y: 17, to: 'cruston_town', tx: 14, ty: 1 },
      { x: 15, y: 17, to: 'cruston_town', tx: 15, ty: 1 },
      { x: 14, y: 0,  to: 'panini_plaza', tx: 14, ty: 16 },
      { x: 15, y: 0,  to: 'panini_plaza', tx: 15, ty: 16 }
    ],
    npcs: [
      { id: 'butter_item', x: 6, y: 6, name: 'Cultured Butter', color: '#F8E888', itemPickup: 'q1_butter_item',
        dialog: 'Found Baker Barnaby’s Cultured Butter! Smells faintly of thyme and triumph.' },
      { id: 'saffron_1', x: 14, y: 8, name: 'Rival Saffron', color: '#D04038', trainer: 'rival_1' }
    ]
  },

  panini_plaza: {
    id: 'panini_plaza', name: 'Panini Plaza', region: 'Breadlands', music: 'town',
    wildPool: [[8,6,9],[12,6,10],[16,7,11],[18,7,11],[34,8,12]],
    grid: parseMapGrid([
      '##############################',
      '#..RRRRR..............RRRRR..#',
      '#..WWWWW......==......WWWWW..#',
      '#..WWM__......==......__MWW..#',
      '#.............==.............#',
      '#....================........#',
      '#....=..............=........#',
      '#..,,,......H.......=........#',
      '#..,,,......_.......==========',
      '#..........._................=',
      '#....================........#',
      '#...........==...............#',
      '#...........==...............#',
      '#..~~~~.....==.....~~~~......#',
      '#..~~~~.....==.....~~~~......#',
      '#...........==...............#',
      '#...........==...............#',
      '##############==##############'
    ]),
    portals: [
      { x: 14, y: 17, to: 'toastwood_trail', tx: 14, ty: 1 },
      { x: 15, y: 17, to: 'toastwood_trail', tx: 15, ty: 1 },
      { x: 29, y: 8,  to: 'bao_harbor', tx: 1, ty: 8, reqSeals: 2 },
      { x: 29, y: 9,  to: 'bao_harbor', tx: 1, ty: 9, reqSeals: 2 }
    ],
    npcs: [
      { id: 'inn_panini', x: 12, y: 8, name: 'Simmer Inn Host', color: '#FF90A8', action: 'heal',
        dialog: 'Simmer Inn at Panini Plaza! Rest up before challenging the Head Chefs!' },
      { id: 'greg_npc', x: 5, y: 4, name: 'Head Chef Griddle Greg', color: '#E8A850', trainer: 'chef_greg' },
      { id: 'clara_npc', x: 24, y: 4, name: 'Head Chef Clara Coldcut', color: '#8AC926', trainer: 'chef_clara' },
      { id: 'gate_bread', x: 28, y: 7, name: 'Bridge Guard', color: '#A0A8B0',
        dialog: 'The bridge East to Steambay opens once you hold 2 Kitchen Seals (Crisp + Stack)!' }
    ]
  },

  bao_harbor: {
    id: 'bao_harbor', name: 'Bao Harbor', region: 'Steambay', music: 'overworld_steam',
    wildPool: [[39,12,16],[42,13,17],[46,14,18],[48,14,18],[54,13,17],[69,15,19]],
    grid: parseMapGrid([
      '##############==##############',
      '#..RRRRR......==......~~~~~..#',
      '#..WWWWW......==......~~~~~..#',
      '#..WWM__......==......~~~~~..#',
      '#.............==.............#',
      '#.......============.........#',
      '#.......=..........=.........#',
      '#.......=....H.....=....,,,..#',
      '=========...._.....=....,,,..#',
      '=............_.....=.........#',
      '#.......============.........#',
      '#............................#',
      '#..~~~~......RRRRR...........#',
      '#..~~~~......WWWWW...........#',
      '#..~~~~......WWDWW...........#',
      '#............................#',
      '#............................#',
      '##############################'
    ]),
    portals: [
      { x: 0,  y: 8,  to: 'panini_plaza', tx: 28, ty: 8 },
      { x: 0,  y: 9,  to: 'panini_plaza', tx: 28, ty: 9 },
      { x: 14, y: 0,  to: 'gyoza_cove', tx: 14, ty: 16 },
      { x: 15, y: 0,  to: 'gyoza_cove', tx: 15, ty: 16 }
    ],
    npcs: [
      { id: 'inn_bao', x: 13, y: 8, name: 'Simmer Inn Host', color: '#FF90A8', action: 'heal',
        dialog: 'Steambay Simmer Inn! Let the bamboo mist restore your party!' },
      { id: 'mart_bao', x: 15, y: 15, name: 'Pantry Mart Clerk', color: '#60C8F8', action: 'shop',
        dialog: 'Welcome to Bao Harbor Pantry Mart! Try our Wooden Boards and Ceramic Plates!' },
      { id: 'baozi_npc', x: 5, y: 4, name: 'Head Chef Master Baozi', color: '#F8F8F0', trainer: 'chef_baozi' },
      { id: 'lid_quest', x: 19, y: 11, name: 'Steamer Apprentice', color: '#A8DADC', quest: 'q2_lid',
        dialog: 'Master Baozi’s lucky Bamboo Lid blew north into Gyoza Cove! Can you find it?' }
    ]
  },

  gyoza_cove: {
    id: 'gyoza_cove', name: 'Gyoza Cove', region: 'Steambay', music: 'overworld_steam',
    wildPool: [[44,18,22],[50,18,22],[52,19,23],[58,20,24],[62,20,24],[68,20,24]],
    grid: parseMapGrid([
      '##############################',
      '#..~~~~................RRRRR.#',
      '#..~~~~..,,,,..........WWWWW.#',
      '#........,,,,..........WWM__.#',
      '#......===============.......#',
      '#......=.............=.......#',
      '#......=.............=========',
      '#..,,,,=.............=.......=',
      '#..,,,,=.............=.......#',
      '#......=....====.....=.......#',
      '#......=....====.....=.......#',
      '#......======..=======.......#',
      '#,,,,,,,,,,,,==,,,,,,,,,,,,,,#',
      '#,,,,,,,,,,,,==,,,,,,,,,,,,,,#',
      '#............==..............#',
      '#............==..............#',
      '#............==..............#',
      '##############==##############'
    ]),
    portals: [
      { x: 14, y: 17, to: 'bao_harbor', tx: 14, ty: 1 },
      { x: 15, y: 17, to: 'bao_harbor', tx: 15, ty: 1 },
      { x: 29, y: 6,  to: 'udon_hollow', tx: 1, ty: 8, reqSeals: 4 },
      { x: 29, y: 7,  to: 'udon_hollow', tx: 1, ty: 9, reqSeals: 4 }
    ],
    npcs: [
      { id: 'lid_item', x: 10, y: 2, name: 'Lucky Bamboo Lid', color: '#D8B880', itemPickup: 'q2_lid_item',
        dialog: 'Found the Lucky Bamboo Lid! It still smells pleasantly of ginger.' },
      { id: 'saffron_2', x: 14, y: 10, name: 'Rival Saffron', color: '#D04038', trainer: 'rival_2' },
      { id: 'mei_npc', x: 25, y: 4, name: 'Head Chef Sizzle Mei', color: '#E6AF2E', trainer: 'chef_mei' }
    ]
  },

  udon_hollow: {
    id: 'udon_hollow', name: 'Udon Hollow', region: 'Noodleridge', music: 'overworld_noodle',
    wildPool: [[77,22,26],[80,23,27],[82,24,28],[86,25,29],[92,25,29]],
    grid: parseMapGrid([
      '##############==##############',
      '#..RRRRR......==......RRRRR..#',
      '#..WWWWW......==......WWWWW..#',
      '#..WWM__......==......WWDWW..#',
      '#.............==.............#',
      '#.......============.........#',
      '#.......=..........=.........#',
      '#.......=....H.....=.........#',
      '=========...._.....=....,,,..#',
      '=............_.....=....,,,..#',
      '#.......============.........#',
      '#............................#',
      '#..####..............####....#',
      '#..####..............####....#',
      '#............................#',
      '#............................#',
      '#............................#',
      '##############################'
    ]),
    portals: [
      { x: 0,  y: 8, to: 'gyoza_cove', tx: 28, ty: 6 },
      { x: 0,  y: 9, to: 'gyoza_cove', tx: 28, ty: 7 },
      { x: 14, y: 0, to: 'slurp_canyon', tx: 14, ty: 16 },
      { x: 15, y: 0, to: 'slurp_canyon', tx: 15, ty: 16 }
    ],
    npcs: [
      { id: 'inn_udon', x: 13, y: 8, name: 'Simmer Inn Host', color: '#FF90A8', action: 'heal',
        dialog: 'Welcome to Udon Hollow Simmer Inn! Rest your noodles!' },
      { id: 'mart_udon', x: 24, y: 4, name: 'Pantry Mart Clerk', color: '#60C8F8', action: 'shop',
        dialog: 'Noodleridge Pantry Mart! Grab Bento Lacquer Sets and Hearty Stews!' },
      { id: 'twirl_npc', x: 5, y: 4, name: 'Head Chef Sensei Twirl', color: '#F0C868', trainer: 'chef_twirl' }
    ]
  },

  slurp_canyon: {
    id: 'slurp_canyon', name: 'Slurp Canyon', region: 'Noodleridge', music: 'overworld_noodle',
    wildPool: [[84,27,31],[88,27,31],[90,28,32],[94,29,33],[97,30,34],[98,30,34],[106,30,34]],
    grid: parseMapGrid([
      '##############################',
      '#..####................RRRRR.#',
      '#..####..,,,,..........WWWWW.#',
      '#........,,,,..........WWM__.#',
      '#......===============.......#',
      '#......=.............=.......#',
      '#......=.............=========',
      '#..,,,,=.............=.......=',
      '#..,,,,=.............=.......#',
      '#......=....====.....=.......#',
      '#......=....====.....=.......#',
      '#......======..=======.......#',
      '#,,,,,,,,,,,,==,,,,,,,,,,,,,,#',
      '#,,,,,,,,,,,,==,,,,,,,,,,,,,,#',
      '#............==..............#',
      '#............==..............#',
      '#............==..............#',
      '##############==##############'
    ]),
    portals: [
      { x: 14, y: 17, to: 'udon_hollow', tx: 14, ty: 1 },
      { x: 15, y: 17, to: 'udon_hollow', tx: 15, ty: 1 },
      { x: 29, y: 6,  to: 'chowder_crossing', tx: 1, ty: 8, reqSeals: 6 },
      { x: 29, y: 7,  to: 'chowder_crossing', tx: 1, ty: 9, reqSeals: 6 }
    ],
    npcs: [
      { id: 'chopsticks_item', x: 10, y: 2, name: 'Golden Chopsticks', color: '#F0C040', itemPickup: 'q3_chopsticks_item',
        dialog: 'Found the Golden Chopsticks! (+500G reward from the Noodle Guild!)' },
      { id: 'saffron_3', x: 14, y: 10, name: 'Rival Saffron', color: '#D04038', trainer: 'rival_3' },
      { id: 'fusilli_npc', x: 25, y: 4, name: 'Head Chef Nonna Fusilli', color: '#52B788', trainer: 'chef_fusilli' }
    ]
  },

  chowder_crossing: {
    id: 'chowder_crossing', name: 'Chowder Crossing', region: 'Brothbasin', music: 'overworld_broth',
    wildPool: [[115,31,35],[118,32,36],[120,33,37],[124,33,37],[128,34,38]],
    grid: parseMapGrid([
      '##############==##############',
      '#..RRRRR......==......RRRRR..#',
      '#..WWWWW......==......WWWWW..#',
      '#..WWM__......==......WWDWW..#',
      '#.............==.............#',
      '#.......============.........#',
      '#.......=..........=.........#',
      '#.......=....H.....=.........#',
      '=========...._.....=....,,,..#',
      '=............_.....=....,,,..#',
      '#.......============.........#',
      '#............................#',
      '#..~~~~..............~~~~....#',
      '#..~~~~..............~~~~....#',
      '#............................#',
      '#............................#',
      '#............................#',
      '##############################'
    ]),
    portals: [
      { x: 0,  y: 8, to: 'slurp_canyon', tx: 28, ty: 6 },
      { x: 0,  y: 9, to: 'slurp_canyon', tx: 28, ty: 7 },
      { x: 14, y: 0, to: 'bisque_bastion', tx: 14, ty: 16 },
      { x: 15, y: 0, to: 'bisque_bastion', tx: 15, ty: 16 }
    ],
    npcs: [
      { id: 'inn_chowder', x: 13, y: 8, name: 'Simmer Inn Host', color: '#FF90A8', action: 'heal',
        dialog: 'Brothbasin Simmer Inn! Ladle up some rest!' },
      { id: 'mart_chowder', x: 24, y: 4, name: 'Pantry Mart Clerk', color: '#60C8F8', action: 'shop',
        dialog: 'Chowder Crossing Pantry Mart! Royal Banquet Settings now in stock!' },
      { id: 'bisque_npc', x: 5, y: 4, name: 'Head Chef Alchemist Bisque', color: '#9B5DE5', trainer: 'chef_bisque' }
    ]
  },

  bisque_bastion: {
    id: 'bisque_bastion', name: 'Bisque Bastion', region: 'Brothbasin', music: 'overworld_broth',
    wildPool: [[126,36,40],[131,37,41],[134,38,42],[138,39,43],[144,40,44],[149,41,45]],
    grid: parseMapGrid([
      '##############==##############',
      '#..~~~~.......==.......RRRRR.#',
      '#..~~~~..,,,,.==.......WWWWW.#',
      '#........,,,,.==.......WWM__.#',
      '#......===============.......#',
      '#......=.............=.......#',
      '#......=.............=.......#',
      '#..,,,,=.............=.......#',
      '#..,,,,=.............=.......#',
      '#......=....====.....=.......#',
      '#......=....====.....=.......#',
      '#......======..=======.......#',
      '#,,,,,,,,,,,,==,,,,,,,,,,,,,,#',
      '#,,,,,,,,,,,,==,,,,,,,,,,,,,,#',
      '#............==..............#',
      '#............==..............#',
      '#............==..............#',
      '##############==##############'
    ]),
    portals: [
      { x: 14, y: 17, to: 'chowder_crossing', tx: 14, ty: 1 },
      { x: 15, y: 17, to: 'chowder_crossing', tx: 15, ty: 1 },
      { x: 14, y: 0,  to: 'grand_tasting_hall', tx: 14, ty: 16, reqSeals: 8 },
      { x: 15, y: 0,  to: 'grand_tasting_hall', tx: 15, ty: 16, reqSeals: 8 }
    ],
    npcs: [
      { id: 'truffle_item', x: 10, y: 2, name: 'Rare Night Truffle', color: '#8D5B4C', itemPickup: 'q4_truffle_item',
        dialog: 'Found a Rare Night Truffle! Gives you a Royal Banquet Setting & a clue: at Night, Champions with all 4 families may open the Secret Pantry in the Grand Hall!' },
      { id: 'bouillon_npc', x: 25, y: 4, name: 'Head Chef Lady Bouillon', color: '#457B9D', trainer: 'chef_bouillon' }
    ]
  },

  grand_tasting_hall: {
    id: 'grand_tasting_hall', name: 'Grand Tasting Hall', region: 'TastingHall', music: 'town',
    wildPool: [],
    grid: parseMapGrid([
      '##############################',
      '#____________D_______________#',
      '#____________M_______________#',
      '#____________________________#',
      '#____________M_______________#',
      '#____________________________#',
      '#____________M_______________#',
      '#____________________________#',
      '#____________M_______________#',
      '#____________________________#',
      '#____________M_______________#',
      '#____________________________#',
      '#......H____________.........#',
      '#......_____________.........#',
      '#____________==______________#',
      '#____________==______________#',
      '#____________==______________#',
      '##############==##############'
    ]),
    portals: [
      { x: 14, y: 17, to: 'bisque_bastion', tx: 14, ty: 1 },
      { x: 15, y: 17, to: 'bisque_bastion', tx: 15, ty: 1 }
    ],
    npcs: [
      { id: 'inn_hall', x: 7, y: 13, name: 'Banquet Prep Chef', color: '#FF90A8', action: 'heal',
        dialog: 'Final tune-up before the Grand Gauntlet! Full HP and PP restored!' },
      { id: 'saffron_4', x: 13, y: 10, name: 'Rival Saffron', color: '#D04038', trainer: 'rival_4' },
      { id: 'pip_npc', x: 13, y: 8, name: 'Master Taster Pip', color: '#E6AF2E', trainer: 'taster_pip' },
      { id: 'roux_npc', x: 13, y: 6, name: 'Master Taster Roux', color: '#8D5B4C', trainer: 'taster_roux' },
      { id: 'mochi_npc', x: 13, y: 4, name: 'Master Taster Mochi', color: '#FF70A6', trainer: 'taster_mochi' },
      { id: 'aurelia_npc', x: 13, y: 2, name: 'Champion Chef Aurelia', color: '#F0C040', trainer: 'champion_aurelia' },
      { id: 'secret_151_door', x: 13, y: 1, name: 'Secret Pantry Door', color: '#FFD700', action: 'secret151' }
    ]
  }
};
