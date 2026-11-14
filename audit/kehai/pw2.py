# Kehai audit: completion bot variants that avoid direct state edits
import re, json
from playwright.sync_api import sync_playwright
src=open('/home/claude/beatsts/tests/run-all.js').read()
bot=[x for x in re.findall(r"wd\.exec\(`([\s\S]*?)`\)", src) if 'walkTo' in x][0]
FREE="g.state.gold -= 1750; g.state.bag.grand_feast = (g.state.bag.grand_feast || 0) + 5;"
BUY="challengeNpc('mart_chowder'); var g0=g.state.gold; for (let k=0;k<7;k++) g.pressButton('DOWN'); for (let k=0;k<5;k++) g.pressButton('A'); g.pressButton('B'); bought=(g0-g.state.gold)/350;"
shop=bot.replace(FREE,"").replace("challengeNpc('bisque_npc');","challengeNpc('bisque_npc'); "+BUY).replace("let steps = 0, battles = 0;","let steps = 0, battles = 0, bought = 0;").replace("party: g.state.party","bought, party: g.state.party")
assert shop.count('mart_chowder')==1
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page()
    for seed in [4242]:
        pg.goto('http://127.0.0.1:8765/beatsts.html'); pg.wait_for_timeout(300)
        print('BOT buys at real mart:', json.dumps(pg.evaluate("(()=>{"+shop+"})()")))
    # seeds sensitivity, verbatim bot
    for seed in [1,7,99,2026]:
        pg.goto('http://127.0.0.1:8765/beatsts.html'); pg.wait_for_timeout(200)
        r=pg.evaluate("(()=>{"+bot.replace("'BotChef', 1, 4242","'BotChef', 1, %d"%seed)+"})()")
        print('verbatim bot seed',seed,'->',r['screen'],'seals',r['seals'],'battles',r['battles'],r.get('err',''))
    b.close()
