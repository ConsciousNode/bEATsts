// Kehai audit: count distinct sprite designs with and without the ID-bit "signature" (step 4)
const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[2],'utf8');
let js=html.match(/<!-- INLINE SCRIPT:[\s\S]*?<script>([\s\S]*?)<\/script>/)[1];
function load(src){const sb={document:{getElementById:()=>({addEventListener(){}}),querySelectorAll:()=>[],createElement:()=>({click(){},remove(){}}),body:{appendChild(){}}},performance:{now:()=>0},requestAnimationFrame(){},addEventListener(){},Uint8Array,Float32Array,Set,Map,Math,JSON,Array,Object,String,Number,Error,console};sb.window=sb;vm.runInNewContext(src,sb);return sb.window.BEATS_API;}
const norm=g=>{const m=new Map();let n=1;return Array.from(g,v=>v===0?0:(m.has(v)?m.get(v):(m.set(v,n),n++))).join(',')};
const sil=g=>Array.from(g,v=>v?1:0).join('');
const A=load(js);
const marker='for (let b = 0; b < 8; b++) {\n    if ((id >> b) & 1) {';
if(!js.includes(marker)) throw 'marker not found';
const B=load(js.replace(marker,'for (let b = 0; b < 0; b++) {\n    if ((id >> b) & 1) {'));
for(const [lab,api] of [['as shipped',A],['signature removed',B]]){
  const L=api.BEATSTS;
  const f=new Set(L.map(b=>norm(b.front))), s=new Set(L.map(b=>sil(b.front))), bk=new Set(L.map(b=>norm(b.back)));
  console.log(`${lab}: species=${L.length} distinct fronts=${f.size} backs=${bk.size} distinct silhouettes(front)=${s.size}`);
  if(lab!=='as shipped'){const fam={};for(const b of L){(fam[b.family]=fam[b.family]||new Set()).add(norm(b.front));}for(const k in fam)console.log('  ',k,'species',L.filter(b=>b.family===k).length,'designs',fam[k].size);
   // biggest identical group
   const grp={};for(const b of L){const k=norm(b.front);(grp[k]=grp[k]||[]).push(b.name);} const big=Object.values(grp).sort((a,b)=>b.length-a.length)[0];console.log('   largest identical group:',big.length,big.slice(0,8).join(', '));}
}
{const L=B.BEATSTS;const d=(a,b)=>{let c=0;for(let i=0;i<576;i++)if(a[i]!==b[i])c++;return c};
 const near=L.map((x,i)=>{let m=1e9,j0=-1;L.forEach((y,j)=>{if(i!==j){const v=d(x.front,y.front);if(v<m){m=v;j0=j}}});return [m,x.name,L[j0].name]});
 const ds=near.map(n=>n[0]).sort((a,b)=>a-b);console.log('nearest-neighbour pixel distance (of 576), no signature: min',ds[0],'median',ds[75],'max',ds[150]);
 console.log('species whose nearest twin differs by <=10 px:',ds.filter(v=>v<=10).length);
 console.log('examples:',near.sort((a,b)=>a[0]-b[0]).slice(0,5).map(n=>`${n[1]}~${n[2]}(${n[0]}px)`).join('; '));
 // render the top pair as ascii
 const ex=near[0];const a=L.find(b=>b.name===ex[1]),b2=L.find(b=>b.name===ex[2]);
 for(let y=0;y<24;y++){let r='';for(let x=0;x<24;x++)r+=(a.front[y*24+x]?a.front[y*24+x].toString(16):'.');r+='   ';for(let x=0;x<24;x++)r+=(b2.front[y*24+x]?b2.front[y*24+x].toString(16):'.');console.log(r)}}
{const L=B.BEATSTS;const byId=Object.fromEntries(L.map(b=>[b.id,b]));const root=b=>{let r=b,guard=0;for(;;){const p=L.find(x=>x.evo&&(x.evo.to===r.id||x.evo.into===r.id||x.evo.id===r.id||x.evo[0]===r.id));if(!p||guard++>5)return r.id;r=p}};
 const d=(a,b)=>{let c=0;for(let i=0;i<576;i++)if(a[i]!==b[i])c++;return c};let same=0,cross=0;
 for(let i=0;i<L.length;i++)for(let j=i+1;j<L.length;j++)if(d(L[i].front,L[j].front)<=10){root(L[i])===root(L[j])?same++:cross++}
 console.log('pairs <=10px apart: same evolution line',same,'| different lines',cross);
 console.log('sample species keys:',Object.keys(L[0]).join(','));}
