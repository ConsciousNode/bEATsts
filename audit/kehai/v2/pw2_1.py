# Kehai audit v2: verbatim completion bot over http, full-bot blocked control, console errors, saves across reload
import re, json, time
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8766/beatsts.html'
src=open('/home/claude/beatsts/tests/run-all.js').read()
bl=re.findall(r"wd\.exec\(`([\s\S]*?)`\)",src); bot=bl[3]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); errs=[]
    pg.on('console', lambda m: m.type in('error','warning') and errs.append(m.text)); pg.on('pageerror', lambda e: errs.append('PAGEERROR '+str(e)))
    pg.goto(U); pg.wait_for_timeout(800)
    print('loaded over http, screen:', pg.evaluate("BEATS_API.Game.screen"))
    t=time.time(); r=pg.evaluate("(()=>{"+bot+"})()"); print('completion bot verbatim (%.0fs):'%(time.time()-t), json.dumps(r)[:600])
    pg.goto(U); pg.wait_for_timeout(300)
    r2=pg.evaluate("(()=>{BEATS_API.MAPS.bisque_bastion.portals.filter(p=>p.to==='grand_tasting_hall').forEach(p=>p.reqSeals=99);"+bot+"})()")
    print('WHOLE bot with every hall entrance blocked:', json.dumps(r2)[:400])
    pg.goto(U); pg.wait_for_timeout(300)
    pg.evaluate("BEATS_API.Game.startNewGame(0,'Reload',1,5)"); pg.evaluate("BEATS_API.Game.saveToSlot(0)")
    a=json.loads(pg.evaluate("BEATS_API.Game.exportSaveJson(0)")); pg.reload(); pg.wait_for_timeout(800)
    pg.evaluate("BEATS_API.Game.loadFromSlot(0)"); c=json.loads(pg.evaluate("BEATS_API.Game.exportSaveJson(0)"))
    print('localStorage keys',pg.evaluate("Object.keys(localStorage)"),'| differs after real reload:', [k for k in a if a[k]!=c[k]])
    print('console errors/warnings:', len(errs), errs[:5])
    b.close()
