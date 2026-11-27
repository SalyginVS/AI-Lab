const vscode=require('vscode'),fs=require('fs'),path=require('path'),assert=require('assert');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
exports.run=async function(){
 const d=path.dirname(__dirname),expected=JSON.parse(fs.readFileSync(path.join(d,'expected.json'),'utf8'));
 const log=(event,obj={})=>fs.appendFileSync(path.join(d,'evidence.jsonl'),JSON.stringify({event,time:new Date().toISOString(),...obj})+'\n');
 function readSessions(){
  const files=[];const visit=p=>{for(const e of fs.readdirSync(p,{withFileTypes:true})){const f=path.join(p,e.name);if(e.isDirectory())visit(f);else if(f.endsWith('.jsonl'))files.push(f);}};visit(path.join(d,'sessions'));
  return files.flatMap(f=>fs.readFileSync(f,'utf8').split('\n').flatMap(l=>{try{return [JSON.parse(l)]}catch{return []}}));
 }
 const extension=vscode.extensions.getExtension('pi0.pi-vscode');
 assert(extension,'Installed extension unavailable');
 assert.strictEqual(extension.packageJSON.version,'0.0.9');
 await extension.activate();
 const doc=await vscode.workspace.openTextDocument(path.join(d,'workspace','probe.txt'));
 await vscode.window.showTextDocument(doc);
 const before=new Set(vscode.window.terminals);
 await vscode.commands.executeCommand('pi-vscode.open');
 let terminal;
 for(let i=0;i<60;i++){terminal=vscode.window.terminals.find(t=>!before.has(t));if(terminal)break;await sleep(500)}
 assert(terminal,'Pi extension did not open terminal');
 const pid=await terminal.processId;
 log('IDE_EXTENSION_TERMINAL',{extension:extension.id,version:extension.packageJSON.version,pid,model:expected.model});
 await sleep(6000);
 terminal.sendText('Use the read tool to read ./probe.txt. Also call vscode_get_editor_state to inspect the VS Code workspace. After both tool results reply with exactly the single line read from probe.txt.',true);
 const deadline=Date.now()+15*60*1000;
 let lastKey='';
 while(Date.now()<deadline){
  const messages=readSessions().filter(x=>x.type==='message'&&x.message).map(x=>x.message);
  const assistants=messages.filter(m=>m.role==='assistant');
  const calls=assistants.flatMap(m=>(m.content||[]).filter(c=>c.type==='toolCall'));
  const results=messages.filter(m=>m.role==='toolResult');
  const txt=m=>(m?.content||[]).filter(c=>c.type==='text').map(c=>c.text).join('');
  const summary={assistants:assistants.length,calls:calls.map(c=>c.name),results:results.map(r=>({name:r.toolName,error:!!r.isError})),model:assistants.at(-1)?.model,provider:assistants.at(-1)?.provider};
  const key=JSON.stringify(summary);
  if(key!==lastKey){log('IDE_PROGRESS',summary);lastKey=key;}
  const read=results.find(r=>!r.isError&&calls.some(c=>c.id===r.toolCallId&&c.name==='read')&&txt(r).includes(expected.marker));
  const bridge=results.find(r=>!r.isError&&calls.some(c=>c.id===r.toolCallId&&c.name==='vscode_get_editor_state')&&txt(r).includes(path.join(d,'workspace')));
  const final=assistants.at(-1);
  if(read&&bridge&&final&&txt(final).trim()===expected.marker&&final.stopReason==='stop'){
   assert(assistants.every(m=>m.provider==='ailab-strata'&&m.model===expected.model));
   log('IDE_LIVE_PASS',{model:expected.model,readCorrelated:true,bridgeCorrelated:true,continuation:true,assistantCount:assistants.length});
   terminal.dispose();return;
  }
  if(final&&['error','aborted'].includes(final.stopReason)){log('IDE_MODEL_ERROR',{stopReason:final.stopReason,error:(final.errorMessage||'').slice(0,300)});break;}
  await sleep(2000);
 }
 terminal.dispose();log('IDE_LIVE_FAIL');throw Error('No valid real IDE read/bridge continuation');
}
