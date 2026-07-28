/**
 * API 数据类型定义
 *
 * 与后端 src/api/schemas.py 的 Pydantic 模型一一对应。
 * 修改时务必同步两边。
 */

/** OCEAN 五维分数（0~1） */
export type OceanVector = {
  O: number; // 开放性
  C: number; // 责任心
  E: number; // 外向性
  A: number; // 宜人性
  N: number; // 神经质
};

/** 对话进度（对应 ProgressInfo） */
export type ProgressInfo = {
  turn: number; // 有效对话轮次
  min_rounds: number; // 最小收敛轮次
  max_rounds: number; // 最大轮次上限
  dimension_coverage: string; // 维度覆盖率，如 "8/11"
  converged: boolean; // 是否已收敛
};

/** 人物基础信息（对应 CharacterBrief） */
export type CharacterBrief = {
  character_id: string;
  name: string;
  source: string; // 恒为 "历史"
  era: string; // 朝代
  description: string; // 生平简介
  image_path: string; // 人物图路径（当前通常为空，前端用占位图）
  ocean_vector: OceanVector; // 人物 OCEAN（用于结果页双雷达对比）
  tags: string[]; // 标签
  quote: string; // 语录
  personality_keyword: string; // 性格关键词
  classic_events: string; // 经典场景
  fun_facts: string; // 趣味冷知识
  advice: string; // 性格建议
  related_books: string; // 相关书籍
};

/** 匹配结果（对应 MatchResultInfo） */
export type MatchResultInfo = {
  character: CharacterBrief;
  similarity: number; // 0~1
  similarity_percent: number; // 0~100
  heat_level: string; // 如 "热门"
  heat_percent: number; // 热度百分比排名 0~100
  is_paid_locked: boolean; // 当前恒为 false（开发阶段全开放）
};

/** 对话响应（对应 ConversationResponse，POST /sessions 和 /reply 通用） */
export type ConversationResponse = {
  session_id: string;
  question: string | null; // 返回给用户的消息（开场白+问题/下一个问题/匹配结果）
  message: string | null; // 提示消息
  personality_state: OceanVector; // 当前 OCEAN 分数
  progress: ProgressInfo;
  is_finished: boolean;
  forced_finish: boolean; // 是否达到最大轮次强制结束
  result: MatchResultInfo | null; // 仅 is_finished=true 时有值
};

/** 会话状态（对应 SessionStateResponse，GET /state） */
export type SessionStateResponse = {
  session_id: string;
  personality_state: OceanVector;
  progress: ProgressInfo;
  is_finished: boolean;
  result: MatchResultInfo | null;
};

/** 单条对话消息（对应 MessageItem，GET /messages） */
export type MessageItem = {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  module: string | null; // 该问题所属维度
  ocean_delta: Partial<OceanVector> | null; // 该回答对 OCEAN 的影响（仅 user 消息）
  created_at: string | null; // ISO 时间
};

/** 对话历史列表（对应 MessageListResponse） */
export type MessageListResponse = {
  session_id: string;
  messages: MessageItem[];
  total: number;
};

/** 创建会话请求 */
export type CreateSessionRequest = {
  user_id?: string;
};

/** 提交回答请求 */
export type ReplyRequest = {
  answer: string;
};

/**
 * API 错误（fetch 失败或 HTTP 非 2xx 时抛出）
 *
 * 后端错误码语义（src/api/routes.py）：
 * - 404: 会话不存在
 * - 409: 测试未完成（查 result 时）
 * - 422: 参数校验失败（answer 空/超 100 字）
 * - 503: AI 服务不可用（智谱失败）
 * - 500: 服务器内部错误
 */
export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`[${status}] ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }

  /** 是否网络错误（fetch 抛出，无 status） */
  static isNetwork(err: unknown): boolean {
    return err instanceof TypeError && err.message.includes("fetch");
  }
}
