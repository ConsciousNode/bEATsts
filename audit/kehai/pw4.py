import re, json
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8765/beatsts.html'
src=open('/home/claude/beatsts/tests/run-all.js').read()
bot=[x for x in re.findall(r"wd\.exec\(`([\s\S]*?)`\)", src) if 'walkTo' in x][0]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.goto(U); pg.wait_for_timeout(300)
    blk=pg.evaluate("(()=>{BEATS_API.MAPS.bisque_bastion.portals.filter(p=>p.to==='grand_tasting_hall').forEach(p=>p.reqSeals=99);"+bot+"})()")
    print('full bot, BOTH hall entrances blocked ->', blk.get('ok'), blk.get('screen'), blk.get('err',''), blk.get('map'))
    pg.goto(U); pg.wait_for_timeout(200)
    for i in range(6): pg.keyboard.press('z'); pg.wait_for_timeout(50)
    pg.evaluate("(()=>{const g=BEATS_API.Game;g.state.mapId='toastwood_trail';})()")
    info=pg.evaluate("(()=>{const g=BEATS_API.Game,m=BEATS_API.MAPS.toastwood_trail;let c=0;for(const t of m.grid)if(t===1)c++;return {grass:c,pos:[g.state.x,g.state.y],pool:m.wildPool}})()")
    print('toastwood grass tiles', info)
    # walk onto every grass tile row by keys: find a grass tile with grass neighbour, teleport-free path via BFS using API-only planning
    res=pg.evaluate("""(()=>{const g=BEATS_API.Game,m=BEATS_API.MAPS.toastwood_trail;for(let y=0;y<18;y++)for(let x=0;x<29;x++)if(m.grid[y*30+x]===1&&m.grid[y*30+x+1]===1)return [x,y];return null})()""")
    print('grass pair at',res)
    b.close()
