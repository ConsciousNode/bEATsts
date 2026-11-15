// Record the reference bot's button sequence (reference only; no ROM involved)
const {makeRef,ROOT}=require("./common.js");const fs=require("fs"),path=require("path");
const api=makeRef();const g=api.Game;const rec=[];const orig=g.pressButton.bind(g);g.pressButton=function(b){rec.push(b);orig(b);};
g.pressButton("A");g.pressButton("A");g.pressButton("A");while(g.screen==="DIALOG")g.pressButton("A");
let steps=0,battles=0;const src=fs.readFileSync(path.join(ROOT,"beatsts-2.2/tests/run-all.js"),"utf8");
eval(src.slice(src.indexOf("function winBattle()"),src.indexOf("if (!goToMap(")).replace(/window\.__checkFrame\(\);/g,""));
goToMap("grand_tasting_hall");talkNpc("inn_hall");["saffron_6","pip_npc","roux_npc","mochi_npc","aurelia_npc"].forEach(talkNpc);
console.log("screen",g.screen,"presses",rec.length);fs.writeFileSync("keys.json",JSON.stringify(rec));
