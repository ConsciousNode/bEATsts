// 07_game_engine.js - Complete 240x160 GBA Game Engine with Bitmap Fonts, 32x32 Sprites, 16x16 Chars, Move Learning & Quests
// PROVENANCE: Core state machine, battle loop, and save/export logic lifted from beatsts-v1/src/07_game_engine.js;
//             upgraded for bitmap fonts, 32x32 sprites, 16x16 characters, wild switching, Recipe Cards, quests, and postgame.

const SAVE_KEY_PREFIX = 'beatsts_v2_slot_';

function mulberry32(a) {
  return function() {
    let t = a += 0x6D2B79F5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function createBeatstInstance(speciesId, level, rngFn = Math.random) {
  const sp = BEATSTS_BY_ID[speciesId] || BEATSTS_BY_ID[1];
  const iv = Math.floor(rngFn() * 8);
  const calcStat = (base, isHp) => isHp
    ? Math.floor(((base + iv) * 2 * level) / 100) + level + 12
    : Math.floor(((base + iv) * 2 * level) / 100) + 6;
  const maxHp = calcStat(sp.stats.hp, true);
  // Pick up to 4 latest learned moves at or below `level`
  const avail = sp.learnset.filter(([lv]) => lv <= level).map(([, id]) => id);
  const chosen = (avail.length ? avail : sp.learnset.map(([, id]) => id)).slice(-4);
  const moves = chosen.map(mid => {
    const m = MOVES[mid] || MOVES[0];
    return { id: m.id, pp: m.pp, maxPp: m.pp };
  });
  return {
    uid: Math.floor(rngFn() * 1e9),
    speciesId: sp.id,
    nickname: sp.name,
    level,
    xp: level * level * 8,
    nextXp: (level + 1) * (level + 1) * 8,
    hp: maxHp,
    maxHp,
    atk: calcStat(sp.stats.atk, false),
    def: calcStat(sp.stats.def, false),
    spd: calcStat(sp.stats.spd, false),
    status: null,
    lastMoveType: null,
    moves
  };
}

function recalcStats(mon) {
  const sp = BEATSTS_BY_ID[mon.speciesId];
  const oldMax = mon.maxHp;
  const calcStat = (base, isHp) => isHp
    ? Math.floor((base * 2 * mon.level) / 100) + mon.level + 12
    : Math.floor((base * 2 * mon.level) / 100) + 6;
  mon.maxHp = calcStat(sp.stats.hp, true);
  mon.hp = Math.min(mon.maxHp, mon.hp + Math.max(0, mon.maxHp - oldMax));
  mon.atk = calcStat(sp.stats.atk, false);
  mon.def = calcStat(sp.stats.def, false);
  mon.spd = calcStat(sp.stats.spd, false);
  mon.nextXp = (mon.level + 1) * (mon.level + 1) * 8;
}

function safeStorageGet(key) {
  try { return window.localStorage.getItem(key); } catch (e) { return null; }
}
function safeStorageSet(key, val) {
  try { window.localStorage.setItem(key, val); return true; } catch (e) { return false; }
}

const Game = {
  canvas: null,
  ctx: null,
  screen: 'TITLE', // TITLE, SLOTS, STARTER, OVERWORLD, DIALOG, BATTLE, MENU, DEX, PARTY, BOX, BAG, SHOP, LEARN_MOVE, OPTIONS, CONTROLS, CREDITS
  activeSlot: 0,
  state: null,
  rng: mulberry32(1337),
  cursor: 0,
  menuCursor: 0,
  dexCursor: 0,
  dexScroll: 0,
  partyCursor: 0,
  boxCursor: 0,
  bagCursor: 0,
  shopCursor: 0,
  learnCursor: 0,
  pendingLearn: null, // { mon, moveId, returnScreen }
  starterIdx: 0,
  dialogQueue: [],
  dialogCallback: null,
  battle: null,
  animTimer: 0,
  animType: null,
  creditsScroll: 0,
  frameCount: 0,
  lastTick: 0,
  keyState: {},
  moveCooldown: 0,
  options: { textSpeed: 2, volume: 50 },
  memoryFallbackSlots: [null, null, null],

  init() {
    this.canvas = document.getElementById('gba-screen');
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.ctx.imageSmoothingEnabled = false;
    this.bindInputs();
    AudioEngine.volume = this.options.volume / 100;
    this.lastTick = performance.now();
    const loop = (now) => {
      const dt = Math.min(0.1, (now - this.lastTick) / 1000);
      this.lastTick = now;
      this.update(dt);
      this.render();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  },

  getSlotSummary(slotIdx) {
    const raw = safeStorageGet(SAVE_KEY_PREFIX + slotIdx);
    let data = null;
    if (raw) { try { data = JSON.parse(raw); } catch (e) {} }
    if (!data && this.memoryFallbackSlots[slotIdx]) data = this.memoryFallbackSlots[slotIdx];
    if (!data) return null;
    return {
      name: data.name || 'Brie',
      playTimeSec: Math.floor(data.playTimeSec || 0),
      badges: (data.seals || []).length,
      caught: (data.dexCaught || []).length,
      data
    };
  },

  saveToSlot(slotIdx) {
    if (!this.state) return false;
    this.state.slot = slotIdx;
    const json = JSON.stringify(this.state);
    this.memoryFallbackSlots[slotIdx] = JSON.parse(json);
    safeStorageSet(SAVE_KEY_PREFIX + slotIdx, json);
    return true;
  },

  loadFromSlot(slotIdx) {
    const sum = this.getSlotSummary(slotIdx);
    if (!sum || !sum.data) return false;
    this.activeSlot = slotIdx;
    this.state = JSON.parse(JSON.stringify(sum.data));
    this.rng = mulberry32(this.state.rngSeed || 1337);
    this.screen = 'OVERWORLD';
    this.playMapMusic();
    return true;
  },

  startNewGame(slotIdx, playerName, starterId, seed = 4242) {
    this.activeSlot = slotIdx;
    this.rng = mulberry32(seed);
    const starter = createBeatstInstance(starterId, 5, () => this.rng());
    this.state = {
      slot: slotIdx,
      name: playerName || 'Brie',
      playTimeSec: 0,
      rngSeed: seed,
      steps: 0,
      isNight: false,
      gold: 500,
      mapId: 'cruston_town',
      x: 14,
      y: 12,
      dir: 'up',
      seals: [],
      defeatedTrainers: [],
      quests: {},
      secrets: [],
      championBeaten: false,
      dexSeen: [starterId],
      dexCaught: [starterId],
      party: [starter],
      box: [],
      bag: {
        paper_plate: 5,
        wooden_board: 2,
        broth_cup: 3,
        garnish_treat: 2
      }
    };
    this.saveToSlot(slotIdx);
    this.screen = 'OVERWORLD';
    this.playMapMusic();
    this.showDialog([
      `Welcome to Pantrylia, ${this.state.name}!`,
      `Your ${starter.nickname} is eager to battle and meet wild dishes!`,
      'Tip: In wild battles, use PLATE to set a table and befriend bEATsts!'
    ]);
  },

  exportSaveJson(slotIdx = this.activeSlot) {
    if (this.state && slotIdx === this.activeSlot) this.saveToSlot(slotIdx);
    const sum = this.getSlotSummary(slotIdx);
    if (!sum) return null;
    return JSON.stringify(sum.data);
  },

  importSaveJson(jsonStr, slotIdx = this.activeSlot) {
    try {
      const parsed = JSON.parse(jsonStr);
      if (!parsed || !Array.isArray(parsed.party) || !parsed.mapId) return false;
      parsed.slot = slotIdx;
      this.memoryFallbackSlots[slotIdx] = parsed;
      safeStorageSet(SAVE_KEY_PREFIX + slotIdx, JSON.stringify(parsed));
      this.activeSlot = slotIdx;
      this.state = parsed;
      this.rng = mulberry32(this.state.rngSeed || 1337);
      return true;
    } catch (e) {
      return false;
    }
  },

  playMapMusic() {
    if (!this.state) return;
    const m = MAPS[this.state.mapId];
    if (m) AudioEngine.playMusic(m.music);
  },

  showDialog(lines, cb = null) {
    this.dialogQueue = Array.isArray(lines) ? lines.slice() : [lines];
    this.dialogCallback = cb;
    this.screen = 'DIALOG';
  },

  advanceDialog() {
    AudioEngine.playSfx('menu_select');
    this.dialogQueue.shift();
    if (this.dialogQueue.length === 0) {
      const cb = this.dialogCallback;
      this.dialogCallback = null;
      if (this.screen === 'DIALOG') this.screen = 'OVERWORLD';
      if (cb) cb();
    }
  },

  bindInputs() {
    const mapKey = (k) => {
      if (k === 'ArrowUp' || k === 'w' || k === 'W') return 'UP';
      if (k === 'ArrowDown' || k === 's' || k === 'S') return 'DOWN';
      if (k === 'ArrowLeft' || k === 'a' || k === 'A') return 'LEFT';
      if (k === 'ArrowRight' || k === 'd' || k === 'D') return 'RIGHT';
      if (k === 'z' || k === 'Z' || k === 'Enter' || k === ' ') return 'A';
      if (k === 'x' || k === 'X' || k === 'Escape' || k === 'Backspace') return 'B';
      if (k === 'm' || k === 'M') return 'START';
      if (k === 'n' || k === 'N' || k === 'Tab') return 'SELECT';
      return null;
    };

    window.addEventListener('keydown', (e) => {
      const btn = mapKey(e.key);
      if (btn) {
        e.preventDefault();
        if (!this.keyState[btn]) this.pressButton(btn);
        this.keyState[btn] = true;
      }
    });
    window.addEventListener('keyup', (e) => {
      const btn = mapKey(e.key);
      if (btn) this.keyState[btn] = false;
    });

    document.querySelectorAll('[data-gba-btn]').forEach(el => {
      const btn = el.getAttribute('data-gba-btn');
      const down = (ev) => {
        ev.preventDefault();
        this.keyState[btn] = true;
        this.pressButton(btn);
      };
      const up = (ev) => {
        ev.preventDefault();
        this.keyState[btn] = false;
      };
      el.addEventListener('pointerdown', down);
      el.addEventListener('pointerup', up);
      el.addEventListener('pointerleave', up);
      el.addEventListener('pointercancel', up);
    });
  },

  pressButton(btn) {
    AudioEngine.ensureCtx();
    if (this.screen === 'TITLE') {
      AudioEngine.playMusic('title');
      if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        this.cursor = (this.cursor + (btn === 'DOWN' ? 1 : 2)) % 3;
      } else if (btn === 'A' || btn === 'START') {
        AudioEngine.playSfx('menu_select');
        if (this.cursor === 0) { this.screen = 'SLOTS'; this.cursor = 0; }
        else if (this.cursor === 1) { this.screen = 'OPTIONS'; this.cursor = 0; }
        else { this.screen = 'CONTROLS'; }
      }
      return;
    }

    if (this.screen === 'CONTROLS') {
      if (btn === 'A' || btn === 'B') {
        AudioEngine.playSfx('menu_back');
        this.screen = this.state ? 'MENU' : 'TITLE';
      }
      return;
    }

    if (this.screen === 'OPTIONS') {
      if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        this.cursor = (this.cursor + 1) % 3;
      } else if (btn === 'LEFT' || btn === 'RIGHT') {
        AudioEngine.playSfx('menu_move');
        const dir = btn === 'RIGHT' ? 1 : -1;
        if (this.cursor === 0) this.options.textSpeed = Math.max(1, Math.min(3, this.options.textSpeed + dir));
        if (this.cursor === 1) {
          this.options.volume = Math.max(0, Math.min(100, this.options.volume + dir * 10));
          AudioEngine.volume = this.options.volume / 100;
        }
      } else if (btn === 'B' || (btn === 'A' && this.cursor === 2)) {
        AudioEngine.playSfx('menu_back');
        this.screen = this.state ? 'MENU' : 'TITLE';
        this.cursor = 0;
      }
      return;
    }

    if (this.screen === 'SLOTS') {
      if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        this.cursor = (this.cursor + (btn === 'DOWN' ? 1 : 2)) % 3;
      } else if (btn === 'A' || btn === 'START') {
        AudioEngine.playSfx('menu_select');
        const sum = this.getSlotSummary(this.cursor);
        if (sum) {
          this.loadFromSlot(this.cursor);
        } else {
          this.activeSlot = this.cursor;
          this.starterIdx = 0;
          this.screen = 'STARTER';
        }
      } else if (btn === 'B') {
        AudioEngine.playSfx('menu_back');
        this.screen = 'TITLE';
        this.cursor = 0;
      }
      return;
    }

    if (this.screen === 'STARTER') {
      const starters = [1, 39, 77, 115];
      if (btn === 'LEFT' || btn === 'RIGHT') {
        AudioEngine.playSfx('menu_move');
        this.starterIdx = (this.starterIdx + (btn === 'RIGHT' ? 1 : 3)) % 4;
      } else if (btn === 'A') {
        AudioEngine.playSfx('menu_select');
        const nameInput = document.getElementById('player-name-input');
        const pname = (nameInput && nameInput.value.trim()) ? nameInput.value.trim().slice(0, 10) : 'Brie';
        this.startNewGame(this.activeSlot, pname, starters[this.starterIdx]);
      } else if (btn === 'B') {
        AudioEngine.playSfx('menu_back');
        this.screen = 'SLOTS';
      }
      return;
    }

    if (this.screen === 'DIALOG') {
      if (btn === 'A' || btn === 'B') this.advanceDialog();
      return;
    }

    if (this.screen === 'LEARN_MOVE' && this.pendingLearn) {
      if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        this.learnCursor = (this.learnCursor + (btn === 'DOWN' ? 1 : 4)) % 5;
      } else if (btn === 'A') {
        AudioEngine.playSfx('menu_select');
        const { mon, moveId, returnScreen } = this.pendingLearn;
        if (this.learnCursor < 4) {
          const mv = MOVES[moveId];
          mon.moves[this.learnCursor] = { id: mv.id, pp: mv.pp, maxPp: mv.pp };
        }
        this.pendingLearn = null;
        this.screen = returnScreen || 'OVERWORLD';
      } else if (btn === 'B') {
        AudioEngine.playSfx('menu_back');
        const ret = this.pendingLearn.returnScreen || 'OVERWORLD';
        this.pendingLearn = null;
        this.screen = ret;
      }
      return;
    }

    if (this.screen === 'OVERWORLD') {
      if (btn === 'START') {
        AudioEngine.playSfx('menu_select');
        this.screen = 'MENU';
        this.menuCursor = 0;
      } else if (btn === 'SELECT') {
        this.state.isNight = !this.state.isNight;
        AudioEngine.playSfx('menu_move');
        this.showDialog(`Time shifted to ${this.state.isNight ? 'Nighttime (Starlight)' : 'Daytime (Sunny)'}!`);
      } else if (btn === 'A') {
        this.interactAhead();
      } else if (['UP','DOWN','LEFT','RIGHT'].includes(btn)) {
        this.tryMove(btn.toLowerCase());
      }
      return;
    }

    if (this.screen === 'MENU') {
      const items = ['PARTY','bEATdex','BOX','BAG','SAVE','OPTIONS','CONTROLS','CLOSE'];
      if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        this.menuCursor = (this.menuCursor + (btn === 'DOWN' ? 1 : items.length - 1)) % items.length;
      } else if (btn === 'B' || btn === 'START') {
        AudioEngine.playSfx('menu_back');
        this.screen = 'OVERWORLD';
      } else if (btn === 'A') {
        AudioEngine.playSfx('menu_select');
        const pick = items[this.menuCursor];
        if (pick === 'PARTY') { this.partyCursor = 0; this.screen = 'PARTY'; }
        else if (pick === 'bEATdex') { this.dexCursor = 0; this.dexScroll = 0; this.screen = 'DEX'; }
        else if (pick === 'BOX') { this.boxCursor = 0; this.screen = 'BOX'; }
        else if (pick === 'BAG') { this.bagCursor = 0; this.screen = 'BAG'; }
        else if (pick === 'SAVE') {
          this.saveToSlot(this.activeSlot);
          this.showDialog(`Saved Slot ${this.activeSlot + 1} (${this.state.name})!`);
        }
        else if (pick === 'OPTIONS') { this.cursor = 0; this.screen = 'OPTIONS'; }
        else if (pick === 'CONTROLS') { this.screen = 'CONTROLS'; }
        else { this.screen = 'OVERWORLD'; }
      }
      return;
    }

    if (this.screen === 'DEX') {
      const maxEntries = this.state.dexCaught.includes(151) || this.state.dexSeen.includes(151) ? 151 : 150;
      if (btn === 'UP') { this.dexCursor = Math.max(0, this.dexCursor - 1); AudioEngine.playSfx('menu_move'); }
      else if (btn === 'DOWN') { this.dexCursor = Math.min(maxEntries - 1, this.dexCursor + 1); AudioEngine.playSfx('menu_move'); }
      else if (btn === 'LEFT') { this.dexCursor = Math.max(0, this.dexCursor - 10); AudioEngine.playSfx('menu_move'); }
      else if (btn === 'RIGHT') { this.dexCursor = Math.min(maxEntries - 1, this.dexCursor + 10); AudioEngine.playSfx('menu_move'); }
      else if (btn === 'B') { AudioEngine.playSfx('menu_back'); this.screen = 'MENU'; }
      if (this.dexCursor < this.dexScroll) this.dexScroll = this.dexCursor;
      if (this.dexCursor >= this.dexScroll + 7) this.dexScroll = this.dexCursor - 6;
      return;
    }

    if (this.screen === 'PARTY') {
      if (btn === 'UP') { this.partyCursor = Math.max(0, this.partyCursor - 1); AudioEngine.playSfx('menu_move'); }
      else if (btn === 'DOWN') { this.partyCursor = Math.min(this.state.party.length - 1, this.partyCursor + 1); AudioEngine.playSfx('menu_move'); }
      else if (btn === 'A' && this.partyCursor > 0) {
        const tmp = this.state.party[0];
        this.state.party[0] = this.state.party[this.partyCursor];
        this.state.party[this.partyCursor] = tmp;
        this.partyCursor = 0;
        AudioEngine.playSfx('menu_select');
      } else if (btn === 'B') { AudioEngine.playSfx('menu_back'); this.screen = 'MENU'; }
      return;
    }

    if (this.screen === 'BOX') {
      if (btn === 'UP') { this.boxCursor = Math.max(0, this.boxCursor - 1); AudioEngine.playSfx('menu_move'); }
      else if (btn === 'DOWN') { this.boxCursor = Math.min(Math.max(0, this.state.box.length - 1), this.boxCursor + 1); AudioEngine.playSfx('menu_move'); }
      else if (btn === 'A' && this.state.box.length > 0 && this.state.party.length < 6) {
        const mon = this.state.box.splice(this.boxCursor, 1)[0];
        this.state.party.push(mon);
        this.boxCursor = Math.max(0, this.boxCursor - 1);
        AudioEngine.playSfx('menu_select');
      } else if (btn === 'B') { AudioEngine.playSfx('menu_back'); this.screen = 'MENU'; }
      return;
    }

    if (this.screen === 'BAG') {
      const keys = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0);
      if (btn === 'UP' && keys.length) { this.bagCursor = (this.bagCursor + keys.length - 1) % keys.length; AudioEngine.playSfx('menu_move'); }
      else if (btn === 'DOWN' && keys.length) { this.bagCursor = (this.bagCursor + 1) % keys.length; AudioEngine.playSfx('menu_move'); }
      else if (btn === 'A' && keys.length) {
        const k = keys[this.bagCursor];
        const item = ITEMS[k];
        const lead = this.state.party[0];
        if (item && (item.kind === 'heal' || item.kind === 'cure')) {
          if (lead && lead.hp > 0) {
            if (item.healHp) lead.hp = Math.min(lead.maxHp, lead.hp + item.healHp);
            if (item.kind === 'cure' || item.id === 'grand_feast') lead.status = null;
            this.state.bag[k]--;
            AudioEngine.playSfx('heal');
          }
        } else if (item && item.kind === 'recipe' && lead) {
          this.state.bag[k]--;
          this.teachMoveToMon(lead, item.moveId, 'BAG');
        }
      } else if (btn === 'B') { AudioEngine.playSfx('menu_back'); this.screen = 'MENU'; }
      return;
    }

    if (this.screen === 'SHOP') {
      const shop = this.getCurrentShop();
      if (btn === 'UP') { this.shopCursor = (this.shopCursor + shop.stock.length - 1) % shop.stock.length; AudioEngine.playSfx('menu_move'); }
      else if (btn === 'DOWN') { this.shopCursor = (this.shopCursor + 1) % shop.stock.length; AudioEngine.playSfx('menu_move'); }
      else if (btn === 'A') {
        const id = shop.stock[this.shopCursor];
        const it = ITEMS[id];
        if (this.state.gold >= it.price) {
          this.state.gold -= it.price;
          this.state.bag[id] = (this.state.bag[id] || 0) + 1;
          AudioEngine.playSfx('menu_select');
        } else {
          AudioEngine.playSfx('menu_back');
        }
      } else if (btn === 'B') {
        AudioEngine.playSfx('menu_back');
        this.screen = 'OVERWORLD';
      }
      return;
    }

    if (this.screen === 'BATTLE') {
      this.handleBattleInput(btn);
      return;
    }

    if (this.screen === 'CREDITS') {
      if (btn === 'A' || btn === 'B' || btn === 'START') {
        this.screen = 'OVERWORLD';
        this.playMapMusic();
      }
      return;
    }
  },

  getCurrentShop() {
    const map = MAPS[this.state.mapId];
    return REGIONAL_SHOPS[map ? map.region : 'Breadlands'] || REGIONAL_SHOPS.Breadlands;
  },

  teachMoveToMon(mon, moveId, returnScreen) {
    if (mon.moves.some(m => m.id === moveId)) return;
    const mv = MOVES[moveId];
    if (!mv) return;
    if (mon.moves.length < 4) {
      mon.moves.push({ id: mv.id, pp: mv.pp, maxPp: mv.pp });
      AudioEngine.playSfx('level_up');
    } else {
      this.pendingLearn = { mon, moveId, returnScreen };
      this.learnCursor = 0;
      this.screen = 'LEARN_MOVE';
    }
  },

  tryMove(dir) {
    if (!this.state) return;
    this.state.dir = dir;
    const dx = dir === 'left' ? -1 : dir === 'right' ? 1 : 0;
    const dy = dir === 'up' ? -1 : dir === 'down' ? 1 : 0;
    const nx = this.state.x + dx;
    const ny = this.state.y + dy;
    const map = MAPS[this.state.mapId];
    if (!map) return;

    const portal = (map.portals || []).find(p => p.x === nx && p.y === ny);
    if (portal) {
      if (portal.reqSeals && this.state.seals.length < portal.reqSeals) {
        this.showDialog(`This path requires ${portal.reqSeals} Kitchen Seals! You have ${this.state.seals.length}.`);
        return;
      }
      if (portal.reqChampion && !this.state.championBeaten) {
        this.showDialog('Only the Grand Champion may enter the Eternal Pantry!');
        return;
      }
      AudioEngine.playSfx('door');
      this.state.mapId = portal.to;
      this.state.x = portal.tx;
      this.state.y = portal.ty;
      this.playMapMusic();
      return;
    }

    if (nx < 0 || nx >= 30 || ny < 0 || ny >= 18) return;
    const tile = map.grid[ny * 30 + nx];
    if (SOLID_TILES.has(tile)) return;
    if ((map.npcs || []).some(n => n.x === nx && n.y === ny && !this.isNpcHidden(n))) return;

    this.state.x = nx;
    this.state.y = ny;
    this.state.steps++;
    if (this.state.steps % 40 === 0) this.state.isNight = !this.state.isNight;

    // Tall grass tiles: 11 (Bread), 23 (Steam), 35 (Noodle), 47 (Broth), 62 (Postgame)
    if ([11, 23, 35, 47, 62].includes(tile) && map.wildPool && map.wildPool.length > 0) {
      if (this.rng() < 0.16) {
        const pool = map.wildPool.filter(e => !BEATSTS_BY_ID[e[0]].nightOnly || this.state.isNight);
        const pick = pool[Math.floor(this.rng() * pool.length)] || map.wildPool[0];
        const lv = pick[1] + Math.floor(this.rng() * (pick[2] - pick[1] + 1));
        this.startWildBattle(pick[0], lv);
      }
    }
  },

  isNpcHidden(npc) {
    if (npc.questComplete && this.state.quests[npc.questComplete]) return true;
    if (npc.secretId && (this.state.secrets || []).includes(npc.secretId)) return true;
    return false;
  },

  interactAhead() {
    const map = MAPS[this.state.mapId];
    const dx = this.state.dir === 'left' ? -1 : this.state.dir === 'right' ? 1 : 0;
    const dy = this.state.dir === 'up' ? -1 : this.state.dir === 'down' ? 1 : 0;
    const tx = this.state.x + dx;
    const ty = this.state.y + dy;
    const npc = (map.npcs || []).find(n => n.x === tx && n.y === ty && !this.isNpcHidden(n));
    if (!npc) return;

    if (npc.action === 'heal') {
      this.healParty();
      AudioEngine.playMusic('healing');
      this.showDialog([...(npc.lines || ['Restored!']), 'All your bEATsts are simmering at 100% HP and PP!'], () => this.playMapMusic());
      return;
    }
    if (npc.action === 'shop') {
      this.shopCursor = 0;
      this.screen = 'SHOP';
      return;
    }
    if (npc.action === 'secret151') {
      const families = new Set(this.state.party.map(m => BEATSTS_BY_ID[m.speciesId].family));
      const hasAll4 = ['Sandwiches','Dumplings','Noodles','Soup'].every(f => families.has(f));
      const hasRoyal = (this.state.bag.royal_banquet || 0) > 0;
      if (this.state.championBeaten && this.state.isNight && hasAll4 && hasRoyal && !this.state.dexCaught.includes(151)) {
        if (!this.state.secrets.includes('sec_151')) this.state.secrets.push('sec_151');
        this.showDialog([
          'The Secret Pantry shimmers with golden steam...',
          'A luminous aroma unites Sandwich, Dumpling, Noodle, and Soup!',
          'The mythical #151 Consommyth emerges!'
        ], () => this.startWildBattle(151, 55));
      } else {
        this.showDialog('A locked golden pantry door. Inscription: "Only a Champion at Night bearing all 4 Food Families and a Royal Banquet Setting may enter."');
      }
      return;
    }
    if (npc.questGive) {
      this.state.quests[npc.questGive + '_started'] = true;
      this.showDialog(npc.lines);
      return;
    }
    if (npc.questStep) {
      this.state.quests[npc.questStep + '_step1'] = true;
      this.showDialog(npc.lines);
      return;
    }
    if (npc.questComplete) {
      this.state.quests[npc.questComplete] = true;
      this.grantQuestReward(npc.questComplete);
      AudioEngine.playSfx('level_up');
      this.showDialog(npc.lines);
      return;
    }
    if (npc.secretId) {
      if (!this.state.secrets.includes(npc.secretId)) {
        this.state.secrets.push(npc.secretId);
        this.state.gold += 150;
      }
      AudioEngine.playSfx('level_up');
      this.showDialog(npc.lines);
      return;
    }
    if (npc.trainer) {
      const tr = TRAINERS[npc.trainer];
      if (this.state.defeatedTrainers.includes(tr.id)) {
        this.showDialog(`${tr.name}: ${tr.after || tr.win}`);
      } else {
        this.showDialog([`${tr.name}: ${tr.intro}`], () => this.startTrainerBattle(tr));
      }
      return;
    }
    if (npc.id === 'brotholomew' && this.state.dexCaught.length >= 151) {
      this.showDialog(['Chef Brotholomew: 151/151!! You have befriended every bEATst in Pantrylia!', 'Accept the Grand Culinary Diploma of ConsciousNode!']);
      return;
    }
    this.showDialog((npc.lines || ['Hello!']).map(l => `${npc.name}: ${l}`));
  },

  grantQuestReward(qid) {
    const b = this.state.bag;
    if (qid === 'q1_butter') b.ceramic_plate = (b.ceramic_plate || 0) + 3;
    else if (qid === 'q2_lid') { b.bento_set = (b.bento_set || 0) + 2; this.state.gold += 300; }
    else if (qid === 'q3_chopsticks') this.state.gold += 500;
    else if (qid === 'q4_truffle') b.royal_banquet = (b.royal_banquet || 0) + 1;
    else if (qid === 'q5_starter') { b.card_fermented = (b.card_fermented || 0) + 1; this.state.gold += 400; }
    else if (qid === 'q6_ginger') { b.hearty_stew = (b.hearty_stew || 0) + 2; this.state.gold += 350; }
    else if (qid === 'q7_chili') { b.card_spicy = (b.card_spicy || 0) + 1; this.state.gold += 500; }
    else if (qid === 'q8_ladle') { b.grand_feast = (b.grand_feast || 0) + 1; this.state.gold += 600; }
    else if (qid === 'q9_critics') b.royal_banquet = (b.royal_banquet || 0) + 1;
    else if (qid === 'q10_crumb') b.broth_cup = (b.broth_cup || 0) + 2;
    else if (qid === 'q11_scallion') b.garnish_treat = (b.garnish_treat || 0) + 3;
    else if (qid === 'q12_salt') b.wooden_board = (b.wooden_board || 0) + 2;
    else if (qid === 'q13_stock') b.card_brothy = (b.card_brothy || 0) + 1;
    else if (qid === 'q14_steam') b.mint_tea = (b.mint_tea || 0) + 3;
    else if (qid === 'q15_wok') b.wakeup_espresso = (b.wakeup_espresso || 0) + 2;
    else if (qid === 'q16_banquet') { b.grand_feast = (b.grand_feast || 0) + 2; this.state.gold += 2000; }
  },

  healParty() {
    if (!this.state) return;
    for (const m of this.state.party) {
      m.hp = m.maxHp;
      m.status = null;
      for (const mv of m.moves) mv.pp = mv.maxPp;
    }
  },

  markSeen(speciesId) {
    if (!this.state.dexSeen.includes(speciesId)) this.state.dexSeen.push(speciesId);
  },
  markCaught(speciesId) {
    this.markSeen(speciesId);
    if (!this.state.dexCaught.includes(speciesId)) this.state.dexCaught.push(speciesId);
  },

  startWildBattle(speciesId, level) {
    this.markSeen(speciesId);
    const foe = createBeatstInstance(speciesId, level, () => this.rng());
    const activeIdx = Math.max(0, this.state.party.findIndex(m => m.hp > 0));
    AudioEngine.playMusic('battle_wild');
    this.battle = {
      isWild: true, trainer: null, foeParty: [foe], foeIdx: 0, playerIdx: activeIdx,
      temp: 0, usedFavTreat: false, phase: 'MAIN', cursor: 0,
      log: `A wild ${foe.nickname} (Lv.${foe.level}) popped out!`
    };
    this.screen = 'BATTLE';
  },

  startTrainerBattle(trainer) {
    const foeParty = trainer.party.map(p => {
      this.markSeen(p.id);
      return createBeatstInstance(p.id, p.lv, () => this.rng());
    });
    const activeIdx = Math.max(0, this.state.party.findIndex(m => m.hp > 0));
    const music = trainer.id.startsWith('rival') ? 'battle_rival'
      : trainer.id === 'champion_aurelia' ? 'battle_champion' : 'battle_chef';
    AudioEngine.playMusic(music);
    this.battle = {
      isWild: false, trainer, foeParty, foeIdx: 0, playerIdx: activeIdx,
      temp: 0, usedFavTreat: false, phase: 'MAIN', cursor: 0,
      log: `${trainer.name} sent out ${foeParty[0].nickname}!`
    };
    this.screen = 'BATTLE';
  },

  handleBattleInput(btn) {
    const b = this.battle;
    if (!b) return;
    if (b.phase === 'LOG') {
      if (btn === 'A' || btn === 'B') {
        AudioEngine.playSfx('menu_select');
        if (b.pendingEnd) this.finishBattle(b.pendingEnd);
        else { b.phase = 'MAIN'; b.cursor = 0; }
      }
      return;
    }

    if (b.phase === 'MAIN') {
      // 0:FIGHT, 1:PLATE, 2:BAG, 3:PARTY (Switching works in wild AND trainer battles! B flees in wild!)
      if (btn === 'B' && b.isWild) {
        AudioEngine.playSfx('menu_back');
        b.log = 'Got away safely!';
        b.pendingEnd = 'RUN';
        b.phase = 'LOG';
        return;
      }
      if (btn === 'UP' || btn === 'DOWN' || btn === 'LEFT' || btn === 'RIGHT') {
        AudioEngine.playSfx('menu_move');
        if (btn === 'LEFT' || btn === 'RIGHT') b.cursor ^= 1;
        else b.cursor ^= 2;
      } else if (btn === 'A') {
        AudioEngine.playSfx('menu_select');
        if (b.cursor === 0) { b.phase = 'FIGHT'; b.cursor = 0; }
        else if (b.cursor === 1) {
          if (!b.isWild) { b.log = 'Cannot plate another chef bEATst!'; b.phase = 'LOG'; }
          else { b.phase = 'PLATE'; b.cursor = 0; }
        }
        else if (b.cursor === 2) { b.phase = 'BAG'; b.cursor = 0; }
        else { b.phase = 'PARTY'; b.cursor = 0; }
      }
      return;
    }

    if (b.phase === 'FIGHT') {
      const mon = this.state.party[b.playerIdx];
      if (btn === 'UP' || btn === 'DOWN' || btn === 'LEFT' || btn === 'RIGHT') {
        AudioEngine.playSfx('menu_move');
        b.cursor = (b.cursor + (btn === 'DOWN' || btn === 'RIGHT' ? 1 : mon.moves.length - 1)) % mon.moves.length;
      } else if (btn === 'B') {
        AudioEngine.playSfx('menu_back'); b.phase = 'MAIN'; b.cursor = 0;
      } else if (btn === 'A') {
        const mvSlot = mon.moves[b.cursor];
        if (mvSlot && mvSlot.pp > 0) { mvSlot.pp--; this.executeBattleTurn(mvSlot.id); }
        else if (mon.moves.every(m => m.pp <= 0)) { this.executeBattleTurn(0); }
      }
      return;
    }

    if (b.phase === 'PLATE') {
      const plates = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0 && (ITEMS[k].kind === 'plate' || ITEMS[k].kind === 'treat'));
      if (btn === 'B' || plates.length === 0) {
        AudioEngine.playSfx('menu_back'); b.phase = 'MAIN'; b.cursor = 0;
      } else if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        b.cursor = (b.cursor + (btn === 'DOWN' ? 1 : plates.length - 1)) % plates.length;
      } else if (btn === 'A') {
        this.usePlatingItem(plates[b.cursor]);
      }
      return;
    }

    if (b.phase === 'BAG') {
      const heals = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0 && ['heal','cure','revive'].includes(ITEMS[k].kind));
      if (btn === 'B' || heals.length === 0) {
        AudioEngine.playSfx('menu_back'); b.phase = 'MAIN'; b.cursor = 0;
      } else if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        b.cursor = (b.cursor + (btn === 'DOWN' ? 1 : heals.length - 1)) % heals.length;
      } else if (btn === 'A') {
        const itemId = heals[b.cursor];
        const it = ITEMS[itemId];
        const mon = this.state.party[b.playerIdx];
        if (it.kind === 'heal') {
          mon.hp = Math.min(mon.maxHp, mon.hp + it.healHp);
          if (it.id === 'grand_feast') mon.status = null;
        } else if (it.kind === 'cure') mon.status = null;
        else if (it.kind === 'revive') {
          const fainted = this.state.party.find(m => m.hp <= 0);
          if (fainted) fainted.hp = Math.floor(fainted.maxHp * 0.5);
        }
        this.state.bag[itemId]--;
        AudioEngine.playSfx('heal');
        const foeMsg = this.doFoeAttack(b.foeParty[b.foeIdx], mon);
        b.log = `Used ${it.name}! ${foeMsg}`;
        b.phase = 'LOG';
      }
      return;
    }

    if (b.phase === 'PARTY') {
      if (btn === 'B') { AudioEngine.playSfx('menu_back'); b.phase = 'MAIN'; b.cursor = 0; }
      else if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        b.cursor = (b.cursor + (btn === 'DOWN' ? 1 : this.state.party.length - 1)) % this.state.party.length;
      } else if (btn === 'A') {
        const target = this.state.party[b.cursor];
        if (target && target.hp > 0 && b.cursor !== b.playerIdx) {
          b.playerIdx = b.cursor;
          const foeMsg = this.doFoeAttack(b.foeParty[b.foeIdx], target);
          b.log = `Go, ${target.nickname}! ${foeMsg}`;
          b.phase = 'LOG';
        }
      }
    }
  },

  computeDamage(attacker, defender, move, battleTemp) {
    if (move.cat === 'status' || move.power === 0) return { dmg: 0, eff: 1, combo: null };
    const atkSp = BEATSTS_BY_ID[attacker.speciesId];
    const defSp = BEATSTS_BY_ID[defender.speciesId];
    const stab = atkSp.types.includes(move.type) ? 1.25 : 1.0;
    const eff = getTypeEffectiveness(move.type, defSp.types);
    let tempMult = 1.0;
    if (battleTemp >= 2) {
      if (['Spicy','Fried','Toasted'].includes(move.type)) tempMult = 1.25;
      if (['Chilled','Raw'].includes(move.type)) tempMult = 0.8;
    } else if (battleTemp <= -2) {
      if (['Chilled','Raw','Pickled'].includes(move.type)) tempMult = 1.25;
      if (['Spicy','Brothy'].includes(move.type)) tempMult = 0.8;
    }
    let combo = null;
    if (attacker.lastMoveType && attacker.lastMoveType !== move.type) {
      combo = FLAVOR_COMBOS[`${attacker.lastMoveType}+${move.type}`] || null;
    }
    const comboMult = combo ? combo.bonus : 1.0;
    const rand = 0.9 + this.rng() * 0.15;
    const base = (((2 * attacker.level / 5 + 2) * move.power * (attacker.atk / Math.max(1, defender.def))) / 42 + 2);
    const dmg = Math.max(1, Math.floor(base * stab * eff * tempMult * comboMult * rand));
    return { dmg, eff, combo };
  },

  executeBattleTurn(moveId) {
    const b = this.battle;
    const player = this.state.party[b.playerIdx];
    const foe = b.foeParty[b.foeIdx];
    const mv = MOVES[moveId] || MOVES[0];

    b.temp = Math.max(-2, Math.min(2, b.temp + (mv.temp || 0)));
    const res = this.computeDamage(player, foe, mv, b.temp);
    player.lastMoveType = mv.type;
    this.animType = mv.anim;
    this.animTimer = 0.35;

    let msg = `${player.nickname} used ${mv.name}! `;
    if (res.dmg > 0) {
      foe.hp = Math.max(0, foe.hp - res.dmg);
      if (res.eff > 1) { msg += 'Super tasty! '; AudioEngine.playSfx('hit_super'); }
      else if (res.eff < 1) { msg += 'Not very savory... '; AudioEngine.playSfx('hit_weak'); }
      else AudioEngine.playSfx('hit_normal');
      if (res.combo) {
        msg += `FLAVOR COMBO (${res.combo.name})! `;
        player.hp = Math.min(player.maxHp, player.hp + Math.max(1, Math.floor(player.maxHp * res.combo.healPct)));
      }
      if (mv.drain) player.hp = Math.min(player.maxHp, player.hp + Math.max(1, Math.floor(res.dmg * mv.drain)));
    }
    if (mv.status && this.rng() < (mv.sChance || 1)) {
      foe.status = mv.status;
      msg += `${foe.nickname} is ${mv.status}! `;
    }

    if (foe.hp <= 0) {
      const xpGain = Math.floor(foe.level * 16 * (b.isWild ? 1 : 1.4));
      msg += `${foe.nickname} fainted! +${xpGain} XP! `;
      msg += this.grantXp(player, xpGain);
      // Kehai fix 2026-11-14: only advance when another foe exists, so the battle
      // screen never indexes past the last foe (was: black screen on every win).
      if (b.foeIdx + 1 < b.foeParty.length) {
        b.foeIdx++;
        msg += `${b.trainer.name} sent out ${b.foeParty[b.foeIdx].nickname}!`;
      } else {
        b.pendingEnd = 'WIN';
      }
      b.log = msg;
      b.phase = 'LOG';
      return;
    }

    msg += this.doFoeAttack(foe, player);
    if (player.hp <= 0) {
      const nextIdx = this.state.party.findIndex(m => m.hp > 0);
      if (nextIdx >= 0) {
        b.playerIdx = nextIdx;
        msg += ` ${player.nickname} fainted! Go, ${this.state.party[nextIdx].nickname}!`;
      } else {
        b.pendingEnd = 'LOSE';
        msg += ' All your bEATsts fainted! Rushing back to Simmer Inn...';
      }
    }
    b.log = msg;
    b.phase = 'LOG';
  },

  doFoeAttack(foe, player) {
    if (foe.hp <= 0 || player.hp <= 0) return '';
    const b = this.battle;
    const mvSlot = foe.moves[Math.floor(this.rng() * foe.moves.length)];
    const mv = MOVES[mvSlot.id] || MOVES[0];
    b.temp = Math.max(-2, Math.min(2, b.temp + (mv.temp || 0)));
    const res = this.computeDamage(foe, player, mv, b.temp);
    foe.lastMoveType = mv.type;
    player.hp = Math.max(0, player.hp - res.dmg);
    return `${foe.nickname} used ${mv.name} (-${res.dmg} HP)!`;
  },

  grantXp(mon, xp) {
    mon.xp += xp;
    let out = '';
    while (mon.xp >= mon.nextXp && mon.level < 100) {
      mon.level++;
      recalcStats(mon);
      AudioEngine.playSfx('level_up');
      out += `${mon.nickname} reached Lv.${mon.level}! `;
      const sp = BEATSTS_BY_ID[mon.speciesId];
      // Check level-up learnset
      for (const [lv, mid] of sp.learnset) {
        if (lv === mon.level && !mon.moves.some(m => m.id === mid)) {
          const mv = MOVES[mid];
          if (mon.moves.length < 4) {
            mon.moves.push({ id: mv.id, pp: mv.pp, maxPp: mv.pp });
            out += `Learned ${mv.name}! `;
          } else {
            let minIdx = 0;
            mon.moves.forEach((m, i) => { if (MOVES[m.id].power < MOVES[mon.moves[minIdx].id].power) minIdx = i; });
            if (mv.power > MOVES[mon.moves[minIdx].id].power) {
              mon.moves[minIdx] = { id: mv.id, pp: mv.pp, maxPp: mv.pp };
              out += `Learned ${mv.name}! `;
            }
          }
        }
      }
      if (sp.evo && mon.level >= sp.evo.level) {
        const nextSp = BEATSTS_BY_ID[sp.evo.to];
        if (nextSp) {
          mon.speciesId = nextSp.id;
          mon.nickname = nextSp.name;
          recalcStats(mon);
          this.markCaught(nextSp.id);
          AudioEngine.playMusic('evolution');
          out += `Evolved into ${nextSp.name}! `;
        }
      }
    }
    return out;
  },

  usePlatingItem(itemId) {
    const b = this.battle;
    const it = ITEMS[itemId];
    const foe = b.foeParty[b.foeIdx];
    const player = this.state.party[b.playerIdx];
    this.state.bag[itemId]--;

    if (it.kind === 'treat') {
      b.usedFavTreat = true;
      AudioEngine.playSfx('plating_set');
      const foeMsg = this.doFoeAttack(foe, player);
      b.log = `Sprinkled ${it.name}! ${foe.nickname} looks delighted! ${foeMsg}`;
      b.phase = 'LOG';
      return;
    }

    const sp = BEATSTS_BY_ID[foe.speciesId];
    const chance = calcPlatingChance(sp, foe.hp, foe.maxHp, foe.status, b.usedFavTreat, this.state.isNight, it);
    AudioEngine.playSfx('plating_set');

    if (chance === 0 && sp.nightOnly && !this.state.isNight) {
      b.log = `${sp.name} only sits down at Night!`; b.phase = 'LOG'; return;
    }
    if (chance === 0 && sp.minTier && it.tier < sp.minTier) {
      b.log = `${sp.name} insists on a Tier ${sp.minTier}+ setting!`; b.phase = 'LOG'; return;
    }

    if (this.rng() < chance) {
      AudioEngine.playSfx('plating_success');
      this.markCaught(sp.id);
      if (this.state.party.length < 6) {
        this.state.party.push(foe);
        b.log = `${foe.nickname} sat down at your ${it.name} and joined your party!`;
      } else {
        this.state.box.push(foe);
        b.log = `${foe.nickname} sat down at your ${it.name} and hopped into your Box!`;
      }
      b.pendingEnd = 'CAUGHT';
      b.phase = 'LOG';
    } else {
      AudioEngine.playSfx('plating_fail');
      const foeMsg = this.doFoeAttack(foe, player);
      b.log = `${foe.nickname} sniffed the ${it.name} (${Math.round(chance*100)}%) and stepped back! ${foeMsg}`;
      b.phase = 'LOG';
    }
  },

  finishBattle(outcome) {
    const b = this.battle;
    this.battle = null;
    if (outcome === 'WIN' && b && !b.isWild && b.trainer) {
      const tr = b.trainer;
      if (!this.state.defeatedTrainers.includes(tr.id)) {
        this.state.defeatedTrainers.push(tr.id);
        this.state.gold += tr.rewardGold || 200;
        if (tr.seal && !this.state.seals.includes(tr.seal)) this.state.seals.push(tr.seal);
      }
      AudioEngine.playMusic('victory');
      if (tr.id === 'champion_aurelia') {
        this.state.championBeaten = true;
        this.saveToSlot(this.activeSlot);
        this.showDialog([tr.win, 'Welcome to the Hall of Flavor! The Eternal Pantry is now open!'], () => {
          this.creditsScroll = 0;
          this.screen = 'CREDITS';
          AudioEngine.playMusic('credits');
        });
        return;
      }
      this.saveToSlot(this.activeSlot);
      this.showDialog(tr.win, () => this.playMapMusic());
      return;
    }

    if (outcome === 'LOSE') {
      this.healParty();
      this.state.mapId = 'cruston_town';
      this.state.x = 11;
      this.state.y = 12;
      this.screen = 'OVERWORLD';
      this.playMapMusic();
      return;
    }

    this.screen = 'OVERWORLD';
    this.playMapMusic();
  },

  update(dt) {
    this.frameCount++;
    if (this.state && ['OVERWORLD','BATTLE','MENU','DEX','PARTY','BOX','BAG','SHOP','LEARN_MOVE'].includes(this.screen)) {
      this.state.playTimeSec += dt;
    }
    if (this.animTimer > 0) this.animTimer = Math.max(0, this.animTimer - dt);
    if (this.screen === 'CREDITS') this.creditsScroll += dt * 18;

    if (this.screen === 'OVERWORLD') {
      this.moveCooldown = Math.max(0, this.moveCooldown - dt);
      if (this.moveCooldown <= 0) {
        for (const d of ['UP','DOWN','LEFT','RIGHT']) {
          if (this.keyState[d]) {
            this.tryMove(d.toLowerCase());
            this.moveCooldown = 0.14;
            break;
          }
        }
      }
    }
  },

  // === GBA 240x160 BITMAP PIXEL RENDERER (BITMAP FONT ONLY) ===
  drawSprite32(grid, palette, dx, dy, scale = 1) {
    const ctx = this.ctx;
    for (let y = 0; y < 32; y++) {
      for (let x = 0; x < 32; x++) {
        const cIdx = grid[y * 32 + x];
        if (cIdx === 0) continue;
        ctx.fillStyle = palette[cIdx] || '#FF00FF';
        ctx.fillRect(dx + x * scale, dy + y * scale, scale, scale);
      }
    }
  },

  drawTile8(tileId, dx, dy) {
    const ctx = this.ctx;
    const t = TILES_8X8[tileId] || TILES_8X8[0];
    for (let y = 0; y < 8; y++) {
      for (let x = 0; x < 8; x++) {
        const cIdx = t[y * 8 + x];
        if (cIdx === 0) continue;
        ctx.fillStyle = TILE_PALETTE[cIdx];
        ctx.fillRect(dx + x, dy + y, 1, 1);
      }
    }
  },

  drawBox(x, y, w, h, bg = '#182030', border = '#F8F8F0') {
    const ctx = this.ctx;
    ctx.fillStyle = bg;
    ctx.fillRect(x, y, w, h);
    ctx.strokeStyle = border;
    ctx.lineWidth = 1;
    ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  },

  drawText(txt, x, y, color = '#F8F8F0', useSerif = false) {
    drawBitmapText(this.ctx, txt, x, y, color, useSerif);
  },

  render() {
    const ctx = this.ctx;
    if (!ctx) return;
    ctx.fillStyle = '#101420';
    ctx.fillRect(0, 0, 240, 160);

    if (this.screen === 'TITLE') return this.renderTitle();
    if (this.screen === 'SLOTS') return this.renderSlots();
    if (this.screen === 'STARTER') return this.renderStarter();
    if (this.screen === 'OPTIONS') return this.renderOptions();
    if (this.screen === 'CONTROLS') return this.renderControls();
    if (this.screen === 'CREDITS') return this.renderCredits();

    if (this.screen === 'BATTLE') return this.renderBattle();
    this.renderOverworld();
    if (this.screen === 'DIALOG') this.renderDialog();
    if (this.screen === 'MENU') this.renderMenu();
    if (this.screen === 'DEX') this.renderDex();
    if (this.screen === 'PARTY') this.renderParty();
    if (this.screen === 'BOX') this.renderBox();
    if (this.screen === 'BAG') this.renderBag();
    if (this.screen === 'SHOP') this.renderShop();
    if (this.screen === 'LEARN_MOVE') this.renderLearnMove();
  },

  renderTitle() {
    this.drawBox(4, 4, 232, 152, '#1A1E34', '#F0C040');
    this.drawText('bEATsts', 92, 12, '#F8E888', true);
    this.drawText('ConsciousNode SoftWorks', 28, 32, '#A8DADC', false);
    this.drawSprite32(BEATSTS_BY_ID[1].front, BEATSTS_BY_ID[1].palette, 22, 48, 1);
    this.drawSprite32(BEATSTS_BY_ID[39].front, BEATSTS_BY_ID[39].palette, 74, 48, 1);
    this.drawSprite32(BEATSTS_BY_ID[77].front, BEATSTS_BY_ID[77].palette, 126, 48, 1);
    this.drawSprite32(BEATSTS_BY_ID[115].front, BEATSTS_BY_ID[115].palette, 178, 48, 1);

    const opts = ['PLAY / SAVE SLOTS', 'OPTIONS', 'CONTROLS'];
    opts.forEach((o, i) => {
      const sel = i === this.cursor;
      this.drawText((sel ? '> ' : '  ') + o, 44, 94 + i * 14, sel ? '#F8E888' : '#F8F8F0');
    });
    this.drawText('Press Z / Enter / A', 44, 140, '#98D830');
  },

  renderSlots() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#F8F8F0');
    this.drawText('SELECT SAVE SLOT', 16, 12, '#F8E888');
    for (let i = 0; i < 3; i++) {
      const sum = this.getSlotSummary(i);
      const y = 30 + i * 38;
      const sel = i === this.cursor;
      this.drawBox(14, y, 212, 32, sel ? '#283854' : '#182234', sel ? '#F8E888' : '#708090');
      if (sum) {
        const mins = Math.floor(sum.playTimeSec / 60);
        this.drawText(`SLOT ${i+1}: ${sum.name}`, 20, y + 5, '#F8F8F0');
        this.drawText(`Seals:${sum.badges}/8 Dex:${sum.caught} ${mins}m`, 20, y + 17, '#A8DADC');
      } else {
        this.drawText(`SLOT ${i+1}: [ NEW GAME ]`, 20, y + 11, '#98D830');
      }
    }
  },

  renderStarter() {
    const starters = [1, 39, 77, 115];
    this.drawBox(6, 6, 228, 148, '#182030', '#F0C040');
    this.drawText('CHOOSE YOUR bEATst!', 40, 12, '#F8E888');
    starters.forEach((id, i) => {
      const sp = BEATSTS_BY_ID[id];
      const x = 14 + i * 54;
      const sel = i === this.starterIdx;
      this.drawBox(x, 28, 50, 62, sel ? '#304060' : '#1A2438', sel ? '#F8E888' : '#506070');
      this.drawSprite32(sp.front, sp.palette, x + 9, 34, 1);
      this.drawText(sp.family.slice(0,5), x + 5, 72, '#A8DADC');
    });
    const cur = BEATSTS_BY_ID[starters[this.starterIdx]];
    this.drawText(`${cur.name}`, 14, 98, '#F8F8F0');
    this.drawText(`${cur.types.join('/')}`, 14, 110, '#A8DADC');
    this.drawText(cur.dex.slice(0, 26), 14, 124, '#C0C8D0');
    this.drawText('LEFT/RIGHT  A:Start!', 36, 140, '#98D830');
  },

  renderOptions() {
    this.drawBox(12, 12, 216, 136, '#141C2C', '#F8F8F0');
    this.drawText('OPTIONS', 92, 20, '#F8E888', true);
    const spdNames = ['', 'Slow', 'Normal', 'Fast'];
    const rows = [
      `Text : < ${spdNames[this.options.textSpeed]} >`,
      `Vol  : < ${this.options.volume}% >`,
      'Back'
    ];
    rows.forEach((r, i) => {
      this.drawText((i === this.cursor ? '> ' : '  ') + r, 28, 54 + i * 18, i === this.cursor ? '#F8E888' : '#F8F8F0');
    });
  },

  renderControls() {
    this.drawBox(8, 8, 224, 144, '#141C2C', '#F8F8F0');
    this.drawText('CONTROLS', 88, 14, '#F8E888', true);
    const lines = [
      'Move : Arrows / WASD / DPad',
      'A    : Z / Enter / Space',
      'B    : X / Esc / Backspace',
      'Menu : M (Start)',
      'Time : N (Select Day/Night)'
    ];
    lines.forEach((l, i) => this.drawText(l, 14, 42 + i * 15, '#F8F8F0'));
    this.drawText('Press A or B to return', 32, 132, '#98D830');
  },

  renderOverworld() {
    const map = MAPS[this.state.mapId];
    if (!map) return;
    this.ctx.fillStyle = '#182030';
    this.ctx.fillRect(0, 0, 240, 16);
    this.drawText(map.name.slice(0, 15), 2, 4, '#F8E888');
    this.drawText(`${this.state.isNight ? 'N' : 'D'} S:${this.state.seals.length} ${this.state.gold}G`, 130, 4, '#A8DADC');

    for (let y = 0; y < 18; y++) {
      for (let x = 0; x < 30; x++) {
        this.drawTile8(map.grid[y * 30 + x], x * 8, 16 + y * 8);
      }
    }

    if (this.state.isNight) {
      this.ctx.fillStyle = 'rgba(16, 24, 56, 0.35)';
      this.ctx.fillRect(0, 16, 240, 144);
    }

    for (const npc of (map.npcs || [])) {
      if (this.isNpcHidden(npc)) continue;
      drawCharSprite16(this.ctx, npc.sprite || 'villager_a', npc.dir || 'down', npc.x * 8 - 4, 16 + npc.y * 8 - 8);
    }

    drawCharSprite16(this.ctx, 'player', this.state.dir || 'down', this.state.x * 8 - 4, 16 + this.state.y * 8 - 8);
  },

  renderDialog() {
    this.drawBox(4, 108, 232, 48, '#141C2C', '#F8F8F0');
    const txt = toAsciiFontStr(this.dialogQueue[0] || '');
    const words = txt.split(' ');
    let line = '', y = 114;
    for (const w of words) {
      if ((line + w).length > 27) {
        this.drawText(line, 10, y, '#F8F8F0');
        line = w + ' ';
        y += 10;
      } else line += w + ' ';
    }
    if (line && y < 148) this.drawText(line, 10, y, '#F8F8F0');
    this.drawText('v', 224, 144, '#F8E888');
  },

  renderBattle() {
    const b = this.battle;
    if (!b) return;
    const player = this.state.party[b.playerIdx];
    const foe = b.foeParty[b.foeIdx];
    const pSp = BEATSTS_BY_ID[player.speciesId];
    const fSp = BEATSTS_BY_ID[foe.speciesId];

    this.ctx.fillStyle = '#243448';
    this.ctx.fillRect(0, 0, 240, 108);
    this.ctx.fillStyle = '#385068';
    this.ctx.fillRect(0, 76, 240, 32);

    const tempLabels = { '-2':'CHILL -2', '-1':'COOL -1', '0':'ROOM 0', '1':'WARM +1', '2':'SEAR +2' };
    const tempColors = { '-2':'#4CC9F0', '-1':'#A8DADC', '0':'#F8F8F0', '1':'#E8A850', '2':'#E63946' };
    this.drawBox(66, 2, 108, 13, '#101824', tempColors[b.temp]);
    this.drawText(`TEMP:${tempLabels[b.temp]}`, 70, 5, tempColors[b.temp]);

    // Foe HUD & 32x32 front sprite
    this.drawBox(4, 18, 128, 28, '#182030', '#F8F8F0');
    this.drawText(`${foe.nickname.slice(0,10)} L${foe.level}`, 8, 21, '#F8F8F0');
    this.ctx.fillStyle = '#404858'; this.ctx.fillRect(8, 32, 114, 5);
    this.ctx.fillStyle = foe.hp > foe.maxHp * 0.3 ? '#52B788' : '#E63946';
    this.ctx.fillRect(8, 32, Math.floor(114 * (foe.hp / foe.maxHp)), 5);
    if (foe.status) this.drawText(foe.status, 8, 38, '#F8E888');
    this.drawSprite32(fSp.front, fSp.palette, 154, 18, 2);

    // Player 32x32 back sprite & HUD
    this.drawSprite32(pSp.back, pSp.palette, 16, 46, 2);
    this.drawBox(102, 66, 134, 38, '#182030', '#F8F8F0');
    this.drawText(`${player.nickname.slice(0,10)} L${player.level}`, 106, 70, '#F8F8F0');
    this.ctx.fillStyle = '#404858'; this.ctx.fillRect(106, 82, 120, 5);
    this.ctx.fillStyle = player.hp > player.maxHp * 0.3 ? '#52B788' : '#E63946';
    this.ctx.fillRect(106, 82, Math.floor(120 * (player.hp / player.maxHp)), 5);
    this.drawText(`HP ${player.hp}/${player.maxHp}`, 106, 91, '#A8DADC');

    if (this.animTimer > 0) {
      this.ctx.fillStyle = this.animType === 'flame' ? 'rgba(230,57,70,0.45)' :
        this.animType === 'chill' ? 'rgba(76,201,240,0.45)' : 'rgba(248,232,136,0.45)';
      this.ctx.fillRect(150, 18, 68, 68);
    }

    this.drawBox(2, 108, 236, 50, '#141C2C', '#F8F8F0');
    if (b.phase === 'LOG') {
      const words = toAsciiFontStr(b.log).split(' ');
      let line = '', y = 113;
      for (const w of words) {
        if ((line + w).length > 27) { this.drawText(line, 8, y, '#F8F8F0'); line = w + ' '; y += 10; }
        else line += w + ' ';
      }
      if (line && y < 150) this.drawText(line, 8, y, '#F8F8F0');
    } else if (b.phase === 'MAIN') {
      this.drawText(b.log.slice(0, 27), 8, 113, '#A8DADC');
      const opts = ['FIGHT', 'PLATE', 'BAG', 'PARTY'];
      opts.forEach((o, i) => {
        const x = 16 + (i % 2) * 110;
        const y = 128 + Math.floor(i / 2) * 13;
        this.drawText((b.cursor === i ? '> ' : '  ') + o, x, y, b.cursor === i ? '#F8E888' : '#F8F8F0');
      });
    } else if (b.phase === 'FIGHT') {
      player.moves.forEach((ms, i) => {
        const mv = MOVES[ms.id];
        const x = 6 + (i % 2) * 118;
        const y = 113 + Math.floor(i / 2) * 21;
        this.drawText((b.cursor === i ? '>' : ' ') + mv.name.slice(0,12), x, y, b.cursor === i ? '#F8E888' : '#F8F8F0');
        this.drawText(`${mv.type.slice(0,5)} ${ms.pp}/${ms.maxPp}`, x + 8, y + 10, '#A8DADC');
      });
    } else if (b.phase === 'PLATE') {
      const plates = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0 && (ITEMS[k].kind === 'plate' || ITEMS[k].kind === 'treat'));
      if (!plates.length) this.drawText('No plates/treats! (B)', 10, 122, '#E63946');
      plates.slice(0, 4).forEach((k, i) => {
        const it = ITEMS[k];
        const pct = it.kind === 'plate' ? Math.round(calcPlatingChance(fSp, foe.hp, foe.maxHp, foe.status, b.usedFavTreat, this.state.isNight, it) * 100) + '%' : 'TRT';
        this.drawText((b.cursor === i ? '>' : ' ') + `${it.name.slice(0,15)} x${this.state.bag[k]} ${pct}`, 6, 113 + i * 11, b.cursor === i ? '#F8E888' : '#F8F8F0');
      });
    } else if (b.phase === 'BAG') {
      const heals = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0 && ['heal','cure','revive'].includes(ITEMS[k].kind));
      if (!heals.length) this.drawText('No healing items! (B)', 10, 122, '#E63946');
      heals.slice(0, 4).forEach((k, i) => {
        this.drawText((b.cursor === i ? '>' : ' ') + `${ITEMS[k].name.slice(0,18)} x${this.state.bag[k]}`, 6, 113 + i * 11, b.cursor === i ? '#F8E888' : '#F8F8F0');
      });
    } else if (b.phase === 'PARTY') {
      this.state.party.slice(0, 4).forEach((m, i) => {
        this.drawText((b.cursor === i ? '>' : ' ') + `${m.nickname.slice(0,12)} ${m.hp}/${m.maxHp}`, 6, 113 + i * 11, b.cursor === i ? '#F8E888' : '#F8F8F0');
      });
    }
  },

  renderMenu() {
    this.drawBox(132, 16, 104, 138, '#141C2C', '#F8F8F0');
    const items = ['PARTY','bEATdex','BOX','BAG','SAVE','OPTIONS','CONTROLS','CLOSE'];
    items.forEach((it, i) => {
      this.drawText((this.menuCursor === i ? '>' : ' ') + it, 138, 24 + i * 15, this.menuCursor === i ? '#F8E888' : '#F8F8F0');
    });
  },

  renderDex() {
    this.drawBox(4, 4, 232, 152, '#141C2C', '#F0C040');
    const maxEntries = this.state.dexCaught.includes(151) || this.state.dexSeen.includes(151) ? 151 : 150;
    this.drawText(`bEATdex ${this.state.dexCaught.length}/${maxEntries}`, 10, 10, '#F8E888');
    if (this.state.dexCaught.length >= 151) this.drawText('COMPLETE!', 154, 10, '#98D830');
    for (let i = 0; i < 7; i++) {
      const idx = this.dexScroll + i;
      if (idx >= maxEntries) break;
      const sp = BEATSTS[idx];
      const seen = this.state.dexSeen.includes(sp.id);
      const caught = this.state.dexCaught.includes(sp.id);
      const sel = idx === this.dexCursor;
      const label = `${String(sp.id).padStart(3,'0')} ${seen ? sp.name.slice(0,10) : '???'}${caught ? '*' : ''}`;
      this.drawText((sel ? '>' : ' ') + label, 8, 26 + i * 13, sel ? '#F8E888' : '#F8F8F0');
    }
    const curSp = BEATSTS[this.dexCursor];
    if (curSp && this.state.dexSeen.includes(curSp.id)) {
      this.drawSprite32(curSp.front, curSp.palette, 154, 24, 2);
      this.drawText(curSp.types.join('/').slice(0, 12), 140, 92, '#A8DADC');
      this.drawText(curSp.dex.slice(0, 27), 10, 126, '#C0C8D0');
      this.drawText(curSp.dex.slice(27, 54), 10, 138, '#C0C8D0');
    } else {
      this.drawText('Not seen yet', 132, 56, '#708090');
    }
  },

  renderParty() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#F8F8F0');
    this.drawText('PARTY (A:Lead B:Back)', 12, 12, '#F8E888');
    this.state.party.forEach((m, i) => {
      const y = 30 + i * 19;
      const sel = i === this.partyCursor;
      this.drawText((sel ? '>' : ' ') + `${m.nickname.slice(0,11)} L${m.level} ${m.hp}/${m.maxHp}`, 10, y, sel ? '#F8E888' : '#F8F8F0');
    });
  },

  renderBox() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#F8F8F0');
    this.drawText(`BOX (${this.state.box.length}) A:ToParty`, 12, 12, '#F8E888');
    if (!this.state.box.length) this.drawText('Box is empty!', 20, 40, '#A8DADC');
    this.state.box.slice(0, 7).forEach((m, i) => {
      this.drawText((i === this.boxCursor ? '>' : ' ') + `${m.nickname.slice(0,14)} L${m.level}`, 12, 30 + i * 15, i === this.boxCursor ? '#F8E888' : '#F8F8F0');
    });
  },

  renderBag() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#F8F8F0');
    this.drawText(`BAG (${this.state.gold}G) A:Use`, 12, 12, '#F8E888');
    const keys = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0);
    const start = Math.max(0, this.bagCursor - 4);
    keys.slice(start, start + 7).forEach((k, idx) => {
      const realIdx = start + idx;
      this.drawText((realIdx === this.bagCursor ? '>' : ' ') + `${ITEMS[k].name.slice(0,18)} x${this.state.bag[k]}`, 12, 30 + idx * 14, realIdx === this.bagCursor ? '#F8E888' : '#F8F8F0');
    });
  },

  renderShop() {
    const shop = this.getCurrentShop();
    this.drawBox(6, 6, 228, 148, '#141C2C', '#60C8F8');
    this.drawText(`MART (${this.state.gold}G) A:Buy`, 12, 12, '#F8E888');
    const start = Math.max(0, this.shopCursor - 4);
    shop.stock.slice(start, start + 7).forEach((id, idx) => {
      const realIdx = start + idx;
      const it = ITEMS[id];
      const sel = realIdx === this.shopCursor;
      this.drawText((sel ? '>' : ' ') + `${it.name.slice(0,17)} ${it.price}G`, 12, 30 + idx * 14, sel ? '#F8E888' : '#F8F8F0');
    });
    const cur = ITEMS[shop.stock[this.shopCursor]];
    if (cur) this.drawText(cur.desc.slice(0, 27), 12, 138, '#A8DADC');
  },

  renderLearnMove() {
    if (!this.pendingLearn) return;
    const { mon, moveId } = this.pendingLearn;
    const newMv = MOVES[moveId];
    this.drawBox(8, 8, 224, 144, '#141C2C', '#F0C040');
    this.drawText(`Teach ${newMv.name}?`, 16, 16, '#F8E888');
    this.drawText('Replace which move:', 16, 30, '#A8DADC');
    mon.moves.forEach((ms, i) => {
      const mv = MOVES[ms.id];
      this.drawText((this.learnCursor === i ? '> ' : '  ') + mv.name, 16, 50 + i * 15, this.learnCursor === i ? '#F8E888' : '#F8F8F0');
    });
    this.drawText((this.learnCursor === 4 ? '> ' : '  ') + 'Cancel / Skip', 16, 114, this.learnCursor === 4 ? '#F8E888' : '#E63946');
  },

  renderCredits() {
    this.drawBox(0, 0, 240, 160, '#101424', '#F0C040');
    const lines = [
      'bEATsts',
      'CONSCIOUSNODE SOFTWORKS',
      'MIT License',
      '',
      'GRAND CHEF-TAMER:',
      (this.state && this.state.name) || 'Brie',
      '',
      'CHAMPION PARTY:',
      ...(this.state ? this.state.party.map(m => `${m.nickname} L${m.level}`) : []),
      '',
      'Thank you for playing!',
      'Press A or B to continue'
    ];
    lines.forEach((l, i) => {
      const y = 160 - this.creditsScroll + i * 16;
      if (y > -16 && y < 164) this.drawText(l, 20, y, i < 3 ? '#F8E888' : '#F8F8F0', i === 0);
    });
  }
};

window.BEATS_API = {
  Game, TYPES, TYPE_CHART, getTypeEffectiveness, FLAVOR_COMBOS, MOVES,
  BEATSTS, BEATSTS_BY_ID, TILES_8X8, TILE_PALETTE, CHAR_SPRITES, ITEMS, REGIONAL_SHOPS, calcPlatingChance,
  REGIONS, MAPS, SOLID_TILES, TRAINERS, QUESTS, SECRETS, EXTRA_DIALOGUE_BANK,
  AUDIO_CHANNELS, MUSIC_TRACKS, SFX_DEFS, renderTrackOffline, renderSfxOffline, AudioEngine,
  FONT_SANS_HEX, FONT_SERIF_HEX, FONT_SANS_BYTES, FONT_SERIF_BYTES, ASCII_FALLBACK_MAP, toAsciiFontStr, isAsciiFontCovered,
  createBeatstInstance
};
