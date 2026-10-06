"""Verify the author's complete downloads without executing model pickle files."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--generator-root", type=Path, required=True)
    base = parser.parse_args().generator_root.resolve()
    metadata = json.loads((base / "archives/zenodo-record.json").read_text())
    expected_commit = "7444ee4762244cf53d316822609e288505c51457"
    commit = subprocess.check_output(
        ["git", "-C", str(base / "code"), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != expected_commit:
        raise ValueError(f"Unexpected source commit: {commit}")
    verified = []
    for item in metadata["files"]:
        path = base / "archives" / item["key"]
        if path.stat().st_size != item["size"]:
            raise ValueError(f"Incomplete file: {path}")
        algorithm, expected = item["checksum"].split(":", 1)
        digest = hashlib.new(algorithm)
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError(f"Checksum mismatch: {path}")
        result = {"file": item["key"], "bytes": item["size"],
                  "checksum": item["checksum"], "matches_author": True}
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                bad_member = archive.testzip()
                if bad_member is not None:
                    raise ValueError(f"Bad ZIP member: {bad_member}")
                names = archive.namelist()
                if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
                    raise ValueError(f"Unsafe ZIP path in {path}")
                result["zip_crc_passed"] = True
                result["archive_members"] = len(names)
                result["pt_or_pkl_members"] = sum(name.endswith((".pt", ".pkl")) for name in names)
        verified.append(result)
        print(f"Verified {item['key']}", flush=True)
    report = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": "SyntheMol-MCTS", "tag": "v_1.0.3", "source_commit": commit,
        "doi": metadata["doi"], "code_license": "MIT",
        "asset_license": metadata["metadata"]["license"]["id"],
        "files": verified, "download_complete": True,
        "runtime_tested": False, "integrated_with_v1": False,
        "note": "Integrity verified only; not an installation, generation, or efficacy test.",
    }
    (base / "download_verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
