#!/usr/bin/env python3
"""MBIP-05 boot/client file transaction. No service start, inference or reboot."""
import argparse, base64, contextlib, copy, fcntl, hashlib, json, os, re, stat, subprocess, tempfile, urllib.request
from pathlib import Path
PKG=Path(__file__).resolve().parent
FLASH="qwen3.8-flash-next-ud-q6_k_xl"
INK="inkling-2-mini-sq-20"
PROVIDER="ailab-strata"
PROFILES={"flash":"405f4d7afa40e7d6ebec2359bc77a4cf419e7a16413e6d706def583e676493d6","inkling":"d5c02363eeb200e414940de3be05e2964136d356c8516174a6ca7021b64ac6df"}
SWITCH="181569c830f2a73d07d476dba27b63a89122fdac228c1f965cd043c96744826e"
UNITS="etc/systemd/system/"
OLD=("ollama.service","llm-gateway.service","rag-mcp.service")
BOOT="mbip-strata.service"
KEEP=("ailab-gpu-power.service","ailab-postboot-check.service")
FILES={
 "stage/systemd/mbip-strata.service.d/97-mbip05-boot.conf":UNITS+"mbip-strata.service.d/97-mbip05-boot.conf",
 "stage/systemd/ailab-postboot-check.service.d/95-mbip05-mode.conf":UNITS+"ailab-postboot-check.service.d/95-mbip05-mode.conf",
 "stage/mbip05-postboot-readiness":"usr/local/libexec/ailab/mbip05-postboot-readiness",
 "stage/tmpfiles/mbip05.conf":"etc/tmpfiles.d/mbip05.conf"}
LINKS={u:UNITS+("default.target.wants/" if u==OLD[0] else "multi-user.target.wants/")+u for u in (*OLD,BOOT,*KEEP)}
GATES=("thermal_gpu_gddr6x","thermal_storage","inkling_e01","flash_api","inkling_cli","inkling_ide","flash_cli","flash_ide","ollama_reserve","f07_review","owner_deployment_review")
class Refused(RuntimeError):pass
def need(c,m):
    if not c:raise Refused(m)
def sha(data):return hashlib.sha256(data).hexdigest()
def jsonbytes(x):return (json.dumps(x,ensure_ascii=False,indent=2)+"\n").encode()
def run(*args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60)
    need(p.returncode==0,"Command failed: "+args[0]+" "+args[1])
    return p.stdout.strip()
def safe(root,rel):
    p=Path(rel);need(not p.is_absolute() and p.parts and ".." not in p.parts,"Unsafe path")
    q=root
    for part in p.parts[:-1]:
        q=q/part
        if q.exists() or q.is_symlink():need(q.is_dir() and not q.is_symlink(),"Unsafe parent: "+rel)
    return root/p
def regular(p):
    need(p.is_file() and not p.is_symlink(),"Expected regular file: "+p.name)
    return p.read_bytes()
def trusted(p,uid):
    st=p.lstat();need(not p.is_symlink() and st.st_uid==uid and not st.st_mode&0o022,"Untrusted file or directory: "+p.name)
def manifest():
    raw=regular(PKG/"SHA256SUMS")
    rows={}
    for line in raw.decode().splitlines():
        m=re.fullmatch(r"([0-9a-f]{64})  (.+)",line);need(m is not None,"Manifest syntax")
        name=m[2];need(name not in rows,"Duplicate manifest path")
        need(sha(regular(safe(PKG,name)))==m[1],"Manifest mismatch: "+name)
        rows[name]=m[1]
    actual={x.relative_to(PKG).as_posix() for x in PKG.rglob("*") if x.is_file() and not x.is_symlink() and x.name!="SHA256SUMS"}
    need(not any(x.is_symlink() for x in PKG.rglob("*")) and actual==set(rows),"Manifest inventory mismatch")
    need(set(FILES)<=set(rows) and "deploy.py" in rows and "pi-config-intent.json" in rows,"Manifest incomplete")
    for n,h in PROFILES.items():need(rows.get("stage/profiles/strata-mbip-"+n+".json")==h,"Profile fingerprint")
    return sha(raw),rows
def receipt(path,scope,live,root,manifest_hash):
    need(path is not None,"Private acceptance receipt required")
    trusted(path,os.geteuid());r=json.loads(regular(path))
    need(r.get("kind")==("live" if live else "fixture"),"Wrong receipt kind")
    need(r.get("scope")==scope and r.get("root")==str(root),"Receipt target mismatch")
    need(r.get("package_manifest_sha256")==manifest_hash and r.get("profiles")==PROFILES,"Receipt fingerprint mismatch")
    need(r.get("power_w")==300 and r.get("owner_approved") is True,"Owner/300 W approval required")
    need(set(r.get("gates",{}))==set(GATES),"Incomplete gate set")
    for name in GATES:
        v=r["gates"][name];need(v.get("result")=="PASS","Gate open: "+name)
        p=safe(path.parent,v["evidence"]);trusted(p,os.geteuid())
        need(sha(regular(p))==v["sha256"],"Evidence mismatch: "+name)
    if live:
        need(r.get("reviewer") and r.get("reviewed_at"),"Independent review required")
        need(r.get("drained") is True,"Drained/closed client session confirmation required")
        need(len({v["evidence"] for v in r["gates"].values()})==len(GATES),"Separate live gate evidence required")
    return r
