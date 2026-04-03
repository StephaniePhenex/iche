"""
models.py — Unified LLM interface.

Supports OpenAI (gpt-4o), Anthropic (claude-3-5-sonnet-20241022), Google (gemini-2.0-flash).
Auto-falls back to deterministic mock responses when no API keys are present.
"""

import os
import json
import hashlib
import textwrap
from typing import Optional

# ── API key detection ────────────────────────────────────────────────────────

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
    """
    Provider for JSON repair in structurer — must not use model_name='mock' when keys exist,
    or repair always yields literal solution \"mock\".
    """
    if is_mock_mode():
        return "mock"
    if _has_google():
        return "google"
    if _has_openai():
        return "openai"
    if _has_anthropic():
        return "anthropic"
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
        max_tokens=8192,
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(prompt: str, system_prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=8192,
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

# Each agent has a distinct "perspective" seeded by role.
# Conflicts are injected in round 1; positions converge by round 2-3.

_MOCK_POSITIONS = {
    "rational_planner": {
        1: {
            "solution": "Adopt a microservices architecture with an API gateway, "
                        "event-driven messaging via Kafka, and PostgreSQL per service.",
            "assumptions": [
                "Team has containerization expertise",
                "System will need independent scaling per component",
                "Budget allows for infrastructure overhead",
            ],
            "tradeoffs": [
                "Higher operational complexity vs. fine-grained scalability",
                "Network latency between services vs. independent deployments",
            ],
            "risks": [
                "Distributed system failure modes are harder to debug",
                "Eventual consistency creates data sync challenges",
            ],
            "failure_cases": [
                "Message broker unavailability cascades across services",
                "Service discovery failure causes total outage",
            ],
            "confidence": 0.78,
            "analysis": (
                "From a system architecture standpoint, the problem demands high scalability "
                "and independent deployability. Microservices with event sourcing provide "
                "clear service boundaries and allow teams to deploy independently. "
                "The trade-off is operational complexity, but this is acceptable given "
                "the expected growth trajectory."
            ),
        },
        2: {
            "solution": "Adopt a modular monolith first, with microservices extraction "
                        "for high-load components (auth, notifications). Use PostgreSQL "
                        "with read replicas and Redis caching.",
            "assumptions": [
                "Start simple, extract services when bottlenecks emerge",
                "Team can handle a single deployment unit initially",
                "Read-heavy workload benefits from caching layer",
            ],
            "tradeoffs": [
                "Simpler ops initially vs. migration effort later",
                "Shared database vs. independent scaling",
            ],
            "risks": [
                "Monolith grows unwieldy if extraction is delayed",
                "Cache invalidation complexity",
            ],
            "failure_cases": [
                "Big-bang extraction causes regression",
                "Cache stampede under peak load",
            ],
            "confidence": 0.84,
            "analysis": (
                "After reviewing the critical analyst's concerns about premature complexity, "
                "I revise toward a modular monolith with selective service extraction. "
                "This balances operational simplicity with future scalability."
            ),
        },
        3: {
            "solution": "Modular monolith with clearly defined domain boundaries, "
                        "async workers for heavy tasks, PostgreSQL + Redis. Extract "
                        "auth and notification as microservices from day one.",
            "assumptions": [
                "Clear domain model is defined upfront",
                "Async processing acceptable for non-critical paths",
            ],
            "tradeoffs": [
                "Moderate complexity vs. proven scalability path",
            ],
            "risks": ["Domain boundary misalignment early on"],
            "failure_cases": ["Worker queue overflow under unexpected spike"],
            "confidence": 0.89,
            "analysis": (
                "Converging with the team: modular monolith with async workers "
                "and selective service extraction is the right pragmatic choice."
            ),
        },
    },
    "critical_analyst": {
        1: {
            "solution": "Build a monolithic application with a well-structured layered "
                        "architecture. Use a single PostgreSQL database with careful "
                        "schema design. Avoid distributed complexity until proven necessary.",
            "assumptions": [
                "YAGNI principle: don't over-engineer for scale that may not arrive",
                "Small-to-medium team size",
                "Rapid iteration is more important than scalability initially",
            ],
            "tradeoffs": [
                "Simpler to build and debug vs. harder to scale individual components",
                "Single deployment artifact vs. deployment flexibility",
            ],
            "risks": [
                "May need significant refactoring if scale requirements change",
                "Potential for tight coupling over time",
            ],
            "failure_cases": [
                "Full application downtime during deployments",
                "Database becomes the bottleneck with no isolation path",
            ],
            "confidence": 0.82,
            "analysis": (
                "The system architect's proposal for microservices is premature optimization. "
                "Distributed systems introduce failure modes that small teams struggle to manage. "
                "A monolith with clean architecture is faster to ship, easier to debug, "
                "and can be extracted into services when actual bottlenecks appear — "
                "not hypothetical ones."
            ),
        },
        2: {
            "solution": "Layered monolith with domain modules enforced at code level. "
                        "PostgreSQL with connection pooling (PgBouncer). Extract only "
                        "proven bottlenecks into services. Add Redis for session/cache.",
            "assumptions": [
                "Domain boundaries can be enforced without physical service separation",
                "Bottleneck-driven extraction reduces migration risk",
            ],
            "tradeoffs": [
                "Lower operational overhead vs. longer refactor when scaling",
            ],
            "risks": [
                "Domain coupling drift without strict code review",
            ],
            "failure_cases": [
                "Premature extraction triggers regressions",
            ],
            "confidence": 0.86,
            "analysis": (
                "I acknowledge the system architect's point on domain isolation. "
                "A hybrid approach with modular boundaries maintained at code level "
                "is a reasonable compromise before physical service separation."
            ),
        },
        3: {
            "solution": "Modular monolith, domain-driven, with async task queue (Celery/Redis) "
                        "for background jobs. PostgreSQL primary with read replica. "
                        "Auth service extracted from day one for security isolation.",
            "assumptions": [
                "Auth isolation is a security requirement, not just scaling",
            ],
            "tradeoffs": [
                "Slight ops overhead for auth service vs. security and compliance benefits",
            ],
            "risks": ["Auth service becomes single point of failure if not HA"],
            "failure_cases": ["Auth downtime blocks entire user-facing system"],
            "confidence": 0.90,
            "analysis": (
                "Strong convergence with the team. Auth as isolated service for "
                "security reasons is non-negotiable; rest stays modular monolith."
            ),
        },
    },
    "divergent_thinker": {
        1: {
            "solution": "Use a serverless-first architecture (AWS Lambda / Cloud Functions) "
                        "with DynamoDB for primary storage and S3 for object storage. "
                        "GraphQL API layer. Zero infrastructure management.",
            "assumptions": [
                "Workload is bursty and benefits from auto-scaling to zero",
                "Team prefers managed infrastructure over Kubernetes complexity",
                "Cost model favors pay-per-request over reserved capacity",
            ],
            "tradeoffs": [
                "Cold start latency vs. zero idle cost",
                "Vendor lock-in vs. fully managed scalability",
                "DynamoDB access patterns must be planned upfront",
            ],
            "risks": [
                "Cold start latency unacceptable for latency-sensitive paths",
                "DynamoDB data model requires upfront access pattern design",
                "Vendor lock-in limits future portability",
            ],
            "failure_cases": [
                "Lambda concurrency limits hit under traffic spikes",
                "DynamoDB hot partition degrades performance",
            ],
            "confidence": 0.71,
            "analysis": (
                "Both the architect and analyst are thinking inside the VM-centric box. "
                "Serverless eliminates entire categories of infrastructure problems. "
                "DynamoDB at scale has proven reliability. GraphQL reduces over-fetching "
                "and gives clients query flexibility. The real risk is cold starts, "
                "which can be mitigated with provisioned concurrency on critical paths."
            ),
        },
        2: {
            "solution": "Hybrid: serverless for async/batch workloads (image processing, "
                        "email, reports), traditional container deployment (Kubernetes) "
                        "for the core API. PostgreSQL as the source of truth.",
            "assumptions": [
                "Not all workloads benefit equally from serverless",
                "PostgreSQL is the correct relational store for complex queries",
            ],
            "tradeoffs": [
                "Dual infrastructure complexity vs. right tool for each workload",
            ],
            "risks": [
                "Two deployment paradigms increase cognitive load",
            ],
            "failure_cases": [
                "Serverless async jobs and sync API state get out of sync",
            ],
            "confidence": 0.79,
            "analysis": (
                "Reconsidering pure serverless given the team's concerns. "
                "A hybrid approach uses serverless where it shines (async, batch) "
                "and containers for the latency-sensitive API core."
            ),
        },
        3: {
            "solution": "Container-based modular monolith (Docker + simple orchestration) "
                        "with serverless async workers for background tasks. PostgreSQL + Redis. "
                        "GraphQL or REST API at the gateway.",
            "assumptions": [
                "Containers strike the right balance between control and manageability",
            ],
            "tradeoffs": [
                "More setup than serverless vs. better latency and portability",
            ],
            "risks": ["Container orchestration learning curve"],
            "failure_cases": ["Worker job failures need dead-letter queue"],
            "confidence": 0.87,
            "analysis": (
                "Converging on container-based modular approach with serverless "
                "reserved for async workloads. Aligns with the team consensus."
            ),
        },
    },
}

_MOCK_CRITIC = {
    1: {
        "agreements": [
            "PostgreSQL is a suitable relational store",
            "The system requires both sync and async processing paths",
            "Security isolation for authentication is important",
        ],
        "conflicts": [
            {
                "topic": "Primary architecture style",
                "position_A": "rational_planner: Full microservices with Kafka",
                "position_B": "critical_analyst: Monolith with layered architecture",
                "required_resolution": "Agree on phased approach — start monolith or modular, define extraction criteria",
            },
            {
                "topic": "Infrastructure paradigm",
                "position_A": "divergent_thinker: Serverless-first with DynamoDB",
                "position_B": "rational_planner + critical_analyst: Container/VM-based with PostgreSQL",
                "required_resolution": "Decide primary compute paradigm; serverless for specific workloads only or as primary",
            },
            {
                "topic": "Database strategy",
                "position_A": "rational_planner: Per-service PostgreSQL databases",
                "position_B": "divergent_thinker: DynamoDB as primary store",
                "position_C": "critical_analyst: Single PostgreSQL with careful schema design",
                "required_resolution": "Unify on a single primary data store strategy",
            },
        ],
        "gaps": [
            "No agent addressed team size and skill constraints explicitly",
            "Deployment and CI/CD strategy not mentioned",
            "Observability and monitoring approach missing",
        ],
        "recommendation": (
            "Major conflicts exist on architecture style and infrastructure. "
            "Agents should converge on a phased approach: pragmatic start, "
            "defined evolution path. Serverless should be scoped to async workloads only."
        ),
    },
    2: {
        "agreements": [
            "Modular monolith as starting point is preferred by majority",
            "PostgreSQL as primary relational store",
            "Redis for caching and async queue",
            "Auth service extraction justified (security isolation)",
        ],
        "conflicts": [
            {
                "topic": "Scope of initial service extraction",
                "position_A": "rational_planner: Extract auth + notifications from day one",
                "position_B": "critical_analyst: Extract only auth; notifications stay in monolith",
                "required_resolution": "Define which services are extracted at launch vs. deferred",
            },
        ],
        "gaps": [
            "Observability stack not yet agreed upon",
            "Data migration strategy for future service extraction not addressed",
        ],
        "recommendation": (
            "Strong convergence achieved. One remaining conflict on extraction scope. "
            "Resolve by defining extraction criteria: security-critical services (auth) "
            "at launch; others deferred until throughput justifies it."
        ),
    },
    3: {
        "agreements": [
            "Modular monolith, domain-driven",
            "PostgreSQL + Redis",
            "Auth service extracted (security isolation)",
            "Async workers for background tasks",
            "Containers as compute unit",
        ],
        "conflicts": [],
        "gaps": [],
        "recommendation": (
            "Full convergence reached. Final solution is well-supported by all agents. "
            "Proceed with synthesis."
        ),
    },
}


def _mock_agent_response(agent_role: str, iteration: int, task: str) -> str:
    # AGENTS registry uses creative_explorer; mock table still keyed as divergent_thinker
    if agent_role == "creative_explorer":
        agent_role = "divergent_thinker"
    pos = _MOCK_POSITIONS.get(agent_role, {}).get(iteration, {})
    if not pos:
        pos = _MOCK_POSITIONS[agent_role][3]

    analysis = pos.get("analysis", "No analysis provided.")
    structured = {
        "solution": pos["solution"],
        "assumptions": pos["assumptions"],
        "tradeoffs": pos["tradeoffs"],
        "risks": pos["risks"],
        "failure_cases": pos["failure_cases"],
        "confidence": pos["confidence"],
    }

    return (
        f"[Analysis]\n{analysis}\n\n"
        f"[Structured Output]\nJSON ONLY:\n{json.dumps(structured, indent=2)}"
    )


def _mock_critic_response(iteration: int) -> str:
    data = _MOCK_CRITIC.get(iteration, _MOCK_CRITIC[3])
    return json.dumps(data, indent=2)


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
    _mock_* params: used internally by mock engine.
    """
    if is_mock_mode() or model_name == "mock":
        if _mock_role == "__critic__":
            return _mock_critic_response(_mock_iteration)
        if _mock_role:
            return _mock_agent_response(_mock_role, _mock_iteration, _mock_task)
        # Generic mock: echo prompt summary
        return (
            "[Analysis]\nMock analysis — no API keys configured.\n\n"
            "[Structured Output]\nJSON ONLY:\n"
            '{"solution": "mock", "assumptions": [], "tradeoffs": [], '
            '"risks": [], "failure_cases": [], "confidence": 0.5}'
        )

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
