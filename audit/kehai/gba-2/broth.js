// Does the 151/151 Brotholomew reward fire? Save made by the delivered converter, loaded as a .sav, then only key presses.
const {makeRef,keys,newRom,romState,KEY}=require("./common.js");const fs=require("fs"),cp=require("child_process");
const enc=require("zlib");
function png(fb,f){const W=240,H=160,raw=Buffer.alloc(H*(1+W*4));for(let y=0;y<H;y++){raw[y*(1+W*4)]=0;for(let i=0;i<W*4;i++)raw[y*(1+W*4)+1+i]=fb[y*W*4+i];}
 const crcT=[];for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;crcT[n]=c>>>0;}
 const crc=b=>{let c=~0;for(const x of b)c=crcT[(c^x)&255]^(c>>>8);return(~c)>>>0;};
 const ch=(t,d)=>{const l=Buffer.alloc(4);l.writeUInt32BE(d.length);const td=Buffer.concat([Buffer.from(t),d]);const c=Buffer.alloc(4);c.writeUInt32BE(crc(td));return Buffer.concat([l,td,c]);};
 const ih=Buffer.alloc(13);ih.writeUInt32BE(W,0);ih.writeUInt32BE(H,4);ih[8]=8;ih[9]=6;
 fs.writeFileSync(f,Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),ch("IHDR",ih),ch("IDAT",enc.deflateSync(raw)),ch("IEND",Buffer.alloc(0))]));}
for(const n of [151,150]){
 const api=makeRef(),G=api.Game;G.startNewGame(0,"Brie",1);
 const ids=[];for(let i=1;i<=n;i++)ids.push(i);G.state.dexSeen=ids.slice();G.state.dexCaught=ids.slice();G.state.mapId="cruston_lab";G.state.x=9;G.state.y=6;G.state.dir="up";G.screen="OVERWORLD";G.dialog=null;
 const js=G.exportSaveJson(0);fs.writeFileSync(`s${n}.json`,js);
 cp.execSync(`python3 -I /tmp/bg/rb2/tools/html-save-to-sav.py s${n}.json -o s${n}.sav --slot 0`);
 const g=newRom();g.sram.set(fs.readFileSync(`s${n}.sav`));
 // same boot-to-continue sequence the delivered tests use after loading a save
 for(const b of ["A","A"]){keys(g,KEY[b]);g.runFrame();keys(g,0);g.runFrame();}
 const before=romState(g);
 keys(g,KEY.A);g.runFrame();keys(g,0);for(let i=0;i<4;i++)g.runFrame();
 png(g.fb,`broth_${n}.png`);
 G.pressButton("A");
 console.log(n,"ROM before:",before.screen,"map",before.map,`(${before.x},${before.y})`,before.dir,"caught n",before.caught.split(",").length,"| after:",romState(g).screen,"| REF dialog:",JSON.stringify((G.dialog&&(G.dialog.lines||G.dialog))||G.dialogLines||"").slice(0,90));
}
