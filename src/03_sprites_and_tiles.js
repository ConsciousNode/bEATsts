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

// === REGIONAL 8x8 TILESETS (12+ unique tiles per region!) ===
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

// Tile IDs:
// 0..7 Core shared (0:Void/Floor, 1:Inn Counter, 2:Door, 3:Sign, 4:Kitchen Mat, 5:Mart Shelf, 6:Chest/Item, 7:Portal Pad)
// 10..21 Breadlands (12 unique!)
// 22..33 Steambay (12 unique!)
// 34..45 Noodleridge (12 unique!)
// 46..57 Brothbasin (12 unique!)
// 58..65 Tasting Hall & Postgame Eternal Pantry (8 unique!)
const TILES_8X8 = {
  0: makeTile8(t => { t.fill(14); t[9]=15; t[44]=15; }),
  1: makeTile8(t => { t.fill(13); for(let x=0;x<8;x++) t[56+x]=11; t[19]=15; t[20]=15; }),
  2: makeTile8(t => { t.fill(11); for(let y=1;y<7;y++) for(let x=2;x<6;x++) t[y*8+x]=13; }),
  3: makeTile8(t => { t.fill(5); for(let y=1;y<5;y++) for(let x=1;x<7;x++) t[y*8+x]=11; t[18]=15; t[19]=15; t[20]=15; }),
  4: makeTile8(t => { t.fill(14); for(let y=2;y<6;y++) for(let x=2;x<6;x++) t[y*8+x]=9; }),
  5: makeTile8(t => { t.fill(11); for(let x=1;x<7;x++){ t[16+x]=13; t[40+x]=9; } }),
  6: makeTile8(t => { t.fill(5); for(let y=2;y<6;y++) for(let x=2;x<6;x++) t[y*8+x]=13; }),
  7: makeTile8(t => { t.fill(13); for(let y=2;y<6;y++) for(let x=2;x<6;x++) t[y*8+x]=8; }),

  // Breadlands (10..21)
  10: makeTile8(t => { t.fill(2); t[9]=4; t[45]=4; }), // Meadow Grass
  11: makeTile8(t => { t.fill(2); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=12; t[y*8+x+1]=4; } }), // Tall Wheat Grass
  12: makeTile8(t => { t.fill(5); t[10]=6; t[28]=6; t[53]=6; }), // Crust Path
  13: makeTile8(t => { t.fill(7); t[17]=8; t[42]=8; }), // Milk River
  14: makeTile8(t => { t.fill(3); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=12; t[51]=11; t[59]=11; }), // Toastwood Tree
  15: makeTile8(t => { t.fill(10); for(let x=0;x<8;x++){ t[x]=14; t[56+x]=14; } }), // Bakery Wall
  16: makeTile8(t => { t.fill(9); for(let x=0;x<8;x+=2) t[24+x]=1; }), // Bakery Roof
  17: makeTile8(t => { t.fill(6); for(let y=1;y<7;y++) for(let x=1;x<7;x++) t[y*8+x]=5; t[27]=13; }), // Oven Stone
  18: makeTile8(t => { t.fill(11); for(let x=0;x<8;x+=2) t[x]=5; }), // Bread Fence
  19: makeTile8(t => { t.fill(2); t[18]=13; t[19]=13; t[26]=15; }), // Buttercup Flower
  20: makeTile8(t => { t.fill(14); for(let y=0;y<8;y+=2) t[y*8+3]=11; }), // Sourdough Cave Floor
  21: makeTile8(t => { t.fill(11); for(let y=1;y<6;y++) for(let x=1;x<6;x++) t[y*8+x]=6; }), // Sourdough Cave Wall

  // Steambay (22..33)
  22: makeTile8(t => { t.fill(4); t[11]=15; t[50]=15; }), // Harbor Turf
  23: makeTile8(t => { t.fill(4); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=15; t[y*8+x+1]=12; } }), // Misty Bamboo Grass
  24: makeTile8(t => { t.fill(11); for(let x=0;x<8;x++) t[24+x]=6; }), // Wooden Dock Plank
  25: makeTile8(t => { t.fill(7); for(let x=0;x<8;x+=2) t[16+x]=15; }), // Harbor Bay Water
  26: makeTile8(t => { t.fill(12); for(let y=0;y<8;y++){ t[y*8+2]=4; t[y*8+5]=4; } }), // Bamboo Stalk
  27: makeTile8(t => { t.fill(15); for(let x=0;x<8;x++) t[56+x]=14; }), // Steamer Wall
  28: makeTile8(t => { t.fill(7); for(let x=0;x<8;x+=2) t[8+x]=15; }), // Pagoda Blue Roof
  29: makeTile8(t => { t.fill(6); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2) t[y*8+x]=13; }), // Bamboo Mat
  30: makeTile8(t => { t.fill(5); t[19]=10; t[20]=10; t[27]=13; }), // Lantern Post
  31: makeTile8(t => { t.fill(14); t[18]=8; t[45]=8; }), // Wet Cobble
  32: makeTile8(t => { t.fill(6); for(let x=0;x<8;x++) t[32+x]=13; }), // Steamer Spire Floor
  33: makeTile8(t => { t.fill(11); for(let y=0;y<8;y+=2) for(let x=0;x<8;x+=2) t[y*8+x]=13; }), // Steamer Spire Wall

  // Noodleridge (34..45)
  34: makeTile8(t => { t.fill(5); t[12]=13; t[41]=13; }), // Canyon Terrace
  35: makeTile8(t => { t.fill(5); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=13; t[y*8+x+1]=9; } }), // Tall Noodle Wheat
  36: makeTile8(t => { t.fill(14); t[18]=13; t[44]=13; }), // Mountain Flagstone
  37: makeTile8(t => { t.fill(9); t[20]=13; t[42]=13; }), // Chili Broth River
  38: makeTile8(t => { t.fill(11); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=9; }), // Red Canyon Rock
  39: makeTile8(t => { t.fill(13); for(let x=0;x<8;x++) t[56+x]=11; }), // Dojo Wall
  40: makeTile8(t => { t.fill(1); for(let x=0;x<8;x+=2) t[16+x]=13; }), // Dark Wok Roof
  41: makeTile8(t => { t.fill(6); for(let x=1;x<7;x++) t[24+x]=15; }), // Tatami Floor
  42: makeTile8(t => { t.fill(5); t[18]=9; t[27]=13; }), // Chili Pepper Bush
  43: makeTile8(t => { t.fill(14); for(let y=1;y<7;y++) t[y*8+4]=11; }), // Rope Bridge
  44: makeTile8(t => { t.fill(1); for(let y=0;y<8;y+=3) for(let x=0;x<8;x+=3) t[y*8+x]=9; }), // Wok Volcano Floor
  45: makeTile8(t => { t.fill(9); for(let y=1;y<7;y+=2) t[y*8+3]=13; }), // Wok Volcano Wall

  // Brothbasin (46..57)
  46: makeTile8(t => { t.fill(3); t[11]=7; t[44]=7; }), // Simmer Fen Turf
  47: makeTile8(t => { t.fill(3); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=7; t[y*8+x+1]=12; } }), // Tall Broth Reeds
  48: makeTile8(t => { t.fill(14); t[10]=7; t[53]=7; }), // Kettle Cobble
  49: makeTile8(t => { t.fill(7); t[18]=12; t[44]=12; }), // Simmering Stock
  50: makeTile8(t => { t.fill(1); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=7; }), // Broth Crystal
  51: makeTile8(t => { t.fill(14); for(let x=0;x<8;x++) t[56+x]=7; }), // Bastion Wall
  52: makeTile8(t => { t.fill(7); for(let x=0;x<8;x+=2) t[24+x]=13; }), // Copper Kettle Roof
  53: makeTile8(t => { t.fill(1); for(let y=2;y<6;y++) for(let x=2;x<6;x++) t[y*8+x]=12; }), // Bubbling Cauldron Tile
  54: makeTile8(t => { t.fill(3); t[19]=15; t[28]=15; }), // Mushroom Patch
  55: makeTile8(t => { t.fill(13); for(let x=1;x<7;x++) t[32+x]=11; }), // Copper Pipe
  56: makeTile8(t => { t.fill(1); t[19]=7; t[44]=7; }), // Catacomb Floor
  57: makeTile8(t => { t.fill(11); for(let y=1;y<6;y++) for(let x=1;x<6;x++) t[y*8+x]=1; }), // Catacomb Wall

  // Grand Tasting Hall & Postgame Eternal Pantry (58..65)
  58: makeTile8(t => { t.fill(15); for(let x=0;x<8;x+=2) t[x]=13; }), // Marble Hall Floor
  59: makeTile8(t => { t.fill(13); for(let y=1;y<7;y++) for(let x=1;x<7;x++) t[y*8+x]=9; }), // Royal Carpet
  60: makeTile8(t => { t.fill(1); for(let x=0;x<8;x+=2) t[24+x]=13; }), // Hall Gold Pillar
  61: makeTile8(t => { t.fill(8); t[19]=15; t[44]=15; }), // Eternal Pantry Floor
  62: makeTile8(t => { t.fill(8); for(let y=1;y<7;y+=2) for(let x=1;x<7;x+=2){ t[y*8+x]=13; t[y*8+x+1]=15; } }), // Starlit Herb Grass
  63: makeTile8(t => { t.fill(13); for(let y=1;y<6;y++) for(let x=1;x<7;x++) t[y*8+x]=15; }) // Golden Pantry Wall
};

