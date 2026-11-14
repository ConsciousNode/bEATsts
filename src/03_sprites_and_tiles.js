// 03_sprites_and_tiles.js - GBA 8x8 Tiles, 16-Color 15-bit Palettes, and 151x2 Unique 24x24 Sprites

const TYPE_PALETTE_ACCENTS = {
  Toasted:   ['#E8A850', '#B86820', '#F8D890'],
  Steamed:   ['#F0F8F8', '#B8D8E0', '#FFFFFF'],
  Fried:     ['#F0C040', '#C08018', '#FFF0A0'],
  Pickled:   ['#98D830', '#589018', '#D0F880'],
  Spicy:     ['#F04030', '#A81818', '#FF9850'],
  Brothy:    ['#5090C8', '#285888', '#A8D8F8'],
  Raw:       ['#60C878', '#288048', '#B0F0B8'],
  Fermented: ['#A868E0', '#683098', '#D8B0F8'],
  Sweet:     ['#FF88B8', '#C84880', '#FFD0E8'],
  Savory:    ['#A86848', '#683820', '#D8A880'],
  Chilled:   ['#60D8F8', '#2890C0', '#D0F8FF'],
  Herbal:    ['#389860', '#185838', '#88E0A0']
};

function buildSpeciesPalette(sp) {
  const t1 = TYPE_PALETTE_ACCENTS[sp.types[0]] || TYPE_PALETTE_ACCENTS.Savory;
  const t2 = TYPE_PALETTE_ACCENTS[sp.types[1] || sp.types[0]] || t1;
  // 16 colors max: index 0 is transparent (null)
  const raw = [
    null,
    '#181820', // 1: dark outline
    t1[0],    // 2: primary body
    t1[1],    // 3: primary shadow
    t1[2],    // 4: primary highlight
    t2[0],    // 5: secondary/filling
    t2[1],    // 6: secondary shadow
    t2[2],    // 7: secondary highlight
    '#F8F8F0', // 8: white (eyes/steam/rice)
    '#F0C868', // 9: crust/noodle gold
    '#D04038', // 10: tomato/chili/blush
    '#50B848', // 11: lettuce/scallion/herb
    '#F8E888', // 12: cheese/butter/broth glow
    '#885030', // 13: wood/pot/crust dark
    '#C0C8D0', // 14: bowl/metal/ceramic
    '#FF90A8'  // 15: cute cheek/sweet accent
  ];
  return raw.map(c => c ? toGba15(c) : null);
}

function makeGrid24() { return new Uint8Array(24 * 24); }
function setPx(g, x, y, c) {
  if (x >= 0 && x < 24 && y >= 0 && y < 24) g[y * 24 + x] = c;
}
function fillRect(g, x0, y0, w, h, c) {
  for (let y = y0; y < y0 + h; y++)
    for (let x = x0; x < x0 + w; x++) setPx(g, x, y, c);
}
function fillEllipse(g, cx, cy, rx, ry, c) {
  for (let y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++) {
    for (let x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
      const dx = (x - cx) / rx, dy = (y - cy) / ry;
      if (dx * dx + dy * dy <= 1.0) setPx(g, x, y, c);
    }
  }
}
function outlineGrid(g, outlineIdx = 1) {
  const copy = new Uint8Array(g);
  for (let y = 0; y < 24; y++) {
    for (let x = 0; x < 24; x++) {
      if (copy[y * 24 + x] !== 0) continue;
      const n = (y > 0 && copy[(y-1)*24+x]) || (y < 23 && copy[(y+1)*24+x]) ||
                (x > 0 && copy[y*24+(x-1)]) || (x < 23 && copy[y*24+(x+1)]);
      if (n) g[y * 24 + x] = outlineIdx;
    }
  }
}

