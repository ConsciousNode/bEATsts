// Kehai audit v2: sprite distances with translation alignment (pose shifts can't fake difference)
const fs=require('fs'),vm=require('vm');
const html=fs.readFileSync(process.argv[2],'utf8');
const js=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const sb={document:{getElementById:()=>({addEventListener(){},getContext:()=>null}),querySelectorAll:()=>[],createElement:()=>({click(){},remove(){},getContext:()=>null}),body:{appendChild(){}}},performance:{now:()=>0},requestAnimationFrame(){},addEventListener(){},Uint8Array,Uint16Array,Int8Array,Float32Array,Set,Map,Math,JSON,Array,Object,String,Number,Error,console,setTimeout(){},TextEncoder};sb.window=sb;vm.runInNewContext(js,sb);
const A=sb.BEATS_API, L=A.BEATSTS, N=Math.sqrt(L[0].front.length)|0;
console.log('species',L.length,'sprite size',N);
const arch=new Set(L.map(b=>b.shape&&b.shape.arch)); console.log('distinct archetypes',arch.size, [...arch].join(' '));
const tup=new Set(L.map(b=>JSON.stringify(b.shape))); console.log('distinct shape tuples',tup.size);
const famArch={};L.forEach(b=>{(famArch[b.family]=famArch[b.family]||new Set()).add(b.shape.arch)});for(const k in famArch)console.log('  ',k,'archetypes',famArch[k].size);
// evolution lines
const parent={};L.forEach(b=>{if(b.evo&&b.evo.to)parent[b.evo.to]=b.id});const root=id=>{let r=id,g=0;while(parent[r]&&g++<6)r=parent[r];return r};
// crop to bbox
function crop(g){let x0=N,y0=N,x1=-1,y1=-1;for(let y=0;y<N;y++)for(let x=0;x<N;x++)if(g[y*N+x]){x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y)}return {x0,y0,w:x1-x0+1,h:y1-y0+1}}
function norm(g){const m=new Map();let n=1;return Array.from(g,v=>v===0?0:(m.has(v)?m.get(v):(m.set(v,n),n++)))}
const F=L.map(b=>{const n=norm(b.front);return {b,n,bb:crop(n),area:n.filter(v=>v).length}});
function best(a,c){ // best alignment over shifts within ±10
  let bestJ=0,bestD=1e9;
  for(let dy=-10;dy<=10;dy++)for(let dx=-10;dx<=10;dx++){let inter=0,uni=0,diff=0;
    for(let y=0;y<N;y++)for(let x=0;x<N;x++){const va=a.n[y*N+x];const xx=x+dx,yy=y+dy;const vc=(xx>=0&&yy>=0&&xx<N&&yy<N)?c.n[yy*N+xx]:0;
      if(va||vc){uni++;if(va&&vc)inter++;if(va!==vc)diff++;}}
    const J=inter/uni;if(J>bestJ)bestJ=J;if(diff<bestD)bestD=diff}
  return [bestJ,bestD/Math.max(a.area,c.area)]}
let pairs=[],fails=0,ex=[];
for(let i=0;i<F.length;i++)for(let j=i+1;j<F.length;j++){if(root(F[i].b.id)===root(F[j].b.id))continue;
  const [J,D]=best(F[i],F[j]);pairs.push([J,D]);if(J>0.85||D<0.20){fails++;if(ex.length<12)ex.push(`${F[i].b.name}~${F[j].b.name} J=${J.toFixed(2)} D=${D.toFixed(2)}`)}}
pairs.sort((a,b)=>b[0]-a[0]);const Js=pairs.map(p=>p[0]),Ds=pairs.map(p=>p[1]).sort((a,b)=>a-b);
console.log('cross-line pairs',pairs.length,'| aligned Jaccard max',Js[0].toFixed(3),'median',Js[Js.length>>1].toFixed(3),'| aligned diff min',Ds[0].toFixed(3),'median',Ds[Ds.length>>1].toFixed(3));
console.log('pairs failing the spec thresholds once aligned:',fails);ex.forEach(e=>console.log('   ',e));
fs.writeFileSync('/tmp/bt2/audit/sprites.json',JSON.stringify(L.map(b=>({id:b.id,name:b.name,front:Array.from(b.front),pal:b.palette,fam:b.family}))));
