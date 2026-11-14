# Kehai audit 2.1: real positive controls on the WHOLE completion bot, rendering on, pageerror trap
import re, json
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8771/beatsts.html'
src=open('/home/claude/beatsts/tests/run-all.js').read()
bot=re.findall(r"wd\.exec\(`([\s\S]*?)`\)",src)[3]
mon=re.search(r"const installMonitor = `([\s\S]*?)`;",src).group(1)
html=open('/home/claude/beatsts/beatsts.html').read()
GUARD="if (b.foeIdx + 1 < b.foeParty.length) {\n        b.foeIdx++;"
assert GUARD in html, 'guard text not found'
bug=html.replace(GUARD,"b.foeIdx++;\n      if (b.foeIdx < b.foeParty.length) {",1)
open('/home/claude/beatsts/_kehai_bugged.html','w').write(bug)
def run(url, pre='', label=''):
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(); errs=[]
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(url); pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(500)
        # render between inputs: patch pressButton to render each call (the spec's "rendering on")
        pg.evaluate("(()=>{const g=BEATS_API.Game;const pb=g.pressButton.bind(g);g.pressButton=function(x){const r=pb(x);try{g.render()}catch(e){window.__renderErrs=(window.__renderErrs||0)+1;window.__lastErr=String(e)}return r};const hb=g.handleBattleInput.bind(g);g.handleBattleInput=function(x){const r=hb(x);try{g.render()}catch(e){window.__renderErrs=(window.__renderErrs||0)+1;window.__lastErr=String(e)}return r}})()")
        pg.evaluate("(()=>{"+mon+"})()")
        try:
            r=pg.evaluate("(()=>{"+pre+bot+"})()")
        except Exception as e:
            print(label,"| THREW:",str(e).split(chr(10))[0][:160]); b.close(); return
        re_=pg.evaluate("[window.__renderErrs||0, window.__lastErr||'']")
        print(label,'| ok',r.get('ok'),'| map',r.get('map'),'| seals',r.get('seals'),'| steps',r.get('steps'),'| battles',r.get('battles'),'| render errors',re_[0],re_[1][:80],'| pageerrors',len(errs))
        b.close()
run(U,'', 'REAL BOT, rendering each input')
run(U,"BEATS_API.MAPS.bisque_bastion.portals.filter(p=>p.to==='grand_tasting_hall').forEach(p=>p.reqSeals=99);", 'WHOLE bot, hall entrances blocked')
run('http://127.0.0.1:8771/_kehai_bugged.html','', 'WHOLE bot, v2 foeIdx bug re-inserted')