// === 16x16 CHARACTER SPRITES (4 Directions: down, up, left, right) ===
const CHAR_SPRITES = {
  player:    { hat: '#E63946', hair: '#F8D8B0', shirt: '#457B9D', pants: '#283854' },
  brotholomew:{ hat: '#F8F8F0', hair: '#C0C8D0', shirt: '#F8F8F0', pants: '#457B9D' },
  saffron:   { hat: '#9B5DE5', hair: '#F0C040', shirt: '#D04038', pants: '#181820' },
  inn:       { hat: '#FF90A8', hair: '#F8D8B0', shirt: '#FF70A6', pants: '#8D5B4C' },
  mart:      { hat: '#60C8F8', hair: '#F8D8B0', shirt: '#457B9D', pants: '#182030' },
  chef_greg: { hat: '#E8A850', hair: '#885030', shirt: '#D9822B', pants: '#181820' },
  chef_clara:{ hat: '#8AC926', hair: '#F8D8B0', shirt: '#52B788', pants: '#2D6A4F' },
  chef_baozi:{ hat: '#F8F8F0', hair: '#F8D8B0', shirt: '#A8DADC', pants: '#457B9D' },
  chef_mei:  { hat: '#E6AF2E', hair: '#181820', shirt: '#E63946', pants: '#181820' },
  chef_twirl:{ hat: '#F0C868', hair: '#8D5B4C', shirt: '#D9822B', pants: '#885030' },
  chef_fusilli:{ hat: '#52B788', hair: '#C0C8D0', shirt: '#2D6A4F', pants: '#181820' },
  chef_bisque:{ hat: '#9B5DE5', hair: '#F8F8F0', shirt: '#683098', pants: '#181820' },
  chef_bouillon:{ hat: '#457B9D', hair: '#C0C8D0', shirt: '#285888', pants: '#181820' },
  taster_pip:{ hat: '#E6AF2E', hair: '#F8D8B0', shirt: '#F0C040', pants: '#8D5B4C' },
  taster_roux:{ hat: '#8D5B4C', hair: '#683820', shirt: '#A86848', pants: '#181820' },
  taster_mochi:{ hat: '#FF70A6', hair: '#F8F8F0', shirt: '#FF90A8', pants: '#9B5DE5' },
  champion:  { hat: '#F0C040', hair: '#F8E888', shirt: '#F8F8F0', pants: '#9B5DE5' },
  villager_a:{ hat: '#52B788', hair: '#885030', shirt: '#E8A850', pants: '#283854' },
  villager_b:{ hat: '#4CC9F0', hair: '#F0C040', shirt: '#8AC926', pants: '#457B9D' },
  villager_c:{ hat: '#FF70A6', hair: '#181820', shirt: '#A8DADC', pants: '#8D5B4C' },
  villager_d:{ hat: '#9B5DE5', hair: '#C0C8D0', shirt: '#E6AF2E', pants: '#181820' },
  item_chest:{ hat: '#F0C040', hair: '#F0C040', shirt: '#885030', pants: '#885030' }
};

