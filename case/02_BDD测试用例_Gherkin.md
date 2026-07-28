# Hylog BDD 测试用例（Gherkin）

> **格式**：Feature / Scenario / Given-When-Then（Gherkin 语法）。
> **预期基准**：以**代码实际行为**为准（见 `01_功能规格说明书_Spec.md` 附录 A 的偏差表）。
> **标记**：`[Mock]` = 仅 Mock 模式可确定；`[Real]` = 真实模式；`[Both]` = 两种模式都适用；`[E2E]` = 前端端到端。
> **优先级**：P0 冒烟 / P1 核心 / P2 重要 / P3 补充。

---

## Feature 1: 健康检查与基础设施（P0）

```gherkin
Feature: 健康检查与基础设施
  作为运维/开发
  我希望确认后端服务存活且文档可用
  以便后续接口联调

  # 背景：服务已启动，未配置任何会话

  Scenario: 根路径健康检查 [Both]
    When 发起 GET /
    Then 响应状态码为 200
    And 响应体包含 "status": "ok"
    And 响应体包含 "service": "Hylog API"

  Scenario: Swagger 文档可访问 [Both]
    When 发起 GET /docs
    Then 响应状态码为 200
    And 响应体为 HTML（含 "Swagger UI"）

  Scenario: 启动时自动初始化数据库 [Both]
    Given 数据库文件不存在（首次启动）
    When 应用启动
    Then 数据库文件被创建
    And 7 张表（users/sessions/messages/personality_snapshots/results/verification_codes/characters）均存在
```

---

## Feature 2: 创建会话（P0）

```gherkin
Feature: 创建会话
  作为用户
  我希望开始一次新对话
  以便进入人格测试

  Background: 后端服务可用，Mock 模式开启
    Given 环境变量 USE_MOCK_AGENT=true

  Scenario: 不传 user_id 创建会话 [Mock]
    When 发起 POST /api/sessions，请求体为 {}
    Then 响应状态码为 200
    And 响应体 session_id 为合法 UUID
    And 响应体 question 不为空，且以开场白文案开头
    And 响应体 question 包含分隔符 "\n\n---\n\n" 后跟首个问题
    And 响应体 is_finished 为 false
    And 响应体 forced_finish 为 false
    And 响应体 result 为 null
    And 响应体 personality_state 为 {"O":0.5,"C":0.5,"E":0.5,"A":0.5,"N":0.5}
    And 响应体 progress.turn 为 0
    And 响应体 progress.min_rounds 为 15
    And 响应体 progress.max_rounds 为 30
    And 响应体 progress.dimension_coverage 为 "0/11"
    And 响应体 progress.converged 为 false

  Scenario: 传 user_id 创建会话 [Mock]
    When 发起 POST /api/sessions，请求体为 {"user_id":"user-001"}
    Then 响应状态码为 200
    And 数据库 users 表存在 user_id="user-001" 的记录

  Scenario: 首维度固定为 social [Mock]
    When 创建新会话
    Then AgentState.current_dimension == "social"
    And 数据库 sessions 表 current_module == "social"

  Scenario: 重复创建产生不同 session_id [Mock]
    When 连续发起两次 POST /api/sessions
    Then 两次返回的 session_id 不同

  Scenario: 创建会话后状态被持久化可恢复 [Mock]
    When 创建新会话，得到 session_id
    Then sessions 表对应记录的 state_json 不为空
    And state_json 含 use_mock=true 字段
```

---

## Feature 3: 对话推进——有效回答（P0）

