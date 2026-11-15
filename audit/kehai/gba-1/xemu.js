// 1337Boy vs mGBA: same ROM, same key script, mailbox bytes compared every 25 presses + framebuffer at a few points
const {keys,newRom,KEY}=require("./common.js");const fs=require("fs"),cp=require("child_process");
const rec=JSON.parse(fs.readFileSync("keys.json"));let script="",pts=[];const g=newRom();const out1=[];
// mGBA: newRom() already ran 1 frame before the first press in 1337Boy, mirror that
script+="run 1 0\n";
const SHOTS=[3,120,700,1500,2400,3693];
for(let i=0;i<rec.length;i++){const m=KEY[rec[i]];script+=`run 1 ${m}\nrun 1 0\n`;keys(g,m);g.runFrame();keys(g,0);g.runFrame();
 if((i+1)%25===0||i+1===rec.length){script+="peek 0203FC00 160\n";let s="";for(let a=0;a<160;a++)s+=g.read8(0x0203FC00+a).toString(16).padStart(2,"0");out1.push([i+1,s]);}
 if(SHOTS.includes(i+1)){script+=`shot /tmp/bg/k/mg_${i+1}.ppm\n`;require("./pngout.js")(g.fb,`b1337_${i+1}.png`);}}
fs.writeFileSync("mg_script.txt",script);
const o2=cp.execSync("/tmp/bg/mg/mg /tmp/bg/rb/beatsts.gba < mg_script.txt",{maxBuffer:1<<26}).toString().trim().split("\n");
let bad=0;for(let i=0;i<out1.length;i++)if(out1[i][1]!==o2[i]){if(bad<3){let j=0;while(out1[i][1][j]===o2[i][j])j++;console.log("press",out1[i][0],"first differing mailbox byte offset",(j>>1).toString(16));}bad++;}
console.log("checkpoints",out1.length,"mailbox mismatches",bad);
let bad2=0,first=null;for(let i=0;i<out1.length;i++){const a=out1[i][1].slice(0,8)+out1[i][1].slice(16),b=o2[i].slice(0,8)+o2[i].slice(16);if(a!==b){bad2++;if(!first){let j=0;while(a[j]===b[j])j++;first=[out1[i][0],((j>>1)+((j>>1)>=4?4:0)).toString(16)];}}}
console.log("ignoring frameCounter: mismatches",bad2,first||"","| frameCounter 1337Boy vs mGBA at end:",parseInt(out1.at(-1)[1].slice(8,16).match(/../g).reverse().join(""),16),parseInt(o2.at(-1).slice(8,16).match(/../g).reverse().join(""),16));
