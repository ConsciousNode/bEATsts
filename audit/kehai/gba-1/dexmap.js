const {makeRef,keys,newRom,romState,refState,KEY}=require("./common.js");const fs=require("fs");
const rec=JSON.parse(fs.readFileSync("keys.json"));const api=makeRef(),G=api.Game,g=newRom();
let prevR=new Set([1]),prevO=new Set([1]);const pairs=[];
for(let i=0;i<rec.length;i++){G.pressButton(rec[i]);keys(g,KEY[rec[i]]);g.runFrame();keys(g,0);g.runFrame();
 if(!G.state)continue;const R=new Set(refState(api).seen.split(",").map(Number)),O=new Set(romState(g).seen.split(",").map(Number));
 const nr=[...R].filter(x=>!prevR.has(x)),no=[...O].filter(x=>!prevO.has(x));if(nr.length||no.length)pairs.push(`${nr.join("+")||"-"}→${no.join("+")||"-"}`);prevR=R;prevO=O;}
console.log(pairs.join("  "));const a=refState(api),b=romState(g);console.log("ref seen n",a.seen.split(",").length,"rom",b.seen.split(",").length);console.log("ref caught",a.caught,"| rom caught",b.caught);
