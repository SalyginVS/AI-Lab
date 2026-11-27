const vscode=require('vscode'),fs=require('fs'),path=require('path'),cp=require('child_process'),assert=require('assert');
exports.run=async()=>{
const p=path.dirname(__dirname),log=x=>fs.appendFileSync(path.join(p,'ide-result.jsonl'),JSON.stringify(x)+'\n');
let term;
try{
const ext=vscode.extensions.getExtension('pi0.pi-vscode');assert(ext);assert.equal(ext.packageJSON.version,'0.0.9');await ext.activate();
const target=vscode.workspace.getConfiguration('pi-vscode').get('path');assert.equal(target,path.join(process.env.HOME,'.local/bin/ailab-ide'));
assert.equal(cp.execFileSync(target,['--version'],{encoding:'utf8'}).trim(),'1.0.3');
const before=new Set(vscode.window.terminals);await vscode.commands.executeCommand('pi-vscode.open');
for(let i=0;i<80;i++){term=vscode.window.terminals.find(t=>!before.has(t));if(term)break;await new Promise(r=>setTimeout(r,200));}
assert(term);assert.equal(term.creationOptions.shellPath,target);assert(term.creationOptions.shellArgs.includes('--extension'));
const pid=await term.processId;assert(pid);
let args=[],seen=new Set();
for(let i=0;i<50;i++){
 const rows=cp.execFileSync('ps',['-eo','pid=,ppid=,comm='],{encoding:'utf8'}).trim().split('\n').map(s=>s.trim().split(/\s+/,3));
 const ids=new Set([String(pid)]);for(let k=0;k<10;k++)for(const [n,parent] of rows)if(ids.has(parent))ids.add(n);
 for(const n of ids){try{const a=fs.readFileSync('/proc/'+n+'/cmdline','utf8').split('\0');seen.add(JSON.stringify({pid:n,exe:path.basename(a[0]),argc:a.length,modelFlag:a.includes('--model'),thinkingFlag:a.includes('--thinking')}));if(a.includes('ailab-strata/inkling-2-mini-sq-20')){args=a;break;}}catch{}}
 if(args.length||term.exitStatus)break;
 await new Promise(r=>setTimeout(r,250));
}
log({result:'PROCESS_DIAGNOSTIC',terminal_pid:pid,seen:[...seen].map(JSON.parse),exitStatus:term.exitStatus||null});
assert(args.includes('--model'));assert.equal(args[args.indexOf('--model')+1],'ailab-strata/inkling-2-mini-sq-20');assert.equal(args[args.indexOf('--thinking')+1],'low');assert(args.includes('--offline'));assert(vscode.window.terminals.includes(term));
log({result:'IDE_ACTIVE_MODEL_LAUNCH_PASS',extension:'0.0.9',pi:'1.0.3',model:'ailab-strata/inkling-2-mini-sq-20',thinking:'low',bridge_argument:true,prompt_sent:false});
}catch(e){log({result:'IDE_LAUNCH_FAIL',error:String(e)});throw e;}finally{if(term)term.dispose();}
};