```gherkin
Feature: 对话推进（有效回答）
  作为用户
  我希望每次提交有效回答后系统推进对话并更新人格
  以便逐步建立我的人格画像

  Background: 已创建 Mock 模式会话
    Given 一个已开始的 Mock 会话，session_id 已知

  Scenario: 有效回答推进轮次并返回下一问题 [Mock]
    Given 当前 turn 为 0
    When 发起 POST /reply，请求体为 {"answer":"我喜欢一个人安静地看书"}
    Then 响应状态码为 200
    And 响应体 progress.turn 为 1
    And 响应体 question 不为空（下一问题）
    And 响应体 is_finished 为 false
    And 响应体 result 为 null

  Scenario: 每轮至少更新 OCEAN 数据或保持边界值 [Mock]
    When 连续提交多轮有效回答
    Then 每轮响应 personality_state 的五个值均在 [0,1] 区间
    And 至少有 3 个维度最终偏离初始值 0.5 超过 0.05

  Scenario: OCEAN 单次变化不超过 0.08 上限 [Mock]
    When 提交一轮有效回答
    Then 与上一轮相比，每个 OCEAN 维度的变化幅度绝对值 <= 0.08（含边缘减速后）

  Scenario: 维度覆盖率随轮次增长 [Mock]
    When 连续提交 11 轮有效回答
    Then 响应体 progress.dimension_coverage 的分子逐轮非递减
    And 最终分子不超过 11

  Scenario: 用户回答被持久化到 messages 表 [Mock]
    When 提交回答 "测试回答内容XYZ"
    Then messages 表存在 role="user" 且 content="测试回答内容XYZ" 的记录
    And 该记录的 ocean_delta 字段不为空

  Scenario: 无效回答被跳过不增加轮次 [Mock]
    Given Mock 模式下 LLM 不会被调用
    When 提交一段任意文本（Mock 不做 skipped 判断）
    Then turn_count 仍然 +1（Mock 模式所有回答都视为有效）
    # 注：skipped 降级仅在真实模式由 LLM 判定，见 Feature 4

  Scenario: 已结束会话再次 reply 返回幂等结果 [Both]
    Given 会话 is_finished=true
    When 发起 POST /reply
    Then 响应状态码为 200
    And 响应体 question 为 null
    And 响应体 message 为 "本次测试已完成"
    And 响应体 progress.turn 与上次相同
```

---

## Feature 4: 无效回答与 LLM 降级（P2）

```gherkin
Feature: 无效回答与 LLM 降级
  作为系统
  我希望在用户回答无效或 LLM 失败时优雅降级
  以便对话不中断

  Background: 真实模式会话（USE_MOCK_AGENT=false）
    Given 一个已开始的真实模式会话

  Scenario: 回答长度 < 1 被前置拦截 [Real]
    When 发起 POST /reply，请求体为 {"answer":""}
    Then 响应状态码为 422
    And 不会调用人格分析 LLM

  Scenario: 回答长度 > 100 被前置拦截 [Real]
    When 发起 POST /reply，请求体为 {"answer":"<101字符>"}
    Then 响应状态码为 422

  Scenario: LLM 判定回答无关时返回引导语 [Real]
    # 模拟 analyze_personality 返回 {skipped:true, reason:"irrelevant", guidance:"..."}
    Given 人格分析返回 skipped=true
    When 提交回答
    Then 响应 question 包含引导语与新问题
    And 响应 progress.turn 不增加
    And 用户回答仍入 messages 表
    And 该消息 ocean_delta 全为 0

  Scenario: LLM 判定拒绝/不明确/不适/负面时跳过 [Real]
    Given 人格分析依次返回 reason=refused/unclear/uncomfortable/negative
    When 连续提交回答
    Then 每轮 turn 均不增加
    And 每轮都返回引导语 + 同维度新问题

  Scenario: LLM 调用异常时跳过本轮继续下一问题 [Real]
    # 模拟 analyze_personality 抛 LLMError（重试 5 次失败）
    Given 人格分析抛出 LLMError
    When 提交回答
    Then 响应状态码为 200（内部降级，非 503）
    And 响应 question 为新问题
    And 响应 progress.turn 不增加

  Scenario: LLM 返回非 JSON 时按全 0 delta 处理 [Real]
    Given 人格分析返回不可解析的文本
    Then 不抛异常
    And turn +1（视为有效但无影响）
    And OCEAN 分数无变化

  Scenario: 问题生成 LLM 失败时使用 fallback 问题 [Real]
    Given 问题生成 LLM 抛异常
    When 推进对话
    Then 仍返回非空问题（来自该维度 fallback 问题池）

  Scenario: LLM 异常透传到顶层时返回 503 [Real]
    # 防御性：若 reply 未捕获 LLMError
    Given reply 内部 LLM 调用未被 fallback 捕获并抛出 LLMError
    Then 路由层返回 503
    And detail 含 "AI 服务暂时不可用"
```

