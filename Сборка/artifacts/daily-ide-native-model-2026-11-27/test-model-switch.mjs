import test from "node:test";
import assert from "node:assert/strict";
import { installModelSwitch } from "./pi-model-switch.ts";
const I="ailab-strata/inkling-2-mini-sq-20";
const F="ailab-strata/qwen3.8-flash-next-ud-q6_k_xl";
const Q="ailab-ollama/qwen3.8-27b-gsq-rco:iq3s-mtp-262k";
const U="other/unsupported";
const K={inkling:I,flash:F,q27:Q};
function model(k){const i=k.indexOf("/");return {provider:k.slice(0,i),id:k.slice(i+1)};}
function fixture(){
  let active=I,fail=false,offline=false,idle=true,pending=false,mode="tui",nextSelect;
  const handlers=new Map(), commands=new Map(), calls=[], notices=[], statuses=[];
  let selected=model(I);
  const ctx={get model(){return selected;},get mode(){return mode;},isIdle:()=>idle,hasPendingMessages:()=>pending,modelRegistry:{find:(p,id)=>model(p+"/"+id)},ui:{notify:(m,l)=>notices.push([m,l]),setStatus:(k,v)=>statuses.push(v)}};
  const pi={on:(e,h)=>handlers.set(e,h),registerCommand:(n,h)=>commands.set(n,h),setModel:async (m)=>{const prev=selected;selected=m;await handlers.get("model_select")({source:"set",model:m,previousModel:prev},ctx);return true;}};
  const ops={current:async()=>{if(offline)throw Error("unreachable");return active;},select:async(c)=>{calls.push(c);if(nextSelect)await nextSelect(c);if(fail)throw Error("controller refused");active=K[c];}};
  installModelSwitch(pi,ops);
  return {ctx,calls,notices,statuses,commands,start:()=>handlers.get("session_start")({},ctx),change:async(k,source="set")=>{let previousModel=selected;selected=model(k);await handlers.get("model_select")({source,model:selected,previousModel},ctx);},input:()=>handlers.get("input")({},ctx),compact:()=>handlers.get("session_before_compact")({},ctx),setActive:k=>active=k,setFail:v=>fail=v,setOffline:v=>offline=v,setIdle:v=>idle=v,setPending:v=>pending=v,setMode:v=>mode=v,onSelect:fn=>nextSelect=fn,get active(){return active;},get selected(){return selected.provider+"/"+selected.id;}};
}
test("start: no transition",async()=>{const f=fixture();await f.start();assert.equal(f.selected,I);assert.deepEqual(f.calls,[]);assert.equal((await f.input()).action,"continue");});
test("native model_select: Flash then Q27 then Inkling",async()=>{const f=fixture();await f.start();for(const k of [F,Q,I]){await f.change(k);assert.equal(f.selected,k);assert.equal(f.active,k);assert.equal((await f.input()).action,"continue");}assert.deepEqual(f.calls,["flash","q27","inkling"]);});
test("controller failure restores actual profile",async()=>{const f=fixture();await f.start();f.setFail(true);await f.change(F);assert.equal(f.selected,I);assert.equal(f.active,I);assert.equal((await f.input()).action,"continue");});
test("busy selection refuses transition and restores",async()=>{const f=fixture();await f.start();f.setIdle(false);await f.change(F);assert.deepEqual(f.calls,[]);assert.equal(f.selected,I);});
test("pending message refuses transition",async()=>{const f=fixture();await f.start();f.setPending(true);await f.change(F);assert.deepEqual(f.calls,[]);assert.equal(f.selected,I);});
test("restore does not load another backend",async()=>{const f=fixture();await f.start();await f.change(F,"restore");assert.deepEqual(f.calls,[]);assert.equal(f.selected,I);});
test("RPC selection does not change backend",async()=>{const f=fixture();await f.start();f.setMode("rpc");await f.change(Q);assert.deepEqual(f.calls,[]);assert.equal(f.selected,I);});
test("unsupported model restores verified profile",async()=>{const f=fixture();await f.start();await f.change(U);assert.deepEqual(f.calls,[]);assert.equal(f.selected,I);});
test("external drift blocks input and compaction",async()=>{const f=fixture();await f.start();f.setActive(F);assert.equal((await f.input()).action,"handled");assert.deepEqual(await f.compact(),{cancel:true});});
test("unknown backend blocks rather than inventing readiness",async()=>{const f=fixture();await f.start();f.setOffline(true);await f.change(F);assert.deepEqual(f.calls,[]);assert.equal((await f.input()).action,"handled");assert.equal(f.selected,I);});
test("input during transition is blocked; second selection ignored",async()=>{const f=fixture();await f.start();let release,entered;const pending=new Promise(r=>release=r);const began=new Promise(r=>entered=r);f.onSelect(async()=>{entered();await pending;});const first=f.change(F);await began;assert.equal((await f.input()).action,"handled");await f.change(Q);release();await first;assert.equal(f.selected,F);assert.equal(f.active,F);assert.deepEqual(f.calls,["flash"]);});
test("startup aligns an existing mismatched session without switch",async()=>{const f=fixture();f.setActive(Q);await f.start();assert.equal(f.selected,Q);assert.deepEqual(f.calls,[]);});
