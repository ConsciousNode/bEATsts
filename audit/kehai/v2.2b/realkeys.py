# Kehai audit 2.2 build B: real keyboard on a fresh game -- start, walk, and try to finish multi-step quests at the final NPC first
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8773/beatsts.html'
CASES=[('q9_critics','chowder_crossing','critic_bisquetta'),('q6_ginger','pierogi_pier','tea_master_po'),('q5_starter','sourdough_cavern_b2','starter_jar')]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(viewport={'width':960,'height':700}); errs=[]
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(U); pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(600)
    pg.evaluate("BEATS_API.AudioEngine.muted=true")
    for i in range(60):
        if pg.evaluate("BEATS_API.Game.screen")=='OVERWORLD': break
        pg.keyboard.press('Enter'); pg.wait_for_timeout(120)
    print('after Enter x',i,'screen',pg.evaluate("BEATS_API.Game.screen"),'map',pg.evaluate("BEATS_API.Game.state&&BEATS_API.Game.state.mapId"))
    pos0=pg.evaluate("[BEATS_API.Game.state.x,BEATS_API.Game.state.y]")
    moved=[]
    for k in ['ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowUp']:
        before=pg.evaluate("[BEATS_API.Game.state.x,BEATS_API.Game.state.y]"); pg.keyboard.down(k); pg.wait_for_timeout(30); pg.keyboard.up(k); pg.wait_for_timeout(250)
        moved.append((k,before,pg.evaluate("[BEATS_API.Game.state.x,BEATS_API.Game.state.y]")))
    print('taps',moved)
    pg.screenshot(path='/home/claude/beatsts/audit/kehai/v2.2b/ingame_start_B.png')
    for qid,m,npc in CASES:
        pg.evaluate("""([m,npc])=>{const g=BEATS_API.Game,n=BEATS_API.MAPS[m].npcs.find(n=>n.id===npc);g.state.mapId=m;g.state.x=n.x;g.state.y=n.y+1;g.screen='OVERWORLD'}""",[m,npc])
        pg.keyboard.press('ArrowUp'); pg.wait_for_timeout(200)
        pg.keyboard.press('z'); pg.wait_for_timeout(200)
        texts=[]
        for _ in range(8):
            t=pg.evaluate("(()=>{const g=BEATS_API.Game;return g.screen==='DIALOG'?JSON.stringify(g.dialog||g.dialogLines||g.dlg||'').slice(0,140):null})()")
            if not t: break
            texts.append(t); pg.keyboard.press('z'); pg.wait_for_timeout(150)
        done=pg.evaluate("q=>!!BEATS_API.Game.state.quests[q]",qid)
        print(qid,'| completed:',done,'| dialog:',texts[:1])
    print('pageerrors',len(errs),errs[:2])
    b.close()
