// Kehai audit 2.1: map role similarity (own role mapping), dialogue reachability, NPC names, interiors/doors
const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[2],'utf8');
const js=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const sb={document:{getElementById:()=>({addEventListener(){},getContext:()=>null}),querySelectorAll:()=>[],createElement:()=>({click(){},remove(){},getContext:()=>null}),body:{appendChild(){}}},performance:{now:()=>0},requestAnimationFrame(){},addEventListener(){},Uint8Array,Uint16Array,Int8Array,Float32Array,Set,Map,Math,JSON,Array,Object,String,Number,Error,console,setTimeout(){},TextEncoder};sb.window=sb;vm.runInNewContext(js,sb);
const A=sb.BEATS_API,M=A.MAPS,ids=Object.keys(M);
console.log('API keys:',Object.keys(A).filter(k=>/ROLE|TILE|DIALOG|BANK|LINES/i.test(k)).join(','));
const R=A.TILE_ROLES; console.log('TILE_ROLES type',typeof R, R&&Object.keys(R).length);
const role=t=>R?(R[t]!==undefined?R[t]:'t'+t):t;
const W=m=>m.w||m.width||30, H=m=>m.h||m.height||18;
const sizes={};ids.forEach(id=>{const k=W(M[id])+'x'+H(M[id]);sizes[k]=(sizes[k]||0)+1});console.log('map sizes',JSON.stringify(sizes));
let pairs=[];for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){const a={...M[ids[i]],grid:Array.from(M[ids[i]].grid)},b={...M[ids[j]],grid:Array.from(M[ids[j]].grid)};if(W(a)!==W(b)||H(a)!==H(b))continue;let s=0,n=a.grid.length;for(let k=0;k<n;k++)if(role(a.grid[k])===role(b.grid[k]))s++;pairs.push([s/n,ids[i],ids[j]])}
pairs.sort((x,y)=>y[0]-x[0]);console.log('same-size pairs',pairs.length,'| >50% same role:',pairs.filter(p=>p[0]>0.5).length,'| top:',pairs.slice(0,5).map(p=>`${p[1]}~${p[2]} ${(p[0]*100).toFixed(1)}%`).join(', '));
// shifted similarity for different-size maps: skip. Template detection: compare non-floor role masks
// dialogue
let lines=[],npcs=0,named=new Set(),numbered=0;
for(const id of ids)for(const n of M[id].npcs||[]){npcs++;named.add(n.name);if(/\d/.test(n.name||''))numbered++;for(const k of ['lines','nightLines','dialog'])(Array.isArray(n[k])?n[k]:n[k]?[n[k]]:[]).forEach(x=>lines.push(x))}
const signs=ids.flatMap(id=>(M[id].signs||[]).map(s=>s.text||s));
console.log('NPCs',npcs,'distinct names',named.size,'names with digits',numbered,'| npc lines',lines.length,'unique',new Set(lines).size,'| signs',signs.length);
const generic=[...named].filter(n=>/^(Villager|Local|Townsperson|Citizen|Resident|Visitor)\b/i.test(n));console.log('generic-ish names:',generic.length,generic.slice(0,8).join(', '));
const u=[...new Set(lines)];[5,100,300,500,700].forEach(i=>u[i]&&console.log('  >',u[i].slice(0,140)));
// templated lines: mask capitalized words
const tm=new Set(u.map(l=>l.replace(/[A-Z][a-z]+/g,'X').replace(/\d+/g,'N')));console.log('unique after masking Capitalized words:',tm.size);
{const pre={};for(const l of u){const k=l.split(' ').slice(0,4).join(' ');pre[k]=(pre[k]||0)+1}
 const top=Object.entries(pre).sort((a,b)=>b[1]-a[1]);console.log('lines sharing a 4-word opening with >=5 others:',top.filter(t=>t[1]>=6).reduce((s,t)=>s+t[1],0),'of',u.length);
 console.log('top openings:',top.slice(0,10).map(t=>`"${t[0]}" x${t[1]}`).join(' | '));
 // skeleton: drop words that vary between lines sharing opening -> estimate templates via LCS-free approach: replace each word that appears in < 3% of lines with *
 const df={};u.forEach(l=>new Set(l.toLowerCase().replace(/[^a-z' ]/g,'').split(' ')).forEach(w=>df[w]=(df[w]||0)+1));
 const sk=new Set(u.map(l=>l.toLowerCase().replace(/[^a-z' ]/g,'').split(' ').map(w=>df[w]>=8?w:'*').join(' ')));console.log('distinct skeletons (rare words masked):',sk.size,'of',u.length);}
