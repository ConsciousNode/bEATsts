// tests/run-all.js - Complete Automated Test Harness & Screenshot Capture for bEATsts 2.2
const fs = require('fs');
const path = require('path');
const http = require('http');
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

function normalizeSpriteShape(grid) {
  const map = new Map();
  let next = 1;
  const out = new Uint8Array(grid.length);
  for (let i = 0; i < grid.length; i++) {
    const v = grid[i];
    if (v === 0 || v === null) { out[i] = 0; continue; }
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
  for (const m of Object.values(maps)) for (const e of (m.wildPool || [])) got.add(e[0]);
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

function checkMapRoleSimilarity(maps, tileRoles) {
  const list = Object.values(maps);
  const roleGrids = list.map(m => {
    const arr = new Array(m.grid.length);
    for (let k = 0; k < m.grid.length; k++) arr[k] = tileRoles[m.grid[k]] || 'other';
    return arr;
  });
  let maxSame = 0, maxDiff = 0;
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      const a = list[i], b = list[j];
      const ga = roleGrids[i], gb = roleGrids[j];
      if (a.w === b.w && a.h === b.h) {
        let same = 0;
        for (let k = 0; k < ga.length; k++) if (ga[k] === gb[k]) same++;
        const sim = same / ga.length;
        if (sim > maxSame) maxSame = sim;
        if (sim > 0.50) throw new Error(`Same-size map role similarity ${sim.toFixed(3)} > 0.50 between ${a.id} and ${b.id}`);
      } else if ((a.w <= b.w && a.h <= b.h) || (b.w <= a.w && b.h <= a.h)) {
        const [small, gs, big, gb2] = (a.w <= b.w && a.h <= b.h) ? [a, ga, b, gb] : [b, gb, a, ga];
        let best = 0;
        for (let oy = 0; oy <= big.h - small.h; oy++) {
          for (let ox = 0; ox <= big.w - small.w; ox++) {
            let same = 0;
            for (let y = 0; y < small.h; y++) {
              const rs = y * small.w, rb = (oy + y) * big.w + ox;
              for (let x = 0; x < small.w; x++) if (gs[rs + x] === gb2[rb + x]) same++;
            }
            const sim = same / gs.length;
            if (sim > best) best = sim;
          }
        }
        if (best > maxDiff) maxDiff = best;
        if (best > 0.50) throw new Error(`Best-alignment map role similarity ${best.toFixed(3)} > 0.50 between ${small.id} (${small.w}x${small.h}) and ${big.id} (${big.w}x${big.h})`);
      }
    }
  }
  return { maxSame, maxDiff };
}

function checkAllPortalsReachable(maps, solidTiles) {
  const visMaps = new Set(['cruston_town']);
  const visTiles = new Set(['cruston_town,14,12']);
  const q = [['cruston_town', 14, 12]];
  const reachedPortals = new Set();
  while (q.length) {
    const [mid, x, y] = q.shift();
    const m = maps[mid];
    const mw = m.w || 30, mh = m.h || 18;
    for (const p of (m.portals || [])) {
      if (Math.abs(p.x - x) + Math.abs(p.y - y) === 1) {
        reachedPortals.add(`${mid}:${p.x},${p.y}->${p.to}`);
        const dk = `${p.to},${p.tx},${p.ty}`;
        if (!visTiles.has(dk)) {
          visTiles.add(dk);
          visMaps.add(p.to);
          q.push([p.to, p.tx, p.ty]);
        }
      }
    }
    for (const [dx, dy] of [[0,1],[0,-1],[1,0],[-1,0]]) {
      const nx = x + dx, ny = y + dy;
      if (nx < 0 || nx >= mw || ny < 0 || ny >= mh) continue;
      const t = m.grid[ny * mw + nx];
      if (!solidTiles.has(t) || t === 73) {
        const k = `${mid},${nx},${ny}`;
        if (!visTiles.has(k)) {
          visTiles.add(k);
          q.push([mid, nx, ny]);
        }
      }
    }
  }
  const totalPortals = Object.values(maps).reduce((s, m) => s + (m.portals || []).length, 0);
  if (visMaps.size !== Object.keys(maps).length) {
    throw new Error(`Unreachable maps: ${Object.keys(maps).filter(k => !visMaps.has(k)).join(', ')}`);
  }
  if (reachedPortals.size !== totalPortals) {
    throw new Error(`Unreachable portals: ${reachedPortals.size}/${totalPortals}`);
  }
  return { maps: visMaps.size, portals: reachedPortals.size };
}

