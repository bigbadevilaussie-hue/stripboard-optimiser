// Requires npm run build:solver && npm run build:native.
const assert=require("node:assert/strict"),fs=require("node:fs"),path=require("node:path");
const wasm=path.join(__dirname,"../../components/stripboard/v5wasm");
const decMod=new WebAssembly.Module(fs.readFileSync(path.join(wasm,"v5decode.wasm")));
const routeMod=new WebAssembly.Module(fs.readFileSync(path.join(wasm,"v5route.wasm")));
delete process.env.V5_NATIVE_LIB_DIR;delete process.env.V5_NATIVE_ROUTE_LIB_DIR;
require("./nativeInstance.js").install(decMod,routeMod);
const {V5WasmDecoder}=require("./out/components/stripboard/v5wasm/v5Wasm.js");
const shape={w:1,h:1,entry:-1,body:[0,0,0,0],pins:[{rowOff:0,colOff:0,net:0}]};
const part=i=>({kind:0,locked:false,isConn:false,clr:0,lines:0,fat:false,idx:i,sides:-1,
 lockY0:0,lockY1:0,lockX:0,lockRot:0,lockFlexH:0,shapes:[shape,shape,shape,shape]});
const model={parts:[part(0),part(1)],nNets:1,netPins:[[{pi:0,kind:0,end:0,pinIdx:[0,0,0,0]},{pi:1,kind:0,end:0,pinIdx:[0,0,0,0]}]],
 flexIdx:[],rigidIdx:[0,1],siblingGroups:[],mRow:0,mCol:0,lockedRowsCap:-1,lockedColsCap:-1,
 sidesDef:15,clrPad:0,wBCut:24,wWire:4,wCut:.05,conns:[],pullNets:[],pullNet:[],halfTurn:[false,false],canHV:[],rotK:[0,1]};
const unrestricted=new V5WasmDecoder(decMod,model);
unrestricted.rngSet(42);assert.deepEqual(unrestricted.labInit().rot,[0,0]);
const d=new V5WasmDecoder(decMod,{...model,davePair:[0,1]});
d.rngSet(42);let g=d.labInit();assert.deepEqual(g.rot,[1,0]);
for(let i=0;i<1000;i++){const n=d.labMutate(g);if(n){assert.ok([1,3].includes(n.rot[0]));assert.ok([0,2].includes(n.rot[1]));g=n;}}
d.writeGenome({...g,rot:[0,0]});assert.equal(d.decode().status,0);
d.writeGenome({...g,rot:[1,1]});assert.equal(d.decode().status,0);
assert.throws(()=>new V5WasmDecoder(decMod,{...model,davePair:[0,0]}),/Canonical Dave/);
console.log("✅ Canonical Dave rotation-domain and unrestricted-model checks");
