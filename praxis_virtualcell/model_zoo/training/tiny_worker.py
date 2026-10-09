"""Fixed, data-only Phase 20 contract trainer.

This file is executed by :mod:`pipeline` in isolated Python.  It accepts one
canonical JSON document on stdin and emits one canonical JSON checkpoint on
stdout.  It never imports uploaded code or touches Pack paths.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _canonical(value) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _number(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def train(payload: dict) -> dict:
    if type(payload) is not dict or set(payload) != {
        "schema_version",
        "job_fingerprint",
        "seed",
        "hyperparameters",
        "samples",
    }:
        raise ValueError("invalid tiny trainer input fields")
    if payload["schema_version"] != "vc.tiny-trainer-input.v1":
        raise ValueError("invalid tiny trainer input schema")
    if (
        type(payload["job_fingerprint"]) is not str
        or len(payload["job_fingerprint"]) != 64
        or any(char not in "0123456789abcdef" for char in payload["job_fingerprint"])
    ):
        raise ValueError("invalid job fingerprint")
    if type(payload["seed"]) is not int or payload["seed"] < 0:
        raise ValueError("seed must be a non-negative integer")
    if type(payload["hyperparameters"]) is not list:
        raise ValueError("hyperparameters must be an array")
    samples = payload["samples"]
    if type(samples) is not list or not samples:
        raise ValueError("samples must be a non-empty array")

    sample_ids: list[str] = []
    rows: list[tuple[list[float], list[float]]] = []
    for index, sample in enumerate(samples):
        if type(sample) is not dict or set(sample) != {"sample_id", "features", "labels"}:
            raise ValueError("invalid tiny trainer sample fields")
        sample_id = sample["sample_id"]
        if type(sample_id) is not str or not sample_id or sample_id.strip() != sample_id:
            raise ValueError("sample_id must be canonical text")
        if sample_id in sample_ids:
            raise ValueError("sample ids must be unique")
        features = sample["features"]
        labels = sample["labels"]
        if type(features) is not list or not features or type(labels) is not list or not labels:
            raise ValueError("features and labels must be non-empty arrays")
        sample_ids.append(sample_id)
        rows.append(
            (
                [_number(value, f"samples[{index}].features") for value in features],
                [_number(value, f"samples[{index}].labels") for value in labels],
            )
        )
    feature_count = len(rows[0][0])
    label_count = len(rows[0][1])
    if any(len(features) != feature_count or len(labels) != label_count for features, labels in rows):
        raise ValueError("tiny trainer rows must have fixed dimensions")

    # Contract-only deterministic summary, deliberately not a scientific model.
    feature_means = [math.fsum(row[0][column] for row in rows) / len(rows) for column in range(feature_count)]
    label_means = [math.fsum(row[1][column] for row in rows) / len(rows) for column in range(label_count)]
    return {
        "schema_version": "vc.tiny-json-checkpoint.v1",
        "job_fingerprint": payload["job_fingerprint"],
        "seed": payload["seed"],
        "sample_ids_sha256": hashlib.sha256(_canonical(sample_ids)).hexdigest(),
        "sample_count": len(rows),
        "feature_count": feature_count,
        "label_count": label_count,
        "feature_means": feature_means,
        "label_means": label_means,
        "contract_only": True,
    }


def main() -> int:
    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw, object_pairs_hook=_object)
        checkpoint = train(payload)
        sys.stdout.buffer.write(_canonical(checkpoint) + b"\n")
        return 0
    except (ArithmeticError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        # No input fragments, environment, or paths are reflected to stderr.
        sys.stderr.write("tiny trainer rejected input\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
