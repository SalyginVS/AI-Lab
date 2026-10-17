#!/usr/bin/env bash
set -euo pipefail
exec python3 -I - "$0" "$@" <<'PY'
import argparse,hashlib,json,os,pwd,re,shutil,subprocess,sys,tempfile
from pathlib import Path

package=Path(sys.argv[1]).resolve().parent
p=argparse.ArgumentParser(description='Install pinned postboot checks; no model inference or service start.')
p.add_argument('--repo',type=Path,default=package.parents[2])
p.add_argument('--commit',help='Full source commit, required for an exported git archive')
p.add_argument('--root',type=Path,default=Path('/'),help='Offline staging root; skips systemctl and account lookup')
p.add_argument('--baseline-name',default='baseline.live-2026-10-17.json',help='Baseline filename already included in the installed suite')
p.add_argument('--uninstall',action='store_true')
a=p.parse_args(sys.argv[2:]);root=a.root.resolve();staging=root!=Path('/')
if not staging and os.geteuid()!=0:raise SystemExit('Run installer as root')
def target(name):return root/name.lstrip('/')
def systemctl(*args):
 if not staging:subprocess.run(['systemctl',*args],check=True)
def put(path,data,mode):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data)
  os.chmod(tmp,mode)
  if not staging:os.chown(tmp,0,0)
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
suite_parent=target('/opt/ailab-acceptance');unit=target('/etc/systemd/system/ailab-postboot-check.service')
libexec=target('/usr/local/libexec/ailab')
if a.uninstall:
 systemctl('disable','--now','ailab-postboot-check.service')
 for f in [unit,libexec/'postboot-check.sh',libexec/'known-findings.json']:
  if f.is_file():f.unlink()
 current=suite_parent/'current'
 if current.is_symlink():current.unlink()
 if suite_parent.exists():
  for d in suite_parent.iterdir():
   marker=d/'INSTALLATION.json'
   if d.is_dir() and not d.is_symlink() and marker.is_file():
    metadata=json.loads(marker.read_text())
    if metadata.get('installer')=='ailab-postboot-v1' and metadata.get('commit','')[:12]==d.name:shutil.rmtree(d)
 systemctl('daemon-reload')
 print(json.dumps({'action':'uninstalled','staging':staging,'retained':'logs and older suites without this installer marker'}));raise SystemExit(0)
operator=os.environ.get('LAB_OPERATOR','')
if not re.fullmatch(r'[a-z_][a-z0-9_-]*',operator):raise SystemExit('Set LAB_OPERATOR to the target operator account')
if not staging:pwd.getpwnam(operator)
repo=a.repo.resolve();commit=a.commit
if commit is None:commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
if not re.fullmatch(r'[0-9a-f]{40}',commit):raise SystemExit('Expected full 40-character commit')
if (repo/'.git').exists():
 actual=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 if actual!=commit:raise SystemExit('Source checkout does not match --commit')
 elif subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']):raise SystemExit('Source checkout must be clean')
elif not (repo/'SOURCE_COMMIT').is_file() or (repo/'SOURCE_COMMIT').read_text().strip()!=commit:
 raise SystemExit('Export must contain SOURCE_COMMIT from its git archive producer')
for line in (package/'SHA256SUMS').read_text().splitlines():
 digest,name=line.split('  ',1)
 if hashlib.sha256((package/name).read_bytes()).hexdigest()!=digest:raise SystemExit('Postboot artifact checksum mismatch: '+name)
names=['Сборка/tests/acceptance/t_fast_server.sh','Сборка/tests/acceptance/evaluate.py','Сборка/tests/acceptance/baseline.json','Сборка/tests/acceptance/baseline.live-2026-10-17.json','Сборка/artifacts/q6/llama-server.wrapper.in']
baseline_names={Path(n).name for n in names if n.startswith('Сборка/tests/acceptance/') and Path(n).match('baseline*.json')}
if not re.fullmatch(r'baseline[^/]*\.json',a.baseline_name) or a.baseline_name not in baseline_names:
 raise SystemExit('Baseline must be a baseline*.json file included in the installed suite')
postboot_source=(package/'postboot-check.sh.in').read_bytes()
baseline_line=b'baseline_name=baseline.live-2026-10-17.json'
if postboot_source.count(baseline_line)!=1:raise SystemExit('Expected exactly one baseline_name assignment')
postboot_script=postboot_source.replace(baseline_line,('baseline_name='+a.baseline_name).encode())
data={n:(repo/n).read_bytes() for n in names};data['SOURCE_COMMIT']=(commit+'\n').encode()
data['SHA256SUMS']=''.join(hashlib.sha256(v).hexdigest()+'  '+n+'\n' for n,v in data.items()).encode()
data['INSTALLATION.json']=(json.dumps({'installer':'ailab-postboot-v1','commit':commit},sort_keys=True)+'\n').encode()
destination=suite_parent/commit[:12];suite_parent.mkdir(parents=True,exist_ok=True)
if destination.exists():
 if destination.is_symlink() or any(not (destination/n).is_file() or (destination/n).read_bytes()!=b for n,b in data.items()):raise SystemExit('Immutable suite directory differs; use a new accepted commit')
else:
 tmp=Path(tempfile.mkdtemp(prefix='.stage-',dir=suite_parent))
 try:
  for n,b in data.items():put(tmp/n,b,0o644)
  for d in [tmp,*[p for p in tmp.rglob('*') if p.is_dir()]]:
   d.chmod(0o755)
   if not staging:os.chown(d,0,0)
  os.replace(tmp,destination)
 finally:
  if tmp.exists():shutil.rmtree(tmp)
unit_bytes=(package/'ailab-postboot-check.service.in').read_text().replace('@LAB_OPERATOR@',operator).encode()
if b'@LAB_' in unit_bytes:raise SystemExit('Unresolved unit marker')
put(libexec/'postboot-check.sh',postboot_script,0o755)
put(libexec/'known-findings.json',(package/'known-findings.json').read_bytes(),0o644)
put(unit,unit_bytes,0o644)
link=suite_parent/('.current-'+str(os.getpid()));link.symlink_to(destination.name);os.replace(link,suite_parent/'current')
systemctl('daemon-reload');systemctl('enable','ailab-postboot-check.service')
receipt={'action':'installed','commit':commit,'suite':str(destination),'staging':staging,'unit_enabled':not staging,'service_started':False,'files':{n:hashlib.sha256(b).hexdigest() for n,b in data.items()}}
print(json.dumps(receipt,ensure_ascii=False))
PY
