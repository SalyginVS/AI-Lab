#!/usr/bin/env python3
"""Offline classification controls, including failures that must not become PASS."""
import ast,copy,hashlib,json,runpy
from pathlib import Path
H=Path(__file__).resolve().parent
E=runpy.run_path(str(H/'evaluate.py'))['evaluate'];path=H/'baseline.json';before=hashlib.sha256(path.read_bytes()).hexdigest();B=json.loads(path.read_text())
def status(i,v):return E(B,{'tests':{i:v}})['results'][0]['status']
assert status('M02',{'body':{'models':[{'name':B['tests']['M01']['model']['value'],'context_length':32768}]}})=='FAIL'
assert status('M01',{'http_status':200,'content':'','ttft_s':1})=='FAIL'
assert status('M01',{'http_status':200,'content':'OK','ttft_s':1})=='PASS'
f={k:v['value'] for k,v in B['tests']['F01'].items()};f['version']='changed';assert status('F01',f)=='REVALIDATE'
f={'packages':copy.deepcopy(B['tests']['F07']['packages']['value']),'kernel':B['tests']['F07']['kernel']['value'],'nvidia':B['tests']['F07']['nvidia']['value']};f['packages']['curl']='different';assert status('F07',f)=='DRIFT'
f['kernel']='different';assert status('F07',f)=='REVALIDATE'
assert status('C04',{'fd':'wrong','rg':'wrong'})=='DRIFT'
assert status('UNKNOWN',{})=='TEST_DEFECT'
vectors=[[0.0]*4096 for _ in range(3)]
reference={'strings_sha256':B['tests']['M05']['strings_sha256']['value'],'dimension':4096,'comparison_atol':0.0,'runs':[vectors,copy.deepcopy(vectors)]}
probe={'reference':{'dimension':4096,'strings_sha256':reference['strings_sha256'],'run_to_run_max_abs_diff':0.0},'runs':[{'body':{'data':[{'index':i,'embedding':row} for i,row in enumerate(copy.deepcopy(vectors))]}},{'body':{'data':[]}}]}
assert E(B,{'tests':{'M05':probe}},embedding_reference=reference)['results'][0]['status']=='PASS'
probe['runs'][0]['body']['data'][2]['embedding'][123]=0.00001
assert E(B,{'tests':{'M05':probe}},embedding_reference=reference)['results'][0]['status']=='FAIL'
live=json.loads((H/'baseline.live-2026-10-18.json').read_text())
historical=json.loads((H/'baseline.live-2026-10-17.json').read_text())
assert 'F09' not in B['tests'] and 'F09' not in historical['tests']
assert {k:v for k,v in live['tests'].items() if k!='F09'}==historical['tests']
assert set(live['tests']['F09'])=={'power_limit_w','active','substate','result','exec_main_status','enabled'}
good={'power_limit_w':300.0,'power_rc':0,'unit_rc':0,'active':'active','substate':'exited','result':'success','exec_main_status':'0','enabled':'enabled','enabled_rc':0}
assert E(live,{'tests':{'F09':good}})['results'][0]['status']=='PASS'
for bad in [{**good,'power_limit_w':420.0},{**good,'power_limit_w':350.0},{**good,'power_limit_w':None,'power_rc':1},{**good,'substate':'dead'},{**good,'enabled':'disabled'},{**good,'unit_rc':1}]:
 assert E(live,{'tests':{'F09':bad}})['results'][0]['status']=='FAIL'
assert E(B,{'tests':{'F09':good}})['results'][0]['status']=='INFO'
# Collector contract: execute only F09 definition against inert command stubs.
script=(H/'t_fast_server.sh').read_text().split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
node=next(n for n in ast.parse(script).body if isinstance(n,ast.FunctionDef) and n.name=='f09')
def stub(args):
 if args[0]=='nvidia-smi':return {'rc':0,'stdout':'300.00\n','stderr':''}
 if args[1]=='show':return {'rc':0,'stdout':'ActiveState=active\nSubState=exited\nResult=success\nExecMainStatus=0\n','stderr':''}
 if args[1]=='is-enabled':return {'rc':0,'stdout':'enabled\n','stderr':''}
 raise AssertionError('unexpected read command')
namespace={'cmd':stub};exec(compile(ast.Module(body=[node],type_ignores=[]),'f09-collector','exec'),namespace)
assert namespace['f09']()==good
assert E(live,{'tests':{'F09':namespace['f09']()}})['results'][0]['status']=='PASS'
assert before==hashlib.sha256(path.read_bytes()).hexdigest()
print('EVALUATOR_CONTROLS=PASS; F09_PASS_FAIL_INFO=PASS; BASELINE_UNCHANGED=YES')
