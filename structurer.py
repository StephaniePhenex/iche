"""
structurer.py — Parse and validate agent outputs.

Extracts [Analysis] and [Structured Output] sections from raw model text.
Validates JSON schema. Falls back to LLM repair if JSON is malformed.
"""

import re
import json
from typing import Optional
from models import call_model

# ── Required keys in structured output ───────────────────────────────────────

REQUIRED_KEYS = {"solution", "assumptions", "tradeoffs", "risks", "failure_cases", "confidence"}

EXPECTED_TYPES = {
    "solution": str,
    "assumptions": list,
    "tradeoffs": list,
    "risks": list,
    "failure_cases": list,
    "confidence": (int, float),
}


# ── Extraction ────────────────────────────────────────────────────────────────

def extract_sections(raw: str) -> tuple[str, str]:
    """Return (analysis_text, structured_json_str)."""
    analysis = ""
    structured = ""

    analysis_match = re.search(
        r"\[Analysis\](.*?)(?=\[Structured Output\]|$)",
        raw,
        re.DOTALL | re.IGNORECASE,
    )
    if analysis_match:
        analysis = analysis_match.group(1).strip()

    structured_match = re.search(
        r"\[Structured Output\].*?JSON ONLY:\s*(\{.*\})",
        raw,
        re.DOTALL | re.IGNORECASE,
    )
    if not structured_match:
        # Fallback: grab last JSON object in the text
        all_json = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}", raw, re.DOTALL)
        if all_json:
            structured = all_json[-1]
    else:
        structured = structured_match.group(1).strip()

    return analysis, structured


def _parse_json(text: str) -> Optional[dict]:
    """Attempt JSON parse with minor cleanup."""
    text = text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _validate_schema(data: dict) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors = []
    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"Missing key: '{key}'")
            continue
        expected = EXPECTED_TYPES[key]
        if not isinstance(data[key], expected):
            errors.append(
                f"Key '{key}' expected {expected}, got {type(data[key]).__name__}"
            )
    if "confidence" in data:
        c = data["confidence"]
        if isinstance(c, (int, float)) and not (0.0 <= c <= 1.0):
            errors.append(f"Confidence {c} out of range [0.0, 1.0]")
    return errors


def _repair_with_llm(raw_output: str) -> Optional[dict]:
    """Ask a model to extract and fix the JSON from a malformed output."""
    repair_prompt = (
        "The following text is a model response that should contain a JSON object "
        "with these exact keys: solution (str), assumptions (list), tradeoffs (list), "
        "risks (list), failure_cases (list), confidence (float 0-1).\n\n"
        "Extract and return ONLY the valid JSON object. Nothing else.\n\n"
        f"Text:\n{raw_output[:3000]}"
    )
    try:
        repaired = call_model("mock", repair_prompt)
        _, structured_str = extract_sections(repaired)
        if not structured_str:
            structured_str = repaired
        return _parse_json(structured_str)
    except Exception:
        return None


def _apply_defaults(data: dict) -> dict:
    """Fill missing optional fields with safe defaults."""
    defaults = {
        "assumptions": [],
        "tradeoffs": [],
        "risks": [],
        "failure_cases": [],
        "confidence": 0.5,
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    if "confidence" in data:
        data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
    return data


# ── Public interface ──────────────────────────────────────────────────────────

def structure_output(raw: str, agent_role: str) -> dict:
    """
    Parse raw agent output into a validated structured dict.

    Returns a dict with keys: analysis, solution, assumptions, tradeoffs,
    risks, failure_cases, confidence, _parse_errors.
    """
    analysis, structured_str = extract_sections(raw)

    parsed = _parse_json(structured_str) if structured_str else None

    if parsed is None:
        parsed = _repair_with_llm(raw)

    if parsed is None:
        # Hard fallback: minimal valid structure
        parsed = {
            "solution": raw[:300] if raw else "Unable to parse solution",
            "assumptions": [],
            "tradeoffs": [],
            "risks": ["Output parsing failed"],
            "failure_cases": [],
            "confidence": 0.3,
        }

    parsed = _apply_defaults(parsed)
    errors = _validate_schema(parsed)

    return {
        "agent": agent_role,
        "analysis": analysis,
        **{k: parsed.get(k) for k in REQUIRED_KEYS},
        "_parse_errors": errors,
    }
