/**
 * API 客户端
 *
 * 封装所有对后端的 HTTP 调用。
 * 设计要点：
 * - 统一错误处理：HTTP 非 2xx 抛 ApiError，网络失败抛 TypeError（fetch 原生行为）
 * - Vite dev server 通过 vite.config.ts 的 proxy 把 /api/* 转发到 8000，
 *   因此前端代码统一用相对路径 "/api/..."，避免硬编码 host 和 CORS 麻烦
 * - 生产环境（部署时）由 Nginx 或后端直接 serve 前端静态文件，同样用相对路径
 */

import type {
  CreateSessionRequest,
  ConversationResponse,
  MessageListResponse,
  ReplyRequest,
  SessionStateResponse,
  MatchResultInfo,
} from "./types";
import { ApiError } from "./types";

/**
 * 底层请求函数
 *
 * 参数:
 *   path: API 路径（以 /api/ 开头）
 *   options: fetch options
 *
 * 返回:
 *   解析后的 JSON
 *
 * 抛出:
 *   ApiError: HTTP 状态码非 2xx
 *   TypeError: 网络失败（fetch 原生）
 */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
  } catch (err) {
    // fetch 抛 TypeError 说明网络不通（后端没起、CORS 拒绝等）
    // 原样抛出，上层用 ApiError.isNetwork 判断
    throw err;
  }

  // 解析响应体（统一兼容空 body）
  let body: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    const detail =
      (body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : typeof body === "string"
          ? body
          : `请求失败`) || `请求失败`;
    throw new ApiError(res.status, detail);
  }

  return body as T;
}

// ============================================================
// 会话与对话接口（5 个核心接口）
// ============================================================

/**
 * 创建会话（POST /api/sessions）
 *
 * 返回开场白和第一个问题。
 */
export async function createSession(
  payload: CreateSessionRequest = {},
): Promise<ConversationResponse> {
  return request<ConversationResponse>("/api/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * 提交回答（POST /api/sessions/{id}/reply）
 *
 * 返回下一个问题，或测试完成时返回匹配结果。
 * 后端校验 answer 长度 1~100 字符，超长返回 422。
 */
export async function reply(
  sessionId: string,
  payload: ReplyRequest,
): Promise<ConversationResponse> {
  return request<ConversationResponse>(
    `/api/sessions/${encodeURIComponent(sessionId)}/reply`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

/**
 * 查询会话状态（GET /api/sessions/{id}/state）
 *
 * 返回当前 OCEAN 分数、进度、是否完成、结果。
 * 不修改任何状态，纯查询。
 */
export async function getSessionState(
  sessionId: string,
): Promise<SessionStateResponse> {
  return request<SessionStateResponse>(
    `/api/sessions/${encodeURIComponent(sessionId)}/state`,
  );
}

/**
 * 查询匹配结果（GET /api/sessions/{id}/result）
 *
 * 测试未完成时抛 ApiError(409)。
 */
export async function getResult(sessionId: string): Promise<MatchResultInfo> {
  return request<MatchResultInfo>(
    `/api/sessions/${encodeURIComponent(sessionId)}/result`,
  );
}

/**
 * 查询对话历史（GET /api/sessions/{id}/messages）
 *
 * 返回该会话的所有消息（用户回答 + AI 回复），按时间正序。
 */
export async function getMessages(sessionId: string): Promise<MessageListResponse> {
  return request<MessageListResponse>(
    `/api/sessions/${encodeURIComponent(sessionId)}/messages`,
  );
}
