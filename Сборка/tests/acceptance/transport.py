"""SSH stdin transport, no remote files, no credentials in receipts."""
import pexpect

def ssh_script(target,script,credential,timeout=120,with_sudo=False):
    child=pexpect.spawn('ssh',['-T','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no','-o','ConnectTimeout=15',target,'bash -s'],encoding=None,echo=False,timeout=timeout)
    state=child.expect([rb'(?i)password:',pexpect.EOF,pexpect.TIMEOUT])
    if state!=0:
        child.close(force=True)
        raise RuntimeError('SSH authentication unavailable; diagnostic suppressed')
    child.sendline(credential.encode())
    payload='set +x\n'
    if with_sudo:payload+='IFS= read -r RB10_CREDENTIAL\n'+credential+'\nexport RB10_CREDENTIAL\n'
    payload+=script+'\n'
    child.send(payload.encode());child.sendeof()
    try:child.expect(pexpect.EOF,timeout=timeout)
    except pexpect.TIMEOUT:
        child.close(force=True)
        raise TimeoutError('SSH command deadline exceeded; no service restart attempted')
    raw=child.before.replace(b'\r\n',b'\n');child.close()
    if credential.encode() in raw:raise RuntimeError('Credential candidate in output; receipt rejected')
    return {'rc':child.exitstatus,'stdout':raw.decode(errors='replace')}
