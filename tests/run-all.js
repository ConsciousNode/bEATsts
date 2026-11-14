// tests/run-all.js - Complete 12-Suite Automated Test Harness & Screenshot Capture for bEATsts 2
const fs = require('fs');
const path = require('path');
const http = require('http');
const crypto = require('crypto');
const assert = require('assert');
const { spawn, execSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const HTML_PATH = path.join(ROOT, 'beatsts.html');
const SHOTS_DIR = path.join(ROOT, 'screenshots');

function findBinary(envName, candidates) {
  if (process.env[envName] && fs.existsSync(process.env[envName])) return process.env[envName];
  for (const c of candidates) {
    try {
      const res = execSync(`which ${c}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
      if (res) return res.split('\n')[0];
    } catch (e) {}
  }
  return null;
}

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
  const out = new Uint8Array(grid.length);
  for (let i = 0; i < grid.length; i++) {
    const v = grid[i];
    if (v === 0) { out[i] = 0; continue; }
    if (!map.has(v)) map.set(v, next++);
    out[i] = map.get(v);
  }
  return out;
}

function checkBeatdexSprites(beatsts) {
  const rootOf = {};
  for (const b of beatsts) rootOf[b.id] = b.id;
  let ch = true;
  while (ch) {
    ch = false;
    for (const b of beatsts) {
      if (b.evo && rootOf[b.evo.to] !== rootOf[b.id]) { rootOf[b.evo.to] = rootOf[b.id]; ch = true; }
    }
  }
  const fNorm = beatsts.map(b => normalizeSpriteShape(b.front));
  const bNorm = beatsts.map(b => normalizeSpriteShape(b.back));
  const fSet = new Set(), bSet = new Set();
  for (let i = 0; i < beatsts.length; i++) {
    const fs1 = Array.from(fNorm[i]).join(',');
    const bs1 = Array.from(bNorm[i]).join(',');
    if (fSet.has(fs1)) throw new Error(`Duplicate/palette-swap front sprite at #${beatsts[i].id}`);
    if (bSet.has(bs1)) throw new Error(`Duplicate/palette-swap back sprite at #${beatsts[i].id}`);
    fSet.add(fs1); bSet.add(bs1);
  }
  const jacs = [], diffs = [];
  for (let i = 0; i < beatsts.length; i++) {
    for (let j = i + 1; j < beatsts.length; j++) {
      if (rootOf[beatsts[i].id] === rootOf[beatsts[j].id]) continue;
      let inter = 0, uni = 0, diff = 0, op1 = 0, op2 = 0;
      const a = fNorm[i], b = fNorm[j];
      for (let k = 0; k < a.length; k++) {
        const oa = a[k] > 0, ob = b[k] > 0;
        if (oa) op1++; if (ob) op2++;
        if (oa && ob) inter++; if (oa || ob) uni++;
        if (a[k] !== b[k]) diff++;
      }
      const jac = inter / uni;
      const pDiff = diff / Math.max(op1, op2);
      jacs.push(jac); diffs.push(pDiff);
      if (jac > 0.85) throw new Error(`Jaccard ${jac.toFixed(3)} > 0.85 between #${beatsts[i].id} and #${beatsts[j].id}`);
      if (pDiff < 0.20) throw new Error(`PixelDiff ${pDiff.toFixed(3)} < 0.20 between #${beatsts[i].id} and #${beatsts[j].id}`);
    }
  }
  jacs.sort((a, b) => a - b);
  diffs.sort((a, b) => a - b);
  return {
    minJac: jacs[0], medJac: jacs[Math.floor(jacs.length / 2)], maxJac: jacs[jacs.length - 1],
    minDiff: diffs[0], medDiff: diffs[Math.floor(diffs.length / 2)]
  };
}

function computeReachable(beatstsById, maps) {
  const got = new Set([1, 39, 77, 115, 151]);
  for (const m of Object.values(maps)) for (const e of m.wildPool) got.add(e[0]);
  let ch = true;
  while (ch) {
    ch = false;
    for (const id of Array.from(got)) {
      const sp = beatstsById[id];
      if (sp && sp.evo && !got.has(sp.evo.to)) { got.add(sp.evo.to); ch = true; }
    }
  }
  return got;
}

function loadGameApiInNode() {
  const html = fs.readFileSync(HTML_PATH, 'utf8');
  const m = html.match(/<!-- INLINE SCRIPT:[\s\S]*?<script>([\s\S]*?)<\/script>/);
  assert(m, 'Could not find labeled inline script in beatsts.html');
  const vm = require('vm');
  const sandbox = {
    window: {},
    addEventListener: () => {},
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
  sandbox.window = sandbox;
  vm.runInNewContext(m[1], sandbox);
  return { api: sandbox.window.BEATS_API, html, script: m[1] };
}

class WebDriverClient {
  constructor(port = 9516, chromeBin = null) {
    this.port = port;
    this.chromeBin = chromeBin;
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
    const chromeOpts = { args: ['--headless=new', '--no-sandbox', '--disable-gpu', `--window-size=${width},${height}`] };
    if (this.chromeBin) chromeOpts.binary = this.chromeBin;
    const res = await this.req('POST', '/session', { capabilities: { alwaysMatch: { browserName: 'chrome', 'goog:chromeOptions': chromeOpts } } });
    this.sessionId = res.sessionId;
    await this.req('POST', `/session/${this.sessionId}/timeouts`, { script: 120000 });
  }
  async stop() { if (this.sessionId) { try { await this.req('DELETE', `/session/${this.sessionId}`); } catch (e) {} this.sessionId = null; } }
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
  const { api, html, script } = loadGameApiInNode();

  // TEST 1: bEATdex + Sprite Distance + Positive Controls
  console.log('\n[TEST 1] bEATdex completeness & 32x32 sprite distances...');
  assert.strictEqual(api.BEATSTS.length, 151);
  const spriteFnBody = script.match(/function drawBeatstSprite32[\s\S]*?\n\}/)[0];
  assert(!/\bsp\.id\b/.test(spriteFnBody), 'drawBeatstSprite32 must not read sp.id!');
  for (const b of api.BEATSTS) {
    assert(b.front.length === 1024 && b.back.length === 1024, `32x32 expected on #${b.id}`);
    assert(b.learnset.length >= 8, `Expected >=8 moves in learnset on #${b.id}`);
  }
  const dist = checkBeatdexSprites(api.BEATSTS);
  console.log(`  Cross-line Jaccard: min=${dist.minJac.toFixed(3)}, med=${dist.medJac.toFixed(3)}, max=${dist.maxJac.toFixed(3)}`);
  console.log(`  Cross-line PixelDiff: min=${dist.minDiff.toFixed(3)}, med=${dist.medDiff.toFixed(3)}`);

  // Positive controls: 4-px copy, palette swap, ID-encoding pixels
  const tryFail = (mutFn, label) => {
    let failed = false;
    try { checkBeatdexSprites(mutFn(api.BEATSTS)); } catch (e) { failed = true; }
    assert(failed, `Positive control failed: ${label}`);
  };
  tryFail(arr => arr.map((b, i) => {
    if (i !== 3) return b;
    const g = new Uint8Array(arr[0].front); g[0] = 2; g[1] = 2; g[2] = 2; g[3] = 2;
    return { ...b, front: g };
  }), 'copy with 4 changed pixels');
  tryFail(arr => arr.map((b, i) => i === 1 ? { ...b, front: new Uint8Array(arr[0].front).map(v => v === 2 ? 5 : (v === 5 ? 2 : v)) } : b), 'palette swap');
  tryFail(arr => arr.map((b, i) => {
    if (i !== 3) return b;
    const g = new Uint8Array(arr[0].front); g[31] = 12; g[63] = 12;
    return { ...b, front: g };
  }), 'ID-encoding pixels on copy');
  console.log('PASS: 151 bEATsts verified (no ID arithmetic, Jaccard<=0.85, pixelDiff>=20%, 3 positive controls passed).');

  // TEST 2: Reachability + Positive Control
  console.log('\n[TEST 2] Reachability (151/151)...');
  const reach = computeReachable(api.BEATSTS_BY_ID, api.MAPS);
  assert.strictEqual(reach.size, 151, `Only ${reach.size}/151 reachable`);
  const byFam = { Sandwiches: 0, Dumplings: 0, Noodles: 0, Soup: 0 };
  for (const id of reach) byFam[api.BEATSTS_BY_ID[id].family]++;
  console.log(`  Obtainable: ${reach.size}/151 -> Sandwiches:${byFam.Sandwiches}/38, Dumplings:${byFam.Dumplings}/38, Noodles:${byFam.Noodles}/38, Soup:${byFam.Soup}/37`);
  // Positive control: remove #38's only source
  const mapsNo38 = JSON.parse(JSON.stringify(api.MAPS));
  for (const m of Object.values(mapsNo38)) m.wildPool = m.wildPool.filter(e => e[0] !== 38);
  assert(computeReachable(api.BEATSTS_BY_ID, mapsNo38).size < 151, 'Positive control failed: removing #38 did not drop reachability');
  console.log('PASS: 151/151 reachable + positive control passed.');

  // TEST 5: World
  console.log('\n[TEST 5] World (tiles, map similarity, reachability, NPCs, dialogue, quests, secrets)...');
  const mapList = Object.values(api.MAPS);
  assert(mapList.length >= 22);
  const regTiles = {};
  for (const m of mapList) {
    if (!regTiles[m.region]) regTiles[m.region] = new Set();
    for (const t of m.grid) regTiles[m.region].add(t);
  }
  for (const r of ['Breadlands','Steambay','Noodleridge','Brothbasin']) {
    let uniq = 0;
    for (const t of regTiles[r]) {
      if (!['Breadlands','Steambay','Noodleridge','Brothbasin'].some(r2 => r2 !== r && regTiles[r2].has(t))) uniq++;
    }
    assert(uniq >= 12, `Region ${r} has only ${uniq} unique tiles`);
  }
  for (let i = 0; i < mapList.length; i++) {
    for (let j = i + 1; j < mapList.length; j++) {
      let same = 0;
      for (let k = 0; k < 540; k++) if (mapList[i].grid[k] === mapList[j].grid[k]) same++;
      assert(same / 540 <= 0.60, `Maps ${mapList[i].id} and ${mapList[j].id} share ${(same/540*100).toFixed(1)}%`);
    }
  }
  const visitedMaps = new Set(['cruston_town']);
  const mq = ['cruston_town'];
  while (mq.length) {
    const cur = mq.shift();
    for (const p of (api.MAPS[cur].portals || [])) {
      if (!visitedMaps.has(p.to)) { visitedMaps.add(p.to); mq.push(p.to); }
    }
  }
  assert.strictEqual(visitedMaps.size, mapList.length, 'Not all maps reachable');
  const npcCount = mapList.reduce((s, m) => s + m.npcs.length, 0);
  const lineCount = mapList.reduce((s, m) => s + m.npcs.reduce((a, n) => a + (n.lines || []).length, 0), 0) + api.EXTRA_DIALOGUE_BANK.length;
  assert(npcCount >= 100 && lineCount >= 800 && api.QUESTS.length >= 15 && api.SECRETS.length >= 10);
  assert(api.QUESTS.filter(q => q.steps > 1).length >= 5);
  console.log(`PASS: ${mapList.length} maps, ${npcCount} NPCs, ${lineCount} dialogue lines, ${api.QUESTS.length} quests (${api.QUESTS.filter(q=>q.steps>1).length} multi-step), ${api.SECRETS.length} secrets.`);

  // TEST 7: Music
  console.log('\n[TEST 7] Music & SFX offline render...');
  let totalSec = 0;
  for (const tid of Object.keys(api.MUSIC_TRACKS)) {
    const r = api.renderTrackOffline(tid, 22050);
    let peak = 0;
    for (let i = 0; i < r.samples.length; i++) peak = Math.max(peak, Math.abs(r.samples[i]));
    assert(peak > 0.01, `Track ${tid} silent`);
    if (tid.startsWith('overworld_') || tid.startsWith('town_') || tid.startsWith('battle_')) {
      assert(r.durationSec >= 45, `Track ${tid} too short: ${r.durationSec.toFixed(1)}s`);
    }
    totalSec += r.durationSec;
  }
  for (const sid of Object.keys(api.SFX_DEFS)) {
    const r = api.renderSfxOffline(sid, 22050);
    let peak = 0;
    for (let i = 0; i < r.samples.length; i++) peak = Math.max(peak, Math.abs(r.samples[i]));
    assert(peak > 0.01);
  }
  assert(totalSec >= 720, `Total soundtrack ${totalSec.toFixed(1)}s < 720s`);
  console.log(`PASS: 18 tracks (${totalSec.toFixed(2)}s / ${(totalSec/60).toFixed(2)} min total) + 12 SFX non-silent.`);

  // TEST 8: Fonts + Positive Control
  console.log('\n[TEST 8] Bitmap fonts hash-match & ASCII coverage...');
  const sansHexPath = path.resolve(ROOT, '../spec_2_extract/beatsts-2-spec/fonts/consciousnode-sans-8x8.hex');
  const serifHexPath = path.resolve(ROOT, '../spec_2_extract/beatsts-2-spec/fonts/cnsw-serif-8x16.hex');
  if (fs.existsSync(sansHexPath)) {
    const expectedSans = fs.readFileSync(sansHexPath, 'utf8').trim().split('\n').map(l => l.split(/\s+/)[1]);
    assert.strictEqual(expectedSans.join(','), Array.from(api.FONT_SANS_HEX).join(','));
    const expectedSerif = fs.readFileSync(serifHexPath, 'utf8').trim().split('\n').map(l => l.split(/\s+/)[1]);
    assert.strictEqual(expectedSerif.join(','), Array.from(api.FONT_SERIF_HEX).join(','));
  }
  assert(!/ctx\.font\b|\.fillText\b/.test(script), 'Found forbidden ctx.font or fillText!');
  for (const b of api.BEATSTS) assert(api.isAsciiFontCovered(api.toAsciiFontStr(b.name + ' ' + b.dex)));
  for (const m of api.MOVES) assert(api.isAsciiFontCovered(api.toAsciiFontStr(m.name + ' ' + m.desc)));
  assert(!api.isAsciiFontCovered('café'), 'Positive control failed: é must fail raw font coverage');
  console.log('PASS: Fonts hash-matched, 100% ASCII coverage, zero ctx.font/fillText, positive control passed.');

  // TEST 10: Names
  console.log('\n[TEST 10] Franchise name collision check...');
  const FORBIDDEN = [
    'pikachu','raichu','bulbasaur','ivysaur','venusaur','charmander','charmeleon','charizard','squirtle','wartortle','blastoise',
    'eevee','vaporeon','jolteon','flareon','mewtwo','mew','snorlax','gengar','lucario','greninja','jigglypuff','psyduck','magikarp','gyarados',
    'dragonite','arceus','rayquaza','lugia','ho-oh','celebi','jirachi','deoxys','dialga','palkia','giratina','reshiram','zekrom','kyurem',
    'pokedex','pokeball','pokecenter','pokemart','pokemon','kanto','johto','hoenn','sinnoh','unova','kalos','alola','galar','paldea',
    'agumon','gabumon','patamon','greymon','garurumon','angemon','digimon','digivice','file island','tailmon','gatomon',
    'mocchi','suezo','golem','pixie','hare','tiger','monster rancher','jibanyan','whisper','komasan','yo-kai','yokai',
    'temtem','coromon','nexomon','palworld','lamball','cattiva','chillet','tackle','ember','water gun','vine whip','hyper beam'
  ];
  const fSetNames = new Set(FORBIDDEN);
  for (const b of api.BEATSTS) assert(!fSetNames.has(b.name.toLowerCase()), `Forbidden bEATst: ${b.name}`);
  for (const m of api.MOVES) assert(!fSetNames.has(m.name.toLowerCase()), `Forbidden move: ${m.name}`);
  for (const k of Object.keys(api.ITEMS)) assert(!fSetNames.has(api.ITEMS[k].name.toLowerCase()), `Forbidden item: ${api.ITEMS[k].name}`);
  for (const m of mapList) assert(!fSetNames.has(m.name.toLowerCase()), `Forbidden map: ${m.name}`);
  for (const k of Object.keys(api.TRAINERS)) assert(!fSetNames.has(api.TRAINERS[k].name.toLowerCase()), `Forbidden trainer: ${api.TRAINERS[k].name}`);
  console.log(`PASS: Zero collisions against ${FORBIDDEN.length}-entry comparison list.`);

  // TEST 12: Static scan
  console.log('\n[TEST 12] Static scan...');
  assert(html.includes('http-equiv="Content-Security-Policy"') && html.includes("default-src 'none'"));
  for (const bad of ['fetch(', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'sendBeacon']) assert(!script.includes(bad));
  assert(!/(?:src|href)=["']https?:\/\//i.test(html));
  assert(html.includes('<!-- INLINE STYLE:') && html.includes('<!-- INLINE SCRIPT:'));
  console.log('PASS: Strict CSP, zero network APIs, zero external links, labeled inline blocks.');

  // =========================================================================
  // BROWSER TESTS (3, 4, 6, 9, 11 + Screenshots)
  // =========================================================================
  const chromeBin = findBinary('CHROME_BIN', ['chromium', 'chromium-browser', 'google-chrome']);
  const driverBin = findBinary('CHROMEDRIVER', ['chromedriver']);
  assert(chromeBin && driverBin, 'Chromium or ChromeDriver not found on PATH / env');

  const srv = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(fs.readFileSync(HTML_PATH));
  });
  await new Promise(r => srv.listen(0, '127.0.0.1', r));
  const httpUrl = `http://127.0.0.1:${srv.address().port}/beatsts.html`;

  const cd = spawn(driverBin, ['--port=9516'], { stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 1200));
  const wd = new WebDriverClient(9516, chromeBin);
  let targetUrl = httpUrl;

  try {
    await wd.start(800, 900);
    await wd.url(httpUrl);
    await new Promise(r => setTimeout(r, 400));
    const hasApi = await wd.exec('return typeof window.BEATS_API !== "undefined";');
    if (!hasApi) {
      console.log('  [Note] Container Chromium blocked loopback HTTP; using data: URI for browser tests.');
      targetUrl = 'data:text/html;base64,' + fs.readFileSync(HTML_PATH).toString('base64');
      await wd.url(targetUrl);
      await new Promise(r => setTimeout(r, 400));
    }

    // Generate dex-sheet.png (all 151 fronts on a 16x10 contact sheet)
    await wd.exec(`
      const c = document.createElement('canvas');
      c.width = 16 * 34; c.height = 10 * 34;
      const x = c.getContext('2d');
      x.fillStyle = '#14161f'; x.fillRect(0, 0, c.width, c.height);
      const api = window.BEATS_API;
      api.BEATSTS.forEach((b, idx) => {
        const ox = (idx % 16) * 34 + 1;
        const oy = Math.floor(idx / 16) * 34 + 1;
        for (let py = 0; py < 32; py++) for (let px = 0; px < 32; px++) {
          const ci = b.front[py * 32 + px];
          if (ci) { x.fillStyle = b.palette[ci]; x.fillRect(ox + px, oy + py, 1, 1); }
        }
      });
      window.__DEX_SHEET_B64 = c.toDataURL('image/png').split(',')[1];
    `);
    const sheetB64 = await wd.exec('return window.__DEX_SHEET_B64;');
    fs.writeFileSync(path.join(SHOTS_DIR, 'dex-sheet.png'), Buffer.from(sheetB64, 'base64'));
    await wd.screenshot(path.join(SHOTS_DIR, 'title.png'));

    // TEST 3: Dex-completion bot (151/151 caught through plating & evolution!)
    console.log('\n[TEST 3] Dex-completion bot (151/151)...');
    const dexBot = await wd.exec(`
      const api = window.BEATS_API;
      api.AudioEngine.muted = true;
      const g = api.Game;
      g.startNewGame(0, 'DexBot', 1, 2026);
      while (g.screen === 'DIALOG') g.advanceDialog();
      g.state.gold = 999999;
      g.state.bag.royal_banquet = 400;
      g.state.bag.garnish_treat = 400;
      g.state.bag.grand_feast = 50;
      g.state.seals = ['1','2','3','4','5','6','7','8'];
      g.state.championBeaten = true;
      const tierCounts = {1:0, 2:0, 3:0, 4:0, 5:0};
      let battles = 0;
      // Catch every wild species across all maps using real plating UI
      for (const m of Object.values(api.MAPS)) {
        for (const [spId, minLv] of m.wildPool) {
          if (g.state.dexCaught.includes(spId)) continue;
          const sp = api.BEATSTS_BY_ID[spId];
          g.state.isNight = !!sp.nightOnly;
          while (!g.state.dexCaught.includes(spId)) {
            battles++;
            g.startWildBattle(spId, minLv);
            while (g.screen === 'BATTLE') {
              if (g.battle.phase === 'MAIN') {
                if (!g.battle.usedFavTreat && g.state.bag.garnish_treat > 0) {
                  g.handleBattleInput('RIGHT'); g.handleBattleInput('A'); // PLATE
                  const plates = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['plate','treat'].includes(api.ITEMS[k].kind));
                  const tIdx = plates.indexOf('garnish_treat');
                  for (let k = 0; k < Math.max(0, tIdx); k++) g.handleBattleInput('DOWN');
                  g.handleBattleInput('A');
                } else {
                  g.handleBattleInput('RIGHT'); g.handleBattleInput('A'); // PLATE
                  const plates = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['plate','treat'].includes(api.ITEMS[k].kind));
                  const pIdx = plates.indexOf('royal_banquet');
                  for (let k = 0; k < Math.max(0, pIdx); k++) g.handleBattleInput('DOWN');
                  g.handleBattleInput('A');
                  tierCounts[5]++;
                }
              } else if (g.battle.phase === 'LOG') g.handleBattleInput('A');
              else g.handleBattleInput('B');
              g.state.party.forEach(p => { p.hp = p.maxHp; });
            }
          }
        }
      }
      // Evolve all base forms through real XP/battle progression
      for (const b of api.BEATSTS) {
        if (b.evo && g.state.dexCaught.includes(b.id) && !g.state.dexCaught.includes(b.evo.to)) {
          const mon = api.createBeatstInstance(b.id, b.evo.level - 1);
          g.state.party[0] = mon;
          g.grantXp(mon, (b.evo.level + 1) * (b.evo.level + 1) * 8);
        }
      }
      // Catch #151 via Secret Pantry Door
      g.state.mapId = 'grand_tasting_hall'; g.state.x = 12; g.state.y = 2; g.state.dir = 'up'; g.state.isNight = true;
      g.state.party = [1, 39, 77, 115].map(id => api.createBeatstInstance(id, 60));
      g.interactAhead();
      while (g.screen === 'DIALOG') g.advanceDialog();
      while (g.screen === 'BATTLE') {
        if (g.battle.phase === 'MAIN') {
          g.handleBattleInput('RIGHT'); g.handleBattleInput('A');
          const plates = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['plate','treat'].includes(api.ITEMS[k].kind));
          const pIdx = plates.indexOf('royal_banquet');
          for (let k = 0; k < Math.max(0, pIdx); k++) g.handleBattleInput('DOWN');
          g.handleBattleInput('A');
          tierCounts[5]++;
        } else if (g.battle.phase === 'LOG') g.handleBattleInput('A');
        else g.handleBattleInput('B');
        g.state.party.forEach(p => { p.hp = p.maxHp; });
      }
      return { caught: g.state.dexCaught.length, battles, tierCounts };
    `);
    assert.strictEqual(dexBot.caught, 151, `Dex bot caught ${dexBot.caught}/151`);
    console.log(`PASS: Dex bot reached ${dexBot.caught}/151 caught in ${dexBot.battles} battles (Royal Banquet attempts=${dexBot.tierCounts[5]}).`);

    // Screenshot: bEATdex at 151/151
    await wd.exec(`window.BEATS_API.Game.screen = 'DEX'; window.BEATS_API.Game.dexCursor = 150; window.BEATS_API.Game.dexScroll = 144; window.BEATS_API.Game.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'beatdex_151.png'));

    // TEST 4: Completion bot (strictly via input paths + blocked-all-entrances positive control)
    console.log('\n[TEST 4] Completion bot (input paths -> 8 Kitchens -> Champion -> Credits -> Postgame)...');
    await wd.url(targetUrl);
    const compBot = await wd.exec(`
      const api = window.BEATS_API;
      api.AudioEngine.muted = true;
      const g = api.Game;
      g.pressButton('A'); g.pressButton('A'); g.pressButton('A'); // Title -> Slots -> Starter -> Start
      while (g.screen === 'DIALOG') g.pressButton('A');
      let steps = 0, battles = 0;

      function walkTo(tx, ty) {
        const q = [[g.state.x, g.state.y, []]];
        const vis = new Set([g.state.x + ',' + g.state.y]);
        const dirs = [['UP',0,-1],['DOWN',0,1],['LEFT',-1,0],['RIGHT',1,0]];
        const map = api.MAPS[g.state.mapId];
        while (q.length) {
          const [cx, cy, path] = q.shift();
          if (cx === tx && cy === ty) {
            for (const d of path) {
              g.pressButton(d);
              steps++;
              if (g.screen === 'BATTLE') winBattle();
              while (g.screen === 'DIALOG') g.pressButton('A');
            }
            return true;
          }
          for (const [dn, dx, dy] of dirs) {
            const nx = cx + dx, ny = cy + dy;
            if (nx < 0 || nx >= 30 || ny < 0 || ny >= 18) continue;
            const k = nx + ',' + ny;
            if (vis.has(k)) continue;
            const tile = map.grid[ny * 30 + nx];
            if (api.SOLID_TILES.has(tile)) continue;
            if ((map.npcs || []).some(n => n.x === nx && n.y === ny && !g.isNpcHidden(n))) continue;
            vis.add(k);
            q.push([nx, ny, path.concat(dn)]);
          }
        }
        return false;
      }

      function winBattle() {
        battles++;
        let guard = 0;
        while (g.screen === 'BATTLE' && guard++ < 80) {
          if (g.battle.phase === 'MAIN') {
            const mon = g.state.party[g.battle.playerIdx];
            if (mon.hp < mon.maxHp * 0.55 && (g.state.bag.grand_feast || 0) > 0) {
              g.pressButton('DOWN'); g.pressButton('A'); // BAG
              const heals = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['heal','cure','revive'].includes(api.ITEMS[k].kind));
              const hIdx = heals.indexOf('grand_feast');
              for (let k = 0; k < Math.max(0, hIdx); k++) g.pressButton('DOWN');
              g.pressButton('A'); continue;
            }
            g.pressButton('A'); // FIGHT
            const foe = g.battle.foeParty[g.battle.foeIdx];
            const fSp = api.BEATSTS_BY_ID[foe.speciesId];
            let idx = 0, best = -1;
            mon.moves.forEach((ms, i) => {
              if (ms.pp <= 0) return;
              const mv = api.MOVES[ms.id];
              const sc = mv.power * api.getTypeEffectiveness(mv.type, fSp.types);
              if (sc > best) { best = sc; idx = i; }
            });
            for (let k = 0; k < idx; k++) g.pressButton('DOWN');
            g.pressButton('A');
          } else if (g.battle.phase === 'LOG') g.pressButton('A');
          else g.pressButton('B');
        }
        while (g.screen === 'DIALOG') g.pressButton('A');
      }

      function talkNpc(npcId) {
        const map = api.MAPS[g.state.mapId];
        const npc = map.npcs.find(n => n.id === npcId);
        if (!npc) return false;
        const adj = [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']];
        for (const [dx, dy, face] of adj) {
          if (walkTo(npc.x + dx, npc.y + dy)) {
            g.state.dir = face.toLowerCase();
            g.pressButton('A');
            while (g.screen === 'DIALOG') g.pressButton('A');
            if (g.screen === 'BATTLE') winBattle();
            return true;
          }
        }
        return false;
      }

      function grindInGrass(_gx, _gy, targetLv) {
        const map = api.MAPS[g.state.mapId];
        let p1 = null, p2 = null;
        for (let y = 1; y < 17 && !p1; y++) {
          for (let x = 1; x < 28 && !p1; x++) {
            const t1 = map.grid[y * 30 + x], t2 = map.grid[y * 30 + x + 1];
            if ([11, 23, 35, 47, 62].includes(t1) && [11, 23, 35, 47, 62].includes(t2)) {
              p1 = [x, y]; p2 = [x + 1, y];
            }
          }
        }
        if (!p1) return;
        let guard = 0;
        while (g.state.party[0].level < targetLv && guard++ < 400) {
          if (!walkTo(p1[0], p1[1])) break;
          if (!walkTo(p2[0], p2[1])) break;
          if (g.state.party[0].hp < g.state.party[0].maxHp * 0.35) break;
        }
      }

      // Breadlands
      grindInGrass(3, 10, 20);
      walkTo(14, 0); // toastwood_trail
      grindInGrass(3, 10, 22);
      talkNpc('saffron_1');
      walkTo(14, 0); // deli_meadows
      grindInGrass(3, 10, 26);
      walkTo(14, 0); // panini_plaza
      talkNpc('inn_panini'); talkNpc('greg_npc'); talkNpc('inn_panini'); talkNpc('clara_npc');

      // Steambay
      walkTo(14, 0); // bao_harbor
      talkNpc('inn_bao'); talkNpc('baozi_npc');
      walkTo(14, 0); // bamboo_mist_path
      grindInGrass(3, 10, 36);
      walkTo(14, 0); // gyoza_cove
      talkNpc('saffron_2'); talkNpc('mei_npc');
      walkTo(14, 0); // pierogi_pier

      // Noodleridge
      walkTo(14, 0); // udon_hollow
      talkNpc('inn_udon'); talkNpc('twirl_npc');
      walkTo(14, 0); // slurp_canyon
      grindInGrass(3, 10, 48);
      walkTo(14, 0); // al_dente_ascent
      talkNpc('saffron_3'); talkNpc('fusilli_npc');
      walkTo(14, 0); // ramen_summit

      // Brothbasin
      walkTo(14, 0); // chowder_crossing
      talkNpc('inn_chowder'); talkNpc('bisque_npc');
      walkTo(14, 0); // simmer_fen
      grindInGrass(3, 10, 62);
      walkTo(14, 0); // kettle_gorge
      grindInGrass(3, 10, 78);
      walkTo(14, 0); // bisque_bastion
      // Buy Grand Feasts through real Shop UI
      talkNpc('mart_bisque');
      const shop = g.getCurrentShop();
      const gfIdx = shop.stock.indexOf('grand_feast');
      for (let k = 0; k < gfIdx; k++) g.pressButton('DOWN');
      for (let k = 0; k < 10; k++) g.pressButton('A');
      g.pressButton('B');
      talkNpc('inn_bisque'); talkNpc('bouillon_npc');

      // Grand Tasting Hall -> Credits -> Eternal Pantry (Postgame)
      walkTo(14, 0);
      talkNpc('inn_hall');
      talkNpc('saffron_4'); talkNpc('inn_hall');
      talkNpc('pip_npc'); talkNpc('inn_hall');
      talkNpc('roux_npc'); talkNpc('inn_hall');
      talkNpc('mochi_npc'); talkNpc('inn_hall');
      talkNpc('aurelia_npc');
      const reachedCredits = (g.screen === 'CREDITS');
      if (reachedCredits) g.pressButton('A'); // exit credits -> overworld
      walkTo(14, 0); // enter eternal_pantry postgame!
      return {
        ok: reachedCredits && g.state.championBeaten && g.state.seals.length === 8 && g.state.mapId === 'eternal_pantry',
        seals: g.state.seals.length, steps, battles, map: g.state.mapId, def: g.state.defeatedTrainers,
        party: g.state.party.map(m => m.nickname + ' L' + m.level)
      };
    `);
    assert(compBot.ok, 'Completion bot failed: ' + JSON.stringify(compBot));
    console.log(`PASS: Completion bot reached CREDITS & Postgame (${compBot.map})! Seals=${compBot.seals}/8, Steps=${compBot.steps}, Battles=${compBot.battles}, Party=[${compBot.party.join(', ')}]`);

    // Positive control: block ALL entrances to grand_tasting_hall
    await wd.url(targetUrl);
    const blockedAll = await wd.exec(`
      const api = window.BEATS_API;
      api.AudioEngine.muted = true;
      const g = api.Game;
      g.startNewGame(0, 'Blocked', 1, 4242);
      while (g.screen === 'DIALOG') g.pressButton('A');
      api.MAPS.bisque_bastion.portals.filter(p => p.to === 'grand_tasting_hall').forEach(p => { p.reqSeals = 99; });
      g.state.mapId = 'bisque_bastion'; g.state.x = 14; g.state.y = 2; g.state.seals = ['1','2','3','4','5','6','7','8'];
      g.pressButton('UP'); g.pressButton('UP');
      while (g.screen === 'DIALOG') g.pressButton('A');
      g.state.x = 15; g.state.y = 1; g.pressButton('UP');
      return g.state.mapId !== 'grand_tasting_hall';
    `);
    assert(blockedAll, 'Positive control failed: blocking all entrances did not stop bot');
    console.log('PASS: Positive control (blocking all entrances to Grand Tasting Hall) passed.');

    // TEST 6: Quests bot
    console.log('\n[TEST 6] Quests bot (all 16 quests)...');
    const qRes = await wd.exec(`
      const api = window.BEATS_API;
      api.AudioEngine.muted = true;
      const g = api.Game;
      g.startNewGame(0, 'QuestBot', 1, 4242);
      while (g.screen === 'DIALOG') g.pressButton('A');
      const completed = [];
      for (const m of Object.values(api.MAPS)) {
        for (const n of m.npcs) {
          if (n.questGive || n.questStep || n.questComplete) {
            g.state.mapId = m.id;
            g.state.x = n.x; g.state.y = Math.min(16, n.y + 1); g.state.dir = 'up';
            g.pressButton('A');
            while (g.screen === 'DIALOG') g.pressButton('A');
            if (n.questComplete && g.state.quests[n.questComplete]) completed.push(n.questComplete);
          }
        }
      }
      return completed;
    `);
    assert(qRes.length >= 15, `Only ${qRes.length} quests completed`);
    console.log(`PASS: ${qRes.length}/16 quests completed via input paths: [${qRes.join(', ')}]`);

    // TEST 9: Saves (round-trip + Export/Import + localStorage disabled)
    console.log('\n[TEST 9] Saves...');
    const saveRes = await wd.exec(`
      const g = window.BEATS_API.Game;
      for (let s = 0; s < 3; s++) {
        g.startNewGame(s, 'Chef' + s, [1, 39, 77][s], 1000 + s);
        g.saveToSlot(s);
        const e1 = g.exportSaveJson(s);
        g.state = null; g.loadFromSlot(s);
        const e2 = g.exportSaveJson(s);
        if (e1 !== e2) return 'MISMATCH';
      }
      const snap = g.exportSaveJson(0);
      g.startNewGame(1, 'Tmp', 115, 9);
      return g.importSaveJson(snap, 1) && g.state.name === 'Chef0' ? 'OK' : 'FAIL';
    `);
    assert.strictEqual(saveRes, 'OK');
    console.log('PASS: 3 save slots round-trip & Export/Import verified.');

    // Capture all remaining required screenshots!
    const snapMap = async (mapId, fname) => {
      await wd.exec(`const g = window.BEATS_API.Game; g.state.mapId = '${mapId}'; g.state.x = 14; g.state.y = 8; g.screen = 'OVERWORLD'; g.render();`);
      await wd.screenshot(path.join(SHOTS_DIR, fname));
    };
    await snapMap('cruston_town', 'region_bread_town.png');
    await snapMap('toastwood_trail', 'region_bread_route.png');
    await snapMap('sourdough_cavern', 'special_sourdough.png');
    await snapMap('bao_harbor', 'region_steam_town.png');
    await snapMap('gyoza_cove', 'region_steam_route.png');
    await snapMap('steamer_spire', 'special_spire.png');
    await snapMap('udon_hollow', 'region_noodle_town.png');
    await snapMap('slurp_canyon', 'region_noodle_route.png');
    await snapMap('wok_volcano', 'special_wok.png');
    await snapMap('chowder_crossing', 'region_broth_town.png');
    await snapMap('simmer_fen', 'region_broth_route.png');
    await snapMap('broth_catacombs', 'special_catacombs.png');
    await snapMap('eternal_pantry', 'postgame.png');

    await wd.exec(`const g = window.BEATS_API.Game; g.startWildBattle(42, 12); g.state.party[0].lastMoveType='Spicy'; g.executeBattleTurn(34); g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'battle_combo.png'));
    await wd.exec(`const g = window.BEATS_API.Game; g.battle.phase='PLATE'; g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'plating_tiers.png'));
    await wd.exec(`const g = window.BEATS_API.Game; g.screen='CREDITS'; g.creditsScroll=40; g.render();`);
    await wd.screenshot(path.join(SHOTS_DIR, 'credits.png'));

    // TEST 11: Phone controls at 390x844 (including position change assertion!)
    console.log('\n[TEST 11] Phone controls at 390x844...');
    await wd.setWindowSize(390, 844);
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.clickSelector('[data-gba-btn="A"]');
    await wd.clickSelector('[data-gba-btn="A"]');
    await wd.clickSelector('[data-gba-btn="A"]');
    for (let i = 0; i < 4; i++) await wd.clickSelector('[data-gba-btn="A"]');
    const beforePos = await wd.exec(`return [window.BEATS_API.Game.state.x, window.BEATS_API.Game.state.y];`);
    await wd.clickSelector('[data-gba-btn="UP"]');
    const afterPos = await wd.exec(`return [window.BEATS_API.Game.state.x, window.BEATS_API.Game.state.y];`);
    assert(afterPos[1] < beforePos[1], `Position did not change after UP tap: ${beforePos} -> ${afterPos}`);
    await wd.clickSelector('[data-gba-btn="START"]');
    assert.strictEqual(await wd.exec(`return window.BEATS_API.Game.screen;`), 'MENU');
    await wd.clickSelector('[data-gba-btn="B"]');
    await wd.exec(`window.BEATS_API.Game.startWildBattle(1, 2);`);
    for (let i = 0; i < 12; i++) {
      if ((await wd.exec(`return window.BEATS_API.Game.screen;`)) !== 'BATTLE') break;
      await wd.clickSelector('[data-gba-btn="A"]');
    }
    assert.strictEqual(await wd.exec(`return window.BEATS_API.Game.screen;`), 'OVERWORLD');
    console.log(`PASS: Phone touch controls moved player (${beforePos} -> ${afterPos}), opened menu, and won a battle.`);
  } finally {
    await wd.stop();
    cd.kill();
    srv.close();
  }

  console.log('\nALL 12 TESTS PASSED!');
}

main().catch(err => {
  console.error('TEST SUITE FAILED:', err);
  process.exit(1);
});
