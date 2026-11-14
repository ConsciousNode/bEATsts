// 03_sprites_and_tiles.js - 32x32 Per-Species Sprites (No ID Arithmetic), 16x16 Character Sprites, and Regional 8x8 Tilesets

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
  const raw = [
    null,
    '#181820', // 1: outline
    t1[0],    // 2: primary
    t1[1],    // 3: primary shadow
    t1[2],    // 4: primary highlight
    t2[0],    // 5: secondary
    t2[1],    // 6: secondary shadow
    t2[2],    // 7: secondary highlight
    '#F8F8F0', // 8: white
    '#F0C868', // 9: crust / noodle gold
    '#D04038', // 10: tomato / chili
    '#50B848', // 11: herb / lettuce
    '#F8E888', // 12: cheese / butter / glow
    '#885030', // 13: wood / pot dark
    '#C0C8D0', // 14: ceramic / steel
    '#FF90A8'  // 15: cheek / sweet accent
  ];
  return raw.map(c => c ? toGba15(c) : null);
}

function makeGrid32() { return new Uint8Array(32 * 32); }
function setPx32(g, x, y, c) {
  const ix = Math.round(x), iy = Math.round(y);
  if (ix >= 0 && ix < 32 && iy >= 0 && iy < 32) g[iy * 32 + ix] = c;
}
function fillRect32(g, x0, y0, w, h, c) {
  for (let y = y0; y < y0 + h; y++)
    for (let x = x0; x < x0 + w; x++) setPx32(g, x, y, c);
}
function fillEllipse32(g, cx, cy, rx, ry, c) {
  for (let y = Math.floor(cy - ry); y <= Math.ceil(cy + ry); y++) {
    for (let x = Math.floor(cx - rx); x <= Math.ceil(cx + rx); x++) {
      const dx = (x - cx) / rx, dy = (y - cy) / ry;
      if (dx * dx + dy * dy <= 1.0) setPx32(g, x, y, c);
    }
  }
}
function outlineGrid32(g, outlineIdx = 1) {
  const copy = new Uint8Array(g);
  for (let y = 0; y < 32; y++) {
    for (let x = 0; x < 32; x++) {
      if (copy[y * 32 + x] !== 0) continue;
      const n = (y > 0 && copy[(y-1)*32+x]) || (y < 31 && copy[(y+1)*32+x]) ||
                (x > 0 && copy[y*32+(x-1)]) || (x < 31 && copy[y*32+(x+1)]);
      if (n) g[y * 32 + x] = outlineIdx;
    }
  }
}

