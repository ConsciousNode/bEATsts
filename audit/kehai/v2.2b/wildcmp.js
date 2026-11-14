const fs=require('fs'),vm=require('vm');
function load(p){const html=fs.readFileSync(p,'utf8');const js=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const sb={document:{getElementById:()=>({addEventListener(){},getContext:()=>null}),querySelectorAll:()=>[],createElement:()=>({click(){},remove(){},getContext:()=>null}),body:{appendChild(){}}},performance:{now:()=>0},requestAnimationFrame(){},addEventListener(){},Uint8Array,Uint16Array,Int8Array,Float32Array,Set,Map,Math,JSON,Array,Object,String,Number,Error,console,setTimeout(){},TextEncoder};sb.window=sb;vm.runInNewContext(js,sb);return sb.BEATS_API}
for(const p of process.argv.slice(2)){const A=load(p);const wild=new Map();
for(const m of Object.values(A.MAPS))for(const e of (m.wildPool||[])){if(!wild.has(e[0]))wild.set(e[0],[]);wild.get(e[0]).push(m.id+'@L'+(e[1]??'?')+(e[2]!==undefined?'-'+e[2]:''))}
const B=A.BEATSTS;const evolved=B.filter(b=>B.some(o=>o.evo&&(o.evo.to===b.id||o.evo.into===b.id||o.evo.id===b.id||(Array.isArray(o.evo)&&o.evo.some(e=>e.to===b.id||e.into===b.id)))));
const keys=Object.keys(B[0]);
console.log(p.slice(-40),'| species in wild:',wild.size,'| evolved species (by evolvesTo):',evolved.length,'| evolved also wild:',evolved.filter(b=>wild.has(b.id)).length);
console.log('  species keys:',keys.join(','));
const ev=evolved.filter(b=>wild.has(b.id)).slice(0,6).map(b=>b.id+' '+b.name+' '+wild.get(b.id).slice(0,3).join(' '));console.log('  e.g.',ev.join(' | '));}
