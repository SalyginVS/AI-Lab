#!/usr/bin/env python3
"""Generate a deterministic local fixture only. Never contacts a model."""
import argparse,hashlib,json
from pathlib import Path
COUNT=224700
MARKERS={'BEGIN':'RB10_BEGIN_723cdaf090e1','MIDDLE':'RB10_MIDDLE_bfc490ac2398','END':'RB10_END_a427e2fa8ba9'}
def fixture():
 parts=['Read the following long record. Retain the three named marker values.\n']
 for i in range(COUNT):
  if i==100:parts.append('\nBEGIN='+MARKERS['BEGIN']+'\n')
  if i==COUNT//2:parts.append('\nMIDDLE='+MARKERS['MIDDLE']+'\n')
  if i==COUNT-100:parts.append('\nEND='+MARKERS['END']+'\n')
  parts.append(' a')
 parts.append('\nReturn a JSON object with exactly keys BEGIN, MIDDLE, END and their recorded values. No explanation.\n')
 body={'model':'qwen3.8-flash-next:125b-a6b-q6_K-ab-262k','messages':[{'role':'user','content':''.join(parts)}],'reasoning_effort':'xhigh','max_tokens':1024,'stream':False}
 return (json.dumps(body,ensure_ascii=False,separators=(',',':'))+'\n').encode()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();data=fixture();a.output.write_bytes(data);print(hashlib.sha256(data).hexdigest()+'  fixture.json')
