const vscode=require('vscode'),fs=require('fs'),path=require('path'),assert=require('assert');
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
exports.run=async function(){
 const d=path.dirname(__dirname),ex=JSON.parse(fs.readFileSync(path.join(d,'expected.json'),'utf8'));
 const log=(event,obj={})=>fs.appendFileSync(path.join(d,'ide-events.jsonl'),JSON.stringify({event,time:new Date().toISOString(),...obj})+'\n');
 function sessions(){const files=[];const visit=p=>{for(const e of fs.readdirSync(p,{withFileTypes:true})){const f=path.join(p,e.name);if(e.isDirectory())visit(f);else if(f.endsWith('.jsonl'))files.push(f)}};visit(path.join(d,'sessions'));return files}
 function entries(){return sessions().flatMap(f=>fs.readFileSync(f,'utf8').split('\n').flatMap(l=>{try{return [JSON.parse(l)]}catch{return []}}))}
 function text(m){return (m?.content||[]).filter(c=>c.type==='text').map(c=>c.text).join('')}
 async function wait(label,pred,timeout=45000){const end=Date.now()+timeout;while(Date.now()<end){const es=entries();const bad=es.find(e=>e.message?.role==='assistant'&&['error','aborted'].includes(e.message.stopReason));if(bad)throw Error(label+' '+bad.message.errorMessage);if(fs.existsSync(path.join(d,'mock-errors.log')))throw Error('mock request error');if(pred(es)){log(label);return}await sleep(250)}throw Error('timeout '+label)}
 const ext=vscode.extensions.getExtension('pi0.pi-vscode');assert(ext);assert.equal(ext.packageJSON.version,'0.0.9');await ext.activate();
 const doc=await vscode.workspace.openTextDocument(path.join(d,'workspace','first.txt'));await vscode.window.showTextDocument(doc);
 const before=new Set(vscode.window.terminals);await vscode.commands.executeCommand('pi-vscode.open');let terminal;
 for(let i=0;i<80;i++){terminal=vscode.window.terminals.find(t=>!before.has(t));if(terminal)break;await sleep(250)}
 assert(terminal);log('EXTENSION_TERMINAL',{version:ext.packageJSON.version,pid:await terminal.processId,model:ex.model});
 function has(es,s){return es.some(e=>e.message?.role==='assistant'&&e.message.stopReason==='stop'&&text(e.message).includes(s))}
 try{
  await wait('START_OK',es=>has(es,'E02_START_OK'));
  terminal.sendText('E02_CHAIN',true);await wait('CHAIN_OK',es=>has(es,'E02_CHAIN_OK '+ex.final));
  terminal.sendText('E02_PRESSURE'+' recent'.repeat(12500),true);
  await wait('COMPACTION_OK',es=>es.some(e=>e.type==='compaction'&&e.summary.includes('E02_CHECKPOINT')),60000);
  terminal.sendText('E02_AFTER_COMPACT',true);await wait('AFTER_OK',es=>has(es,'E02_AFTER_OK'));
  assert.equal(sessions().length,1);log('IDE_MOCK_PASS');
 }catch(e){log('IDE_MOCK_FAIL',{error:String(e)});throw e}finally{terminal.dispose()}
}