function drawBeatstSprite32(sp, isBack) {
  const g = makeGrid32();
  const sh = sp.shape;
  const s = sh.sizeMod; // 0 (small), 1 (med), 2 (large)
  let cx = 16, cy = 17 - s;
  if (sh.pose === 'high') cy -= 4;
  else if (sh.pose === 'low') cy += 4;
  else if (sh.pose === 'left') cx -= 5;
  else if (sh.pose === 'right') cx += 5;
  else if (sh.pose === 'lean_l') { cx -= 4; cy -= 3; }
  else if (sh.pose === 'lean_r') { cx += 4; cy += 3; }
  else if (sh.pose === 'wide') { cy += 2; fillRect32(g, cx - 13, cy + 1, 26, 3, 2); }
  else if (sh.pose === 'tall') { cy -= 3; fillRect32(g, cx - 4, cy - 10, 8, 6, 2); }

  // 1. Arch-specific 32x32 body silhouette (authored per-species, zero ID arithmetic)
  switch (sh.arch) {
    case 'slice': {
      const w = 12 + s * 3, h = 11 + s * 2;
      fillRect32(g, cx - Math.floor(w/2), cy - Math.floor(h/2), w, 3, 9);
      fillRect32(g, cx - Math.floor(w/2) - 1, cy - Math.floor(h/2) + 3, w + 2, 2, 11);
      fillRect32(g, cx - Math.floor(w/2), cy - Math.floor(h/2) + 5, w, 2, 5);
      fillRect32(g, cx - Math.floor(w/2), cy - Math.floor(h/2) + 7, w, h - 7, 9);
      break;
    }
    case 'club': {
      const w = 13 + s * 2;
      for (let r = 0; r < 14 + s * 2; r++) {
        const rw = Math.max(4, Math.floor((r + 2) * w / (15 + s * 2)));
        fillRect32(g, cx - Math.floor(rw / 2), 6 + r, rw, 1, r % 4 === 0 ? 9 : (r % 4 === 1 ? 11 : (r % 4 === 2 ? 10 : 5)));
      }
      break;
    }
    case 'sub': {
      fillEllipse32(g, cx, cy + 1, 11 + s * 2, 4 + s, 9);
      fillRect32(g, cx - 9 - s, cy, 18 + s * 2, 2, 11);
      fillRect32(g, cx - 8 - s, cy + 1, 16 + s * 2, 2, 5);
      break;
    }
    case 'burger': {
      const r = 7 + s * 2;
      fillEllipse32(g, cx, cy - 3, r, 4 + s, 9);
      fillRect32(g, cx - r - 1, cy + 1, r * 2 + 2, 2, 12);
      fillRect32(g, cx - r, cy + 3, r * 2, 2, 13);
      fillRect32(g, cx - r + 1, cy + 5, r * 2 - 2, 3, 9);
      break;
    }
    case 'croissant': {
      fillEllipse32(g, cx, cy, 8 + s * 2, 4 + s, 9);
      fillEllipse32(g, cx - 6 - s, cy + 3, 3 + s, 3, 3);
      fillEllipse32(g, cx + 6 + s, cy + 3, 3 + s, 3, 3);
      break;
    }
    case 'pita': {
      fillEllipse32(g, cx, cy + 2, 8 + s * 2, 7 + s, 9);
      fillEllipse32(g, cx, cy - 2, 6 + s, 3, 5);
      fillRect32(g, cx - 5, cy - 3, 10, 2, 11);
      break;
    }
    case 'waffle': {
      const sz = 12 + s * 3;
      fillRect32(g, cx - Math.floor(sz/2), cy - Math.floor(sz/2), sz, sz, 9);
      for (let y = cy - Math.floor(sz/2) + 2; y < cy + Math.floor(sz/2) - 1; y += 3)
        for (let x = cx - Math.floor(sz/2) + 2; x < cx + Math.floor(sz/2) - 1; x += 3)
          setPx32(g, x, y, 3);
      break;
    }
    case 'bagel': {
      const r = 8 + s * 2;
      fillEllipse32(g, cx, cy, r, r - 1, 9);
      fillEllipse32(g, cx, cy, 2 + s, 2, 0);
      break;
    }
    case 'scone': {
      for (let r = 0; r < 12 + s * 2; r++) {
        const w = 4 + Math.floor(r * 1.1);
        fillRect32(g, cx - Math.floor(w/2), 10 + r - s, w, 1, r < 4 ? 12 : 2);
      }
      break;
    }
    case 'pretzel': {
      fillEllipse32(g, cx - 4, cy - 2, 5 + s, 5 + s, 9);
      fillEllipse32(g, cx + 4, cy - 2, 5 + s, 5 + s, 9);
      fillEllipse32(g, cx, cy + 3, 7 + s, 4, 13);
      fillEllipse32(g, cx - 4, cy - 2, 2, 2, 0);
      fillEllipse32(g, cx + 4, cy - 2, 2, 2, 0);
      break;
    }
    case 'muffin': {
      fillEllipse32(g, cx, cy - 2, 8 + s * 2, 5 + s, 9);
      fillRect32(g, cx - 6 - s, cy + 2, 12 + s * 2, 5 + s, 13);
      break;
    }
    case 'taco_open': {
      fillEllipse32(g, cx, cy + 2, 10 + s * 2, 5 + s, 12);
      fillRect32(g, cx - 8 - s, cy - 1, 16 + s * 2, 3, 10);
      fillRect32(g, cx - 7 - s, cy - 2, 14 + s * 2, 2, 11);
      break;
    }
    case 'bao': {
      fillEllipse32(g, cx, cy + 1, 8 + s * 2, 7 + s * 2, 2);
      fillEllipse32(g, cx, cy - 5 - s, 3 + s, 2 + s, 4);
      break;
    }
    case 'gyoza': {
      fillEllipse32(g, cx, cy + 2, 10 + s * 2, 5 + s, 2);
      fillRect32(g, cx - 9 - s, cy + 6 + s, 18 + s * 2, 2, 9);
      for (let x = cx - 6; x <= cx + 6; x += 3) setPx32(g, x, cy - 3 - s, 4);
      break;
    }
    case 'shumai': {
      fillRect32(g, cx - 6 - s, cy - 3, 12 + s * 2, 10 + s, 9);
      fillEllipse32(g, cx, cy - 3, 6 + s, 3, 5);
      setPx32(g, cx, cy - 4, 11); setPx32(g, cx + 1, cy - 4, 11);
      break;
    }
    case 'onigiri': {
      for (let r = 0; r < 13 + s * 2; r++) {
        const w = 3 + Math.floor(r * 1.15);
        fillRect32(g, cx - Math.floor(w/2), 8 + r - s, w, 1, 8);
      }
      fillRect32(g, cx - 4, 15, 8, 6 + s, 1);
      break;
    }
    case 'ravioli': {
      const sz = 12 + s * 2;
      fillRect32(g, cx - Math.floor(sz/2), cy - Math.floor(sz/2), sz, sz, 9);
      fillEllipse32(g, cx, cy, 4 + s, 4 + s, 2);
      break;
    }
    case 'empanada': {
      fillEllipse32(g, cx, cy + 1, 9 + s * 2, 6 + s, 9);
      fillRect32(g, cx - 8 - s, cy + 1, 16 + s * 2, 2, 3);
      break;
    }
    case 'mochi': {
      fillEllipse32(g, cx, cy + 2, 7 + s * 2, 6 + s, 2);
      fillEllipse32(g, cx - 2, cy, 3 + s, 2, 4);
      break;
    }
    case 'khinkali': {
      fillEllipse32(g, cx, cy + 3, 8 + s * 2, 6 + s, 2);
      for (let r = 0; r < 5 + s; r++) fillRect32(g, cx - 2 - Math.floor(r/2), cy - 5 - s + r, 4 + r, 1, 4);
      break;
    }
    case 'takoyaki': {
      fillEllipse32(g, cx, cy, 7 + s * 2, 7 + s * 2, 9);
      fillEllipse32(g, cx, cy - 4 - s, 5 + s, 2, 13);
      break;
    }
    case 'burek': {
      fillEllipse32(g, cx, cy + 1, 9 + s * 2, 6 + s * 2, 9);
      fillEllipse32(g, cx, cy + 1, 5 + s, 3 + s, 3);
      fillEllipse32(g, cx, cy + 1, 2, 1, 4);
      break;
    }
    case 'ramen': {
      fillEllipse32(g, cx, cy + 3, 9 + s * 2, 5 + s, 14);
      fillRect32(g, cx - 8 - s, cy - 1, 16 + s * 2, 4, 14);
      fillEllipse32(g, cx, cy - 2, 8 + s, 3 + s, 9);
      break;
    }
    case 'pho': {
      fillEllipse32(g, cx, cy + 4, 7 + s * 2, 4 + s, 8);
      fillRect32(g, cx - 7 - s, cy - 2, 14 + s * 2, 6, 8);
      fillEllipse32(g, cx, cy - 3, 7 + s, 3, 5);
      for (let i = 0; i < 6; i++) { setPx32(g, cx + 3 + i, cy - 8 + i, 13); }
      break;
    }
    case 'pasta_nest': {
      fillEllipse32(g, cx, cy + 1, 9 + s * 2, 6 + s, 9);
      fillEllipse32(g, cx, cy - 1, 5 + s, 3, 10);
      break;
    }
    case 'wok_pan': {
      fillEllipse32(g, cx, cy + 2, 10 + s * 2, 5 + s, 1);
      fillRect32(g, cx + 9 + s, cy, 5, 2, 13);
      fillEllipse32(g, cx, cy - 1, 8 + s, 3, 9);
      break;
    }
    case 'lasagna': {
      const w = 14 + s * 3, h = 10 + s * 2;
      fillRect32(g, cx - Math.floor(w/2), cy - Math.floor(h/2), w, h, 9);
      fillRect32(g, cx - Math.floor(w/2), cy - 2, w, 2, 10);
      fillRect32(g, cx - Math.floor(w/2), cy + 2, w, 2, 12);
      break;
    }
    case 'noodle_drake': {
      fillEllipse32(g, cx - 3, cy - 3, 5 + s, 4 + s, 9);
      fillEllipse32(g, cx + 3, cy + 2, 6 + s, 4 + s, 12);
      fillEllipse32(g, cx - 2, cy + 5, 5 + s, 3, 9);
      break;
    }
    case 'mac_cup': {
      fillRect32(g, cx - 6 - s, cy - 2, 12 + s * 2, 10 + s, 14);
      fillEllipse32(g, cx, cy - 3, 6 + s, 3 + s, 12);
      break;
    }
    case 'soba_mat': {
      fillRect32(g, cx - 10 - s, cy + 2, 20 + s * 2, 5, 13);
      fillEllipse32(g, cx, cy - 1, 7 + s, 4 + s, 3);
      break;
    }
    case 'teacup': {
      fillEllipse32(g, cx, cy + 2, 6 + s * 2, 5 + s, 8);
      fillRect32(g, cx - 6 - s, cy - 3, 12 + s * 2, 5, 8);
      fillEllipse32(g, cx, cy - 3, 5 + s, 2, 5);
      fillRect32(g, cx + 6 + s, cy - 1, 3, 4, 8);
      break;
    }
    case 'cauldron': {
      fillEllipse32(g, cx, cy + 2, 9 + s * 2, 7 + s, 13);
      fillRect32(g, cx - 7 - s, cy - 5, 14 + s * 2, 3, 14);
      fillEllipse32(g, cx, cy - 5, 6 + s, 2, 5);
      break;
    }
    case 'bread_bowl': {
      fillEllipse32(g, cx, cy + 2, 9 + s * 2, 6 + s, 9);
      fillEllipse32(g, cx, cy - 2, 6 + s, 3, 5);
      break;
    }
    case 'tureen': {
      fillEllipse32(g, cx, cy + 1, 8 + s * 2, 6 + s, 14);
      fillRect32(g, cx - 6 - s, cy - 5, 12 + s * 2, 3, 8);
      fillEllipse32(g, cx, cy - 6, 4 + s, 2, 12);
      break;
    }
    case 'clay_pot': {
      fillEllipse32(g, cx, cy + 2, 8 + s * 2, 6 + s, 10);
      fillEllipse32(g, cx, cy - 3, 6 + s, 2, 5);
      break;
    }
    case 'chili_pot': {
      fillRect32(g, cx - 7 - s, cy - 4, 14 + s * 2, 11 + s, 10);
      fillEllipse32(g, cx, cy - 4, 7 + s, 3, 5);
      break;
    }
    case 'myth_bowl': {
      fillEllipse32(g, cx, cy + 2, 10 + s * 2, 6 + s, 12);
      fillEllipse32(g, cx, cy - 3, 8 + s, 3, 5);
      fillRect32(g, cx - 4, cy + 7 + s, 8, 3, 12);
      break;
    }
  }

  // 2. Toppers / Headgear
  switch (sh.top) {
    case 'flag': fillRect32(g, cx, 3, 1, 6, 13); fillRect32(g, cx + 1, 3, 5, 3, 10); break;
    case 'grill': fillRect32(g, cx - 5, 6, 10, 2, 1); break;
    case 'skewer': fillRect32(g, cx, 2, 2, 7, 13); fillEllipse32(g, cx + 1, 3, 2, 2, 11); break;
    case 'leaf': fillEllipse32(g, cx - 2, 6, 3, 2, 11); fillEllipse32(g, cx + 3, 5, 3, 2, 11); break;
    case 'periscope': fillRect32(g, cx - 1, 3, 2, 6, 14); fillRect32(g, cx - 1, 3, 5, 2, 14); break;
    case 'drip': fillRect32(g, cx - 5, 7, 10, 2, 15); setPx32(g, cx - 3, 9, 15); setPx32(g, cx + 2, 10, 15); break;
    case 'crown': fillRect32(g, cx - 5, 5, 10, 3, 12); setPx32(g, cx - 4, 4, 12); setPx32(g, cx, 3, 10); setPx32(g, cx + 4, 4, 12); break;
    case 'dill': fillRect32(g, cx - 3, 4, 2, 4, 11); fillRect32(g, cx + 2, 4, 2, 4, 11); break;
    case 'horns': fillRect32(g, cx - 7, 4, 2, 4, 8); fillRect32(g, cx + 5, 4, 2, 4, 8); break;
    case 'sugar': fillRect32(g, cx - 4, 6, 8, 2, 8); break;
    case 'ears': fillEllipse32(g, cx - 5, 6, 2, 3, 2); fillEllipse32(g, cx + 5, 6, 2, 3, 2); break;
    case 'chili': fillRect32(g, cx - 2, 4, 4, 4, 10); setPx32(g, cx, 3, 11); break;
    case 'cream': fillEllipse32(g, cx, 6, 4, 3, 8); setPx32(g, cx, 3, 10); break;
    case 'seeds': setPx32(g, cx - 3, 8, 8); setPx32(g, cx, 7, 8); setPx32(g, cx + 3, 8, 8); break;
    case 'antennae': fillRect32(g, cx - 4, 3, 1, 5, 1); fillRect32(g, cx + 4, 3, 1, 5, 1); break;
    case 'moon': fillEllipse32(g, cx, 5, 3, 3, 12); fillEllipse32(g, cx + 1, 5, 2, 2, 0); break;
    case 'egg': fillEllipse32(g, cx, 6, 4, 3, 8); fillEllipse32(g, cx, 6, 2, 2, 12); break;
    case 'knot': fillEllipse32(g, cx, 6, 3, 2, 4); break;
    case 'steam': setPx32(g, cx - 4, 4, 8); setPx32(g, cx - 3, 2, 8); setPx32(g, cx + 4, 4, 8); setPx32(g, cx + 5, 2, 8); break;
    case 'pleat': for (let x = cx - 5; x <= cx + 5; x += 2) setPx32(g, x, 6, 8); break;
    case 'flame': fillEllipse32(g, cx, 5, 3, 4, 10); fillEllipse32(g, cx, 6, 2, 2, 12); break;
    case 'halo': fillEllipse32(g, cx, 4, 7, 2, 12); fillEllipse32(g, cx, 4, 5, 1, 0); break;
  }

  // 3. Limbs
  switch (sh.limb) {
    case 'stub': fillRect32(g, cx - 6, 25, 3, 3, 3); fillRect32(g, cx + 3, 25, 3, 3, 3); break;
    case 'paws': fillEllipse32(g, cx - 6, 26, 3, 2, 3); fillEllipse32(g, cx + 6, 26, 3, 2, 3); break;
    case 'heavy': fillRect32(g, cx - 8, 24, 5, 5, 13); fillRect32(g, cx + 3, 24, 5, 5, 13); break;
    case 'fins': fillEllipse32(g, cx - 9, 24, 4, 2, 5); fillEllipse32(g, cx + 9, 24, 4, 2, 5); break;
    case 'arms': fillRect32(g, cx - 12, 16, 3, 5, 2); fillRect32(g, cx + 9, 16, 3, 5, 2); fillRect32(g, cx - 6, 25, 3, 3, 3); fillRect32(g, cx + 3, 25, 3, 3, 3); break;
    case 'bounce': fillEllipse32(g, cx, 27, 6, 2, 3); break;
    case 'claws': fillRect32(g, cx - 13, 14, 4, 4, 10); fillRect32(g, cx + 9, 14, 4, 4, 10); fillRect32(g, cx - 6, 25, 3, 3, 3); fillRect32(g, cx + 3, 25, 3, 3, 3); break;
    case 'float': break;
    case 'none': break;
  }

  // 4. Side appendages
  switch (sh.side) {
    case 'tail': fillEllipse32(g, cx + 11, 20, 3, 2, 5); fillEllipse32(g, cx + 13, 18, 2, 2, 12); break;
    case 'cape': fillRect32(g, cx - 12, 13, 3, 11, 10); fillRect32(g, cx + 9, 13, 3, 11, 10); break;
    case 'wings': fillEllipse32(g, cx - 12, 14, 3, 5, 4); fillEllipse32(g, cx + 12, 14, 3, 5, 4); break;
    case 'shield': fillEllipse32(g, cx - 12, 18, 3, 5, 14); break;
    case 'aura': setPx32(g, 3, 12, 12); setPx32(g, 28, 12, 12); setPx32(g, 4, 22, 8); setPx32(g, 27, 22, 8); break;
    case 'fins': fillEllipse32(g, cx - 12, 17, 3, 3, 5); fillEllipse32(g, cx + 12, 17, 3, 3, 5); break;
    case 'arms': fillRect32(g, cx - 12, 15, 3, 5, 6); fillRect32(g, cx + 9, 15, 3, 5, 6); break;
    case 'claws': fillRect32(g, cx - 12, 12, 3, 3, 10); fillRect32(g, cx + 9, 12, 3, 3, 10); break;
  }

  // Pose-specific body proportion accents
  if (sh.pose === 'wide') { fillRect32(g, cx - 10, cy + 2, 20, 2, 3); }
  if (sh.pose === 'tall') { fillRect32(g, cx - 3, cy - 8, 6, 3, 4); }
  // 5. Front eyes vs Back rear detail
  if (!isBack) {
    const ey = cy;
    fillRect32(g, cx - 4, ey - 1, 2, 3, 1); setPx32(g, cx - 4, ey - 1, 8);
    fillRect32(g, cx + 2, ey - 1, 2, 3, 1); setPx32(g, cx + 2, ey - 1, 8);
    setPx32(g, cx - 6, ey + 2, 15); setPx32(g, cx + 5, ey + 2, 15);
    setPx32(g, cx - 1, ey + 2, 1); setPx32(g, cx, ey + 3, 1); setPx32(g, cx + 1, ey + 2, 1);
  } else {
    fillRect32(g, cx - 3, cy - 1, 6, 4, 6);
    fillRect32(g, cx - 2, cy, 4, 2, 3);
  }

  outlineGrid32(g, 1);
  return g;
}

