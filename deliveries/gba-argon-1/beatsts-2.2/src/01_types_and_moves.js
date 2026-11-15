// 01_types_and_moves.js - 12 Cooking Types, Type Chart, Flavor Combos, and 124 Moves
// PROVENANCE: Base 12 types, TYPE_CHART, FLAVOR_COMBOS, and moves 0-50 lifted from beatsts-v1/src/01_types_and_moves.js; extended with moves 51-123.

const TYPES = [
  'Toasted', 'Steamed', 'Fried', 'Pickled',
  'Spicy', 'Brothy', 'Raw', 'Fermented',
  'Sweet', 'Savory', 'Chilled', 'Herbal'
];

const TYPE_COLORS = {
  Toasted:   '#D9822B',
  Steamed:   '#A8DADC',
  Fried:     '#E6AF2E',
  Pickled:   '#8AC926',
  Spicy:     '#E63946',
  Brothy:    '#457B9D',
  Raw:       '#52B788',
  Fermented: '#9B5DE5',
  Sweet:     '#FF70A6',
  Savory:    '#8D5B4C',
  Chilled:   '#4CC9F0',
  Herbal:    '#2D6A4F'
};

// 12x12 Type Chart: TYPE_CHART[atkType][defType] = 2 | 1 | 0.5
const TYPE_CHART = {
  Toasted:   { Toasted:1, Steamed:0.5, Fried:1, Pickled:1, Spicy:1, Brothy:0.5, Raw:2, Fermented:2, Sweet:1, Savory:1, Chilled:2, Herbal:1 },
  Steamed:   { Toasted:2, Steamed:1, Fried:0.5, Pickled:1, Spicy:2, Brothy:1, Raw:1, Fermented:1, Sweet:1, Savory:1, Chilled:0.5, Herbal:1 },
  Fried:     { Toasted:1, Steamed:2, Fried:1, Pickled:0.5, Spicy:1, Brothy:0.5, Raw:2, Fermented:1, Sweet:1, Savory:1, Chilled:1, Herbal:2 },
  Pickled:   { Toasted:1, Steamed:1, Fried:2, Pickled:1, Spicy:1, Brothy:0.5, Raw:1, Fermented:0.5, Sweet:0.5, Savory:2, Chilled:1, Herbal:1 },
  Spicy:     { Toasted:1, Steamed:0.5, Fried:1, Pickled:1, Spicy:1, Brothy:0.5, Raw:2, Fermented:1, Sweet:0.5, Savory:2, Chilled:2, Herbal:1 },
  Brothy:    { Toasted:2, Steamed:1, Fried:2, Pickled:1, Spicy:2, Brothy:1, Raw:1, Fermented:0.5, Sweet:1, Savory:1, Chilled:0.5, Herbal:0.5 },
  Raw:       { Toasted:0.5, Steamed:1, Fried:0.5, Pickled:1, Spicy:0.5, Brothy:1, Raw:1, Fermented:2, Sweet:1, Savory:1, Chilled:2, Herbal:0.5 },
  Fermented: { Toasted:0.5, Steamed:1, Fried:1, Pickled:2, Spicy:1, Brothy:2, Raw:0.5, Fermented:1, Sweet:2, Savory:1, Chilled:1, Herbal:1 },
  Sweet:     { Toasted:1, Steamed:1, Fried:1, Pickled:2, Spicy:2, Brothy:1, Raw:1, Fermented:0.5, Sweet:1, Savory:0.5, Chilled:1, Herbal:1 },
  Savory:    { Toasted:1, Steamed:1, Fried:1, Pickled:0.5, Spicy:0.5, Brothy:1, Raw:1, Fermented:1, Sweet:2, Savory:1, Chilled:1, Herbal:2 },
  Chilled:   { Toasted:0.5, Steamed:2, Fried:1, Pickled:1, Spicy:0.5, Brothy:2, Raw:0.5, Fermented:1, Sweet:1, Savory:1, Chilled:1, Herbal:1 },
  Herbal:    { Toasted:1, Steamed:1, Fried:0.5, Pickled:1, Spicy:1, Brothy:2, Raw:2, Fermented:1, Sweet:1, Savory:0.5, Chilled:1, Herbal:1 }
};

