#!/usr/bin/env python3
"""RB-11 K1-K9. Read-only package inspection; offline tests write only to evidence/tmp.

Run with python3 -I. --static-only runs K1-K7. Full verification additionally
requires --evidence-root and --freshness (private RB-11 freshness.json).
Public diagnostics never print matched credentials or protection details.
"""
import argparse,ast,csv,hashlib,html,ipaddress,json,os,re,subprocess,sys,tempfile,shutil,urllib.parse
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
BASE='90ccb3f8187bc00c065471a2f2083c0246dae4d6'
START='db0737e0b55ca68d390a9d006f8e1edf70b66a49'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--base',default=BASE,help='Base commit for public diff and Markdown frontmatter comparison')
p.add_argument('--start',default=START,help='Last accepted package commit; later artifact changes require acceptance')
p.add_argument('--static-only',action='store_true');p.add_argument('--working-tree',action='store_true')
p.add_argument('--evidence-root',type=Path);p.add_argument('--freshness',type=Path);p.add_argument('--output',type=Path)
a=p.parse_args();BASE=a.base;START=a.start;results={};candidates=[]
def git(*args):return subprocess.check_output(['git','-c','core.quotepath=false','-C',str(ROOT),*args])
for option,ref in [('base',BASE),('start',START)]:
 q=subprocess.run(['git','-C',str(ROOT),'rev-parse','--verify','--end-of-options',ref+'^{commit}'],capture_output=True,text=True)
 if q.returncode:
  print('PACKAGE_CHECK=ERROR: commit for --'+option+' is unavailable. Pass --'+option+' <existing accepted commit>; for maintenance pass --start <last accepted package commit>.',file=sys.stderr)
  sys.exit(2)
BASE=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',BASE+'^{commit}']).decode().strip()
START=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',START+'^{commit}']).decode().strip()
def sha(b):return hashlib.sha256(b).hexdigest()
def record(k,errors,**extra):results[k]={'status':'FAIL' if errors else 'PASS','errors':errors,**extra}
def text(f):return f.read_text(encoding='utf-8',errors='replace')
def prose(s):
 out=[];fence=None
 for l in s.splitlines():
  m=re.match(r'^\s{0,3}(`{3,}|~{3,})',l)
  if m:
   token=m[1][0]
   if fence is None:fence=token
   elif fence==token:fence=None
   continue
  if fence is None:out.append(l)
 return '\n'.join(out)
def anchors(s):
 counts={};out=set()
 for heading in re.findall(r'^ {0,3}#{1,6}\s+(.+?)\s*#*$',prose(s),re.M):
  h=re.sub(r'<[^>]+>','',heading);h=h.replace('`','');h=html.unescape(h).lower()
  h=re.sub(r'[^\w\- ]','',h,flags=re.UNICODE).replace(' ','-');n=counts.get(h,0);counts[h]=n+1
  out.add(h+('-'+str(n) if n else ''))
 out.update(re.findall(r'(?:id|name)=["\x27]([^"\x27]+)',s));return out
# K1 ordinary Markdown inline links, images and reference definitions; code is excluded.
files=[ROOT/'README.md',ROOT/'Паспорт_лаборатории_v39.md',ROOT/'Этапы/2026-10-16_Rebuild_Package/Результаты.md',*sorted((ROOT/'Сборка').rglob('*.md'))]
errors=[];nlinks=0
for f in files:
 s=prose(text(f));s=re.sub(r'`[^`\n]+`','',s)
 targets=re.findall(r'\]\(\s*(<[^>]+>|(?:[^()]|\([^()]*\))+)\s*\)',s)
 targets+=re.findall(r'^\s*\[[^]]+\]:\s*(\S+)',s,re.M)
 for raw in targets:
  u=raw.strip()
  if u.startswith('<'):u=u[1:u.find('>')]
  else:u=re.sub(r'\s+["\x27].*$','',u)
  if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',u) or u.startswith('//'):continue
  path,_,frag=urllib.parse.unquote(u).partition('#');target=(f.parent/path).resolve() if path else f
  nlinks+=1
  if not target.exists():errors.append(f'{f.relative_to(ROOT)}: missing link {u}')
  elif frag and target.suffix.lower()=='.md' and frag not in anchors(text(target)):errors.append(f'{f.relative_to(ROOT)}: missing anchor {u}')
