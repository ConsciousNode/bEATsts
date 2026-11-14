const fs=require('fs'),vm=require('vm');const html=fs.readFileSync(process.argv[2],'utf8');
const js=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const sb={document:{getElementById:()=>({addEventListener(){},getContext:()=>null}),querySelectorAll:()=>[],createElement:()=>({click(){},remove(){},getContext:()=>null}),body:{appendChild(){}}},performance:{now:()=>0},requestAnimationFrame(){},addEventListener(){},Uint8Array,Uint16Array,Int8Array,Float32Array,Set,Map,Math,JSON,Array,Object,String,Number,Error,console,setTimeout(){},TextEncoder};sb.window=sb;vm.runInNewContext(js,sb);
const T=sb.BEATS_API.MUSIC_TRACKS;const t=T.overworld_bread;console.log('track keys',Object.keys(t));
for(const n of ['overworld_bread','town_noodle','battle_wild','credits']){const tr=T[n];const ch=tr.pulse1||tr.channels&&tr.channels.pulse1||tr.p1;const notes=ch||[];
 // split pulse1 into 16-note chunks, count distinct
 const flat=notes.map(x=>JSON.stringify(x));const chunks=new Set();for(let i=0;i<flat.length;i+=16)chunks.add(flat.slice(i,i+16).join());
 console.log(n,'pulse1 notes',flat.length,'distinct 16-note phrases',chunks.size,'of',Math.ceil(flat.length/16));}