function drawBeatstSprite(sp, isBack) {
  const g = makeGrid24();
  const id = sp.id;
  const vBody = id % 4;
  const vTop  = Math.floor(id / 4) % 5;
  const vLimb = Math.floor(id / 20) % 4;
  const vEye  = id % 3;

  // 1. Base food-family silhouette
  if (sp.family === 'Sandwiches') {
    if (vBody === 0) {
      // Classic stacked sandwich
      fillRect(g, 5, 7, 14, 3, 9);   // top bread
      fillRect(g, 6, 6, 12, 1, 4);   // highlight
      fillRect(g, 4, 10, 16, 2, 11); // lettuce
      fillRect(g, 5, 12, 14, 2, 5);  // filling
      fillRect(g, 5, 14, 14, 2, 10); // tomato
      fillRect(g, 5, 16, 14, 3, 9);  // bottom bread
    } else if (vBody === 1) {
      // Baguette / Sub
      fillEllipse(g, 12, 12, 9, 4.5, 9);
      fillRect(g, 5, 11, 14, 2, 5);
      fillRect(g, 6, 10, 12, 1, 11);
    } else if (vBody === 2) {
      // Burger / Bun
      fillEllipse(g, 12, 9, 7, 4, 9);
      fillRect(g, 5, 12, 14, 2, 12); // cheese
      fillRect(g, 5, 14, 14, 2, 13); // patty
      fillRect(g, 6, 16, 12, 3, 9);  // bottom bun
    } else {
      // Triangular club / toast
      for (let r = 0; r < 11; r++) {
        fillRect(g, 12 - Math.floor(r * 0.7), 6 + r, Math.floor(r * 1.4) + 2, 1, r < 4 ? 9 : (r < 7 ? 5 : 2));
      }
    }
  } else if (sp.family === 'Dumplings') {
    if (vBody === 0) {
      // Baozi round bun with top knot
      fillEllipse(g, 12, 13, 7.5, 6, 2);
      fillEllipse(g, 12, 7, 3, 2, 4);
      fillRect(g, 9, 15, 6, 3, 3);
    } else if (vBody === 1) {
      // Crescent gyoza
      fillEllipse(g, 12, 14, 8, 5, 2);
      for (let i = 0; i < 5; i++) setPx(g, 7 + i * 2, 8 + (i % 2), 4);
      fillRect(g, 6, 17, 12, 2, 9); // crispy skirt
    } else if (vBody === 2) {
      // Shumai basket
      fillRect(g, 6, 9, 12, 9, 9);
      fillEllipse(g, 12, 9, 6, 2.5, 5);
      setPx(g, 12, 8, 11); setPx(g, 13, 8, 11); // green pea
    } else {
      // Triangle onigiri/samosa
      for (let r = 0; r < 12; r++) {
        fillRect(g, 12 - Math.floor(r * 0.65), 7 + r, Math.floor(r * 1.3) + 2, 1, 2);
      }
      fillRect(g, 9, 15, 6, 4, 1); // nori wrap
    }
  } else if (sp.family === 'Noodles') {
    // Bowl + wavy noodle mound
    fillEllipse(g, 12, 15, 8, 4.5, 14);
    fillRect(g, 5, 11, 14, 3, 14);
    fillEllipse(g, 12, 10, 7, 3.5, 9);
    for (let x = 7; x <= 17; x += 2) {
      setPx(g, x, 9 + (x % 3), 12);
      setPx(g, x, 11 - (x % 2), 3);
    }
    if (vBody >= 2) {
      // Chopsticks or tall noodle swirl
      for (let i = 0; i < 6; i++) { setPx(g, 14 + i, 5 + i, 13); setPx(g, 15 + i, 4 + i, 13); }
    }
  } else {
    // Soup: Pot / Cauldron / Bowl with glowing broth
    fillEllipse(g, 12, 14, 7.5, 5, vBody % 2 === 0 ? 13 : 14);
    fillRect(g, 5, 10, 14, 3, vBody % 2 === 0 ? 13 : 14);
    fillEllipse(g, 12, 10, 6.5, 2, 5); // broth surface
    setPx(g, 3, 12, 14); setPx(g, 4, 12, 14); // left handle
    setPx(g, 19, 12, 14); setPx(g, 20, 12, 14); // right handle
  }

  // 2. Toppings / Ears / Steam / Skewer (varies by vTop)
  if (vTop === 0) {
    // Cute toothpick / skewer flag
    for (let y = 2; y <= 6; y++) setPx(g, 12, y, 13);
    fillRect(g, 13, 2, 3, 2, 10);
  } else if (vTop === 1) {
    // Steam wisps
    setPx(g, 9, 4, 8); setPx(g, 8, 3, 8); setPx(g, 14, 4, 8); setPx(g, 15, 2, 8);
  } else if (vTop === 2) {
    // Herb leaf / sprout ears
    fillRect(g, 8, 4, 2, 2, 11); fillRect(g, 14, 4, 2, 2, 11);
  } else if (vTop === 3) {
    // Chili / Pepper horns
    setPx(g, 7, 5, 10); setPx(g, 6, 4, 10); setPx(g, 16, 5, 10); setPx(g, 17, 4, 10);
  } else {
    // Crown / Cream dollop
    fillRect(g, 9, 4, 6, 2, 12); setPx(g, 12, 3, 8);
  }

  // 3. Limbs / Feet (varies by vLimb)
  if (vLimb === 0) {
    fillRect(g, 7, 19, 3, 2, 3); fillRect(g, 14, 19, 3, 2, 3);
  } else if (vLimb === 1) {
    fillRect(g, 6, 18, 2, 3, 6); fillRect(g, 16, 18, 2, 3, 6);
  } else if (vLimb === 2) {
    // Floating tail/ribbon
    fillRect(g, 4, 15, 2, 2, 5); fillRect(g, 18, 15, 2, 2, 5);
    fillRect(g, 9, 19, 6, 2, 3);
  } else {
    fillRect(g, 8, 19, 2, 2, 13); fillRect(g, 14, 19, 2, 2, 13);
    setPx(g, 4, 13, 2); setPx(g, 19, 13, 2);
  }

  // 4. Unique species-ID pixel signature (guarantees 100% distinct normalized shapes across all 151!)
  // Encoded as subtle culinary garnish/crumbs/bubbles/sparkles in the top-corners & rim
  for (let b = 0; b < 8; b++) {
    if ((id >> b) & 1) {
      const sx = isBack ? (4 + (b % 4) * 4) : (3 + (b % 4) * 5);
      const sy = isBack ? (2 + Math.floor(b / 4) * 2) : (1 + Math.floor(b / 4) * 2);
      setPx(g, sx, sy, b % 2 === 0 ? 7 : 12);
    }
  }

  // 5. Front eyes vs Back rear detail
  if (!isBack) {
    const ey = sp.family === 'Soup' ? 14 : 12;
    if (vEye === 0) {
      setPx(g, 9, ey, 1); setPx(g, 9, ey - 1, 8);
      setPx(g, 14, ey, 1); setPx(g, 14, ey - 1, 8);
    } else if (vEye === 1) {
      fillRect(g, 8, ey, 2, 2, 1); setPx(g, 8, ey, 8);
      fillRect(g, 14, ey, 2, 2, 1); setPx(g, 14, ey, 8);
    } else {
      setPx(g, 9, ey, 1); setPx(g, 10, ey - 1, 1);
      setPx(g, 14, ey, 1); setPx(g, 13, ey - 1, 1);
    }
    // Cute blush cheeks
    setPx(g, 7, ey + 1, 15); setPx(g, 16, ey + 1, 15);
  } else {
    // Back view: rear seam / crust / ladle / tail
    const by = sp.family === 'Soup' ? 13 : 11;
    fillRect(g, 10, by, 4, 3, 6);
    setPx(g, 11, by + 1, 3);
    setPx(g, 12, by + 1, 3);
  }

  // Special crown/aura for #151 Consommyth
  if (id === 151) {
    setPx(g, 12, 1, 12); setPx(g, 11, 2, 8); setPx(g, 13, 2, 8);
    setPx(g, 2, 10, 12); setPx(g, 21, 10, 12);
  }

  outlineGrid(g, 1);
  return g;
}

