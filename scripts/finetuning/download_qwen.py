"""Download the pinned official Qwen checkpoint without duplicating its cache."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, wait
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--endpoint', default='https://hf-mirror.com')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    root = args.workspace.resolve()
    official = json.loads((root / 'reports/official_model_metadata.json').read_text())
    if official['id'] != 'Qwen/Qwen3-32B' or not re.fullmatch(r'[0-9a-f]{40}', official['sha']):
        raise ValueError('Unexpected model identity or revision')
    if args.endpoint not in ('https://huggingface.co', 'https://hf-mirror.com'):
        raise ValueError('Unsupported public download endpoint')
    target = root / 'models/Qwen3-32B'
    target.mkdir(parents=True, exist_ok=True)
    metadata_names = {'LICENSE', 'README.md', 'config.json', 'generation_config.json',
                      'merges.txt', 'model.safetensors.index.json', 'tokenizer.json',
                      'tokenizer_config.json', 'vocab.json'}
    files = [row for row in official['siblings'] if row['rfilename'] in metadata_names
             or re.fullmatch(r'model-\d{5}-of-\d{5}\.safetensors', row['rfilename'])]
    if sum(row['rfilename'].endswith('.safetensors') for row in files) != 17:
        raise ValueError('Expected 17 official weight shards')
    report_path = root / 'reports/model_download.json'
    status = {'model_id': official['id'], 'revision': official['sha'],
              'endpoint': args.endpoint, 'status': 'downloading', 'files': []}

    def download(row: dict) -> dict:
        name = row['rfilename']
        path = target / name
        expected = row.get('size')
        if not path.exists() or (expected is not None and path.stat().st_size != expected):
            partial = path.with_name(name + '.part')
            command = ['curl', '--ipv4', '--fail', '--location', '--silent', '--show-error',
                       '--retry', '0', '--connect-timeout', '20',
                       '--speed-limit', '1024', '--speed-time', '120', '--continue-at', '-',
                       '--output', str(partial),
                       f"{args.endpoint}/{official['id']}/resolve/{official['sha']}/{name}"]
            # A fresh curl invocation re-reads the current partial-file offset.
            # curl's internal retry can reset output to its initial offset and
            # discard bytes downloaded during the failed attempt.
            for attempt in range(4):
                if expected is not None and partial.exists() and partial.stat().st_size == expected:
                    break
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode == 0:
                    break
                if attempt == 3:
                    # Signed redirect URLs are not included in terminal output.
                    raise RuntimeError(f'{name}: curl exit {result.returncode}')
                print(json.dumps({'resuming_file': name, 'attempt': attempt + 2,
                                  'partial_bytes': partial.stat().st_size if partial.exists() else 0}), flush=True)
                time.sleep(2)
            if expected is not None and partial.stat().st_size != expected:
                raise ValueError(f'{name}: download size mismatch')
            partial.replace(path)
        record = {'file': name, 'bytes': path.stat().st_size}
        expected_sha = row.get('lfs', {}).get('sha256')
        if expected_sha:
            digest = hashlib.sha256()
            with path.open('rb') as handle:
                for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
                    digest.update(block)
            if digest.hexdigest() != expected_sha:
                raise ValueError(f'{name}: official SHA256 mismatch')
            record.update(sha256=digest.hexdigest(), official_sha256_verified=True)
        elif row.get('blobId'):
            content = path.read_bytes()
            git_digest = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
            if git_digest != row['blobId']:
                raise ValueError(f'{name}: official Git blob mismatch')
            record.update(git_blob_id=git_digest, official_git_blob_verified=True)
        print(json.dumps({'verified_file': name, 'bytes': record['bytes']}, ensure_ascii=False), flush=True)
        return record

    def save() -> None:
        temporary = report_path.with_suffix('.json.part')
        temporary.write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(report_path)

    save()
    # Make the official tokenizer available before the large weight transfers.
    try:
        for row in files:
            if not row['rfilename'].endswith('.safetensors'):
                status['files'].append(download(row))
                save()
        weights = [row for row in files if row['rfilename'].endswith('.safetensors')]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = {pool.submit(download, row) for row in weights}
            while pending:
                finished, pending = wait(pending, timeout=30)
                for future in finished:
                    status['files'].append(future.result())
                status['downloaded_bytes_including_partial'] = sum(
                    p.stat().st_size for p in target.iterdir() if p.is_file())
                save()
                print(json.dumps({'status': 'downloading', 'completed_files': len(status['files']),
                                  'bytes_on_disk': status['downloaded_bytes_including_partial']}), flush=True)
        index = json.loads((target / 'model.safetensors.index.json').read_text())
        if set(index['weight_map'].values()) != {row['rfilename'] for row in weights}:
            raise ValueError('Official weight index does not match downloaded shards')
        status.update(status='complete', verified_weight_shards=17,
                      weight_tensor_bytes=index['metadata']['total_size'],
                      completed_at_unix=int(time.time()))
        save()
    except Exception as exc:
        status.update(status='failed', error=str(exc))
        save()
        raise


if __name__ == '__main__':
    main()
