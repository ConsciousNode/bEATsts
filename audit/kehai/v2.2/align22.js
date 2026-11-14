// Kehai audit 2.2: best-alignment role similarity for different-size map pairs (slide smaller over larger)
const fs=require('fs'),vm=require('vm');const html=fs.readFileSync(process.argv[2],'utf8');
const js=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
const sb={document:{getElementById:()=>({addEventListener(){},getContext:()=>null}),querySelectorAll:()=>[],createElement:()=>({click(){},remove(){},getContext:()=>null}),body:{appendChild(){}}},performance:{now:()=>0},requestAnimationFrame(){},addEventListener(){},Uint8Array,Uint16Array,Int8Array,Float32Array,Set,Map,Math,JSON,Array,Object,String,Number,Error,console,setTimeout(){},TextEncoder};sb.window=sb;vm.runInNewContext(js,sb);
const A=sb.BEATS_API,M=A.MAPS,R=A.TILE_ROLES,ids=Object.keys(M);const role=t=>R[t]!==undefined?R[t]:'t'+t;
const G=ids.map(id=>({id,w:M[id].w,h:M[id].h,r:Array.from(M[id].grid).map(role)}));
let res=[];
for(let i=0;i<G.length;i++)for(let j=i+1;j<G.length;j++){let a=G[i],b=G[j];if(a.w===b.w&&a.h===b.h)continue;
  // overlap at every offset; similarity = matches / smaller area (smaller fully inside when it fits, else overlap area)
  let best=0;const W=Math.min(a.w,b.w),H=Math.min(a.h,b.h);
  for(let dy=-(a.h-1);dy<b.h;dy++)for(let dx=-(a.w-1);dx<b.w;dx++){let m=0,n=0;
    for(let y=Math.max(0,-dy);y<a.h&&y+dy<b.h;y++)for(let x=Math.max(0,-dx);x<a.w&&x+dx<b.w;x++){n++;if(a.r[y*a.w+x]===b.r[(y+dy)*b.w+x+dx])m++}
    if(n>=W*H*0.9){const s=m/n;if(s>best)best=s}}
  res.push([best,a.id,b.id])}
res.sort((x,y)=>y[0]-x[0]);console.log('diff-size pairs',res.length,'| >0.50:',res.filter(r=>r[0]>0.5).length,'| >0.45:',res.filter(r=>r[0]>0.45).length);
console.log('top:',res.slice(0,8).map(r=>`${r[1]}~${r[2]} ${(r[0]*100).toFixed(1)}%`).join(', '));
