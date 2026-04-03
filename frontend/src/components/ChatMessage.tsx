import { useState } from "react";
import type { ChatResult, Iteration, AgentOutput, ResearcherOutput, PlannerOutput, CriticOutput } from "../services/api";

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

// ── Type guards ───────────────────────────────────────────────────────────────

function isResearcher(a: AgentOutput): a is ResearcherOutput {
  return a.agent === "Researcher";
}
function isPlanner(a: AgentOutput): a is PlannerOutput {
  return a.agent === "Planner+Synthesizer";
}
function isCritic(a: AgentOutput): a is CriticOutput {
  return a.agent === "Critic";
}

// ── Conflict type badge ───────────────────────────────────────────────────────

function ConflictBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    fact_conflict: "bg-red-900/50 text-red-400",
    logic_conflict: "bg-yellow-900/50 text-yellow-400",
    preference_conflict: "bg-blue-900/50 text-blue-400",
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${colors[type] ?? "bg-surface-600 text-gray-400"}`}>
      {type.replace(/_/g, " ")}
    </span>
  );
}

// ── Researcher panel ──────────────────────────────────────────────────────────

function ToolTags({ tools }: { tools: string[] }) {
  if (!tools?.length) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {tools.map((t) => (
        <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-600 text-gray-500">{t}</span>
      ))}
    </div>
  );
}

function ResearcherPanel({ out }: { out: ResearcherOutput }) {
  return (
    <div className="space-y-2">
      {out.evidence.map((e, i) => (
        <div key={i} className="rounded-lg bg-surface-800 border border-surface-600 px-3 py-2.5">
          <p className="text-[10px] text-indigo-400 font-medium mb-1 uppercase tracking-wide">{e.source}</p>
          <p className="text-gray-300 text-xs leading-relaxed">{e.content}</p>
        </div>
      ))}
      <ToolTags tools={out.tool_used} />
    </div>
  );
}

// ── Planner panel ─────────────────────────────────────────────────────────────

function PlannerPanel({ out }: { out: PlannerOutput }) {
  return (
    <div className="space-y-2">
      {out.proposed_plan.map((s, i) => (
        <div key={i} className="rounded-lg bg-surface-800 border border-surface-600 px-3 py-2.5">
          <p className="text-xs text-emerald-400 font-medium mb-1">{s.step}</p>
          <p className="text-gray-300 text-xs leading-relaxed">{s.description}</p>
        </div>
      ))}
      <ToolTags tools={out.tool_used} />
    </div>
  );
}

// ── Critic panel ──────────────────────────────────────────────────────────────

function CriticPanel({ out }: { out: CriticOutput }) {
  return (
    <div className="space-y-3">
      {out.conflicts.map((c) => (
        <div key={c.id} className="rounded-lg bg-surface-800 border border-red-900/40 px-3 py-2.5">
          <div className="flex items-center gap-2 mb-1.5">
            <ConflictBadge type={c.type} />
            <span className="text-[10px] text-gray-600">{c.agents_involved.join(" · ")}</span>
          </div>
          <p className="text-gray-300 text-xs leading-relaxed mb-1.5">{c.description}</p>
          <p className="text-yellow-400/80 text-xs leading-relaxed">→ {c.resolution_suggestion}</p>
        </div>
      ))}
      {out.resolved.length > 0 && (
        <div className="space-y-1">
          {out.resolved.map((r, i) => (
            <p key={i} className="text-xs text-emerald-500/70 flex gap-1.5 items-start">
              <span className="shrink-0 mt-0.5">✓</span><span>{r}</span>
            </p>
          ))}
        </div>
      )}
      {out.conflicts.length === 0 && out.resolved.length === 0 && (
        <p className="text-xs text-gray-600 italic">No conflicts detected.</p>
      )}
      <ToolTags tools={out.tool_used} />
    </div>
  );
}

// ── Iteration row ─────────────────────────────────────────────────────────────

function IterationRow({ it }: { it: Iteration }) {
  const [open, setOpen] = useState(false);
  const critic = it.agents.find(isCritic) as CriticOutput | undefined;
  const nUnresolved = critic?.unresolved?.length ?? 0;
  const nConflicts = critic?.conflicts?.length ?? 0;

  const agentLabel = (a: AgentOutput) => {
    if (isResearcher(a)) return { icon: "🔎", label: "Researcher", render: <ResearcherPanel out={a} /> };
    if (isPlanner(a)) return { icon: "📋", label: "Planner+Synthesizer", render: <PlannerPanel out={a} /> };
    if (isCritic(a)) return { icon: "⚖️", label: "Critic", render: <CriticPanel out={a} /> };
    return null;
  };

  return (
    <div className="border border-surface-600 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-surface-800 hover:bg-surface-700 transition-colors text-left"
      >
        <span className="flex items-center gap-2 text-gray-500 text-xs">
          <span>第 {it.iteration_number} 轮</span>
          <span className={`px-1.5 py-0.5 rounded-full text-[10px] ${
            nConflicts === 0 ? "bg-emerald-900/50 text-emerald-400"
            : nUnresolved === 0 ? "bg-yellow-900/50 text-yellow-400"
            : "bg-red-900/50 text-red-400"
          }`}>
            {nConflicts} 个冲突 · {nUnresolved} 未解决
          </span>
          {it.metadata.latency && (
            <span className="text-gray-700">{it.metadata.latency}</span>
          )}
        </span>
        <span className="text-gray-600 text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-4 py-3 bg-surface-900 space-y-4 animate-fade-in">
          {it.agents.map((a, i) => {
            const info = agentLabel(a);
            if (!info) return null;
            return (
              <div key={i}>
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                  <span>{info.icon}</span>{info.label}
                </p>
                {info.render}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Process trace (collapsible) ───────────────────────────────────────────────

function ProcessTrace({ data }: { data: ChatResult["structured_output"] }) {
  const [open, setOpen] = useState(false);
  const totalConflicts = data.iterations.reduce((s, it) => {
    const c = it.agents.find(isCritic) as CriticOutput | undefined;
    return s + (c?.conflicts?.length ?? 0);
  }, 0);

  return (
    <div className="mt-3 border border-surface-600 rounded-lg overflow-hidden text-sm">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 bg-surface-800 hover:bg-surface-700 transition-colors text-left"
      >
        <span className="flex items-center gap-2 text-gray-500 text-xs">
          <span>🔄</span>
          协商过程
          <span>({data.iterations.length} 轮 · {totalConflicts} 冲突已处理)</span>
        </span>
        <span className="text-gray-600 text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="px-4 py-3 bg-surface-900 space-y-3 animate-fade-in">
          {data.iterations.map((it) => (
            <IterationRow key={it.iteration_number} it={it} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Final answer card (always visible) ───────────────────────────────────────

function FinalAnswerCard({ data }: { data: ChatResult["structured_output"] }) {
  const hasFinal = !!data.final_choice?.trim();
  const hasReasoning = !!data.reasoning?.trim();
  const hasUnresolved = data.unresolved_issues?.length > 0;

  if (!hasFinal && !hasReasoning) return null;

  return (
    <div className="mt-3 rounded-xl border border-surface-500 overflow-hidden text-sm bg-surface-800">
      {/* Header */}
      <div className="flex items-center px-4 py-2.5 bg-surface-700 border-b border-surface-600">
        <span className="flex items-center gap-2 text-gray-300 font-medium text-xs">
          <span>✅</span> 最终方案
        </span>
      </div>

      <div className="px-4 py-4 space-y-4">
        {/* Final choice — full text */}
        {hasFinal && (
          <p className="text-gray-100 leading-relaxed whitespace-pre-wrap">
            {data.final_choice.trim()}
          </p>
        )}

        {/* Reasoning */}
        {hasReasoning && (
          <div>
            <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-2">采纳理由</p>
            <p className="text-sm text-gray-300 leading-relaxed">{data.reasoning.trim()}</p>
          </div>
        )}

        {/* Unresolved issues */}
        {hasUnresolved && (
          <div className="border-t border-surface-600 pt-3">
            <p className="text-xs text-yellow-600 font-medium uppercase tracking-wide mb-2">尚未解决</p>
            <ul className="space-y-1">
              {data.unresolved_issues.map((issue, i) => (
                <li key={i} className="flex gap-2 items-start text-xs text-yellow-500/70 leading-relaxed">
                  <span className="shrink-0 mt-0.5">⚠</span>
                  <span>{issue}</span>
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
        {/* Chat bubble */}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? "bg-indigo-600 text-white rounded-tr-sm"
              : "bg-surface-700 text-gray-400 rounded-tl-sm"
          }`}
        >
          {msg.text}
        </div>

        {/* Final answer card — always visible */}
        {!isUser && msg.structured && <FinalAnswerCard data={msg.structured} />}

        {/* Process trace — collapsible */}
        {!isUser && msg.structured && <ProcessTrace data={msg.structured} />}

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
