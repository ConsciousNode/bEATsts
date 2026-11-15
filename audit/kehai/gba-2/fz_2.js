// Same as fuzz.js but waits for the mailbox "accepting input" flag before each press (as a person would)
// and records how long the ROM was busy (frames) after each press.
const {makeRef,keys,newRom,romState,refState,diff,KEY}=require("./common.js");const fs=require("fs");
const rec=JSON.parse(fs.readFileSync("keys.json"));const romFile=process.argv[2];const N=+(process.argv[3]||400);
const cps=(process.argv[4]||"0,300,700,1100,1500,1900,2300,2700,3100,3500,3693").split(",").map(Number);
function rng(s){return()=>{s|=0;s=s+0x6D2B79F5|0;let t=Math.imul(s^s>>>15,1|s);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const POOL=[["A",25],["B",10],["UP",13],["DOWN",13],["LEFT",13],["RIGHT",13],["START",8],["SELECT",3]];
function pick(r){let x=r()*98;for(const[k,w]of POOL){if((x-=w)<0)return k;}return "A";}
let total=0,fails=[],busy=[];
for(const cp of cps){
  const api=makeRef(),G=api.Game,g=newRom(romFile);let first=null;
  const press=(b,tag)=>{let w=0;while(g.read8(0x0203FC08)!==1&&w<600){g.runFrame();w++;}busy.push(w);
    G.pressButton(b);keys(g,KEY[b]);g.runFrame();keys(g,0);for(let q=0;q<2;q++)g.runFrame();
    if(G.state){const d=diff(romState(g),refState(api));if(d.length&&!first)first={tag,b,d:d.slice(0,4)};}};
  for(let i=0;i<cp;i++)press(rec[i],"bot#"+(i+1));
  const r=rng(cp*7919+13);for(let i=0;i<N;i++){press(pick(r),"fuzz#"+(i+1));total++;}
  // settle and compare once more
  let w=0;while(g.read8(0x0203FC08)!==1&&w<600){g.runFrame();w++;}
  const d=diff(romState(g),refState(api));if(d.length&&!first)first={tag:"end",d:d.slice(0,4)};
  const rs=romState(g);console.log(`cp ${cp}: ${first?"DIVERGE "+JSON.stringify(first):"match"} | end ${rs.screen} map${rs.map} (${rs.x},${rs.y}) seals${rs.seals} party ${rs.party.split(" ").length} seen ${rs.seen.split(",").length}`);
  if(first)fails.push(cp);
}
busy.sort((a,b)=>a-b);const hist={};for(const b of busy)hist[b]=(hist[b]||0)+1;
console.log("fuzz presses",total,"checkpoints diverged:",fails.length?fails.join(","):"none");
console.log("busy frames before a press was accepted: max",busy.at(-1),"p99",busy[Math.floor(busy.length*0.99)],"hist",JSON.stringify(hist));
