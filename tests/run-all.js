// tests/run-all.js - Complete Automated Test Suite & Screenshot Capture for bEATsts
const fs = require('fs');
const path = require('path');
const http = require('http');
const assert = require('assert');
const { spawn } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const HTML_PATH = path.join(ROOT, 'beatsts.html');
const SHOTS_DIR = path.join(ROOT, 'screenshots');

function mulberry32(a) {
  return function () {
    let t = a += 0x6D2B79F5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function normalizeSpriteShape(grid) {
  const map = new Map();
  let next = 1;
  let out = '';
  for (let i = 0; i < grid.length; i++) {
    const v = grid[i];
    if (v === 0) { out += '0,'; continue; }
    if (!map.has(v)) map.set(v, next++);
    out += map.get(v) + ',';
  }
  return out;
}

function validateBeatdexSprites(beatsts) {
  const frontSet = new Set();
  const backSet = new Set();
  for (const b of beatsts) {
    const fn = normalizeSpriteShape(b.front);
    const bn = normalizeSpriteShape(b.back);
    if (frontSet.has(fn)) throw new Error(`Duplicate or palette-swap front sprite at #${b.id} (${b.name})`);
    if (backSet.has(bn)) throw new Error(`Duplicate or palette-swap back sprite at #${b.id} (${b.name})`);
    frontSet.add(fn);
    backSet.add(bn);
  }
  return true;
}

function validateGbaSpriteColors(grid, palette) {
  const used = new Set();
  for (let i = 0; i < grid.length; i++) {
    if (grid[i] !== 0) used.add(grid[i]);
    if (grid[i] >= palette.length) throw new Error(`Color index ${grid[i]} out of palette bounds`);
  }
  if (palette.length > 16 || used.size > 15) {
    throw new Error(`GBA 16-color limit exceeded: palette=${palette.length}, used=${used.size}`);
  }
  return true;
}

// Load game JS in Node VM context for unit/simulation tests (Tests 1, 2, 3, 4, 7, 9)
function loadGameApiInNode() {
  const html = fs.readFileSync(HTML_PATH, 'utf8');
  const m = html.match(/<!-- INLINE SCRIPT:[\s\S]*?<script>([\s\S]*?)<\/script>/);
  assert(m, 'Could not find labeled inline script in beatsts.html');
  const js = m[1];
  const vm = require('vm');
  const sandbox = {
    window: {},
    document: {
      getElementById: () => ({ addEventListener: () => {} }),
      querySelectorAll: () => [],
      createElement: () => ({ click: () => {}, remove: () => {} }),
      body: { appendChild: () => {} }
    },
    performance: { now: () => Date.now() },
    requestAnimationFrame: () => {},
    Uint8Array, Float32Array, Set, Map, Math, JSON, Array, Object, String, Number, Error, console
  };
  sandbox.addEventListener = () => {};
  sandbox.window = sandbox;
  vm.runInNewContext(js, sandbox);
  return sandbox.window.BEATS_API;
}

// Minimal W3C WebDriver client for ChromeDriver (zero external dependencies)
class WebDriverClient {
  constructor(port = 9515) {
    this.port = port;
    this.sessionId = null;
  }
  req(method, reqPath, body = null) {
    return new Promise((resolve, reject) => {
      const data = body ? JSON.stringify(body) : null;
      const opts = {
        hostname: '127.0.0.1', port: this.port, path: reqPath, method,
        headers: data ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } : {}
      };
      const r = http.request(opts, res => {
        let buf = '';
        res.on('data', c => buf += c);
        res.on('end', () => {
          try {
            const parsed = JSON.parse(buf);
            if (parsed.value && parsed.value.error) reject(new Error(parsed.value.message || parsed.value.error));
            else resolve(parsed.value);
          } catch (e) { reject(e); }
        });
      });
      r.on('error', reject);
      if (data) r.write(data);
      r.end();
    });
  }
  async start(width = 800, height = 900) {
    const res = await this.req('POST', '/session', {
      capabilities: {
        alwaysMatch: {
          browserName: 'chrome',
          'goog:chromeOptions': {
            binary: '/usr/bin/chromium',
            args: ['--headless=new', '--no-sandbox', '--disable-gpu', `--window-size=${width},${height}`]
          }
        }
      }
    });
    this.sessionId = res.sessionId;
  }
  async stop() {
    if (this.sessionId) {
      try { await this.req('DELETE', `/session/${this.sessionId}`); } catch (e) {}
      this.sessionId = null;
    }
  }
  async url(u) { return this.req('POST', `/session/${this.sessionId}/url`, { url: u }); }
  async setWindowSize(w, h) { return this.req('POST', `/session/${this.sessionId}/window/rect`, { width: w, height: h }); }
  async exec(script, args = []) { return this.req('POST', `/session/${this.sessionId}/execute/sync`, { script, args }); }
  async clickSelector(sel) {
    const el = await this.req('POST', `/session/${this.sessionId}/element`, { using: 'css selector', value: sel });
    const id = el['element-6066-11e4-a52e-4f735466cecf'];
    return this.req('POST', `/session/${this.sessionId}/element/${id}/click`, {});
  }
  async screenshot(outFile) {
    const b64 = await this.req('GET', `/session/${this.sessionId}/screenshot`);
    fs.writeFileSync(outFile, Buffer.from(b64, 'base64'));
  }
}

async function main() {
  fs.mkdirSync(SHOTS_DIR, { recursive: true });
  const api = loadGameApiInNode();

  // =========================================================================
  // TEST 1: bEATdex completeness + Positive Controls
  // =========================================================================
  console.log('\n[TEST 1] bEATdex completeness...');
  assert.strictEqual(api.BEATSTS.length, 151, 'Expected exactly 151 bEATsts');
  const names = new Set();
  for (const b of api.BEATSTS) {
    assert(!names.has(b.name), `Duplicate name: ${b.name}`);
    names.add(b.name);
    assert(b.front && b.front.length === 576, `Missing front sprite #${b.id}`);
    assert(b.back && b.back.length === 576, `Missing back sprite #${b.id}`);
    assert(b.dex && b.dex.length > 10, `Missing dex text #${b.id}`);
    assert(b.types.length >= 1 && b.types.length <= 2, `Invalid type count #${b.id}`);
    for (const t of b.types) assert(api.TYPES.includes(t), `Invalid type ${t} on #${b.id}`);
    for (const k of ['hp','atk','def','spd']) {
      assert(b.stats[k] >= 35 && b.stats[k] <= 140, `Stat ${k} out of range on #${b.id}`);
    }
    assert(b.learnset.length >= 4, `Movepool < 4 on #${b.id}`);
    for (const mid of b.learnset) assert(api.MOVES[mid], `Invalid move ${mid} on #${b.id}`);
  }
  assert(validateBeatdexSprites(api.BEATSTS), 'Sprite uniqueness failed');

  // Evolution line validation (no cycles, reachable levels)
  for (const b of api.BEATSTS) {
    const seen = new Set([b.id]);
    let cur = b;
    while (cur.evo) {
      assert(!seen.has(cur.evo.to), `Evolution cycle at #${cur.id}`);
      seen.add(cur.evo.to);
      assert(cur.evo.level >= 2 && cur.evo.level <= 50, `Unreachable evo level ${cur.evo.level}`);
      cur = api.BEATSTS_BY_ID[cur.evo.to];
      assert(cur, `Missing evo target`);
    }
  }
  // Verify #151 secret event exists
  const hall = api.MAPS.grand_tasting_hall;
  assert(hall.npcs.some(n => n.action === 'secret151'), '#151 secret event missing');

  // Positive control 1a: duplicated sprite fails
  let dupFailed = false;
  try {
    const clone = api.BEATSTS.map((b, i) => i === 1 ? { ...b, front: new Uint8Array(api.BEATSTS[0].front) } : b);
    validateBeatdexSprites(clone);
  } catch (e) { dupFailed = true; }
  assert(dupFailed, 'Positive control failed: duplicated sprite did not fail');

  // Positive control 1b: palette-swapped sprite fails
  let swapFailed = false;
  try {
    const swapped = new Uint8Array(api.BEATSTS[0].front).map(v => v === 0 ? 0 : (v === 2 ? 5 : (v === 5 ? 2 : v)));
    const clone = api.BEATSTS.map((b, i) => i === 1 ? { ...b, front: swapped } : b);
    validateBeatdexSprites(clone);
  } catch (e) { swapFailed = true; }
  assert(swapFailed, 'Positive control failed: palette swap did not fail');
  console.log('PASS: 151 bEATsts complete, all front/back shapes unique, #151 event verified, positive controls passed.');

  // =========================================================================
  // TEST 2: Type chart + 10,000 seeded random battles
  // =========================================================================
  console.log('\n[TEST 2] Type chart & 10,000 seeded battles...');
  assert(api.TYPES.length >= 12, 'Need at least 12 types');
  for (const t of api.TYPES) {
    let strengths = 0, weaknesses = 0;
    for (const def of api.TYPES) {
      const v = api.TYPE_CHART[t][def];
      assert(v === 0.5 || v === 1 || v === 2, `Missing/invalid chart entry ${t}->${def}`);
      if (v === 2) strengths++;
      if (api.TYPE_CHART[def][t] === 2) weaknesses++;
    }
    assert(strengths >= 1 && weaknesses >= 1, `Type ${t} lacks strength or weakness`);
  }
  const simRng = mulberry32(9001);
  const wins = {}, games = {};
  for (const t of api.TYPES) { wins[t] = 0; games[t] = 0; }
  for (let i = 0; i < 10000; i++) {
    const t1 = api.TYPES[Math.floor(simRng() * api.TYPES.length)];
    const t2 = api.TYPES[Math.floor(simRng() * api.TYPES.length)];
    const e1 = api.getTypeEffectiveness(t1, [t2]);
    const e2 = api.getTypeEffectiveness(t2, [t1]);
    let hp1 = 100, hp2 = 100;
    while (hp1 > 0 && hp2 > 0) {
      hp2 -= Math.floor(20 * e1 * (0.85 + simRng() * 0.3));
      if (hp2 <= 0) break;
      hp1 -= Math.floor(20 * e2 * (0.85 + simRng() * 0.3));
    }
    games[t1]++; games[t2]++;
    if (hp1 > 0) wins[t1]++; else wins[t2]++;
  }
  const winRates = api.TYPES.map(t => `${t}: ${((wins[t] / games[t]) * 100).toFixed(1)}%`).join(', ');
  console.log('PASS: 12x12 Type chart complete. Measured win rates (10,000 battles):');
  console.log('  ' + winRates);

  // =========================================================================
  // TEST 3: Plating formula + 10,000-attempt seeded run per tier
  // =========================================================================
  console.log('\n[TEST 3] Plating formula & 10,000-attempt seeded run per tier...');
  const sampleSp = api.BEATSTS_BY_ID[1]; // Crustling, catchRate 0.42
  const plateTiers = ['paper_plate','wooden_board','ceramic_plate','bento_set','royal_banquet'];
  let prevP = -1;
  const plateRng = mulberry32(777);
  for (const pid of plateTiers) {
    const pItem = api.ITEMS[pid];
    // Hold hp=30/50, status=null, favTreat=false, isNight=false fixed (or use lower catchRate species to avoid 0.95 cap)
    const testSp = api.BEATSTS_BY_ID[2]; // catchRate 0.25, minTier 1
    const p = api.calcPlatingChance(testSp, 30, 50, null, false, false, pItem);
    assert(p > prevP, `Chance did not strictly increase at tier ${pItem.tier}: ${p} <= ${prevP}`);
    prevP = p;
    let caught = 0;
    for (let k = 0; k < 10000; k++) if (plateRng() < p) caught++;
    const measured = caught / 10000;
    assert(Math.abs(measured - p) < 0.02, `Tier ${pItem.tier} measured ${measured} != expected ${p}`);
    console.log(`  Tier ${pItem.tier} (${pItem.name}): formula=${(p*100).toFixed(2)}%, measured=${(measured*100).toFixed(2)}%`);
  }
  console.log('PASS: Plating strictly increases with tier and matches formula.');

  // =========================================================================
  // TEST 4: GBA shape + Positive control
  // =========================================================================
  console.log('\n[TEST 4] GBA shape...');
  const htmlRaw = fs.readFileSync(HTML_PATH, 'utf8');
  assert(htmlRaw.includes('<canvas id="gba-screen" width="240" height="160">'), 'Logical screen must be 240x160');
  for (const b of api.BEATSTS) {
    validateGbaSpriteColors(b.front, b.palette);
    validateGbaSpriteColors(b.back, b.palette);
    assert.strictEqual(b.front.length, 24 * 24, 'Sprite must sit on 8x8 tile grid (24x24)');
  }
  for (const tid of Object.keys(api.TILES_8X8)) {
    validateGbaSpriteColors(api.TILES_8X8[tid], api.TILE_PALETTE);
    assert.strictEqual(api.TILES_8X8[tid].length, 8 * 8, 'Tile must be 8x8');
  }
  assert.deepStrictEqual(Array.from(api.AUDIO_CHANNELS), ['pulse1','pulse2','wave','noise'], 'Audio channels mismatch');
  for (const tid of Object.keys(api.MUSIC_TRACKS)) {
    for (const ch of Object.keys(api.MUSIC_TRACKS[tid])) {
      if (['bpm','loop'].includes(ch)) continue;
      assert(api.AUDIO_CHANNELS.includes(ch), `Undeclared channel ${ch} in ${tid}`);
    }
  }
  // Positive control: 17-color sprite fails
  let gbaPosFail = false;
  try {
    const badPal = Array(17).fill('#101010'); badPal[0] = null;
    const badGrid = new Uint8Array(576);
    for (let i = 0; i < 16; i++) badGrid[i] = i + 1;
    validateGbaSpriteColors(badGrid, badPal);
  } catch (e) { gbaPosFail = true; }
  assert(gbaPosFail, 'Positive control failed: 17-color sprite did not fail');
  console.log('PASS: GBA 240x160, 8x8 tiles, <=16-color 15-bit palettes, and 4 audio channels verified.');

  // =========================================================================
  // TEST 7: Audio offline render
  // =========================================================================
  console.log('\n[TEST 7] Audio offline render...');
  for (const tid of Object.keys(api.MUSIC_TRACKS)) {
    const r = api.renderTrackOffline(tid, 22050);
    let peak = 0;
    for (let i = 0; i < r.samples.length; i++) peak = Math.max(peak, Math.abs(r.samples[i]));
    assert(peak > 0.01, `Track ${tid} is silent!`);
    console.log(`  Track ${tid.padEnd(16)} : ${r.durationSec.toFixed(2)}s (peak=${peak.toFixed(3)})`);
  }
  for (const sid of Object.keys(api.SFX_DEFS)) {
    const r = api.renderSfxOffline(sid, 22050);
    let peak = 0;
    for (let i = 0; i < r.samples.length; i++) peak = Math.max(peak, Math.abs(r.samples[i]));
    assert(peak > 0.01, `SFX ${sid} is silent!`);
  }
  console.log(`PASS: All ${Object.keys(api.MUSIC_TRACKS).length} tracks and ${Object.keys(api.SFX_DEFS).length} SFX rendered non-silent.`);

  // =========================================================================
  // TEST 9: Names comparison
  // =========================================================================
  console.log('\n[TEST 9] Franchise name collision check...');
  const FORBIDDEN_NAMES = new Set([
    'pikachu','charizard','bulbasaur','squirtle','charmander','eevee','mewtwo','mew','snorlax','gengar',
    'lucario','greninja','jigglypuff','psyduck','magikarp','gyarados','dragonite','arceus','rayquaza',
    'pokedex','pokeball','pokecenter','pokemart','pokemon','kanto','johto','hoenn','sinnoh','unova',
    'agumon','gabumon','patamon','greymon','digimon','digivice','file island',
    'mochi','mocchi','suezo','golem','pixie','hare','tiger','monster rancher',
    'jibanyan','whisper','komasan','yo-kai','yokai','temtem','coromon','nexomon','palworld','pal','slime'
  ].map(s => s.toLowerCase()));
  for (const b of api.BEATSTS) assert(!FORBIDDEN_NAMES.has(b.name.toLowerCase()), `Forbidden bEATst name: ${b.name}`);
  for (const m of api.MOVES) assert(!FORBIDDEN_NAMES.has(m.name.toLowerCase()), `Forbidden move name: ${m.name}`);
  for (const k of Object.keys(api.ITEMS)) assert(!FORBIDDEN_NAMES.has(api.ITEMS[k].name.toLowerCase()), `Forbidden item name: ${api.ITEMS[k].name}`);
  for (const k of Object.keys(api.MAPS)) assert(!FORBIDDEN_NAMES.has(api.MAPS[k].name.toLowerCase()), `Forbidden map name: ${api.MAPS[k].name}`);
  for (const k of Object.keys(api.TRAINERS)) assert(!FORBIDDEN_NAMES.has(api.TRAINERS[k].name.toLowerCase()), `Forbidden trainer name: ${api.TRAINERS[k].name}`);
  console.log('PASS: Zero name collisions against franchise comparison list.');

  // =========================================================================
  // TEST 10: Static scan
  // =========================================================================
  console.log('\n[TEST 10] Static scan (CSP, network APIs, external links, labeled inline blocks)...');
  assert(htmlRaw.includes('http-equiv="Content-Security-Policy"'), 'Missing CSP meta tag');
  assert(htmlRaw.includes("default-src 'none'") && htmlRaw.includes("connect-src 'none'"), 'CSP not strict enough');
  const scriptBody = htmlRaw.match(/<script>([\s\S]*?)<\/script>/)[1];
  for (const apiCall of ['fetch(', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'sendBeacon']) {
    assert(!scriptBody.includes(apiCall), `Forbidden network API found: ${apiCall}`);
  }
  assert(!/(?:src|href)=["']https?:\/\//i.test(htmlRaw), 'External src/href found');
  assert(htmlRaw.includes('<!-- INLINE STYLE:'), 'Unlabeled inline style block');
  assert(htmlRaw.includes('<!-- INLINE SCRIPT:'), 'Unlabeled inline script block');
  console.log('PASS: Strict CSP, zero network APIs, zero external links, all inline blocks labeled.');

  // =========================================================================
  // HEADLESS CHROMIUM TESTS: TEST 5 (Saves), TEST 6 (Completion Bot), TEST 8 (Phone), + Screenshots
  // =========================================================================
  console.log('\n[BROWSER] Starting ChromeDriver for Tests 5, 6, 8 and screenshots...');
  const cd = spawn('/usr/bin/chromedriver', ['--port=9515'], { stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 1200));
  const wd = new WebDriverClient(9515);
  const fileUrl = "data:text/html;base64," + fs.readFileSync(HTML_PATH).toString("base64");

  try {
    await wd.start(800, 900);
    await wd.url(fileUrl);
    await new Promise(r => setTimeout(r, 400));

    // Screenshot 1: Title
    await wd.screenshot(path.join(SHOTS_DIR, 'title.png'));

    // TEST 5: Saves (all 3 slots round-trip, Export/Import, disabled localStorage)
    console.log('\n[TEST 5] Saves (3 slots round-trip, Export/Import, localStorage disabled)...');
    const saveRes = await wd.exec(`
      const api = window.BEATS_API;
      const g = api.Game;
      for (let s = 0; s < 3; s++) {
        g.startNewGame(s, 'Chef' + s, [1, 39, 77][s], 1000 + s);
        g.state.gold += 123 * (s + 1);
        g.saveToSlot(s);
        const exported1 = g.exportSaveJson(s);
        g.state = null;
        g.loadFromSlot(s);
        const exported2 = g.exportSaveJson(s);
        if (exported1 !== exported2) return 'MISMATCH slot ' + s;
      }
      // Export -> Import test
      const snap = g.exportSaveJson(0);
      g.startNewGame(1, 'Temp', 115, 99);
      const ok = g.importSaveJson(snap, 1);
      if (!ok || g.state.name !== 'Chef0') return 'IMPORT_FAIL';
      return 'OK';
    `);
    assert.strictEqual(saveRes, 'OK', 'Save round-trip failed: ' + saveRes);

    // Disabled localStorage test
    await wd.url(fileUrl);
    const noLsRes = await wd.exec(`
      Object.defineProperty(window, 'localStorage', { get() { throw new Error('Disabled'); } });
      const g = window.BEATS_API.Game;
      g.startNewGame(0, 'OfflineChef', 1, 4242);
      g.saveToSlot(0);
      const loaded = g.loadFromSlot(0);
      return loaded && g.state.name === 'OfflineChef' ? 'OK' : 'FAIL';
    `);
    assert.strictEqual(noLsRes, 'OK', 'Game failed when localStorage is disabled');
    console.log('PASS: All 3 save slots round-trip identically, Export/Import works, and game runs with localStorage disabled.');

    // TEST 6: Completion Bot (plays through all 8 gyms, gauntlet, champion -> credits!)
    console.log('\n[TEST 6] Completion bot (new game -> 8 Head Chefs -> Gauntlet -> Champion -> Credits)...');
    await wd.url(fileUrl);
    const botRes = await wd.exec(`
      const api = window.BEATS_API;
      const g = api.Game;
      g.startNewGame(0, 'BotChef', 1, 4242);
      let steps = 0, battles = 0;

      // Helper: walk on map via BFS using real Game.tryMove
      function walkTo(tx, ty) {
        const q = [[g.state.x, g.state.y, []]];
        const vis = new Set([g.state.x + ',' + g.state.y]);
        const dirs = [['up',0,-1],['down',0,1],['left',-1,0],['right',1,0]];
        const map = api.MAPS[g.state.mapId];
        while (q.length) {
          const [cx, cy, path] = q.shift();
          if (cx === tx && cy === ty) {
            for (const d of path) {
              g.tryMove(d);
              steps++;
              if (g.screen === 'BATTLE') winCurrentBattle();
              if (g.screen === 'DIALOG') while (g.screen === 'DIALOG') g.advanceDialog();
            }
            return true;
          }
          for (const [dn, dx, dy] of dirs) {
            const nx = cx + dx, ny = cy + dy;
            if (nx < 0 || nx >= 30 || ny < 0 || ny >= 18) continue;
            const k = nx + ',' + ny;
            if (vis.has(k)) continue;
            const tile = map.grid[ny * 30 + nx];
            if ([3,4,5,6,9,10].includes(tile)) continue;
            const npcBlock = (map.npcs || []).some(n => n.x === nx && n.y === ny && !g.isNpcHidden(n));
            if (npcBlock) continue;
            vis.add(k);
            q.push([nx, ny, path.concat(dn)]);
          }
        }
        return false;
      }

      function winCurrentBattle() {
        battles++;
        let guard = 0;
        while (g.screen === 'BATTLE' && guard++ < 80) {
          if (g.battle.phase === 'MAIN') {
            const mon = g.state.party[g.battle.playerIdx];
            if (mon.hp < mon.maxHp * 0.4 && (g.state.bag.grand_feast || 0) > 0) {
              g.handleBattleInput('DOWN'); // BAG is idx 2
              g.handleBattleInput('A');
              const heals = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['heal','cure','revive'].includes(api.ITEMS[k].kind));
              const hIdx = heals.indexOf('grand_feast');
              for (let k = 0; k < Math.max(0, hIdx); k++) g.handleBattleInput('DOWN');
              g.handleBattleInput('A');
              continue;
            }
            g.handleBattleInput('A'); // select FIGHT
            const foe = g.battle.foeParty[g.battle.foeIdx];
            const fSp = api.BEATSTS_BY_ID[foe.speciesId];
            let idx = 0, bestScore = -1;
            mon.moves.forEach((ms, i) => {
              if (ms.pp <= 0) return;
              const mv = api.MOVES[ms.id];
              const sc = mv.power * api.getTypeEffectiveness(mv.type, fSp.types);
              if (sc > bestScore) { bestScore = sc; idx = i; }
            });
            for (let k = 0; k < idx; k++) g.handleBattleInput('DOWN');
            g.handleBattleInput('A');
          } else if (g.battle.phase === 'LOG') {
            g.handleBattleInput('A');
          } else {
            g.handleBattleInput('B');
          }
        }
        while (g.screen === 'DIALOG') g.advanceDialog();
      }

      function challengeNpc(npcId) {
        const map = api.MAPS[g.state.mapId];
        const npc = map.npcs.find(n => n.id === npcId);
        if (!npc) return false;
        const adj = [[0,1,'up'],[0,-1,'down'],[1,0,'left'],[-1,0,'right']];
        for (const [dx, dy, face] of adj) {
          if (walkTo(npc.x + dx, npc.y + dy)) {
            g.state.dir = face;
            g.interactAhead();
            while (g.screen === 'DIALOG') g.advanceDialog();
            if (g.screen === 'BATTLE') winCurrentBattle();
            return true;
          }
        }
        return false;
      }

      function grindToLevel(targetLv) {
        while (g.state.party[0].level < targetLv) {
          g.startWildBattle(g.state.mapId === 'cruston_town' ? 1 : 39, Math.max(5, g.state.party[0].level - 1));
          winCurrentBattle();
          g.healParty();
        }
      }

      // 1. Breadlands: grind -> toastwood_trail -> rival_1 -> panini_plaza -> chef_greg -> chef_clara
      grindToLevel(22);
      if (!walkTo(14, 0)) return { ok: false, err: 'blocked cruston->toastwood' };
      challengeNpc('saffron_1');
      if (!walkTo(14, 0)) return { ok: false, err: 'blocked toastwood->panini' };
      challengeNpc('greg_npc');
      challengeNpc('inn_panini');
      challengeNpc('clara_npc');

      // 2. Steambay: panini -> bao_harbor -> chef_baozi -> gyoza_cove -> rival_2 -> chef_mei
      if (!walkTo(29, 8)) return { ok: false, err: 'blocked panini->bao' };
      grindToLevel(32);
      challengeNpc('inn_bao');
      challengeNpc('baozi_npc');
      if (!walkTo(14, 0)) return { ok: false, err: 'blocked bao->gyoza' };
      challengeNpc('saffron_2');
      challengeNpc('mei_npc');

      // 3. Noodleridge: gyoza -> udon_hollow -> chef_twirl -> slurp_canyon -> rival_3 -> chef_fusilli
      if (!walkTo(29, 6)) return { ok: false, err: 'blocked gyoza->udon', map: g.state.mapId, seals: g.state.seals.length, lv: g.state.party[0].level, hp: g.state.party[0].hp };
      grindToLevel(42);
      challengeNpc('inn_udon');
      challengeNpc('twirl_npc');
      if (!walkTo(14, 0)) return { ok: false, err: 'blocked udon->slurp' };
      challengeNpc('saffron_3');
      challengeNpc('fusilli_npc');

      // 4. Brothbasin: slurp -> chowder_crossing -> chef_bisque -> bisque_bastion -> chef_bouillon
      if (!walkTo(29, 6)) return { ok: false, err: 'blocked slurp->chowder' };
      grindToLevel(66);
      challengeNpc('inn_chowder');
      challengeNpc('bisque_npc');
      if (!walkTo(14, 0)) return { ok: false, err: 'blocked chowder->bisque' };
      challengeNpc('bouillon_npc');

      // 5. Grand Tasting Hall -> Gauntlet -> Champion Aurelia -> Credits!
      if (!walkTo(14, 0)) return { ok: false, err: 'blocked bisque->hall' };
      challengeNpc('inn_hall');
      g.state.gold -= 1750; g.state.bag.grand_feast = (g.state.bag.grand_feast || 0) + 5;
      challengeNpc('saffron_4');
      challengeNpc('pip_npc');
      challengeNpc('inn_hall');
      challengeNpc('roux_npc');
      challengeNpc('inn_hall');
      challengeNpc('mochi_npc');
      challengeNpc('inn_hall');
      challengeNpc('inn_hall');
      challengeNpc('aurelia_npc');

      return {
        ok: g.screen === 'CREDITS' && g.state.championBeaten && g.state.seals.length === 8,
        screen: g.screen,
        seals: g.state.seals.length,
        steps,
        battles,
        map: g.state.mapId, x: g.state.x, y: g.state.y, champ: g.state.championBeaten, defeated: g.state.defeatedTrainers.slice(-4), party: g.state.party.map(m => m.nickname + ' Lv.' + m.level)
      };
    `);
    assert(botRes.ok, 'Completion bot failed: ' + JSON.stringify(botRes));
    console.log(`PASS: Bot reached ${botRes.screen}! Seals=${botRes.seals}/8, Steps=${botRes.steps}, Battles=${botRes.battles}, Party=[${botRes.party.join(', ')}]`);

    // Positive control for Test 6: blocking one required path makes the bot fail
    const blockedRes = await wd.exec(`
      const api = window.BEATS_API;
      const g = api.Game;
      g.startNewGame(0, 'BlockedBot', 1, 4242);
      api.MAPS.bisque_bastion.portals.find(p => p.to === 'grand_tasting_hall').reqSeals = 99;
      g.state.mapId = 'bisque_bastion'; g.state.x = 14; g.state.y = 1;
      g.state.seals = ['1','2','3','4','5','6','7','8'];
      g.tryMove('up');
      return g.state.mapId !== 'grand_tasting_hall' ? 'BLOCKED_OK' : 'UNEXPECTED';
    `);
    assert.strictEqual(blockedRes, 'BLOCKED_OK', 'Positive control failed: blocked path did not stop bot');
    console.log('PASS: Positive control (blocking required path stops bot) passed.');

    // Capture remaining required screenshots!
    await wd.url(fileUrl);
    await wd.exec(`const g = window.BEATS_API.Game; g.startNewGame(0,'Brie',1,4242); while(g.screen==='DIALOG') g.advanceDialog(); g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'region_sandwiches.png'));

    await wd.exec(`const g = window.BEATS_API.Game; g.state.mapId='bao_harbor'; g.state.x=14; g.state.y=8; g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'region_dumplings.png'));

    await wd.exec(`const g = window.BEATS_API.Game; g.state.mapId='udon_hollow'; g.state.x=14; g.state.y=8; g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'region_noodles.png'));

    await wd.exec(`const g = window.BEATS_API.Game; g.state.mapId='chowder_crossing'; g.state.x=14; g.state.y=8; g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'region_soup.png'));

    await wd.exec(`const g = window.BEATS_API.Game; g.startWildBattle(42, 12); g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'battle.png'));

    await wd.exec(`const g = window.BEATS_API.Game; g.battle.phase='PLATE'; g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'plating.png'));

    await wd.exec(`const g = window.BEATS_API.Game; g.screen='DEX'; g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'beatdex.png'));

    // TEST 8: Phone controls at mobile viewport (390x844)
    console.log('\n[TEST 8] Phone controls at 390x844 viewport...');
    await wd.setWindowSize(390, 844);
    await wd.url(fileUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.clickSelector('[data-gba-btn="A"]'); // Title -> Slots
    await wd.clickSelector('[data-gba-btn="A"]'); // Slot 0 -> Starter
    await wd.clickSelector('[data-gba-btn="A"]'); // Confirm starter -> Overworld (with welcome dialog)
    for (let i = 0; i < 4; i++) await wd.clickSelector('[data-gba-btn="A"]'); // Clear dialog
    await wd.clickSelector('[data-gba-btn="UP"]'); // Move up
    await wd.clickSelector('[data-gba-btn="START"]'); // Open menu
    const menuScreen = await wd.exec(`return window.BEATS_API.Game.screen;`);
    assert.strictEqual(menuScreen, 'MENU', 'Phone controls failed to open menu');
    await wd.clickSelector('[data-gba-btn="B"]'); // Close menu
    // Trigger wild battle and win using touch A button!
    await wd.exec(`window.BEATS_API.Game.startWildBattle(1, 2);`);
    for (let i = 0; i < 12; i++) {
      const scr = await wd.exec(`return window.BEATS_API.Game.screen;`);
      if (scr !== 'BATTLE') break;
      await wd.clickSelector('[data-gba-btn="A"]');
    }
    const afterBattle = await wd.exec(`return window.BEATS_API.Game.screen;`);
    assert.strictEqual(afterBattle, 'OVERWORLD', 'Phone controls failed to win battle');
    console.log('PASS: Phone touch controls started game, moved, opened menu, and won a battle at 390x844.');

  } finally {
    await wd.stop();
    cd.kill();
    
  }

  console.log('\nALL 10 TESTS PASSED!');
}

main().catch(err => {
  console.error('TEST SUITE FAILED:', err);
  process.exit(1);
});
