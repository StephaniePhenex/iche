"""
agents.py — Agent definitions and prompt builders.

Three specialized agents:
  1. researcher          — evidence collection
  2. planner_synthesizer — step planning + final synthesis
  3. critic              — conflict detection and resolution
"""

from typing import Optional
from models import call_model

# ── Agent registry ────────────────────────────────────────────────────────────

AGENTS = {
    "researcher": {
        "model": "google",
        "description": (
            "You gather relevant facts, domain knowledge, context, and data points "
            "to support planning and decision-making. You draw on general knowledge, "
            "user context, and reasoned inference to surface the most relevant evidence."
        ),
    },
    "planner_synthesizer": {
        "model": "google",
        "description": (
            "You break problems into clear, actionable steps and synthesize the best "
            "final recommendation. You integrate evidence from the Researcher and "
            "incorporate Critic feedback to produce an optimal, realistic plan."
        ),
    },
    "critic": {
        "model": "google",
        "description": (
            "You identify conflicts, logical gaps, and unsupported assumptions between "
            "the Researcher's evidence and the Planner's proposals. You classify each "
            "conflict by type and suggest concrete, actionable resolutions."
        ),
    },
}

# ── Output format contracts ───────────────────────────────────────────────────

_RESEARCHER_FORMAT = """Return ONLY valid JSON — no markdown fences, no extra text:
{
  "agent": "Researcher",
  "evidence": [
    {"source": "<domain knowledge / user context / reasoning>", "content": "<detailed, actionable finding>"},
    {"source": "...", "content": "..."}
  ],
  "tool_used": ["WebSearch", "DomainKnowledge"]
}
Include 3–6 evidence items. Each `content` must be specific and directly useful to the planner.
`tool_used`: list the knowledge/retrieval methods you drew on (e.g. WebSearch, DomainKnowledge, UserContext, DocumentRetrieval)."""

_PLANNER_FORMAT = """Return ONLY valid JSON — no markdown fences, no extra text:
{
  "agent": "Planner+Synthesizer",
  "proposed_plan": [
    {"step": "Step 1: <label>", "description": "<detailed action or consideration>"},
    {"step": "Step 2: ...", "description": "..."}
  ],
  "final_choice": "<your single best recommendation — write as a complete, standalone answer the user can act on immediately; be specific, detailed, and practical>",
  "reasoning": "<why this plan and choice; address key tradeoffs, how Critic feedback was incorporated, and how previous reasoning was refined>",
  "tool_used": ["Reasoning", "Calculator"]
}
Include 3–6 steps. `final_choice` must be detailed enough to stand alone as the primary user-facing answer.
`tool_used`: list the methods you used (e.g. Reasoning, Calculator, CodeExecutor, APIQuery)."""

_CRITIC_FORMAT = """Return ONLY valid JSON — no markdown fences, no extra text:
{
  "agent": "Critic",
  "conflicts": [
    {
      "id": 1,
      "type": "fact_conflict",
      "agents_involved": ["Researcher", "Planner+Synthesizer"],
      "description": "<what exactly conflicts or is problematic, and why it matters>",
      "resolution_suggestion": "<concrete, specific suggestion to resolve this>"
    }
  ],
  "resolved": ["<description of a conflict resolved in this round>"],
  "unresolved": ["<description of a conflict still needing resolution>"],
  "key_conflicts_prioritized": true,
  "tool_used": ["ConflictAnalysis"]
}
Conflict types: fact_conflict | logic_conflict | preference_conflict
If no conflicts exist: "conflicts": [], "unresolved": [].
`tool_used`: list the analysis methods you used (e.g. ConflictAnalysis, LogicCheck, FactVerification)."""

# ── Prompt builders ───────────────────────────────────────────────────────────

def _previous_round_block(previous_round: Optional[dict]) -> str:
    """Format the previous round context for injection into agent prompts."""
    if not previous_round:
        return ""
    lines = ["\n\nPREVIOUS ROUND CONTEXT (from the last deliberation — build on or refine this):"]
    if previous_round.get("final_choice"):
        lines.append(f"  Previous final choice: {previous_round['final_choice']}")
    if previous_round.get("reasoning"):
        lines.append(f"  Previous reasoning: {previous_round['reasoning']}")
    if previous_round.get("unresolved_issues"):
        unresolved = "\n".join(f"    - {u}" for u in previous_round["unresolved_issues"])
        lines.append(f"  Still unresolved:\n{unresolved}")
    return "\n".join(lines)