---

## Feature 5: 收敛判断（P1，核心算法）

> ⚠️ 以代码实际条件为准：① 总探索次数 ≥ 15 ② OCEAN 平均不确定性 < 0.3，两者同时满足。
> README 描述的"每维≥2次/连续3轮稳定/11维不确定性"**未实现**，下述用例验证它们**不生效**。

```gherkin
Feature: 收敛判断
  作为系统
  我希望在人格画像信息量足够时判定收敛
  以便进入人物匹配

  Scenario: 未达最小轮次不收敛 [Mock]
    Given 总探索次数 < 15
    And OCEAN 平均不确定性 < 0.3
    Then check_convergence 返回 False
    And 进度 progress.converged 为 false

  Scenario: 不确定性未达标不收敛 [Mock]
    Given 总探索次数 >= 15
    And OCEAN 平均不确定性 >= 0.3
    Then check_convergence 返回 False

  Scenario: 两个条件同时满足时收敛 [Mock]
    Given 总探索次数 >= 15
    And OCEAN 平均不确定性 < 0.3
    Then check_convergence 返回 True
    And 下一次 reply 触发 _finish（自然收敛，forced=false）

  Scenario Outline: 废弃条件不影响收敛 [Mock]
    # 验证 README 声称但代码未实现的条件
    Given 总探索次数 >= 15 且 OCEAN 不确定性 < 0.3
    And <废弃条件>
    Then 仍判定为收敛
    Examples:
      | 废弃条件 |
      | 存在某维度探索次数 < 2 |
      | OCEAN 连续 3 轮变化 > 0.05 |
      | 11 维平均不确定性 > 0.3 |

  Scenario: 仅降有效维度的不确定性 [Mock]
    Given 一轮更新中只有 O 维收到 |delta|>=0.01 的信号
    When update_ocean 执行
    Then O 维不确定性下降 0.2
    And 其他四维不确定性保持不变

  Scenario: 边缘减速防止饱和 [Mock]
    Given 某 OCEAN 维度分数 = 0.95
    When 收到一个 +0.08 的 delta
    Then 该维度新值 < 1.0（headroom/0.2 衰减生效）
    And 不会精确等于 1.0
```

---

## Feature 6: 兜底——最大轮次强制结束（P1）

```gherkin
Feature: 最大轮次兜底
  作为系统
  我希望在达到轮次上限时强制输出结果
  以防止对话无限进行

  Scenario: 达到 30 轮强制结束 [Mock]
    Given 已有效对话 29 轮仍未收敛
    When 提交第 30 个有效回答
    Then 响应 is_finished 为 true
    And 响应 forced_finish 为 true
    And 响应 result 不为 null

  Scenario: 收敛先于兜底触发时不算强制 [Mock]
    Given 第 20 轮时收敛条件已满足
    When 提交第 20 个回答
    Then is_finished 为 true
    And forced_finish 为 false

  Scenario: 强制结束后人物 match_count 自增 [Both]
    Given 强制结束匹配到人物 X
    Then characters 表 X 的 match_count += 1

  Scenario: 强制结束后 Session.status 变 completed [Both]
    Given 会话被强制结束
    Then sessions 表对应记录 status == "completed"
    And ended_at 不为空
```

---

## Feature 7: 人物匹配（P1，核心算法）