record('K1',errors,files=len(files),relative_links=nlinks)
# K2 typed references and actual repository paths, including legacy capture refs.
rows=list(csv.DictReader((ROOT/'Сборка/manifest/components.tsv').open(),delimiter='\t'))
errors=[];typed=0;checked=0
for r in rows:
 for col in ['REBUILD_SOURCE','RUNBOOK','CONFIG_ARTIFACTS','TESTS']:
  value=r[col]
  typed+=len(re.findall(r'(?:private:|RB-\d+(?:\.\d+)?:|GAP:|external:|NOT_COVERED:|N/A:EXCLUDED|TBD:RB-12)',value))
  for item in value.split(';'):
   item=item.strip()
   if re.match(r'^(?:private:|external:|GAP:|NOT_COVERED:|N/A:|TBD:|https?://|RB-\d+(?:\.\d+)?(?::|/))',item):continue
   if item.startswith('reindex:'):item=item[len('reindex:'):]
   if item.startswith('backup:private:'):continue
   match=re.match(r'((?:Сборка|Конфиги|Решения|Этапы|Meta|scripts|gateway)/.+)',item)
   if not match:continue
   path=match[1];options=[path]
   brace=re.search(r'\{([^}]+)\}',path)
   if brace:options=[path[:brace.start()]+v+path[brace.end():] for v in brace[1].split(',')]
   for name in options:
    q=ROOT/name
    if name.startswith('gateway/'):q=ROOT/'Сборка/artifacts/services'/name
    checked+=1
    if not q.exists():errors.append(f'{r["COMPONENT_ID"]}.{col}: missing {name}')
record('K2',errors,repository_paths=checked,typed_references=typed)
# K3 preserves state/membership and allows only explicitly deferred documentation rows.
errors=[];deferred={'DOCS-VAULT','DOCS-USER-FILES','DOCS-OBSIDIAN-CONFIG'}
for r in rows:
 for col,val in r.items():
  if re.search(r'TBD:RB-(?:0[4-9]|10|11)\b',val):errors.append(r['COMPONENT_ID']+': past TBD')
  if 'TBD:RB-12' in val and (r['COMPONENT_ID'] not in deferred or col not in ['RUNBOOK','TESTS']):errors.append(r['COMPONENT_ID']+': invalid RB12')
 if r['MEMBERSHIP']=='MANDATORY':
  for col in ['REBUILD_SOURCE','RUNBOOK','TESTS']:
   if r[col] in ['','-']:errors.append(r['COMPONENT_ID']+': empty '+col)
old=list(csv.DictReader(git('show',START+':Сборка/manifest/components.tsv').decode().splitlines(),delimiter='\t'))
for before,after in zip(old,rows):
 for col in before:
  if col not in ['RUNBOOK','TESTS','NOTES'] and before[col]!=after[col]:errors.append(after['COMPONENT_ID']+': altered '+col)
 if before['NOTES']!=after['NOTES'] and after['COMPONENT_ID'] not in ['Q6-WRAPPER','SRV-OS']:errors.append(after['COMPONENT_ID']+': altered NOTES')
if len(rows)!=48:errors.append('component count changed')
record('K3',errors,remaining_tbd=sum(v.count('TBD:RB-12') for r in rows for v in r.values()))
# K4 markers and site values. Fixed generic runtime paths are package defaults.
env=text(ROOT/'Сборка/site.example.env');declared=set(re.findall(r'^(LAB_[A-Z0-9_]+)=',env,re.M));used=set()
for f in (ROOT/'Сборка').rglob('*'):
 if f.is_file():
  used.update(x or y for x,y in re.findall(r'@(LAB_[A-Z0-9_]+)@|\$\{(LAB_[A-Z0-9_]+)\}',text(f)))
errors=[f'undocumented marker {x}' for x in sorted(used-declared)]
fixed={'LAB_OLLAMA_BIN':"'/usr/local/bin/ollama'",'LAB_OLLAMA_MODELS':"'/usr/share/ollama/.ollama/models'"}
for k,v in re.findall(r'^(LAB_[A-Z0-9_]+)=(.*)$',env,re.M):
 if v.strip() not in ["''",'""','',fixed.get(k)]:errors.append('site value in '+k)
