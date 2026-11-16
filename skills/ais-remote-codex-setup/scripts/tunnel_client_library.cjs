// Load the installed official Remote Tunnels client without starting its proxy server.
const fs=require('fs'),os=require('os'),path=require('path'),vm=require('vm');
const {createRequire}=require('module');
class LocalError extends Error {}
function fail(message){throw new LocalError(message)}
function loadClient(explicit){
 let candidates=[];
 if(explicit)candidates=[path.resolve(explicit)];
 else{
  const base=path.join(os.homedir(),'.vscode','extensions');
  if(fs.existsSync(base))candidates=fs.readdirSync(base).filter(n=>n.startsWith('ms-vscode.remote-server-')).map(n=>path.join(base,n)).sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}));
 }
 const root=candidates.find(p=>fs.existsSync(path.join(p,'dist/node/proxyServer.js')));
 if(!root)fail('Remote Tunnels extension missing; install ms-vscode.remote-server or pass --extension-path');
 const file=path.join(root,'dist/node/proxyServer.js');
 const source=fs.readFileSync(file,'utf8');
 // Resolve the library imports from the entrypoint, rather than freezing module IDs.
 const starts=[...source.matchAll(/var \w+=\{\};\(\(\)=>\{"use strict";var /g)];
 const start=starts.at(-1)?.index;
 if(start===undefined)fail('Unsupported Remote Tunnels bundle layout; review the adapter for this extension version');
 const entry=source.slice(start);
 const proxyAlias=entry.match(/extends (\w+)\.ProxyServer/)?.[1];
 const basisAlias=entry.match(/new (\w+)\.BasisConnectionBearer/)?.[1];
 function imported(alias){
  if(!alias)fail('Unsupported Remote Tunnels entrypoint');
  const m=entry.match(new RegExp('\\b'+alias+'=(\\w+)\\((\\d+)\\)'));
  if(!m)fail('Cannot locate Remote Tunnels client imports');
  return {require:m[1],id:m[2]};
 }
 const proxyImport=imported(proxyAlias),basisImport=imported(basisAlias);
 if(proxyImport.require!==basisImport.require)fail('Unsupported Remote Tunnels module loader');
 const req=proxyImport.require;
 const adapted=source.slice(0,start)+`module.exports={basis:${req}(${basisImport.id}),proxy:${req}(${proxyImport.id})};})();`;
 const mod={exports:{}};
 vm.runInThisContext('(function(require,module,exports,__dirname,__filename){'+adapted+'\n})',{filename:file})(createRequire(file),mod,mod.exports,path.dirname(file),file);
 const {basis,proxy}=mod.exports;
 if(!basis?.AccessTokenBasisClient||!basis?.BasisConnectionBearer||!proxy?.ConnectionManager||!proxy?.ExecServer)fail('Installed Remote Tunnels API is unsupported');
 return {basis,proxy,extensionVersion:JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8')).version};
}
module.exports={loadClient,LocalError};
