# Kehai's independent pixel differential: real Chromium (Playwright) renders the reference;
# frames compared to ROM frames from romframes.js (1337Boy). Both quantized to 5 bits/channel.
import json, sys, asyncio
from playwright.sync_api import sync_playwright
from PIL import Image
REF = "file:///tmp/bg/rb2/beatsts-2.2/beatsts.html"
d = json.load(open("pd_presses.json")); presses, samples, fpp = d["presses"], d["samples"], d["fpp"]
rom = open("pd_rom.bin", "rb").read(); FR = 240*160*3
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    pg = b.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    # freeze the page's own animation loop so frames depend only on presses (same as the reference harness)
    pg.add_init_script("window.requestAnimationFrame = () => 0;")
    pg.goto(REF); pg.wait_for_timeout(300)
    pg.evaluate("() => { window.BEATS_API.AudioEngine.muted = true; }")
    def ref_frame():
        return pg.evaluate("""() => { const g = window.BEATS_API.Game; g.render();
          const d = g.ctx.getImageData(0,0,240,160).data; const o = new Array(240*160*3);
          for (let i=0,j=0;i<d.length;i+=4,j+=3){o[j]=d[i]>>3;o[j+1]=d[i+1]>>3;o[j+2]=d[i+2]>>3;} return o; }""")
    si = 0; results = []; worst = []
    def compare(idx):
        global si
        rf = ref_frame(); rb = rom[si*FR:(si+1)*FR]
        bad = sum(1 for k in range(0, FR, 3) if rf[k]!=rb[k] or rf[k+1]!=rb[k+1] or rf[k+2]!=rb[k+2])
        scr = pg.evaluate("() => window.BEATS_API.Game.screen")
        results.append((idx, scr, bad))
        if bad: worst.append((bad, idx, scr, bytes(rf), rb))
        si += 1
    compare(0)
    for i, btn in enumerate(presses):
        # press, then advance the reference by exactly as many 60 Hz frames as the ROM ran (no state overrides)
        pg.evaluate("([b,n]) => { const g = window.BEATS_API.Game; g.pressButton(b); for (let k = 0; k < n; k++) g.update(1/60); }", [btn, fpp[i]])
        if si < len(samples) and samples[si] == i+1: compare(i+1)
    b.close()
from collections import defaultdict
agg = defaultdict(lambda: [0,0,0])
for idx, scr, bad in results:
    a = agg[scr]; a[0]+=1; a[1]+= (bad==0); a[2]+= 38400-bad
for s,(n,perf,px) in sorted(agg.items()): print(f"{s:11s} frames {n:4d} perfect {perf:4d} pixels {px}/{n*38400}")
tot = len(results); perf = sum(1 for r in results if r[2]==0)
print("TOTAL frames", tot, "perfect", perf, "page errors", len(errs), errs[:2])
worst.sort(key=lambda w: -w[0])
for k,(bad, idx, scr, rf, rb) in enumerate(worst[:8]):
    im = Image.new("RGB", (480,160))
    im.putdata([(rb[j]<<3, rb[j+1]<<3, rb[j+2]<<3) if x<240 else (rf[j2]<<3, rf[j2+1]<<3, rf[j2+2]<<3)
               for y in range(160) for x in range(480)
               for j in [(y*240+x)*3] for j2 in [(y*240+x-240)*3]])
    im.resize((960,320), Image.NEAREST).save(f"pdu_worst_{k+1}_press{idx}_{scr}_{bad}px.png")
    print("worst", k+1, "press", idx, scr, bad, "px", "(fuzz)" if idx>1500 else "(bot)")
