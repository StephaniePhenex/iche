"""
critic.py — Conflict detection and analysis.

Compares structured outputs from all agents and identifies:
  - Agreements (convergence signals)
  - Conflicts (divergence requiring resolution)
  - Gaps (topics no agent addressed)
"""

import json
from typing import Optional
from models import call_model, is_mock_mode


# ── LLM-based critic ──────────────────────────────────────────────────────────

_CRITIC_SYSTEM = (
    "You are a meta-critic in a multi-agent deliberation system. "
    "Your job is to compare proposals from multiple agents, identify where they agree, "
    "where they conflict, and what important topics are missing. "
    "Be precise and objective. Do not favor any agent."
)

_CRITIC_OUTPUT_FORMAT = """
Return ONLY valid JSON in this exact format:
{
  "agreements": ["point of agreement 1", "point of agreement 2"],
  "conflicts": [
    {
      "topic": "name of the conflicting topic",
      "position_A": "agent_name: their position",
      "position_B": "other_agent_name: their position",
      "required_resolution": "what needs to be decided to resolve this"
    }
  ],
  "gaps": ["topic not addressed 1", "topic not addressed 2"],
  "recommendation": "one-paragraph summary of what agents should focus on to converge"
}
"""


def _build_critic_prompt(structured_outputs: dict[str, dict]) -> str:
    agent_summaries = []
    for role, output in structured_outputs.items():
        summary = (
            f"=== {role} ===\n"
            f"Solution: {output.get('solution', 'N/A')}\n"
            f"Assumptions: {json.dumps(output.get('assumptions', []))}\n"
            f"Tradeoffs: {json.dumps(output.get('tradeoffs', []))}\n"
            f"Risks: {json.dumps(output.get('risks', []))}\n"
            f"Confidence: {output.get('confidence', 0.0)}"
        )
        agent_summaries.append(summary)

    return (
        "Compare the following agent proposals and identify agreements, conflicts, and gaps.\n\n"
        + "\n\n".join(agent_summaries)
        + f"\n\n{_CRITIC_OUTPUT_FORMAT}"
    )


def _parse_critic_response(raw: str) -> dict:
    """Extract JSON from critic response."""
    import re

    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Best-effort: find JSON block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

    return {
        "agreements": data.get("agreements", []),
        "conflicts": data.get("conflicts", []),
        "gaps": data.get("gaps", []),
        "recommendation": data.get("recommendation", ""),
    }


# ── Rule-based fallback critic ────────────────────────────────────────────────

def _rule_based_critic(structured_outputs: dict[str, dict]) -> dict:
    """
    Simple heuristic conflict detection when LLM critic is unavailable.
    Compares solution strings for similarity; flags obvious differences.
    """
    solutions = {role: out.get("solution", "") for role, out in structured_outputs.items()}
    roles = list(solutions.keys())

    conflicts = []
    agreements = []

    # Check for keyword overlap in solutions
    def keywords(text: str) -> set:
        stop = {"a", "an", "the", "and", "or", "with", "for", "to", "is", "in", "of", "on"}
        return {w.lower() for w in text.split() if w.lower() not in stop and len(w) > 3}

    for i in range(len(roles)):
        for j in range(i + 1, len(roles)):
            r1, r2 = roles[i], roles[j]
            kw1 = keywords(solutions[r1])
            kw2 = keywords(solutions[r2])
            overlap = kw1 & kw2
            similarity = len(overlap) / max(len(kw1 | kw2), 1)

            if similarity < 0.3:
                conflicts.append({
                    "topic": f"Solution approach: {r1} vs {r2}",
                    "position_A": f"{r1}: {solutions[r1][:120]}",
                    "position_B": f"{r2}: {solutions[r2][:120]}",
                    "required_resolution": "Agents must align on core architectural approach",
                })
            elif similarity > 0.6:
                agreements.append(f"{r1} and {r2} broadly agree on approach")

    # Check confidence gap
    confidences = {role: out.get("confidence", 0.5) for role, out in structured_outputs.items()}
    max_c = max(confidences.values())
    min_c = min(confidences.values())
    if max_c - min_c > 0.25:
        conflicts.append({
            "topic": "Confidence divergence",
            "position_A": f"High confidence agent: {max(confidences, key=confidences.get)} ({max_c:.2f})",
            "position_B": f"Low confidence agent: {min(confidences, key=confidences.get)} ({min_c:.2f})",
            "required_resolution": "Low-confidence agent should clarify uncertainties",
        })

    return {
        "agreements": agreements,
        "conflicts": conflicts,
        "gaps": ["Rule-based critic: gaps not analyzed"],
        "recommendation": (
            f"Found {len(conflicts)} conflict(s). "
            "Agents should align on primary architectural decisions."
        ),
    }


# ── Public interface ──────────────────────────────────────────────────────────

def run_critic(
    structured_outputs: dict[str, dict],
    iteration: int = 1,
) -> dict:
    """
    Analyze structured agent outputs and return conflict report.

    Returns:
        {
            "agreements": [...],
            "conflicts": [...],
            "gaps": [...],
            "recommendation": "..."
        }
    """
    if is_mock_mode():
        raw = call_model(
            "mock", "",
            _mock_role="__critic__",
            _mock_iteration=iteration,
        )
        return _parse_critic_response(raw)

    # Live mode: call a model to do the critique
    prompt = _build_critic_prompt(structured_outputs)
    try:
        # Use whichever model is available
        from models import _has_openai, _has_anthropic, _has_google
        if _has_openai():
            raw = call_model("openai", prompt, _CRITIC_SYSTEM)
        elif _has_anthropic():
            raw = call_model("anthropic", prompt, _CRITIC_SYSTEM)
        elif _has_google():
            raw = call_model("google", prompt, _CRITIC_SYSTEM)
        else:
            return _rule_based_critic(structured_outputs)

        result = _parse_critic_response(raw)
        if not result.get("conflicts") and not result.get("agreements"):
            # Parse failed — fall back to rule-based
            return _rule_based_critic(structured_outputs)
        return result

    except Exception:
        return _rule_based_critic(structured_outputs)
