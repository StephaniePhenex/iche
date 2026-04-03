"""
Minimal HTTP API for the frontend — maps orchestrator state to /api/chat.

Run from repo root:
  pip install -r requirements.txt
  python server.py

Then set frontend VITE_API_URL=http://127.0.0.1:8000 and restart Vite.
"""

from __future__ import annotations

import base64
import json
import time

from flask import Flask, jsonify, request
from flask_cors import CORS

import orchestrator

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _state_to_chat_result(state: dict) -> dict:
    iterations_out = [
        {
            "iteration_number": rec.get("iteration_number", i + 1),
            "agents": rec.get("agents", []),
            "metadata": rec.get("metadata", {
                "timestamp": "", "token_usage": "", "cost": "", "latency": "",
            }),
        }
        for i, rec in enumerate(state.get("iterations") or [])
    ]

    final = state.get("final_answer") or {}
    return {
        "response": f"Multi-agent deliberation complete ({len(iterations_out)} iteration(s)).",
        "structured_output": {
            "iterations": iterations_out,
            "final_choice": final.get("final_choice") or "",
            "reasoning": final.get("reasoning") or "",
            "unresolved_issues": list(final.get("unresolved_issues") or []),
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

    # Optional: context from the previous message's deliberation result
    previous_round = data.get("previous_round") or None

    state = orchestrator.run_deliberation(message, previous_round=previous_round)

    return jsonify(_state_to_chat_result(state))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
