// Kehai audit v2: reachability closure, structural map similarity (tile roles, not IDs), per-track music length, font bytes
const fs=require('fs'),vm=require('vm'),crypto=require('crypto');
const html=fs.readFileSync(process.argv[2],'utf8');
const js=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const sb={document:{getElementById:()=>({addEventListener(){},getContext:()=>null}),querySelectorAll:()=>[],createElement:()=>({click(){},remove(){},getContext:()=>null}),body:{appendChild(){}}},performance:{now:()=>0},requestAnimationFrame(){},addEventListener(){},Uint8Array,Uint16Array,Int8Array,Float32Array,Set,Map,Math,JSON,Array,Object,String,Number,Error,console,setTimeout(){},TextEncoder};sb.window=sb;vm.runInNewContext(js,sb);
const A=sb.BEATS_API,L=A.BEATSTS,M=A.MAPS;
// reachability: starters + wild pools + evolutions + #151 (gifts not counted, so this is a lower bound)
const ok=new Set([1,39,77,115,151]);for(const m of Object.values(M))(m.wildPool||[]).forEach(w=>ok.add(w[0]));
let gr=true;while(gr){gr=false;for(const b of L)if(ok.has(b.id)&&b.evo&&b.evo.to&&!ok.has(b.evo.to)){ok.add(b.evo.to);gr=true}}
console.log('obtainable (starters+wild+evolution+#151):',ok.size,'/ 151');
const minTierBad=L.filter(b=>{for(const m of Object.values(M))for(const w of m.wildPool||[])if(w[0]===b.id)return false;return false});
// structural similarity: map each tile to a role
const ids=Object.keys(M);const role=t=>t>=10&&t<58?((t-10)%12):(t>=58?100+t:t);
const R=ids.map(id=>M[id].grid.map(role));let worst=[];
for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){let s=0;for(let k=0;k<540;k++)if(R[i][k]===R[j][k])s++;worst.push([s/540,ids[i],ids[j]]);
}
worst.sort((a,b)=>b[0]-a[0]);console.log('map pairs >60% identical by tile ROLE:',worst.filter(w=>w[0]>0.6).length,'of',worst.length);
console.log('  top:',worst.slice(0,6).map(w=>`${w[1]}~${w[2]} ${(w[0]*100).toFixed(0)}%`).join(', '));
let idSame=0;for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){let s=0;for(let k=0;k<540;k++)if(M[ids[i]].grid[k]===M[ids[j]].grid[k])s++;if(s/540>0.6)idSame++}console.log('map pairs >60% identical by tile ID (the test):',idSame);
// music
const T=A.MUSIC_TRACKS;const names=Object.keys(T);let tot=0,short=[];
for(const n of names){const buf=A.renderTrackOffline(n);const sec=buf.length/(buf.sampleRate||22050);tot+=sec;if(sec<45&&!/victory|healing|evolution|jingle|fanfare/i.test(n))short.push(n+' '+sec.toFixed(1)+'s');}
console.log('tracks',names.length,'total',(tot/60).toFixed(2),'min | overworld/town/battle under 45s:',short.length?short.join(', '):'none');
// fonts
const hex=f=>Buffer.from(fs.readFileSync(f,'utf8').trim().split('\n').map(l=>l.split(' ')[1]).join(''),'hex');
console.log('font candidates on API:',Object.keys(A).filter(k=>/font/i.test(k)).join(','));
{const b=A.renderTrackOffline(names[0]);console.log('render returns',typeof b,b&&b.constructor&&b.constructor.name,Object.keys(b).slice(0,6),b.length);
 const r=[];for(const n of names){const x=A.renderTrackOffline(n);const arr=x.samples||x.data||x;const sr=x.sampleRate||22050;const sec=(x.duration)||(arr.length/sr);r.push(n+':'+(+sec).toFixed(0)+'s')}console.log(r.join(' '));}
{const f=p=>fs.readFileSync(p,'utf8').trim().split('\n').map(l=>l.trim().split(/\s+/)[1]);const s=f('/home/claude/cnsw-fonts/fonts/consciousnode-sans-8x8.hex'),se=f('/home/claude/cnsw-fonts/fonts/cnsw-serif-8x16.hex');
 console.log('sans glyphs match file:',JSON.stringify(s)===JSON.stringify(A.FONT_SANS_HEX),'| serif:',JSON.stringify(se)===JSON.stringify(A.FONT_SERIF_HEX));}
{const reg={};for(const id of ids){const m=M[id];const r=m.region||id;const s=(reg[r]=reg[r]||{all:new Set(),noStrip:new Set()});m.grid.forEach((t,k)=>{s.all.add(t);if(Math.floor(k/30)!==1)s.noStrip.add(t)})}
 const rs=Object.keys(reg);for(const r of rs){const others=new Set();rs.filter(x=>x!==r).forEach(x=>reg[x].all.forEach(t=>others.add(t)));
  const u=[...reg[r].all].filter(t=>!others.has(t)).length,u2=[...reg[r].noStrip].filter(t=>!others.has(t)).length;console.log('region',r,'unique tiles',u,'| without row-1 strip',u2)}}
{const lines=[];for(const id of ids)for(const n of M[id].npcs||[]){const d=n.dialog;(Array.isArray(d)?d:d?[d]:[]).forEach(x=>lines.push(x));['after','intro','win','lose','done','questDone','questText'].forEach(k=>{if(n[k])(Array.isArray(n[k])?n[k]:[n[k]]).forEach(x=>lines.push(x))})}
 const T=A.TRAINERS;for(const t of Object.values(T))for(const k of Object.keys(t))if(typeof t[k]==='string'&&k!=='id'&&k!=='name')lines.push(t[k]);
 const uniq=new Set(lines);const tmpl=new Set(lines.map(l=>l.replace(/[A-Z][a-z]+( [A-Z][a-z]+)*/g,'X').replace(/\d+/g,'N')));
 console.log('dialogue strings found',lines.length,'unique',uniq.size,'unique after masking names/numbers',tmpl.size);
 const r=[...uniq];for(const i of [3,40,120,300,500,700,900])if(r[i])console.log('  >',r[i].slice(0,140));}
{let npcL=[];let named=0,generic=0;for(const id of ids)for(const n of M[id].npcs||[]){(n.lines||[]).forEach(x=>npcL.push(x));/Local \d+/.test(n.name)?generic++:named++}
 const bank=A.EXTRA_DIALOGUE_BANK||[];console.log('NPC lines',npcL.length,'unique',new Set(npcL).size,'| bank',bank.length,'unique',new Set(bank).size,'| bank lines also used by an NPC',bank.filter(b=>npcL.includes(b)).length);
 console.log('NPCs named',named,'generic "Local N"',generic);
 const u=[...new Set(npcL)];[10,60,150,220,300].forEach(i=>u[i]&&console.log('  >',u[i].slice(0,150)));}
{const bank=A.EXTRA_DIALOGUE_BANK;const base=new Set(bank.map(b=>b.replace(/ \(Chef Almanac Vol\. \d+\)$/,'')));const vols=new Set(bank.map(b=>(b.match(/Vol\. (\d+)/)||[])[1]));console.log('bank base lines',base.size,'x volumes',vols.size);}
