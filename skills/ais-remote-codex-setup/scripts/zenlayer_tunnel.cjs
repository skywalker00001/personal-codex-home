#!/usr/bin/env node
// Reuse an existing VS Code Tunnel; credentials remain in local process memory.
process.env.NODE_TLS_REJECT_UNAUTHORIZED='1';
const {execFileSync}=require('child_process'),readline=require('readline');
const {performance}=require('perf_hooks');
const {loadClient,LocalError}=require('./tunnel_client_library.cjs');
const LIMIT=1024*1024;
const USAGE=`Usage: node zenlayer_tunnel.cjs status|read|exec|session [options] [-- program args...]
  --tunnel NAME          Existing tunnel (default h200-b32-master0)
  --expect-host HOST     Required for exec; verify the actual connected hostname
  --cwd DIRECTORY        Remote exec cwd (default /aigc/avatar/houyi)
  --path FILE            Absolute remote path for read
  --max-bytes NUMBER     Read/captured output limit (default 1048576)
  --extension-path DIR   Installed ms-vscode.remote-server directory
session reads JSONL: {id,op:'status'|'read'|'exec'|'close',path,command,args,cwd,stdin,expect_host}
No tunnel is created, restarted or re-registered by this tool.`;
function parse(argv){
 const opts={mode:argv.shift(),tunnel:'h200-b32-master0',cwd:'/aigc/avatar/houyi',limit:LIMIT,command:[]};
 if(['--help','-h',undefined].includes(opts.mode))return {help:true};
 if(!['status','read','exec','session'].includes(opts.mode))throw new LocalError('Unknown command; use --help');
 const names={'--tunnel':'tunnel','--expect-host':'expected','--cwd':'cwd','--path':'path','--max-bytes':'limit','--extension-path':'extension'};
 while(argv.length){
  const flag=argv.shift();
  if(flag==='--'){opts.command=argv;break}
  if(!names[flag]||!argv.length||!argv[0]||argv[0].startsWith('--'))throw new LocalError('Invalid option; use --help');
  opts[names[flag]]=argv.shift();
 }
 opts.limit=Number(opts.limit);
 if(!Number.isSafeInteger(opts.limit)||opts.limit<1)throw new LocalError('Invalid --max-bytes');
 if(opts.mode==='read'&&!opts.path)throw new LocalError('read requires --path');
 if(opts.mode==='exec'&&(!opts.expected||!opts.command.length))throw new LocalError('exec requires --expect-host and -- program args');
 return opts;
}
function absolute(p){if(typeof p!=='string'||!p.startsWith('/')||p.includes('\0'))throw new LocalError('An absolute remote path is required');return p}
function collect(stream,limit,sink){
 let kept=0,total=0;const chunks=[];
 stream.onDidReceiveMessage(data=>{
  const b=Buffer.from(data);total+=b.length;
  if(sink)sink.write(b);
  else if(kept<limit){const part=b.subarray(0,limit-kept);chunks.push(part);kept+=part.length}
 });
 return {done:Promise.resolve(stream.onEnd),data:()=>Buffer.concat(chunks),truncated:()=>!sink&&total>kept};
}
async function run(options){
 const began=performance.now();
 const {basis,proxy,extensionVersion}=loadClient(options.extension);
 let credential;
 try{credential=execFileSync('/usr/bin/git',['credential','fill'],{
  input:'protocol=https\nhost=github.com\n\n',encoding:'utf8',timeout:20000,
  env:{...process.env,GIT_TERMINAL_PROMPT:'0',GCM_INTERACTIVE:'Never'},stdio:['pipe','pipe','pipe']});
 }catch{throw new LocalError('GitHub credential unavailable; authenticate the intended local GitHub account first')}
 const fields=Object.fromEntries(credential.trim().split('\n').map(line=>{const i=line.indexOf('=');return[line.slice(0,i),line.slice(i+1)]}));
 credential=undefined;
 if(!fields.password)throw new LocalError('GitHub credential unavailable');
 const client=new basis.AccessTokenBasisClient('github','vscode.dev.remote-server',async()=>fields.password);
 let bearer,manager,server;
 const timer=setTimeout(()=>{process.stderr.write('Tunnel connection timed out; inspect the existing tunnel and account.\n');process.exit(2)},60000);
 try{
  const tunnel=await client.getTunnelForTag(options.tunnel);
  if(!tunnel)throw new LocalError('Existing tunnel not found for the authenticated GitHub account');
  bearer=new basis.BasisConnectionBearer(client,tunnel,31545);
  manager=new proxy.ConnectionManager({bearer});server=new proxy.ExecServer(manager);
  async function hostname(expected){
   const result=await manager.call('gethostname',{});
   if(typeof result.value!=='string')throw new LocalError('Unsupported tunnel hostname response');
   if(expected&&result.value!==expected)throw new LocalError('Tunnel destination changed; run status and verify the target before retrying');
   return result.value;
  }
  const host=await hostname(options.expected);clearTimeout(timer);
  async function status(){
   return {tunnel:options.tunnel,hostname:await hostname(options.expected),workspace_exists:(await server.fsStat('/aigc/avatar/houyi')).exists,extension_version:extensionVersion,protocol:basis.getProtocolVersionFromTags(tunnel)};
  }
  async function read(file,expected){
   await hostname(expected||options.expected);
   file=absolute(file);const stat=await server.fsStat(file);
   if(!stat.exists)throw new LocalError('Remote file does not exist');
   if(stat.size>options.limit)throw new LocalError('Remote file exceeds --max-bytes');
   const stream=await server.fs.read(file),output=collect(stream,options.limit);
   await output.done;
   if(output.truncated())throw new LocalError('Remote read exceeded --max-bytes');
   return output.data();
  }
  async function execute(request,streaming){
   const expected=request.expect_host||options.expected;
   if(!expected)throw new LocalError('exec requires expect_host from a verified status result');
   await hostname(expected);
   if(typeof request.command!=='string'||!request.command||!Array.isArray(request.args)||request.args.some(v=>typeof v!=='string'))throw new LocalError('exec requires command and a string args array');
   if(request.stdin!==undefined&&typeof request.stdin!=='string')throw new LocalError('stdin must be text');
   const child=await server.spawn(request.command,request.args,{cwd:absolute(request.cwd||options.cwd)});
   const out=collect(child.stdout,options.limit,streaming?process.stdout:null);
   const err=collect(child.stderr,options.limit,streaming?process.stderr:null);
   if(streaming){
    process.stdin.on('data',chunk=>child.stdin.write(chunk));
    process.stdin.on('end',()=>child.stdin.end());
    if(process.stdin.readableEnded)child.stdin.end();else process.stdin.resume();
   }else{if(request.stdin)child.stdin.write(Buffer.from(request.stdin));child.stdin.end()}
   const result=await child.onExit;
   await Promise.all([out.done,err.done]);
   return {exit_code:result.status,stdout:streaming?undefined:out.data().toString('utf8'),stderr:streaming?undefined:err.data().toString('utf8'),truncated:out.truncated()||err.truncated()};
  }
  if(options.mode==='status')console.log(JSON.stringify(await status(),null,2));
  else if(options.mode==='read')process.stdout.write(await read(options.path));
  else if(options.mode==='exec'){
   const result=await execute({command:options.command[0],args:options.command.slice(1)},true);
   process.exitCode=Number.isInteger(result.exit_code)?result.exit_code:1;
  }else{
   console.log(JSON.stringify({event:'ready',hostname:host,tunnel:options.tunnel,setup_ms:Math.round(performance.now()-began)}));
   const input=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
   for await(const line of input){
    let req;
    try{
     req=JSON.parse(line);let result;
     if(req.op==='close'){console.log(JSON.stringify({id:req.id,ok:true}));break}
     if(req.op==='status')result=await status();
     else if(req.op==='read')result={text:(await read(req.path,req.expect_host)).toString('utf8')};
     else if(req.op==='exec')result=await execute(req,false);
     else throw new LocalError('Unknown session operation');
     console.log(JSON.stringify({id:req.id,ok:true,result}));
    }catch(error){console.log(JSON.stringify({id:req?.id,ok:false,error:safeError(error)}))}
   }
   input.close();
  }
 }finally{clearTimeout(timer);try{bearer?.close()}catch{}}
}
function safeError(error){
 // SDK messages can contain HTTP headers; only typed local errors are printable.
 if(error instanceof LocalError)return error.message;
 return 'Tunnel operation failed; inspect authentication, connectivity and extension compatibility';
}

module.exports={parse,loadClient,collect,absolute};
if(require.main===module){
 let opts;try{opts=parse(process.argv.slice(2))}catch(e){process.stderr.write(e.message+'\n');process.exit(2)}
 if(opts.help){console.log(USAGE);process.exit(0)}
 run(opts).then(()=>process.exit(process.exitCode||0),error=>{process.stderr.write(safeError(error)+'\n');process.exit(1)});
}