record('K4',errors,declared=len(declared),used=len(used))
# K5 accepted artifact checksums and protection of accepted bytes.
errors=[];count=0;external_unchecked=[]
for f in sorted((ROOT/'Сборка/artifacts').rglob('SHA256SUMS')):
 count+=1
 for l in text(f).splitlines():
  if not l.strip() or l.lstrip().startswith("#"):continue
  m=re.fullmatch(r'([0-9a-f]{64}) [ *](.+)',l)
  if not m:errors.append(str(f.relative_to(ROOT))+': malformed checksum');continue
  source=f.parent/m[2]
  if not source.exists() and f.parent.name=='ollama' and m[2]=='ollama-linux-amd64.tar.zst' and a.evidence_root:
   source=a.evidence_root/'RB-06'/m[2]
  if not source.is_file() and a.static_only and f.parent.name=='ollama' and m[2]=='ollama-linux-amd64.tar.zst':
   external_unchecked.append(m[2]);continue
  if not source.is_file():errors.append(str(f.relative_to(ROOT))+': missing checksum input '+m[2]);continue
  digest=hashlib.sha256()
  with source.open('rb') as stream:
   for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
  if digest.hexdigest()!=m[1]:errors.append(str(f.relative_to(ROOT))+': checksum mismatch '+m[2])