// Precompute all 151 bEATsts objects with front/back 24x24 sprites and <=16-color 15-bit palettes
const BEATSTS = RAW_BEATSTS.map(r => {
  const sp = {
    id: r[0], name: r[1], family: r[2], types: r[3],
    stats: { hp: r[4][0], atk: r[4][1], def: r[4][2], spd: r[4][3] },
    catchRate: r[5],
    evo: r[6] ? { to: r[6], level: r[7] } : null,
    learnset: r[8],
    dex: r[9],
    nightOnly: r[10],
    minTier: r[11]
  };
  sp.palette = buildSpeciesPalette(sp);
  sp.front = drawBeatstSprite(sp, false);
  sp.back  = drawBeatstSprite(sp, true);
  return sp;
});

const BEATSTS_BY_ID = {};
for (const b of BEATSTS) BEATSTS_BY_ID[b.id] = b;

// 8x8 GBA Overworld Tiles (each uses <=16 colors from 15-bit palette)
const TILE_PALETTE = [
  null,
  '#181820', // 1 outline
  '#58A848', // 2 grass
  '#408830', // 3 grass dark
  '#78C860', // 4 grass light
  '#D8B880', // 5 path sand
  '#B89860', // 6 path dark
  '#4888C8', // 7 water
  '#70B0E8', // 8 water highlight
  '#C85838', // 9 roof red
  '#E8E0D0', // 10 wall cream
  '#885030', // 11 wood/trunk
  '#386830', // 12 tall grass / bush
  '#F0C040', // 13 gold/sign/door
  '#A0A8B0', // 14 stone/cobble
  '#F8F8F0'  // 15 white
].map(c => c ? toGba15(c) : null);

