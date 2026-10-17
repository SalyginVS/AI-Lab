#!/usr/bin/env python3
"""Offline classification controls, including failures that must not become PASS."""
import copy,hashlib,json,runpy
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
assert before==hashlib.sha256(path.read_bytes()).hexdigest()
print('EVALUATOR_CONTROLS=PASS 10; BASELINE_UNCHANGED=YES')
