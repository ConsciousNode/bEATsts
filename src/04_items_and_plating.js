// 04_items_and_plating.js - Items, Place-Setting Tiers, and Exact Plating Formula

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
  }
};

const SHOP_STOCK = [
  'paper_plate', 'wooden_board', 'ceramic_plate', 'bento_set', 'royal_banquet',
  'broth_cup', 'hearty_stew', 'grand_feast', 'mint_tea', 'wakeup_espresso', 'garnish_treat'
];

// Exact Plating Probability Formula:
// P(join) = min(0.95, baseRate * plateBonus * hpFactor * statusBonus * favBonus * timeBonus)
// where:
//   hpFactor    = (3 * maxHp - 2 * curHp) / (3 * maxHp)   [0.333 at full HP -> ~1.0 at 1 HP]
//   statusBonus = status === 'Appetized' ? 1.5 : (status ? 1.3 : 1.0)
//   favBonus    = usedFavTreat ? 1.6 : 1.0
//   timeBonus   = (species.nightOnly && isNight) ? 1.35 : 1.0
// Note: if species.minTier && plateItem.tier < species.minTier, returns 0 (needs fancier plate!)
//       if species.nightOnly && !isNight, returns 0 (only joins at night!)
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
