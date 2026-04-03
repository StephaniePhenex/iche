"""
structurer.py — Role-specific JSON parsers for agent outputs.

Each parser extracts the relevant fields for its agent role with a safe fallback.
"""

import re
import json


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict | None:
    """Strip markdown fences and parse the first JSON object found."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ── Role-specific parsers ─────────────────────────────────────────────────────

def _tool_used(data: dict, default: list) -> list:
    tools = data.get("tool_used")
    if isinstance(tools, list):
        return [str(t) for t in tools]
    return default


def parse_researcher(raw: str) -> dict:
    data = _extract_json(raw)
    if isinstance(data, dict) and isinstance(data.get("evidence"), list):
        evidence = [
            e for e in data["evidence"]
            if isinstance(e, dict) and "source" in e and "content" in e
        ]
        return {
            "agent": "Researcher",
            "evidence": evidence,
            "tool_used": _tool_used(data, ["DomainKnowledge"]),
        }
    return {
        "agent": "Researcher",
        "evidence": [{"source": "fallback", "content": raw[:800]}],
        "tool_used": [],
    }


def parse_planner(raw: str) -> dict:
    data = _extract_json(raw)
    if isinstance(data, dict):
        plan = [
            s for s in (data.get("proposed_plan") or [])
            if isinstance(s, dict) and "step" in s and "description" in s
        ]
        return {
            "agent": "Planner+Synthesizer",
            "proposed_plan": plan,
            "final_choice": str(data.get("final_choice") or "").strip(),
            "reasoning": str(data.get("reasoning") or "").strip(),
            "tool_used": _tool_used(data, ["Reasoning"]),
        }
    return {
        "agent": "Planner+Synthesizer",
        "proposed_plan": [],
        "final_choice": raw[:800].strip(),
        "reasoning": "",
        "tool_used": [],
    }


def parse_critic(raw: str) -> dict:
    data = _extract_json(raw)
    if isinstance(data, dict):
        conflicts = [c for c in (data.get("conflicts") or []) if isinstance(c, dict)]
        return {
            "agent": "Critic",
            "conflicts": conflicts,
            "resolved": list(data.get("resolved") or []),
            "unresolved": list(data.get("unresolved") or []),
            "key_conflicts_prioritized": bool(data.get("key_conflicts_prioritized", True)),
            "tool_used": _tool_used(data, ["ConflictAnalysis"]),
        }
    return {
        "agent": "Critic",
        "conflicts": [],
        "resolved": [],
        "unresolved": [],
        "key_conflicts_prioritized": True,
        "tool_used": [],
    }


# ── Legacy shim ───────────────────────────────────────────────────────────────

def structure_output(raw: str, agent_role: str) -> dict:
    """Route to the appropriate role-specific parser."""
    if agent_role == "researcher":
        return parse_researcher(raw)
    if agent_role == "planner_synthesizer":
        return parse_planner(raw)
    if agent_role == "critic":
        return parse_critic(raw)
    parsed = _extract_json(raw)
    return parsed if isinstance(parsed, dict) else {"raw": raw[:500]}
