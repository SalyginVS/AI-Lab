#!/usr/bin/env python3
"""Read-only MCP initialize/tools-list/tool-call probe."""
import argparse,json,urllib.request

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',required=True);p.add_argument('--tool',required=True);p.add_argument('--arguments',default='{}');a=p.parse_args()
    headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
    def call(body):
        q=urllib.request.Request(a.url,data=json.dumps(body).encode(),headers=headers)
        with urllib.request.urlopen(q,timeout=45) as r:
            session=r.headers.get('Mcp-Session-Id')
            if session:headers['Mcp-Session-Id']=session
            text=r.read().decode()
        if not text:return None
        if text.startswith(('event:','data:')):
            values=[l[5:].strip() for l in text.splitlines() if l.startswith('data:')]
            return json.loads(values[-1]) if values else None
        return json.loads(text)
    initialized=call({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'rb07-probe','version':'1.0'}}})
    assert initialized and 'result' in initialized,initialized
    call({'jsonrpc':'2.0','method':'notifications/initialized'})
    tools=call({'jsonrpc':'2.0','id':2,'method':'tools/list'});assert a.tool in [t['name'] for t in tools['result']['tools']]
    result=call({'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':a.tool,'arguments':json.loads(a.arguments)}})
    assert result and 'result' in result and not result['result'].get('isError'),result
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
