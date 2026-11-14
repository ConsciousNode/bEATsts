from playwright.sync_api import sync_playwright
import json
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type=='error' and errs.append(m.text))
    pg.goto('http://127.0.0.1:8773/beatsts.html'); pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(500)
    pg.evaluate("BEATS_API.AudioEngine.muted=true; BEATS_API.Game.startNewGame(0,'Bug',1,7); while(BEATS_API.Game.screen==='DIALOG') BEATS_API.Game.advanceDialog();")
    n=pg.evaluate("BEATS_API.MOVES.length"); bad=[]
    for mid in range(n):
        errs.clear()
        r=pg.evaluate("""(mid)=>{const A=BEATS_API,g=A.Game;g.state.party[0].hp=g.state.party[0].maxHp;g.startWildBattle(1,5);
          const mon=g.state.party[0];mon.moves[0]={id:mid,pp:5};g.battle.phase='MAIN';g.battle.cursor=0;
          g.handleBattleInput('A');g.handleBattleInput('A');return {anim:A.MOVES[mid].anim,name:A.MOVES[mid].name,phase:g.battle&&g.battle.phase,screen:g.screen}}""", mid)
        frames=[]
        for t in range(6):
            pg.wait_for_timeout(120)
            frames.append(pg.evaluate("""(()=>{const c=document.querySelector('canvas');const x=c.getContext('2d');const d=x.getImageData(0,0,c.width,c.height).data;let lit=0;for(let i=0;i<d.length;i+=16)if(d[i]+d[i+1]+d[i+2]>30)lit++;return lit})()"""))
        if errs or min(frames)<50: bad.append((mid,r['name'],r['anim'],min(frames),errs[:1]))
    print('moves tested',n,'bad',len(bad))
    for x in bad[:20]: print(x)
    b.close()
