// 01_types_and_moves.js - 12 Cooking Types, Type Chart, Flavor Combos, and Moves

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

// Original Battle Mechanic: Kitchen Temp (-2 Chilled .. +2 Searing) & Flavor Combos
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
  // Toasted
  { id: 0,  name: 'Crust Bash',      type: 'Toasted',   power: 40, acc: 100, pp: 30, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'A hearty tackle with a golden-brown crust.' },
  { id: 1,  name: 'Panini Press',    type: 'Toasted',   power: 65, acc: 95,  pp: 20, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Flattens the foe between two hot plates.' },
  { id: 2,  name: 'Charred Slam',    type: 'Toasted',   power: 85, acc: 90,  pp: 15, temp: 1,  cat: 'physical', anim: 'flame',   desc: 'Smoky grill-marked impact. May Sizzle.', status: 'Sizzling', sChance: 0.2 },
  { id: 3,  name: 'Crouton Barrage', type: 'Toasted',   power: 55, acc: 100, pp: 25, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Launches a volley of noisy, crunchy cubes.' },
  { id: 4,  name: 'hearth-Toast',    type: 'Toasted',   power: 95, acc: 85,  pp: 10, temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Blast of oven-baked warmth.' },

  // Steamed
  { id: 5,  name: 'Puff Bump',       type: 'Steamed',   power: 40, acc: 100, pp: 30, temp: 1,  cat: 'physical', anim: 'steam',   desc: 'A pillowy, surprisingly solid bounce.' },
  { id: 6,  name: 'Bamboo Mist',     type: 'Steamed',   power: 60, acc: 95,  pp: 20, temp: 1,  cat: 'special',  anim: 'steam',   desc: 'Envelops the target in fragrant steam.' },
  { id: 7,  name: 'Bao Squeeze',     type: 'Steamed',   power: 75, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'steam',   desc: 'Fluffy, inescapable hug. May make Drowsy.', status: 'Drowsy', sChance: 0.25 },
  { id: 8,  name: 'Geyser Vent',     type: 'Steamed',   power: 90, acc: 90,  pp: 10, temp: 1,  cat: 'special',  anim: 'steam',   desc: 'High-pressure kettle burst.' },
  { id: 9,  name: 'Soften Up',       type: 'Steamed',   power: 0,  acc: 100, pp: 20, temp: 1,  cat: 'status',   anim: 'steam',   desc: 'Makes the foe Appetized and relaxed.', status: 'Appetized', sChance: 1.0 },

  // Fried
  { id: 10, name: 'Skillet Pop',     type: 'Fried',     power: 45, acc: 100, pp: 25, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Crisp oil-pop strike.' },
  { id: 11, name: 'Tempura Crunch',  type: 'Fried',     power: 70, acc: 95,  pp: 15, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Light, shattering batter impact.' },
  { id: 12, name: 'Deep-Fry Surge',  type: 'Fried',     power: 95, acc: 85,  pp: 10, temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Bubbling golden oil wave. May Sizzle.', status: 'Sizzling', sChance: 0.3 },
  { id: 13, name: 'Crispy Toss',     type: 'Fried',     power: 55, acc: 100, pp: 20, temp: 1,  cat: 'physical', anim: 'whirl',   desc: 'Wok-tossed spin attack.' },

  // Pickled
  { id: 14, name: 'Brine Flick',     type: 'Pickled',   power: 40, acc: 100, pp: 30, temp: -1, cat: 'special',  anim: 'splash',  desc: 'Sharp vinegar splash.' },
  { id: 15, name: 'Tangy Snap',      type: 'Pickled',   power: 65, acc: 95,  pp: 20, temp: -1, cat: 'physical', anim: 'slash',   desc: 'Tart, zesty bite that wakes the palate.' },
  { id: 16, name: 'Dill Surge',      type: 'Pickled',   power: 85, acc: 90,  pp: 15, temp: -1, cat: 'special',  anim: 'splash',  desc: 'Overwhelmingly briny wave. May Brine.', status: 'Brined', sChance: 0.3 },
  { id: 17, name: 'Pickle Jar',      type: 'Pickled',   power: 0,  acc: 95,  pp: 20, temp: -1, cat: 'status',   anim: 'splash',  desc: 'Brines the foe, lowering speed.', status: 'Brined', sChance: 1.0 },

  // Spicy
  { id: 18, name: 'Pepper Puff',     type: 'Spicy',     power: 45, acc: 100, pp: 25, temp: 1,  cat: 'special',  anim: 'flame',   desc: 'A sneeze-inducing cloud of chili.' },
  { id: 19, name: 'Chili Oil Jet',   type: 'Spicy',     power: 70, acc: 95,  pp: 15, temp: 1,  cat: 'special',  anim: 'flame',   desc: 'Searing red oil stream. May Sizzle.', status: 'Sizzling', sChance: 0.25 },
  { id: 20, name: 'Scoville Nova',   type: 'Spicy',     power: 100,acc: 85,  pp: 10, temp: 2,  cat: 'special',  anim: 'flame',   desc: 'Five-alarm pepper eruption.' },
  { id: 21, name: 'Wasabi Zing',     type: 'Spicy',     power: 60, acc: 100, pp: 20, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Instant sinus-clearing strike.' },

  // Brothy
  { id: 22, name: 'Ladle Splash',    type: 'Brothy',    power: 40, acc: 100, pp: 30, temp: 0,  cat: 'special',  anim: 'splash',  desc: 'Warm spoonful of savory stock.' },
  { id: 23, name: 'Simmer Wave',     type: 'Brothy',    power: 65, acc: 95,  pp: 20, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Rolling tide of rich soup.' },
  { id: 24, name: 'Boil Over',       type: 'Brothy',    power: 90, acc: 90,  pp: 10, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Lid-rattling cauldron overflow.' },
  { id: 25, name: 'Slurp Drain',     type: 'Brothy',    power: 55, acc: 100, pp: 15, temp: 0,  cat: 'special',  anim: 'whirl',   desc: 'Siphons comforting broth to heal 30% dmg.', drain: 0.3 },

  // Raw
  { id: 26, name: 'Crisp Leaf',      type: 'Raw',       power: 40, acc: 100, pp: 30, temp: -1, cat: 'physical', anim: 'slash',   desc: 'Snappy garden-fresh slap.' },
  { id: 27, name: 'Sashimi Slice',   type: 'Raw',       power: 75, acc: 95,  pp: 15, temp: -1, cat: 'physical', anim: 'slash',   desc: 'Clean, precise knife-edge strike.' },
  { id: 28, name: 'Salad Toss',      type: 'Raw',       power: 60, acc: 100, pp: 20, temp: -1, cat: 'physical', anim: 'whirl',   desc: 'Whirling medley of fresh greens.' },
  { id: 29, name: 'Sprout Burst',    type: 'Raw',       power: 85, acc: 90,  pp: 15, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Vibrant, crunchy botanical surge.' },

  // Fermented
  { id: 30, name: 'Miso Swirl',      type: 'Fermented', power: 45, acc: 100, pp: 25, temp: 0,  cat: 'special',  anim: 'whirl',   desc: 'Deep, funky paste vortex.' },
  { id: 31, name: 'Kimchi Kick',     type: 'Fermented', power: 70, acc: 95,  pp: 15, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Zesty, bubbly martial kick.' },
  { id: 32, name: 'Sourdough Rise',  type: 'Fermented', power: 85, acc: 90,  pp: 15, temp: 0,  cat: 'special',  anim: 'steam',   desc: 'Unstoppable starter-culture swell.' },
  { id: 33, name: 'Kombucha Fizz',   type: 'Fermented', power: 60, acc: 100, pp: 20, temp: -1, cat: 'special',  anim: 'sparkle', desc: 'Effervescent tangy blast. May Season.', status: 'Seasoned', sChance: 0.3 },

  // Sweet
  { id: 34, name: 'Sugar Glaze',     type: 'Sweet',     power: 40, acc: 100, pp: 30, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Sticky, shiny coating.' },
  { id: 35, name: 'Caramel Snap',    type: 'Sweet',     power: 70, acc: 95,  pp: 15, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Hard-crack spun sugar strike.' },
  { id: 36, name: 'Honey Drizzle',   type: 'Sweet',     power: 55, acc: 100, pp: 20, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Sweet coat that may make Drowsy.', status: 'Drowsy', sChance: 0.3 },
  { id: 37, name: 'Meringue Peak',   type: 'Sweet',     power: 85, acc: 90,  pp: 15, temp: 0,  cat: 'special',  anim: 'steam',   desc: 'Whipped cloud avalanche.' },

  // Savory
  { id: 38, name: 'Umami Tackle',    type: 'Savory',    power: 45, acc: 100, pp: 30, temp: 0,  cat: 'physical', anim: 'crunch',  desc: 'Rich, satisfying full-body bump.' },
  { id: 39, name: 'Gravy Pour',      type: 'Savory',    power: 65, acc: 95,  pp: 20, temp: 1,  cat: 'special',  anim: 'splash',  desc: 'Velvety brown sauce deluge.' },
  { id: 40, name: 'Truffle Shave',   type: 'Savory',    power: 85, acc: 95,  pp: 10, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Luxurious aromatic strike.' },
  { id: 41, name: 'Roast Slam',      type: 'Savory',    power: 95, acc: 85,  pp: 10, temp: 1,  cat: 'physical', anim: 'crunch',  desc: 'Slow-cooked heavy wallop.' },

  // Chilled
  { id: 42, name: 'Ice Cube Toss',   type: 'Chilled',   power: 40, acc: 100, pp: 30, temp: -1, cat: 'physical', anim: 'chill',   desc: 'Clattering frozen cube.' },
  { id: 43, name: 'Gazpacho Splash', type: 'Chilled',   power: 65, acc: 95,  pp: 20, temp: -1, cat: 'special',  anim: 'chill',   desc: 'Refreshing cold tomato wave.' },
  { id: 44, name: 'Sorbet Freeze',   type: 'Chilled',   power: 85, acc: 90,  pp: 15, temp: -2, cat: 'special',  anim: 'chill',   desc: 'Brain-freeze flurry. May Brine.', status: 'Brined', sChance: 0.2 },
  { id: 45, name: 'Fridge Draft',    type: 'Chilled',   power: 55, acc: 100, pp: 20, temp: -1, cat: 'special',  anim: 'chill',   desc: 'Sudden blast of pantry cold.' },

  // Herbal
  { id: 46, name: 'Basil Whip',      type: 'Herbal',    power: 45, acc: 100, pp: 30, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Fragrant green leaf lash.' },
  { id: 47, name: 'Rosemary Needle', type: 'Herbal',    power: 65, acc: 95,  pp: 20, temp: 0,  cat: 'physical', anim: 'slash',   desc: 'Piney, aromatic dart volley.' },
  { id: 48, name: 'Matcha Whisk',    type: 'Herbal',    power: 80, acc: 95,  pp: 15, temp: 0,  cat: 'special',  anim: 'whirl',   desc: 'Frothy emerald tea cyclone.' },
  { id: 49, name: 'Herb Garnish',    type: 'Herbal',    power: 0,  acc: 100, pp: 20, temp: 0,  cat: 'status',   anim: 'sparkle', desc: 'Seasons the foe, making it Appetized.', status: 'Appetized', sChance: 1.0 },
  { id: 50, name: 'Bay Leaf Aura',   type: 'Herbal',    power: 90, acc: 90,  pp: 10, temp: 0,  cat: 'special',  anim: 'sparkle', desc: 'Ancient simmering aroma wave.' }
];
