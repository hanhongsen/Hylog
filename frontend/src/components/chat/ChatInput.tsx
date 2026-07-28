/**
 * 对话输入框
 *
 * 功能：
 * - 100 字硬上限（与后端 schemas.py 一致），实时计数
 * - 回车发送（Shift+回车换行）
 * - 发送按钮：空/超长/loading 时禁用
 * - 错误提示（422 校验错误等）
 *
 * 移动端：textarea 自动撑高（最多 4 行），发送按钮固定在右下
 */

import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { MAX_ANSWER_LENGTH } from "../../lib/constants";

type ChatInputProps = {
  /** 发送回调 */
  onSend: (answer: string) => void;
  /** 是否禁用（loading 时） */
  disabled?: boolean;
  /** 错误提示文本 */
  errorText?: string | null;
};

export default function ChatInput({ onSend, disabled, errorText }: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 自适应高度
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`; // 最多 4 行左右
  }, [value]);

  const tooLong = value.length > MAX_ANSWER_LENGTH;
  const empty = value.trim().length === 0;
  const canSend = !disabled && !empty && !tooLong;

  const handleSend = () => {
    if (!canSend) return;
    const trimmed = value.trim();
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 回车发送（Shift+回车换行，且不要在组合输入法时触发）
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-cha/20 bg-xuanzhi/90 backdrop-blur-sm">
      <div className="max-w-3xl mx-auto px-4 py-3">
        {/* 错误提示 */}
        {errorText && (
          <div className="mb-2 text-xs text-zhu-dark text-center">{errorText}</div>
        )}

        <div className="flex items-end gap-2">
          {/* 输入区 */}
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
              rows={1}
              maxLength={MAX_ANSWER_LENGTH + 50} // 允许略微超出用于显示红色计数
              placeholder={disabled ? "等待回复中..." : "在这里写下你的真实想法…"}
              className={`
                w-full resize-none px-4 py-3 pr-16 rounded-card
                bg-xuanzhi-card border transition-colors
                ${tooLong
                  ? "border-zhu/60 focus:border-zhu"
                  : "border-cha/30 focus:border-jin"
                }
                text-mo placeholder:text-mo-faint text-[15px] leading-relaxed
                outline-none scrollbar-ink
                disabled:opacity-60
              `}
            />
            {/* 字符计数 */}
            <span
              className={`
                absolute right-3 bottom-2.5 text-xs tabular-nums
                ${tooLong ? "text-zhu-dark font-medium" : "text-mo-faint"}
              `}
            >
              {value.length}/{MAX_ANSWER_LENGTH}
            </span>
          </div>

          {/* 发送按钮 */}
          <button
            onClick={handleSend}
            disabled={!canSend}
            className="btn-zhu px-5 py-3 flex-shrink-0"
            aria-label="发送"
          >
            <span className="font-serif">发送</span>
          </button>
        </div>

        {/* 提示语 */}
        <div className="mt-1.5 text-[11px] text-mo-faint text-center">
          回车发送 · Shift+回车换行 · 回答限 {MAX_ANSWER_LENGTH} 字内
        </div>
      </div>
    </div>
  );
}
