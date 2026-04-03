"""
orchestrator.py — Deliberation loop controller.

Controls:
  1. Parallel agent execution
  2. Output structuring
  3. Critic analysis
  4. Conflict resolution injection
  5. Convergence check
  6. Final synthesis
"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import agents as agent_module
import critic as critic_module
import state as state_module
import structurer
import utils


# ── Configuration ─────────────────────────────────────────────────────────────

MAX_ITERATIONS = 3
CONVERGENCE_CONFLICT_THRESHOLD = 2  # Stop if conflicts < this


# ── Parallel agent runner ─────────────────────────────────────────────────────

def _run_agents_parallel(
    task: str,
    conflicts: Optional[list],
    iteration: int,
) -> dict[str, str]:
    """Run all agents concurrently. Returns {role: raw_output}."""
    roles = list(agent_module.AGENTS.keys())
    results = {}

    with ThreadPoolExecutor(max_workers=len(roles)) as pool:
        futures = {
            pool.submit(
                agent_module.run_agent,
                role,
                task,
                conflicts,
                iteration=iteration,
            ): role
            for role in roles
        }
        for future in as_completed(futures):
            role = futures[future]
            try:
                results[role] = future.result()
            except Exception as exc:
                results[role] = (
                    f"[Analysis]\nAgent error: {exc}\n\n"
                    "[Structured Output]\nJSON ONLY:\n"
                    '{"solution": "error", "assumptions": [], "tradeoffs": [], '
                    '"risks": ["agent_execution_error"], "failure_cases": [], "confidence": 0.0}'
                )

    return results


# ── Structuring ───────────────────────────────────────────────────────────────

def _structure_all(raw_outputs: dict[str, str]) -> dict[str, dict]:
    return {
        role: structurer.structure_output(raw, role)
        for role, raw in raw_outputs.items()
    }


# ── Synthesizer ───────────────────────────────────────────────────────────────

def _synthesize(state: dict) -> dict:
    """
    Combine all final structured outputs into a unified decision.
    Uses the last iteration's structured outputs.
    """
    iterations = state["iterations"]
    if not iterations:
        return {"final_solution": "No deliberation completed.", "why_this": [], "rejected_options": [], "confidence": 0.0}

    last = iterations[-1]
    structured = last["structured_outputs"]

    # Collect all solutions
    solutions = {role: out.get("solution", "") for role, out in structured.items()}
    confidences = {role: float(out.get("confidence", 0.5)) for role, out in structured.items()}

    # Pick highest-confidence solution as primary
    primary_role = max(confidences, key=confidences.get)
    primary_solution = solutions[primary_role]

    # Build "why this": merge agreements + primary analysis
    resolution = last.get("resolution", {})
    agreements = resolution.get("agreements", [])
    why_this = list(agreements) if agreements else []
    why_this.append(f"Highest confidence solution from {primary_role} ({confidences[primary_role]:.0%})")

    # Rejected: solutions that diverged significantly from primary
    rejected = []
    for role, sol in solutions.items():
        if role == primary_role:
            continue
        sim = utils.cosine_similarity(primary_solution, sol)
        if sim < 0.3:
            rejected.append(f"{role}: {sol}")

    avg_conf = utils.average_confidence(structured)

    # Consensus solution: merge primary with any common elements
    all_assumptions = []
    all_risks = []
    seen_a, seen_r = set(), set()
    for out in structured.values():
        for a in out.get("assumptions", []):
            if a not in seen_a:
                all_assumptions.append(a)
                seen_a.add(a)
        for r in out.get("risks", []):
            if r not in seen_r:
                all_risks.append(r)
                seen_r.add(r)

    # Build a richer final solution description
    if len(iterations) >= 2:
        # Check convergence across iterations
        iter1_solutions = set(iterations[0]["structured_outputs"][r].get("solution", "")[:50] for r in structured)
        iter_last_solutions = set(structured[r].get("solution", "")[:50] for r in structured)
        converged = iter1_solutions != iter_last_solutions

        if converged:
            why_this.insert(0, f"Agents converged over {len(iterations)} iteration(s) from divergent initial positions")

    return {
        "final_solution": primary_solution,
        "why_this": why_this,
        "rejected_options": rejected,
        "confidence": avg_conf,
        "supporting_agents": [r for r in structured if r != primary_role],
        "consensus_risks": all_risks[:5],
        "consensus_assumptions": all_assumptions[:5],
    }


# ── Iteration display ─────────────────────────────────────────────────────────

def _print_agent_outputs(structured: dict[str, dict]) -> None:
    for role, out in structured.items():
        analysis_preview = (out.get("analysis") or "")[:200].replace("\n", " ")
        conf = out.get("confidence", 0.0)
        sol_preview = (out.get("solution") or "")[:100]
        utils.print_section(
            f"{role}  (confidence: {conf:.0%})",
            f"Solution: {sol_preview}\nAnalysis: {analysis_preview}...",
            color=utils.BLUE,
        )


def _print_similarities(structured: dict[str, dict]) -> None:
    sims = utils.pairwise_similarities(structured)
    if sims:
        print(utils.DIM + "  Solution similarities:" + utils.RESET)
        for pair, score in sims.items():
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            print(f"    {pair}: [{bar}] {score:.0%}")


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run_deliberation(task: str) -> dict:
    """
    Execute the full multi-agent deliberation loop.

    Returns the final state dict.
    """
    state = state_module.make_state(task)
    active_conflicts = None

    for iteration_num in range(1, MAX_ITERATIONS + 1):
        utils.print_iteration_banner(iteration_num)

        # 1. Run all agents in parallel
        print(utils._color("  Running agents in parallel...", utils.DIM))
        raw_outputs = _run_agents_parallel(task, active_conflicts, iteration_num)

        # 2. Structure outputs
        print(utils._color("  Structuring outputs...", utils.DIM))
        structured_outputs = _structure_all(raw_outputs)

        # 3. Display agent outputs
        _print_agent_outputs(structured_outputs)
        _print_similarities(structured_outputs)

        # 4. Run critic
        print(utils._color("\n  Running critic...", utils.DIM))
        critique = critic_module.run_critic(structured_outputs, iteration=iteration_num)
        active_conflicts = critique.get("conflicts", [])

        # 5. Record iteration
        record = state_module.make_iteration_record()
        record["raw_outputs"] = raw_outputs
        record["structured_outputs"] = structured_outputs
        record["conflicts"] = active_conflicts
        record["resolution"] = critique
        state_module.push_iteration(state, record)

        # 6. Display critique
        n_conflicts = len(active_conflicts)
        avg_conf = utils.average_confidence(structured_outputs)

        print()
        print(utils._color(f"  Critic Report:", utils.BOLD + utils.MAGENTA))
        print(f"    Agreements  : {len(critique.get('agreements', []))}")
        print(utils._color(f"    Conflicts   : {n_conflicts}", utils.RED if n_conflicts >= CONVERGENCE_CONFLICT_THRESHOLD else utils.GREEN))
        print(f"    Avg Confidence: {avg_conf:.0%}")

        if active_conflicts:
            print(utils._color("  Conflicts detected:", utils.RED))
            for i, c in enumerate(active_conflicts, 1):
                utils.print_conflict(c, i)

        if critique.get("recommendation"):
            print()
            print(utils._color("  Recommendation: ", utils.YELLOW) + critique["recommendation"])

        # 7. Convergence check
        if n_conflicts < CONVERGENCE_CONFLICT_THRESHOLD:
            print()
            print(utils._color(
                f"  ✓ Convergence reached ({n_conflicts} conflict(s) remaining). Stopping.",
                utils.GREEN + utils.BOLD,
            ))
            break

        if iteration_num < MAX_ITERATIONS:
            print()
            print(utils._color(
                f"  ↺ {n_conflicts} conflicts remain. Injecting resolution prompts...",
                utils.YELLOW,
            ))

    # 8. Synthesize final answer
    final = _synthesize(state)
    state_module.set_final_answer(state, final)

    return state
