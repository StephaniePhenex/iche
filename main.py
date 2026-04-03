"""
main.py — CLI entry point for the Multi-Agent Deliberation Engine.

Usage:
    python main.py
    python main.py --task "Design a real-time chat system for 1M users"
    python main.py --save          # save state to JSON after deliberation
    python main.py --no-color      # disable ANSI colors
"""

import argparse
import sys
import os

import utils
import orchestrator
from models import is_mock_mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-Agent Deliberation Engine — orchestrates LLMs to solve complex problems.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --task "How should we design our payment system?"
  python main.py --save --task "Choose between SQL and NoSQL for our app"
        """,
    )
    parser.add_argument(
        "--task", "-t",
        type=str,
        default=None,
        help="Problem to deliberate on (prompted interactively if not provided)",
    )
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        default=False,
        help="Save full deliberation state to deliberation_state.json",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="Disable ANSI color output",
    )
    return parser.parse_args()


def get_task(args: argparse.Namespace) -> str:
    if args.task:
        return args.task.strip()
    print(utils._color("\nMulti-Agent Deliberation Engine", utils.BOLD + utils.CYAN))
    print(utils._color("Powered by: GPT-4o · Claude 3.5 · Gemini 2.0", utils.DIM))
    print()
    task = input(utils._color("Enter your problem or question:\n› ", utils.BOLD)).strip()
    if not task:
        print(utils._color("No input provided. Exiting.", utils.RED))
        sys.exit(1)
    return task


def print_startup_info(task: str) -> None:
    utils.print_header("MULTI-AGENT DELIBERATION ENGINE")
    print()
    print(utils._color("Task:", utils.BOLD) + f"  {task}")
    print()

    mock = is_mock_mode()
    if mock:
        print(utils._color(
            "⚠  Running in MOCK MODE (no API keys detected).\n"
            "   Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY for live mode.",
            utils.YELLOW,
        ))
    else:
        active = []
        from models import _has_openai, _has_anthropic, _has_google
        if _has_openai(): active.append("OpenAI GPT-4o")
        if _has_anthropic(): active.append("Claude 3.5")
        if _has_google(): active.append("Gemini 2.0")
        print(utils._color(f"✓  Live mode — Models: {', '.join(active)}", utils.GREEN))

    print()
    print(utils._color("Agents:", utils.BOLD))
    from agents import AGENTS
    for role, cfg in AGENTS.items():
        print(f"  • {utils._color(role, utils.CYAN)}  →  {cfg['model']}  —  {cfg['description']}")

    print()
    print(utils._color(f"Max iterations: {orchestrator.MAX_ITERATIONS}", utils.DIM))
    print(utils._color(f"Convergence threshold: < {orchestrator.CONVERGENCE_CONFLICT_THRESHOLD} conflicts", utils.DIM))


def print_summary_trace(state: dict) -> None:
    utils.print_header("DELIBERATION TRACE")
    print()
    for i, rec in enumerate(state["iterations"], 1):
        n_conflicts = len(rec.get("conflicts", []))
        avg_conf = utils.average_confidence(rec.get("structured_outputs", {}))
        status = utils._color("✓ converged", utils.GREEN) if n_conflicts < orchestrator.CONVERGENCE_CONFLICT_THRESHOLD else utils._color(f"{n_conflicts} conflicts", utils.RED)
        print(f"  Iteration {i}:  Conflicts = {n_conflicts:2d}  |  Avg Confidence = {avg_conf:.0%}  |  {status}")


def main() -> None:
    args = parse_args()

    # Disable colors if requested
    if args.no_color:
        for attr in ["RESET", "BOLD", "DIM", "CYAN", "GREEN", "YELLOW", "RED", "BLUE", "MAGENTA"]:
            setattr(utils, attr, "")

    task = get_task(args)
    print_startup_info(task)

    try:
        state = orchestrator.run_deliberation(task)
    except KeyboardInterrupt:
        print(utils._color("\n\nAborted by user.", utils.RED))
        sys.exit(130)

    # Print trace
    print_summary_trace(state)

    # Print final answer
    if state.get("final_answer"):
        utils.print_final(state["final_answer"])
    else:
        print(utils._color("\nNo final answer produced.", utils.RED))

    # Save state
    if args.save:
        path = utils.save_state(state)
        print(utils._color(f"\n💾  State saved to: {path}", utils.DIM))

    print()


if __name__ == "__main__":
    main()
