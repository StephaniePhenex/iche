"""
utils.py — Shared utilities.

  - Text similarity (cosine on word counts)
  - Confidence averaging
  - State persistence to JSON
  - Terminal output helpers
"""

import json
import math
import os
import re
from collections import Counter
from datetime import datetime
from typing import Any


# ── Similarity ────────────────────────────────────────────────────────────────

def _word_vector(text: str) -> Counter:
    tokens = re.findall(r"[a-z]+", text.lower())
    return Counter(tokens)


def cosine_similarity(text_a: str, text_b: str) -> float:
    """Return cosine similarity [0.0, 1.0] between two strings."""
    va = _word_vector(text_a)
    vb = _word_vector(text_b)
    all_words = set(va) | set(vb)
    if not all_words:
        return 0.0
    dot = sum(va[w] * vb[w] for w in all_words)
    mag_a = math.sqrt(sum(v ** 2 for v in va.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in vb.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def pairwise_similarities(structured_outputs: dict[str, dict]) -> dict[str, float]:
    """Return cosine similarity for each pair of agent solutions."""
    roles = list(structured_outputs.keys())
    results = {}
    for i in range(len(roles)):
        for j in range(i + 1, len(roles)):
            r1, r2 = roles[i], roles[j]
            s1 = structured_outputs[r1].get("solution", "")
            s2 = structured_outputs[r2].get("solution", "")
            key = f"{r1} ↔ {r2}"
            results[key] = round(cosine_similarity(s1, s2), 3)
    return results


# ── Confidence ────────────────────────────────────────────────────────────────

def average_confidence(structured_outputs: dict[str, dict]) -> float:
    scores = [
        float(v.get("confidence", 0.5))
        for v in structured_outputs.values()
        if v.get("confidence") is not None
    ]
    return round(sum(scores) / len(scores), 3) if scores else 0.5


# ── State persistence ─────────────────────────────────────────────────────────

def save_state(state: dict, path: str = "deliberation_state.json") -> str:
    """Save full deliberation state to JSON. Returns the file path."""
    output = {
        "saved_at": datetime.utcnow().isoformat() + "Z",
        **state,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return os.path.abspath(path)


# ── Terminal rendering ────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
BLUE   = "\033[34m"
MAGENTA= "\033[35m"


def _color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def print_header(text: str) -> None:
    width = 70
    print()
    print(_color("═" * width, CYAN))
    print(_color(f"  {text}", BOLD + CYAN))
    print(_color("═" * width, CYAN))


def print_section(title: str, body: str = "", color: str = BLUE) -> None:
    print()
    print(_color(f"┌─ {title}", color + BOLD))
    if body:
        for line in body.splitlines():
            print(_color("│  ", color) + line)
    print(_color("└" + "─" * 50, color))


def print_iteration_banner(n: int) -> None:
    print()
    print(_color(f"{'─'*25} ITERATION {n} {'─'*25}", BOLD + YELLOW))


def print_conflict(conflict: dict, index: int) -> None:
    print(_color(f"\n  [{index}] [{conflict.get('type', '')}] {conflict.get('description', '')[:100]}", BOLD + RED))
    agents_involved = conflict.get("agents_involved", [])
    if agents_involved:
        print(_color(f"      Agents: {', '.join(agents_involved)}", DIM))
    if "resolution_suggestion" in conflict:
        print(_color("      → Resolution: ", YELLOW) + conflict["resolution_suggestion"])


def print_final(final: dict) -> None:
    print_header("FINAL SYNTHESIZED DECISION")
    print()
    print(_color("Final Choice:", BOLD + GREEN))
    print(f"  {final.get('final_choice', 'N/A')}")
    print()
    print(_color("Reasoning:", BOLD))
    print(f"  {final.get('reasoning', '')}")
    if final.get("unresolved_issues"):
        print()
        print(_color("Unresolved Issues:", BOLD + YELLOW))
        for issue in final.get("unresolved_issues", []):
            print(f"  ⚠ {issue}")
    print()
