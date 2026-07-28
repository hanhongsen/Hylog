/**
 * 单条聊天气泡
 *
 * 区分 user / assistant 两种样式：
 * - user：右对齐，朱红底白字（小一些）
 * - assistant：左对齐，宣纸卡片底（大一些），区分开场白/问题/结果/普通
 *
 * assistant 的开场白和结果消息样式更柔和、有装饰。
 */

import Seal from "../layout/Seal";
import type { ChatMessage } from "../../store/session";

type MessageBubbleProps = {
  message: ChatMessage;
};

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const kind = message.kind || "normal";

  if (isUser) {
    // ---------- 用户消息 ----------
    return (
      <div className="flex justify-end animate-fade-up">
        <div className="max-w-[80%] sm:max-w-[70%]">
          <div className="bg-zhu text-xuanzhi px-4 py-2.5 rounded-card rounded-tr-sm shadow-sm">
            <p className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">
              {message.content}
            </p>
          </div>
        </div>
      </div>
    );
  }

  // ---------- AI 消息 ----------
  // 开场白：宽一些，有印章装饰，文字稍柔
  // 结果：朱红边框强调
  // 普通/问题：标准卡片
  const isOpening = kind === "opening";
  const isResult = kind === "result";

  return (
    <div className="flex gap-3 animate-fade-up">
      {/* 左侧头像：印章 */}
      <div className="flex-shrink-0 mt-1">
        <Seal size={32} text="嗨" />
      </div>

      {/* 气泡 */}
      <div className={`max-w-[85%] sm:max-w-[75%] ${isOpening ? "w-full" : ""}`}>
        <div
          className={`
            px-4 py-3 rounded-card rounded-tl-sm shadow-sm
            ${isOpening
              ? "bg-xuanzhi-card/70 border border-jin/30"
              : isResult
                ? "bg-xuanzhi-card border border-zhu/40"
                : "bg-xuanzhi-card border border-cha/20"
            }
          `}
        >
          {/* 开场白：顶部标签 */}
          {isOpening && (
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-jin/20">
              <span className="text-xs font-serif text-jin tracking-widest">· 开 场 ·</span>
            </div>
          )}

          {/* 结果：顶部标签 */}
          {isResult && (
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-zhu/20">
              <span className="text-xs font-serif text-zhu tracking-widest">· 测试完成 ·</span>
            </div>
          )}

          {/* 内容 */}
          <p
            className={`
              text-[15px] leading-relaxed whitespace-pre-wrap break-words text-mo
              ${isOpening ? "font-serif" : ""}
            `}
          >
            {message.content}
          </p>
        </div>
      </div>
    </div>
  );
}
