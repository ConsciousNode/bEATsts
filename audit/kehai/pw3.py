# Kehai audit: real keyboard play, real-reload saves, #151 event, full-bot positive control
import re, json
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8765/beatsts.html'
src=open('/home/claude/beatsts/tests/run-all.js').read()
bot=[x for x in re.findall(r"wd\.exec\(`([\s\S]*?)`\)", src) if 'walkTo' in x][0]
S=lambda pg: pg.evaluate("BEATS_API.Game.screen")
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(); pg=ctx.new_page(); pg.goto(U); pg.wait_for_timeout(500)
    seen=[]
    for i in range(40):
        s=S(pg); seen.append(s)
        if s=='OVERWORLD': break
        pg.keyboard.press('z'); pg.wait_for_timeout(60)
    print('keyboard boot path:', ' > '.join(dict.fromkeys(seen)))
    st=pg.evaluate("({map:BEATS_API.Game.state.mapId,x:BEATS_API.Game.state.x,y:BEATS_API.Game.state.y,party:BEATS_API.Game.state.party.map(m=>m.nickname),bag:BEATS_API.Game.state.bag,gold:BEATS_API.Game.state.gold})")
    print('after keyboard boot:', json.dumps(st))
    # find nearest grass tile reachable, walk with real arrow keys via BFS path
    BFS="""(goal)=>{const g=BEATS_API.Game,m=BEATS_API.MAPS[g.state.mapId];const q=[[g.state.x,g.state.y,[]]],v=new Set([g.state.x+','+g.state.y]);
      const D=[['ArrowUp',0,-1],['ArrowDown',0,1],['ArrowLeft',-1,0],['ArrowRight',1,0]];
      const isGoal=(x,y)=>goal==='grass'?m.grid[y*30+x]===1:(m.portals||[]).some(p=>p.x===x&&p.y===y);
      while(q.length){const [x,y,p]=q.shift(); if(p.length&&isGoal(x,y)) return p;
       for(const [k,dx,dy] of D){const nx=x+dx,ny=y+dy;if(nx<0||ny<0||nx>=30||ny>=18)continue;const t=m.grid[ny*30+nx];if(!isGoal(nx,ny)&&([3,4,5,6,9,10].includes(t)||v.has(nx+','+ny)))continue;
        if((m.npcs||[]).some(n=>n.x===nx&&n.y===ny))continue;v.add(nx+','+ny);q.push([nx,ny,p.concat(k)])}} return null}"""
    for hop in range(3):
        path=pg.evaluate(BFS,'grass')
        if path: break
        pp=pg.evaluate(BFS,'portal'); print('  no grass on',pg.evaluate("BEATS_API.Game.state.mapId"),'-> walking to portal by keys',len(pp))
        for k in pp:
            pg.keyboard.press(k); pg.wait_for_timeout(140)
            while S(pg)=='DIALOG': pg.keyboard.press('z'); pg.wait_for_timeout(60)
            if S(pg)=='BATTLE': break
    print('map now', pg.evaluate("BEATS_API.Game.state.mapId"), 'keys to grass:', len(path))
    for k in path:
        pg.keyboard.press(k); pg.wait_for_timeout(140)
        if S(pg)=='BATTLE': break
    for i in range(400):
        if S(pg)=='BATTLE': break
        pg.keyboard.press('ArrowLeft' if i%2 else 'ArrowRight'); pg.wait_for_timeout(140)
        while S(pg)=='DIALOG': pg.keyboard.press('z'); pg.wait_for_timeout(60)
    print('wild battle via grass steps:', S(pg), pg.evaluate("BEATS_API.Game.battle&&BEATS_API.Game.battle.log"))
    caught0=pg.evaluate("BEATS_API.Game.state.dexCaught.length"); tries=0
    while S(pg)=='BATTLE' and tries<30:
        ph=pg.evaluate("BEATS_API.Game.battle.phase")
        if ph=='MAIN':
            pg.keyboard.press('ArrowRight'); pg.keyboard.press('z'); tries+=1
            if pg.evaluate("BEATS_API.Game.battle.phase")=='PLATE': pg.keyboard.press('z')
            else: pg.keyboard.press('x'); pg.keyboard.press('ArrowLeft'); pg.keyboard.press('z'); pg.keyboard.press('z')  # no plates -> fight
        else: pg.keyboard.press('z')
        pg.wait_for_timeout(40)
        while S(pg)=='DIALOG': pg.keyboard.press('z')
    print('plating by keyboard: attempts',tries,'caught',caught0,'->',pg.evaluate("BEATS_API.Game.state.dexCaught.length"),'party',pg.evaluate("BEATS_API.Game.state.party.map(m=>m.nickname)"))
    # real saves across reload
    pg.evaluate("BEATS_API.Game.saveToSlot(0)"); before=pg.evaluate("BEATS_API.Game.exportSaveJson(0)")
    ls=pg.evaluate("Object.keys(localStorage)")
    pg.reload(); pg.wait_for_timeout(400)
    pg.evaluate("BEATS_API.Game.loadFromSlot(0)"); after=pg.evaluate("BEATS_API.Game.exportSaveJson(0)")
    print('localStorage keys:',ls,'| save survives real reload identically:', before==after)
    # #151: hidden on dex before, event works after champion
    r=pg.evaluate("""(()=>{const A=BEATS_API,g=A.Game; g.startNewGame(2,'Night',1,7);
      const s=g.state; const fam={Sandwiches:1,Dumplings:39,Noodles:77,Soup:115};
      const hidden=!(s.dexSeen.includes(151)); s.championBeaten=true; s.isNight=true; s.bag.royal_banquet=1;
      s.party=Object.values(fam).map(id=>A.createBeatstInstance?A.createBeatstInstance(id,60,()=>0.5):null);
      if(s.party.includes(null)) return 'no createBeatstInstance on API';
      s.mapId='grand_tasting_hall'; const m=A.MAPS[s.mapId]; const n=m.npcs.find(n=>n.action==='secret151'); if(!n) return 'no secret npc';
      s.x=n.x; s.y=n.y+1; s.dir='up'; g.interactAhead(); while(g.screen==='DIALOG') g.advanceDialog();
      return {hiddenBefore:hidden, door:[n.x,n.y], screen:g.screen, foe:g.battle&&g.battle.foeParty[0].speciesId}})()""")
    print('#151 event:', json.dumps(r))
    # full-bot positive control: block hall portal, run the whole bot
    pg.goto(U); pg.wait_for_timeout(200)
    blk=pg.evaluate("(()=>{BEATS_API.MAPS.bisque_bastion.portals.find(p=>p.to==='grand_tasting_hall').reqSeals=99;"+bot+"})()")
    print('full bot with hall portal blocked ->', blk.get('ok'), blk.get('screen'), blk.get('err',''), blk.get('map'))
    b.close()
