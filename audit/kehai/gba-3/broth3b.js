const {makeRef,keys,newRom,romState,KEY}=require("./common.js");const fs=require("fs");
for(const n of [151,150]){const g=newRom("/tmp/bg/rb3/beatsts.gba");g.sram.set(fs.readFileSync(`s${n}.sav`));
 const tap=(b,w=4)=>{keys(g,KEY[b]);g.runFrame();keys(g,0);for(let i=0;i<w;i++)g.runFrame();};
 tap("A");tap("A");let k=0;tap("A");while(romState(g).screen==="DIALOG"&&k<10){tap("A");k++;}
 const api=makeRef(),G=api.Game;G.importSaveJson(fs.readFileSync(`s${n}.json`,"utf8"),0);G.screen="OVERWORLD";G.pressButton("A");let r=0;while(G.screen==="DIALOG"&&r<10){G.pressButton("A");r++;}
 console.log(`${n} caught: ROM dialog closed after ${k} more A presses; REF after ${r}`);}
