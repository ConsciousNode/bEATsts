# Kehai: real-Chromium checks of the 2026-11-15 playtest fixes
from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/chromium",args=["--no-sandbox"]); pg=b.new_page()
    errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)))
    pg.goto("file:///tmp/bfix/beatsts.html"); pg.wait_for_timeout(500)
    # 1. paging: every NPC/sign line splits into pages of <=4 wrapped rows, words preserved
    r=pg.evaluate("""() => { const G=window.BEATS_API.Game, M=window.BEATS_API.MAPS; let n=0,bad=0,multi=0,maxp=0;
      const wrap=t=>{const w=t.split(' ');let l='',k=0;for(const x of w){if((l+x).length>27){k++;l=x+' ';}else l+=x+' ';}if(l.trim())k++;return k;};
      for(const m of Object.values(M)){ const L=[]; for(const c of m.npcs||[]) L.push(...(c.lines||[]),...(c.nightLines||[])); for(const s of m.signs||[]) L.push(s.text);
        for(const t of L){ n++; const pages=G.paginateDialog(t); if(pages.length>1)multi++; maxp=Math.max(maxp,pages.length);
          for(const pgx of pages) if(wrap(pgx)>4) bad++;
          if(pages.join(' ').split(/\\s+/).join(' ')!==String(toAsciiFontStr(t)).trim().split(/\\s+/).join(' ')) bad++; } }
      return {lines:n,overflowOrLost:bad,linesNowPaged:multi,maxPages:maxp}; }""")
    print("1. paging:",r)
    # Vera on screen: talk and screenshot each page
    pg.evaluate("""() => { const G=window.BEATS_API.Game; G.startNewGame(0,'Brie',1); G.dialogQueue=[]; G.screen='OVERWORLD'; const v=Object.values(window.BEATS_API.MAPS).flatMap(m=>m.npcs||[]).flatMap(c=>c.lines||[]).find(l=>l.includes('thirty-degree'))||'x'; G.showDialog(v); G.render(); }""")
    pages=[]
    for i in range(4):
        st=pg.evaluate("() => { const G=window.BEATS_API.Game; G.render(); return {s:G.screen,q:G.dialogQueue.length,t:G.dialogQueue[0]||''}; }")
        pages.append(st)
        pg.locator("canvas").first.screenshot(path=f"/tmp/vera_page{i+1}.png")
        if st["s"]!="DIALOG": break
        pg.evaluate("() => window.BEATS_API.Game.pressButton('A')")
    print("   Vera pages:",json.dumps(pages))
    # 2. name field: type with focus; game must not react, value must survive
    before=pg.evaluate("() => window.BEATS_API.Game.screen")
    inp=pg.locator("#player-name-input"); inp.fill(""); inp.click(); pg.keyboard.type("Muse Sam Wanda", delay=20); pg.keyboard.press("Backspace")
    val=inp.input_value(); after=pg.evaluate("() => window.BEATS_API.Game.screen")
    print("2. name field:", repr(val), "| screen before/after typing:", before, after)
    # 3. Tab must not toggle day/night; N still does (after leaving the field)
    pg.evaluate("() => { const G=window.BEATS_API.Game; G.startNewGame(0,'Brie',1); G.dialogQueue=[]; G.screen='OVERWORLD'; }")
    pg.locator("canvas").first.click(); n0=pg.evaluate("() => window.BEATS_API.Game.state.isNight")
    pg.keyboard.press("Tab"); n1=pg.evaluate("() => window.BEATS_API.Game.state.isNight")
    pg.evaluate("() => { document.activeElement && document.activeElement.blur && document.activeElement.blur(); const G=window.BEATS_API.Game; G.screen='OVERWORLD'; G.dialogQueue=[]; }")
    pg.keyboard.press("n"); n2=pg.evaluate("() => window.BEATS_API.Game.state.isNight")
    print("3. isNight start/after Tab/after N:", n0, n1, n2)
    print("page errors:", errs)
    b.close()
