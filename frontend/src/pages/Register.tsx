import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../services/api";

type Status = "idle" | "loading" | "approved" | "pending" | "rejected" | "error";

export function Register() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setStatus("error");
      setMessage("Passwords do not match.");
      return;
    }
    setStatus("loading");
    try {
      const res = await register(username, password);
      if (res.approved) {
        setStatus("approved");
        setMessage(res.message);
        setTimeout(() => navigate("/login"), 1800);
      } else {
        setStatus(res.message.toLowerCase().includes("pending") ? "pending" : "rejected");
        setMessage(res.message);
      }
    } catch (err: unknown) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Registration failed.");
    }
  };

  const statusBanner = {
    approved: "bg-emerald-900/50 border-emerald-600 text-emerald-300",
    pending:  "bg-yellow-900/50 border-yellow-600 text-yellow-300",
    rejected: "bg-red-900/50 border-red-600 text-red-300",
    error:    "bg-red-900/50 border-red-600 text-red-300",
    idle: "", loading: "",
  } as const;

  const statusIcon = { approved: "✓", pending: "⏳", rejected: "✗", error: "✗", idle: "", loading: "" };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-3xl mb-2">⚡</div>
          <h1 className="text-xl font-semibold text-gray-100">Create account</h1>
          <p className="text-sm text-gray-500 mt-1">Multi-Agent Deliberation Engine</p>
        </div>

        <div className="card p-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Username</label>
              <input
                className="input-field"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="your_username"
                required
                autoFocus
                disabled={status === "loading" || status === "approved"}
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Password</label>
              <input
                className="input-field"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                disabled={status === "loading" || status === "approved"}
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1.5">Confirm password</label>
              <input
                className="input-field"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                required
                disabled={status === "loading" || status === "approved"}
              />
            </div>

            {status !== "idle" && status !== "loading" && (
              <div className={`flex gap-2 items-start p-3 rounded-lg border text-sm ${statusBanner[status]}`}>
                <span className="shrink-0 font-bold">{statusIcon[status]}</span>
                <span>{message}</span>
              </div>
            )}

            <button
              type="submit"
              className="btn-primary"
              disabled={status === "loading" || status === "approved"}
            >
              {status === "loading" ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                  </svg>
                  Registering…
                </span>
              ) : status === "approved" ? (
                "Redirecting to login…"
              ) : (
                "Create account"
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-gray-500 mt-4">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-400 hover:text-indigo-300 transition-colors">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