const BEATSTS = RAW_BEATSTS.map(r => {
  const sp = {
    id: r[0], name: r[1], family: r[2], types: r[3],
    stats: { hp: r[4][0], atk: r[4][1], def: r[4][2], spd: r[4][3] },
    catchRate: r[5],
    evo: r[6] ? { to: r[6], level: r[7] } : null,
    learnset: buildLearnset(r[3], r[8]),
    dex: r[9],
    nightOnly: r[10],
    minTier: r[11],
    shape: { arch: r[12], sizeMod: r[13], limb: r[14], top: r[15], side: r[16], pose: r[17], eye: r[18] }
  };
  sp.palette = buildSpeciesPalette(sp);
  sp.front = drawBeatstSprite32(sp, false);
  sp.back  = drawBeatstSprite32(sp, true);
  return sp;
});

const BEATSTS_BY_ID = {};
for (const b of BEATSTS) BEATSTS_BY_ID[b.id] = b;

// === REGIONAL 8x8 TILESETS (12+ unique tiles per region + readable doors/windows/stalls/puzzles) ===
const TILE_PALETTE = [
  null,
  '#181820', // 1 outline
  '#58A848', // 2 bread grass
  '#408830', // 3 bread grass dark
  '#78C860', // 4 bread grass light
  '#D8B880', // 5 path / wood
  '#B89860', // 6 path dark
  '#4888C8', // 7 water
  '#70B0E8', // 8 water highlight
  '#C85838', // 9 roof / spicy red
  '#E8E0D0', // 10 wall cream
  '#885030', // 11 dark wood / bark
  '#386830', // 12 bush / herb
  '#F0C040', // 13 gold / sign / lantern
  '#A0A8B0', // 14 stone / cobble
  '#F8F8F0'  // 15 white / steam
].map(c => c ? toGba15(c) : null);

