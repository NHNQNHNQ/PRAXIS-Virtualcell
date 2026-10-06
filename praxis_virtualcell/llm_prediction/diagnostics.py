"""Public rejected answers and safe field diagnostics, without private reasoning."""
from __future__ import annotations

import json
import math
import re
from typing import Any

from pydantic import ValidationError

PRIVATE_FIELDS = {
    "reasoning_content", "reasoning", "thinking", "analysis", "chain_of_thought",
    "api_key", "authorization", "password", "secret", "access_token",
}


def _strip_thoughts(text: str) -> str:
    text = re.sub(r"<(think|analysis)>.*?</\1>", "", text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"<(?:think|analysis)>.*$", "", text, flags=re.IGNORECASE | re.DOTALL)


def _public_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _public_value(child) for key, child in value.items()
                if key.lower() not in PRIVATE_FIELDS}
    if isinstance(value, list):
        return [_public_value(child) for child in value]
    if isinstance(value, str):
        return _strip_thoughts(value)
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def schema_diagnostics(error: ValidationError) -> list[dict]:
    return [{"location": list(item["loc"]), "code": item["type"], "message": item["msg"]}
            for item in error.errors(include_url=False, include_context=False, include_input=False)]


def rejected_draft(
    content: Any, *, schema_errors: list[dict] | None = None, evidence_errors: list[dict] | None = None,
) -> dict[str, Any]:
    public = _strip_thoughts(content) if isinstance(content, str) else None
    parsed = None
    if public is not None:
        parse_text = public.strip()
        if parse_text.startswith("```json\n") and parse_text.endswith("```"):
            parse_text = parse_text[8:-3].strip()
        try:
            raw = json.loads(parse_text)
            parsed = _public_value(raw)
            # Re-encode so even unexpected private fields in a public JSON
            # answer cannot be copied into the diagnostic draft.
            public = json.dumps(parsed, ensure_ascii=False, allow_nan=False)
        except (ValueError, TypeError):
            # Malformed JSON cannot be recursively scrubbed reliably. Keep
            # ordinary public text, but omit ambiguous private-field payloads.
            private_keys = "|".join(re.escape(key) for key in PRIVATE_FIELDS)
            if re.search(rf'"(?:{private_keys})"\s*:', public, flags=re.IGNORECASE):
                public = None
    return {
        "is_prediction": False, "public_answer": public, "parsed_draft": parsed,
        "schema_errors": schema_errors or [], "evidence_errors": evidence_errors or [],
    }
