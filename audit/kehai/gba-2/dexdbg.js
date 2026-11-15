const {makeRef,keys,KEY,GBA,romState}=require("./common.js");const fs=require("fs");
const d=JSON.parse(fs.readFileSync("pd_presses.json"));const api=makeRef(),G=api.Game;
const g=new GBA();g.loadRom(new Uint8Array(fs.readFileSync("/tmp/bg/rb2/beatsts.gba")));while(g.read8(0x0203FC08)!==1)g.runFrame();for(let i=0;i<4;i++)g.runFrame();
for(let i=0;i<1531;i++){const b=d.presses[i];G.pressButton(b);for(let k=0;k<d.fpp[i];k++)G.update(1/60);keys(g,KEY[b]);g.runFrame();keys(g,0);let w=0;while(g.read8(0x0203FC08)!==1&&w++<600)g.runFrame();for(let q=0;q<4;q++)g.runFrame();
 if(i>=1505)console.log(i+1,b,"ref",G.screen,"dexCursor",G.dexCursor,"dexScroll",G.dexScroll,"| rom",romState(g).screen);
 if(i+1===1526)require("./pngout.js")(g.fb,"dex1526_rom.png");}
