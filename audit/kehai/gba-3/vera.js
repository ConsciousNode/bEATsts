// Dialog paging check on round 3: real .sav (delivered converter) parked facing an NPC with a 2-page line;
// press A and count presses until the dialog closes, ROM vs reference; dump each ROM page as PNG + quantized frame.
const {makeRef,keys,newRom,romState,KEY}=require("./common.js");const fs=require("fs"),cp=require("child_process");
const api=makeRef();const mid="cruston_town";const n=api.MAPS.cruston_town.npcs.find(x=>x.name==="Baker Vera");const spot={x:n.x,y:n.y+1,d:"up"};
console.log("NPC",n.id,"on",mid,"at",n.x,n.y,"stand",JSON.stringify(spot));
const G=api.Game;G.startNewGame(0,"Brie",1);G.state.mapId=mid;G.state.x=spot.x;G.state.y=spot.y;G.state.dir=spot.d;G.screen="OVERWORLD";G.dialogQueue=[];
fs.writeFileSync("vera.json",G.exportSaveJson(0));cp.execSync("python3 -I /tmp/bg/rb3/tools/html-save-to-sav.py vera.json -o vera.sav --slot 0");
// reference
const R=makeRef(),RG=R.Game;RG.importSaveJson(fs.readFileSync("vera.json","utf8"),0);RG.screen="OVERWORLD";RG.dialogQueue=[];
RG.pressButton("A");const refPages=[];while(RG.screen==="DIALOG"&&refPages.length<10){refPages.push(RG.dialogQueue[0]);RG.pressButton("A");}
// ROM
const g=newRom("/tmp/bg/rb3/beatsts.gba");g.sram.set(fs.readFileSync("vera.sav"));
const tap=b=>{keys(g,KEY[b]);g.runFrame();keys(g,0);let w=0;while(g.read8(0x0203FC08)!==1&&w++<600)g.runFrame();for(let i=0;i<4;i++)g.runFrame();};
tap("A");tap("A");tap("A");let romPages=0;while(romState(g).screen==="DIALOG"&&romPages<10){require("./pngout.js")(g.fb,`vera_rom_p${romPages+1}.png`);romPages++;tap("A");}
console.log("REF pages",refPages.length,JSON.stringify(refPages).slice(0,300));console.log("ROM dialog boxes before closing:",romPages);
