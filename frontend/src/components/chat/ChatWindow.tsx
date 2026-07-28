/**
 * 聊天窗口（消息流 + 输入框）
 *
 * 职责：
 * - 渲染所有消息气泡
 * - 滚动到底部（新消息/加载中时）
 * - 加载时显示 TypingDots 占位
 * - 接收用户输入并调用 store.sendAnswer
 * - 测试完成后显示"查看结果"按钮
 *
 * 不负责：状态管理（全部从 store 读）、侧栏（由 Chat 页面布局）
 */

import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import TypingDots from "./TypingDots";
import { useSessionStore } from "../../store/session";
import { useNavigate } from "react-router-dom";

export default function ChatWindow() {
  const navigate = useNavigate();
  const messages = useSessionStore((s) => s.messages);
  const loading = useSessionStore((s) => s.loading);
  const error = useSessionStore((s) => s.error);
  const isFinished = useSessionStore((s) => s.isFinished);
  const sendAnswer = useSessionStore((s) => s.sendAnswer);

  const scrollRef = useRef<HTMLDivElement>(null);

  // 新消息或 loading 变化时，滚动到底部
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages.length, loading]);

  return (
    <div className="flex flex-col h-full">
      {/* ---------- 消息流 ---------- */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto scrollbar-ink px-4 sm:px-6 py-6"
      >
        <div className="max-w-3xl mx-auto space-y-5">
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {/* AI 正在思考 */}
          {loading && (
            <div className="flex gap-3 animate-fade-up">
              <div className="flex-shrink-0 mt-1">
                <div className="w-8 h-8" />
              </div>
              <div className="bg-xuanzhi-card border border-cha/20 rounded-card rounded-tl-sm">
                <TypingDots />
              </div>
            </div>
          )}

          {/* 测试完成，查看结果 */}
          {isFinished && !loading && (
            <div className="pt-4 text-center animate-fade-up">
              <button
                onClick={() => navigate("/result")}
                className="btn-zhu text-base px-8 py-3"
              >
                查看你的画像 →
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ---------- 输入区 ---------- */}
      {!isFinished && (
        <ChatInput
          onSend={sendAnswer}
          disabled={loading}
          errorText={error?.detail || null}
        />
      )}
    </div>
  );
}