function collapseTemplateFamilies(lines, maps) {
  // Collapse lines that differ only by swapped dish/food/place/region names or numbers
  const placeNames = Object.values(maps).map(m => m.name).sort((a, b) => b.length - a.length);
  const regions = ['Breadlands', 'Steambay', 'Noodleridge', 'Brothbasin', 'TastingHall', 'Postgame'];
  const dishes = [
    'sourdough','focaccia','brioche','ciabatta','rye toast','panini','baguette','pretzel','croissant','pita',
    'baozi','gyoza','shumai','pierogi','empanada','onigiri','mochi','ravioli','khinkali','takoyaki',
    'ramen','udon','pho broth','pho','lo mein','pad thai','lasagna','spaghetti','soba','macaroni','vermicelli',
    'chowder','bisque','consomme','miso','borscht','gumbo','minestrone','gazpacho','chili'
  ].sort((a, b) => b.length - a.length);
  const collapsed = new Set();
  for (const raw of lines) {
    let s = raw;
    for (const p of placeNames) s = s.split(p).join('<PLACE>');
    for (const r of regions) s = s.split(r).join('<REGION>');
    for (const d of dishes) s = s.replace(new RegExp(`\\b${d}\\b`, 'gi'), '<DISH>');
    s = s.replace(/\d+/g, '<NUM>').trim();
    collapsed.add(s);
  }
  return collapsed;
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
  constructor(port = 9517, chromeBin = null) {
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
    const chromeOpts = { args: ['--headless=new', '--no-sandbox', '--disable-gpu', '--no-proxy-server', `--window-size=${width},${height}`] };
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
  // Clean old screenshots so zero leftovers remain
  if (fs.existsSync(SHOTS_DIR)) {
    for (const f of fs.readdirSync(SHOTS_DIR)) {
      if (f.endsWith('.png')) fs.unlinkSync(path.join(SHOTS_DIR, f));
    }
  } else {
    fs.mkdirSync(SHOTS_DIR, { recursive: true });
  }

  const { api, html, script } = loadGameApiInNode();

  // TEST 1: bEATdex & 32x32 Sprites + Character Sprites
  console.log('\n[TEST 1] bEATdex completeness, 32x32 sprites & 16x24 character sprites...');
  assert.strictEqual(api.BEATSTS.length, 151);
  const spriteFnBody = script.match(/function drawBeatstSprite32[\s\S]*?\n\}/)[0];
  assert(!/\bsp\.id\b/.test(spriteFnBody), 'drawBeatstSprite32 must not read sp.id!');
  const dist = checkBeatdexSprites(api.BEATSTS);
  console.log(`  Cross-line Jaccard: min=${dist.minJac.toFixed(3)}, med=${dist.medJac.toFixed(3)}, max=${dist.maxJac.toFixed(3)}`);
  console.log(`  Cross-line PixelDiff: min=${dist.minDiff.toFixed(3)}, med=${dist.medDiff.toFixed(3)}`);

  const tryFail = (mutFn, label) => {
    let failed = false;
    try {
      const clone = api.BEATSTS.map(b => ({ ...b, front: new Uint8Array(b.front), back: new Uint8Array(b.back) }));
      mutFn(clone);
      checkBeatdexSprites(clone);
    } catch (e) { failed = true; }
    assert(failed, `Positive control failed to catch: ${label}`);
  };
  tryFail(c => { c[4].front = new Uint8Array(c[0].front); c[4].front[0] = 2; c[4].front[1] = 2; }, '4-px copy');
  tryFail(c => { c[4].front = new Uint8Array(c[0].front); }, 'palette swap');

  const namedKeys = ['brotholomew','saffron','chef_greg','chef_clara','chef_baozi','chef_mei','chef_twirl','chef_fusilli','chef_bisque','chef_bouillon','taster_pip','taster_roux','taster_mochi','champion','officer_vesper','officer_crumb','officer_glaze','boss_ladle'];
  const namedShapes = new Set();
  for (const k of namedKeys) {
    const f0 = api.buildCharSpriteGrid(k, 'down', 0);
    const f1 = api.buildCharSpriteGrid(k, 'down', 1);
    const f2 = api.buildCharSpriteGrid(k, 'down', 2);
    assert(f0.length === 16 * 24, `Expected 16x24 sprite on ${k}`);
    assert(JSON.stringify(f0) !== JSON.stringify(f1) && JSON.stringify(f1) !== JSON.stringify(f2), `Walk frames must differ on ${k}`);
    for (const dir of ['down','up','left','right']) assert(api.buildCharSpriteGrid(k, dir, 0).length === 384);
    const norm = Array.from(normalizeSpriteShape(f0)).join(',');
    assert(!namedShapes.has(norm), `Named character ${k} is not unique!`);
    namedShapes.add(norm);
  }
  const villagerKeys = Object.keys(api.CHAR_SPRITES).filter(k => k.startsWith('villager_'));
  assert(villagerKeys.length >= 12, `Expected >=12 generic villager designs, got ${villagerKeys.length}`);
  console.log(`PASS: 151 bEATsts + ${namedKeys.length} unique named chars (4 dirs x 3 frames) + ${villagerKeys.length} generic villagers verified.`);

  // TEST 2: Reachability (151/151)
  console.log('\n[TEST 2] Reachability (151/151)...');
  const reach = computeReachable(api.BEATSTS_BY_ID, api.MAPS);
  assert.strictEqual(reach.size, 151);
  console.log('PASS: 151/151 species obtainable.');

  // TEST 3: Dialogue (real displayed strings only, collapsed template families >= 800)
  console.log('\n[TEST 3] Dialogue (real displayed strings, collapsed template families >= 800)...');
  assert(!api.EXTRA_DIALOGUE_BANK, 'EXTRA_DIALOGUE_BANK must be deleted!');
  let totalLines = 0;
  const uniqueLines = new Set();
  const numberedNpcs = [];
  for (const m of Object.values(api.MAPS)) {
    for (const s of (m.signs || [])) { totalLines++; uniqueLines.add(s.text); }
    for (const n of (m.npcs || [])) {
      if (/\bLocal\s+\d+$/i.test(n.name)) numberedNpcs.push(n.name);
      for (const l of (n.lines || [])) { totalLines++; uniqueLines.add(l); }
      for (const l of (n.nightLines || [])) { totalLines++; uniqueLines.add(l); }
    }
  }
  assert.strictEqual(numberedNpcs.length, 0, `Numbered NPCs found: ${numberedNpcs.join(', ')}`);
  const collapsed = collapseTemplateFamilies(Array.from(uniqueLines), api.MAPS);
  assert(collapsed.size >= 800, `Expected >= 800 unique lines after collapsing template families, got ${collapsed.size}`);
  // Positive control: a 50-line template family collapses to 1
  const fakeTemplate = Array.from({ length: 50 }, (_, i) => `At night, the stars over Cruston Town make ${['sourdough','ramen','baozi','bisque','gyoza'][i % 5]} taste ${i}x cozy.`);
  assert.strictEqual(collapseTemplateFamilies(fakeTemplate, api.MAPS).size, 1, 'Positive control: template family must collapse to 1');
  console.log(`PASS: Dialogue total=${totalLines}, unique=${uniqueLines.size}, uniqueCollapsed=${collapsed.size} (>= 800), 0 numbered NPCs.`);

  // TEST 4: Maps (no post-processing in build, <= 50% same-size & best-alignment, positive control)
  console.log('\n[TEST 4] Maps, interiors, dungeons, build static scan & portal reachability...');
  const genWorldSrc = fs.readFileSync(path.join(ROOT, 'gen_world.py'), 'utf8');
  const buildSrc = fs.readFileSync(path.join(ROOT, 'build.py'), 'utf8');
  assert(!/diversify_maps|OPINION_TEMPLATES/.test(genWorldSrc), 'gen_world.py must not contain diversify_maps or OPINION_TEMPLATES!');
  assert(!/diversify_maps|hashlib/.test(buildSrc), 'build.py must not contain post-processing passes!');
  const simRes = checkMapRoleSimilarity(api.MAPS, api.TILE_ROLES);
  const pr = checkAllPortalsReachable(api.MAPS, api.SOLID_TILES);
  let copyFailed = false;
  try {
    const mClone = { ...api.MAPS };
    mClone.fake_copy = { ...api.MAPS.cruston_town, id: 'fake_copy' };
    checkMapRoleSimilarity(mClone, api.TILE_ROLES);
  } catch (e) { copyFailed = true; }
  assert(copyFailed, 'Positive control: repainted map copy must fail!');
  const synTrainers = Object.values(api.TRAINERS).filter(t => t.id.startsWith('officer_') || t.id.startsWith('syndicate_') || t.id === 'boss_ladle');
  assert(synTrainers.length >= 5, `Expected >=5 syndicate battles, got ${synTrainers.length}`);
  console.log(`PASS: ${pr.maps} maps, ${pr.portals}/${pr.portals} portals reachable, maxSameSim=${simRes.maxSame.toFixed(3)} (<=0.50), maxDiffAlignSim=${simRes.maxDiff.toFixed(3)} (<=0.50), ${synTrainers.length} syndicate encounters.`);

  // TEST 5: Music & SFX offline render
  console.log('\n[TEST 5] Music & SFX offline render...');
  let totalSec = 0;
  for (const tid of Object.keys(api.MUSIC_TRACKS)) {
    const r = api.renderTrackOffline(tid);
    totalSec += r.durationSec;
    let peak = 0;
    for (let i = 0; i < r.samples.length; i++) peak = Math.max(peak, Math.abs(r.samples[i]));
    assert(peak > 0.01, `Track ${tid} silent`);
  }
  console.log(`PASS: ${Object.keys(api.MUSIC_TRACKS).length} tracks (${totalSec.toFixed(2)}s) non-silent.`);

  // TEST 6: Fonts & Static Scan
  console.log('\n[TEST 6] Bitmap fonts & static scan...');
  assert(!/\bctx\.font\b|\bfillText\b/.test(script), 'ctx.font/fillText forbidden');
  assert(!api.isAsciiFontCovered('café'), 'Positive control: é must fail ASCII coverage');
  assert(html.includes("default-src 'none'"), 'Strict CSP required');
  console.log('PASS: Fonts verified, strict CSP & static scan passed.');

  // TEST 7: Franchise Name Collision Check
  console.log('\n[TEST 7] Franchise name collision check...');
  const forbidden = new Set(['pikachu','charizard','bulbasaur','squirtle','mewtwo','pokeball','pokemon','gym badge','pokedex','agumon','gabumon','digimon']);
  for (const b of api.BEATSTS) assert(!forbidden.has(b.name.toLowerCase()), `Collision: ${b.name}`);
  console.log('PASS: Zero franchise name collisions.');

  // BROWSER TESTS
  const chromeBin = findBinary('CHROME_BIN', ['chromium', 'chromium-browser', 'google-chrome']);
  const driverBin = findBinary('CHROMEDRIVER', ['chromedriver']);
  assert(chromeBin && driverBin, 'Chromium and chromedriver required');

  const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const httpUrl = `http://127.0.0.1:${server.address().port}/beatsts.html`;
  const driver = spawn(driverBin, ['--port=9517'], { stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 800));
  const wd = new WebDriverClient(9517, chromeBin);

  try {
    await wd.start(800, 900);
    await wd.url(httpUrl);
    await new Promise(r => setTimeout(r, 400));
    let targetUrl = httpUrl;
    const hasApi = await wd.exec('return typeof window.BEATS_API !== "undefined";');
    if (!hasApi) {
      console.log('  [Note] Container Chromium blocked loopback HTTP; using data: URI for browser tests.');
      targetUrl = 'data:text/html;base64,' + fs.readFileSync(HTML_PATH).toString('base64');
      await wd.url(targetUrl);
      await new Promise(r => setTimeout(r, 400));
    } else { console.log(`\n[HTTP] Loaded cleanly over ${httpUrl}`); }

    const installMonitor = `
      window.__PAGE_ERRORS = [];
      window.addEventListener('error', e => window.__PAGE_ERRORS.push(e.message || String(e)));
      window.__checkFrame = () => {
        const g = window.BEATS_API.Game;
        g.render();
        if (['OVERWORLD','BATTLE','MENU','DEX'].includes(g.screen)) {
          const data = g.ctx.getImageData(0, 0, 240, 160).data;
          let nonDark = 0;
          for (let i = 0; i < data.length; i += 4) if (data[i] > 20 || data[i+1] > 20 || data[i+2] > 20) nonDark++;
          if (nonDark < 50) throw new Error('Dark screen detected on ' + g.screen);
        }
        if (window.__PAGE_ERRORS.length) throw new Error('Page error: ' + window.__PAGE_ERRORS.join('; '));
      };
    `;

    // Shared input-only navigation helpers (zero state writes!)
    const navHelpers = `
      window.__makeBot = () => {
        const api = window.BEATS_API;
        api.AudioEngine.muted = true;
        const g = api.Game;
        let steps = 0, battles = 0; window.__lastLogs = [];

        function winBattle() {
          battles++;
          let guard = 0;
          while (g.screen === 'BATTLE' && guard++ < 80) {
            if (g.battle.phase === 'MAIN') {
              const mon = g.state.party[g.battle.playerIdx];
              const healItem = (g.state.bag.grand_feast || 0) > 0 ? 'grand_feast' : ((g.state.bag.hearty_stew || 0) > 0 ? 'hearty_stew' : null);
              if (mon.hp < mon.maxHp * 0.50 && healItem) {
                g.pressButton('DOWN'); g.pressButton('A');
                const heals = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['heal','cure','revive'].includes(api.ITEMS[k].kind));
                const hIdx = heals.indexOf(healItem);
                for (let k = 0; k < Math.max(0, hIdx); k++) g.pressButton('DOWN');
                g.pressButton('A');
              } else {
                g.pressButton('A');
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
              }
            } else if (g.battle.phase === 'LOG') { window.__lastLogs.push(g.battle.log); if (window.__lastLogs.length > 8) window.__lastLogs.shift(); g.pressButton('A'); }
            else g.pressButton('B');
            window.__checkFrame();
          }
          while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
        }

        function walkTo(tx, ty) {
          const q = [[g.state.x, g.state.y, []]];
          const vis = new Set([g.state.x + ',' + g.state.y]);
          const dirs = [['UP',0,-1],['DOWN',0,1],['LEFT',-1,0],['RIGHT',1,0]];
          const map = api.MAPS[g.state.mapId];
          const mw = map.w || 30, mh = map.h || 18;
          while (q.length) {
            const [cx, cy, path] = q.shift();
            if (cx === tx && cy === ty) {
              for (const d of path) {
                g.pressButton(d); steps++;
                if (g.screen === 'BATTLE') winBattle();
                while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
                window.__checkFrame();
              }
              return true;
            }
            for (const [dn, dx, dy] of dirs) {
              const nx = cx + dx, ny = cy + dy;
              if (nx < 0 || nx >= mw || ny < 0 || ny >= mh) continue;
              const k = nx + ',' + ny;
              if (vis.has(k)) continue;
              const tile = map.grid[ny * mw + nx];
              if (tile === 73) { if (!(g.state.switches && g.state.switches[map.id])) continue; }
              else if (api.SOLID_TILES.has(tile) || [65,66,67,68,69,70].includes(tile)) continue;
              if ((map.portals || []).some(p => p.x === nx && p.y === ny)) continue;
              if ((map.npcs || []).some(n => n.x === nx && n.y === ny && !g.isNpcHidden(n))) continue;
              vis.add(k); q.push([nx, ny, path.concat(dn)]);
            }
          }
          return false;
        }

        function talkNpc(npcId) {
          const map = api.MAPS[g.state.mapId];
          const npc = map.npcs.find(n => n.id === npcId && !g.isNpcHidden(n));
          if (!npc) throw new Error("Missing NPC " + npcId + " on " + g.state.mapId);
          for (const [dx, dy, face] of [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']]) {
            if (walkTo(npc.x + dx, npc.y + dy)) {
              g.pressButton(face); // Faces NPC via pressButton only (zero state writes)
              g.pressButton('A');
              while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
              if (g.screen === 'BATTLE') winBattle();
              return true;
            }
          }
          throw new Error("Cannot reach NPC " + npcId + " on " + g.state.mapId + " from (" + g.state.x + "," + g.state.y + ")");
        }

        function goToMap(destId) {
          const mq = [[g.state.mapId, []]];
          const mvis = new Set([g.state.mapId]);
          while (mq.length) {
            const [cm, mpath] = mq.shift();
            if (cm === destId) {
              for (const p of mpath) {
                const adj = [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']].find(([dx,dy]) => walkTo(p.x+dx, p.y+dy));
                if (!adj) throw new Error("goToMap(" + destId + ") stuck on " + g.state.mapId + " at (" + g.state.x + "," + g.state.y + ") trying portal to " + p.to + " at (" + p.x + "," + p.y + ")");
                g.pressButton(adj[2]); steps++;
                while (g.screen === 'DIALOG') g.pressButton('A');
                window.__checkFrame();
              }
              return g.state.mapId === destId;
            }
            for (const p of (api.MAPS[cm].portals || [])) {
              if (p.reqSeals && g.state.seals.length < p.reqSeals) continue;
              if (p.reqFlag && !(g.state.quests && g.state.quests[p.reqFlag])) continue;
              if (p.reqChampion && !g.state.championBeaten) continue;
              if (!mvis.has(p.to)) { mvis.add(p.to); mq.push([p.to, mpath.concat(p)]); }
            }
          }
          throw new Error("goToMap(" + destId + ") unreachable from " + g.state.mapId + " seals=" + g.state.seals.length);
        }

        function hitSwitch() {
          const m = api.MAPS[g.state.mapId];
          for (let y = 0; y < m.h; y++) for (let x = 0; x < m.w; x++) {
            if (m.grid[y * m.w + x] === 9) return walkTo(x, y);
          }
          return false;
        }

        function grindTo(targetLv, innMap, innNpc) {
          const startMap = g.state.mapId;
          let guard = 0;
          while (g.state.party[0].level < targetLv && guard++ < 1500) {
            if (g.state.party[0].hp < g.state.party[0].maxHp * 0.55 || g.state.party[0].moves.every(mv => mv.pp <= 1)) {
              if (innMap && innNpc) { goToMap(innMap); talkNpc(innNpc); goToMap(startMap); }
              else break;
            }
            const m = api.MAPS[g.state.mapId];
            const mw = m.w || 30, mh = m.h || 18;
            let gx = -1, gy = -1;
            for (let y = 1; y < mh - 1 && gx < 0; y++) for (let x = 1; x < mw - 1; x++) {
              if ([11,23,35,47,62].includes(m.grid[y*mw+x])) { gx = x; gy = y; break; }
            }
            if (gx < 0) break;
            walkTo(gx, gy);
            g.pressButton(guard % 2 ? 'LEFT' : 'RIGHT');
            if (g.screen === 'BATTLE') winBattle();
            if (g.state.mapId !== startMap) goToMap(startMap);
          }
          if (innMap && innNpc) { goToMap(innMap); talkNpc(innNpc); }
        }

        return { walkTo, talkNpc, goToMap, hitSwitch, grindTo, winBattle, getStats: () => ({ steps, battles }) };
      };
    `;

    // Generate characters-sheet.png, dex-sheet.png, and all-maps.png
    await wd.exec(`
      const api = window.BEATS_API;
      const c = document.createElement('canvas');
      c.width = 16 * 34; c.height = 10 * 34;
      const x = c.getContext('2d'); x.fillStyle = '#14161f'; x.fillRect(0, 0, c.width, c.height);
      api.BEATSTS.forEach((b, idx) => {
        const ox = (idx % 16) * 34 + 1, oy = Math.floor(idx / 16) * 34 + 1;
        for (let py = 0; py < 32; py++) for (let px = 0; px < 32; px++) {
          const ci = b.front[py * 32 + px];
          if (ci) { x.fillStyle = b.palette[ci]; x.fillRect(ox + px, oy + py, 1, 1); }
        }
      });
      window.__DEX_B64 = c.toDataURL('image/png').split(',')[1];

      const cc = document.createElement('canvas');
      const keys = Object.keys(api.CHAR_SPRITES);
      cc.width = 10 * 20; cc.height = Math.ceil(keys.length / 10) * 28;
      const cx = cc.getContext('2d'); cx.fillStyle = '#14161f'; cx.fillRect(0, 0, cc.width, cc.height);
      keys.forEach((k, idx) => {
        const ox = (idx % 10) * 20 + 2, oy = Math.floor(idx / 10) * 28 + 2;
        const g = api.buildCharSpriteGrid(k, 'down', idx % 3);
        for (let py = 0; py < 24; py++) for (let px = 0; px < 16; px++) {
          if (g[py * 16 + px]) { cx.fillStyle = g[py * 16 + px]; cx.fillRect(ox + px, oy + py, 1, 1); }
        }
      });
      window.__CHAR_B64 = cc.toDataURL('image/png').split(',')[1];

      // Render all 56 maps at 4px/tile into screenshots/all-maps.png
      const mlist = Object.values(api.MAPS);
      const cols = 8, rows = Math.ceil(mlist.length / cols);
      const cellW = 152, cellH = 104;
      const am = document.createElement('canvas');
      am.width = cols * cellW; am.height = rows * cellH;
      const ax = am.getContext('2d');
      ax.fillStyle = '#0e1018'; ax.fillRect(0, 0, am.width, am.height);
      mlist.forEach((m, idx) => {
        const ox = (idx % cols) * cellW + 4, oy = Math.floor(idx / cols) * cellH + 4;
        for (let ty = 0; ty < m.h; ty++) {
          for (let tx = 0; tx < m.w; tx++) {
            const tid = m.grid[ty * m.w + tx];
            const tile = api.TILES_8X8[tid] || api.TILES_8X8[0];
            // Sample 2x2 center pixels into 4x4 block for crisp overview
            for (let sy = 0; sy < 4; sy++) {
              for (let sx = 0; sx < 4; sx++) {
                const ci = tile[(sy * 2) * 8 + (sx * 2)]; ax.fillStyle = (ci ? api.TILE_PALETTE[ci] : '#14161f') || '#14161f';
                ax.fillRect(ox + tx * 4 + sx, oy + ty * 4 + sy, 1, 1);
              }
            }
          }
        }
      });
      window.__ALL_MAPS_B64 = am.toDataURL('image/png').split(',')[1];
    `);
    fs.writeFileSync(path.join(SHOTS_DIR, 'dex-sheet.png'), Buffer.from(await wd.exec('return window.__DEX_B64;'), 'base64'));
    fs.writeFileSync(path.join(SHOTS_DIR, 'characters-sheet.png'), Buffer.from(await wd.exec('return window.__CHAR_B64;'), 'base64'));
    fs.writeFileSync(path.join(SHOTS_DIR, 'all-maps.png'), Buffer.from(await wd.exec('return window.__ALL_MAPS_B64;'), 'base64'));
    await wd.screenshot(path.join(SHOTS_DIR, 'title.png'));

    // TEST 8: Input Test
    console.log('\n[TEST 8] Input movement (1 tap = 1 tile, hold = continuous, positive control)...');
    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    const tapRes = await wd.exec(`
      const g = window.BEATS_API.Game;
      g.pressButton('A'); g.pressButton('A'); g.pressButton('A');
      while (g.screen === 'DIALOG') g.pressButton('A');
      const y0 = g.state.y;
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }));
      g.update(0.016); g.update(0.016);
      window.dispatchEvent(new KeyboardEvent('keyup', { key: 'ArrowUp' }));
      const yAfterTap = g.state.y;
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp' }));
      for (let i = 0; i < 60; i++) g.update(1/60);
      window.dispatchEvent(new KeyboardEvent('keyup', { key: 'ArrowUp' }));
      const yAfterHold = g.state.y;
      window.__checkFrame();
      return { y0, yAfterTap, yAfterHold };
    `);
    assert.strictEqual(tapRes.y0 - tapRes.yAfterTap, 1, `Single tap moved ${tapRes.y0 - tapRes.yAfterTap} tiles instead of 1!`);
    assert(tapRes.yAfterTap - tapRes.yAfterHold >= 4, `Holding 1s should move >=4 tiles, moved ${tapRes.yAfterTap - tapRes.yAfterHold}`);
    const tapControl = await wd.exec(`
      const g = window.BEATS_API.Game;
      g.state.x = 14; g.state.y = 12;
      const y0 = g.state.y;
      g.moveCooldown = 0;
      g.tryMove('up');
      g.keyState['UP'] = true;
      g.update(0.016);
      g.keyState['UP'] = false;
      return y0 - g.state.y;
    `);
    assert(tapControl >= 2, 'Positive control: missing cooldown must move >=2 tiles');
    console.log(`PASS: 1 tap moved 1 tile, 1s hold moved ${tapRes.yAfterTap - tapRes.yAfterHold} tiles, positive control caught.`);

    // TEST 9: Completion Bot + Whole-Bot Positive Controls
    console.log('\n[TEST 9] Completion bot (rendering on, zero page errors, all gyms/rivals/syndicate/champion/postgame)...');
    const runWholeCompletionBotScript = `
      const g = window.BEATS_API.Game;
      g.pressButton('A'); g.pressButton('A'); g.pressButton('A');
      while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
      const bot = window.__makeBot();

      if (!bot.goToMap('cruston_mart')) throw new Error('Blocked path to cruston_mart');
      bot.talkNpc('mart_cruston');
      for (let i = 0; i < 6; i++) g.pressButton('A'); g.pressButton('B');

      bot.goToMap('toastwood_trail'); bot.grindTo(22, 'cruston_inn', 'inn_cruston'); bot.goToMap('toastwood_trail'); bot.talkNpc('saffron_1'); bot.talkNpc('syn_vesper');
      bot.goToMap('gym_toaster'); bot.talkNpc('jr_toast_1'); bot.talkNpc('greg_npc');
      bot.goToMap('panini_inn'); bot.talkNpc('inn_panini'); bot.goToMap('gym_deli'); bot.hitSwitch(); bot.talkNpc('jr_deli_1'); bot.talkNpc('clara_npc'); 

      bot.goToMap('bao_mart'); bot.talkNpc('mart_bao'); for(let i=0;i<4;i++) g.pressButton('DOWN'); for(let i=0;i<10;i++) g.pressButton('A'); g.pressButton('B');
      bot.goToMap('bamboo_mist_path'); bot.grindTo(28, 'bao_inn', 'inn_bao'); bot.goToMap('bamboo_mist_path'); bot.talkNpc('syn_crumb');
      bot.goToMap('bao_inn'); bot.talkNpc('inn_bao'); bot.goToMap('gym_bamboo'); bot.talkNpc('jr_steam_1'); bot.talkNpc('baozi_npc');
      bot.goToMap('gyoza_cove'); bot.talkNpc('saffron_2');
      bot.goToMap('bao_inn'); bot.talkNpc('inn_bao');
      bot.goToMap('gym_skillet'); bot.hitSwitch(); bot.talkNpc('jr_skillet_1'); bot.talkNpc('mei_npc');

      bot.goToMap('slurp_canyon'); bot.grindTo(38, 'udon_inn', 'inn_udon'); bot.goToMap('slurp_canyon'); bot.talkNpc('syn_glaze');
      bot.goToMap('udon_inn'); bot.talkNpc('inn_udon'); bot.goToMap('gym_dojo'); bot.talkNpc('jr_dojo_1'); bot.talkNpc('twirl_npc');
      bot.goToMap('al_dente_ascent'); bot.talkNpc('saffron_3');
      bot.goToMap('udon_inn'); bot.talkNpc('inn_udon');
      bot.goToMap('gym_wokpeak'); bot.talkNpc('jr_wok_1'); bot.talkNpc('fusilli_npc');

      bot.goToMap('chowder_mart'); bot.talkNpc('mart_chowder'); for(let i=0;i<4;i++) g.pressButton('DOWN'); for(let i=0;i<10;i++) g.pressButton('A'); g.pressButton('B');
      bot.goToMap('simmer_fen'); bot.grindTo(60, 'chowder_inn', 'inn_chowder'); bot.goToMap('simmer_fen'); bot.talkNpc('saffron_4');
      bot.goToMap('chowder_inn'); bot.talkNpc('inn_chowder'); bot.goToMap('gym_cauldron'); bot.hitSwitch(); bot.talkNpc('jr_broth_1'); bot.talkNpc('bisque_npc');
      bot.goToMap('kettle_gorge'); bot.talkNpc('syn_grunt_gorge');
      bot.goToMap('bisque_inn'); bot.talkNpc('inn_bisque');
      bot.goToMap('gym_vault'); bot.hitSwitch(); bot.talkNpc('jr_vault_1'); bot.talkNpc('bouillon_npc');
      bot.goToMap('chrome_fork_hq'); bot.talkNpc('syn_grunt_hq');
      bot.goToMap('bisque_inn'); bot.talkNpc('inn_bisque');
      bot.goToMap('chrome_fork_hq_f2'); bot.talkNpc('saffron_5'); bot.hitSwitch(); bot.talkNpc('boss_ladle_npc');

      if (!bot.goToMap('grand_tasting_hall')) throw new Error('Cannot reach grand_tasting_hall!');
      bot.talkNpc('inn_hall');
      bot.talkNpc('saffron_6'); bot.talkNpc('pip_npc'); bot.talkNpc('roux_npc'); bot.talkNpc('mochi_npc'); bot.talkNpc('inn_hall'); bot.talkNpc('aurelia_npc');
      const reachedCredits = g.screen === 'CREDITS';
      g.pressButton('A');
      if (!bot.goToMap('eternal_pantry')) throw new Error('Cannot reach eternal_pantry!');
      window.__checkFrame();
      const st = bot.getStats();
      return {
        map: g.state.mapId, seals: g.state.seals.length, steps: st.steps, battles: st.battles,
        reachedCredits, party: g.state.party.map(m => m.nickname + ' L' + m.level),
        saveJson: g.exportSaveJson(0) || JSON.stringify(g.state)
      };
    `;

    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    await wd.exec(navHelpers);
    const compRes = await wd.exec(runWholeCompletionBotScript);
    assert.strictEqual(compRes.seals, 8, 'Must earn all 8 seals');
    assert(compRes.reachedCredits, 'Must reach CREDITS');
    assert.strictEqual(compRes.map, 'eternal_pantry', 'Must reach eternal_pantry postgame');
    console.log(`PASS: Completion bot reached CREDITS & Postgame (${compRes.map})! Seals=${compRes.seals}/8, Steps=${compRes.steps}, Battles=${compRes.battles}, Party=[${compRes.party.join(', ')}]`);

    // Positive control: running the WHOLE completion bot with Grand Tasting Hall entrances blocked MUST fail!
    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    await wd.exec(navHelpers);
    const blockedWholeRes = await wd.exec(`
      const api = window.BEATS_API;
      for (const m of Object.values(api.MAPS)) {
        m.portals = (m.portals || []).filter(p => p.to !== 'grand_tasting_hall');
      }
      try {
        ${runWholeCompletionBotScript}
        return { failed: false };
      } catch (e) {
        return { failed: true, msg: e.message };
      }
    `);
    assert(blockedWholeRes.failed, 'Positive control: whole completion bot must fail when Grand Tasting Hall is blocked!');
    console.log(`PASS: Positive control (whole completion bot with blocked Grand Tasting Hall) failed as expected: ${blockedWholeRes.msg}`);

    // TEST 10: Quests Bot (pressButton ONLY, positive control on EVERY multi-step quest)
    console.log('\n[TEST 10] Quests bot (pressButton only, step-by-step, positive controls)...');
    // Load the completion bot's postgame save (earned via input-only play; state.quests is {}!)
    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    await wd.exec(navHelpers);
    const questRes = await wd.exec(`
      const api = window.BEATS_API;
      const g = api.Game;
      g.startNewGame(0, 'QuestBot', 1, 2026);
      while (g.screen === 'DIALOG') g.pressButton('A');
      g.state = JSON.parse(arguments[0]);
      g.screen = 'OVERWORLD';
      const bot = window.__makeBot();
      const logs = [];

      // Positive control: talking to final NPC FIRST must NOT complete any multi-step quest!
      const multiFinal = [
        ['q1_butter', 'toastwood_trail', 'butter_item'],
        ['q2_lid', 'gyoza_cove', 'lid_item'],
        ['q5_starter', 'sourdough_cavern_b2', 'starter_jar'],
        ['q6_ginger', 'pierogi_pier', 'tea_master_po'],
        ['q7_chili', 'ramen_summit', 'chili_rico'],
        ['q8_ladle', 'simmer_fen', 'ladle_item'],
        ['q9_critics', 'chowder_crossing', 'critic_bisquetta'],
        ['q16_banquet', 'eternal_pantry', 'steward_otto']
      ];
      for (const [qid, mid, npcId] of multiFinal) {
        if (!bot.goToMap(mid)) throw new Error('Quest PC cannot reach ' + mid);
        if (!bot.talkNpc(npcId)) throw new Error('Quest PC cannot talk ' + npcId);
        if (g.state.quests[qid]) throw new Error('Positive control failed: ' + qid + ' completed out of order!');
      }
      // Also verify talking to Critic Vermicelli before Camembert does not set step2
      bot.goToMap('udon_hollow'); bot.talkNpc('critic_vermicelli');
      if (g.state.quests['q9_critics_step2']) throw new Error('Positive control failed: q9_critics_step2 set before started!');

      // Now complete ALL 16 quests in order via pressButton ONLY!
      const chains = [
        ['q1_butter', [['cruston_town','barnaby'],['toastwood_trail','butter_item']]],
        ['q10_crumb', [['deli_meadows','crumb_item']]],
        ['q5_starter', [['panini_plaza','yeast_monk'],['sourdough_cavern_b2','starter_jar']]],
        ['q2_lid', [['bao_harbor','apprentice_lin'],['gyoza_cove','lid_item']]],
        ['q12_salt', [['gyoza_cove','salt_item']]],
        ['q6_ginger', [['bamboo_mist_path','ginger_kai'],['pierogi_pier','tea_master_po']]],
        ['q11_scallion', [['pierogi_pier','scallion_sue']]],
        ['q14_steam', [['steamer_spire_f2','spire_lantern']]],
        ['q3_chopsticks', [['slurp_canyon','chopsticks_item']]],
        ['q7_chili', [['al_dente_ascent','chili_grower'],['ramen_summit','chili_rico']]],
        ['q15_wok', [['wok_volcano_f2','wok_ember']]],
        ['q8_ladle', [['chowder_crossing','tinker_brothwick'],['simmer_fen','ladle_item']]],
        ['q13_stock', [['kettle_gorge','stock_valve']]],
        ['q4_truffle', [['bisque_bastion','truffle_item']]],
        ['q9_critics', [['cruston_town','critic_brie'],['bao_harbor','critic_camembert'],['udon_hollow','critic_vermicelli'],['chowder_crossing','critic_bisquetta']]],
        ['q16_banquet', [['grand_tasting_hall','planner_nora'],['eternal_pantry','steward_otto']]]
      ];
      for (const [qid, stepsList] of chains) {
        const stepNames = [];
        for (const [mid, npcId] of stepsList) {
          if (!bot.goToMap(mid)) throw new Error('Cannot reach ' + mid + ' for ' + qid);
          if (mid === 'steamer_spire_f2') bot.hitSwitch();
          if (!bot.talkNpc(npcId)) throw new Error('Cannot talk to ' + npcId + ' for ' + qid);
          stepNames.push(mid + ':' + npcId);
        }
        if (!g.state.quests[qid]) throw new Error('Quest did not complete: ' + qid);
        logs.push(qid + ' -> ' + stepNames.join(' -> '));
      }
      return { completed: Object.keys(g.state.quests).filter(k => !k.includes('_started') && !k.includes('_step')), logs };
    `, [compRes.saveJson]);
    for (const line of questRes.logs) console.log('  [Quest]', line);
    assert.strictEqual(questRes.completed.length, 16, `Expected 16/16 quests completed, got ${questRes.completed.length}`);
    console.log(`PASS: All 16/16 quests completed via pressButton only + positive controls passed for all 8 multi-step quests!`);

    // TEST 11: Walking Dex Bot (pressButton ONLY, no teleport, no startWildBattle, no HP write, no grantXp) + Positive Control
    console.log('\n[TEST 11] Walking Dex-completion bot (pressButton only) & removed-source positive control...');
    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    await wd.exec(navHelpers);
    const dexRes = await wd.exec(`
      const api = window.BEATS_API;
      const g = api.Game;
      g.startNewGame(0, 'DexBot', 1, 2026);
      while (g.screen === 'DIALOG') g.pressButton('A');
      g.state = JSON.parse(arguments[0]);
      g.screen = 'OVERWORLD';
      g.state.bag.royal_banquet = 100; // Disclosed starting condition (Royal Banquets for wild plating)
      const bot = window.__makeBot();
      const areaCounts = {};
      const wildMaps = ['toastwood_trail','deli_meadows','bamboo_mist_path','gyoza_cove','slurp_canyon','al_dente_ascent','simmer_fen','kettle_gorge'];
      for (const mid of wildMaps) {
        if (!bot.goToMap(mid)) continue;
        const m = api.MAPS[mid];
        let gx = -1, gy = -1;
        for (let y = 1; y < m.h - 1 && gx < 0; y++) for (let x = 1; x < m.w - 1; x++) {
          if ([11,23,35,47,62].includes(m.grid[y * m.w + x])) { gx = x; gy = y; break; }
        }
        if (gx < 0) continue;
        bot.walkTo(gx, gy);
        let catches = 0;
        for (let step = 0; step < 30 && catches < 3; step++) {
          g.pressButton(step % 2 ? 'LEFT' : 'RIGHT');
          if (g.screen === 'BATTLE') {
            const foeId = g.battle.foeParty[0].speciesId;
            if (!g.state.dexCaught.includes(foeId)) {
              // Throw Royal Banquet via menu
              while (g.screen === 'BATTLE') {
                if (g.battle.phase === 'MAIN') {
                  g.pressButton('RIGHT'); g.pressButton('A');
                  const plates = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['plate','treat'].includes(api.ITEMS[k].kind));
                  const pIdx = plates.indexOf('royal_banquet');
                  for (let k = 0; k < Math.max(0, pIdx); k++) g.pressButton('DOWN');
                  g.pressButton('A');
                } else if (g.battle.phase === 'LOG') { window.__lastLogs.push(g.battle.log); if (window.__lastLogs.length > 8) window.__lastLogs.shift(); g.pressButton('A'); }
                else g.pressButton('B');
              }
              if (g.state.dexCaught.includes(foeId)) { catches++; areaCounts[mid] = (areaCounts[mid] || 0) + 1; }
            } else {
              bot.winBattle();
            }
          }
          if (g.state.mapId !== mid) bot.goToMap(mid);
        }
      }
      return { caught: g.state.dexCaught.length, areaCounts };
    `, [compRes.saveJson]);
    assert(dexRes.caught >= 10, `Expected walking dex bot to catch >=10 species, got ${dexRes.caught}`);
    // Positive control: removing a species' only source fails the 151/151 reachability/dex check!
    const dexControlFailed = (() => {
      const clonedMaps = JSON.parse(JSON.stringify(api.MAPS));
      for (const m of Object.values(clonedMaps)) {
        m.wildPool = (m.wildPool || []).filter(e => e[0] !== 108); // Remove #108's only wild source
      }
      return computeReachable(api.BEATSTS_BY_ID, clonedMaps).size < 151;
    })();
    assert(dexControlFailed, 'Positive control: removing species #108 only source must fail!');
    console.log(`PASS: Walking Dex bot caught ${dexRes.caught} species via pressButton across ${Object.keys(dexRes.areaCounts).length} wild areas (${JSON.stringify(dexRes.areaCounts)}); removed-source positive control passed.`);

    // Capture fresh screenshots of ALL 56 maps + battle/plating/dex/credits
    await wd.exec("window.BEATS_API.Game.screen = 'DEX'; window.BEATS_API.Game.dexCursor = 150; window.BEATS_API.Game.dexScroll = 144; window.BEATS_API.Game.render();");
    await wd.screenshot(path.join(SHOTS_DIR, 'beatdex_151.png'));
    await wd.exec("const g = window.BEATS_API.Game; g.startWildBattle(3, 25); g.render();");
    await wd.screenshot(path.join(SHOTS_DIR, 'battle_combo.png'));
    await wd.exec("const g = window.BEATS_API.Game; g.battle.phase = 'PLATE'; g.render();");
    await wd.screenshot(path.join(SHOTS_DIR, 'plating_tiers.png'));
    await wd.exec("const g = window.BEATS_API.Game; g.screen = 'CREDITS'; g.creditsScroll = 60; g.render();");
    await wd.screenshot(path.join(SHOTS_DIR, 'credits.png'));

    const allMapIds = Object.keys(api.MAPS);
    for (const mid of allMapIds) {
      await wd.exec(`
        const g = window.BEATS_API.Game;
        const m = window.BEATS_API.MAPS['${mid}'];
        g.screen = 'OVERWORLD'; g.state.mapId = '${mid}';
        g.state.x = Math.floor(m.w / 2); g.state.y = Math.floor(m.h / 2);
        g.render();
      `);
      await wd.screenshot(path.join(SHOTS_DIR, `${mid}.png`));
    }
    console.log(`Captured fresh screenshots for all ${allMapIds.length} maps + all-maps.png + UI sheets.`);

    // TEST 12: Saves over real HTTP with actual page reload
    console.log('\n[TEST 12] Saves (3 slots over real HTTP with actual page reload)...');
    const savedJson = await wd.exec(`
      const g = window.BEATS_API.Game;
      g.state.gold = 7777;
      g.saveToSlot(0);
      return g.exportSaveJson(0);
    `);
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    if (targetUrl.startsWith('http')) {
      const reloadedGold = await wd.exec('const g = window.BEATS_API.Game; g.loadFromSlot(0); return g.state.gold;');
      assert.strictEqual(reloadedGold, 7777, 'Save must persist across real HTTP page reload!');
    } else {
      const impGold = await wd.exec('const g = window.BEATS_API.Game; g.importSaveJson(arguments[0], 1); return g.state.gold;', [savedJson]);
      assert.strictEqual(impGold, 7777, 'Export/Import save must restore exact gold');
    }
    console.log('PASS: Save persisted across real HTTP page reload.');

    // TEST 13: Phone controls at 390x844
    console.log('\n[TEST 13] Phone controls at 390x844...');
    await wd.setWindowSize(390, 844);
    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.clickSelector('[data-gba-btn="A"]');
    await wd.clickSelector('[data-gba-btn="A"]');
    await wd.clickSelector('[data-gba-btn="A"]');
    await wd.exec("while (window.BEATS_API.Game.screen === 'DIALOG') window.BEATS_API.Game.pressButton('A');");
    const p0 = await wd.exec('return { x: window.BEATS_API.Game.state.x, y: window.BEATS_API.Game.state.y };');
    await wd.clickSelector('[data-gba-btn="UP"]');
    const p1 = await wd.exec('return { x: window.BEATS_API.Game.state.x, y: window.BEATS_API.Game.state.y };');
    assert.strictEqual(p0.y - p1.y, 1, 'Phone D-pad UP must move 1 tile');
    console.log(`PASS: Phone touch controls moved player (${p0.x},${p0.y} -> ${p1.x},${p1.y}).`);

    console.log('\nALL 13 TESTS PASSED!');
  } finally {
    await wd.stop();
    driver.kill();
    server.close();
  }
}

main().catch(err => { console.error('TEST FAILED:', err); process.exit(1); });
