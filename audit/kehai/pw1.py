# Kehai audit: run Hydrogen's browser test scripts verbatim in Playwright over http://
import re, json, sys
from playwright.sync_api import sync_playwright
src=open('/home/claude/beatsts/tests/run-all.js').read()
blocks=re.findall(r"wd\.exec\(`([\s\S]*?)`\)", src)
print('exec blocks:',len(blocks))
URL='http://127.0.0.1:8765/beatsts.html'
def run(page, body): return page.evaluate("(()=>{"+body+"})()")
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':800,'height':900})
    errs=[]; pg.on('console', lambda m: m.type in('error','warning') and errs.append(m.text)); pg.on('pageerror', lambda e: errs.append('PAGEERROR '+str(e)))
    pg.goto(URL); pg.wait_for_timeout(800)
    print('screen on load:', pg.evaluate("window.BEATS_API&&BEATS_API.Game.screen"))
    print('save test:', run(pg, blocks[0]))
    pg.goto(URL); pg.wait_for_timeout(300)
    bot=[x for x in blocks if 'walkTo' in x][0]
    r=run(pg, bot); print('BOT verbatim:', json.dumps(r))
    # variant: no free gold/items line
    pg.goto(URL); pg.wait_for_timeout(300)
    nofree=bot.replace("g.state.gold -= 1750; g.state.bag.grand_feast = (g.state.bag.grand_feast || 0) + 5;","")
    assert nofree!=bot
    print('BOT without state edit:', json.dumps(run(pg,nofree)))
    print('console errors/warnings:', errs[:10], len(errs))
    b.close()
