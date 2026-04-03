"""
agents.py — Agent definitions and prompt builders.

Three agents, each with a distinct cognitive role and assigned model.
All receive the same task; prompts are role-tuned.
"""

from typing import Optional
from models import call_model

# ── Agent registry ────────────────────────────────────────────────────────────

AGENTS = {
    "rational_planner": {
        "model": "google",
        "description": (
            "A structured, methodical thinker who breaks any problem — whether a travel itinerary, "
            "a health goal, a creative project, or a life decision — into clear steps, priorities, "
            "and trade-offs. Focuses on feasibility, sequencing, and realistic constraints."
        ),
    },
    "critical_analyst": {
        "model": "google",
        "description": (
            "A rigorous devil's advocate who stress-tests every plan. Surfaces hidden risks, "
            "challenges assumptions, asks what could go wrong, and pushes for honest evaluation "
            "of costs, downsides, and blind spots — across any domain of life."
        ),
    },
    "creative_explorer": {
        "model": "google",
        "description": (
            "An imaginative lateral thinker who reframes the problem, proposes unexpected alternatives, "
            "and finds options others overlook. Comfortable with travel, relationships, wellness, "
            "writing, career pivots, and any open-ended human challenge."
        ),
    },
}

# ── Output format contract (injected into every prompt) ──────────────────────

_OUTPUT_FORMAT = """
Your response MUST follow this exact format:

[Analysis]
(your reasoning here — free text, 2-4 paragraphs)

[Structured Output]
JSON ONLY:
{
  "solution": "concise description of your proposed solution",
  "assumptions": ["assumption 1", "assumption 2"],
  "tradeoffs": ["tradeoff 1", "tradeoff 2"],
  "risks": ["risk 1", "risk 2"],
  "failure_cases": ["failure case 1", "failure case 2"],
  "confidence": 0.0
}

Ensure confidence is a float between 0.0 and 1.0.
Do not include anything outside these two sections.
""".strip()


# ── Prompt builders ───────────────────────────────────────────────────────────

def _base_prompt(role: str, task: str, conflicts: Optional[list] = None) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given role and task."""
    agent = AGENTS[role]
    description = agent["description"]

    system_prompt = (
        f"You are a {role.replace('_', ' ').title()} in a multi-agent deliberation panel. "
        f"Your cognitive profile: {description}\n\n"
        "You help with ANY kind of question — travel planning, health, writing, career, relationships, "
        "finance, creativity, lifestyle decisions, and more. You are NOT limited to technical topics.\n"
        "Be direct, specific, warm where appropriate, and intellectually honest about tradeoffs."
    )

    if conflicts:
        conflict_block = _format_conflicts_for_resolution(conflicts)
        user_prompt = (
            f"QUESTION / TASK:\n{task}\n\n"
            f"CONFLICT RESOLUTION REQUIRED:\n"
            f"The other agents have proposed different perspectives. "
            f"Address the following conflicts and update your position:\n\n"
            f"{conflict_block}\n\n"
            f"Either defend your view with stronger reasoning, or revise it. "
            f"Be explicit about what you're changing and why.\n\n"
            f"{_OUTPUT_FORMAT}"
        )
    else:
        user_prompt = (
            f"QUESTION / TASK:\n{task}\n\n"
            f"Respond from your role's perspective. This could be a life question, travel plan, "
            f"health goal, creative challenge, decision dilemma, or anything else — approach it fully.\n\n"
            f"{_OUTPUT_FORMAT}"
        )

    return system_prompt, user_prompt


def _format_conflicts_for_resolution(conflicts: list) -> str:
    lines = []
    for i, c in enumerate(conflicts, 1):
        lines.append(f"Conflict {i}: {c.get('topic', 'Unknown topic')}")
        for k, v in c.items():
            if k != "topic":
                lines.append(f"  {k}: {v}")
        lines.append("")
    return "\n".join(lines).strip()


# ── Agent runner ──────────────────────────────────────────────────────────────

def run_agent(
    role: str,
    task: str,
    conflicts: Optional[list] = None,
    *,
    iteration: int = 1,
) -> str:
    """
    Run a single agent and return its raw text output.

    In mock mode, the call_model function generates deterministic role-based responses.
    In live mode, it calls the real API.
    """
    system_prompt, user_prompt = _base_prompt(role, task, conflicts)
    model = AGENTS[role]["model"]

    return call_model(
        model,
        user_prompt,
        system_prompt,
        _mock_role=role,
        _mock_iteration=iteration,
        _mock_task=task,
    )
