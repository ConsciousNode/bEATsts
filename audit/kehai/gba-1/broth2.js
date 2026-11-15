const {makeRef,keys,newRom,romState,KEY}=require("./common.js");const fs=require("fs");const MB=0x0203FC00;
for(const n of [151,150]){const g=newRom();g.sram.set(fs.readFileSync(`s${n}.sav`));
 const tap=(b,w=1)=>{keys(g,KEY[b]);g.runFrame();keys(g,0);for(let i=0;i<w;i++)g.runFrame();};
 tap("A",2);tap("A",2);let s=romState(g);console.log(n,"after load",s.screen,s.map,s.x,s.y,s.dir,"accept",g.read8(MB+8));
 for(let k=0;k<4;k++){tap("A",8);s=romState(g);console.log("  A ->",s.screen,"accept",g.read8(MB+8));if(s.screen==="DIALOG")break;}
 for(let i=0;i<30;i++)g.runFrame();require("./pngout.js")(g.fb,`broth2_${n}.png`);
 const api=makeRef(),G=api.Game;G.importSaveJson(fs.readFileSync(`s${n}.json`,"utf8"),0);G.screen="OVERWORLD";G.pressButton("A");console.log("  REF:",G.screen,JSON.stringify(G.dialogQueue).slice(0,100));}
