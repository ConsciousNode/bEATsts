// 04_items_and_plating.js - Items, 5 Place-Setting Tiers, 12 Recipe Cards, Progressive Regional Shops, & Plating Formula
// PROVENANCE: Core ITEMS and calcPlatingChance lifted from beatsts-v1/src/04_items_and_plating.js; extended with Recipe Cards and progressive REGIONAL_SHOPS.

const ITEMS = {
  paper_plate: {
    id: 'paper_plate', name: 'Paper Plate', kind: 'plate', tier: 1, plateBonus: 1.0, price: 50,
    desc: 'A humble picnic paper plate. Slightly bends under heavy gravy, yet oddly inviting.'
  },
  wooden_board: {
    id: 'wooden_board', name: 'Wooden Board', kind: 'plate', tier: 2, plateBonus: 1.5, price: 150,
    desc: 'Rustic acacia charcuterie board. Makes even a rebellious pickle feel artisan.'
  },
  ceramic_plate: {
    id: 'ceramic_plate', name: 'Ceramic Plate', kind: 'plate', tier: 3, plateBonus: 2.2, price: 400,
    desc: 'Warm glazed stoneware with a hand-painted rim. bEATsts instinctively wipe their feet.'
  },
  bento_set: {
    id: 'bento_set', name: 'Bento Lacquer Set', kind: 'plate', tier: 4, plateBonus: 3.2, price: 900,
    desc: 'Four-compartment lacquered tray with matching chopsticks and a tiny folded napkin.'
  },
  royal_banquet: {
    id: 'royal_banquet', name: 'Royal Banquet Setting', kind: 'plate', tier: 5, plateBonus: 5.0, price: 2000,
    desc: 'Gold-rimmed porcelain, crystal ladle, and candlelight. Even mythical soups sit down.'
  },
  broth_cup: {
    id: 'broth_cup', name: 'Warm Broth Cup', kind: 'heal', healHp: 25, price: 40,
    desc: 'Restores 25 HP. Smells like someone cares about your hydration.'
  },
  hearty_stew: {
    id: 'hearty_stew', name: 'Hearty Stew', kind: 'heal', healHp: 65, price: 120,
    desc: 'Restores 65 HP. Thick enough to stand a wooden spoon straight up.'
  },
  grand_feast: {
    id: 'grand_feast', name: 'Grand Feast', kind: 'heal', healHp: 999, price: 350,
    desc: 'Fully restores HP and clears any kitchen status condition.'
  },
  mint_tea: {
    id: 'mint_tea', name: 'Peppermint Tea', kind: 'cure', price: 60,
    desc: 'Clears Sizzling, Brined, Drowsy, or Seasoned status.'
  },
  wakeup_espresso: {
    id: 'wakeup_espresso', name: 'Double Espresso', kind: 'revive', price: 250,
    desc: 'Revives a fainted bEATst with 50% HP. Do not give to toddlers.'
  },
  garnish_treat: {
    id: 'garnish_treat', name: 'Chef Garnish Treat', kind: 'treat', price: 100,
    desc: 'Sprinkled in wild battles to delight a bEATst (+60% plating chance!).'
  },
  // 12 Move-Teaching Recipe Cards (one per type)
  card_toasted:   { id: 'card_toasted',   name: 'Recipe: Hearth Toast',   kind: 'recipe', moveId: 4,   price: 600, desc: 'Teaches Hearth Toast (Toasted, 95 PWR).' },
  card_steamed:   { id: 'card_steamed',   name: 'Recipe: Geyser Vent',    kind: 'recipe', moveId: 8,   price: 600, desc: 'Teaches Geyser Vent (Steamed, 90 PWR).' },
  card_fried:     { id: 'card_fried',     name: 'Recipe: Deep-Fry Surge', kind: 'recipe', moveId: 12,  price: 650, desc: 'Teaches Deep-Fry Surge (Fried, 95 PWR).' },
  card_pickled:   { id: 'card_pickled',   name: 'Recipe: Kraut Storm',    kind: 'recipe', moveId: 72,  price: 650, desc: 'Teaches Kraut Storm (Pickled, 95 PWR).' },
  card_spicy:     { id: 'card_spicy',     name: 'Recipe: Sriracha Beam',  kind: 'recipe', moveId: 76,  price: 600, desc: 'Teaches Sriracha Beam (Spicy, 80 PWR).' },
  card_brothy:    { id: 'card_brothy',    name: 'Recipe: Boil Over',      kind: 'recipe', moveId: 24,  price: 650, desc: 'Teaches Boil Over (Brothy, 90 PWR).' },
  card_raw:       { id: 'card_raw',       name: 'Recipe: Tartare Strike', kind: 'recipe', moveId: 90,  price: 650, desc: 'Teaches Tartare Strike (Raw, 95 PWR).' },
  card_fermented: { id: 'card_fermented', name: 'Recipe: Aged Cheddar',   kind: 'recipe', moveId: 97,  price: 650, desc: 'Teaches Aged Cheddar (Fermented, 95 PWR).' },
  card_sweet:     { id: 'card_sweet',     name: 'Recipe: Brulee Torch',   kind: 'recipe', moveId: 102, price: 650, desc: 'Teaches Brulee Torch (Sweet, 95 PWR).' },
  card_savory:    { id: 'card_savory',    name: 'Recipe: Demi-Glace',     kind: 'recipe', moveId: 109, price: 700, desc: 'Teaches Demi-Glace (Savory, 105 PWR).' },
  card_chilled:   { id: 'card_chilled',   name: 'Recipe: Cryo Broth',     kind: 'recipe', moveId: 114, price: 650, desc: 'Teaches Cryo Broth (Chilled, 95 PWR).' },
  card_herbal:    { id: 'card_herbal',    name: 'Recipe: Bouquet Garni',  kind: 'recipe', moveId: 121, price: 700, desc: 'Teaches Bouquet Garni (Herbal, 100 PWR).' }
};

