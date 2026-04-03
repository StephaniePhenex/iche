"""
models.py — Unified LLM interface.

Supports OpenAI (gpt-4o), Anthropic (claude-3-5-sonnet-20241022), Google (gemini-2.5-flash).
Auto-falls back to deterministic mock responses when no API keys are present.
"""

import os
import json
from typing import Optional

# ── API key detection ─────────────────────────────────────────────────────────

def _has_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())

def _has_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())

def _has_google() -> bool:
    return bool(
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
    )

def is_mock_mode() -> bool:
    return not (_has_openai() or _has_anthropic() or _has_google())

def repair_model_name() -> str:
    """Return the best available model name for repair/fallback tasks."""
    if _has_openai():
        return "openai"
    if _has_anthropic():
        return "anthropic"
    if _has_google():
        return "google"
    return "mock"


# ── Real API calls ────────────────────────────────────────────────────────────

def _call_openai(prompt: str, system_prompt: str) -> str:
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=4096,
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(prompt: str, system_prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text if resp.content else ""


def _call_google(prompt: str, system_prompt: str) -> str:
    from google import genai
    from google.genai import types
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=8192,
        ),
    )
    return resp.text or ""


# ── Mock engine ───────────────────────────────────────────────────────────────
#
# Three-agent system: Researcher → Planner+Synthesizer → Critic.
# Each returns pure JSON matching its role's output schema.
# Conflicts inject in round 1, partially resolve in round 2, fully resolve in round 3.

_MOCK_RESEARCHER: dict[int, dict] = {
    1: {
        "agent": "Researcher",
        "evidence": [
            {
                "source": "domain knowledge",
                "content": "Successful plans require clearly defined goals with measurable success criteria established before execution begins.",
            },
            {
                "source": "general knowledge",
                "content": "Common failure modes: underestimating complexity, skipping validation, not accounting for dependencies, and ignoring edge cases.",
            },
            {
                "source": "expert consensus",
                "content": "Iterative/phased approaches consistently outperform big-bang delivery in uncertain environments — validate core assumptions early.",
            },
            {
                "source": "user context",
                "content": "The specific constraints and context provided shape which options are viable. Fixed constraints must be respected; flexible ones can be negotiated.",
            },
        ],
    },
    2: {
        "agent": "Researcher",
        "evidence": [
            {
                "source": "updated analysis",
                "content": "Addressing Critic conflicts: the primary concern is resolvable with explicit phase boundaries and outcome-based milestones rather than time-only gates.",
            },
            {
                "source": "domain knowledge",
                "content": "Outcome-based phase gates (e.g., 'N assumptions validated') outperform pure time-boxes as readiness indicators.",
            },
            {
                "source": "risk assessment",
                "content": "Phased execution with clear checkpoints reduces blast radius of early-phase failures significantly.",
            },
        ],
    },
    3: {
        "agent": "Researcher",
        "evidence": [
            {
                "source": "consensus findings",
                "content": "All key uncertainties addressed. The chosen approach is well-supported and no significant counter-evidence found.",
            },
            {
                "source": "validation",
                "content": "Remaining unknowns are manageable within the proposed plan. No blocking risks identified.",
            },
        ],
    },
}

_MOCK_PLANNER: dict[int, dict] = {
    1: {
        "agent": "Planner+Synthesizer",
        "proposed_plan": [
            {
                "step": "Step 1: Clarify objectives",
                "description": "Define specific, measurable goals. Identify success criteria and hard constraints upfront so all decisions stay aligned.",
            },
            {
                "step": "Step 2: Map constraints and resources",
                "description": "Inventory time, budget, skills, and dependencies. Distinguish fixed constraints from flexible ones.",
            },
            {
                "step": "Step 3: Generate options",
                "description": "Develop 2–3 concrete approaches using Researcher evidence. Evaluate each against goals and constraints.",
            },
            {
                "step": "Step 4: Select and plan execution",
                "description": "Choose the highest-value option. Break it into concrete actions with milestones and checkpoints.",
            },
            {
                "step": "Step 5: Build contingencies",
                "description": "Identify top 2–3 failure modes and prepare fallback actions for each.",
            },
        ],
        "final_choice": (
            "Adopt a phased, iterative approach: build a minimal viable version first, "
            "validate it against real constraints, then expand. This balances speed with "
            "risk management and allows early course-correction before full commitment."
        ),
        "reasoning": (
            "A phased approach reduces commitment risk, allows early validation, and adapts "
            "as new information emerges. Full upfront planning fails when initial assumptions prove wrong."
        ),
    },
    2: {
        "agent": "Planner+Synthesizer",
        "proposed_plan": [
            {
                "step": "Step 1: Resolve Critic-identified conflicts",
                "description": "Address the specific issues raised before proceeding. Define explicit phase boundaries to prevent debt accumulation.",
            },
            {
                "step": "Step 2: Refine scope with outcome-based milestones",
                "description": "Replace time-only phase gates with outcome-based success criteria (e.g., 'N assumptions validated').",
            },
            {
                "step": "Step 3: Execute with validation gates",
                "description": "Each phase requires passing defined success criteria before the next begins.",
            },
            {
                "step": "Step 4: Monitor and adapt",
                "description": "Track progress against milestones. Activate contingency plans for the most likely failure modes.",
            },
        ],
        "final_choice": (
            "Two-phase implementation: Phase 1 validates core assumptions (outcome-based, not just "
            "time-boxed); Phase 2 scales with confidence from Phase 1 learnings. Explicit phase "
            "boundaries prevent debt accumulation."
        ),
        "reasoning": (
            "Incorporating Critic feedback: replaced rigid time-only milestones with outcome-based "
            "gates. This addresses the conflict between ideal scope and realistic constraints."
        ),
    },
    3: {
        "agent": "Planner+Synthesizer",
        "proposed_plan": [
            {
                "step": "Step 1: Execute validated approach",
                "description": "Proceed with the stress-tested plan. All Critic conflicts have been resolved.",
            },
            {
                "step": "Step 2: Monitor key metrics",
                "description": "Track the specific indicators most critical to success. Adjust if metrics diverge from projections.",
            },
            {
                "step": "Step 3: Document and iterate",
                "description": "Capture learnings at each milestone. Apply them to improve subsequent phases.",
            },
        ],
        "final_choice": (
            "Final: Two-phase phased approach with outcome-based validation gates. Phase 1 validates "
            "core assumptions at low cost; Phase 2 scales with confidence. All identified conflicts resolved."
        ),
        "reasoning": (
            "Full convergence achieved. Approach is pragmatic, risk-aware, and achievable within "
            "realistic constraints. Phased structure provides flexibility while maintaining clear direction."
        ),
    },
}

