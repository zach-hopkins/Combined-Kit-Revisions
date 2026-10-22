"""Run WeiDU syntax checks on every generated CKR action and the final installer."""
import argparse,json,subprocess
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('weidu',type=Path)
parser.add_argument('--package',type=Path,default=Path('build/package'))
args=parser.parse_args();root=args.package.resolve();exe=args.weidu.resolve()
files=[root/'combined-kit-revisions/combined-kit-revisions.tp2']
files+=list((root/'combined-kit-revisions/generated').glob('*.tpa'))
files+=list((root/'combined-kit-revisions/lib').glob('*.tpa'))
failures=[]
for f in files:
    p=subprocess.run([str(exe),'--nogame','--no-exit-pause','--noautoupdate','--parse-check',
                      'TP2' if f.suffix.lower()=='.tp2' else 'TPA',str(f)],
                     cwd=root,capture_output=True,input=b'',timeout=30)
    if p.returncode:failures.append({'file':f.name,'output':(p.stdout+p.stderr).decode(errors='replace')[-3000:]})
print(json.dumps({'files':len(files),'failures':failures},indent=2))
raise SystemExit(bool(failures))
