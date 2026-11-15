// 1337Boy vs mGBA on round 2: same ROM, same fixed-timing key script (1 frame down, 5 up), mailbox every 25 presses + 6 frames
const {keys,KEY,GBA}=require("./common.js");const fs=require("fs"),cp=require("child_process");
const ROM=process.argv[2];const rec=JSON.parse(fs.readFileSync("keys.json"));
const g=new GBA();g.loadRom(new Uint8Array(fs.readFileSync(ROM)));
let script="";const PRE=180;g.runFrame();for(let i=1;i<PRE;i++)g.runFrame();script+=`run ${PRE} 0\n`;
const out1=[];const SHOTS=[3,4,120,118,700,1500,2400,3693];
for(let i=0;i<rec.length;i++){const m=KEY[rec[i]];script+=`run 1 ${m}\nrun 5 0\n`;keys(g,m);g.runFrame();keys(g,0);for(let q=0;q<5;q++)g.runFrame();
 if((i+1)%25===0||i+1===rec.length){script+="peek 0203FC00 160\n";let s="";for(let a=0;a<160;a++)s+=g.read8(0x0203FC00+a).toString(16).padStart(2,"0");out1.push([i+1,s]);}
 if(SHOTS.includes(i+1)){script+=`shot /tmp/bg/k/r2mg_${i+1}.ppm\n`;require("./pngout.js")(g.fb,`r2b_${i+1}.png`);}}
fs.writeFileSync("mg2_script.txt",script);
const o2=cp.execSync(`/tmp/bg/mg/mg ${ROM} < mg2_script.txt`,{maxBuffer:1<<26}).toString().trim().split("\n");
let bad=0,first=null;for(let i=0;i<out1.length;i++){const a=out1[i][1].slice(0,8)+out1[i][1].slice(16),b=o2[i].slice(0,8)+o2[i].slice(16);if(a!==b){bad++;if(!first){let j=0;while(a[j]===b[j])j++;first=[out1[i][0],j>>1];}}}
console.log("checkpoints",out1.length,"mailbox mismatches (ignoring frame counter)",bad,first||"");
const r=g.read8(0x0203FC0C);console.log("1337Boy end screen",r,"map",g.read8(0x0203FC0D),"seals",g.read8(0x0203FC12));
