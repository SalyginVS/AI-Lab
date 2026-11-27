const vscode=require('vscode'),fs=require('fs'),path=require('path'),cp=require('child_process'),assert=require('assert');
exports.run=async()=>{
const p=path.dirname(__dirname),log=(x)=>fs.appendFileSync(path.join(p,'ide-check.jsonl'),JSON.stringify(x)+'\n');
let term;
try{
const ext=vscode.extensions.getExtension('pi0.pi-vscode');assert(ext);assert.equal(ext.packageJSON.version,'0.0.9');await ext.activate();
const target=vscode.workspace.getConfiguration('pi-vscode').get('path');assert.equal(target,path.join(process.env.HOME,'.local/bin/pi'));
assert.equal(cp.execFileSync(target,['--version'],{encoding:'utf8'}).trim(),'1.0.3');
const before=new Set(vscode.window.terminals);await vscode.commands.executeCommand('pi-vscode.open');
for(let i=0;i<80;i++){term=vscode.window.terminals.find(t=>!before.has(t));if(term)break;await new Promise(r=>setTimeout(r,200));}
assert(term);assert.equal(term.creationOptions.shellPath,target);assert(term.creationOptions.shellArgs.includes('--extension'));
const pid=await term.processId;assert(pid);
await new Promise(r=>setTimeout(r,2000));
const cmd=fs.readFileSync('/proc/'+pid+'/cmdline','utf8');
assert(cmd.includes('pi')||cmd.includes('node'));
assert(vscode.window.terminals.includes(term));
log({result:'IDE_LAUNCH_PASS',extension:ext.packageJSON.version,pi:'1.0.3',terminal_pid:pid,launcher_matched:true,bridge_argument:true,prompt_sent:false});
}catch(e){log({result:'IDE_LAUNCH_FAIL',error:String(e)});throw e;}finally{if(term)term.dispose();}
};