_MOCK_CRITIC_AGENT: dict[int, dict] = {
    1: {
        "agent": "Critic",
        "conflicts": [
            {
                "id": 1,
                "type": "logic_conflict",
                "agents_involved": ["Planner+Synthesizer", "Researcher"],
                "description": (
                    "Planner treats a phased approach as inherently lower-risk, but Researcher "
                    "evidence shows phased rollouts can accumulate technical debt if phase "
                    "boundaries are not explicitly defined."
                ),
                "resolution_suggestion": (
                    "Planner should define explicit phase boundaries and acceptance criteria "
                    "to prevent debt accumulation between phases."
                ),
            },
            {
                "id": 2,
                "type": "fact_conflict",
                "agents_involved": ["Researcher", "Planner+Synthesizer"],
                "description": (
                    "Researcher identifies 'underestimating complexity' as a top failure mode, "
                    "but the Planner's proposed steps do not include an explicit complexity estimation step."
                ),
                "resolution_suggestion": (
                    "Add an explicit complexity estimation step, or expand Step 2 to include it "
                    "before option generation."
                ),
            },
        ],
        "resolved": [],
        "unresolved": [
            "Phase boundary definition missing — risk of technical debt accumulation",
            "Complexity estimation absent from proposed plan steps",
        ],
    },
    2: {
        "agent": "Critic",
        "conflicts": [
            {
                "id": 1,
                "type": "preference_conflict",
                "agents_involved": ["Planner+Synthesizer", "Researcher"],
                "description": (
                    "Planner's phase gates are still partially time-based. "
                    "Researcher evidence supports outcome-based criteria as more reliable."
                ),
                "resolution_suggestion": (
                    "Replace time-only phase gates with outcome-based success criteria "
                    "(e.g., 'validate N assumptions' rather than 'complete in 4 weeks')."
                ),
            },
        ],
        "resolved": [
            "Phase boundary definition: resolved — Planner Step 1 now explicitly defines phase boundaries",
            "Complexity estimation: resolved — embedded in Step 2 scope refinement",
        ],
        "unresolved": [
            "Phase gates partially time-based — should be primarily outcome-based for reliability",
        ],
    },
    3: {
        "agent": "Critic",
        "conflicts": [],
        "resolved": [
            "Phase boundary definition: resolved",
            "Complexity estimation: resolved",
            "Phase gate criteria: resolved — final plan uses outcome-based success criteria",
        ],
        "unresolved": [],
    },
}


def _mock_agent_response(agent_role: str, iteration: int, task: str) -> str:
    """Return a deterministic pure-JSON mock response for the given role and iteration."""
    lookup: dict[str, dict[int, dict]] = {
        "researcher": _MOCK_RESEARCHER,
        "planner_synthesizer": _MOCK_PLANNER,
        "critic": _MOCK_CRITIC_AGENT,
    }
    role_data = lookup.get(agent_role, {})
    if not role_data:
        return json.dumps({"error": f"Unknown mock role: {agent_role}"})
    data = role_data.get(iteration) or role_data.get(max(role_data.keys()), {})
    return json.dumps(data, ensure_ascii=False)


# ── Public interface ──────────────────────────────────────────────────────────

def call_model(
    model_name: str,
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant.",
    *,
    _mock_role: Optional[str] = None,
    _mock_iteration: int = 1,
    _mock_task: str = "",
) -> str:
    """
    Call the specified model with the given prompt.

    model_name: "openai" | "anthropic" | "google" | "mock"
    _mock_* params: used internally by the mock engine.
    """
    if is_mock_mode() or model_name == "mock":
        if _mock_role:
            return _mock_agent_response(_mock_role, _mock_iteration, _mock_task)
        return json.dumps({"error": "mock — no role specified"})

    if model_name == "openai":
        if not _has_openai():
            raise EnvironmentError("OPENAI_API_KEY not set")
        return _call_openai(prompt, system_prompt)

    if model_name == "anthropic":
        if not _has_anthropic():
            raise EnvironmentError("ANTHROPIC_API_KEY not set")
        return _call_anthropic(prompt, system_prompt)

    if model_name in ("google", "gemini"):
        if not _has_google():
            raise EnvironmentError("GOOGLE_API_KEY / GEMINI_API_KEY not set")
        return _call_google(prompt, system_prompt)

    raise ValueError(f"Unknown model: {model_name}")