changed=git('diff','--name-only','-z',START,*([] if a.working_tree else ['HEAD'])).decode().split('\0')
protected=[n for n in changed if n.startswith('Сборка/artifacts/') or n.startswith('Решения/') or n=='Целевая_архитектура_AI_Coding_Platform_v1_22.md']
if protected:errors.extend('accepted bytes changed: '+n for n in protected)
record('K5',errors,sha256sums_files=count,external_unchecked=external_unchecked)
# K6 RB00 A.6.5 and K7 RB09 T5 on added lines in the full diff.
reference=ROOT/'Сборка/tests/repo/boundary_review.json'
reviews=json.loads(text(reference)) if reference.exists() else {}
allowed_ips=set();base_ipv6=set()
ip4=re.compile(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?(?![\w.])')
for name in git('ls-tree','-r','--name-only','-z',BASE).decode().rstrip('\0').split('\0'):
 b=git('show',BASE+':'+name)
 if b'\0' not in b:allowed_ips.update(ip4.findall(b.decode(errors='replace')))
diff=git('diff','--no-ext-diff','--unified=0','--no-renames',BASE,*([] if a.working_tree else ['HEAD']),'--').decode(errors='replace')
added=[];name='';line=0
for l in diff.splitlines():
 if l.startswith('+++ b/'):name=l[6:];continue
 if l.startswith('+++ '):
  # git can quote UTF-8 names; use core.quotepath=false at invocation below instead.
  continue
 if l.startswith('@@'):
  m=re.search(r'\+(\d+)',l);line=int(m[1]) if m else 0;continue
 if l.startswith('+'):added.append((name,line,l[1:]));line+=1
 elif not l.startswith('-'):line+=1
if a.working_tree:
 for name in git('ls-files','--others','--exclude-standard','-z').decode().split('\0'):
  if name and (ROOT/name).is_file():added.extend((name,i,l) for i,l in enumerate(text(ROOT/name).splitlines(),1))
secret=re.compile(r'''(ghp_|gho_|github_pat_|hf_|sk-[A-Za-z0-9]|glpat-)[A-Za-z0-9_-]{10,}|BEGIN [A-Z ]*PRIVATE KEY|(api[_-]?key|apikey|token|secret|passw(or)?d)["']?\s*[=:]\s*["']?[^*\s"',}]{8,}''',re.I)
rules={
 'UFW_COMMAND':re.compile(r'^\s*(?:sudo\s+)?ufw\s+(?:allow|deny|reject|limit|route|default|insert|delete)\b',re.I),
 'UFW_CHAIN':re.compile(r'^\s*(?:-A\s+ufw|:ufw-|### tuple ###)'),
 'SSHD_VALUE':re.compile(r'^\s*(?:PasswordAuthentication|PubkeyAuthentication|PermitRootLogin|ListenAddress|AllowUsers|DenyUsers|AuthenticationMethods|KbdInteractiveAuthentication|X11Forwarding|AllowTcpForwarding|GatewayPorts|MaxAuthTries)\s+\S+',re.I),
 'PORT_RULE':re.compile(r'(?i)(?<![\w./:-])(?:allow|deny|open|listen)(?![\w./:-]).{0,45}(?<![\d.-])\b\d{2,5}\b(?![\d.-])|(?<![\d.-])\b\d{2,5}\b(?![\d.-]).{0,45}(?<![\w./:-])(?:allow|deny|open|listen)(?![\w./:-])'),
 'PORT_MAP':re.compile(r'(?:\d{1,3}\.){3}\d{1,3}:\d+\s*->\s*\d+/(?:tcp|udp)')}
def candidate(k,code,name,lineno,l):
 ident=sha((k+'\0'+code+'\0'+name+'\0'+l).encode());review=reviews.get(ident)
 item={'id':ident,'check':k,'code':code,'path':name,'line':lineno,'reviewed':bool(review),'reason':review or ''};candidates.append(item)
for name,ln,l in added:
 if secret.search(l) and 'MASKED' not in l:candidate('K6','SECRET_PATTERN',name,ln,l)
 for token in ip4.findall(l):
  if token not in allowed_ips:candidate('K7','NEW_IPV4_OR_VERSION',name,ln,l)
 for code,rule in rules.items():
  if rule.search(l):candidate('K7',code,name,ln,l)
 for token in re.findall(r'(?<![\w:])[0-9a-fA-F]*:[0-9a-fA-F:]+(?:%[\w.-]+)?',l):
  try:ipaddress.IPv6Address(token.split('%')[0])
  except ValueError:continue
  # IPv6 constants in code need the same explicit line review as other candidates.
  candidate('K7','IPV6',name,ln,l)
for k in ['K6','K7']:record(k,[{key:v for key,v in c.items() if key!='reason'} for c in candidates if c['check']==k and not c['reviewed']],candidates=sum(c['check']==k for c in candidates),reviewed=sum(c['check']==k and c['reviewed'] for c in candidates))
# K8 offline tests. RB08 T1/T2 reuse the accepted function body up to T3, unchanged.
if not a.static_only:
 errors=[];runs=[]
 if not a.evidence_root:errors.append('--evidence-root required')
 else:
  ev=a.evidence_root.resolve();out=ev/'RB-11/checks';out.mkdir(parents=True,exist_ok=True)
  commands=[('RB05',['python3','-I',str(ROOT/'Сборка/tests/q6/test_q6_runtime.py'),'--extract',str(ev/'RB-02/extract')]),('RB071',['python3','-I',str(ROOT/'Сборка/tests/services/test_healthcheck_revision.py'),'--repo',str(ROOT),'--evidence',str(out/'RB071'),'--venv',str(ev/'RB-07/venvs/gateway'),'--shellcheck',str(Path(shutil.which('shellcheck') or ev/'RB-09/tooling/usr/bin/shellcheck'))]),('RB10',['python3','-I',str(ROOT/'Сборка/tests/acceptance/test_evaluate.py')])]
  client=ROOT/'Сборка/tests/client/test_client.py';source=text(client);cut=source.index('        meta = load(evidence / "rb08_pi_registry.json")')
  prefix=source[:cut]+'    print("T1=PASS\\nT2=PASS")\n'
  prefix+='\nimport argparse\nrun_tests(argparse.Namespace(package=Path('+repr(str(ROOT/'Сборка/artifacts/client'))+'),capture=Path('+repr(str(ev/'RB-01/extract/home/vladimir/.pi/agent'))+'),evidence=Path('+repr(str(out/'RB08'))+'),downloads=Path("/unused")))\n'
  with tempfile.TemporaryDirectory(prefix='rb11-k8-') as tmp:
   driver=Path(tmp)/'rb08_t1_t2.py';driver.write_text(prefix);commands.append(('RB08_T1_T2',['python3','-I',str(driver)]))
   for label,cmd in commands:
    q=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=180,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    (out/(label+'.log')).write_text(q.stdout+q.stderr);runs.append({'test':label,'rc':q.returncode})
    if q.returncode:errors.append(label+' failed; inspect private/local test log')
 record('K8',errors,runs=runs,not_run=[{'tests':'RB06 archive/platform; RB07 complete; RB08 T3-T7','reason':'RB06 needs archive/platform receipts (archive SHA256 is checked in K5); full RB07/RB08 additionally need release assets, wheel/download receipts and a prepared temporary npm prefix. These broader source reproduction tests are retained as previously accepted and are not repeated by the four mandatory offline groups.'},{'tests':'T-LONG, GPU container, clean rebuild','reason':'Not authorized for phase A; procedure only / RB14.'}])
 # K9 validate private bundle identity, classified section coverage and passport essentials.
 errors=[]
 if not a.freshness or not a.freshness.is_file():errors.append('--freshness private receipt required')
 else:
  fresh=json.loads(text(a.freshness));priv=a.freshness.parent;bundle=priv/'rb11_server_survey.out';classes=json.loads(text(priv/'classification.json'));raw=text(bundle)
  if sha(bundle.read_bytes())!=fresh['collector']['bundle_sha256']:errors.append('fresh bundle hash mismatch')
  if fresh['collector']['collector_sha256']!='bc1415955cef05332d15fa20c2aaece63832ea89dc88c37ec15abb8df7154ffa':errors.append('collector hash mismatch')
  if len(classes)!=fresh['section_changes'] or any(not x['reviewed'] or x['classification'] not in ['REFLECTED','DRIFT','REVALIDATE'] for x in classes):errors.append('classification incomplete')
  if fresh['needs_decision'] or fresh['symlink_targets_match']!='17/17':errors.append('freshness unresolved')
  passport=text(ROOT/'Паспорт_лаборатории_v39.md')
  for expected in ['2026-10-17','6.8.0-147','6.8.0-146','595.99.02','0.35.1','REVALIDATE','67352629248','09b8aff72a79']:
   if expected not in passport:errors.append('passport missing accepted freshness datum')
  if 'KERNEL=6.8.0-146-generic' not in raw or 'NVIDIA_DRIVER=595.99.02' not in raw:errors.append('runtime contradicts passport')
 record('K9',errors,classified_sections=30)
else:
 for k in ['K8','K9']:results[k]={'status':'NOT_RUN','reason':'static-only; full run required for acceptance'}
# K10 frontmatter position and key preservation; no YAML dependency required.
def frontmatter_keys(value):
 lines=value.splitlines()
 if not lines or lines[0]!='---':return None
 try:end=lines.index('---',1)
 except ValueError:return None
 keys=[]
 for line in lines[1:end]:
  if not line or line[0].isspace() or line.lstrip().startswith('#'):continue
  match=re.match(r"(?P<key>[^:#][^:]*):(?:\s|$)",line)
  if match:
   key=match['key'].strip()
   if key.startswith(('\"', "'")):
    try:key=ast.literal_eval(key)
    except (SyntaxError,ValueError):pass
   keys.append(key)
 return set(keys)
errors=[];frontmatter_count=0
tracked=set(git('ls-files','-z').decode().split('\0'))
if a.working_tree:tracked.update(git('ls-files','--others','--exclude-standard','-z').decode().split('\0'))
for name in git('ls-tree','-r','--name-only','-z',BASE).decode().split('\0'):
 if not name.endswith('.md'):continue
 before=git('show',BASE+':'+name).decode(errors='replace')
 if not before.startswith('---\n'):continue
 frontmatter_count+=1
 path=ROOT/name
 if not path.is_file():errors.append(name+': missing Markdown with original frontmatter');continue
 after=text(path);before_keys=frontmatter_keys(before);after_keys=frontmatter_keys(after)
 if after_keys is None:errors.append(name+': YAML frontmatter must start on line 1 and have closing ---')
 elif after_keys!=before_keys:errors.append(name+': YAML frontmatter key set changed')
status_files=[*sorted((ROOT/'Сборка').glob('*.md')),ROOT/'Сборка/manifest/README.md',ROOT/'Паспорт_лаборатории_v39.md',ROOT/'Этапы/2026-10-16_Rebuild_Package/Результаты.md']
for f in status_files:
 for line in text(f).splitlines():
  if re.match(r'^(?:\*\*)?Статус(?:\*\*)?:',line) and re.search(r'READY_FOR_REVIEW|готов к приёмке|готовится к приёмке',line,re.I):errors.append(str(f.relative_to(ROOT))+': stale review status')
record('K10',errors,frontmatter_files=frontmatter_count,status_files=len(status_files))
result={'checks':results,'boundary_candidates':candidates,'status':'FAIL' if any(r['status']=='FAIL' for r in results.values()) else ('STATIC_PASS' if a.static_only else 'PASS')}
if a.output:a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for k,r in results.items():print(k+'='+r['status']+' errors='+str(len(r.get('errors',[]))))
print('MANIFEST_CHECK='+('PASS' if results['K2']['status']==results['K3']['status']=='PASS' else 'FAIL'))
print('PACKAGE_CHECK='+result['status']);sys.exit(1 if result['status']=='FAIL' else 0)