// Progressive Pantry Mart inventories by region
const REGIONAL_SHOPS = {
  Breadlands: {
    clerkLine: 'Breadlands Pantry Mart! Fresh Paper Plates, Wooden Boards, and Warm Broth Cups!',
    stock: ['paper_plate', 'wooden_board', 'broth_cup', 'mint_tea', 'garnish_treat', 'card_toasted', 'card_savory']
  },
  Steambay: {
    clerkLine: 'Steambay Pantry Mart! Ceramic Plates, Hearty Stews, and Steamer Recipes now unlocked!',
    stock: ['paper_plate', 'wooden_board', 'ceramic_plate', 'broth_cup', 'hearty_stew', 'mint_tea', 'garnish_treat', 'card_steamed', 'card_fried', 'card_pickled']
  },
  Noodleridge: {
    clerkLine: 'Noodleridge Pantry Mart! Bento Lacquer Sets and Double Espresso for mountain climbs!',
    stock: ['wooden_board', 'ceramic_plate', 'bento_set', 'hearty_stew', 'wakeup_espresso', 'mint_tea', 'garnish_treat', 'card_spicy', 'card_raw', 'card_herbal']
  },
  Brothbasin: {
    clerkLine: 'Brothbasin Pantry Mart! Royal Banquet Settings and Grand Feasts are finally in stock!',
    stock: ['ceramic_plate', 'bento_set', 'royal_banquet', 'hearty_stew', 'grand_feast', 'wakeup_espresso', 'garnish_treat', 'card_brothy', 'card_fermented', 'card_chilled', 'card_sweet']
  },
  Postgame: {
    clerkLine: 'Eternal Pantry Boutique! Every plate tier and all master Recipe Cards available!',
    stock: Object.keys(ITEMS)
  }
};

function calcPlatingChance(species, curHp, maxHp, status, usedFavTreat, isNight, plateItem) {
  if (!species || !plateItem || plateItem.kind !== 'plate') return 0;
  if (species.nightOnly && !isNight) return 0;
  if (species.minTier && plateItem.tier < species.minTier) return 0;
  const hpFactor = Math.max(0.1, (3 * maxHp - 2 * curHp) / (3 * maxHp));
  const statusBonus = status === 'Appetized' ? 1.5 : (status ? 1.3 : 1.0);
  const favBonus = usedFavTreat ? 1.6 : 1.0;
  const timeBonus = (species.nightOnly && isNight) ? 1.35 : 1.0;
  const raw = species.catchRate * plateItem.plateBonus * hpFactor * statusBonus * favBonus * timeBonus;
  return Math.min(0.95, Math.max(0, raw));
}
