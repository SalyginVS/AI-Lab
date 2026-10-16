#!/usr/bin/env python3
"""Render service templates or generate new installation credentials."""
import argparse,json,os,re,secrets
from pathlib import Path

def write_private(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8',newline='') as f:f.write(data)

def main():
    p=argparse.ArgumentParser();sp=p.add_subparsers(dest='command',required=True)
    r=sp.add_parser('templates');r.add_argument('--source',type=Path,required=True);r.add_argument('--output',type=Path,required=True);r.add_argument('--root',required=True);r.add_argument('--operator',required=True)
    e=sp.add_parser('credentials');e.add_argument('--output',type=Path,required=True);e.add_argument('--operator',required=True)
    s=sp.add_parser('settings');s.add_argument('--template',type=Path,required=True);s.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.command=='templates':
        if not re.fullmatch(r'/[A-Za-z0-9_./-]+',a.root) or '..' in Path(a.root).parts:p.error('root must be an absolute path without spaces or parent traversal')
        if not re.fullmatch(r'[a-z_][a-z0-9_-]*',a.operator):p.error('invalid operator')
        for f in sorted((a.source/'units').rglob('*.in')):
            out=a.output/'units'/f.relative_to(a.source/'units');out=out.with_suffix('');out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(f.read_bytes().replace(b'@LAB_SERVICE_ROOT@',a.root.encode()).replace(b'@LAB_OPERATOR@',a.operator.encode()))
        a.output.mkdir(parents=True,exist_ok=True)
        (a.output/'cron').write_bytes((a.source/'cron.in').read_bytes().replace(b'@LAB_SERVICE_ROOT@',a.root.encode()))
        (a.output/'docker-compose.yml').write_bytes((a.source/'searxng/docker-compose.yml').read_bytes().replace(b'@LAB_SERVICE_ROOT@',a.root.encode()))
    elif a.command=='credentials':
        user,client,orchestrator=[secrets.token_hex(32) for _ in range(3)]
        tokens={user:a.operator,client:'roadwarrior',orchestrator:'orchestrator'}
        write_private(a.output,"LLM_GATEWAY_TOKENS='"+json.dumps(tokens,separators=(',',':'))+"'\nLLM_ORCHESTRATOR_TOKEN="+orchestrator+'\n')
    else:
        text=a.template.read_text();assert text.count('@SEARXNG_SECRET_KEY@')==1
        write_private(a.output,text.replace('@SEARXNG_SECRET_KEY@',secrets.token_hex(32)))
if __name__=='__main__':main()
