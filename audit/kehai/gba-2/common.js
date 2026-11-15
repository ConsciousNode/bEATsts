// Kehai audit harness: shared setup. Emulator = unmodified 1337boy.html (sha e7bd2b3a…), ref = beatsts.html (sha b12be617…)
const fs=require("fs"),path=require("path"),vm=require("vm");
const ROOT=process.env.ROOT||"/tmp/bg/rb";
const emuHtml=fs.readFileSync(path.join(ROOT,"1337boy/1337boy.html"),"utf8");
const emuCode=emuHtml.slice(emuHtml.indexOf('<script id="b1337-core">')+24,emuHtml.indexOf("function initB1337App"));
const GBA=vm.runInNewContext(emuCode+"\n;GBA;",{Uint8Array,Uint16Array,Uint32Array,Int8Array,Int16Array,Int32Array,Float32Array,Float64Array,Uint8ClampedArray,DataView,ArrayBuffer,Math,console,Date,String,Number,Boolean,Array,Object,RegExp,Error,parseInt,parseFloat,isNaN});
function makeRef(){
  const h=fs.readFileSync(path.join(ROOT,"beatsts-2.2/beatsts.html"),"utf8");
  const r=h.indexOf("<!-- INLINE SCRIPT:");const s=h.slice(h.indexOf("<script>",r)+8,h.lastIndexOf("</script>"));
  const box={addEventListener:()=>{},document:{getElementById:()=>({value:"Brie",addEventListener:()=>{}}),querySelectorAll:()=>[],createElement:()=>({click:()=>{},remove:()=>{}}),body:{appendChild:()=>{}}},
    performance:{now:()=>0},requestAnimationFrame:()=>{},Uint8Array,Uint16Array,Uint32Array,Int32Array,Float32Array,Float64Array,DataView,ArrayBuffer,Set,Map,Math,JSON,Array,Object,String,Number,Error,console};
  box.window=box;vm.runInNewContext(s,box);box.BEATS_API.AudioEngine.muted=true;return box.BEATS_API;
}
const KEY={A:1,B:2,SELECT:4,START:8,RIGHT:16,LEFT:32,UP:64,DOWN:128,R:256,L:512};
const SCREENS=["TITLE","SLOTS","STARTER","OVERWORLD","DIALOG","BATTLE","MENU","DEX","PARTY","BOX","BAG","SHOP","LEARN_MOVE","OPTIONS","CONTROLS","CREDITS","NAME_ENTRY"];
const DIRS=["down","up","left","right"];
// Input only through the KEYINPUT register value the emulator exposes (same as setKeys in TESTING.md)
function keys(g,m){g.keyMask=(~m)&0x3FF;g.io16[0x130>>1]=g.keyMask;}
function newRom(file){const g=new GBA();g.loadRom(new Uint8Array(fs.readFileSync(file||path.join(ROOT,"beatsts.gba"))));g.runFrame();let n=0;while(g.read8(0x0203FC08)!==1&&n++<600)g.runFrame();return g;}
const MB=0x0203FC00;
function bits(g,off){const a=[];for(let i=0;i<151;i++)if(g.read8(MB+off+(i>>3))&(1<<(i&7)))a.push(i+1);return a.join(",");}
function romState(g){const p=[];const n=g.read8(MB+0x19);for(let i=0;i<n;i++){const b=MB+0x48+i*12;p.push([g.read8(b),g.read8(b+1),g.read16(b+2),g.read16(b+4)].join("/"));}
  return {screen:SCREENS[g.read8(MB+0xC)],map:g.read8(MB+0xD),x:g.read8(MB+0xE),y:g.read8(MB+0xF),dir:DIRS[g.read8(MB+0x10)],night:g.read8(MB+0x11),seals:g.read8(MB+0x12),gold:g.read32(MB+0x14)>>>0,champ:g.read8(MB+0x18),party:p.join(" "),seen:bits(g,0x20),caught:bits(g,0x34),box:g.read16(MB+0x98),steps:g.read32(MB+0x94)>>>0,lag:g.read16(MB+0xA)};}
function refState(api){const G=api.Game,s=G.state,M=Object.keys(api.MAPS);
  return {screen:G.screen,map:M.indexOf(s.mapId),x:s.x,y:s.y,dir:s.dir,night:s.isNight?1:0,seals:s.seals.length,gold:s.gold,champ:s.championBeaten?1:0,
   party:s.party.map(b=>[b.speciesId,b.level,b.hp,b.maxHp].join("/")).join(" "),seen:[...new Set(s.dexSeen)].sort((a,b)=>a-b).join(","),caught:[...new Set(s.dexCaught)].sort((a,b)=>a-b).join(","),box:s.box.length,steps:s.steps,lag:0};}
function diff(a,b){const d=[];for(const k in a)if(String(a[k])!==String(b[k]))d.push(`${k}: rom=${a[k]} ref=${b[k]}`);return d;}
module.exports={GBA,makeRef,KEY,keys,newRom,romState,refState,diff,ROOT};
