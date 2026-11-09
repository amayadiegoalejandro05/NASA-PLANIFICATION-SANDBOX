// Logical presentation/race regressions. Real browser evidence is separate.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const dir=path.join(__dirname,'evidence/stage06_maps');
const samples=JSON.parse(fs.readFileSync(path.join(dir,'regional-evaluation.json'),'utf8'));
const cat=JSON.parse(fs.readFileSync(path.join(dir,'regional-catalog.json'),'utf8'));
class Element{constructor(){this.value='';this.innerHTML='';this.children=[];this.textContent='';}append(...a){this.children.push(...a);}replaceChildren(){this.children=[];this.innerHTML='';this.textContent='';}}
const elements=new Map(),document={getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement(){return new Element();},querySelectorAll(){return[];}};
const context=vm.createContext({document,console,JSON,Number,Object,String,Math,Promise,setTimeout,assert,samples,cat,fetch:()=>new Promise(()=>{})});
vm.runInContext(fs.readFileSync(path.join(__dirname,'web/map-app.js'),'utf8'),context);
async function main(){await vm.runInContext(`(async()=>{
 catalog=cat;config=copy(cat.defaults.regional.astronaut);controls();
 assert.equal(config.base.toString(),config.current.toString());
 bundle=samples.astronaut_success.bundle;renderResults();
 assert.ok($('recommendation').textContent.includes('Ruta recomendada según el perfil'));
 assert.ok($('coincidence').textContent.includes('1 ruta distinta'));
 assert.ok($('resultDetail').innerHTML.includes('Restante al regresar'));
 bundle=samples.rover_success.bundle;renderResults();assert.ok($('resultDetail').innerHTML.includes('No aplica'));
 dirty();assert.equal($('status').className,'stale');
 let resolve,calls=0;fetch=()=>{calls++;return new Promise(r=>resolve=r);};
 const pending=calculate();await calculate();assert.equal(calls,1);
 config.activity_min=3;dirty();resolve({ok:true,json:async()=>samples.astronaut_success.bundle});await pending;
 assert.equal($('status').className,'stale');assert.notEqual(resultRevision,revision);assert.equal(busy,false);
 $('clearGoal').onclick();assert.equal(config.goal,null);
 await calculate();assert.ok($('status').textContent.includes('Marca la salida'));
})()`,context);
const output='PASS: regional controls, original/current balances, recommendation, coincidence, rover not applicable, stale result, in-flight edit, duplicate suppression and removed destination. Browser verification is recorded separately.\n';fs.writeFileSync(path.join(dir,'frontend-unit.log'),output);console.log(output);}
main().catch(e=>{console.error(e);process.exitCode=1;});
