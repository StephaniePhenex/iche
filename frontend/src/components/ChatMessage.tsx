import { useState } from "react";
import type { ChatResult } from "../services/api";

// ── Icons ─────────────────────────────────────────────────────────────────────

const UserIcon = () => (
  <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-sm font-bold shrink-0">
    U
  </div>
);

const AgentIcon = () => (
  <div className="w-8 h-8 rounded-full bg-emerald-700 flex items-center justify-center text-sm shrink-0">
    ⚡
  </div>
);

// ── Confidence bar ────────────────────────────────────────────────────────────

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? "bg-emerald-500" : pct >= 60 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-surface-600 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 w-8 text-right">{pct}%</span>
    </div>
  );
}

// ── Collapsible process trace (iterations only) ───────────────────────────────

function ProcessTrace({ data }: { data: ChatResult["structured_output"] }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-3 border border-surface-600 rounded-lg overflow-hidden text-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-surface-800 hover:bg-surface-700 transition-colors text-left"
      >
        <span className="flex items-center gap-2 text-gray-500 text-xs">
          <span>🔄</span>
          协商过程
          <span>
            ({data.iterations.length} 轮 ·{" "}
            {data.iterations.reduce((s, i) => s + i.conflicts, 0)} 分歧已解决)
          </span>
        </span>
        <span className="text-gray-600 text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-4 py-3 bg-surface-900 space-y-4 animate-fade-in">
          {data.iterations.map((it) => (
            <div key={it.number}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                  第 {it.number} 轮
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    it.conflicts === 0
                      ? "bg-emerald-900/50 text-emerald-400"
                      : it.conflicts === 1
                      ? "bg-yellow-900/50 text-yellow-400"
                      : "bg-red-900/50 text-red-400"
                  }`}
                >
                  {it.conflicts} 个分歧
                </span>
              </div>

              <div className="space-y-2">
                {it.agents.map((ag) => (
                  <div key={ag.agent} className="rounded-lg bg-surface-800 border border-surface-600 px-3 py-2.5">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-indigo-400 font-medium text-xs">
                        {ag.agent.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </span>
                    </div>
                    <p className="text-gray-300 text-xs leading-relaxed mb-2">{ag.solution}</p>
                    <ConfidenceBar value={ag.confidence} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Final answer card (always visible) ───────────────────────────────────────

function FinalAnswerCard({ data }: { data: ChatResult["structured_output"] }) {
  const hasFinal = !!data.final_solution?.trim();
  const hasWhy = data.why_this.length > 0;
  const hasRejected = data.rejected_options.length > 0;

  if (!hasFinal && !hasWhy) return null;

  return (
    <div className="mt-3 rounded-xl border border-surface-500 overflow-hidden text-sm bg-surface-800">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-surface-700 border-b border-surface-600">
        <span className="flex items-center gap-2 text-gray-300 font-medium text-xs">
          <span>✅</span> 最终方案
        </span>
        <ConfidenceBar value={data.confidence} />
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Main solution — full text, no truncation */}
        {hasFinal && (
          <p className="text-gray-100 leading-relaxed whitespace-pre-wrap">
            {data.final_solution.trim()}
          </p>
        )}

        {/* Why this */}
        {hasWhy && (
          <div>
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-2">
              采纳理由
            </p>
            <ul className="space-y-1.5">
              {data.why_this.map((w, i) => (
                <li key={i} className="flex gap-2 items-start text-sm text-gray-300 leading-relaxed">
                  <span className="text-emerald-400 mt-0.5 shrink-0">✓</span>
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Rejected options */}
        {hasRejected && (
          <div className="border-t border-surface-600 pt-3">
            <p className="text-xs text-gray-600 font-medium uppercase tracking-wide mb-2">
              已排除方案
            </p>
            <ul className="space-y-1">
              {data.rejected_options.map((r, i) => (
                <li key={i} className="flex gap-2 items-start text-xs text-gray-500 leading-relaxed">
                  <span className="text-red-500 mt-0.5 shrink-0">✗</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Message types ─────────────────────────────────────────────────────────────

export interface Message {
  id: string;
  role: "user" | "agent";
  text: string;
  structured?: ChatResult["structured_output"];
  timestamp: Date;
}

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function ChatMessage({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {isUser ? <UserIcon /> : <AgentIcon />}

      <div
        className={`flex flex-col ${
          isUser ? "items-end max-w-[72%]" : "items-start w-full max-w-3xl"
        }`}
      >
        {/* Chat bubble — user message or agent status line */}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? "bg-indigo-600 text-white rounded-tr-sm"
              : "bg-surface-700 text-gray-400 rounded-tl-sm"
          }`}
        >
          {msg.text}
        </div>

        {/* Final answer card — always fully visible */}
        {!isUser && msg.structured && (
          <FinalAnswerCard data={msg.structured} />
        )}

        {/* Process trace — collapsible */}
        {!isUser && msg.structured && (
          <ProcessTrace data={msg.structured} />
        )}

        <span className="text-[11px] text-gray-600 mt-1.5 px-1">
          {formatTime(msg.timestamp)}
        </span>
      </div>
    </div>
  );
}

// ── Typing indicator ──────────────────────────────────────────────────────────

export function TypingIndicator() {
  return (
    <div className="flex gap-3 animate-fade-in">
      <AgentIcon />
      <div className="bg-surface-700 rounded-2xl rounded-tl-sm px-4 py-3.5 flex gap-1.5 items-center">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}
