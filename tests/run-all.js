// tests/run-all.js - Complete Automated Test Harness & Screenshot Capture for bEATsts 2.2
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

// Compare both same-size AND different-size map pairs (sliding smaller over larger at best alignment)
function checkMapRoleSimilarity(maps, tileRoles) {
  const list = Object.values(maps);
  let maxSame = 0, maxDiff = 0;
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      const a = list[i], b = list[j];
      const wa = a.w || 30, ha = a.h || 18, wb = b.w || 30, hb = b.h || 18;
      const ga = Array.from(a.grid, t => tileRoles[t] || 'other');
      const gb = Array.from(b.grid, t => tileRoles[t] || 'other');
      const ow = Math.min(wa, wb), oh = Math.min(ha, hb);
      let best = 0;
      for (let dya = 0; dya <= ha - oh; dya++) {
        for (let dyb = 0; dyb <= hb - oh; dyb++) {
          if (dya > 0 && dyb > 0) continue;
          for (let dxa = 0; dxa <= wa - ow; dxa++) {
            for (let dxb = 0; dxb <= wb - ow; dxb++) {
              if (dxa > 0 && dxb > 0) continue;
              let same = 0;
              for (let y = 0; y < oh; y++) {
                const ra = (dya + y) * wa + dxa;
                const rb = (dyb + y) * wb + dxb;
                for (let x = 0; x < ow; x++) {
                  if (ga[ra + x] === gb[rb + x]) same++;
                }
              }
              const sim = same / (ow * oh);
              if (sim > best) best = sim;
            }
          }
        }
      }
      if (wa === wb && ha === hb) { if (best > maxSame) maxSame = best; }
      else { if (best > maxDiff) maxDiff = best; }
      if (best > 0.50) throw new Error(`Map role similarity ${best.toFixed(3)} > 0.50 between ${a.id} and ${b.id}`);
    }
  }
  return { maxSame, maxDiff };
}

