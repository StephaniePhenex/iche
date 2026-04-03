import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { chat } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { ChatMessage, TypingIndicator } from "../components/ChatMessage";
import { ChatInput } from "../components/ChatInput";
import type { Message } from "../components/ChatMessage";

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ onNewChat, onLogout }: { onNewChat: () => void; onLogout: () => void }) {
  return (
    <div className="hidden md:flex flex-col w-64 bg-surface-800 border-r border-surface-600 p-3">
      <button
        onClick={onNewChat}
        className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-700 text-sm text-gray-300 transition-colors mb-4 border border-surface-600"
      >
        <span>＋</span> New deliberation
      </button>

      <div className="flex-1">
        <p className="text-xs text-gray-600 uppercase tracking-wide px-3 mb-2">Agents</p>
        {[
          { icon: "🗂", label: "Rational Planner", sub: "结构化拆解 · 可行性" },
          { icon: "🔍", label: "Critical Analyst", sub: "风险 · 盲点 · 反驳" },
          { icon: "✨", label: "Creative Explorer", sub: "创意 · 替代方案" },
        ].map((a) => (
          <div key={a.label} className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm">
            <span className="text-base">{a.icon}</span>
            <div>
              <p className="text-gray-300 text-xs font-medium">{a.label}</p>
              <p className="text-gray-600 text-xs">{a.sub}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-surface-600 pt-3">
        <button
          onClick={onLogout}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg hover:bg-surface-700 text-sm text-gray-400 transition-colors"
        >
          <span>↩</span> Sign out
        </button>
      </div>
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  const examples = [
    { icon: "✈️", text: "帮我规划一个 5 天冲绳旅行行程，预算适中" },
    { icon: "🏃", text: "我想在 3 个月内减掉 10 斤，给我一个可执行计划" },
    { icon: "✍️", text: "我要写一篇关于孤独的短文，帮我找角度和结构" },
    { icon: "💼", text: "我纠结是继续现在的工作还是去创业，帮我分析" },
    { icon: "💊", text: "我总是睡眠质量差，有什么改善方法" },
    { icon: "🤝", text: "和朋友产生了矛盾，我该如何沟通修复关系" },
  ];
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4 gap-6">
      <div>
        <div className="text-5xl mb-3">⚡</div>
        <h2 className="text-xl font-semibold text-gray-200">三位 AI 顾问为你出谋划策</h2>
        <p className="text-sm text-gray-500 mt-1 max-w-sm">
          旅行 · 健康 · 写作 · 职业 · 生活决策……任何问题都可以问
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-2xl">
        {examples.map((ex) => (
          <div
            key={ex.text}
            className="card px-4 py-3 text-sm text-gray-400 text-left cursor-default hover:bg-surface-700 transition-colors rounded-xl flex gap-2.5 items-start"
          >
            <span className="text-base shrink-0">{ex.icon}</span>
            <span>{ex.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Chat page ─────────────────────────────────────────────────────────────────

let msgIdCounter = 0;
function nextId() {
  return `msg-${++msgIdCounter}`;
}

export function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [thinking, setThinking] = useState(false);
  const { logout } = useAuth();
  const navigate = useNavigate();
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinking, scrollToBottom]);

  const handleSend = useCallback(async (text: string) => {
    const userMsg: Message = {
      id: nextId(),
      role: "user",
      text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setThinking(true);

    try {
      const res = await chat(text);
      const agentMsg: Message = {
        id: nextId(),
        role: "agent",
        text: res.response,
        structured: res.structured_output,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch (err: unknown) {
      const errMsg: Message = {
        id: nextId(),
        role: "agent",
        text: `Error: ${err instanceof Error ? err.message : "Request failed"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setThinking(false);
    }
  }, []);

  const handleNewChat = useCallback(() => {
    setMessages([]);
  }, []);

  const handleLogout = useCallback(() => {
    logout();
    navigate("/login");
  }, [logout, navigate]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar onNewChat={handleNewChat} onLogout={handleLogout} />

      <div className="flex flex-col flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-600 bg-surface-900 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-lg">⚡</span>
            <span className="font-medium text-sm text-gray-200">Deliberation Engine</span>
            <span className="hidden sm:inline text-xs text-gray-600 ml-1">· 3 agents · up to 3 iterations</span>
          </div>
          <button
            onClick={handleLogout}
            className="md:hidden text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            Sign out
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto space-y-6">
            {messages.length === 0 && !thinking && <EmptyState />}

            {messages.map((msg) => (
              <ChatMessage key={msg.id} msg={msg} />
            ))}

            {thinking && <TypingIndicator />}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={thinking} />
      </div>
    </div>
  );
}
