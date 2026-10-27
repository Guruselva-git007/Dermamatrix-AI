"""Bounded tracked-source hygiene check; never prints suspected secret values."""
from pathlib import Path
import re
import subprocess

if __name__=='__main__':
    root=Path(__file__).resolve().parents[3]
    names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    findings=[]
    for name in filter(None,names):
        path=root/name
        if not path.is_file():continue
        if path.name=='.env' or path.suffix in {'.pem','.key','.p12'}:findings.append(name);continue
        if path.stat().st_size>2_000_000:continue
        try:text=path.read_text()
        except UnicodeError:continue
        # Split literals so this checker does not flag its own implementation.
        patterns=[r'-----BEGIN '+r'(?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'sk-'+r'proj-[A-Za-z0-9_-]{32,}']
        if any(re.search(pattern,text) for pattern in patterns):findings.append(name)
    print('Tracked-source hygiene: '+('PASS' if not findings else 'FAIL: '+', '.join(findings)))
    raise SystemExit(bool(findings))