def state(p):
    try:s=p.lstat()
    except FileNotFoundError:return {"kind":"absent"}
    r={"uid":s.st_uid,"gid":s.st_gid,"mode":stat.S_IMODE(s.st_mode)}
    if stat.S_ISLNK(s.st_mode):return dict(r,kind="link",target=os.readlink(p))
    if stat.S_ISREG(s.st_mode):return dict(r,kind="file",data=base64.b64encode(p.read_bytes()).decode())
    if stat.S_ISDIR(s.st_mode):return dict(r,kind="dir")
    raise Refused("Unsupported object: "+p.name)
def file_state(data,mode,uid,gid):return dict(kind="file",data=base64.b64encode(data).decode(),mode=mode,uid=uid,gid=gid)
def link_state(target,uid,gid):return dict(kind="link",target=target,mode=0o777,uid=uid,gid=gid)
ABSENT={"kind":"absent"}
def syncdir(p):
    fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
def put(p,s):
    old=state(p)
    if old==s:return
    if s["kind"]=="absent":
        if old["kind"]=="dir":p.rmdir()
        elif old["kind"]!="absent":p.unlink()
    elif s["kind"]=="dir":
        need(old==ABSENT,"Cannot overwrite directory")
        p.mkdir(mode=s["mode"]);os.chown(p,s["uid"],s["gid"]);p.chmod(s["mode"])
    else:
        need(old["kind"] in ("absent","file","link"),"Cannot replace non-file")
        with tempfile.TemporaryDirectory(prefix=".mbip05-",dir=p.parent) as d:
            t=Path(d)/"object"
            if s["kind"]=="link":
                t.symlink_to(s["target"]);os.chown(t,s["uid"],s["gid"],follow_symlinks=False)
            else:
                with t.open("xb") as f:
                    f.write(base64.b64decode(s["data"],validate=True));f.flush()
                    os.fchown(f.fileno(),s["uid"],s["gid"]);os.fchmod(f.fileno(),s["mode"]);os.fsync(f.fileno())
            os.replace(t,p)
    syncdir(p.parent)
    need(state(p)==s,"Object verification failed: "+p.name)
def enabled(root,u):
    p=subprocess.run(["systemctl","--root="+str(root),"is-enabled",u],capture_output=True,text=True,timeout=15)
    return p.stdout.strip()
def check_boot(root,installed):
    expect={BOOT:"enabled" if installed else "static",**{u:"disabled" if installed else "enabled" for u in OLD},**{u:"enabled" for u in KEEP}}
    for u,v in expect.items():need(enabled(root,u)==v,"Unexpected enablement: "+u)
def assert_profiles(root):
    for n,h in PROFILES.items():
        p=safe(root,"etc/mbip05/profiles/strata-mbip-"+n+".json")
        if root==Path("/"):trusted(p,0)
        need(sha(regular(p))==h,"Installed profile not accepted candidate: "+n)
    switch=safe(root,"usr/local/sbin/mbip-backend")
    if root==Path("/"):trusted(switch,0)
    need(sha(regular(switch))==SWITCH,"Switcher fingerprint")
def server_plan(root):
    check_boot(root,False);assert_profiles(root)
    uid,gid=os.geteuid(),os.getegid();changes={}
    for src,dst in FILES.items():
        need(state(safe(root,dst))==ABSENT,"New boot artifact already exists: "+dst)
        parent=Path(dst).parent
        for i in range(1,len(parent.parts)+1):
            n=str(Path(*parent.parts[:i]));p=safe(root,n)
            if state(p)==ABSENT:changes[n]=dict(kind="dir",uid=uid,gid=gid,mode=0o755)
            else:need(state(p)["kind"]=="dir","Unexpected directory: "+n)
        changes[dst]=file_state(regular(safe(PKG,src)),0o755 if "libexec" in dst else 0o644,uid,gid)
    for u in (*OLD,*KEEP):
        p=safe(root,LINKS[u]);s=state(p)
        need(s["kind"]=="link" and s["target"]=="/"+UNITS+u,"Unexpected original unit link: "+u)
        if u in OLD:changes[LINKS[u]]=ABSENT
    need(state(safe(root,LINKS[BOOT]))==ABSENT,"Unexpected existing Strata link")
    changes[LINKS[BOOT]]=link_state("/"+UNITS+BOOT,uid,gid)
    return changes