function makeTile8(fn) {
  const t = new Uint8Array(64);
  fn(t);
  return t;
}

const TILE_ROLES = {
  0: 'floor', 1: 'counter', 2: 'door', 3: 'sign', 4: 'mat', 5: 'shelf',
  6: 'stairs', 7: 'stairs', 8: 'building', 9: 'switch',
  10: 'ground', 11: 'tall_grass', 12: 'path', 13: 'water', 14: 'wall', 15: 'building', 16: 'roof', 17: 'plaza', 18: 'fence', 19: 'decoration', 20: 'floor', 21: 'wall',
  22: 'ground', 23: 'tall_grass', 24: 'path', 25: 'water', 26: 'wall', 27: 'building', 28: 'roof', 29: 'plaza', 30: 'decoration', 31: 'path', 32: 'floor', 33: 'wall',
  34: 'ground', 35: 'tall_grass', 36: 'path', 37: 'water', 38: 'wall', 39: 'building', 40: 'roof', 41: 'plaza', 42: 'decoration', 43: 'bridge', 44: 'floor', 45: 'wall',
  46: 'ground', 47: 'tall_grass', 48: 'path', 49: 'water', 50: 'wall', 51: 'building', 52: 'roof', 53: 'decoration', 54: 'decoration', 55: 'wall', 56: 'floor', 57: 'wall',
  58: 'plaza', 59: 'path', 60: 'wall', 61: 'ground', 62: 'tall_grass', 63: 'wall',
  64: 'decoration', 65: 'ledge', 66: 'ice', 67: 'conveyor', 68: 'conveyor', 69: 'conveyor', 70: 'conveyor',
  71: 'floor', 72: 'wall', 73: 'gate'
};