```gherkin
Feature: 人物匹配
  作为系统
  我希望用 OCEAN 余弦相似度匹配最像的历史人物
  以便给用户有意义的对照

  Scenario: 返回相似度最高的人物 [Both]
    Given 用户 OCEAN 向量 V
    And 人物库含人物 A/B/C
    When 触发匹配
    Then 返回的人物与 V 的余弦相似度 = max(sim(A), sim(B), sim(C))

  Scenario: 匹配只用 OCEAN 不用 11 维 [Both]
    Given 两个 OCEAN 相同但 11 维不同的用户
    When 分别匹配
    Then 返回相同的人物（或相似度相同的等价结果）

  Scenario: 相同相似度时随机选择 [Both]
    Given Top 结果中有 2 个人物相似度完全相等
    When 多次触发匹配
    Then 至少有一次返回不同人物（随机性）

  Scenario: 人物库为空时返回 None [Both]
    Given 人物库为空列表
    When 触发匹配
    Then match_character_node 返回 None
    And _finish 返回 "人物库暂时为空" 消息
    And is_finished 仍置为 true

  Scenario: 仅匹配 is_active=true 的人物 [Both]
    Given 人物库含 1 个 active 和 1 个 inactive
    When 触发匹配
    Then inactive 人物不在候选中

  Scenario: 热度等级按 match_count 排名 [Both]
    Given 人物库 match_count 排名后该人物位于前 20%
    Then MatchResult.heat_level == "最热门"
    And heat_percent < 20

  Scenario Outline: 热度等级区间正确 [Both]
    Given 人物 match_count 排名百分位为 <percent>
    Then heat_level == "<level>"
    Examples:
      | percent | level   |
      | 10      | 最热门  |
      | 30      | 热门    |
      | 50      | 中等    |
      | 70      | 冷门    |
      | 90      | 最冷门  |

  Scenario: 相似度百分比取整 [Both]
    Given 余弦相似度 = 0.859
    Then similarity_percent == 85

  Scenario: 结束消息含轮次、人物、相似度 [Both]
    When 自然收敛结束
    Then 响应 question 文本包含轮次数
    And 包含人物名称
    And 包含相似度百分比

  Scenario: 付费字段当前全部返回 [Both]
    Given 任一已结束会话
    When GET /result
    Then is_paid_locked == false
    And character.tags / quote / advice / related_books 等字段存在（可为空字符串/空数组）
```

---

## Feature 8: 只读查询接口（P1）

```gherkin
Feature: 只读查询接口
  作为前端
  我希望查询进度、结果、历史
  以便刷新恢复与展示

  Background: 存在一个已开始若干轮的会话

  Scenario: GET /state 返回实时人格与进度 [Both]
    When 发起 GET /api/sessions/{id}/state
    Then 状态码 200
    And personality_state 与最新 reply 一致
    And progress.turn 与最新 reply 一致
    And 不修改任何后端状态

  Scenario: GET /messages 按时间正序 [Both]
    When 发起 GET /api/sessions/{id}/messages
    Then 状态码 200
    And messages 按 created_at 升序
    And user 与 assistant 消息交替出现

  Scenario: GET /messages 的 user 消息含 ocean_delta [Both]
    Then 每条 role=user 消息的 ocean_delta 不为 null（有效回答）

  Scenario: GET /result 完成时返回结果 [Both]
    Given 会话 is_finished=true
    When 发起 GET /api/sessions/{id}/result
    Then 状态码 200
    And 响应体为 MatchResultInfo

  Scenario: 连续多次 GET /state 不改变进度 [Both]
    When 连续发起 3 次 GET /state
    Then 三次返回的 progress.turn 完全相同
    And 三次返回的 personality_state 完全相同
```

---

## Feature 9: 错误处理与状态码（P1）

