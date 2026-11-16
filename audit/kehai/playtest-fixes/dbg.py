from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/chromium",args=["--no-sandbox"]); pg=b.new_page()
    pg.goto("file:///tmp/bfix/beatsts.html"); pg.wait_for_timeout(500)
    print(pg.evaluate("() => { const L=Object.values(window.BEATS_API.MAPS).flatMap(m=>m.npcs||[]).flatMap(c=>c.lines||[]); return [L.length, L.filter(l=>typeof l==='string'&&l.includes('thirty')).length, typeof L[0]]; }"))
    pg.evaluate("""() => { const G=window.BEATS_API.Game; G.startNewGame(0,'Brie',1); G.dialogQueue=[]; G.screen='OVERWORLD';
      const v='We score our baguettes at a thirty-degree angle with a razor blade so the oven spring opens like wheat ears.'; G.showDialog('Baker Vera: '+v); }""")
    for i in range(3):
        st=pg.evaluate("() => { const G=window.BEATS_API.Game; G.render(); return [G.screen,G.dialogQueue.slice()]; }"); print(st)
        pg.locator("canvas").first.screenshot(path=f"/tmp/vera_page{i+1}.png")
        if st[0]!="DIALOG": break
        pg.evaluate("() => window.BEATS_API.Game.pressButton('A')")
    b.close()
