# Kehai audit v2: real keyboard play from title to a plated bEATst
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8766/beatsts.html'
S=lambda pg: pg.evaluate("BEATS_API.Game.screen")
BFS="""(goal)=>{const A=BEATS_API,g=A.Game,m=A.MAPS[g.state.mapId];const q=[[g.state.x,g.state.y,[]]],v=new Set([g.state.x+','+g.state.y]);
 const D=[['ArrowUp',0,-1],['ArrowDown',0,1],['ArrowLeft',-1,0],['ArrowRight',1,0]];
 const isGrass=t=>[11,23,35,47,62].includes(t);
 const isGoal=(x,y)=>goal==='grass'?(m.wildPool&&m.wildPool.length>0)&&isGrass(m.grid[y*30+x]):(m.portals||[]).some(p=>p.x===x&&p.y===y&&!(p.reqSeals>g.state.seals.length));
 while(q.length){const [x,y,p]=q.shift(); if(p.length&&isGoal(x,y)) return p;
  for(const [k,dx,dy] of D){const nx=x+dx,ny=y+dy;if(nx<0||ny<0||nx>=30||ny>=18||v.has(nx+','+ny))continue;const t=m.grid[ny*30+nx];
   if(!isGoal(nx,ny)&&A.SOLID_TILES.has(t))continue;if((m.npcs||[]).some(n=>n.x===nx&&n.y===ny&&!g.isNpcHidden(n)))continue;v.add(nx+','+ny);q.push([nx,ny,p.concat(k)])}} return null}"""
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':800,'height':800}); pg.goto(U); pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(500)
    seen=[]
    for i in range(40):
        s=S(pg); seen.append(s)
        if s=='OVERWORLD': break
        pg.keyboard.press('z'); pg.wait_for_timeout(60)
    print('boot by keys:',' > '.join(dict.fromkeys(seen)), '| map', pg.evaluate("BEATS_API.Game.state.mapId"))
    pg.screenshot(path='kb_town.png')
    for hop in range(3):
        path=pg.evaluate(BFS,'grass')
        if path: break
        for k in pg.evaluate(BFS,'portal') or []:
            pg.keyboard.press(k); pg.wait_for_timeout(110)
            while S(pg)=='DIALOG': pg.keyboard.press('z'); pg.wait_for_timeout(50)
    print('map', pg.evaluate("BEATS_API.Game.state.mapId"), 'keys to grass', len(path))
    for k in path:
        pg.keyboard.press(k); pg.wait_for_timeout(110)
        if S(pg)=='BATTLE': break
    n=0
    while S(pg)!='BATTLE' and n<300:
        d=pg.evaluate("(()=>{const A=BEATS_API,g=A.Game,m=A.MAPS[g.state.mapId];const G=t=>[11,23,35,47,62].includes(t);return G(m.grid[g.state.y*30+g.state.x+1])?'ArrowRight':'ArrowLeft'})()")
        pg.keyboard.press(d); pg.wait_for_timeout(110); n+=1
        while S(pg)=='DIALOG': pg.keyboard.press('z'); pg.wait_for_timeout(50)
    print('grass steps',n,'->',S(pg), pg.evaluate("BEATS_API.Game.battle&&BEATS_API.Game.battle.log"))
    pg.screenshot(path='kb_battle.png')
    tries=0;logs=[]
    while S(pg)=='BATTLE' and tries<25:
        if pg.evaluate("BEATS_API.Game.battle.phase")=='MAIN':
            pg.keyboard.press('ArrowRight'); pg.keyboard.press('z'); tries+=1
            if pg.evaluate("BEATS_API.Game.battle.phase")=='PLATE': pg.keyboard.press('z')
        else: logs.append(pg.evaluate("BEATS_API.Game.battle.log")); pg.keyboard.press('z')
        pg.wait_for_timeout(40)
    while S(pg) in('DIALOG',): pg.keyboard.press('z')
    print('plate tries',tries,'| party', pg.evaluate("BEATS_API.Game.state.party.map(m=>m.nickname)"),'| last', [l for l in logs if l][-2:])
    b.close()
