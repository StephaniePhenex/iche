"""
orchestrator.py — 3-agent deliberation loop controller.

Flow per round (sequential within each iteration):
  1. Researcher   — collects evidence
  2. Planner+Synthesizer — builds plan + drafts final synthesis (using evidence)
  3. Critic       — identifies conflicts between evidence and plan

Convergence: unresolved conflicts < CONVERGENCE_THRESHOLD, or max iterations reached.
"""

from datetime import datetime, timezone
from typing import Optional

import agents
import structurer
import utils


MAX_ITERATIONS = 3
CONVERGENCE_THRESHOLD = 1  # Stop when len(unresolved) < this


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_deliberation(task: str, previous_round: Optional[dict] = None) -> dict:
    """Execute the full multi-agent deliberation loop. Returns the final state dict."""
    state: dict = {
        "task": task,
        "iterations": [],
        "final_answer": None,
    }
    prev_unresolved: list = []

    # previous_round is only injected into the first iteration of this deliberation
    round_ctx = previous_round

    for iteration_num in range(1, MAX_ITERATIONS + 1):
        utils.print_iteration_banner(iteration_num)
        t_start = datetime.now(timezone.utc)

        # ── Step 1: Researcher ────────────────────────────────────────────────
        print(utils._color("  [1/3] Researcher collecting evidence...", utils.DIM))
        raw_researcher = agents.run_researcher(
            task, prev_unresolved, round_ctx, iteration=iteration_num
        )
        researcher_out = structurer.parse_researcher(raw_researcher)
        evidence = researcher_out.get("evidence", [])
        print(utils._color(f"  → {len(evidence)} evidence item(s).", utils.GREEN))

        # ── Step 2: Planner+Synthesizer ───────────────────────────────────────
        print(utils._color("  [2/3] Planner+Synthesizer building plan...", utils.DIM))
        raw_planner = agents.run_planner(
            task, evidence, prev_unresolved, round_ctx, iteration=iteration_num
        )
        planner_out = structurer.parse_planner(raw_planner)
        n_steps = len(planner_out.get("proposed_plan", []))
        print(utils._color(f"  → {n_steps} step(s). Final choice drafted.", utils.GREEN))

        # ── Step 3: Critic ────────────────────────────────────────────────────
        print(utils._color("  [3/3] Critic analyzing conflicts...", utils.DIM))
        raw_critic = agents.run_critic(
            task, evidence, planner_out, round_ctx, iteration=iteration_num
        )
        critic_out = structurer.parse_critic(raw_critic)
        conflicts = critic_out.get("conflicts", [])
        resolved = critic_out.get("resolved", [])
        unresolved = critic_out.get("unresolved", [])

        latency_ms = int((datetime.now(timezone.utc) - t_start).total_seconds() * 1000)

        # ── Display critic report ─────────────────────────────────────────────
        print()
        print(utils._color("  Critic Report:", utils.BOLD + utils.MAGENTA))
        print(f"    Conflicts  : {len(conflicts)}")
        print(f"    Resolved   : {len(resolved)}")
        print(utils._color(
            f"    Unresolved : {len(unresolved)}",
            utils.RED if len(unresolved) >= CONVERGENCE_THRESHOLD else utils.GREEN,
        ))
        for i, c in enumerate(conflicts, 1):
            print(utils._color(f"\n  [{i}] [{c.get('type','')}] {c.get('description','')[:100]}", utils.RED))
            print(utils._color(f"      → {c.get('resolution_suggestion','')}", utils.YELLOW))

        # ── Record iteration ──────────────────────────────────────────────────
        state["iterations"].append({
            "iteration_number": iteration_num,
            "previous_round": round_ctx,  # None after first iteration
            "agents": [researcher_out, planner_out, critic_out],
            "metadata": {
                "timestamp": _ts(),
                "token_usage": "",
                "cost": "",
                "latency": f"{latency_ms}ms",
            },
        })

        prev_unresolved = unresolved
        round_ctx = None  # only inject previous_round into the first iteration

        # ── Convergence check ─────────────────────────────────────────────────
        if len(unresolved) < CONVERGENCE_THRESHOLD:
            print()
            print(utils._color(
                f"  ✓ Convergence reached ({len(unresolved)} unresolved). Stopping.",
                utils.GREEN + utils.BOLD,
            ))
            break

        if iteration_num < MAX_ITERATIONS:
            print()
            print(utils._color(
                f"  ↺ {len(unresolved)} conflict(s) unresolved. Starting next round...",
                utils.YELLOW,
            ))

    # ── Final answer: taken from last iteration's Planner + Critic ───────────
    last = state["iterations"][-1]
    last_planner = next(
        (a for a in last["agents"] if a.get("agent") == "Planner+Synthesizer"), {}
    )
    last_critic = next(
        (a for a in last["agents"] if a.get("agent") == "Critic"), {}
    )
    state["final_answer"] = {
        "final_choice": last_planner.get("final_choice", ""),
        "reasoning": last_planner.get("reasoning", ""),
        "unresolved_issues": last_critic.get("unresolved", []),
    }

    utils.print_final(state["final_answer"])
    return state
