#!/usr/bin/python3
"""MBIP-05: replace only the pilot Strata model and add per-model settings."""
import argparse,copy,hashlib,json,os,stat,tempfile
from pathlib import Path
MODELS={
    "flash":("qwen3.8-flash-next-ud-q6_k_xl","Qwen3.8 Flash-Next UD-Q6_K_XL (Strata)",8192,2048,2048),
    "inkling":("inkling-2-mini-sq-20","Inkling 2 Mini SQ-20 (Strata)",32768,8192,8192),
}
PILOT="qwen3.6-35b-a3b-ud-q4_k_xl"
PROVIDER="ailab-strata"
def sha(b):return hashlib.sha256(b).hexdigest()
def evolve(models,settings,default=None):
    m,s=copy.deepcopy(models),copy.deepcopy(settings)
    providers=m["providers"]
    p=providers[PROVIDER]
    assert "ailab-ollama" in providers
    assert p["baseUrl"]=="http://127.0.0.1:18081/v1" and p["api"]=="openai-completions"
    ids={x["id"] for x in p["models"]}
    desired={x[0] for x in MODELS.values()}
    assert ids in ({PILOT},desired),f"Unexpected Strata model IDs: {ids}"
    template=p["models"][0]
    new=[]
    for mid,label,ctx,out,keep in MODELS.values():
        x=copy.deepcopy(template)
        x.update(id=mid,name=label,contextWindow=ctx,maxTokens=out,input=["text"])
        new.append(x)
        s.setdefault("compaction",{}).setdefault("modelOverrides",{})[f"{PROVIDER}/{mid}"]={"reserveTokens":out,"keepRecentTokens":keep}
        s.setdefault("modelThinkingLevels",{})[f"{PROVIDER}/{mid}"]="low"
    p["models"]=new
    if default:
        s.update(defaultProvider=PROVIDER,defaultModel=MODELS[default][0],defaultThinkingLevel="low")
    assert {k:v for k,v in providers.items() if k!=PROVIDER}=={k:v for k,v in models["providers"].items() if k!=PROVIDER}
    return m,s
def commit(p,old,new):
    if old==new:return
    raw=json.dumps(new,ensure_ascii=False,indent=2).encode()+b"\n"
    current=p.read_bytes()
    assert json.loads(current)==old,"Config changed during preparation"
    with tempfile.NamedTemporaryFile(dir=p.parent,prefix=".mbip05-",delete=False) as f:
        tmp=Path(f.name);f.write(raw)
    try:
        tmp.chmod(stat.S_IMODE(p.stat().st_mode))
        assert p.read_bytes()==current
        tmp.replace(p)
    finally:tmp.unlink(missing_ok=True)
    print(p.name,sha(current),"->",sha(raw))
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--root",type=Path,default=Path.home()/".pi/agent")
    a.add_argument("--default",choices=MODELS)
    a.add_argument("--backup",type=Path,required=True)
    args=a.parse_args()
    mp,sp=(args.root/n for n in ("models.json","settings.json"))
    for p in (mp,sp):
        assert p.is_file() and not p.is_symlink()
    m,s=map(lambda p:json.loads(p.read_bytes()),(mp,sp))
    nm,ns=evolve(m,s,args.default)
    args.backup.mkdir(mode=0o700,parents=True,exist_ok=False)
    for p in (mp,sp):
        q=args.backup/p.name
        q.write_bytes(p.read_bytes());q.chmod(0o600)
    commit(mp,m,nm)
    commit(sp,s,ns)
    assert json.loads(mp.read_bytes())==nm and json.loads(sp.read_bytes())==ns
    print("PI_MBIP05_CONFIG=PASS",args.backup)
if __name__=="__main__":main()
