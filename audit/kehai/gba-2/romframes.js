// ROM side of my pixel differential: replay presses (bot route, then 300 random presses from the end state),
// waiting like the shipped harness's human model (press 1 frame, release until accepting + 4 frames).
// Writes sampled frames quantized to BGR555 (r>>3,g>>3,b>>3) + the full press list.
const {keys,KEY,GBA}=require("./common.js");const fs=require("fs");
const ROM=process.argv[2];const rec=JSON.parse(fs.readFileSync("keys.json"));
function rng(s){return()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const POOL=[["A",25],["B",10],["UP",13],["DOWN",13],["LEFT",13],["RIGHT",13],["START",8],["SELECT",3]];
const r=rng(777);const fuzz=[];for(let i=0;i<300;i++){let x=r()*98;for(const[k,w]of POOL){if((x-=w)<0){fuzz.push(k);break;}}}
// fuzz is spliced in at press 1500 (mid-game) and the bot continues after it would desync the bot, so: bot to 1500, then fuzz.
const presses=rec.slice(0,1500).concat(fuzz);
const g=new GBA();g.loadRom(new Uint8Array(fs.readFileSync(ROM)));while(g.read8(0x0203FC08)!==1)g.runFrame();for(let i=0;i<4;i++)g.runFrame();
const samples=[],bufs=[],fpp=[];
const grab=(i)=>{const q=new Uint8Array(240*160*3);for(let p=0;p<240*160;p++){q[p*3]=g.fb[p*4]>>3;q[p*3+1]=g.fb[p*4+1]>>3;q[p*3+2]=g.fb[p*4+2]>>3;}samples.push(i);bufs.push(Buffer.from(q));};
grab(0);
for(let i=0;i<presses.length;i++){const f0=g.read32(0x0203FC04);keys(g,KEY[presses[i]]);g.runFrame();keys(g,0);let w=0;while(g.read8(0x0203FC08)!==1&&w++<600)g.runFrame();for(let q=0;q<4;q++)g.runFrame();fpp.push(5+w);
  if((i+1)%7===0||i>=1500)grab(i+1);}
fs.writeFileSync("pd_presses.json",JSON.stringify({presses,samples,fpp}));fs.writeFileSync("pd_rom.bin",Buffer.concat(bufs));
console.log("presses",presses.length,"sampled frames",samples.length);