```gherkin
Feature: 错误处理与状态码

  Scenario: 不存在的 session_id 调 reply 返回 404 [Both]
    When 发起 POST /api/sessions/<不存在>/reply
    Then 状态码 404
    And detail 含 "会话不存在"

  Scenario: 不存在的 session_id 调 state 返回 404 [Both]
    When 发起 GET /api/sessions/<不存在>/state
    Then 状态码 404

  Scenario: 未完成时 GET /result 返回 409 [Both]
    Given 会话 is_finished=false
    When 发起 GET /api/sessions/{id}/result
    Then 状态码 409
    And detail 含 "尚未完成"

  Scenario: reply 缺少 answer 字段返回 422 [Both]
    When 发起 POST /reply，请求体为 {}
    Then 状态码 422

  Scenario: answer 为非字符串类型返回 422 [Both]
    When 发起 POST /reply，请求体为 {"answer": 123}
    Then 状态码 422

  Scenario: 未捕获异常统一返回 500 [Both]
    Given 触发一个未被业务层捕获的异常
    Then 状态码 500
    And 响应体含 error_code="INTERNAL_ERROR"
    And 响应体不包含 Python 堆栈信息

  Scenario: 前端跨域请求被 CORS 允许 [E2E]
    Given CORS_ORIGINS 已包含 http://localhost:5173
    When 从 5173 发起 OPTIONS 预检
    Then 响应含正确的 CORS 头
    # ⚠️ 默认配置未含 5173，需手动配置，否则此用例失败
```

---

## Feature 10: Mock 模式完整闭环（P0，集成）

```gherkin
Feature: Mock 模式完整闭环
  作为前端/测试开发
  我希望不消耗智谱额度即可跑通完整流程
  以便独立验证 API 链路

  Background:
    Given USE_MOCK_AGENT=true
    And 使用临时数据库（不影响 hylog.db）

  Scenario: Mock 模式全程不调用智谱 [Mock]
    When 创建会话并连续 reply 直到完成
    Then analyze_personality 调用次数 == 0
    And chat() 调用次数 == 0

  Scenario: Mock 模式问题来自 fallback 池 [Mock]
    When 创建会话
    Then 返回的首问题来自 social 维度 questions 列表
    And 不经过 LLM

  Scenario: Mock 模式 OCEAN 真实演化不漂移 [Mock]
    When 用固定回答序列连续 reply
    Then 同一 session 多次请求间 OCEAN 单调演化（方向签名持久化）
    And 跨重启 restore 后演化方向一致

  Scenario: Mock 模式触发自然收敛 [Mock]
    When 连续 reply 15~20 轮
    Then is_finished 变为 true
    And forced_finish 为 false（自然收敛，非兜底）

  Scenario: Mock 模式最终返回合法匹配结果 [Mock]
    Given 会话已完成
    Then result.character.name 是 25 个内置 Mock 人物之一
    And result.similarity 在 (0,1] 区间
    And result.similarity_percent 在 [0,100] 区间

  Scenario: Mock 模式只读接口全部可用 [Mock]
    Given Mock 会话已完成
    Then GET /state 返回 is_finished=true 且 result 非空
    And GET /result 返回 200
    And GET /messages 返回 total > 0

  Scenario: Mock 模式 30 轮内必定结束 [Mock]
    When 最多连续 reply 30 轮
    Then 一定在某轮触发 is_finished=true（收敛或兜底）
    # 防止死循环
```

---

## Feature 11: 会话持久化与恢复（P1，集成）

```gherkin
Feature: 会话持久化与恢复
  作为 HTTP 无状态架构
  我希望每次请求都能从数据库恢复完整状态
  以便多轮对话正确延续

  Scenario: 每次 reply 都从 state_json 恢复 [Both]
    Given 会话已进行 5 轮
    When 提交第 6 个回答
    Then 恢复出的 AgentState.turn_count == 5
    And ocean_vector 与第 5 轮结束时一致

  Scenario: OCEAN 向量可正确序列化/反序列化 [Both]
    Given 一个 OCEANVector 实例
    When to_dict 后 from_dict
    Then 五维分数和不确定性完全相等

  Scenario: MatchResult 可正确反序列化含付费字段 [Both]
    Given 一个含付费字段的 MatchResult
    When to_dict(include_paid=True) 后 _match_result_from_dict
    Then 所有付费字段（tags/quote/advice/...）完整保留

  Scenario: restore 不存在的会话抛 ValueError [Both]
    When restore(session_id="<不存在>")
    Then 抛出 ValueError
    And 路由层映射为 404

  Scenario: restore state_json 为空抛 RuntimeError [Both]
    Given sessions 表某记录 state_json 为 NULL
    When restore 该 session_id
    Then 抛出 RuntimeError
    And 路由层映射为 500

  Scenario: 刷新页面后前端能恢复对话 [E2E]
    Given 浏览器已进行 5 轮对话
    When 用户刷新页面
    Then 前端从 localStorage 读 session_id
    And 调用 resumeSession 恢复 messages 与 OCEAN
    And 首条 AI 消息被拆分为 [开场白, 首问题] 两个气泡
```

