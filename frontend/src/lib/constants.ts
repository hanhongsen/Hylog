/**
 * 全局常量
 */

// 品牌
export const BRAND_NAME = "嗨，老己";
export const BRAND_NAME_EN = "Hylog";
export const BRAND_SLOGAN = "Hi + Log · 记录真实的自己";
export const BRAND_TAGLINE = "通过对话认识自己，匹配历史名人";

// OCEAN 五维的中文标签和颜色（用于雷达图）
export type OceanKey = "O" | "C" | "E" | "A" | "N";

export const OCEAN_LABELS: Record<OceanKey, string> = {
  O: "开放性",
  C: "责任心",
  E: "外向性",
  A: "宜人性",
  N: "神经质",
};

export const OCEAN_FULL_LABELS: Record<OceanKey, string> = {
  O: "O · 开放性",
  C: "C · 责任心",
  E: "E · 外向性",
  A: "A · 宜人性",
  N: "N · 神经质",
};

// 雷达图轴顺序（按开放性→责任心→外向性→宜人性→神经质的标准顺序）
export const OCEAN_KEYS: OceanKey[] = ["O", "C", "E", "A", "N"];

// OCEAN 五维分数区间对应的解读（用于展示）
export function getOceanLevel(score: number): { label: string; color: string } {
  if (score >= 0.7) return { label: "高", color: "#B22222" };
  if (score >= 0.55) return { label: "中高", color: "#C9A961" };
  if (score >= 0.45) return { label: "中", color: "#8B6F47" };
  if (score >= 0.3) return { label: "中低", color: "#6B8E5A" };
  return { label: "低", color: "#5C544A" };
}

// 答案长度上限（与后端 schemas.py 的 ReplyRequest 一致）
export const MAX_ANSWER_LENGTH = 100;

// localStorage 键
export const STORAGE_KEYS = {
  sessionId: "hylog:session_id",
} as const;

// 热度等级图标（emoji，每 20% 一档）
export function getHeatIcon(heatPercent: number): string {
  if (heatPercent < 20) return "🔥🔥🔥🔥🔥";
  if (heatPercent < 40) return "🔥🔥🔥";
  if (heatPercent < 60) return "🔥🔥";
  if (heatPercent < 80) return "🔥";
  return "❄️";
}
