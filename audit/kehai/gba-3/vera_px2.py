import json
from playwright.sync_api import sync_playwright
from PIL import Image
sav=open('/tmp/bg/k3/vera.json').read()
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/chromium",args=["--no-sandbox"]); pg=b.new_page()
    pg.add_init_script("window.requestAnimationFrame = () => 0;")
    pg.goto("file:///tmp/bg/rb3/beatsts-2.2/beatsts.html"); pg.wait_for_timeout(300)
    pg.evaluate("s => { const G=window.BEATS_API.Game; window.BEATS_API.AudioEngine.muted=true; G.importSaveJson(s,0); G.screen='OVERWORLD'; G.dialogQueue=[]; G.pressButton('A'); }", sav)
    for k in range(1,7):
        rf=pg.evaluate("() => { const G=window.BEATS_API.Game; for(let i=0;i<30;i++) G.update(1/60); G.render(); const d=G.ctx.getImageData(0,0,240,160).data; const o=[]; for(let i=0;i<d.length;i+=4) o.push([d[i]>>3,d[i+1]>>3,d[i+2]>>3]); return o; }")
        rom=Image.open(f'/tmp/bg/k3/vera_rom_p{k}.png').convert('RGB'); rp=[(r>>3,g>>3,bb>>3) for r,g,bb in rom.getdata()]
        # compare only the dialog box rows (y 104..159); the map above animates on its own clock
        diff=sum(1 for i in range(104*240,160*240) if tuple(rf[i])!=rp[i])
        
        if diff:
            xs=[i%240 for i in range(104*240,160*240) if tuple(rf[i])!=rp[i]]; ys=[i//240 for i in range(104*240,160*240) if tuple(rf[i])!=rp[i]]
            print("   bbox x",min(xs),max(xs),"y",min(ys),max(ys))
            im=Image.new('RGB',(240,112)); im.paste(rom.crop((0,104,240,160)),(0,0))
            ri=Image.new('RGB',(240,56)); ri.putdata([(a<<3,b2<<3,c<<3) for a,b2,c in rf[104*240:160*240]]); im.paste(ri,(0,56)); im.resize((720,336),Image.NEAREST).save(f'/tmp/bg/k3/vera_diff_p{k}.png')
        print(f"page {k}: dialog-box pixels differing ROM vs reference: {diff} / {56*240}")
        pg.evaluate("() => window.BEATS_API.Game.pressButton('A')")
    b.close()
