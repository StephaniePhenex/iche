import React, { useState, useRef, useEffect } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleSend = () => {
    const msg = value.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-surface-600 bg-surface-900 px-4 py-4">
      <div className="max-w-3xl mx-auto flex items-end gap-3 bg-surface-700 border border-surface-500 rounded-xl px-4 py-3 focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent transition-all">
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="旅行、健康、写作、决策……什么都可以问（Enter 发送，Shift+Enter 换行）"
          className="flex-1 bg-transparent resize-none text-sm text-gray-100 placeholder-gray-500 focus:outline-none disabled:opacity-50 leading-relaxed"
        />

        <button
          onClick={handleSend}
          disabled={!value.trim() || disabled}
          className="shrink-0 w-8 h-8 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          title="Send (Enter)"
        >
          <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>

      <p className="text-center text-[11px] text-gray-600 mt-2">
        三位 AI 顾问协商 · Gemini 2.5 Flash
      </p>
    </div>
  );
}
