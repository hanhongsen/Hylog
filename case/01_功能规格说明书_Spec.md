# Hylog 功能规格说明书（Spec）

> **基准**：本文档基于代码实际行为（`src/`、`frontend/src/`）编写。代码与 README 存在差异时，**以代码为准**，差异处以 `⚠️` 标注。
> **版本**：对应 `main.py` v0.1.0 / commit `5d408cc`。

---

## 目录
1. [系统架构与组件](#1-系统架构与组件)
2. [API 接口契约](#2-api-接口契约)
3. [Agent 对话状态机](#3-agent-对话状态机)
4. [问题生成与维度选择](#4-问题生成与维度选择)
5. [人格建模算法](#5-人格建模算法)
6. [人物匹配](#6-人物匹配)
7. [数据库与持久化](#7-数据库与持久化)
8. [前端行为](#8-前端行为)
9. [配置与环境变量](#9-配置与环境变量)
10. [错误码与异常清单](#10-错误码与异常清单)

---

## 1. 系统架构与组件

```
前端 (React + Vite)
  └─ /api/* (Vite proxy → 8000)
后端 (FastAPI, src/api/)
  ├─ routes.py        5 个接口
  ├─ schemas.py       Pydantic 请求/响应模型
  └─ deps.py          依赖注入（DB / Mock 开关 / DB 路径）
Agent 调度 (src/agent/)
  ├─ graph.py         ConversationAgent 主控制器（编排 + 路由 + 持久化）
  ├─ state.py         AgentState 状态 + 阈值常量
  ├─ nodes.py         8 个流程节点 + 25 个 Mock 人物
  └─ router.py        ⚠️ 空文件（维度选择实际在 questions/generator.py）
人格建模 (src/personality/)
  ├─ model.py         OCEANVector / Dimension11Vector 数据结构
  ├─ updater.py       更新器（EWMA / 贝叶斯 / smooth_update / 收敛判断）
  └─ ocean.py         OCEAN 维度定义
问题模块 (src/questions/)
  ├─ generator.py     LLM 问题生成 + select_next_dimension 维度选择
  └─ modules/         11 个维度定义 + fallback 问题池
人物匹配 (src/matching/matcher.py)  余弦相似度 / 热度 / 结果封装
LLM (src/utils/llm.py)              智谱 SDK 封装 / 成本控制 / 重试
数据 (src/data/models.py)           7 张 SQLAlchemy 表
```

**8 个 Agent 节点**（`nodes.py`）：
`start_node` → `select_dimension_node` → `generate_question_node` → `process_answer_node` → `update_personality_node` → `check_convergence_node` → `match_character_node` → `build_result_node`

---

## 2. API 接口契约

### 2.1 健康检查
| 项 | 值 |
|----|----|
| Method/Path | `GET /` |
| 响应 | `{"status": "ok", "service": "Hylog API", "version": "0.1.0"}` |

### 2.2 POST `/api/sessions` — 创建会话
- **请求体**（可选）：`{"user_id": "string"}`，不传则用 `"anonymous-user"`。
- **行为**：创建 User（若不存在）→ 创建 Session 记录 → 初始化 AgentState → 输出开场白 + 首问题（首维度固定 `social`）→ 持久化 state_json。
- **响应**：`ConversationResponse`（见 §2.7）。
- **错误**：创建失败 → `500`。

### 2.3 POST `/api/sessions/{session_id}/reply` — 提交回答
- **请求体**：`{"answer": "string"}`，`answer` 长度 **1~100 字符**（Pydantic 强制，超出 `422`）。
- **行为**：从 DB restore 会话 → 执行 `reply()` 状态机 → 持久化 → 返回下一个问题或结果。
- **响应**：`ConversationResponse`。
- **错误**：会话不存在 `404`；LLM 失败抛到顶层 `503`；其他 `500`；长度违规 `422`。

### 2.4 GET `/api/sessions/{session_id}/state` — 查询进度
- **响应**：`SessionStateResponse`（personality_state + progress + is_finished + result）。
- **纯查询，不修改状态**。
- **错误**：会话不存在 `404`。

### 2.5 GET `/api/sessions/{session_id}/result` — 查询匹配结果
- **响应**：`MatchResultInfo`。
- **错误**：会话不存在 `404`；测试未完成（无 result）`409`。

### 2.6 GET `/api/sessions/{session_id}/messages` — 查询对话历史
- **响应**：`MessageListResponse`（按 `created_at` 正序的全部 user+assistant 消息）。
- **错误**：会话不存在 `404`。

### 2.7 核心响应结构
```jsonc
// ConversationResponse（start / reply 通用）
{
  "session_id": "uuid",
  "question": "开场白+问题 / 下一问题 / 结果消息 / null(已结束)",
  "message": "与 question 同值；已结束时为 '本次测试已完成'",
  "personality_state": {"O":0.5,"C":0.5,"E":0.5,"A":0.5,"N":0.5},
  "progress": {
    "turn": 0,                // 有效对话轮次
    "min_rounds": 15,
    "max_rounds": 30,
    "dimension_coverage": "0/11",
    "converged": false
  },
  "is_finished": false,
  "forced_finish": false,
  "result": null              // 仅 is_finished=true 时有值
}

// MatchResultInfo
{
  "character": { /* CharacterBrief：含 name/source/era/ocean_vector/tags/quote/... */ },
  "similarity": 0.92,         // 0~1 原始余弦相似度
  "similarity_percent": 92,   // 整数百分比
  "heat_level": "热门",        // 最热门/热门/中等/冷门/最冷门
  "heat_percent": 30,         // 热度排名百分位
  "is_paid_locked": false     // 当前始终 false（开发期全开放）
}
```

---

## 3. Agent 对话状态机

### 3.1 start()
`start_node`（设首维度=social，返回固定开场白）→ `generate_question_node` → 组合为 `开场白\n\n---\n\n首问题` → 入 history + 持久化。

### 3.2 reply(answer) 主流程
```
若 is_finished == True:
    → 返回 question=null, message="本次测试已完成"，不改任何状态（幂等）

① process_answer_node   → 用户回答入 history（turn_count 不变）
② update_personality_node（见 §5）：
   - 成功（success=True, skipped=False）→ 持久化 snapshot；turn_count += 1
   - skipped=True（无效回答）           → 返回 "引导语 + 同维度新问题"，turn_count 不变
   - success=False（LLM 异常）          → 选新维度 + 生成新问题，turn_count 不变
③ check_convergence_node（见 §5.3）
④ 路由：
   - converged == True            → _finish(forced=False)   【自然收敛】
   - turn_count >= MAX_ROUNDS(30) → _finish(forced=True)    【兜底强制】
   - 否则                          → select_dimension + generate_question，返回新问题
```

### 3.3 _finish(forced)
`match_character_node`（OCEAN 余弦，Top1）→ 若人物库为空 → 返回"人物库为空"消息，仍标记 is_finished。否则 `build_result_node` → 持久化 Result + 增加人物 match_count + 标记 Session.completed → 返回结束消息（含轮次、人物名、相似度%）。

### 3.4 阈值常量（`state.py`）
| 常量 | 值 | 含义 |
|------|----|------|
| `MIN_ROUNDS` | 15 | 收敛要求的最小总探索次数 |
| `MAX_ROUNDS` | 30 | 兜底最大轮次 |
| `MIN_EXPLORE_PER_DIMENSION` | 2 | ⚠️ 已废弃，收敛判断不再使用 |
| `MAX_UNCERTAINTY` | 0.3 | 收敛要求的 OCEAN 平均不确定性上限 |
| `OCEAN_SIMILARITY_REFERENCE` | 0.85 | 仅展示用，不做流程拦截 |

---

## 4. 问题生成与维度选择

### 4.1 问题生成（`generate_question_node`）
- **真实模式**：调 `chat(function="question_generation")`，解析 JSON `{"question": "..."}`；失败/解析失败 → fallback 到该维度 `get_random_question()`。
- **Mock 模式**：直接 `get_random_question()`，不调 LLM。
- 历史上下文：取最近 2 轮（4 条）配对为 `[{question, answer}]` 送入 prompt。

### 4.2 维度选择策略（`select_next_dimension`）
> ⚠️ **文档/实现差异**：README 描述"10% 概率随机探索"，**代码未实现**。实际策略为：

```
1. 存在不确定性 > 0.3 的维度 → 选不确定性最高的（平局取列表首个）
2. 否则 存在探索次数 < 2 的维度 → 选探索次数最少的
3. 否则 → 从 11 维中纯随机选一个
```

### 4.3 11 个问题维度
`social, emotion, decision, values, self_awareness, trust, stress, creativity, intimacy, achievement, life_attitude`

### 4.4 回答有效性判断（`analyze_personality`）
| 触发 | 结果 |
|------|------|
| 空回答 / `len > 100` | 返回 `skipped=True`（⚠️ 实际被 Pydantic 422 前置拦截，不会到此处） |
| LLM 判定为 irrelevant/refused/unclear/uncomfortable/negative | 返回 `skipped=True` + guidance 引导语 |
| 正常回答 | 返回 `{O,C,E,A,N}` delta，每个值被裁剪到 `[-0.08, 0.08]` |
| LLM JSON 解析失败 | 返回全 0 delta（**不抛异常**，当作有效但无影响） |
| LLM 调用异常（网络/限流/空响应，重试 5 次仍失败） | 抛 `LLMError`，被 nodes 捕获 → `success=False` 跳过本轮 |

---

## 5. 人格建模算法

### 5.1 数据结构
- **OCEANVector**：O/C/E/A/N 五维分数（默认 0.5）+ 各自不确定性（默认 1.0）+ 元数据。分数范围 `[0,1]`，构造时校验。
- **Dimension11Vector**：11 维分数 + 不确定性 + 探索次数，仅用于维度选择和展示，**不参与人物匹配**。

### 5.2 OCEAN 更新（`update_ocean` / `smooth_update`）
> ⚠️ **参数差异**：README 写 `MAX_CHANGE_PER_UPDATE=0.05`、`UNCERTAINTY_REDUCTION=0.1`；**代码实际**为下表。

| 参数 | 代码值 | 含义 |
|------|--------|------|
| `EWMA_LEARNING_RATE` | 0.2 | EWMA 权重（仅 bayesian 分支显式用 apply_ewma） |
| `MAX_CHANGE_PER_UPDATE` | **0.08** | 单次 delta 裁剪上限 |
| `MIN_UPDATE_THRESHOLD` | 0.01 | `|delta| < 此值` 不更新该维分数，也不降其不确定性 |
| `UNCERTAINTY_REDUCTION` | **0.2** | 每次有效信号降低的不确定性 |
| `BAYESIAN_PRIOR_VARIANCE` | 0.25 | 贝叶斯分支的先验方差 |

**smooth_update 规则**（默认 ewma 分支调用）：
1. `|delta| < 0.01` → 不变。
2. `delta` 裁剪到 `[-0.08, 0.08]`。
3. **边缘减速**（README 未提及）：若同向距 0 或 1 `< 0.2`，按 `headroom/0.2` 比例衰减 delta。
4. `new = current + delta`，再裁剪到 `[0,1]`。

**不确定性下降规则**：仅当 `|delta| >= 0.01` 的维度才降 0.2，否则该维不确定性不变。

### 5.3 收敛判断（`check_convergence`）
> ⚠️ **文档/实现差异（重大）**：README 列出 5 个收敛条件，**代码实际只有 2 个**。

**代码实际收敛条件（同时满足）**：
1. `sum(11 维探索次数) >= MIN_ROUNDS(15)`
2. `OCEAN 平均不确定性 < MAX_UNCERTAINTY(0.3)`

**README 声称但未实现**：
- ~~每个维度至少探索 2 次~~（`min_explore_per_dimension` 已废弃，参数保留但不生效）
- ~~OCEAN 连续 3 轮变化 < 0.05~~
- ~~11 维连续 3 轮变化 < 0.05~~
- ~~11 维平均不确定性 < 0.3~~（11 维仅展示，不参与判断）

**设计注释**：注释说明 11 维需 77 次探索才能收敛、远超 30 轮上限，故移除该条件。

### 5.4 Mock 模式合成 delta（`_generate_mock_ocean_delta`）
- 每维首次随机选方向签名 `+1/-1`，存入 `state.mock_ocean_signs` 并随 state_json 持久化（跨请求稳定）。
- 接近边缘（距 0/1 < 0.15）→ 签名清零，停止推动，仅微抖 `±0.01`。
- 推动幅度 `min(uniform(0.03,0.06), remaining*0.6+0.01)` + 噪声 `±0.015`。
- 目标：15~20 轮内 OCEAN 演化到 0.15~0.85 区间、不确定性均匀 < 0.1，触发自然收敛。

---

## 6. 人物匹配

### 6.1 相似度（`calculate_ocean_similarity`）
- OCEAN 5 维余弦相似度，结果裁剪到 `[0,1]`。
- **只用 OCEAN，不用 11 维**。

### 6.2 最佳匹配（`get_best_match`）
- 过滤 `is_active=True` → 算相似度 → 降序取 Top5 → 若 Top 部分有相同相似度 → **随机选一个**（保证每次可能不同）。

### 6.3 热度等级（`calculate_heat_level`）
| 百分位排名 | 等级名 |
|-----------|--------|
| `[0, 20)` | 最热门 |
| `[20, 40)` | 热门 |
| `[40, 60)` | 中等 |
| `[60, 80)` | 冷门 |
| `[80, 100]` | 最冷门 |
- 百分位按 `match_count` 降序排名计算；人物库为空 → 默认 `("中等", 50)`。

### 6.4 时代校验（`validate_era_for_history`）
历史人物 `era` 含"现代/民国/近代/当代/20世纪/21世纪"→ 无效；含枚举的清朝及之前朝代 → 有效。⚠️ **当前流程未调用此函数**（仅 `build_character_db.py` 构库时用），运行时不校验。

---

## 7. 数据库与持久化

### 7.1 表（7 张）
| 表 | 关键字段 | 用途 |
|----|---------|------|
| `users` | user_id(PK), nickname | 用户 |
| `sessions` | session_id(PK), user_id(FK), status, round_count, current_module, **state_json**, started_at, ended_at | 会话；**state_json 存完整 AgentState 快照** |
| `messages` | message_id(PK), session_id(FK), role, content, module, **ocean_delta** | 对话记录 |
| `personality_snapshots` | round, ocean_vector, ocean_uncertainty, dim11_* | 人格演化轨迹 |
| `results` | final_ocean, matched_character_*, matched_similarity | 最终结果 |
| `verification_codes` | target, code, expires_at | ⚠️ 表存在但认证功能未实现 |
| `characters` | name, era, ocean_vector, tags, quote, match_count, is_active | 人物库 |

### 7.2 持久化职责分离
- **state_json**（Session 表）：完整 AgentState 快照，每次 start/reply/_finish 后写，下次请求 `restore()` + `AgentState.from_dict()` 恢复。**高频读写，恢复核心**。
- **messages 表**：历史归档，供 GET /messages。
- **personality_snapshots 表**：每次有效更新后写一条，供演化可视化。

---

## 8. 前端行为

### 8.1 路由（`App.tsx`）
- `/` → Landing（开始按钮 → `startSession()`）
- `/chat` → Chat（无 sessionId 则重定向回 `/`）
- `/result` → Result

### 8.2 store（`store/session.ts`，zustand）
- `sessionId` 持久化到 `localStorage`，刷新可恢复。
- `startSession`：调 `createSession`，把 `开场白\n\n---\n\n首问题` 拆成两条气泡（opening + question）。
- `sendAnswer`：先乐观插入 user 消息 → 调 `reply` → 失败则撤回该消息。
- `resumeSession`：并行 `GET /state` + `GET /messages`；messages 失败不阻塞；首条 assistant 消息拆分。
- `resetSession`：清空 state + 删 localStorage。
- 错误统一转 `ApiError`，`status=0` 表示网络失败（后端未起）。

### 8.3 API client（`api/client.ts`）
- 统一相对路径 `/api/*`（Vite proxy 到 8000）。
- 非 2xx → `ApiError(status, detail)`；`status=0` → 网络错误提示"请确认后端已启动"。

---

## 9. 配置与环境变量

| 变量 | 默认 | 作用 | 读取位置 |
|------|------|------|---------|
| `ZHIPU_API_KEY` | — | 智谱 API Key（真实模式必填） | llm.py |
| `ZHIPU_MODEL` | `glm-4` | 模型名；推荐 `glm-4-flash`（免费） | llm.py |
| `USE_MOCK_AGENT` | `false` | true=Mock 模式（不调智谱） | deps.py `get_mock_flag` |
| `DB_PATH` | `hylog.db` | SQLite 路径 | deps.py / main.py |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | 后端监听 | main.py |
| `CORS_ORIGINS` | `localhost:8501,...` | ⚠️ 默认值是 Streamlit 端口，**React 5173 未包含**，需手动加 | api/main.py |
| `DAILY_COST_LIMIT` / `MONTHLY_COST_LIMIT` | `10` / `200` | 成本上限；flash 模型价格为 0，不会触限 | llm.py |
| `LLM_TEMPERATURE` / `LLM_MAX_TOKENS` / `LLM_TIMEOUT` | `0.7`/`2000`/`60` | 调用参数 | llm.py |

⚠️ `src/utils/config.py` 是空文件，配置实际散落在 `llm.py` 和 `deps.py`。

---

## 10. 错误码与异常清单

| HTTP | 触发条件 | 前端表现建议 |
|------|---------|-------------|
| `200` | 成功 | — |
| `422` | `answer` 长度不在 1~100；请求体格式错误 | "回答需 1~100 字" |
| `404` | session_id 不存在（reply/state/result/messages） | "会话不存在，请重新开始" |
| `409` | GET /result 但测试未完成 | 不应出现（前端按 is_finished 跳转） |
| `503` | reply 时 LLM 异常抛到顶层（理论上内部已 fallback，防御性） | "AI 服务暂时不可用，请稍后重试" |
| `500` | 创建/恢复/处理失败；全局兜底未捕获异常 | "服务器内部错误" |

**LLM 异常分类**（`classify_error`）：network / timeout / rate_limit（可重试，最多 5 次指数退避）/ api / param / cost_limit / json_parse / unknown（不重试）。

**全局兜底**：`api/main.py` 注册 `@app.exception_handler(Exception)` → 统一 500，不泄露堆栈。

---

## 附录 A：文档/实现差异汇总

| # | 项 | README 描述 | 代码实际 | 影响 |
|---|----|-----------|---------|------|
| D1 | 收敛条件 | 5 项（含每维≥2次、连续3轮稳定、11维不确定性） | 仅 2 项（总轮次≥15 + OCEAN 不确定性<0.3） | 收敛比文档描述更易达成 |
| D2 | MAX_CHANGE_PER_UPDATE | 0.05 | 0.08 | 单次分数变化更灵敏 |
| D3 | UNCERTAINTY_REDUCTION | 0.1 | 0.2 | 不确定性下降更快 |
| D4 | 边缘减速 | 未提及 | 存在（headroom<0.2 衰减） | 防止饱和到 0/1 |
| D5 | 维度随机探索 | 10% 概率 | 仅兜底全随机 | 策略不同 |
| D6 | tests/ 单测 | 暗示已覆盖 | 5 个文件全空 | 测试几乎缺失 |
| D7 | router.py | 提及为路由模块 | 空文件 | 无影响（逻辑在 generator.py） |
| D8 | config.py | 提及 | 空文件 | 配置散落在 llm.py/deps.py |
| D9 | CORS 默认 | — | 未含 React 5173 | 前端跨域需手动配 |
