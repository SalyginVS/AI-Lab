#!/usr/bin/env python3
"""Deterministic comparison. Baseline is input only and is never rewritten."""
import argparse,base64,collections,hashlib,json,math,re
from pathlib import Path

def evaluate(baseline,raw,client=None,embedding_reference=None):
 B=baseline['tests'];E=lambda i,k:B[i][k]['value'];out=[]
 def emit(i,checks,observed):
  rank={'PASS':0,'INFO':1,'DRIFT':2,'REVALIDATE':3,'FAIL':4,'TEST_DEFECT':5};status=max((c['status'] for c in checks),key=lambda s:rank[s])
  out.append({'id':i,'status':status,'checks':checks,'observed':observed})
 def ck(name,ok,bad='FAIL',detail=None):return {'check':name,'status':'PASS' if ok else bad,'detail':detail}
 def texts(r):
  return '\n'.join(x.get('text','') for x in r.get('result',{}).get('content',[]) if x.get('type')=='text')
 def each(i,v):
  if 'collection_error' in v:return [ck('collector',False,'TEST_DEFECT',v)]
  if 'probe_error' in v:return [ck('request',False,'INFO' if i=='M12' else 'FAIL',v)]
  if i=='F01':return [ck(k,v.get(k)==E(i,k),'REVALIDATE',{'expected':E(i,k),'actual':v.get(k)}) for k in ['version','ollama_sha256','runner_sha256']]
  if i=='F02':return [ck(k,v['environment'].get(k)==x,detail={'expected':x,'actual':v['environment'].get(k)}) for k,x in E(i,'environment').items()]
  if i=='F03':
   template=Path(__file__).resolve().parents[2]/'artifacts/q6/llama-server.wrapper.in';expected=template.read_bytes().replace(b'@REAL@',('/usr/local/lib/ollama/llama-server.real-'+v['version']).encode()).replace(b'@Q6_ID@',v['qid'].encode());return [ck('filled_wrapper',hashlib.sha256(expected).hexdigest()==v['wrapper_sha256']),ck('chat_sha256',v['chat_sha256']==E(i,'chat_sha256'),'REVALIDATE'),ck('real_present',v['real_present']==E(i,'real_present'))]
  if i=='F04':
   checks=[ck(name,v['models'].get(name)==digest,'REVALIDATE' if 'q6_' in name else 'DRIFT',{'expected':digest,'actual':v['models'].get(name)}) for name,digest in E(i,'models').items()];checks+=[ck('num_ctx',v['num_ctx']==E(i,'num_ctx')),ck('capabilities',set(v['capabilities'])==set(E(i,'capabilities')))]
   pi=(client or {}).get('tests',{}).get('C02',{}).get('pi_input',E(i,'pi_input'));checks.append(ck('pi_image_requires_vision','image' not in pi or 'vision' in v['capabilities'],detail={'pi_input':pi,'ollama_capabilities':v['capabilities']}));return checks
  if i=='F05':
   if v['rc']!=0:return [ck('journal_read',False)]
   ids=re.findall(r'model_id=([a-f0-9]+)',v['stdout']);qid=raw['tests']['F03']['qid']
   return [ck('only_current_q6',all(x==qid for x in ids)),{'check':'profile_rows','status':'PASS' if ids else 'INFO','detail':len(ids)}]
  if i=='F06':
   checks=[]
   for service in E(i,'services'):
    for key in ['active','enabled']:checks.append(ck(service+'.'+key,v['services'][service][key]['rc']==0 and v['services'][service][key]['value']==E(i,key)))
   checks+=[ck('health.'+k,v['health'].get(k)==x,detail={'expected':x,'actual':v['health'].get(k)}) for k,x in E(i,'health').items()]
   checks.append(ck('compose',v['compose_rc']==0 and all(any(c['service']==n and c['state']=='running' and c['health'] not in ['unhealthy','starting'] for c in v['compose']) for n in E(i,'compose_services'))));return checks
  if i=='F07':
   expected=E(i,'packages');raw_packages=v['packages'];actual={};changes=[]
   groups=collections.defaultdict(list)
   for key,value in raw_packages.items():groups[key.split(':',1)[0]].append((key,value))
   for short,rows in groups.items():
    for key,value in rows:
     normalized=short if len(rows)==1 and key not in expected else key
     actual[normalized]=value
   for k in sorted(set(expected)|set(actual)):
    # Compare package names in the source lock format. Preserve qualifiers for multiarch collisions.
    if expected.get(k)!=actual.get(k):changes.append({'package':k,'expected':expected.get(k),'actual':actual.get(k)})
   sensitive=[x for x in changes if any(x['package'].startswith(p) for p in E(i,'sensitive_prefixes'))];return [ck('kernel',v['kernel']==E(i,'kernel'),'REVALIDATE',{'expected':E(i,'kernel'),'actual':v['kernel']}),ck('nvidia',v['nvidia']==E(i,'nvidia'),'REVALIDATE',{'expected':E(i,'nvidia'),'actual':v['nvidia']}),ck('packages',not changes,'REVALIDATE' if sensitive else 'DRIFT',changes)]
  if i=='C01':return [ck(k,v[k]==E(i,k),'DRIFT',{'expected':E(i,k),'actual':v[k]}) for k in ['version','cli_sha256']]
  if i=='C02':
   checks=[ck(k,v.get(k)==x['value'],detail={'expected':x['value'],'actual':v.get(k)}) for k,x in B[i].items()]
   checks.extend([ck('override_contextWindow',v.get('override_contextWindow')==E(i,'contextWindow')),ck('override_maxTokens',v.get('override_maxTokens')==E(i,'maxTokens'))]);comp=v.get('model_compaction_override')
   if comp:checks.extend(ck('model_compaction.'+k,comp.get(k)==E(i,k)) for k in ['reserveTokens','keepRecentTokens'])
   return checks
  if i=='C03':return [ck('vscode',E(i,'vscode') in v['vscode_versions'],'DRIFT'),ck('pi0.pi-vscode',E(i,'extension') in v['extensions'],'DRIFT')]
  if i=='C04':return [ck(k,v.get(k)==E(i,k),'DRIFT',{'expected':E(i,k),'actual':v.get(k)}) for k in ['fd','rg']]
  if i=='M01':return [ck('http_200',v['http_status']==E(i,'http_status')),ck('nonempty_content',bool(v.get('content','').strip())),ck('ttft_recorded',v.get('ttft_s') is not None)]
  if i=='M02':
   rows=v['body'].get('models',[]);q=next((x for x in rows if x.get('name')==E('M01','model')),{});return [ck('context_length',q.get('context_length')==E(i,'context_length'),detail={'expected':E(i,'context_length'),'actual':q.get('context_length')})]
  if i=='M03':
   qid=E('F04','models')[E('M01','model')][:12];return [ck('profile_logged',v['rc']==0 and any('Q6 profile applied' in l and 'model_id='+qid in l and E(i,'profile') in l for l in v['stdout'].splitlines()))]
  if i=='M04':
   renders=[(v[x]['body'].get('_debug_info') or {}).get('rendered_template') for x in E(i,'efforts')];return [ck('max_xhigh_render_identical',all(isinstance(x,str) and bool(x) for x in renders) and renders[0]==renders[1])]
  if i=='M05':
   ref=v.get('reference',{});checks=[ck('dimension',ref.get('dimension')==E(i,'dimension')),ck('two_runs',len(v.get('runs',[]))==E(i,'repeats')),ck('measured_tolerance',isinstance(ref.get('run_to_run_max_abs_diff'),(float,int)) and ref['run_to_run_max_abs_diff']>=0),ck('fixed_strings_hash',ref.get('strings_sha256')==E(i,'strings_sha256'))]
   if embedding_reference is not None:
    expected=embedding_reference;actual=[x['embedding'] for x in sorted(v['runs'][0]['body']['data'],key=lambda r:r['index'])];reference=expected['runs'][0];shape=len(actual)==len(reference) and all(len(x)==len(y)==E(i,'dimension') for x,y in zip(actual,reference));diff=max(abs(x-y) for aa,bb in zip(actual,reference) for x,y in zip(aa,bb)) if shape else None
    checks.append(ck('embedding_identity',shape and ref.get('strings_sha256')==expected['strings_sha256'] and diff is not None and math.isfinite(diff) and diff<=expected['comparison_atol'],detail={'max_abs_diff':diff,'accepted_atol':expected['comparison_atol']}))
   return checks
  if i=='M06':return [ck('no_q6_profile_during_embedding',v['rc']==0 and 'Q6 profile applied' not in v['stdout'])]
  if i=='M07':
   choices=v['body'].get('choices',[]);c=choices[0] if choices else {};return [{'check':'smoke_observation','status':'INFO','detail':{'finish_reason':c.get('finish_reason'),'visible_answer':bool(c.get('message',{}).get('content','').strip())}}]
  if i=='M08':
   cols=texts(v['collections']);search=texts(v['search']);return [ck('lab_docs',E(i,'collection') in cols),ck('nonzero_search','Result 1' in search),ck('known_document',E(i,'known_document') in search)]
  if i=='M09':return [ck('exit_0',v['rc']==E(i,'exit_code')),ck('nonempty_response',bool(v['stdout'].strip())),ck('temporary_home',v['temporary_home']),ck('live_configs_unchanged',v['live_configs_unchanged'])]
  if i=='M10':return [ck('20_of_20',v['passed']==E(i,'passed') and v['total']==E(i,'total'),detail={'passed':v['passed'],'total':v['total'],'failed_indexes':[x['index'] for x in v['checks'] if x['status']=='FAIL']})]
  if i=='M11':return [{'check':'captured_healthcheck','status':'INFO','detail':v}]
  if i=='M12':
   text=texts(v)
   try:data=json.loads(text)
   except json.JSONDecodeError:return [{'check':'external_search','status':'INFO','detail':'No parseable search result'}]
   return [{'check':'external_search','status':'PASS' if data.get('results') else 'INFO','detail':{'count':len(data.get('results',[]))}}]
  return [ck('known_test',False,'TEST_DEFECT')]
 for i,v in raw.get('tests',{}).items():
  try:checks=each(i,v)
  except Exception as ex:checks=[ck('evaluator',False,'TEST_DEFECT',{'type':type(ex).__name__,'message':str(ex)})]
  emit(i,checks,v)
 return {'started_at':raw.get('started_at'),'finished_at':raw.get('finished_at'),'duration_min':raw.get('duration_min'),'results':out,'counts':dict(collections.Counter(x['status'] for x in out))}
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,default=Path(__file__).with_name('baseline.json'));p.add_argument('--raw',type=Path,required=True);p.add_argument('--client',type=Path);p.add_argument('--embedding-reference',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();raw=json.loads(a.raw.read_text());report=evaluate(json.loads(a.baseline.read_text()),raw,json.loads(a.client.read_text()) if a.client else None,json.loads(a.embedding_reference.read_text()) if a.embedding_reference else None);a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['counts']));raise SystemExit(2 if report['counts'].get('TEST_DEFECT') else 1 if any(report['counts'].get(x) for x in ['FAIL','REVALIDATE']) else 0)
if __name__=='__main__':main()