---

## Feature 12: 前端端到端用户旅程（P1，E2E）

```gherkin
Feature: 前端端到端用户旅程
  作为真实用户
  我希望通过浏览器完成完整测试
  以便看到与我匹配的历史人物

  Scenario: 完整主路径 [E2E]
    Given 后端已启动且 Mock 模式开启
    And 前端 dev server 已启动
    When 用户打开 http://localhost:5173
    Then 进入 Landing 页，显示"开始"按钮
    When 点击开始
    Then 跳转到 /chat
    And 看到开场白气泡 + 首个问题气泡
    And 侧栏显示 OCEAN 雷达图（初始为正五边形）和进度面板

  Scenario: 对话中雷达图实时更新 [E2E]
    When 用户输入回答并提交
    Then 用户气泡立即出现（乐观更新）
    And AI 回复气泡出现
    And 雷达图形状发生变化（OCEAN 演化）
    And 进度面板的轮次 +1

  Scenario: 回答发送失败时撤回用户气泡 [E2E]
    Given 后端服务已停止
    When 用户提交回答
    Then 出现网络错误提示
    And 刚加入的用户气泡被移除

  Scenario: 收敛后跳转结果页 [E2E]
    When 完成足量对话触发 is_finished
    Then 跳转到 /result
    And 结果页显示匹配人物名称、相似度、关键词、标签、语录

  Scenario: 强制结束也在结果页正常展示 [E2E]
    Given 会话因达到 30 轮强制结束
    Then 结果页仍正常显示匹配人物（forced 标记可能提示）

  Scenario: 重新开始清空状态 [E2E]
    Given 用户在 /chat 页
    When 点击"重新开始"并确认
    Then localStorage 的 sessionId 被删除
    And 跳转回 /
    And store 状态重置为初始

  Scenario: 直接访问 /chat 无 session 时回首页 [E2E]
    Given 未开始会话（无 localStorage）
    When 直接访问 /chat
    Then 重定向到 /

  Scenario: 移动端侧栏抽屉 [E2E]
    Given 视口为移动端宽度
    When 点击"画像"按钮
    Then 侧栏以抽屉形式展开
    And 显示雷达图与进度
    When 点击遮罩或关闭按钮
    Then 抽屉收起

  Scenario: CORS 未配置时前端报错 [E2E]
    Given CORS_ORIGINS 未包含 5173
    When 前端请求 /api
    Then 浏览器控制台报 CORS 错误
    # ⚠️ 此为配置缺陷用例，提醒部署
```

---

## 附录：用例统计

| Feature | 场景数 | 覆盖模块 | 关键优先级 |
|---------|--------|---------|-----------|
| F1 健康检查 | 3 | 基础设施 | P0 |
| F2 创建会话 | 5 | API/Agent | P0 |
| F3 对话推进 | 7 | Agent/人格 | P0 |
| F4 无效降级 | 8 | LLM/异常 | P2 |
| F5 收敛判断 | 6 | 算法 | P1 |
| F6 兜底 | 4 | Agent | P1 |
| F7 人物匹配 | 10 | 匹配 | P1 |
| F8 只读接口 | 4 | API | P1 |
| F9 错误码 | 7 | 契约 | P1 |
| F10 Mock 闭环 | 7 | 集成 | P0 |
| F11 持久化 | 6 | 集成 | P1 |
| F12 前端 E2E | 9 | 前端 | P1 |
| **合计** | **76** | — | — |

> 可执行化映射（pytest + Playwright 实现）见 `03_测试矩阵与执行指南.md`。
