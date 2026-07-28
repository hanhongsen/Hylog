/**
 * 会话状态管理（zustand）
 *
 * 集中管理整个对话流程的状态：
 * - 当前 session_id（持久化到 localStorage）
 * - 对话消息列表（user + assistant）
 * - 实时 OCEAN 分数（驱动雷达图）
 * - 进度（轮次、维度覆盖、是否收敛）
 * - 最终匹配结果
 * - 加载/错误状态
 *
 * 设计要点：
 * - 所有 API 调用都封装在 store 的 action 里，组件不直接调 api/client
 * - session_id 自动同步到 localStorage，支持页面刷新后恢复
 * - 错误以 ApiError 形式暴露，组件按 status 渲染不同提示
 */

import { create } from "zustand";
import * as api from "../api/client";
import type {
  ConversationResponse,
  MatchResultInfo,
  MessageItem,
  OceanVector,
  ProgressInfo,
} from "../api/types";
import { ApiError } from "../api/types";
import { STORAGE_KEYS } from "../lib/constants";

// ============================================================
// 消息类型（前端渲染用，比后端 MessageItem 多一个 kind 标记）
// ============================================================

export type ChatMessage = {
  id: string; // 前端生成的唯一 id
  role: "user" | "assistant";
  content: string;
  /** 消息子类型，决定气泡样式 */
  kind?: "opening" | "question" | "guidance" | "result" | "normal";
  /** 该问题所属维度（仅 assistant 有） */
  dimension?: string | null;
  createdAt?: string;
};

// ============================================================
// Store 类型定义
// ============================================================

type SessionStore = {
  // ---------- 基础状态 ----------
  sessionId: string | null;
  messages: ChatMessage[];
  ocean: OceanVector;
  progress: ProgressInfo | null;
  result: MatchResultInfo | null;
  isFinished: boolean;
  forcedFinish: boolean;

  // ---------- 加载与错误 ----------
  loading: boolean; // 是否正在请求后端
  error: ApiError | null; // 最近一次错误

  // ---------- Actions ----------
  /** 开始新会话（调 POST /sessions），返回是否成功 */
  startSession: () => Promise<boolean>;
  /** 提交回答（调 POST /reply），返回是否成功 */
  sendAnswer: (answer: string) => Promise<boolean>;
  /** 从后端恢复会话状态（GET /state + GET /messages） */
  resumeSession: (sessionId: string) => Promise<void>;
  /** 重置整个会话（清空状态，删除 localStorage） */
  resetSession: () => void;

  // ---------- 内部辅助 ----------
  _consumeResponse: (resp: ConversationResponse, opts?: { isStart?: boolean }) => void;
};

// ============================================================
// 默认 OCEAN（对话开始前）
// ============================================================

const DEFAULT_OCEAN: OceanVector = { O: 0.5, C: 0.5, E: 0.5, A: 0.5, N: 0.5 };

// ============================================================
// 生成唯一 id（前端用，无需密码学强度）
// ============================================================

let idCounter = 0;
function genId(): string {
  idCounter += 1;
  return `msg-${Date.now()}-${idCounter}`;
}

// ============================================================
// Store 实现
// ============================================================