const TILES_8X8 = {
  0: makeTile8(t => { t.fill(14); t[9]=15; t[44]=15; }), // Stone/Interior Floor
  1: makeTile8(t => { t.fill(13); for(let x=0;x<8;x++) t[56+x]=11; t[19]=15; t[20]=15; }), // Inn Counter
  2: makeTile8(t => { t.fill(11); for(let y=1;y<8;y++) for(let x=1;x<7;x++) t[y*8+x]=5; for(let y=2;y<7;y++) for(let x=2;x<6;x++) t[y*8+x]=11; t[37]=13; }), // Consistent Door
  3: makeTile8(t => { t.fill(5); for(let y=1;y<5;y++) for(let x=1;x<7;x++) t[y*8+x]=11; t[18]=15; t[19]=15; t[20]=15; t[43]=11; t[51]=11; }), // Signpost
  4: makeTile8(t => { t.fill(14); for(let y=2;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=9; }), // Exit Mat
  5: makeTile8(t => { t.fill(11); for(let x=1;x<7;x++){ t[16+x]=13; t[40+x]=9; } }), // Mart Shelf
  6: makeTile8(t => { t.fill(14); for(let y=1;y<7;y+=2) for(let x=1;x<7;x++) t[y*8+x]=13; for(let x=2;x<6;x++) t[8+x]=15; }), // Stairs Up
  7: makeTile8(t => { t.fill(1); for(let y=1;y<7;y+=2) for(let x=1;x<7;x++) t[y*8+x]=14; t[43]=13; t[44]=13; }), // Stairs Down
  8: makeTile8(t => { t.fill(10); for(let x=0;x<8;x++){ t[x]=14; t[56+x]=14; } for(let y=2;y<6;y++) for(let x=2;x<6;x++) t[y*8+x]=8; t[27]=15; }), // Building Window
  9: makeTile8(t => { t.fill(14); for(let y=2;y<6;y++) for(let x=2;x<6;x++) t[y*8+x]=13; t[27]=9; t[28]=9; }), // Floor Switch

  // Breadlands (10..21)
  10: makeTile8(t => { t.fill(2); t[9]=4; t[45]=4; }),
  11: makeTile8(t => { t.fill(2); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=12; t[y*8+x+1]=4; } }),
  12: makeTile8(t => { t.fill(5); t[10]=6; t[28]=6; t[53]=6; }),
  13: makeTile8(t => { t.fill(7); t[17]=8; t[42]=8; }),
  14: makeTile8(t => { t.fill(3); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=12; t[51]=11; t[59]=11; }),
  15: makeTile8(t => { t.fill(10); for(let x=0;x<8;x++){ t[x]=14; t[56+x]=14; } }),
  16: makeTile8(t => { t.fill(9); for(let x=0;x<8;x+=2) t[24+x]=1; }),
  17: makeTile8(t => { t.fill(6); for(let y=1;y<7;y++) for(let x=1;x<7;x++) t[y*8+x]=5; t[27]=13; }),
  18: makeTile8(t => { t.fill(11); for(let x=0;x<8;x+=2) t[x]=5; }),
  19: makeTile8(t => { t.fill(2); t[18]=13; t[19]=13; t[26]=15; }),
  20: makeTile8(t => { t.fill(14); for(let y=0;y<8;y+=2) t[y*8+3]=11; }),
  21: makeTile8(t => { t.fill(11); for(let y=1;y<6;y++) for(let x=1;x<6;x++) t[y*8+x]=6; }),

  // Steambay (22..33)
  22: makeTile8(t => { t.fill(4); t[11]=15; t[50]=15; }),
  23: makeTile8(t => { t.fill(4); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=15; t[y*8+x+1]=12; } }),
  24: makeTile8(t => { t.fill(11); for(let x=0;x<8;x++) t[24+x]=6; }),
  25: makeTile8(t => { t.fill(7); for(let x=0;x<8;x+=2) t[16+x]=15; }),
  26: makeTile8(t => { t.fill(12); for(let y=0;y<8;y++){ t[y*8+2]=4; t[y*8+5]=4; } }),
  27: makeTile8(t => { t.fill(15); for(let x=0;x<8;x++) t[56+x]=14; }),
  28: makeTile8(t => { t.fill(7); for(let x=0;x<8;x+=2) t[8+x]=15; }),
  29: makeTile8(t => { t.fill(6); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2) t[y*8+x]=13; }),
  30: makeTile8(t => { t.fill(5); t[19]=10; t[20]=10; t[27]=13; }),
  31: makeTile8(t => { t.fill(14); t[18]=8; t[45]=8; }),
  32: makeTile8(t => { t.fill(6); for(let x=0;x<8;x++) t[32+x]=13; }),
  33: makeTile8(t => { t.fill(11); for(let y=0;y<8;y+=2) for(let x=0;x<8;x+=2) t[y*8+x]=13; }),

  // Noodleridge (34..45)
  34: makeTile8(t => { t.fill(5); t[12]=13; t[41]=13; }),
  35: makeTile8(t => { t.fill(5); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=13; t[y*8+x+1]=9; } }),
  36: makeTile8(t => { t.fill(14); t[18]=13; t[44]=13; }),
  37: makeTile8(t => { t.fill(9); t[20]=13; t[42]=13; }),
  38: makeTile8(t => { t.fill(11); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=9; }),
  39: makeTile8(t => { t.fill(13); for(let x=0;x<8;x++) t[56+x]=11; }),
  40: makeTile8(t => { t.fill(1); for(let x=0;x<8;x+=2) t[16+x]=13; }),
  41: makeTile8(t => { t.fill(6); for(let x=1;x<7;x++) t[24+x]=15; }),
  42: makeTile8(t => { t.fill(5); t[18]=9; t[27]=13; }),
  43: makeTile8(t => { t.fill(14); for(let y=1;y<7;y++) t[y*8+4]=11; }),
  44: makeTile8(t => { t.fill(1); for(let y=0;y<8;y+=3) for(let x=0;x<8;x+=3) t[y*8+x]=9; }),
  45: makeTile8(t => { t.fill(9); for(let y=1;y<7;y+=2) t[y*8+3]=13; }),

  // Brothbasin (46..57)
  46: makeTile8(t => { t.fill(3); t[11]=7; t[44]=7; }),
  47: makeTile8(t => { t.fill(3); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=7; t[y*8+x+1]=12; } }),
  48: makeTile8(t => { t.fill(14); t[10]=7; t[53]=7; }),
  49: makeTile8(t => { t.fill(7); t[18]=12; t[44]=12; }),
  50: makeTile8(t => { t.fill(1); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=7; }),
  51: makeTile8(t => { t.fill(14); for(let x=0;x<8;x++) t[56+x]=7; }),
  52: makeTile8(t => { t.fill(7); for(let x=0;x<8;x+=2) t[24+x]=13; }),
  53: makeTile8(t => { t.fill(1); for(let y=2;y<6;y++) for(let x=2;x<6;x++) t[y*8+x]=12; }),
  54: makeTile8(t => { t.fill(3); t[19]=15; t[28]=15; }),
  55: makeTile8(t => { t.fill(13); for(let x=1;x<7;x++) t[32+x]=11; }),
  56: makeTile8(t => { t.fill(1); t[19]=7; t[44]=7; }),
  57: makeTile8(t => { t.fill(11); for(let y=1;y<6;y++) for(let x=1;x<6;x++) t[y*8+x]=1; }),

  // Tasting Hall, Eternal Pantry, Market Stalls, Syndicate & Puzzles (58..73)
  58: makeTile8(t => { t.fill(15); for(let x=0;x<8;x+=2) t[x]=13; }),
  59: makeTile8(t => { t.fill(13); for(let y=1;y<7;y++) for(let x=1;x<7;x++) t[y*8+x]=9; }),
  60: makeTile8(t => { t.fill(1); for(let x=0;x<8;x+=2) t[24+x]=13; }),
  61: makeTile8(t => { t.fill(8); t[19]=15; t[44]=15; }),
  62: makeTile8(t => { t.fill(8); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=13; t[y*8+x+1]=15; } }),
  63: makeTile8(t => { t.fill(13); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=15; }),
  64: makeTile8(t => { t.fill(11); for(let x=0;x<8;x++){ t[x]=9; t[8+x]=(x%2?15:9); t[16+x]=13; } }), // Market Stall
  65: makeTile8(t => { t.fill(2); for(let x=0;x<8;x++){ t[48+x]=11; t[56+x]=6; } }), // Ledge South
  66: makeTile8(t => { t.fill(8); t[9]=15; t[18]=15; t[36]=15; t[45]=15; }), // Spilled Oil / Ice Floor
  67: makeTile8(t => { t.fill(14); t[26]=13; t[27]=13; t[36]=13; t[19]=13; }), // Conveyor East
  68: makeTile8(t => { t.fill(14); t[29]=13; t[28]=13; t[19]=13; t[35]=13; }), // Conveyor West
  69: makeTile8(t => { t.fill(14); t[19]=13; t[27]=13; t[28]=13; t[34]=13; }), // Conveyor North
  70: makeTile8(t => { t.fill(14); t[43]=13; t[35]=13; t[36]=13; t[26]=13; }), // Conveyor South
  71: makeTile8(t => { t.fill(14); for(let x=0;x<8;x+=4) t[x]=15; t[36]=8; }), // Syndicate Chrome Floor
  72: makeTile8(t => { t.fill(1); for(let x=0;x<8;x++) t[24+x]=14; t[27]=9; }), // Syndicate Chrome Wall
  73: makeTile8(t => { t.fill(1); for(let y=0;y<8;y+=2) for(let x=0;x<8;x++) t[y*8+x]=9; }) // Laser Gate (solid)
};