def client_plan(root,r):
    mpath=".pi/agent/models.json";spath=".pi/agent/settings.json"
    mp,sp=[safe(root,x) for x in (mpath,spath)]
    mraw,sraw=regular(mp),regular(sp)
    need(r.get("client_before")=={"models.json":sha(mraw),"settings.json":sha(sraw)},"Client changed since review")
    m,s=json.loads(mraw),json.loads(sraw);nm,ns=copy.deepcopy(m),copy.deepcopy(s)
    p=nm["providers"][PROVIDER];need("ailab-ollama" in nm["providers"],"Ollama provider missing")
    need(p.get("api")=="openai-completions" and p.get("baseUrl")=="http://127.0.0.1:18081/v1","Wrong provider endpoint")
    intent=json.loads(regular(PKG/"pi-config-intent.json"))
    models={x["id"]:x for x in intent["models"]}
    need(len(p["models"])==2 and {x["id"] for x in p["models"]}==set(models)=={FLASH,INK},"Unexpected model IDs")
    for x in p["models"]:
        v=models[x["id"]]
        need(x.get("reasoning") is True and x.get("input")==["text"] and x.get("thinkingLevelMap")==v["thinkingLevelMap"],"Model metadata mismatch")
        x.update(contextWindow=v["contextWindow"],maxTokens=v["maxTokens"])
        k=PROVIDER+"/"+x["id"]
        ns.setdefault("compaction",{}).setdefault("modelOverrides",{})[k]=v["compaction"]
        ns.setdefault("modelThinkingLevels",{})[k]=v["thinking"]
    need(ns["compaction"].get("enabled") is True,"Compaction disabled")
    ns.update(defaultProvider=PROVIDER,defaultModel=INK)
    need(nm["providers"]["ailab-ollama"]==m["providers"]["ailab-ollama"] and ns.get("defaultThinkingLevel")==s.get("defaultThinkingLevel"),"Unrelated policy changed")
    return {rel:file_state(jsonbytes(x),state(p)["mode"],state(p)["uid"],state(p)["gid"]) for rel,p,x in ((mpath,mp,nm),(spath,sp,ns))}
def live_server_preflight(root):
    need(os.geteuid()==0 and root==Path("/"),"Live server root required")
    need(run("systemctl","is-active",BOOT)=="active","Strata inactive")
    for u in OLD:
        q=subprocess.run(["systemctl","is-active",u],capture_output=True,text=True,timeout=10)
        need(q.stdout.strip()=="inactive","Competing backend")
    need(run("systemctl","is-active",KEEP[0])=="active","Power service inactive")
    need(run("ss","-Htn","state","established","( sport = :18081 )")=="","Open clients")
    need(run("ss","-Hlt","( sport = :11434 or sport = :8000 or sport = :8100 )")=="","Competing listener")
    pointer=Path("/run/mbip05/active.json")
    need(pointer.is_symlink() and pointer.lstat().st_uid==0 and os.readlink(pointer)=="/etc/mbip05/profiles/strata-mbip-inkling.json","Wrong runtime pointer")
    power=run("nvidia-smi","--query-gpu=power.limit,temperature.gpu,clocks_event_reasons.hw_thermal_slowdown,clocks_event_reasons.sw_thermal_slowdown","--format=csv,noheader,nounits")
    w,t,hw,sw=map(str.strip,power.split(","));need(float(w)==300 and int(t)<82 and hw==sw=="Not Active","Power/thermal state")
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open("http://127.0.0.1:18081/v1/status",timeout=5) as response:st=json.load(response)
    need(st.get("loaded") is True and st.get("model")==INK and st.get("context")=={"native":262144,"max_positions":262144} and st.get("activity",{}).get("in_flight")==0,"Actual runtime not ready/drained")
def postcheck(root,scope,installed,live):
    if scope=="server":
        check_boot(root,installed)
        if live:
            run("systemctl","daemon-reload")
            run("systemd-analyze","verify",BOOT,KEEP[1])
def writejournal(p,j):
    fd,tmp=tempfile.mkstemp(prefix=".journal-",dir=p.parent)
    with os.fdopen(fd,"wb") as f:
        f.write(jsonbytes(j));f.flush();os.fsync(f.fileno())
    os.replace(tmp,p);syncdir(p.parent)