function getTypeEffectiveness(atkType, defTypes) {
  let mult = 1;
  for (const dt of defTypes) {
    const row = TYPE_CHART[atkType];
    if (row && row[dt] !== undefined) mult *= row[dt];
  }
  return mult;
}

const FLAVOR_COMBOS = {
  'Spicy+Sweet':      { name: 'Sweet Heat Glaze', bonus: 1.3, healPct: 0.08 },
  'Sweet+Spicy':      { name: 'Sweet Heat Glaze', bonus: 1.3, healPct: 0.08 },
  'Savory+Fermented': { name: 'Umami Bomb', bonus: 1.35, healPct: 0.05 },
  'Fermented+Savory': { name: 'Umami Bomb', bonus: 1.35, healPct: 0.05 },
  'Fried+Pickled':    { name: 'Crunch & Tang', bonus: 1.3, healPct: 0.08 },
  'Pickled+Fried':    { name: 'Crunch & Tang', bonus: 1.3, healPct: 0.08 },
  'Brothy+Herbal':    { name: 'Aromatic Infusion', bonus: 1.25, healPct: 0.12 },
  'Herbal+Brothy':    { name: 'Aromatic Infusion', bonus: 1.25, healPct: 0.12 },
  'Toasted+Savory':   { name: 'Maillard Crust', bonus: 1.3, healPct: 0.06 },
  'Savory+Toasted':   { name: 'Maillard Crust', bonus: 1.3, healPct: 0.06 },
  'Steamed+Chilled':  { name: 'Al Dente Shock', bonus: 1.3, healPct: 0.08 },
  'Chilled+Steamed':  { name: 'Al Dente Shock', bonus: 1.3, healPct: 0.08 },
  'Raw+Pickled':      { name: 'Quick Ceviche', bonus: 1.3, healPct: 0.08 },
  'Pickled+Raw':      { name: 'Quick Ceviche', bonus: 1.3, healPct: 0.08 }
};