// === 16x24 CHARACTER SPRITES (4 Directions x 3 Frames, Unique Named Silhouettes + 12+ Villagers) ===
const CHAR_SPRITES = {
  player_0:       { hat: '#E63946', hair: '#F8D8B0', shirt: '#457B9D', pants: '#283854', hatStyle: 'toque', acc: 'apron' },
  player_1:       { hat: '#2D6A4F', hair: '#885030', shirt: '#52B788', pants: '#182030', hatStyle: 'visor', acc: 'scarf' },
  player_2:       { hat: '#F0C040', hair: '#181820', shirt: '#9B5DE5', pants: '#283854', hatStyle: 'beret', acc: 'apron' },
  brotholomew:    { hat: '#F8F8F0', hair: '#C0C8D0', shirt: '#F8F8F0', pants: '#457B9D', hatStyle: 'tall_toque', acc: 'stache' },
  saffron:        { hat: '#9B5DE5', hair: '#F0C040', shirt: '#D04038', pants: '#181820', hatStyle: 'spiky', acc: 'scarf' },
  inn:            { hat: '#FF90A8', hair: '#F8D8B0', shirt: '#FF70A6', pants: '#8D5B4C', hatStyle: 'kerchief', acc: 'apron' },
  mart:           { hat: '#60C8F8', hair: '#F8D8B0', shirt: '#457B9D', pants: '#182030', hatStyle: 'visor', acc: 'vest' },
  chef_greg:      { hat: '#E8A850', hair: '#885030', shirt: '#D9822B', pants: '#181820', hatStyle: 'bandana', acc: 'stache' },
  chef_clara:     { hat: '#8AC926', hair: '#F8D8B0', shirt: '#52B788', pants: '#2D6A4F', hatStyle: 'beret', acc: 'collar' },
  chef_baozi:     { hat: '#F8F8F0', hair: '#F8D8B0', shirt: '#A8DADC', pants: '#457B9D', hatStyle: 'bun_hat', acc: 'robe' },
  chef_mei:       { hat: '#E6AF2E', hair: '#181820', shirt: '#E63946', pants: '#181820', hatStyle: 'hairpins', acc: 'jacket' },
  chef_twirl:     { hat: '#F0C868', hair: '#8D5B4C', shirt: '#D9822B', pants: '#885030', hatStyle: 'headband', acc: 'sash' },
  chef_fusilli:   { hat: '#52B788', hair: '#C0C8D0', shirt: '#2D6A4F', pants: '#181820', hatStyle: 'kerchief', acc: 'apron' },
  chef_bisque:    { hat: '#9B5DE5', hair: '#F8F8F0', shirt: '#683098', pants: '#181820', hatStyle: 'hood', acc: 'cloak' },
  chef_bouillon:  { hat: '#457B9D', hair: '#C0C8D0', shirt: '#285888', pants: '#181820', hatStyle: 'crown_toque', acc: 'cloak' },
  taster_pip:     { hat: '#E6AF2E', hair: '#F8D8B0', shirt: '#F0C040', pants: '#8D5B4C', hatStyle: 'bowler', acc: 'monocle' },
  taster_roux:    { hat: '#8D5B4C', hair: '#683820', shirt: '#A86848', pants: '#181820', hatStyle: 'tall_toque', acc: 'sash' },
  taster_mochi:   { hat: '#FF70A6', hair: '#F8F8F0', shirt: '#FF90A8', pants: '#9B5DE5', hatStyle: 'twin_buns', acc: 'ribbon' },
  champion:       { hat: '#F0C040', hair: '#F8E888', shirt: '#F8F8F0', pants: '#9B5DE5', hatStyle: 'crown', acc: 'cloak' },
  // Chrome Fork Syndicate (Villains)
  syndicate_grunt:{ hat: '#C0C8D0', hair: '#404858', shirt: '#283040', pants: '#181820', hatStyle: 'visor', acc: 'tie' },
  officer_vesper: { hat: '#A868E0', hair: '#181820', shirt: '#383048', pants: '#181820', hatStyle: 'pompadour', acc: 'shades' },
  officer_crumb:  { hat: '#D8B880', hair: '#683820', shirt: '#404858', pants: '#181820', hatStyle: 'fedora', acc: 'tie' },
  officer_glaze:  { hat: '#FF70A6', hair: '#F8F8F0', shirt: '#482848', pants: '#181820', hatStyle: 'spiky', acc: 'collar' },
  boss_ladle:     { hat: '#F0C040', hair: '#C0C8D0', shirt: '#181820', pants: '#404858', hatStyle: 'tophat', acc: 'cloak' },
  // Named Quest Givers
  barnaby:        { hat: '#D8B880', hair: '#885030', shirt: '#E8A850', pants: '#283854', hatStyle: 'toque', acc: 'stache' },
  critic_brie:    { hat: '#FF70A6', hair: '#181820', shirt: '#9B5DE5', pants: '#181820', hatStyle: 'beret', acc: 'shades' },
  yeast_monk:     { hat: '#885030', hair: '#F8D8B0', shirt: '#B89860', pants: '#683820', hatStyle: 'hood', acc: 'robe' },
  apprentice_lin: { hat: '#A8DADC', hair: '#181820', shirt: '#457B9D', pants: '#283854', hatStyle: 'bun_hat', acc: 'apron' },
  ginger_kai:     { hat: '#D04038', hair: '#885030', shirt: '#E8A850', pants: '#404858', hatStyle: 'bandana', acc: 'vest' },
  tea_master_po:  { hat: '#52B788', hair: '#F8F8F0', shirt: '#2D6A4F', pants: '#181820', hatStyle: 'bowler', acc: 'stache' },
  scallion_sue:   { hat: '#8AC926', hair: '#F0C040', shirt: '#52B788', pants: '#283854', hatStyle: 'straw', acc: 'apron' },
  chili_rico:     { hat: '#E63946', hair: '#181820', shirt: '#F0C040', pants: '#181820', hatStyle: 'headband', acc: 'jacket' },
  steward_otto:   { hat: '#F8E888', hair: '#C0C8D0', shirt: '#457B9D', pants: '#181820', hatStyle: 'crown_toque', acc: 'ribbon' },
  // 12 Distinct Generic Villager Designs
  villager_0:     { hat: '#52B788', hair: '#885030', shirt: '#E8A850', pants: '#283854', hatStyle: 'cap', acc: 'none' },
  villager_1:     { hat: '#4CC9F0', hair: '#F0C040', shirt: '#8AC926', pants: '#457B9D', hatStyle: 'beret', acc: 'scarf' },
  villager_2:     { hat: '#FF70A6', hair: '#181820', shirt: '#A8DADC', pants: '#8D5B4C', hatStyle: 'twin_buns', acc: 'apron' },
  villager_3:     { hat: '#9B5DE5', hair: '#C0C8D0', shirt: '#E6AF2E', pants: '#181820', hatStyle: 'bowler', acc: 'stache' },
  villager_4:     { hat: '#E8A850', hair: '#683820', shirt: '#D04038', pants: '#283854', hatStyle: 'straw', acc: 'vest' },
  villager_5:     { hat: '#A8DADC', hair: '#F8D8B0', shirt: '#457B9D', pants: '#182030', hatStyle: 'visor', acc: 'none' },
  villager_6:     { hat: '#F0C040', hair: '#885030', shirt: '#52B788', pants: '#2D6A4F', hatStyle: 'bandana', acc: 'collar' },
  villager_7:     { hat: '#D04038', hair: '#181820', shirt: '#F8F8F0', pants: '#404858', hatStyle: 'headband', acc: 'sash' },
  villager_8:     { hat: '#60C8F8', hair: '#F0C040', shirt: '#9B5DE5', pants: '#181820', hatStyle: 'spiky', acc: 'jacket' },
  villager_9:     { hat: '#8AC926', hair: '#C0C8D0', shirt: '#885030', pants: '#181820', hatStyle: 'hood', acc: 'robe' },
  villager_10:    { hat: '#FF90A8', hair: '#8D5B4C', shirt: '#F0C868', pants: '#457B9D', hatStyle: 'kerchief', acc: 'ribbon' },
  villager_11:    { hat: '#C0C8D0', hair: '#181820', shirt: '#2D6A4F', pants: '#181820', hatStyle: 'fedora', acc: 'shades' },
  item_chest:     { hat: '#F0C040', hair: '#F0C040', shirt: '#885030', pants: '#885030', hatStyle: 'chest', acc: 'none' },
  push_block:     { hat: '#B89860', hair: '#B89860', shirt: '#885030', pants: '#683820', hatStyle: 'block', acc: 'none' }
};

