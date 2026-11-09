// Preserve all historical logs while executing the original two suites unchanged.
const fs=require('node:fs'),path=require('node:path');
const write=fs.writeFileSync;
fs.writeFileSync=(file,...args)=>write.call(fs,path.basename(file)==='frontend-unit.log'
    ?path.join(__dirname,path.basename(path.dirname(file))+'-js.log'):file,...args);
const base=path.resolve(__dirname,'../..');
require(path.join(base,'test_stage06_frontend.cjs'));
require(path.join(base,'test_stage06_map_frontend.cjs'));
require(path.join(base,'test_stage065_preparation.cjs'));
