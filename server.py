"""
Minimal HTTP API for the frontend — maps orchestrator state to /api/chat.

Run from repo root:
  pip install -r requirements.txt
  python server.py

Then set frontend VITE_API_URL=http://127.0.0.1:8000 and restart Vite.
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import time

from flask import Flask, jsonify, request
from flask_cors import CORS

import orchestrator
import utils

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _norm_text(s: str) -> str:
    return " ".join((s or "").split())


def _compose_final_solution(state: dict, synthesized: str) -> str:
    """
    Synthesizer only keeps one agent's solution; users expect every agent's full text.
    Append other agents' last-round solutions under clear headings.
    """
    syn = (synthesized or "").strip()
    iters = state.get("iterations") or []
    if not iters:
        return syn
    so = iters[-1].get("structured_outputs") or {}
    if not so:
        return syn

    nsyn = _norm_text(syn)
    seen_norms: set[str] = {nsyn} if nsyn else set()
    blocks: list[str] = []

    if syn:
        blocks.append("【综合结论】\n" + syn)

    for role, out in so.items():
        sol = (out.get("solution") or "").strip()
        if not sol:
            continue
        n = _norm_text(sol)
        if n in seen_norms:
            continue
        seen_norms.add(n)
        label = role.replace("_", " ").strip() or "Agent"
        blocks.append(f"\n\n【{label} · 完整提案】\n{sol}")

    return "".join(blocks).strip() if blocks else syn


def _state_to_chat_result(state: dict) -> dict:
    iterations_out: list[dict] = []
    for i, rec in enumerate(state.get("iterations") or [], start=1):
        so = rec.get("structured_outputs") or {}
        agents = []
        for role, out in so.items():
            agents.append(
                {
                    "agent": role,
                    "solution": out.get("solution") or "",
                    "confidence": float(out.get("confidence") or 0.0),
                    "analysis": out.get("analysis") or "",
                }
            )
        n_conf = len(rec.get("conflicts") or [])
        avg_conf = utils.average_confidence(so) if so else 0.0
        iterations_out.append(
            {
                "number": i,
                "conflicts": n_conf,
                "avg_confidence": avg_conf,
                "agents": agents,
            }
        )

    final = state.get("final_answer") or {}
    synthesized = final.get("final_solution") or ""
    display_final = _compose_final_solution(state, synthesized)
    return {
        "response": f"Multi-agent deliberation complete ({len(iterations_out)} iterations).",
        "structured_output": {
            "iterations": iterations_out,
            "final_solution": display_final,
            "confidence": float(final.get("confidence") or 0.0),
            "why_this": list(final.get("why_this") or []),
            "rejected_options": list(final.get("rejected_options") or []),
        },
    }


@app.post("/api/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username") or "user"
    return jsonify(
        {"approved": True, "message": f"Welcome, {username}. (dev server — no real account store.)"}
    )


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    if not data.get("username") or not data.get("password"):
        return jsonify({"message": "Username and password required"}), 400
    payload = base64.b64encode(
        json.dumps({"sub": data["username"], "iat": int(time.time())}).encode()
    ).decode()
    return jsonify({"token": f"dev.{payload}.sig"})


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"message": "message required"}), 400

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        state = orchestrator.run_deliberation(message)

    return jsonify(_state_to_chat_result(state))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