const MOVES = [
  // 0..50 from v1
  { id: 0,  name: 'Crust Bash',      type: 'Toasted',   power: 40, acc: 100, pp: 30, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'A hearty tackle with a golden-brown crust.' },
  { id: 1,  name: 'Panini Press',    type: 'Toasted',   power: 65, acc: 95,  pp: 20, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Flattens the foe between two hot plates.' },
  { id: 2,  name: 'Charred Slam',    type: 'Toasted',   power: 85, acc: 90,  pp: 15, temp: 1,  cat: 'physical', anim: 'flame',   desc: 'Smoky grill-marked impact. May Sizzle.', status: 'Sizzling', sChance: 0.2 },
  { id: 3,  name: 'Crouton Barrage', type: 'Toasted',   power: 55, acc: 100, pp: 25, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Launches a volley of noisy, crunchy cubes.' },
  { id: 4,  name: 'Hearth Toast',    type: 'Toasted',   power: 95, acc: 85,  pp: 10, temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Blast of oven-baked warmth.' },

  { id: 5,  name: 'Puff Bump',       type: 'Steamed',   power: 40, acc: 100, pp: 30, temp: 1,  cat: 'physical', anim: 'steam',   desc: 'A pillowy, surprisingly solid bounce.' },
  { id: 6,  name: 'Bamboo Mist',     type: 'Steamed',   power: 60, acc: 95,  pp: 20, temp: 1,  cat: 'special',  anim: 'steam',   desc: 'Envelops the target in fragrant steam.' },
  { id: 7,  name: 'Bao Squeeze',     type: 'Steamed',   power: 75, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'steam',   desc: 'Fluffy, inescapable hug. May make Drowsy.', status: 'Drowsy', sChance: 0.25 },
  { id: 8,  name: 'Geyser Vent',     type: 'Steamed',   power: 90, acc: 90,  pp: 10, temp: 1,  cat: 'special',  anim: 'steam',   desc: 'High-pressure kettle burst.' },
  { id: 9,  name: 'Soften Up',       type: 'Steamed',   power: 0,  acc: 100, pp: 20, temp: 1,  cat: 'status',   anim: 'steam',   desc: 'Makes the foe Appetized and relaxed.', status: 'Appetized', sChance: 1.0 },

  { id: 10, name: 'Skillet Pop',     type: 'Fried',     power: 45, acc: 100, pp: 25, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Crisp oil-pop strike.' },
  { id: 11, name: 'Tempura Crunch',  type: 'Fried',     power: 70, acc: 95,  pp: 15, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Light, shattering batter impact.' },
  { id: 12, name: 'Deep-Fry Surge',  type: 'Fried',     power: 95, acc: 85,  pp: 10, temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Bubbling golden oil wave. May Sizzle.', status: 'Sizzling', sChance: 0.3 },
  { id: 13, name: 'Crispy Toss',     type: 'Fried',     power: 55, acc: 100, pp: 20, temp: 1,  cat: 'physical', anim: 'whirl',   desc: 'Wok-tossed spin attack.' },

  { id: 14, name: 'Brine Flick',     type: 'Pickled',   power: 40, acc: 100, pp: 30, temp: -1, cat: 'special',  anim: 'splash',  desc: 'Sharp vinegar splash.' },
  { id: 15, name: 'Tangy Snap',      type: 'Pickled',   power: 65, acc: 95,  pp: 20, temp: -1, cat: 'physical', anim: 'slash',   desc: 'Tart, zesty bite that wakes the palate.' },
  { id: 16, name: 'Dill Surge',      type: 'Pickled',   power: 85, acc: 90,  pp: 15, temp: -1, cat: 'special',  anim: 'splash',  desc: 'Overwhelmingly briny wave. May Brine.', status: 'Brined', sChance: 0.3 },
  { id: 17, name: 'Pickle Jar',      type: 'Pickled',   power: 0,  acc: 95,  pp: 20, temp: -1, cat: 'status',   anim: 'splash',  desc: 'Brines the foe, lowering speed.', status: 'Brined', sChance: 1.0 },

  { id: 18, name: 'Pepper Puff',     type: 'Spicy',     power: 45, acc: 100, pp: 25, temp: 1,  cat: 'special',  anim: 'flame',   desc: 'A sneeze-inducing cloud of chili.' },
  { id: 19, name: 'Chili Oil Jet',   type: 'Spicy',     power: 70, acc: 95,  pp: 15, temp: 1,  cat: 'special',  anim: 'flame',   desc: 'Searing red oil stream. May Sizzle.', status: 'Sizzling', sChance: 0.25 },
  { id: 20, name: 'Scoville Nova',   type: 'Spicy',     power: 100,acc: 85,  pp: 10, temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Five-alarm pepper eruption.' },
  { id: 21, name: 'Wasabi Zing',     type: 'Spicy',     power: 60, acc: 100, pp: 20, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Instant sinus-clearing strike.' },

  { id: 22, name: 'Ladle Splash',    type: 'Brothy',    power: 40, acc: 100, pp: 30, temp: 0,  cat: 'special',  anim: 'splash',  desc: 'Warm spoonful of savory stock.' },
  { id: 23, name: 'Simmer Wave',     type: 'Brothy',    power: 65, acc: 95,  pp: 20, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Rolling tide of rich soup.' },
  { id: 24, name: 'Boil Over',       type: 'Brothy',    power: 90, acc: 90,  pp: 10, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Lid-rattling cauldron overflow.' },
  { id: 25, name: 'Slurp Drain',     type: 'Brothy',    power: 55, acc: 100, pp: 15, temp: 0,  cat: 'special',  anim: 'whirl',   desc: 'Siphons comforting broth to heal 30% dmg.', drain: 0.3 },

  { id: 26, name: 'Crisp Leaf',      type: 'Raw',       power: 40, acc: 100, pp: 30, temp: -1, cat: 'physical', anim: 'slash',   desc: 'Snappy garden-fresh slap.' },
  { id: 27, name: 'Sashimi Slice',   type: 'Raw',       power: 75, acc: 95,  pp: 15, temp: -1, cat: 'physical', anim: 'slash',   desc: 'Clean, precise knife-edge strike.' },
  { id: 28, name: 'Salad Toss',      type: 'Raw',       power: 60, acc: 100, pp: 20, temp: -1, cat: 'physical', anim: 'whirl',   desc: 'Whirling medley of fresh greens.' },
  { id: 29, name: 'Sprout Burst',    type: 'Raw',       power: 85, acc: 90,  pp: 15, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Vibrant, crunchy botanical surge.' },

  { id: 30, name: 'Miso Swirl',      type: 'Fermented', power: 45, acc: 100, pp: 25, temp: 0,  cat: 'special',  anim: 'whirl',   desc: 'Deep, funky paste vortex.' },
  { id: 31, name: 'Kimchi Kick',     type: 'Fermented', power: 70, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Zesty, bubbly martial kick.' },
  { id: 32, name: 'Sourdough Rise',  type: 'Fermented', power: 85, acc: 90,  pp: 15, temp: 0,  cat: 'special',  anim: 'steam',   desc: 'Unstoppable starter-culture swell.' },
  { id: 33, name: 'Kombucha Fizz',   type: 'Fermented', power: 60, acc: 100, pp: 20, temp: -1, cat: 'special',  anim: 'sparkle', desc: 'Effervescent tangy blast. May Season.', status: 'Seasoned', sChance: 0.3 },

  { id: 34, name: 'Sugar Glaze',     type: 'Sweet',     power: 40, acc: 100, pp: 30, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Sticky, shiny coating.' },
  { id: 35, name: 'Caramel Snap',    type: 'Sweet',     power: 70, acc: 95,  pp: 15, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Hard-crack spun sugar strike.' },
  { id: 36, name: 'Honey Drizzle',   type: 'Sweet',     power: 55, acc: 100, pp: 20, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Sweet coat that may make Drowsy.', status: 'Drowsy', sChance: 0.3 },
  { id: 37, name: 'Meringue Peak',   type: 'Sweet',     power: 85, acc: 90,  pp: 15, temp: 0,  cat: 'special',  anim: 'steam',   desc: 'Whipped cloud avalanche.' },

  { id: 38, name: 'Umami Tackle',    type: 'Savory',    power: 45, acc: 100, pp: 30, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Rich, satisfying full-body bump.' },
  { id: 39, name: 'Gravy Pour',      type: 'Savory',    power: 65, acc: 95,  pp: 20, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Velvety brown sauce deluge.' },
  { id: 40, name: 'Truffle Shave',   type: 'Savory',    power: 85, acc: 95,  pp: 10, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Luxurious aromatic strike.' },
  { id: 41, name: 'Roast Slam',      type: 'Savory',    power: 95, acc: 85,  pp: 10, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Slow-cooked heavy wallop.' },

  { id: 42, name: 'Ice Cube Toss',   type: 'Chilled',   power: 40, acc: 100, pp: 30, temp: -1, cat: 'physical', anim: 'chill',   desc: 'Clattering frozen cube.' },
  { id: 43, name: 'Gazpacho Splash', type: 'Chilled',   power: 65, acc: 95,  pp: 20, temp: -1, cat: 'special',  anim: 'chill',   desc: 'Refreshing cold tomato wave.' },
  { id: 44, name: 'Sorbet Freeze',   type: 'Chilled',   power: 85, acc: 90,  pp: 15, temp: -2, cat: 'special',  anim: 'chill',   desc: 'Brain-freeze flurry. May Brine.', status: 'Brined', sChance: 0.2 },
  { id: 45, name: 'Fridge Draft',    type: 'Chilled',   power: 55, acc: 100, pp: 20, temp: -1, cat: 'special',  anim: 'chill',   desc: 'Sudden blast of pantry cold.' },

  { id: 46, name: 'Basil Whip',      type: 'Herbal',    power: 45, acc: 100, pp: 30, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Fragrant green leaf lash.' },
  { id: 47, name: 'Rosemary Needle', type: 'Herbal',    power: 65, acc: 95,  pp: 20, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Piney, aromatic dart volley.' },
  { id: 48, name: 'Matcha Whisk',    type: 'Herbal',    power: 80, acc: 95,  pp: 15, temp: 0,  cat: 'special',  anim: 'whirl',   desc: 'Frothy emerald tea cyclone.' },
  { id: 49, name: 'Herb Garnish',    type: 'Herbal',    power: 0,  acc: 100, pp: 20, temp: 0,  cat: 'status',   anim: 'sparkle', desc: 'Seasons the foe, making it Appetized.', status: 'Appetized', sChance: 1.0 },
  { id: 50, name: 'Bay Leaf Aura',   type: 'Herbal',    power: 90, acc: 90,  pp: 10, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Ancient simmering aroma wave.' },

  // 51..123 New v2 Moves across all 12 types (124 total moves!)
  { id: 51, name: 'Toast Pop',       type: 'Toasted',   power: 50, acc: 100, pp: 25, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Spring-loaded pop from a warm slot.' },
  { id: 52, name: 'Brioche Roll',    type: 'Toasted',   power: 60, acc: 100, pp: 20, temp: 0,  cat: 'physical', anim: 'whirl',   desc: 'Buttery tumbling charge.' },
  { id: 53, name: 'Crumb Storm',     type: 'Toasted',   power: 75, acc: 95,  pp: 15, temp: 1,  cat: 'special',  anim: 'crunch',  desc: 'Swirling blizzard of golden panko.' },
  { id: 54, name: 'Broiler Beam',    type: 'Toasted',   power: 105,acc: 85,  pp: 5,  temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Top-rack radiant heat blast.' },
  { id: 55, name: 'Warm Butter',     type: 'Toasted',   power: 0,  acc: 100, pp: 20, temp: 1,  cat: 'status',   anim: 'sparkle', desc: 'Coats the foe in melted butter (Appetized).', status: 'Appetized', sChance: 1.0 },
  { id: 56, name: 'Rye Crunch',      type: 'Toasted',   power: 70, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Caraway-studded heavy bite.' },

  { id: 57, name: 'Dim Sum Spin',    type: 'Steamed',   power: 50, acc: 100, pp: 25, temp: 0,  cat: 'physical', anim: 'whirl',   desc: 'Turntable-fast spinning bump.' },
  { id: 58, name: 'Kettle Whistle',  type: 'Steamed',   power: 65, acc: 100, pp: 20, temp: 1,  cat: 'special',  anim: 'steam',   desc: 'Piercing steam-spout shriek.' },
  { id: 59, name: 'Cloud Knead',     type: 'Steamed',   power: 80, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'steam',   desc: 'Rhythmic dough-folding slam.' },
  { id: 60, name: 'Sauna Surge',     type: 'Steamed',   power: 100,acc: 85,  pp: 10, temp: 2,  cat: 'special',  anim: 'steam',   desc: 'Dense bamboo-tier steam eruption.' },
  { id: 61, name: 'Rice Pillow',     type: 'Steamed',   power: 45, acc: 100, pp: 25, temp: 0,  cat: 'physical', anim: 'steam',   desc: 'Soft sticky-rice cushion strike.' },
  { id: 62, name: 'Steamer Lid',     type: 'Steamed',   power: 55, acc: 100, pp: 20, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Clatters down like a heavy bamboo lid.' },

  { id: 63, name: 'Wok Toss',        type: 'Fried',     power: 60, acc: 100, pp: 20, temp: 1,  cat: 'physical', anim: 'whirl',   desc: 'High-arcing carbon-steel flip.' },
  { id: 64, name: 'Crackling Snap',  type: 'Fried',     power: 75, acc: 95,  pp: 15, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Loud, crispy golden crunch.' },
  { id: 65, name: 'Fritter Flurry',  type: 'Fried',     power: 85, acc: 90,  pp: 15, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Rapid combo of batter-fried strikes.' },
  { id: 66, name: 'Sizzle Spit',     type: 'Fried',     power: 50, acc: 100, pp: 25, temp: 1,  cat: 'special',  anim: 'flame',   desc: 'Tiny hot oil droplet spray. May Sizzle.', status: 'Sizzling', sChance: 0.2 },
  { id: 67, name: 'Golden Crust',    type: 'Fried',     power: 105,acc: 85,  pp: 5,  temp: 2,  cat: 'physical', anim: 'flame',   desc: 'Ultimate crispy double-fried impact.' },
  { id: 68, name: 'Hashbrown Bash',  type: 'Fried',     power: 65, acc: 95,  pp: 20, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Griddle-crisped potato slam.' },

  { id: 69, name: 'Vinegar Zing',    type: 'Pickled',   power: 50, acc: 100, pp: 25, temp: -1, cat: 'special',  anim: 'splash',  desc: 'Mouth-puckering cider splash.' },
  { id: 70, name: 'Caper Barrage',   type: 'Pickled',   power: 60, acc: 100, pp: 20, temp: -1, cat: 'physical', anim: 'crunch',  desc: 'Pelts the foe with salty flower buds.' },
  { id: 71, name: 'Relish Rush',     type: 'Pickled',   power: 75, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Zesty, sweet-tart tackle.' },
  { id: 72, name: 'Kraut Storm',     type: 'Pickled',   power: 95, acc: 90,  pp: 10, temp: -1, cat: 'special',  anim: 'whirl',   desc: 'Tangy shredded cabbage tempest.' },
  { id: 73, name: 'Yuzu Spritz',     type: 'Pickled',   power: 55, acc: 100, pp: 20, temp: -1, cat: 'special',  anim: 'sparkle', desc: 'Bright citrus-brine mist.' },
  { id: 74, name: 'Gherkin Jab',     type: 'Pickled',   power: 70, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Crisp, crunchy pickle poke.' },

  { id: 75, name: 'Paprika Dust',    type: 'Spicy',     power: 40, acc: 100, pp: 30, temp: 1,  cat: 'special',  anim: 'flame',   desc: 'Smoky red spice cloud.' },
  { id: 76, name: 'Sriracha Beam',   type: 'Spicy',     power: 80, acc: 95,  pp: 15, temp: 1,  cat: 'special',  anim: 'flame',   desc: 'Focused garlicky chili laser.' },
  { id: 77, name: 'Habanero Hop',    type: 'Spicy',     power: 75, acc: 95,  pp: 15, temp: 1,  cat: 'physical', anim: 'flame',   desc: 'Fiery bouncing tackle. May Sizzle.', status: 'Sizzling', sChance: 0.25 },
  { id: 78, name: 'Mala Tingle',     type: 'Spicy',     power: 65, acc: 100, pp: 20, temp: 1,  cat: 'special',  anim: 'sparkle', desc: 'Numbing Sichuan peppercorn shock.' },
  { id: 79, name: 'Ghost Pepper',    type: 'Spicy',     power: 110,acc: 80,  pp: 5,  temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Blistering volcanic spice blast.' },
  { id: 80, name: 'Cayenne Kick',    type: 'Spicy',     power: 55, acc: 100, pp: 25, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Quick pepper-dusted kick.' },

  { id: 81, name: 'Consomme Jet',    type: 'Brothy',    power: 50, acc: 100, pp: 25, temp: 0,  cat: 'special',  anim: 'splash',  desc: 'Crystal-clear stream of savory stock.' },
  { id: 82, name: 'Marrow Surge',    type: 'Brothy',    power: 80, acc: 95,  pp: 15, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Rich, velvety bone-broth wave.' },
  { id: 83, name: 'Noodle Whip',     type: 'Brothy',    power: 60, acc: 100, pp: 20, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Snap of a broth-soaked wheat ribbon.' },
  { id: 84, name: 'Pot Overflow',    type: 'Brothy',    power: 100,acc: 85,  pp: 10, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Tidal wave from a giant stockpot.' },
  { id: 85, name: 'Sip Restore',     type: 'Brothy',    power: 45, acc: 100, pp: 20, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Warm sip that heals 40% of damage dealt.', drain: 0.4 },
  { id: 86, name: 'Stock Bubble',    type: 'Brothy',    power: 70, acc: 95,  pp: 15, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Bursting simmer-pot bubbles.' },

  { id: 87, name: 'Radish Slice',    type: 'Raw',       power: 50, acc: 100, pp: 25, temp: -1, cat: 'physical', anim: 'slash',   desc: 'Peppery crisp root slash.' },
  { id: 88, name: 'Cabbage Crunch',  type: 'Raw',       power: 65, acc: 100, pp: 20, temp: -1, cat: 'physical', anim: 'crunch',  desc: 'Resounding snap of cold leaves.' },
  { id: 89, name: 'Nori Wrap',       type: 'Raw',       power: 55, acc: 100, pp: 20, temp: 0,  cat: 'physical', anim: 'whirl',   desc: 'Binds the foe in toasted seaweed.' },
  { id: 90, name: 'Tartare Strike',  type: 'Raw',       power: 95, acc: 90,  pp: 10, temp: -1, cat: 'physical', anim: 'slash',   desc: 'Precision knife-work finisher.' },
  { id: 91, name: 'Avocado Smash',   type: 'Raw',       power: 75, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Creamy green impact.' },
  { id: 92, name: 'Microgreen Mist', type: 'Raw',       power: 0,  acc: 100, pp: 20, temp: -1, cat: 'status',   anim: 'sparkle', desc: 'Refreshes and makes foe Appetized.', status: 'Appetized', sChance: 1.0 },

  { id: 93, name: 'Yeast Puff',      type: 'Fermented', power: 50, acc: 100, pp: 25, temp: 0,  cat: 'special',  anim: 'steam',   desc: 'Bubbly starter-dough pop.' },
  { id: 94, name: 'Tempeh Slam',     type: 'Fermented', power: 75, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Dense cultured-soy wallop.' },
  { id: 95, name: 'Kefir Wave',      type: 'Fermented', power: 65, acc: 100, pp: 20, temp: -1, cat: 'special',  anim: 'splash',  desc: 'Creamy, tangy probiotic splash.' },
  { id: 96, name: 'Natto Tangler',   type: 'Fermented', power: 60, acc: 95,  pp: 20, temp: 0,  cat: 'physical', anim: 'whirl',   desc: 'Sticky fermented threads. May Season.', status: 'Seasoned', sChance: 0.4 },
  { id: 97, name: 'Aged Cheddar',    type: 'Fermented', power: 95, acc: 90,  pp: 10, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Sharp, crystalline cave-aged slam.' },
  { id: 98, name: 'Starter Burst',   type: 'Fermented', power: 105,acc: 85,  pp: 5,  temp: 1,  cat: 'special',  anim: 'steam',   desc: 'Overnight-ferment pressure blast.' },

  { id: 99, name: 'Maple Pour',      type: 'Sweet',     power: 50, acc: 100, pp: 25, temp: 0,  cat: 'special',  anim: 'splash',  desc: 'Warm amber syrup cascade.' },
  { id: 100,name: 'Sprinkle Storm',  type: 'Sweet',     power: 60, acc: 100, pp: 20, temp: 0,  cat: 'physical', anim: 'sparkle', desc: 'Rainbow confetti sugar barrage.' },
  { id: 101,name: 'Custard Splash',  type: 'Sweet',     power: 75, acc: 95,  pp: 15, temp: 0,  cat: 'special',  anim: 'splash',  desc: 'Silky vanilla-bean wave.' },
  { id: 102,name: 'Brulee Torch',    type: 'Sweet',     power: 95, acc: 90,  pp: 10, temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Torches sugar into a glassy shell.' },
  { id: 103,name: 'Frosting Swirl',  type: 'Sweet',     power: 0,  acc: 100, pp: 20, temp: 0,  cat: 'status',   anim: 'sparkle', desc: 'Makes the foe Drowsy with sugar.', status: 'Drowsy', sChance: 1.0 },
  { id: 104,name: 'Fudge Crash',     type: 'Sweet',     power: 80, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Dense chocolate-ganache tackle.' },

  { id: 105,name: 'Mushroom Bash',   type: 'Savory',    power: 55, acc: 100, pp: 25, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Earthy shiitake-powered bump.' },
  { id: 106,name: 'Parmesan Snow',   type: 'Savory',    power: 60, acc: 100, pp: 20, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Grated umami flurry.' },
  { id: 107,name: 'Jus Splash',      type: 'Savory',    power: 75, acc: 95,  pp: 15, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Concentrated pan-dripping wave.' },
  { id: 108,name: 'Bacon Snap',      type: 'Savory',    power: 80, acc: 95,  pp: 15, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Smoky, crispy strip lash.' },
  { id: 109,name: 'Demi-Glace',      type: 'Savory',    power: 105,acc: 85,  pp: 5,  temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Twenty-four-hour reduction deluge.' },
  { id: 110,name: 'Sesame Press',    type: 'Savory',    power: 70, acc: 100, pp: 15, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Nutty toasted-sesame slam.' },

  { id: 111,name: 'Frost Bite',      type: 'Chilled',   power: 50, acc: 100, pp: 25, temp: -1, cat: 'physical', anim: 'chill',   desc: 'Crisp freezer-frost nip.' },
  { id: 112,name: 'Granita Shard',   type: 'Chilled',   power: 75, acc: 95,  pp: 15, temp: -1, cat: 'special',  anim: 'chill',   desc: 'Crunchy shaved-ice crystals.' },
  { id: 113,name: 'Gelato Spin',     type: 'Chilled',   power: 70, acc: 100, pp: 15, temp: -1, cat: 'physical', anim: 'whirl',   desc: 'Dense, creamy frozen swirl.' },
  { id: 114,name: 'Cryo Broth',      type: 'Chilled',   power: 95, acc: 90,  pp: 10, temp: -2, cat: 'special',  anim: 'chill',   desc: 'Sub-zero consomme wave.' },
  { id: 115,name: 'Ice Bath',        type: 'Chilled',   power: 0,  acc: 100, pp: 20, temp: -2, cat: 'status',   anim: 'chill',   desc: 'Plunges Kitchen Temp to Chilled and Brines.', status: 'Brined', sChance: 1.0 },
  { id: 116,name: 'Mint Slush',      type: 'Chilled',   power: 60, acc: 100, pp: 20, temp: -1, cat: 'special',  anim: 'chill',   desc: 'Cooling crushed-ice splash.' },

  { id: 117,name: 'Cilantro Slap',   type: 'Herbal',    power: 50, acc: 100, pp: 25, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Divisive yet refreshing herb strike.' },
  { id: 118,name: 'Thyme Sprig',     type: 'Herbal',    power: 60, acc: 100, pp: 20, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Woodsy aromatic volley.' },
  { id: 119,name: 'Sage Smoke',      type: 'Herbal',    power: 75, acc: 95,  pp: 15, temp: 1,  cat: 'special',  anim: 'steam',   desc: 'Brown-butter sage cloud. May Drowsy.', status: 'Drowsy', sChance: 0.25 },
  { id: 120,name: 'Oregano Gust',    type: 'Herbal',    power: 70, acc: 95,  pp: 15, temp: 0,  cat: 'special',  anim: 'whirl',   desc: 'Pizza-parlor spice whirlwind.' },
  { id: 121,name: 'Bouquet Garni',   type: 'Herbal',    power: 100,acc: 90,  pp: 10, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Tied bundle of ancient culinary herbs.' },
  { id: 122,name: 'Scallion Lash',   type: 'Herbal',    power: 55, acc: 100, pp: 25, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Snappy green-onion whip.' },
  { id: 123,name: 'Star Anise Ray',  type: 'Herbal',    power: 85, acc: 95,  pp: 10, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Warm, licorice-scented pho beam.' }
];
