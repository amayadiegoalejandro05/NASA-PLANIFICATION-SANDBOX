// Execute the production button: precision, provenance, unchanged inputs and rerun.
// DOM double only; this substage does not change or claim visual verification.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const cat=JSON.parse(fs.readFileSync(path.join(__dirname,'evidence/stage06_maps/regional-catalog.json'),'utf8'));
const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'evidence/stage065/preparation.json'),'utf8'));
class Element{constructor(){this.value='';this.innerHTML='';this.children=[];this.textContent='';}append(...x){this.children.push(...x);}replaceChildren(){this.children=[];}}
const elements=new Map(),document={getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement(){return new Element();},querySelectorAll(){return[];}};
const context=vm.createContext({document,console,JSON,Number,Object,String,Math,Promise,setTimeout,assert,cat,fixture,fetch:()=>new Promise(()=>{})});
vm.runInContext(fs.readFileSync(path.join(__dirname,'web/map-app.js'),'utf8'),context);
vm.runInContext(`
catalog=cat;config=copy(fixture.configuration);bundle=fixture.before;resultRevision=revision;selected=0;
config.remaining.time=500;config.profile.resources.time.capacity=500;
let calls=0,submitted;
calculate=(action)=>{calls++;submitted={action,config:copy(config)};};
const initial=copy(config),conditions=bundle.result.alternatives[0].mission_conditions;
$('adjustResources').onclick();
assert.equal(calls,1);assert.equal(submitted.action,'compare');
for(const r of conditions.resources){
 assert.equal(config.remaining[r.resource],Math.max(initial.remaining[r.resource],r.required_initial));
 assert.equal(config.profile.resources[r.resource].reserve,initial.profile.resources[r.resource].reserve);
 assert.equal(config.profile.resources[r.resource].movement_rate,initial.profile.resources[r.resource].movement_rate);
 assert.equal(config.profile.resources[r.resource].activity_rate,initial.profile.resources[r.resource].activity_rate);
}
for(const k of ['base','current','goal','obstacles','scenario','factor','activity_min','activity_status'])assert.deepEqual(config[k],initial[k]);
assert.deepEqual(config.profile.motion,initial.profile.motion);
const expected=copy(fixture.prepared.resource_adjustments);expected[0].changes=expected[0].changes.filter(r=>r.resource!=='time');
assert.deepEqual(JSON.parse(JSON.stringify(config.resource_adjustments)),expected);
assert.equal(config.remaining.time,500);assert.equal(config.profile.resources.time.capacity,500);
assert.ok(conditions.resources.some(r=>r.required_initial.toFixed(3)!==String(r.required_initial)));
assert.equal(resultRevision===revision,false);
$('adjustResources').onclick();assert.equal(calls,1); // Stale evidence cannot be reused.
`,context);
console.log('PASS: production preparation button uses unrounded complete candidate, increases only deficits, preserves rates/reserves/scenario/points, records adjustments, reruns once and rejects stale results.');