export const useSessionStore = create<SessionStore>((set, get) => ({
  // ---------- 初始状态 ----------
  sessionId: typeof localStorage !== "undefined"
    ? localStorage.getItem(STORAGE_KEYS.sessionId)
    : null,
  messages: [],
  ocean: DEFAULT_OCEAN,
  progress: null,
  result: null,
  isFinished: false,
  forcedFinish: false,
  loading: false,
  error: null,

  // ============================================================
  // 开始新会话
  // ============================================================
  startSession: async () => {
    set({ loading: true, error: null });
    try {
      const resp = await api.createSession({});

      // 持久化 session_id
      localStorage.setItem(STORAGE_KEYS.sessionId, resp.session_id);

      // 把开场白 + 第一个问题拆成两条消息
      // 后端格式：resp.question = "开场白\n\n---\n\n第一个问题"
      const parts = resp.question
        ? splitForStore(resp.question)
        : [];

      const newMessages: ChatMessage[] = parts.map((content, idx) => ({
        id: genId(),
        role: "assistant" as const,
        content,
        kind: idx === 0 && parts.length > 1 ? "opening" : "question",
      }));

      set({
        sessionId: resp.session_id,
        messages: newMessages,
        ocean: resp.personality_state,
        progress: resp.progress,
        result: resp.result,
        isFinished: resp.is_finished,
        forcedFinish: resp.forced_finish,
        loading: false,
      });

      return true;
    } catch (err) {
      set({ loading: false, error: toApiError(err) });
      return false;
    }
  },

  // ============================================================
  // 提交回答
  // ============================================================
  sendAnswer: async (answer: string) => {
    const { sessionId } = get();
    if (!sessionId) {
      set({ error: new ApiError(0, "会话未开始，请返回首页重新开始") });
      return false;
    }

    // 先把用户回答加到消息列表（乐观更新）
    const userMsg: ChatMessage = {
      id: genId(),
      role: "user",
      content: answer,
    };
    set((state) => ({
      messages: [...state.messages, userMsg],
      loading: true,
      error: null,
    }));

    try {
      const resp = await api.reply(sessionId, { answer });
      get()._consumeResponse(resp);
      set({ loading: false });
      return true;
    } catch (err) {
      set({ loading: false, error: toApiError(err) });
      // 失败时把刚加的用户消息撤回，避免 UI 错乱
      set((state) => ({
        messages: state.messages.filter((m) => m.id !== userMsg.id),
      }));
      return false;
    }
  },

  // ============================================================
  // 从后端恢复会话（页面刷新时调用）
  // ============================================================
  resumeSession: async (sessionId: string) => {
    set({ loading: true, error: null });
    try {
      const [state, messageList] = await Promise.all([
        api.getSessionState(sessionId),
        api.getMessages(sessionId).catch(() => null), // messages 失败不阻塞
      ]);

      // 重建消息列表
      const rebuilt: ChatMessage[] = (messageList?.messages || [])
        .filter((m: MessageItem) => m.role === "assistant" || m.role === "user")
        .map((m: MessageItem, idx: number) => ({
          id: m.message_id || genId(),
          role: m.role,
          content: m.content,
          kind: idx === 0 && m.role === "assistant" ? "opening" : "normal",
          dimension: m.module,
          createdAt: m.created_at || undefined,
        }));

      set({
        sessionId,
        messages: rebuilt,
        ocean: state.personality_state,
        progress: state.progress,
        result: state.result,
        isFinished: state.is_finished,
        forcedFinish: false,
        loading: false,
      });
    } catch (err) {
      set({ loading: false, error: toApiError(err) });
    }
  },

  // ============================================================
  // 重置会话
  // ============================================================
  resetSession: () => {
    localStorage.removeItem(STORAGE_KEYS.sessionId);
    set({
      sessionId: null,
      messages: [],
      ocean: DEFAULT_OCEAN,
      progress: null,
      result: null,
      isFinished: false,
      forcedFinish: false,
      loading: false,
      error: null,
    });
  },

  // ============================================================
  // 内部：把 reply/start 的响应消费到 state
  // ============================================================
  _consumeResponse: (resp, opts = {}) => {
    // 更新 OCEAN、进度、结果
    const updates: Partial<SessionStore> = {
      ocean: resp.personality_state,
      progress: resp.progress,
      result: resp.result,
      isFinished: resp.is_finished,
      forcedFinish: resp.forced_finish,
    };

    if (resp.question) {
      // 如果是已结束会话的 reply，question 为 null，不会进入这里
      // 对于 start：question 是开场白+问题，但 start 走的是 startSession 自己处理
      // 对于 reply：question 是下一个问题（或最终结果消息）
      const aiMsg: ChatMessage = {
        id: genId(),
        role: "assistant",
        content: resp.question,
        kind: resp.is_finished ? "result" : "question",
      };
      updates.messages = [...get().messages, aiMsg];
    }

    set(updates);
  },
}));

// ============================================================
// 辅助函数
// ============================================================

/** 把任何错误转成 ApiError（便于组件按 status 判断） */
function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  if (ApiError.isNetwork(err)) {
    return new ApiError(0, "网络连接失败，请确认后端服务已启动（默认 http://127.0.0.1:8000）");
  }
  const message = err instanceof Error ? err.message : String(err);
  return new ApiError(0, message);
}

/** 把首条 AI 消息拆为 [开场白, 第一个问题] */
function splitForStore(content: string): string[] {
  const sep = "\n\n---\n\n";
  if (content.includes(sep)) {
    return content.split(sep).map((s) => s.trim()).filter(Boolean);
  }
  return [content];
}
