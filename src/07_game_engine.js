// 07_game_engine.js - Complete 240x160 GBA Game Engine, Battle, Plating, Saves, UI & Credits

const SAVE_KEY_PREFIX = 'beatsts_save_v1_slot_';

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
  const moves = sp.learnset.slice(0, 4).map(mid => {
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
  screen: 'TITLE', // TITLE, SLOTS, STARTER, OVERWORLD, DIALOG, BATTLE, MENU, DEX, PARTY, BOX, BAG, SHOP, OPTIONS, CONTROLS, CREDITS
  activeSlot: 0,
  state: null,
  rng: mulberry32(1337),
  cursor: 0,
  subCursor: 0,
  menuCursor: 0,
  dexCursor: 0,
  dexScroll: 0,
  partyCursor: 0,
  boxCursor: 0,
  bagCursor: 0,
  shopCursor: 0,
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
  options: { textSpeed: 2, volume: 50 }, // textSpeed 1=Slow, 2=Normal, 3=Fast
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

    if (this.screen === 'OVERWORLD') {
      if (btn === 'START') {
        AudioEngine.playSfx('menu_select');
        this.screen = 'MENU';
        this.menuCursor = 0;
      } else if (btn === 'SELECT') {
        // Toggle Day / Night cleanly so players can also hunt night-only bEATsts!
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
        // Swap selected with lead slot 0
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
        if (item && (item.kind === 'heal' || item.kind === 'cure')) {
          const lead = this.state.party[0];
          if (lead && lead.hp > 0) {
            if (item.healHp) lead.hp = Math.min(lead.maxHp, lead.hp + item.healHp);
            if (item.kind === 'cure' || item.id === 'grand_feast') lead.status = null;
            this.state.bag[k]--;
            AudioEngine.playSfx('heal');
          }
        }
      } else if (btn === 'B') { AudioEngine.playSfx('menu_back'); this.screen = 'MENU'; }
      return;
    }

    if (this.screen === 'SHOP') {
      if (btn === 'UP') { this.shopCursor = (this.shopCursor + SHOP_STOCK.length - 1) % SHOP_STOCK.length; AudioEngine.playSfx('menu_move'); }
      else if (btn === 'DOWN') { this.shopCursor = (this.shopCursor + 1) % SHOP_STOCK.length; AudioEngine.playSfx('menu_move'); }
      else if (btn === 'A') {
        const id = SHOP_STOCK[this.shopCursor];
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

  tryMove(dir) {
    if (!this.state) return;
    this.state.dir = dir;
    const dx = dir === 'left' ? -1 : dir === 'right' ? 1 : 0;
    const dy = dir === 'up' ? -1 : dir === 'down' ? 1 : 0;
    const nx = this.state.x + dx;
    const ny = this.state.y + dy;
    const map = MAPS[this.state.mapId];
    if (!map) return;

    // Check portal
    const portal = (map.portals || []).find(p => p.x === nx && p.y === ny);
    if (portal) {
      if (portal.reqSeals && this.state.seals.length < portal.reqSeals) {
        this.showDialog(`This path requires ${portal.reqSeals} Kitchen Seals! You have ${this.state.seals.length}.`);
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

    // Wild encounter check in Tall Herb Grass (tile === 1)
    if (tile === 1 && map.wildPool && map.wildPool.length > 0) {
      if (this.rng() < 0.16) {
        const pool = map.wildPool.filter(e => !BEATSTS_BY_ID[e[0]].nightOnly || this.state.isNight);
        const pick = pool[Math.floor(this.rng() * pool.length)] || map.wildPool[0];
        const lv = pick[1] + Math.floor(this.rng() * (pick[2] - pick[1] + 1));
        this.startWildBattle(pick[0], lv);
      }
    }
  },

  isNpcHidden(npc) {
    if (npc.itemPickup && this.state.quests[npc.itemPickup]) return true;
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
      this.showDialog([npc.dialog, 'All your bEATsts are simmering at 100% HP and PP!'], () => this.playMapMusic());
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
        this.showDialog([
          'The Secret Pantry shimmers with golden steam...',
          'A luminous aroma unites Sandwich, Dumpling, Noodle, and Soup!',
          'The mythical #151 Consommyth emerges!'
        ], () => this.startWildBattle(151, 55));
      } else {
        this.showDialog('A locked golden pantry door. An inscription reads: "Only a Champion at Night bearing all 4 Food Families and a Royal Banquet Setting may enter."');
      }
      return;
    }
    if (npc.itemPickup) {
      this.state.quests[npc.itemPickup] = true;
      if (npc.itemPickup === 'q1_butter_item') this.state.bag.ceramic_plate = (this.state.bag.ceramic_plate || 0) + 3;
      if (npc.itemPickup === 'q2_lid_item') { this.state.bag.bento_set = (this.state.bag.bento_set || 0) + 2; this.state.gold += 300; }
      if (npc.itemPickup === 'q3_chopsticks_item') this.state.gold += 500;
      if (npc.itemPickup === 'q4_truffle_item') this.state.bag.royal_banquet = (this.state.bag.royal_banquet || 0) + 1;
      AudioEngine.playSfx('level_up');
      this.showDialog(npc.dialog);
      return;
    }
    if (npc.trainer) {
      const tr = TRAINERS[npc.trainer];
      if (this.state.defeatedTrainers.includes(tr.id)) {
        this.showDialog(`${tr.name}: ${tr.win}`);
      } else {
        this.showDialog([`${tr.name}: ${tr.intro}`], () => this.startTrainerBattle(tr));
      }
      return;
    }
    this.showDialog(`${npc.name}: ${npc.dialog}`);
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
      isWild: true,
      trainer: null,
      foeParty: [foe],
      foeIdx: 0,
      playerIdx: activeIdx,
      temp: 0, // -2..+2
      usedFavTreat: false,
      phase: 'MAIN', // MAIN, FIGHT, PLATE, BAG, PARTY, LOG
      cursor: 0,
      log: `A wild ${foe.nickname} (Lv.${foe.level}) popped out of the pantry!`
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
      isWild: false,
      trainer,
      foeParty,
      foeIdx: 0,
      playerIdx: activeIdx,
      temp: 0,
      usedFavTreat: false,
      phase: 'MAIN',
      cursor: 0,
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
        if (b.pendingEnd) {
          this.finishBattle(b.pendingEnd);
        } else {
          b.phase = 'MAIN';
          b.cursor = 0;
        }
      }
      return;
    }

    if (b.phase === 'MAIN') {
      // 0:FIGHT, 1:PLATE, 2:BAG, 3:PARTY/RUN
      if (btn === 'UP' || btn === 'DOWN' || btn === 'LEFT' || btn === 'RIGHT') {
        AudioEngine.playSfx('menu_move');
        if (btn === 'LEFT' || btn === 'RIGHT') b.cursor ^= 1;
        else b.cursor ^= 2;
      } else if (btn === 'A') {
        AudioEngine.playSfx('menu_select');
        if (b.cursor === 0) { b.phase = 'FIGHT'; b.cursor = 0; }
        else if (b.cursor === 1) {
          if (!b.isWild) {
            b.log = 'You cannot plate another chef’s bEATst!';
            b.phase = 'LOG';
          } else { b.phase = 'PLATE'; b.cursor = 0; }
        }
        else if (b.cursor === 2) { b.phase = 'BAG'; b.cursor = 0; }
        else {
          if (b.isWild) {
            b.log = 'Got away safely!';
            b.pendingEnd = 'RUN';
            b.phase = 'LOG';
          } else {
            b.phase = 'PARTY';
            b.cursor = 0;
          }
        }
      }
      return;
    }

    if (b.phase === 'FIGHT') {
      const mon = this.state.party[b.playerIdx];
      if (btn === 'UP' || btn === 'DOWN' || btn === 'LEFT' || btn === 'RIGHT') {
        AudioEngine.playSfx('menu_move');
        b.cursor = (b.cursor + (btn === 'DOWN' || btn === 'RIGHT' ? 1 : mon.moves.length - 1)) % mon.moves.length;
      } else if (btn === 'B') {
        AudioEngine.playSfx('menu_back');
        b.phase = 'MAIN'; b.cursor = 0;
      } else if (btn === 'A') {
        const mvSlot = mon.moves[b.cursor];
        if (mvSlot && mvSlot.pp > 0) {
          mvSlot.pp--;
          this.executeBattleTurn(mvSlot.id);
        }
      }
      return;
    }

    if (b.phase === 'PLATE') {
      const plates = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0 && (ITEMS[k].kind === 'plate' || ITEMS[k].kind === 'treat'));
      if (btn === 'B' || plates.length === 0) {
        AudioEngine.playSfx('menu_back');
        b.phase = 'MAIN'; b.cursor = 0;
      } else if (btn === 'UP' || btn === 'DOWN') {
        AudioEngine.playSfx('menu_move');
        b.cursor = (b.cursor + (btn === 'DOWN' ? 1 : plates.length - 1)) % plates.length;
      } else if (btn === 'A') {
        const itemId = plates[b.cursor];
        this.usePlatingItem(itemId);
      }
      return;
    }

    if (b.phase === 'BAG') {
      const heals = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0 && ['heal','cure','revive'].includes(ITEMS[k].kind));
      if (btn === 'B' || heals.length === 0) {
        AudioEngine.playSfx('menu_back');
        b.phase = 'MAIN'; b.cursor = 0;
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
        } else if (it.kind === 'cure') {
          mon.status = null;
        } else if (it.kind === 'revive') {
          const fainted = this.state.party.find(m => m.hp <= 0);
          if (fainted) fainted.hp = Math.floor(fainted.maxHp * 0.5);
        }
        this.state.bag[itemId]--;
        AudioEngine.playSfx('heal');
        const foe = b.foeParty[b.foeIdx];
        const foeMsg = this.doFoeAttack(foe, mon);
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
          const foe = b.foeParty[b.foeIdx];
          const foeMsg = this.doFoeAttack(foe, target);
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
    // Kitchen Temp modifier
    let tempMult = 1.0;
    if (battleTemp >= 2) {
      if (['Spicy','Fried','Toasted'].includes(move.type)) tempMult = 1.25;
      if (['Chilled','Raw'].includes(move.type)) tempMult = 0.8;
    } else if (battleTemp <= -2) {
      if (['Chilled','Raw','Pickled'].includes(move.type)) tempMult = 1.25;
      if (['Spicy','Brothy'].includes(move.type)) tempMult = 0.8;
    }
    // Flavor Combo modifier
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
      b.foeIdx++;
      if (b.foeIdx < b.foeParty.length) {
        const nextFoe = b.foeParty[b.foeIdx];
        msg += `${b.trainer.name} sent out ${nextFoe.nickname}!`;
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
      if (sp.evo && mon.level >= sp.evo.level) {
        const nextSp = BEATSTS_BY_ID[sp.evo.to];
        if (nextSp) {
          mon.speciesId = nextSp.id;
          mon.nickname = nextSp.name;
          mon.moves = nextSp.learnset.slice(0, 4).map(mid => ({ id: mid, pp: MOVES[mid].pp, maxPp: MOVES[mid].pp }));
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
      b.log = `${sp.name} only sits down at Night!`;
      b.phase = 'LOG';
      return;
    }
    if (chance === 0 && sp.minTier && it.tier < sp.minTier) {
      b.log = `${sp.name} insists on a Tier ${sp.minTier}+ place setting!`;
      b.phase = 'LOG';
      return;
    }

    if (this.rng() < chance) {
      AudioEngine.playSfx('plating_success');
      this.markCaught(sp.id);
      if (this.state.party.length < 6) {
        this.state.party.push(foe);
        b.log = `${foe.nickname} sat down at your ${it.name} and joined your party!`;
      } else {
        this.state.box.push(foe);
        b.log = `${foe.nickname} sat down at your ${it.name} and hopped into your Storage Box!`;
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
        if (tr.seal && !this.state.seals.includes(tr.seal)) {
          this.state.seals.push(tr.seal);
        }
      }
      AudioEngine.playMusic('victory');
      if (tr.id === 'champion_aurelia') {
        this.state.championBeaten = true;
        this.saveToSlot(this.activeSlot);
        this.showDialog([tr.win, 'Welcome to the Hall of Flavor!'], () => {
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
    if (this.state && ['OVERWORLD','BATTLE','MENU','DEX','PARTY','BOX','BAG','SHOP'].includes(this.screen)) {
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

  // === GBA 240x160 PIXEL RENDERER ===
  drawSprite24(grid, palette, dx, dy, scale = 1) {
    const ctx = this.ctx;
    for (let y = 0; y < 24; y++) {
      for (let x = 0; x < 24; x++) {
        const cIdx = grid[y * 24 + x];
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

  drawText(txt, x, y, color = '#F8F8F0', size = 8) {
    const ctx = this.ctx;
    ctx.fillStyle = color;
    ctx.font = `bold ${size}px monospace`;
    ctx.textBaseline = 'top';
    ctx.fillText(String(txt), x, y);
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
  },

  renderTitle() {
    this.drawBox(4, 4, 232, 152, '#1A1E34', '#F0C040');
    this.drawText('bEATsts', 72, 18, '#F8E888', 20);
    this.drawText('ConsciousNode SoftWorks', 52, 42, '#A8DADC', 8);
    // Show 4 mascot sprites on title
    this.drawSprite24(BEATSTS_BY_ID[1].front, BEATSTS_BY_ID[1].palette, 26, 60, 1);
    this.drawSprite24(BEATSTS_BY_ID[39].front, BEATSTS_BY_ID[39].palette, 78, 60, 1);
    this.drawSprite24(BEATSTS_BY_ID[77].front, BEATSTS_BY_ID[77].palette, 130, 60, 1);
    this.drawSprite24(BEATSTS_BY_ID[115].front, BEATSTS_BY_ID[115].palette, 182, 60, 1);

    const opts = ['PLAY / SAVE SLOTS', 'OPTIONS', 'CONTROLS'];
    opts.forEach((o, i) => {
      const sel = i === this.cursor;
      this.drawText((sel ? '> ' : '  ') + o, 64, 98 + i * 14, sel ? '#F8E888' : '#F8F8F0', 8);
    });
    this.drawText('Press Z / Enter / A', 66, 142, '#98D830', 8);
  },

  renderSlots() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#F8F8F0');
    this.drawText('SELECT SAVE SLOT (A:Play / B:Back)', 16, 14, '#F8E888', 8);
    for (let i = 0; i < 3; i++) {
      const sum = this.getSlotSummary(i);
      const y = 34 + i * 36;
      const sel = i === this.cursor;
      this.drawBox(14, y, 212, 30, sel ? '#283854' : '#182234', sel ? '#F8E888' : '#708090');
      if (sum) {
        const mins = Math.floor(sum.playTimeSec / 60);
        this.drawText(`SLOT ${i+1}: ${sum.name}`, 22, y + 5, '#F8F8F0', 8);
        this.drawText(`Seals:${sum.badges}/8  Dex:${sum.caught}  ${mins}m`, 22, y + 17, '#A8DADC', 8);
      } else {
        this.drawText(`SLOT ${i+1}: [ NEW ADVENTURE ]`, 22, y + 10, '#98D830', 8);
      }
    }
  },

  renderStarter() {
    const starters = [1, 39, 77, 115];
    this.drawBox(6, 6, 228, 148, '#182030', '#F0C040');
    this.drawText('CHOOSE YOUR FIRST bEATst!', 36, 14, '#F8E888', 8);
    starters.forEach((id, i) => {
      const sp = BEATSTS_BY_ID[id];
      const x = 16 + i * 54;
      const sel = i === this.starterIdx;
      this.drawBox(x, 32, 48, 64, sel ? '#304060' : '#1A2438', sel ? '#F8E888' : '#506070');
      this.drawSprite24(sp.front, sp.palette, x + 12, 40, 1);
      this.drawText(sp.family.slice(0,5), x + 6, 72, '#A8DADC', 8);
    });
    const cur = BEATSTS_BY_ID[starters[this.starterIdx]];
    this.drawText(`${cur.name} (${cur.types.join('/')})`, 16, 106, '#F8F8F0', 8);
    this.drawText(cur.dex.slice(0, 36), 16, 118, '#C0C8D0', 7);
    this.drawText('LEFT/RIGHT: Pick  A: Start!', 36, 138, '#98D830', 8);
  },

  renderOptions() {
    this.drawBox(12, 12, 216, 136, '#141C2C', '#F8F8F0');
    this.drawText('OPTIONS', 92, 22, '#F8E888', 10);
    const spdNames = ['', 'Slow', 'Normal', 'Fast'];
    const rows = [
      `Text Speed : < ${spdNames[this.options.textSpeed]} >`,
      `Volume     : < ${this.options.volume}% >`,
      'Back'
    ];
    rows.forEach((r, i) => {
      this.drawText((i === this.cursor ? '> ' : '  ') + r, 32, 50 + i * 18, i === this.cursor ? '#F8E888' : '#F8F8F0', 8);
    });
  },

  renderControls() {
    this.drawBox(8, 8, 224, 144, '#141C2C', '#F8F8F0');
    this.drawText('CONTROLS', 88, 16, '#F8E888', 10);
    const lines = [
      'Move      : Arrow Keys / WASD / D-Pad',
      'Confirm/A : Z / Enter / Space',
      'Cancel/B  : X / Esc / Backspace',
      'Menu/Start: M  |  Day/Night(Sel): N',
      'Touch     : On-screen GBA Pad'
    ];
    lines.forEach((l, i) => this.drawText(l, 16, 38 + i * 16, '#F8F8F0', 7));
    this.drawText('Press A or B to return', 52, 132, '#98D830', 8);
  },

  renderOverworld() {
    const map = MAPS[this.state.mapId];
    if (!map) return;
    // Top 16px GBA HUD bar
    this.ctx.fillStyle = '#182030';
    this.ctx.fillRect(0, 0, 240, 16);
    this.drawText(`${map.name}`, 4, 4, '#F8E888', 8);
    this.drawText(`${this.state.isNight ? 'NIGHT' : 'DAY'} S:${this.state.seals.length}/8 ${this.state.gold}G`, 112, 4, '#A8DADC', 7);

    // 30x18 8x8 tiles starting at y=16
    for (let y = 0; y < 18; y++) {
      for (let x = 0; x < 30; x++) {
        this.drawTile8(map.grid[y * 30 + x], x * 8, 16 + y * 8);
      }
    }

    // Night tint overlay
    if (this.state.isNight) {
      this.ctx.fillStyle = 'rgba(16, 24, 56, 0.35)';
      this.ctx.fillRect(0, 16, 240, 144);
    }

    // NPCs (8x8/16x16 aligned on 8x8 grid)
    for (const npc of (map.npcs || [])) {
      if (this.isNpcHidden(npc)) continue;
      this.ctx.fillStyle = '#181820';
      this.ctx.fillRect(npc.x * 8, 16 + npc.y * 8, 8, 8);
      this.ctx.fillStyle = npc.color || '#F8F8F0';
      this.ctx.fillRect(npc.x * 8 + 1, 16 + npc.y * 8 + 1, 6, 6);
    }

    // Player
    const px = this.state.x * 8;
    const py = 16 + this.state.y * 8;
    this.ctx.fillStyle = '#181820';
    this.ctx.fillRect(px, py, 8, 8);
    this.ctx.fillStyle = '#E63946';
    this.ctx.fillRect(px + 1, py + 1, 6, 3);
    this.ctx.fillStyle = '#F8D8B0';
    this.ctx.fillRect(px + 2, py + 4, 4, 3);
  },

  renderDialog() {
    this.drawBox(4, 112, 232, 44, '#141C2C', '#F8F8F0');
    const txt = this.dialogQueue[0] || '';
    const words = txt.split(' ');
    let line = '', y = 118;
    for (const w of words) {
      if ((line + w).length > 36) {
        this.drawText(line, 10, y, '#F8F8F0', 8);
        line = w + ' ';
        y += 10;
      } else line += w + ' ';
    }
    if (line) this.drawText(line, 10, y, '#F8F8F0', 8);
    this.drawText('v', 226, 144, '#F8E888', 8);
  },

  renderBattle() {
    const b = this.battle;
    if (!b) return;
    const player = this.state.party[b.playerIdx];
    const foe = b.foeParty[b.foeIdx];
    const pSp = BEATSTS_BY_ID[player.speciesId];
    const fSp = BEATSTS_BY_ID[foe.speciesId];

    // Arena background
    this.ctx.fillStyle = '#243448';
    this.ctx.fillRect(0, 0, 240, 108);
    this.ctx.fillStyle = '#385068';
    this.ctx.fillRect(0, 76, 240, 32);

    // Kitchen Temp indicator (Top center)
    const tempLabels = { '-2':'CHILLED -2', '-1':'COOL -1', '0':'ROOM 0', '1':'WARM +1', '2':'SEARING +2' };
    const tempColors = { '-2':'#4CC9F0', '-1':'#A8DADC', '0':'#F8F8F0', '1':'#E8A850', '2':'#E63946' };
    this.drawBox(76, 2, 88, 12, '#101824', tempColors[b.temp]);
    this.drawText(`TEMP: ${tempLabels[b.temp]}`, 80, 4, tempColors[b.temp], 7);

    // Foe HUD & Sprite (top right)
    this.drawBox(6, 16, 106, 28, '#182030', '#F8F8F0');
    this.drawText(`${foe.nickname} Lv${foe.level}`, 10, 19, '#F8F8F0', 7);
    this.ctx.fillStyle = '#404858'; this.ctx.fillRect(10, 30, 94, 5);
    this.ctx.fillStyle = foe.hp > foe.maxHp * 0.3 ? '#52B788' : '#E63946';
    this.ctx.fillRect(10, 30, Math.floor(94 * (foe.hp / foe.maxHp)), 5);
    if (foe.status) this.drawText(foe.status, 10, 36, '#F8E888', 6);
    this.drawSprite24(fSp.front, fSp.palette, 164, 20, 2);

    // Player HUD & Back Sprite (bottom left)
    this.drawSprite24(pSp.back, pSp.palette, 26, 56, 2);
    this.drawBox(124, 68, 110, 34, '#182030', '#F8F8F0');
    this.drawText(`${player.nickname} Lv${player.level}`, 128, 71, '#F8F8F0', 7);
    this.ctx.fillStyle = '#404858'; this.ctx.fillRect(128, 82, 100, 5);
    this.ctx.fillStyle = player.hp > player.maxHp * 0.3 ? '#52B788' : '#E63946';
    this.ctx.fillRect(128, 82, Math.floor(100 * (player.hp / player.maxHp)), 5);
    this.drawText(`HP ${player.hp}/${player.maxHp}`, 128, 90, '#A8DADC', 7);

    // Move animation flash
    if (this.animTimer > 0) {
      this.ctx.fillStyle = this.animType === 'flame' ? 'rgba(230,57,70,0.45)' :
        this.animType === 'chill' ? 'rgba(76,201,240,0.45)' : 'rgba(248,232,136,0.45)';
      this.ctx.fillRect(160, 18, 52, 52);
    }

    // Bottom Battle Panel (y=108..160)
    this.drawBox(2, 108, 236, 50, '#141C2C', '#F8F8F0');
    if (b.phase === 'LOG') {
      const words = b.log.split(' ');
      let line = '', y = 114;
      for (const w of words) {
        if ((line + w).length > 36) { this.drawText(line, 8, y, '#F8F8F0', 7); line = w + ' '; y += 10; }
        else line += w + ' ';
      }
      if (line) this.drawText(line, 8, y, '#F8F8F0', 7);
    } else if (b.phase === 'MAIN') {
      this.drawText(b.log.slice(0, 34), 8, 112, '#A8DADC', 7);
      const opts = ['FIGHT', 'PLATE', 'BAG', b.isWild ? 'RUN' : 'PARTY'];
      opts.forEach((o, i) => {
        const x = 16 + (i % 2) * 110;
        const y = 128 + Math.floor(i / 2) * 14;
        this.drawText((b.cursor === i ? '> ' : '  ') + o, x, y, b.cursor === i ? '#F8E888' : '#F8F8F0', 8);
      });
    } else if (b.phase === 'FIGHT') {
      player.moves.forEach((ms, i) => {
        const mv = MOVES[ms.id];
        const x = 8 + (i % 2) * 116;
        const y = 114 + Math.floor(i / 2) * 20;
        this.drawText((b.cursor === i ? '>' : ' ') + mv.name.slice(0,13), x, y, b.cursor === i ? '#F8E888' : '#F8F8F0', 7);
        this.drawText(` ${mv.type.slice(0,5)} ${ms.pp}/${ms.maxPp}`, x + 6, y + 9, '#A8DADC', 6);
      });
    } else if (b.phase === 'PLATE') {
      const plates = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0 && (ITEMS[k].kind === 'plate' || ITEMS[k].kind === 'treat'));
      if (!plates.length) this.drawText('No plates/treats left! (B:Back)', 10, 120, '#E63946', 8);
      plates.slice(0, 4).forEach((k, i) => {
        const it = ITEMS[k];
        const pct = it.kind === 'plate' ? Math.round(calcPlatingChance(fSp, foe.hp, foe.maxHp, foe.status, b.usedFavTreat, this.state.isNight, it) * 100) + '%' : 'TREAT';
        this.drawText((b.cursor === i ? '> ' : '  ') + `${it.name} x${this.state.bag[k]} (${pct})`, 8, 113 + i * 11, b.cursor === i ? '#F8E888' : '#F8F8F0', 7);
      });
    } else if (b.phase === 'BAG') {
      const heals = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0 && ['heal','cure','revive'].includes(ITEMS[k].kind));
      if (!heals.length) this.drawText('No healing items! (B:Back)', 10, 120, '#E63946', 8);
      heals.slice(0, 4).forEach((k, i) => {
        this.drawText((b.cursor === i ? '> ' : '  ') + `${ITEMS[k].name} x${this.state.bag[k]}`, 8, 113 + i * 11, b.cursor === i ? '#F8E888' : '#F8F8F0', 7);
      });
    } else if (b.phase === 'PARTY') {
      this.state.party.slice(0, 4).forEach((m, i) => {
        this.drawText((b.cursor === i ? '> ' : '  ') + `${m.nickname} ${m.hp}/${m.maxHp}`, 8, 113 + i * 11, b.cursor === i ? '#F8E888' : '#F8F8F0', 7);
      });
    }
  },

  renderMenu() {
    this.drawBox(140, 16, 96, 138, '#141C2C', '#F8F8F0');
    const items = ['PARTY','bEATdex','BOX','BAG','SAVE','OPTIONS','CONTROLS','CLOSE'];
    items.forEach((it, i) => {
      this.drawText((this.menuCursor === i ? '> ' : '  ') + it, 146, 24 + i * 15, this.menuCursor === i ? '#F8E888' : '#F8F8F0', 8);
    });
  },

  renderDex() {
    this.drawBox(4, 4, 232, 152, '#141C2C', '#F0C040');
    const maxEntries = this.state.dexCaught.includes(151) || this.state.dexSeen.includes(151) ? 151 : 150;
    this.drawText(`bEATdex  Seen:${this.state.dexSeen.length} Caught:${this.state.dexCaught.length}/${maxEntries}`, 10, 10, '#F8E888', 8);
    for (let i = 0; i < 7; i++) {
      const idx = this.dexScroll + i;
      if (idx >= maxEntries) break;
      const sp = BEATSTS[idx];
      const seen = this.state.dexSeen.includes(sp.id);
      const caught = this.state.dexCaught.includes(sp.id);
      const sel = idx === this.dexCursor;
      const label = `#${String(sp.id).padStart(3,'0')} ${seen ? sp.name : '???'} ${caught ? '*' : ''}`;
      this.drawText((sel ? '>' : ' ') + label, 10, 26 + i * 14, sel ? '#F8E888' : '#F8F8F0', 7);
    }
    const curSp = BEATSTS[this.dexCursor];
    if (curSp && this.state.dexSeen.includes(curSp.id)) {
      this.drawSprite24(curSp.front, curSp.palette, 164, 26, 2);
      this.drawText(curSp.types.join('/'), 146, 78, '#A8DADC', 7);
      this.drawText(curSp.dex.slice(0, 34), 10, 130, '#C0C8D0', 7);
      this.drawText(curSp.dex.slice(34, 68), 10, 140, '#C0C8D0', 7);
    } else {
      this.drawText('Not yet encountered!', 130, 56, '#708090', 7);
    }
  },

  renderParty() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#F8F8F0');
    this.drawText('PARTY (A:Make Lead  B:Back)', 12, 12, '#F8E888', 8);
    this.state.party.forEach((m, i) => {
      const y = 28 + i * 20;
      const sel = i === this.partyCursor;
      this.drawText((sel ? '> ' : '  ') + `${m.nickname} Lv${m.level} HP:${m.hp}/${m.maxHp}`, 12, y, sel ? '#F8E888' : '#F8F8F0', 8);
    });
  },

  renderBox() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#F8F8F0');
    this.drawText(`STORAGE BOX (${this.state.box.length}) A:Move to Party`, 12, 12, '#F8E888', 7);
    if (!this.state.box.length) this.drawText('Box is empty!', 20, 40, '#A8DADC', 8);
    this.state.box.slice(0, 7).forEach((m, i) => {
      this.drawText((i === this.boxCursor ? '> ' : '  ') + `${m.nickname} Lv${m.level}`, 14, 30 + i * 15, i === this.boxCursor ? '#F8E888' : '#F8F8F0', 8);
    });
  },

  renderBag() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#F8F8F0');
    this.drawText(`PANTRY BAG (${this.state.gold}G) A:Use`, 12, 12, '#F8E888', 8);
    const keys = Object.keys(this.state.bag).filter(k => this.state.bag[k] > 0);
    keys.slice(0, 8).forEach((k, i) => {
      this.drawText((i === this.bagCursor ? '> ' : '  ') + `${ITEMS[k].name} x${this.state.bag[k]}`, 14, 30 + i * 14, i === this.bagCursor ? '#F8E888' : '#F8F8F0', 7);
    });
  },

  renderShop() {
    this.drawBox(6, 6, 228, 148, '#141C2C', '#60C8F8');
    this.drawText(`PANTRY MART (${this.state.gold}G) A:Buy B:Exit`, 12, 12, '#F8E888', 7);
    const start = Math.max(0, this.shopCursor - 4);
    SHOP_STOCK.slice(start, start + 7).forEach((id, idx) => {
      const realIdx = start + idx;
      const it = ITEMS[id];
      const sel = realIdx === this.shopCursor;
      this.drawText((sel ? '> ' : '  ') + `${it.name} - ${it.price}G`, 14, 30 + idx * 14, sel ? '#F8E888' : '#F8F8F0', 7);
    });
    const cur = ITEMS[SHOP_STOCK[this.shopCursor]];
    if (cur) this.drawText(cur.desc.slice(0, 38), 12, 138, '#A8DADC', 6);
  },

  renderCredits() {
    this.drawBox(0, 0, 240, 160, '#101424', '#F0C040');
    const lines = [
      'bEATsts',
      'CONSCIOUSNODE SOFTWORKS',
      'MIT License',
      '',
      'NEW GRAND CHEF-TAMER:',
      (this.state && this.state.name) || 'Brie',
      '',
      'CHAMPION PARTY:',
      ...(this.state ? this.state.party.map(m => `${m.nickname} (Lv.${m.level})`) : []),
      '',
      'Thank you for cooking',
      'and befriending Pantrylia!',
      '',
      'Press A or B to continue'
    ];
    lines.forEach((l, i) => {
      const y = 160 - this.creditsScroll + i * 14;
      if (y > -12 && y < 164) this.drawText(l, 24, y, i < 3 ? '#F8E888' : '#F8F8F0', 8);
    });
  }
};

// Expose clean API for Export/Import buttons and automated tests
window.BEATS_API = {
  Game, TYPES, TYPE_CHART, getTypeEffectiveness, FLAVOR_COMBOS, MOVES,
  BEATSTS, BEATSTS_BY_ID, TILES_8X8, TILE_PALETTE, ITEMS, SHOP_STOCK, calcPlatingChance,
  REGIONS, MAPS, TRAINERS, AUDIO_CHANNELS, MUSIC_TRACKS, SFX_DEFS,
  renderTrackOffline, renderSfxOffline, AudioEngine, createBeatstInstance
};
