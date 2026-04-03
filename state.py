"""
state.py — Global deliberation state.

Single source of truth passed through the entire engine.
Mutated in-place by the orchestrator; never copied.
"""

from typing import Any


def make_state(task: str) -> dict:
    return {
        "task": task,
        "iterations": [],
        "final_answer": None,
    }


def make_iteration_record() -> dict:
    return {
        "raw_outputs": {},       # agent_role -> str
        "structured_outputs": {}, # agent_role -> dict
        "conflicts": [],          # list of conflict dicts from critic
        "resolution": {},         # full critic output dict
    }


def push_iteration(state: dict, record: dict) -> None:
    state["iterations"].append(record)


def current_iteration_number(state: dict) -> int:
    return len(state["iterations"])


def last_conflicts(state: dict) -> list:
    if not state["iterations"]:
        return []
    return state["iterations"][-1].get("conflicts", [])


def set_final_answer(state: dict, answer: dict) -> None:
    state["final_answer"] = answer
