"""Cached ChEMBL-only acquisition retaining version, attribution and provenance."""
import hashlib
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
_lock=threading.Lock()
_hosts={}

def get(url, name, source, version=None, license='unverified', data_root=Path('data')):
    RAW = Path(data_root) / 'raw'
    path = RAW / source / name
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    event = dict(url=url, source=source, path=str(path), version=version,
                 license=license, retrieved_at=datetime.now(timezone.utc).isoformat())
    for attempt in range(3):
        try:
            host = urllib.parse.urlsplit(url).netloc
            with _lock:
                time.sleep(max(0, _hosts.get(host,0) + 1 - time.monotonic()))
                _hosts[host] = time.monotonic()
            req = urllib.request.Request(url,headers={'User-Agent':'abwm-public-research/0.1'})
            with urllib.request.urlopen(req, timeout=50) as r:
                if int(r.headers.get('Content-Length',0)) > 1024**3:
                    raise ValueError('single-file quota')
                data = r.read(1024**3+1)
                if len(data)>1024**3: raise ValueError('single-file quota')
                if sum(p.stat().st_size for p in RAW.rglob('*') if p.is_file())+len(data)>10*1024**3:
                    raise ValueError('total quota')
                event['final_url'] = r.url
            if name.endswith(('.csv','.tsv','.json','.gz','.xlsx','.pdf','.zip')) and data.lstrip().lower().startswith((b'<!doctype html',b'<html')):
                raise ValueError('HTML challenge/error page is not numerical data')
            if data.startswith(b'version https://git-lfs.github.com/spec'):
                raise ValueError('Git LFS pointer, not data')
            path.write_bytes(data)
            path.chmod(0o444)
            event.update(status='obtained',bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
            break
        except Exception as e:
            event.update(status='failed',error=f'{type(e).__name__}: {e}')
            if isinstance(e,urllib.error.HTTPError) and e.code in [401,403]: break
            if attempt < 2:
                retry = e.headers.get('Retry-After') if isinstance(e,urllib.error.HTTPError) else None
                if retry and retry.isdigit() and int(retry)>60: break
                time.sleep(int(retry) if retry and retry.isdigit() else 2**attempt)
    with _lock:
        with (RAW/'manifest.jsonl').open('a') as f: f.write(json.dumps(event,ensure_ascii=False)+'\n')
    print(source,name,event['status'],event.get('bytes',event.get('error')),flush=True)
    return path if event['status']=='obtained' else None


def chembl(data_root):
    s=get('https://www.ebi.ac.uk/chembl/api/data/status.json','status.json','chembl_mic',license='CC BY-SA 3.0',data_root=data_root)
    version=json.loads(s.read_text())['chembl_db_version'] if s else None
    # Species target is an explicit first cohort; no claim of exhaustive recall.
    url='https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL614425&standard_type=MIC&limit=1000'
    i=0
    while url:
        p=get(url,f'activities_{i:03d}.json','chembl_mic',version,'CC BY-SA 3.0',data_root=data_root)
        if not p: break
        obj=json.loads(p.read_text())
        print('ChEMBL page',i,'total',obj['page_meta']['total_count'],flush=True)
        url=obj['page_meta']['next']
        if url: url=urllib.parse.urljoin('https://www.ebi.ac.uk',url)
        i+=1