def restore(root,j,scope,live):
    # Check every target before the first rollback mutation. Do not overwrite third-party changes.
    for e in j["entries"]:
        p=safe(root,e["path"]);need(state(p) in (e["before"],e["after"]),"Rollback conflict: "+e["path"])
        if e["before"]==ABSENT and e["after"]["kind"]=="dir" and p.is_dir():
            planned={Path(x["path"]).name for x in j["entries"] if str(Path(x["path"]).parent)==e["path"]}
            need({x.name for x in p.iterdir()}<=planned,"Rollback directory conflict")
    for e in reversed(j["entries"]):
        p=safe(root,e["path"]);need(state(p) in (e["before"],e["after"]),"Concurrent rollback conflict: "+e["path"])
        put(p,e["before"])
    postcheck(root,scope,False,live)
    need(all(state(safe(root,e["path"]))==e["before"] for e in j["entries"]),"Rollback verification")
def transact(root,backup,scope,live,changes,fail_after=None):
    entries=[dict(path=k,before=state(safe(root,k)),after=v) for k,v in changes.items()]
    backup.mkdir(mode=0o700,exist_ok=False);syncdir(backup.parent)
    journal=backup/"transaction.json"
    j=dict(root=str(root),scope=scope,live=live,status="PREPARED",entries=entries)
    writejournal(journal,j);print("BACKUP",backup,flush=True)
    try:
        for i,e in enumerate(entries,1):
            p=safe(root,e["path"]);need(state(p)==e["before"],"Concurrent modification: "+e["path"])
            put(p,e["after"])
            if fail_after==i:raise Refused("Injected fixture failure")
        postcheck(root,scope,True,live)
        need(all(state(safe(root,e["path"]))==e["after"] for e in entries),"Final verification")
        j["status"]="INSTALLED";writejournal(journal,j)
    except BaseException:
        try:restore(root,j,scope,live);j["status"]="ROLLED_BACK"
        except BaseException:j["status"]="RECOVERY_REQUIRED";writejournal(journal,j);raise
        writejournal(journal,j);raise
def rollback(root,backup,scope,live):
    trusted(backup,os.geteuid());need(stat.S_IMODE(backup.stat().st_mode)==0o700,"Backup must be private")
    p=backup/"transaction.json";trusted(p,os.geteuid());j=json.loads(regular(p))
    need((j["root"],j["scope"],j["live"])==(str(root),scope,live),"Rollback target mismatch")
    restore(root,j,scope,live);j["status"]="ROLLED_BACK";writejournal(p,j)
def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("operation",choices=["server-install","server-rollback","client-install","client-rollback"])
    a.add_argument("--root",type=Path,required=True);a.add_argument("--backup",type=Path,required=True)
    a.add_argument("--receipt",type=Path);a.add_argument("--live",action="store_true")
    a.add_argument("--fixture-fail-after",type=int)
    o=a.parse_args();root=o.root.resolve();backup=o.backup.absolute();scope,op=o.operation.split("-")
    need(root.is_dir() and not o.root.is_symlink(),"Invalid root")
    if o.live:
        need(o.fixture_fail_after is None,"Fixture fault injection forbidden live")
        need(root==(Path("/") if scope=="server" else Path.home().resolve()),"Wrong live root")
        need((os.geteuid(),os.getegid())==(0,0) if scope=="server" else os.geteuid()!=0,"Wrong privilege level")
        for p in [PKG,PKG/"SHA256SUMS",*PKG.rglob("*")]:trusted(p,os.geteuid())
    else:
        need(root!=Path("/") and root!=Path.home().resolve(),"Fixture cannot target live root")
        need(regular(root/".mbip05-fixture")==b"MBIP05_ISOLATED_FIXTURE\n","Fixture marker required")
        need(not backup.is_relative_to(root),"Fixture backup must be outside root")
    need(backup.parent.is_dir() and not backup.parent.is_symlink(),"Private backup parent required")
    trusted(backup.parent,os.geteuid())
    need(stat.S_IMODE(backup.parent.stat().st_mode)==0o700,"Backup parent mode must be 0700")
    lock=(Path("/run/lock/mbip-strata-smoke.lock") if scope=="server" else safe(root,".pi/agent/.mbip05-deploy.lock")) if o.live else backup.parent/".mbip05-deploy.lock"
    fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"a") as f:
        fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if op=="rollback":rollback(root,backup,scope,o.live)
        else:
            digest,_=manifest();r=receipt(o.receipt,scope,o.live,root,digest)
            if scope=="server" and o.live:live_server_preflight(root)
            changes=server_plan(root) if scope=="server" else client_plan(root,r)
            transact(root,backup,scope,o.live,changes,o.fixture_fail_after)
    print("MBIP05_TRANSACTION_"+("INSTALLED" if op=="install" else "ROLLED_BACK"))
if __name__=="__main__":
    try:main()
    except (Refused,OSError,ValueError,KeyError,subprocess.SubprocessError) as e:
        raise SystemExit("MBIP05_REFUSED "+str(e))
