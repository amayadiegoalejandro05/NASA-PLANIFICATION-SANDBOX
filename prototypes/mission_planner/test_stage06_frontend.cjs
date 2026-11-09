// Unit-level presentation checks with a minimal DOM double, NOT browser/visual QA.
// Uses fresh Python engine output from verify_stage06.py, never a UI data source.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const here=__dirname, fixtures=JSON.parse(fs.readFileSync(path.join(here,'evidence/stage06/functional.json'),'utf8')).cases;
const catalogFixtures=JSON.parse(fs.readFileSync(path.join(here,'evidence/stage06/catalog.json'),'utf8'));
class Element {
  constructor(){this.value='both';this.className='';this.textContent='';this.innerHTML='';this.children=[];this.dataset={};this.style={setProperty(){}};this.disabled=false;this.attrs={};this.classList={add:(v)=>this.className+=' '+v};}
  append(...children){this.children.push(...children);} replaceChildren(...children){this.children=children;this.innerHTML='';this.textContent='';}setAttribute(k,v){this.attrs[k]=v;} addEventListener(){} querySelector(){return null;}
}
const elements=new Map(),document={getElementById(id){if(!elements.has(id))elements.set(id,new Element());return elements.get(id);},createElement(){return new Element();},createElementNS(){return new Element();},querySelectorAll(){return[];}};
const context=vm.createContext({document,console,JSON,Number,Object,String,Math,Promise,setTimeout,fixtures,catalogFixtures,fetch:()=>new Promise(()=>{}),assert});
vm.runInContext(fs.readFileSync(path.join(here,'web/app.js'),'utf8'),context);
vm.runInContext(`
config=clone(fixtures.ctx_compare.configuration);
catalog=catalogFixtures;
renderConfig();
assert.equal($('mapGrid').children.length,49);
showCell(catalog.maps.ctx.cells.find(x=>x.cell.toString()==='4,2'));
assert.ok($('coordinates').textContent.includes('10; 18'));
assert.ok($('coordinates').textContent.includes('-6; -2'));
bundle=fixtures.ctx_compare; selected=0; resultRevision=revision;
renderResults();
assert.ok($('detail').innerHTML.includes('Actividad'));
assert.ok($('detail').innerHTML.includes('8 Wh'));
assert.ok($('detail').innerHTML.includes('Saldo final'));
assert.ok($('coincidence').textContent.includes('1 recorridos distintos'));
assert.ok($('recommendation').textContent.includes('Equilibrada'));
drawMap();
assert.equal($('mapGrid').children[49].children[0].attrs.points,'350,350 450,250');
bundle=fixtures.ctx_rover;renderResults();
assert.ok($('detail').innerHTML.includes('No aplica'));
bundle=fixtures.ctx_limit;renderResults();
assert.ok($('detail').innerHTML.includes('Búsqueda interrumpida; factibilidad desconocida'));
assert.ok($('recommendation').textContent.includes('regreso sin confirmar'));
bundle=fixtures.ctx_invalid_semantic;renderResults();
assert.ok($('detail').innerHTML.includes('Entrada inválida'));
bundle=fixtures.ctx_completed;renderResults();
assert.ok(!$('detail').innerHTML.includes(' · science'));
bundle=fixtures.ctx_compare;stale();
assert.equal($('status').className,'stale');
assert.ok($('status').textContent.includes('pendiente de recalcular'));
`,context);
async function main(){
  await vm.runInContext(`(async()=>{
    let resolveResponse,calls=0;
    fetch=()=>{calls++;return new Promise(resolve=>resolveResponse=resolve);};
    const first=calculate('compare');await calculate('evaluate');
    assert.equal(calls,1);assert.equal($('compare').disabled,true);
    config.activity_min=3;stale();
    resolveResponse({ok:true,json:async()=>fixtures.ctx_compare});await first;
    assert.equal($('status').className,'stale');
    assert.notEqual(resultRevision,revision);
    assert.equal($('compare').disabled,false);
    fetch=async()=>({ok:false,json:async()=>({status:'INVALID_INPUT',message:'Fixture inválido'})});
    await calculate('compare');
    assert.ok($('status').textContent.includes('INVALID_INPUT'));
    assert.equal($('detail').innerHTML,'');
    assert.equal(busy,false);
  })()`,context);
  const log='PASS: real payload presentation (phases, resources, rover, limit, invalid, completed); stale results; duplicate suppression; edits during calculation; HTTP error handling.\nDOM double only: no browser, screenshots, downloads or layout verified.\n';
  fs.writeFileSync(path.join(here,'evidence/stage06/frontend-unit.log'),log);console.log(log);
}
main().catch(e=>{console.error(e);process.exitCode=1;});
