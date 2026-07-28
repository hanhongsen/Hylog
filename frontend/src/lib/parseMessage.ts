/**
 * 消息解析工具
 *
 * 后端的第一个 AI 消息格式是 "开场白\n\n---\n\n第一个问题"，
 * 前端需要拆成两条气泡（开场白样式更柔和，问题是正常的提问气泡）。
 */

/** 开场白与首个问题之间的分隔符（与 src/agent/graph.py:351 的 start() 一致） */
const OPENING_SEPARATOR = "\n\n---\n\n";

/**
 * 把首条 AI 消息拆为 [开场白, 第一个问题]
 *
 * 如果不含分隔符，返回 [原文]（兼容未来格式变化）
 */
export function splitOpeningMessage(content: string): string[] {
  if (content.includes(OPENING_SEPARATOR)) {
    return content.split(OPENING_SEPARATOR).map((s) => s.trim()).filter(Boolean);
  }
  return [content];
}

/**
 * 判断一段消息是否是开场白（启发式：含特定关键词）
 *
 * 用于历史消息渲染时，识别开场白并应用柔和样式。
 */
export function isOpeningMessage(content: string): boolean {
  return content.includes("嗨，我是 Hylog") || content.includes("欢迎来到一场关于");
}