function drawCharSprite16(ctx, spriteKey, dir, dx, dy) {
  const pal = CHAR_SPRITES[spriteKey] || CHAR_SPRITES.villager_a;
  // 16x16 pixel character aligned to 8x8 tile grid
  ctx.fillStyle = '#181820';
  ctx.fillRect(dx + 3, dy + 1, 10, 14);
  // Hat / Hair
  ctx.fillStyle = pal.hat;
  ctx.fillRect(dx + 4, dy + 1, 8, 4);
  // Face
  ctx.fillStyle = pal.hair;
  ctx.fillRect(dx + 4, dy + 5, 8, 4);
  // Directional eyes
  ctx.fillStyle = '#181820';
  if (dir === 'down') {
    ctx.fillRect(dx + 5, dy + 6, 2, 2);
    ctx.fillRect(dx + 9, dy + 6, 2, 2);
  } else if (dir === 'left') {
    ctx.fillRect(dx + 4, dy + 6, 2, 2);
  } else if (dir === 'right') {
    ctx.fillRect(dx + 10, dy + 6, 2, 2);
  }
  // Shirt
  ctx.fillStyle = pal.shirt;
  ctx.fillRect(dx + 4, dy + 9, 8, 4);
  // Pants / Feet
  ctx.fillStyle = pal.pants;
  ctx.fillRect(dx + 4, dy + 13, 3, 2);
  ctx.fillRect(dx + 9, dy + 13, 3, 2);
}
