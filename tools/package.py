#!/usr/bin/env python3
"""Package editable source, verification and ready-built dist without caches/secrets."""
from pathlib import Path
import argparse,hashlib,zipfile,json
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT.parent/'Alexandra-Mislin-Portable-Website-2026-10-30.zip');args=p.parse_args();target=args.output.resolve()
files=[]
for f in ROOT.rglob('*'):
 if not f.is_file():continue
 rel=f.relative_to(ROOT)
 if any(x in ('.git','__pycache__','.pytest_cache','node_modules','.local-editor') for x in rel.parts):continue
 if f.name.startswith('.env') or f.name=='.DS_Store' or f.suffix in ('.pyc','.zip','.log') or f.name=='FILE-CHECKSUMS.sha256':continue
 files.append(f)
checks=''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+str(f.relative_to(ROOT))+'\n' for f in sorted(files));(ROOT/'FILE-CHECKSUMS.sha256').write_text(checks);files.append(ROOT/'FILE-CHECKSUMS.sha256');target.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for f in sorted(files):z.write(f,Path(ROOT.name)/f.relative_to(ROOT))
with zipfile.ZipFile(target) as z:assert z.testzip() is None;assert len(z.namelist())==len(set(z.namelist()))
size=target.stat().st_size
if size>=20_000_000:raise SystemExit('Archive exceeds 20MB; split the review screenshots before delivery.')
report={'path':str(target),'bytes':size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'files':len(files),'under_20MB':True};target.with_suffix('.zip.sha256').write_text(report['sha256']+'  '+target.name+'\n');print(json.dumps(report,indent=2))
