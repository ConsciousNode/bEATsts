// ROM side: bot route to checkpoint CP, then N random presses (seed). Every fuzz press sampled.
const {keys,KEY,GBA}=require("./common.js");const fs=require("fs");
const [ROM,CP,N,SEED,TAG]=[process.argv[2],+process.argv[3],+process.argv[4],+process.argv[5],process.argv[6]];
const rec=JSON.parse(fs.readFileSync("keys.json"));
function rng(s){return()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const POOL=[["A",22],["B",10],["UP",13],["DOWN",13],["LEFT",13],["RIGHT",13],["START",9],["SELECT",3]];
const r=rng(SEED);const fz=[];for(let i=0;i<N;i++){let x=r()*96;for(const[k,w]of POOL){if((x-=w)<0){fz.push(k);break;}}}
const presses=rec.slice(0,CP).concat(fz);
const g=new GBA();g.loadRom(new Uint8Array(fs.readFileSync(ROM)));while(g.read8(0x0203FC08)!==1)g.runFrame();for(let i=0;i<4;i++)g.runFrame();
const samples=[],bufs=[],fpp=[],fcs=[];
const grab=(i)=>{const q=new Uint8Array(240*160*3);for(let p=0;p<240*160;p++){q[p*3]=g.fb[p*4]>>3;q[p*3+1]=g.fb[p*4+1]>>3;q[p*3+2]=g.fb[p*4+2]>>3;}samples.push(i);bufs.push(Buffer.from(q));fcs.push(g.read32(0x0203FC04));};
for(let i=0;i<presses.length;i++){keys(g,KEY[presses[i]]);g.runFrame();keys(g,0);let w=0;while(g.read8(0x0203FC08)!==1&&w++<600)g.runFrame();for(let q=0;q<4;q++)g.runFrame();fpp.push(5+w);
  if(i>=CP)grab(i+1);}
fs.writeFileSync(`pd_${TAG}.json`,JSON.stringify({presses,samples,fpp,fcs,CP}));fs.writeFileSync(`pd_${TAG}.bin`,Buffer.concat(bufs));
console.log(TAG,"presses",presses.length,"sampled",samples.length);
