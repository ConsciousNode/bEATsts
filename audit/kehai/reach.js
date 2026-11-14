// Kehai audit: which species can a player actually obtain?
const fs=require('fs'),vm=require('vm');const html=fs.readFileSync('/home/claude/beatsts/beatsts.html','utf8');
const js=html.match(/<!-- INLINE SCRIPT:[\s\S]*?<script>([\s\S]*?)<\/script>/)[1];
const sb={document:{getElementById:()=>({addEventListener(){}}),querySelectorAll:()=>[],createElement:()=>({click(){},remove(){}}),body:{appendChild(){}}},performance:{now:()=>0},requestAnimationFrame(){},addEventListener(){},Uint8Array,Float32Array,Set,Map,Math,JSON,Array,Object,String,Number,Error,console};sb.window=sb;vm.runInNewContext(js,sb);const A=sb.BEATSTS?sb:sb.BEATS_API;
const L=A.BEATSTS,M=A.MAPS;const starters=JSON.parse(process.argv[2]);
const ok=new Set(starters);const perMap={};
for(const id in M){perMap[id]=(M[id].wildPool||[]).map(w=>w[0]);perMap[id].forEach(s=>ok.add(s))}
ok.add(151);let grew=true;while(grew){grew=false;for(const b of L)if(ok.has(b.id)&&b.evo&&b.evo.to&&!ok.has(b.evo.to)){ok.add(b.evo.to);grew=true}}
console.log('wild pools per map:',Object.entries(perMap).map(([k,v])=>k+':'+v.length).join(' '));
console.log('obtainable species (starters+wild+evolutions+#151):',ok.size,'of',L.length);
const fam={};for(const b of L){fam[b.family]=fam[b.family]||[0,0];fam[b.family][1]++;if(ok.has(b.id))fam[b.family][0]++}console.log('by family obtainable/total',JSON.stringify(fam));
const trainerOnly=new Set();for(const t of Object.values(A.TRAINERS))for(const p of t.party)if(!ok.has(p.id))trainerOnly.add(p.id);
console.log('seen only in trainer parties:',trainerOnly.size,'| never appear anywhere:',L.filter(b=>!ok.has(b.id)&&!trainerOnly.has(b.id)).length);