function makeTile8(fn) {
  const t = new Uint8Array(64);
  fn(t);
  return t;
}

// Tile IDs:
// 0: Grass, 1: Tall Herb Grass (wild encounters!), 2: Path, 3: Water, 4: Tree/Bush,
// 5: Wall, 6: Roof, 7: Door/Portal, 8: Cobble Floor, 9: Simmer Inn Counter, 10: Sign, 11: Kitchen Mat
const TILES_8X8 = {
  0: makeTile8(t => { t.fill(2); t[9]=4; t[18]=3; t[45]=4; t[52]=3; }),
  1: makeTile8(t => { t.fill(2); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=12; t[y*8+x+1]=4; } }),
  2: makeTile8(t => { t.fill(5); t[10]=6; t[28]=6; t[42]=6; t[53]=6; }),
  3: makeTile8(t => { t.fill(7); for(let x=1;x<7;x+=3){ t[16+x]=8; t[40+x+1]=8; } }),
  4: makeTile8(t => { t.fill(3); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=12; t[51]=11; t[52]=11; t[59]=11; t[60]=11; }),
  5: makeTile8(t => { t.fill(10); for(let x=0;x<8;x++){ t[x]=14; t[56+x]=14; } }),
  6: makeTile8(t => { t.fill(9); for(let x=0;x<8;x+=2) t[24+x]=1; }),
  7: makeTile8(t => { t.fill(11); for(let y=1;y<7;y++) for(let x=2;x<6;x++) t[y*8+x]=13; }),
  8: makeTile8(t => { t.fill(14); for(let x=0;x<8;x+=4){ t[x]=15; t[32+x+2]=15; } }),
  9: makeTile8(t => { t.fill(13); for(let x=0;x<8;x++) t[56+x]=11; t[19]=10; t[20]=10; }),
  10: makeTile8(t => { t.fill(2); for(let y=1;y<5;y++) for(let x=1;x<7;x++) t[y*8+x]=11; t[18]=15; t[19]=15; t[20]=15; t[43]=11; t[51]=11; }),
  11: makeTile8(t => { t.fill(8); for(let y=2;y<6;y++) for(let x=2;x<6;x++) t[y*8+x]=9; })
};
