/**
 * AI "正在思考" 动画（水墨滴落）
 *
 * 三个朱红圆点交替缩放，模拟水墨滴落感。
 * 用于 ChatWindow 等待 AI 回复时的占位。
 */

export default function TypingDots() {
  return (
    <div className="flex items-center gap-2 px-4 py-3">
      <span
        className="w-2.5 h-2.5 rounded-full bg-zhu animate-ink-drop"
        style={{ animationDelay: "0s" }}
      />
      <span
        className="w-2.5 h-2.5 rounded-full bg-zhu animate-ink-drop"
        style={{ animationDelay: "0.16s" }}
      />
      <span
        className="w-2.5 h-2.5 rounded-full bg-zhu animate-ink-drop"
        style={{ animationDelay: "0.32s" }}
      />
      <span className="ml-2 text-xs text-mo-faint">正在思考</span>
    </div>
  );
}