def _researcher_prompt(
    task: str, prev_unresolved: list, previous_round: Optional[dict]
) -> tuple[str, str]:
    system = (
        "You are the Researcher in a multi-agent deliberation panel. "
        + AGENTS["researcher"]["description"]
        + "\nYou help with ANY topic: travel, health, finance, writing, relationships, career, and more."
    )
    prior = _previous_round_block(previous_round)
    conflict_note = ""
    if prev_unresolved:
        items = "\n".join(f"- {c}" for c in prev_unresolved)
        conflict_note = (
            f"\n\nThe Critic identified these unresolved issues from the previous iteration. "
            f"Your evidence should directly address them:\n{items}"
        )
    user = (
        f"TASK:\n{task}{prior}{conflict_note}\n\n"
        f"Gather the most relevant evidence, facts, and context for this task.\n\n"
        f"{_RESEARCHER_FORMAT}"
    )
    return system, user


def _planner_prompt(
    task: str, evidence: list, prev_unresolved: list, previous_round: Optional[dict]
) -> tuple[str, str]:
    system = (
        "You are the Planner+Synthesizer in a multi-agent deliberation panel. "
        + AGENTS["planner_synthesizer"]["description"]
        + "\nYou help with ANY topic: travel, health, finance, writing, relationships, career, and more."
    )
    prior = _previous_round_block(previous_round)
    evidence_block = ""
    if evidence:
        lines = "\n".join(f"- [{e.get('source', '')}] {e.get('content', '')}" for e in evidence)
        evidence_block = f"\n\nRESEARCHER EVIDENCE:\n{lines}"
    conflict_block = ""
    if prev_unresolved:
        lines = "\n".join(f"- {c}" for c in prev_unresolved)
        conflict_block = (
            f"\n\nCRITIC FEEDBACK (unresolved — you MUST address these in your plan and final_choice):\n{lines}"
        )
    user = (
        f"TASK:\n{task}{prior}{evidence_block}{conflict_block}\n\n"
        f"Create a step-by-step plan and synthesize the best final recommendation.\n\n"
        f"{_PLANNER_FORMAT}"
    )
    return system, user


def _critic_prompt(
    task: str, evidence: list, planner: dict, previous_round: Optional[dict]
) -> tuple[str, str]:
    system = (
        "You are the Critic in a multi-agent deliberation panel. "
        + AGENTS["critic"]["description"]
    )
    prior = _previous_round_block(previous_round)
    evidence_block = ""
    if evidence:
        lines = "\n".join(f"- [{e.get('source', '')}] {e.get('content', '')}" for e in evidence)
        evidence_block = f"\n\nRESEARCHER EVIDENCE:\n{lines}"
    planner_block = ""
    if planner:
        steps = "\n".join(
            f"  {s.get('step', '')}: {s.get('description', '')}"
            for s in planner.get("proposed_plan", [])
        )
        planner_block = (
            f"\n\nPLANNER+SYNTHESIZER OUTPUT:"
            f"\nPlan steps:\n{steps}"
            f"\nFinal choice: {planner.get('final_choice', '')}"
            f"\nReasoning: {planner.get('reasoning', '')}"
        )
    user = (
        f"TASK:\n{task}{prior}{evidence_block}{planner_block}\n\n"
        f"Identify conflicts between the Researcher evidence and the Planner's proposals. "
        f"Classify each conflict and suggest resolutions.\n\n"
        f"{_CRITIC_FORMAT}"
    )
    return system, user


# ── Agent runners ─────────────────────────────────────────────────────────────

def run_researcher(
    task: str,
    prev_unresolved: list = (),
    previous_round: Optional[dict] = None,
    *,
    iteration: int = 1,
) -> str:
    system, user = _researcher_prompt(task, list(prev_unresolved), previous_round)
    return call_model(
        AGENTS["researcher"]["model"], user, system,
        _mock_role="researcher", _mock_iteration=iteration, _mock_task=task,
    )


def run_planner(
    task: str,
    evidence: list = (),
    prev_unresolved: list = (),
    previous_round: Optional[dict] = None,
    *,
    iteration: int = 1,
) -> str:
    system, user = _planner_prompt(task, list(evidence), list(prev_unresolved), previous_round)
    return call_model(
        AGENTS["planner_synthesizer"]["model"], user, system,
        _mock_role="planner_synthesizer", _mock_iteration=iteration, _mock_task=task,
    )


def run_critic(
    task: str,
    evidence: list = (),
    planner: Optional[dict] = None,
    previous_round: Optional[dict] = None,
    *,
    iteration: int = 1,
) -> str:
    system, user = _critic_prompt(task, list(evidence), planner or {}, previous_round)
    return call_model(
        AGENTS["critic"]["model"], user, system,
        _mock_role="critic", _mock_iteration=iteration, _mock_task=task,
    )