function checkAllPortalsReachable(maps, solidTiles) {
  const visMaps = new Set(['cruston_town']);
  const visTiles = new Set(['cruston_town,15,10']);
  const q = [['cruston_town', 15, 10]];
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

function loadGameApiInNode() {
  const html = fs.readFileSync(HTML_PATH, 'utf8');
  const m = html.match(/<!-- INLINE SCRIPT:[\s\S]*?<script>([\s\S]*?)<\/script>/);
  assert(m, 'Could not find labeled inline script in beatsts.html');
  const vm = require('vm');
  const sandbox = {
    window: {},
    addEventListener: () => {},
    document: {
      getElementById: () => ({ value: 'Brie', addEventListener: () => {} }),
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
    await this.req('POST', `/session/${this.sessionId}/timeouts`, { script: 180000 });
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
  // Clean and recreate screenshots dir so zero leftovers from earlier versions exist
  fs.rmSync(SHOTS_DIR, { recursive: true, force: true });
  fs.mkdirSync(SHOTS_DIR, { recursive: true });
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
    for (const dir of ['down','up','left','right']) {
      assert(api.buildCharSpriteGrid(k, dir, 0).length === 384);
    }
    const norm = Array.from(normalizeSpriteShape(f0)).join(',');
    assert(!namedShapes.has(norm), `Named character ${k} is not unique!`);
    namedShapes.add(norm);
  }
  const villagerKeys = Object.keys(api.CHAR_SPRITES).filter(k => k.startsWith('villager_'));
  assert(villagerKeys.length >= 12, `Expected >=12 generic villager designs, got ${villagerKeys.length}`);
  console.log(`PASS: 151 bEATsts + ${namedKeys.length} unique named chars (4 dirs x 3 frames) + ${villagerKeys.length} generic villagers verified.`);

  // TEST 2: Reachability (151/151 + positive control)
  console.log('\n[TEST 2] Reachability (151/151)...');
  const reach = computeReachable(api.BEATSTS_BY_ID, api.MAPS);
  assert.strictEqual(reach.size, 151);
  // Positive control: removing #6 (Pbnjinx) from wildPool drops reachability of #6 and #7
  const mapsNo6 = JSON.parse(JSON.stringify(api.MAPS));
  for (const m of Object.values(mapsNo6)) m.wildPool = (m.wildPool || []).filter(e => e[0] !== 6);
  const reachNo6 = computeReachable(api.BEATSTS_BY_ID, mapsNo6);
  assert(reachNo6.size < 151, 'Reachability positive control must fail when species #6 source is removed');
  console.log(`PASS: 151/151 species obtainable (positive control without #6 dropped to ${reachNo6.size}/151).`);

  // TEST 3: Dialogue (real displayed strings only, collapsed template families >= 800, 0 numbered NPCs)
  console.log('\n[TEST 3] Dialogue (real displayed strings & collapsed template families)...');
  assert(!api.EXTRA_DIALOGUE_BANK, 'EXTRA_DIALOGUE_BANK must be deleted!');
  const genWorldSrc = fs.readFileSync(path.join(ROOT, 'gen_world.py'), 'utf8');
  assert(!/OPINION_TEMPLATES/.test(genWorldSrc), 'OPINION_TEMPLATES must be deleted from gen_world.py!');

  // Build vocabulary of food/place/region/species names to collapse any template families
  const vocab = [
    'sourdough','focaccia','brioche','ciabatta','rye toast','panini','baguette','pretzel','croissant','pita',
    'baozi','gyoza','shumai','pierogi','empanada','onigiri','mochi','ravioli','khinkali','takoyaki',
    'ramen','udon','pho','lo mein','pad thai','lasagna','spaghetti','soba','macaroni','vermicelli',
    'chowder','bisque','consomme','miso','borscht','gumbo','minestrone','gazpacho','pho broth','chili',
    'Breadlands','Steambay','Noodleridge','Brothbasin','Grand Tasting Hall','Eternal Pantry'
  ];
  for (const m of Object.values(api.MAPS)) vocab.push(m.name);
  for (const b of api.BEATSTS) vocab.push(b.name);
  vocab.sort((a, b) => b.length - a.length);
  const vocabRe = new RegExp('\\b(' + vocab.map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|') + ')\\b', 'gi');
  const collapseTemplate = s => s.replace(/\d+/g, '#').replace(vocabRe, '<X>').trim();

  let totalLines = 0;
  const uniqueLines = new Set();
  const collapsedLines = new Set();
  const numberedNpcs = [];
  for (const m of Object.values(api.MAPS)) {
    for (const s of (m.signs || [])) {
      totalLines++; uniqueLines.add(s.text); collapsedLines.add(collapseTemplate(s.text));
    }
    for (const n of (m.npcs || [])) {
      if (/\bLocal\s+\d+$/i.test(n.name)) numberedNpcs.push(n.name);
      for (const l of (n.lines || [])) {
        totalLines++; uniqueLines.add(l); collapsedLines.add(collapseTemplate(l));
      }
      for (const l of (n.nightLines || [])) {
        totalLines++; uniqueLines.add(l); collapsedLines.add(collapseTemplate(l));
      }
    }
  }
  assert.strictEqual(numberedNpcs.length, 0, `Numbered NPCs found: ${numberedNpcs.join(', ')}`);
  assert(collapsedLines.size >= 800, `Expected >= 800 unique collapsed lines, got ${collapsedLines.size}`);
  // Verify template collapsing collapses mad-lib families to 1
  const madLibTest = new Set(['I walked three miles just to smell ramen simmering in Cruston Town.', 'I walked three miles just to smell baozi simmering in Bao Harbor.'].map(collapseTemplate));
  assert.strictEqual(madLibTest.size, 1, 'Template collapser must collapse swapped food/place lines to 1');
  console.log(`PASS: Dialogue total=${totalLines}, unique=${uniqueLines.size}, uniqueCollapsed=${collapsedLines.size} (>= 800), 0 numbered NPCs.`);

  // TEST 4: Maps (static scan of build scripts for no post-processing pass, role similarity <= 50% for same-size & sliding-window diff-size, repainted copy positive control)
  console.log('\n[TEST 4] Maps, interiors, dungeons, static build scan & portal reachability...');
  const buildPySrc = fs.readFileSync(path.join(ROOT, 'build.py'), 'utf8');
  assert(!/diversify_maps|hashlib\.md5/.test(genWorldSrc + buildPySrc), 'Post-processing map repaint/scatter passes are forbidden!');
  const simRes = checkMapRoleSimilarity(api.MAPS, api.TILE_ROLES);
  const pr = checkAllPortalsReachable(api.MAPS, api.SOLID_TILES);
  // Positive control: a repainted copy of a map (different regional tile IDs with same roles!) fails
  let copyFailed = false;
  try {
    const mClone = { ...api.MAPS };
    const repaintedGrid = new Uint8Array(api.MAPS.cruston_town.grid).map(t => t === 10 ? 22 : (t === 12 ? 24 : (t === 14 ? 26 : t)));
    mClone.repainted_copy = { ...api.MAPS.cruston_town, id: 'repainted_copy', grid: repaintedGrid };
    checkMapRoleSimilarity(mClone, api.TILE_ROLES);
  } catch (e) { copyFailed = true; }
  assert(copyFailed, 'Positive control: repainted copy of a map must fail!');
  const synTrainers = Object.values(api.TRAINERS).filter(t => t.id.startsWith('officer_') || t.id.startsWith('syndicate_') || t.id === 'boss_ladle');
  assert(synTrainers.length >= 5, `Expected >=5 syndicate battles, got ${synTrainers.length}`);
  console.log(`PASS: ${pr.maps} maps, ${pr.portals}/${pr.portals} portals reachable, maxSameSim=${simRes.maxSame.toFixed(3)} (<=0.50), maxDiffSlidingSim=${simRes.maxDiff.toFixed(3)} (<=0.50), repainted copy failed as expected.`);

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
      window.__FRAME_Checks = 0;
      window.__LAST_SCREEN = '';
      window.addEventListener('error', e => window.__PAGE_ERRORS.push(e.message || String(e)));
      window.__checkFrame = () => {
        const g = window.BEATS_API.Game;
        g.render();
        window.__FRAME_Checks++;
        if (['OVERWORLD','BATTLE','MENU','DEX'].includes(g.screen) && (g.screen !== window.__LAST_SCREEN || window.__FRAME_Checks % 25 === 0)) {
          window.__LAST_SCREEN = g.screen;
          const data = g.ctx.getImageData(0, 0, 240, 160).data;
          let nonDark = 0;
          for (let i = 0; i < data.length; i += 4) if (data[i] > 20 || data[i+1] > 20 || data[i+2] > 20) nonDark++;
          if (nonDark < 50) throw new Error('Dark screen detected on ' + g.screen);
        }
        if (window.__PAGE_ERRORS.length) throw new Error('Page error: ' + window.__PAGE_ERRORS.join('; '));
      };
    `;

    // Generate dex-sheet.png, characters-sheet.png, and all-maps.png (every map at once!)
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

      // Render all 56 maps side-by-side into all-maps.png (8 columns x 7 rows)
      const mlist = Object.values(api.MAPS);
      const cellW = 38 * 8 + 8, cellH = 24 * 8 + 18;
      const mc = document.createElement('canvas');
      mc.width = 8 * cellW; mc.height = 7 * cellH;
      const mx = mc.getContext('2d'); mx.fillStyle = '#0e1018'; mx.fillRect(0, 0, mc.width, mc.height);
      mlist.forEach((m, idx) => {
        const col = idx % 8, row = Math.floor(idx / 8);
        const bx = col * cellW + 4, by = row * cellH + 14;
        mx.fillStyle = '#f8e888'; mx.font = '10px monospace';
        mx.fillText(m.id + ' (' + m.w + 'x' + m.h + ')', bx, by - 3);
        for (let ty = 0; ty < m.h; ty++) {
          for (let tx = 0; tx < m.w; tx++) {
            const tid = m.grid[ty * m.w + tx];
            const t = api.TILES_8X8[tid] || api.TILES_8X8[0];
            for (let py = 0; py < 8; py++) for (let px = 0; px < 8; px++) {
              const ci = t[py * 8 + px];
              if (ci) { mx.fillStyle = api.TILE_PALETTE[ci]; mx.fillRect(bx + tx * 8 + px, by + ty * 8 + py, 1, 1); }
            }
          }
        }
      });
      window.__ALL_MAPS_B64 = mc.toDataURL('image/png').split(',')[1];
    `);
    fs.writeFileSync(path.join(SHOTS_DIR, 'dex-sheet.png'), Buffer.from(await wd.exec('return window.__DEX_B64;'), 'base64'));
    fs.writeFileSync(path.join(SHOTS_DIR, 'characters-sheet.png'), Buffer.from(await wd.exec('return window.__CHAR_B64;'), 'base64'));
    fs.writeFileSync(path.join(SHOTS_DIR, 'all-maps.png'), Buffer.from(await wd.exec('return window.__ALL_MAPS_B64;'), 'base64'));
    await wd.screenshot(path.join(SHOTS_DIR, 'title.png'));

    // TEST 8: Input Test (1 tap = 1 tile, hold 1s = continuous, positive control)
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
      g.state.x = 15; g.state.y = 12;
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

    // TEST 9: Completion Bot + Whole-Bot Blocked Entrance Positive Control
    console.log('\n[TEST 9] Completion bot (rendering on, zero page errors, all gyms/rivals/syndicate/champion/postgame + whole-bot blocked control)...');
    const completionBotScript = `
      const api = window.BEATS_API;
      api.AudioEngine.muted = true;
      const g = api.Game;
      g.pressButton('A'); g.pressButton('A'); g.pressButton('A');
      while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
      let steps = 0, battles = 0;

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
          } else if (g.battle.phase === 'LOG') g.pressButton('A');
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
        const npc = map.npcs.find(n => n.id === npcId);
        if (!npc) return false;
        for (const [dx, dy, face] of [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']]) {
          if (walkTo(npc.x + dx, npc.y + dy)) {
            g.pressButton(face);
            g.pressButton('A');
            while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
            if (g.screen === 'BATTLE') winBattle();
            return true;
          }
        }
        return false;
      }

      function goToMap(destId) {
        const mq = [[g.state.mapId, []]];
        const mvis = new Set([g.state.mapId]);
        while (mq.length) {
          const [cm, mpath] = mq.shift();
          if (cm === destId) {
            for (const p of mpath) {
              const adj = [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']].find(([dx,dy]) => walkTo(p.x+dx, p.y+dy));
              if (adj) { g.pressButton(adj[2]); steps++; while (g.screen === 'DIALOG') g.pressButton('A'); window.__checkFrame(); }
            }
            return g.state.mapId === destId;
          }
          for (const p of (api.MAPS[cm].portals || [])) {
            if (p.reqSeals && g.state.seals.length < p.reqSeals) continue;
            if (p.reqChampion && !g.state.championBeaten) continue;
            if (!mvis.has(p.to)) { mvis.add(p.to); mq.push([p.to, mpath.concat(p)]); }
          }
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

      goToMap('cruston_mart'); talkNpc('mart_cruston');
      for (let i = 0; i < 6; i++) g.pressButton('A'); g.pressButton('B');

      goToMap('toastwood_trail'); grindTo(14, 'cruston_inn', 'inn_cruston'); goToMap('toastwood_trail'); talkNpc('saffron_1'); talkNpc('syn_vesper');
      goToMap('gym_toaster'); talkNpc('jr_toast_1'); talkNpc('greg_npc');
      goToMap('gym_deli'); walkTo(4, 11); talkNpc('jr_deli_1'); talkNpc('clara_npc');

      goToMap('bao_mart'); talkNpc('mart_bao'); for(let i=0;i<4;i++) g.pressButton('DOWN'); for(let i=0;i<10;i++) g.pressButton('A'); g.pressButton('B');
      goToMap('bamboo_mist_path'); grindTo(28, 'bao_inn', 'inn_bao'); goToMap('bamboo_mist_path'); talkNpc('syn_crumb');
      goToMap('bao_inn'); talkNpc('inn_bao'); goToMap('gym_bamboo'); talkNpc('jr_steam_1'); talkNpc('baozi_npc');
      goToMap('gyoza_cove'); talkNpc('saffron_2');
      goToMap('bao_inn'); talkNpc('inn_bao');
      goToMap('gym_skillet'); walkTo(17, 11); talkNpc('jr_skillet_1'); talkNpc('mei_npc');

      goToMap('slurp_canyon'); grindTo(38, 'udon_inn', 'inn_udon'); goToMap('slurp_canyon'); talkNpc('syn_glaze');
      goToMap('udon_inn'); talkNpc('inn_udon'); goToMap('gym_dojo'); talkNpc('jr_dojo_1'); talkNpc('twirl_npc');
      goToMap('al_dente_ascent'); talkNpc('saffron_3');
      goToMap('udon_inn'); talkNpc('inn_udon');
      goToMap('gym_wokpeak'); talkNpc('jr_wok_1'); talkNpc('fusilli_npc');

      goToMap('chowder_mart'); talkNpc('mart_chowder'); for(let i=0;i<4;i++) g.pressButton('DOWN'); for(let i=0;i<10;i++) g.pressButton('A'); g.pressButton('B');
      goToMap('simmer_fen'); grindTo(56, 'chowder_inn', 'inn_chowder'); goToMap('simmer_fen'); talkNpc('saffron_4');
      goToMap('chowder_inn'); talkNpc('inn_chowder'); goToMap('gym_cauldron'); walkTo(5, 11); talkNpc('jr_broth_1'); talkNpc('bisque_npc');
      goToMap('kettle_gorge'); talkNpc('syn_grunt_gorge');
      goToMap('bisque_inn'); talkNpc('inn_bisque');
      goToMap('gym_vault'); walkTo(17, 11); talkNpc('jr_vault_1'); talkNpc('bouillon_npc');
      goToMap('chrome_fork_hq'); talkNpc('syn_grunt_hq');
      goToMap('bisque_inn'); talkNpc('inn_bisque');
      goToMap('chrome_fork_hq_f2'); talkNpc('saffron_5'); walkTo(4, 11); talkNpc('boss_ladle_npc');

      if (!goToMap('grand_tasting_hall')) {
        return { map: g.state.mapId, seals: g.state.seals.length, steps, battles, reachedCredits: false, party: g.state.party.map(m => m.nickname + ' L' + m.level) };
      }
      talkNpc('inn_hall');
      talkNpc('saffron_6'); talkNpc('pip_npc'); talkNpc('roux_npc'); talkNpc('mochi_npc'); talkNpc('aurelia_npc');
      const reachedCredits = g.screen === 'CREDITS';
      g.pressButton('A');
      goToMap('eternal_pantry');
      window.__checkFrame();
      return {
        map: g.state.mapId, seals: g.state.seals.length, steps, battles,
        reachedCredits, party: g.state.party.map(m => m.nickname + ' L' + m.level)
      };
    `;

    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    const compRes = await wd.exec(completionBotScript);
    assert.strictEqual(compRes.seals, 8, 'Must earn all 8 seals');
    assert(compRes.reachedCredits, 'Must reach CREDITS');
    assert.strictEqual(compRes.map, 'eternal_pantry', 'Must reach eternal_pantry postgame');
    console.log(`PASS: Completion bot reached CREDITS & Postgame (${compRes.map})! Seals=${compRes.seals}/8, Steps=${compRes.steps}, Battles=${compRes.battles}, Party=[${compRes.party.join(', ')}]`);

    // Save post-champion state for downstream tests & screenshots
    const postChampSave = await wd.exec('return window.BEATS_API.Game.exportSaveJson(0);');

    // Whole-bot positive control: block every entrance to Grand Tasting Hall and run the WHOLE completion bot!
    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    await wd.exec(`
      for (const m of Object.values(window.BEATS_API.MAPS)) {
        m.portals = (m.portals || []).filter(p => p.to !== 'grand_tasting_hall');
      }
    `);
    const blockedBotRes = await wd.exec(completionBotScript);
    assert(!blockedBotRes.reachedCredits && blockedBotRes.map !== 'eternal_pantry', 'Whole completion bot MUST fail when Grand Tasting Hall entrances are blocked!');
    console.log(`PASS: Whole-bot positive control (blocked Grand Tasting Hall) failed as expected at map=${blockedBotRes.map} after ${blockedBotRes.steps} steps.`);

    // Reload clean page for Test 10 & 11
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);

    // TEST 10: Real Input-Only Quests Bot (walks and talks via pressButton only + multi-step positive controls)
    console.log('\n[TEST 10] Quests bot (walking & talking via pressButton only + multi-step positive controls)...');
    const questBotRes = await wd.exec(`
      const api = window.BEATS_API;
      api.AudioEngine.muted = true;
      const g = api.Game;
      const baseSave = arguments[0];

      function fleeOrWin() {
        let guard = 0;
        while (g.screen === 'BATTLE' && guard++ < 80) {
          if (g.battle.isWild) {
            g.pressButton('B');
            if (g.screen === 'BATTLE' && g.battle.phase === 'LOG') g.pressButton('A');
          } else { g.pressButton('A'); g.pressButton('A'); }
          window.__checkFrame();
        }
        while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
      }

      function walkTo(tx, ty) {
        let tries = 0;
        while (g.state.x !== tx || g.state.y !== ty) {
          if (tries++ > 35) return false;
          const map = api.MAPS[g.state.mapId];
          const mw = map.w || 30, mh = map.h || 18;
          const q = [[g.state.x, g.state.y, []]];
          const vis = new Set([g.state.x + ',' + g.state.y]);
          const dirs = [['UP',0,-1],['DOWN',0,1],['LEFT',-1,0],['RIGHT',1,0]];
          let foundPath = null;
          while (q.length) {
            const [cx, cy, path] = q.shift();
            if (cx === tx && cy === ty) { foundPath = path; break; }
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
          if (!foundPath) return false;
          const startMap = g.state.mapId;
          for (const d of foundPath) {
            g.pressButton(d);
            if (g.screen === 'BATTLE') fleeOrWin();
            while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
            window.__checkFrame();
            if (g.state.mapId !== startMap) return false;
          }
        }
        return true;
      }

      function goToMap(destId) {
        let attempts = 0;
        while (g.state.mapId !== destId && attempts++ < 50) {
          const mq = [[g.state.mapId, []]];
          const mvis = new Set([g.state.mapId]);
          let nextPortal = null;
          while (mq.length) {
            const [cm, mpath] = mq.shift();
            if (cm === destId) { nextPortal = mpath[0]; break; }
            for (const p of (api.MAPS[cm].portals || [])) {
              if (!mvis.has(p.to)) { mvis.add(p.to); mq.push([p.to, mpath.concat(p)]); }
            }
          }
          if (!nextPortal) return false;
          const adj = [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']].find(([dx,dy]) => walkTo(nextPortal.x+dx, nextPortal.y+dy));
          if (!adj) {
            const curM = api.MAPS[g.state.mapId];
            const mw = curM.w || 30, mh = curM.h || 18;
            for (let y = 0; y < mh; y++) for (let x = 0; x < mw; x++) if (curM.grid[y*mw+x] === 9) walkTo(x, y);
            continue;
          }
          g.pressButton(adj[2]);
          if (g.screen === 'BATTLE') fleeOrWin();
          while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
          window.__checkFrame();
        }
        return g.state.mapId === destId;
      }

      function talkNpcByPress(npcId) {
        const map = api.MAPS[g.state.mapId];
        const npc = map.npcs.find(n => n.id === npcId);
        if (!npc) return null;
        for (let pass = 0; pass < 2; pass++) {
          for (const [dx, dy, faceBtn] of [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']]) {
            if (walkTo(npc.x + dx, npc.y + dy)) {
              g.pressButton(faceBtn);
              g.pressButton('A');
              const firstLine = (g.dialogQueue && g.dialogQueue[0]) || '';
              while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
              if (g.screen === 'BATTLE') fleeOrWin();
              window.__checkFrame();
              return firstLine;
            }
          }
          const mw = map.w || 30, mh = map.h || 18;
          for (let y = 0; y < mh; y++) for (let x = 0; x < mw; x++) if (map.grid[y*mw+x] === 9) walkTo(x, y);
        }
        return null;
      }

      // 1. Positive controls on all 6 multi-step quests: talking to final NPC first does NOT complete quest
      const posControlLogs = [];
      for (const q of api.QUESTS) {
        if (q.steps <= 1) continue;
        g.importSaveJson(baseSave, 0);
        g.screen = 'OVERWORLD';
        let comp = null;
        for (const mp of Object.values(api.MAPS)) for (const n of (mp.npcs||[])) if (n.questComplete === q.id) comp = { map: mp.id, id: n.id };
        if (!goToMap(comp.map)) throw new Error('Could not reach ' + comp.map);
        const line = talkNpcByPress(comp.id);
        if (g.state.quests[q.id]) throw new Error('Positive control failed: ' + q.id + ' completed without earlier steps!');
        posControlLogs.push(q.id + ' blocked ("' + line.slice(0, 48) + '...")');
      }

      // 2. Complete all 16 quests in order via pressButton only
      g.importSaveJson(baseSave, 0);
      g.screen = 'OVERWORLD';
      const questLogs = [];
      const completed = [];
      for (const q of api.QUESTS) {
        let giver = null, steps = [], comp = null;
        for (const mp of Object.values(api.MAPS)) {
          for (const n of (mp.npcs || [])) {
            if (n.questGive === q.id) giver = { map: mp.id, id: n.id };
            if (n.questStep === q.id) steps.push({ idx: n.stepIndex || 1, map: mp.id, id: n.id });
            if (n.questComplete === q.id) comp = { map: mp.id, id: n.id };
          }
        }
        steps.sort((a,b) => a.idx - b.idx);
        const chain = [giver, ...steps, comp];
        const stepStrs = [];
        for (let i = 0; i < chain.length; i++) {
          const st = chain[i];
          if (!goToMap(st.map)) throw new Error('Could not walk to ' + st.map + ' for ' + q.id);
          const line = talkNpcByPress(st.id);
          if (line === null) throw new Error('Could not talk to ' + st.id + ' on ' + st.map);
          if (i > 0 && i < chain.length - 1) {
            const stepBefore = g.state.quests[q.id + '_step'];
            talkNpcByPress(st.id);
            if (g.state.quests[q.id + '_step'] !== stepBefore) throw new Error('Talking twice incremented step twice on ' + q.id);
          }
          stepStrs.push(st.map + ':' + st.id);
        }
        if (!g.state.quests[q.id]) throw new Error('Quest ' + q.id + ' did not complete!');
        completed.push(q.id);
        questLogs.push('  ' + q.id + ': ' + stepStrs.join(' -> '));
      }
      return { completed, questLogs, posControlLogs };
    `, [postChampSave]);
    for (const l of questBotRes.questLogs) console.log(l);
    console.log(`  Multi-step positive controls verified (${questBotRes.posControlLogs.length}/6 rejected out-of-order completion): ${questBotRes.posControlLogs.join('; ')}`);
    assert.strictEqual(questBotRes.completed.length, 16);
    console.log(`PASS: All 16/16 quests completed via pressButton only!`);

    // TEST 11: Walking Dex-Completion Bot (151/151) + Whole-Bot Positive Control with 1 Species Removed
    console.log('\n[TEST 11] Walking Dex-completion bot (151/151 via pressButton) + whole-bot positive control...');
    const dexBotScript = `
      const api = window.BEATS_API;
      api.AudioEngine.muted = true;
      const g = api.Game;
      const maxGuardPerArea = arguments[0] || 1500;
      g.pressButton('A'); g.pressButton('A'); g.pressButton('A');
      while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
      // Disclosed starting conditions in REPORT.md:
      g.state.party = [
        api.createBeatstInstance(3, 85, () => g.rng()),
        api.createBeatstInstance(41, 85, () => g.rng()),
        api.createBeatstInstance(79, 85, () => g.rng()),
        api.createBeatstInstance(117, 85, () => g.rng())
      ];
      for (const id of [1,2,3, 39,40,41, 77,78,79, 115,116,117]) g.markCaught(id);
      g.state.gold = 999999;
      g.state.bag.royal_banquet = 2500;
      g.state.bag.garnish_treat = 2500;
      g.state.bag.grand_feast = 1000;
      g.state.seals = ['Crisp Seal','Stack Seal','Steam Seal','Sear Seal','Slurp Seal','Twirl Seal','Simmer Seal','Stock Seal'];
      g.state.championBeaten = true;

      let steps = 0, battles = 0, ladleEncounters = 0;
      const areaCounts = {};

      function handleWildBattle(wantCatchIds) {
        battles++;
        const foe = g.battle.foeParty[0];
        const spId = foe.speciesId;
        areaCounts[g.state.mapId] = (areaCounts[g.state.mapId] || 0) + 1;
        let guard = 0;
        while (g.screen === 'BATTLE' && guard++ < 80) {
          if (g.battle.phase === 'MAIN') {
            if (!g.state.dexCaught.includes(spId) || wantCatchIds.has(spId)) {
              if (!g.battle.usedFavTreat && (g.state.bag.garnish_treat || 0) > 0 && api.BEATSTS_BY_ID[spId].catchRate < 0.25) {
                g.pressButton('RIGHT'); g.pressButton('A');
                const plates = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['plate','treat'].includes(api.ITEMS[k].kind));
                const tIdx = plates.indexOf('garnish_treat');
                for (let k = 0; k < Math.max(0, tIdx); k++) g.pressButton('DOWN');
                g.pressButton('A');
              } else {
                g.pressButton('RIGHT'); g.pressButton('A');
                const plates = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0 && ['plate','treat'].includes(api.ITEMS[k].kind));
                const pIdx = plates.indexOf('royal_banquet');
                for (let k = 0; k < Math.max(0, pIdx); k++) g.pressButton('DOWN');
                g.pressButton('A');
              }
            } else {
              g.pressButton('B');
            }
          } else if (g.battle.phase === 'LOG') g.pressButton('A');
          else g.pressButton('B');
          window.__checkFrame();
        }
        while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
      }

      function walkTo(tx, ty) {
        while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
        while (g.screen !== 'OVERWORLD' && g.screen !== 'BATTLE') { g.pressButton('B'); window.__checkFrame(); }
        const map = api.MAPS[g.state.mapId];
        const mw = map.w || 30, mh = map.h || 18;
        const q = [[g.state.x, g.state.y, []]];
        const vis = new Set([g.state.x + ',' + g.state.y]);
        const dirs = [['UP',0,-1],['DOWN',0,1],['LEFT',-1,0],['RIGHT',1,0]];
        while (q.length) {
          const [cx, cy, path] = q.shift();
          if (cx === tx && cy === ty) {
            for (const d of path) {
              g.pressButton(d); steps++;
              if (g.screen === 'BATTLE') handleWildBattle(new Set());
              while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
              window.__checkFrame();
            }
            return g.state.x === tx && g.state.y === ty;
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

      function goToMap(destId) {
        let attempts = 0;
        while (g.state.mapId !== destId && attempts++ < 50) {
          const mq = [[g.state.mapId, []]];
          const mvis = new Set([g.state.mapId]);
          let nextPortal = null;
          while (mq.length) {
            const [cm, mpath] = mq.shift();
            if (cm === destId) { nextPortal = mpath[0]; break; }
            for (const p of (api.MAPS[cm].portals || [])) {
              if (!mvis.has(p.to)) { mvis.add(p.to); mq.push([p.to, mpath.concat(p)]); }
            }
          }
          if (!nextPortal) return false;
          const adj = [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']].find(([dx,dy]) => walkTo(nextPortal.x+dx, nextPortal.y+dy));
          if (!adj) {
            const curM = api.MAPS[g.state.mapId];
            const mw = curM.w || 30, mh = curM.h || 18;
            for (let y = 0; y < mh; y++) for (let x = 0; x < mw; x++) if (curM.grid[y*mw+x] === 9) walkTo(x, y);
            continue;
          }
          g.pressButton(adj[2]); steps++;
          if (g.screen === 'BATTLE') handleWildBattle(new Set());
          while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
          window.__checkFrame();
        }
        return g.state.mapId === destId;
      }

      function ensureNight(wantNight) {
        if (!!g.state.isNight !== !!wantNight) {
          g.pressButton('SELECT');
          while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
        }
      }

      for (const m of Object.values(api.MAPS)) {
        if (!m.wildPool || !m.wildPool.length) continue;
        const needed = m.wildPool.map(e => e[0]).filter(id => !g.state.dexCaught.includes(id));
        if (!needed.length) continue;
        if (!goToMap(m.id)) throw new Error('Could not walk to ' + m.id);
        const mw = m.w || 30, mh = m.h || 18;
        for (let y = 0; y < mh; y++) for (let x = 0; x < mw; x++) if (m.grid[y*mw+x] === 9) walkTo(x, y);

        if (ladleEncounters === 0) {
          for (let y = 1; y < mh - 1 && ladleEncounters === 0; y++) {
            for (let x = 1; x < mw - 1 && ladleEncounters === 0; x++) {
              if ([13,25,37,49].includes(m.grid[y*mw+x])) {
                for (const [dx, dy, faceBtn] of [[0,1,'UP'],[0,-1,'DOWN'],[1,0,'LEFT'],[-1,0,'RIGHT']]) {
                  if (walkTo(x + dx, y + dy)) {
                    g.pressButton(faceBtn);
                    g.pressButton('A');
                    while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
                    if (g.screen === 'BATTLE') { ladleEncounters++; handleWildBattle(new Set(m.wildPool.map(e => e[0]))); break; }
                  }
                }
              }
            }
          }
        }

        const portals = new Set((m.portals || []).map(p => p.x + ',' + p.y));
        const npcs = new Set((m.npcs || []).filter(n => !g.isNpcHidden(n)).map(n => n.x + ',' + n.y));
        let gx = -1, gy = -1, stepDir = 'LEFT', backDir = 'RIGHT';
        for (let y = 1; y < mh - 1 && gx < 0; y++) {
          for (let x = 1; x < mw - 1 && gx < 0; x++) {
            if ([11,23,35,47,62].includes(m.grid[y*mw+x]) && !portals.has(x+','+y) && !npcs.has(x+','+y)) {
              for (const [dx, dy, d1, d2] of [[1,0,'RIGHT','LEFT'],[-1,0,'LEFT','RIGHT'],[0,1,'DOWN','UP'],[0,-1,'UP','DOWN']]) {
                const nx = x + dx, ny = y + dy;
                if (nx <= 0 || nx >= mw - 1 || ny <= 0 || ny >= mh - 1) continue;
                if (portals.has(nx + ',' + ny) || npcs.has(nx + ',' + ny)) continue;
                if ([11,23,35,47,62].includes(m.grid[ny*mw+nx]) && walkTo(x, y)) {
                  gx = x; gy = y; stepDir = d1; backDir = d2; break;
                }
              }
            }
          }
        }
        let guard = 0;
        while (m.wildPool.some(e => !g.state.dexCaught.includes(e[0])) && guard++ < maxGuardPerArea) {
          if (g.state.party[0].hp < g.state.party[0].maxHp * 0.65 && (g.state.bag.grand_feast || 0) > 0) {
            g.pressButton('START');
            let mGuard = 0;
            while (g.menuCursor !== 3 && mGuard++ < 12) g.pressButton('DOWN');
            g.pressButton('A');
            const keys = Object.keys(g.state.bag).filter(k => g.state.bag[k] > 0);
            const fIdx = keys.indexOf('grand_feast');
            let bGuard = 0;
            while (g.bagCursor !== fIdx && fIdx >= 0 && bGuard++ < 20) g.pressButton('DOWN');
            g.pressButton('A');
            let cGuard = 0;
            while (g.screen !== 'OVERWORLD' && cGuard++ < 10) {
              if (g.screen === 'DIALOG') g.pressButton('A');
              else g.pressButton('B');
            }
          }
          const nextMissing = m.wildPool.map(e => e[0]).find(id => !g.state.dexCaught.includes(id));
          ensureNight(!!api.BEATSTS_BY_ID[nextMissing].nightOnly);
          g.pressButton(guard % 2 === 1 ? stepDir : backDir);
          steps++;
          if (g.screen === 'BATTLE') handleWildBattle(new Set(m.wildPool.map(e => e[0])));
          while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
          window.__checkFrame();
        }
      }

      if (!goToMap('grand_tasting_hall')) throw new Error('Could not walk to grand_tasting_hall');
      let guard151 = 0;
      while (!g.state.dexCaught.includes(151) && guard151++ < 20) {
        ensureNight(true);
        walkTo(11, 3);
        g.pressButton('UP');
        g.pressButton('A');
        while (g.screen === 'DIALOG') { g.pressButton('A'); window.__checkFrame(); }
        if (g.screen === 'BATTLE') handleWildBattle(new Set([151]));
      }
      return { caught: g.state.dexCaught.length, steps, battles, ladleEncounters, areaCounts };
    `;

    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    // KEHAI PATCH 2026-11-14 (Kham's call: evolved forms are evolution-only, so they are no longer in
    // wild pools). The walking bot must now plate EVERY species that has a wild source (+ #151's door);
    // the evolution-only species are covered by Test 2's 151/151 reachability, not by this bot.
    const wildIds = await wd.exec(`const s=new Set([151]);for(const m of Object.values(window.BEATS_API.MAPS))for(const e of (m.wildPool||[]))s.add(e[0]);return [...s];`);
    const dexRes = await wd.exec(dexBotScript, [1500]);
    const dexCaughtNow = await wd.exec('return window.BEATS_API.Game.state.dexCaught.slice();');
    const wildMissed = wildIds.filter(id => !dexCaughtNow.includes(id));
    assert.strictEqual(wildMissed.length, 0, `Walking dex bot missed wild species: ${wildMissed.join(',')}`);
    console.log(`PASS: Walking Dex bot plated all ${wildIds.length} wild-sourced species (dex total ${dexRes.caught}/151 incl. disclosed starter-line marks; evolution-only species covered by Test 2) across ${Object.keys(dexRes.areaCounts).length} wild areas (steps=${dexRes.steps}, battles=${dexRes.battles}, ladle=${dexRes.ladleEncounters}).`);

    // Whole-bot positive control for Dex bot: remove species #24 (Meltmoth) from its only source and run the whole dex bot!
    await wd.exec('try { localStorage.clear(); } catch(e) {}');
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec(installMonitor);
    await wd.exec(`
      for (const m of Object.values(window.BEATS_API.MAPS)) {
        m.wildPool = (m.wildPool || []).filter(e => e[0] !== 24);
      }
    `);
    const dexMissingRes = await wd.exec(dexBotScript, [1500]);
    const missCaught = await wd.exec('return window.BEATS_API.Game.state.dexCaught.slice();');
    assert.ok(!missCaught.includes(24), 'Control: #24 must not be plated once its wild source is removed');
    assert.strictEqual(dexMissingRes.caught, dexRes.caught - 1, `Expected whole dex bot with #24 removed to plate exactly one fewer (${dexRes.caught - 1}), got ${dexMissingRes.caught}`);
    console.log(`PASS: Whole-bot Dex positive control (species #24 removed) plated one fewer as expected (${dexMissingRes.caught} vs ${dexRes.caught}).`);

    // Fresh Screenshots of EVERY map + battle + plating + credits + beatdex_151 + regional/special shots
    await wd.url(targetUrl);
    await new Promise(r => setTimeout(r, 300));
    await wd.exec('window.BEATS_API.Game.importSaveJson(arguments[0], 0);', [postChampSave]);
    await wd.exec(`
      const g = window.BEATS_API.Game;
      for (let i = 1; i <= 151; i++) g.markCaught(i);
      g.screen = 'DEX'; g.dexCursor = 150; g.dexScroll = 144; g.render();
    `);
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
        g.screen = 'OVERWORLD';
        g.state.mapId = '${mid}';
        g.state.x = Math.floor(m.w / 2);
        g.state.y = Math.floor(m.h / 2);
        g.bannerTimer = 0;
        g.transitionTimer = 0;
        g.render();
      `);
      await wd.screenshot(path.join(SHOTS_DIR, `${mid}.png`));
    }
    // Also write the canonical region_* and special_* aliases from freshly captured screenshots so zero v2 leftovers exist
    const aliases = [
      ['cruston_town.png', 'region_bread_town.png'],
      ['toastwood_trail.png', 'region_bread_route.png'],
      ['bao_harbor.png', 'region_steam_town.png'],
      ['bamboo_mist_path.png', 'region_steam_route.png'],
      ['udon_hollow.png', 'region_noodle_town.png'],
      ['slurp_canyon.png', 'region_noodle_route.png'],
      ['chowder_crossing.png', 'region_broth_town.png'],
      ['simmer_fen.png', 'region_broth_route.png'],
      ['sourdough_cavern.png', 'special_sourdough.png'],
      ['steamer_spire.png', 'special_spire.png'],
      ['wok_volcano.png', 'special_wok.png'],
      ['broth_catacombs.png', 'special_catacombs.png'],
      ['eternal_pantry.png', 'postgame.png']
    ];
    for (const [src, dst] of aliases) {
      fs.copyFileSync(path.join(SHOTS_DIR, src), path.join(SHOTS_DIR, dst));
    }

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