function buildCharSpriteGrid(spriteKey, dir = 'down', walkFrame = 0) {
  const pal = CHAR_SPRITES[spriteKey] || CHAR_SPRITES.villager_0;
  const grid = Array(16 * 24).fill(null);
  const px = (x, y, c) => { if (x >= 0 && x < 16 && y >= 0 && y < 24) grid[y * 16 + x] = c; };
  const rect = (x0, y0, w, h, c) => { for (let y = y0; y < y0 + h; y++) for (let x = x0; x < x0 + w; x++) px(x, y, c); };

  if (pal.hatStyle === 'chest') {
    rect(2, 9, 12, 11, '#181820');
    rect(3, 10, 10, 4, '#F0C040');
    rect(3, 14, 10, 5, '#885030');
    rect(7, 13, 2, 3, '#F8F8F0');
    return grid;
  }
  if (pal.hatStyle === 'block') {
    rect(1, 8, 14, 14, '#181820');
    rect(2, 9, 12, 12, '#D8B880');
    rect(4, 11, 8, 8, '#885030');
    return grid;
  }

  const bob = walkFrame === 1 ? -1 : (walkFrame === 2 ? 1 : 0);
  const hy = 3 + (walkFrame === 1 ? -1 : 0);

  // Hat / Hair silhouette
  rect(4, hy, 8, 5, '#181820');
  rect(5, hy + 1, 6, 4, pal.hat);
  if (pal.hatStyle === 'tall_toque' || pal.hatStyle === 'tophat' || pal.hatStyle === 'crown_toque') {
    rect(4, hy - 3, 8, 4, '#181820');
    rect(5, hy - 2, 6, 3, pal.hat);
    if (pal.hatStyle === 'crown_toque') { px(5, hy - 3, '#F0C040'); px(8, hy - 3, '#F0C040'); px(10, hy - 3, '#F0C040'); }
  } else if (pal.hatStyle === 'crown') {
    rect(4, hy - 2, 8, 2, '#F0C040');
    px(4, hy - 3, '#F0C040'); px(7, hy - 3, '#F0C040'); px(11, hy - 3, '#F0C040');
  } else if (pal.hatStyle === 'spiky') {
    px(4, hy - 1, pal.hat); px(7, hy - 2, pal.hat); px(11, hy - 1, pal.hat);
  } else if (pal.hatStyle === 'twin_buns') {
    rect(2, hy, 2, 3, pal.hat); rect(12, hy, 2, 3, pal.hat);
  } else if (pal.hatStyle === 'straw' || pal.hatStyle === 'fedora') {
    rect(2, hy + 3, 12, 2, pal.hat);
  } else if (pal.hatStyle === 'visor' || pal.hatStyle === 'cap') {
    if (dir === 'left') rect(2, hy + 3, 4, 2, pal.hat);
    else if (dir === 'right') rect(10, hy + 3, 4, 2, pal.hat);
    else rect(4, hy + 3, 8, 1, pal.hat);
  } else if (pal.hatStyle === 'beret') {
    rect(3, hy, 9, 3, pal.hat);
  } else if (pal.hatStyle === 'hood') {
    rect(3, hy + 1, 10, 7, pal.hat);
  } else if (pal.hatStyle === 'pompadour') {
    rect(4, hy - 2, 7, 3, pal.hat); rect(9, hy - 3, 3, 2, pal.hat);
  } else if (pal.hatStyle === 'hairpins') {
    px(3, hy + 1, '#F0C040'); px(12, hy + 1, '#F0C040'); px(2, hy + 2, '#F0C040'); px(13, hy + 2, '#F0C040');
  } else if (pal.hatStyle === 'bun_hat') {
    rect(5, hy - 2, 6, 3, pal.hat); px(7, hy - 3, '#F8F8F0');
  } else if (pal.hatStyle === 'bandana') {
    rect(3, hy + 2, 10, 2, pal.hat); px(13, hy + 3, pal.hat);
  } else if (pal.hatStyle === 'headband') {
    rect(4, hy + 2, 8, 2, '#F8F8F0'); px(12, hy + 1, '#F8F8F0');
  } else if (pal.hatStyle === 'bowler') {
    rect(5, hy - 1, 6, 2, pal.hat); rect(3, hy + 3, 10, 1, pal.hat);
  } else if (pal.hatStyle === 'kerchief') {
    rect(4, hy + 1, 8, 3, pal.hat); px(3, hy + 4, pal.hat); px(12, hy + 4, pal.hat);
  }

  // Face
  rect(4, hy + 4, 8, 6, '#181820');
  rect(5, hy + 5, 6, 4, pal.hair);
  if (dir === 'down') {
    if (pal.acc === 'shades') { rect(5, hy + 6, 6, 2, '#181820'); }
    else {
      px(6, hy + 6, '#181820'); px(9, hy + 6, '#181820');
      if (pal.acc === 'monocle') rect(8, hy + 5, 3, 3, '#F0C040');
    }
    if (pal.acc === 'stache') rect(6, hy + 8, 4, 1, '#F8F8F0');
  } else if (dir === 'left') {
    px(5, hy + 6, '#181820');
  } else if (dir === 'right') {
    px(10, hy + 6, '#181820');
  } else {
    rect(5, hy + 5, 6, 4, pal.hat);
  }

  // Torso / Coat / Cloak
  const ty = hy + 9;
  rect(3, ty, 10, 7, '#181820');
  rect(4, ty + 1, 8, 5, pal.shirt);
  if (pal.acc === 'apron') rect(5, ty + 2, 6, 4, '#F8F8F0');
  else if (pal.acc === 'scarf') rect(4, ty + 1, 8, 2, '#F0C040');
  else if (pal.acc === 'tie') rect(7, ty + 1, 2, 4, '#E63946');
  else if (pal.acc === 'sash') { px(5, ty + 1, '#F0C040'); px(6, ty + 2, '#F0C040'); px(7, ty + 3, '#F0C040'); }
  else if (pal.acc === 'cloak') { rect(2, ty + 1, 2, 7, pal.hat); rect(12, ty + 1, 2, 7, pal.hat); }
  else if (pal.acc === 'vest') { rect(4, ty + 1, 2, 5, pal.hat); rect(10, ty + 1, 2, 5, pal.hat); }
  else if (pal.acc === 'collar') { px(5, ty + 1, '#F8F8F0'); px(10, ty + 1, '#F8F8F0'); }
  else if (pal.acc === 'jacket') { rect(6, ty + 1, 4, 5, '#F8F8F0'); }
  else if (pal.acc === 'robe') { rect(4, ty + 4, 8, 3, pal.shirt); }
  else if (pal.acc === 'ribbon') { rect(6, ty + 2, 4, 2, '#FF70A6'); }

  // Arms (swing with walkFrame)
  const armOff = walkFrame === 1 ? -1 : (walkFrame === 2 ? 1 : 0);
  rect(2, ty + 1 + armOff, 2, 4, pal.shirt);
  rect(12, ty + 1 - armOff, 2, 4, pal.shirt);

  // Legs (2+ walk frames)
  const ly = ty + 6;
  if (walkFrame === 0) {
    rect(4, ly, 3, 4, pal.pants);
    rect(9, ly, 3, 4, pal.pants);
  } else if (walkFrame === 1) {
    rect(4, ly - 1, 3, 4, pal.pants);
    rect(9, ly + 1, 3, 4, pal.pants);
  } else {
    rect(4, ly + 1, 3, 4, pal.pants);
    rect(9, ly - 1, 3, 4, pal.pants);
  }
  return grid;
}

function drawCharSprite16(ctx, spriteKey, dir, dx, dy, walkFrame = 0) {
  const grid = buildCharSpriteGrid(spriteKey, dir, walkFrame);
  for (let y = 0; y < 24; y++) {
    for (let x = 0; x < 16; x++) {
      const c = grid[y * 16 + x];
      if (c) {
        ctx.fillStyle = c;
        ctx.fillRect(dx + x, dy + y, 1, 1);
      }
    }
  }
}
