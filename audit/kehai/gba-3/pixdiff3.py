# Independent pixel differential, real Chromium. Reference advanced by exactly the ROM's frame count per press
# via its own update(1/60). Only alignment: ref frameCount set to the ROM's frame counter before render
# (phase of the 18-frame tile animation, which counts from boot). Each diff is classified by the reference's
# own live timers: fade (transitionTimer>0), move flash (animTimer>0), or other.
import json, sys, collections
from playwright.sync_api import sync_playwright
from PIL import Image
TAG=sys.argv[1]; d=json.load(open(f"pd_{TAG}.json")); rom=open(f"pd_{TAG}.bin","rb").read(); FR=240*160*3
P=d["presses"]; S=set(d["samples"]); fpp=d["fpp"]; fcs=d["fcs"]
res=[]; saved=collections.Counter()
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/usr/bin/chromium",args=["--no-sandbox"]); pg=b.new_page()
    errs=[]; pg.on("pageerror",lambda e: errs.append(str(e)))
    pg.add_init_script("window.requestAnimationFrame = () => 0;")
    pg.goto("file:///tmp/bg/rb3/beatsts-2.2/beatsts.html"); pg.wait_for_timeout(300)
    pg.evaluate("() => { window.BEATS_API.AudioEngine.muted = true; }")
    # fast-forward bot part in one evaluate
    pg.evaluate("([ps,fs]) => { const g=window.BEATS_API.Game; for (let i=0;i<ps.length;i++){ g.pressButton(ps[i]); for(let k=0;k<fs[i];k++) g.update(1/60);} }",[P[:d["CP"]],fpp[:d["CP"]]])
    si=0
    for i in range(d["CP"],len(P)):
        out=pg.evaluate("""([b,n,fc]) => { const g=window.BEATS_API.Game; g.pressButton(b); for(let k=0;k<n;k++) g.update(1/60);
            const fade=g.transitionTimer>0, flash=(g.screen==='BATTLE'&&g.animTimer>0); g.frameCount=fc; g.render();
            const dd=g.ctx.getImageData(0,0,240,160).data; const o=new Array(240*160*3);
            for(let i2=0,j=0;i2<dd.length;i2+=4,j+=3){o[j]=dd[i2]>>3;o[j+1]=dd[i2+1]>>3;o[j+2]=dd[i2+2]>>3;}
            return {o, scr:g.screen, fade, flash}; }""",[P[i],fpp[i],fcs[si]])
        rb=rom[si*FR:(si+1)*FR]; rf=out["o"]
        bad=sum(1 for k in range(0,FR,3) if rf[k]!=rb[k] or rf[k+1]!=rb[k+1] or rf[k+2]!=rb[k+2])
        cls="match" if bad==0 else ("fade" if out["fade"] else ("flash" if out["flash"] else "OTHER"))
        res.append((i+1,P[i],out["scr"],bad,cls))
        if cls=="OTHER" and saved[out["scr"]]<3:
            saved[out["scr"]]+=1
            im=Image.new("RGB",(480,160)); px=[]
            for y in range(160):
                for x in range(480):
                    if x<240: j=(y*240+x)*3; px.append((rb[j]<<3,rb[j+1]<<3,rb[j+2]<<3))
                    else: j=(y*240+x-240)*3; px.append((rf[j]<<3,rf[j+1]<<3,rf[j+2]<<3))
            im.putdata(px); im.resize((960,320),Image.NEAREST).save(f"pd3_{TAG}_{out['scr']}_press{i+1}_{bad}px.png")
        si+=1
    b.close()
json.dump(res,open(f"pd3_{TAG}_res.json","w"))
c=collections.Counter(r[4] for r in res); print(TAG,"frames",len(res),dict(c),"page errors",len(errs))
oth=collections.Counter(r[2] for r in res if r[4]=="OTHER"); print("  OTHER by screen",dict(oth))
for r in [r for r in res if r[4]=="OTHER"][:12]: print("  ",r)
