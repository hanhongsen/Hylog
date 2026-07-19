# Hylog 项目状态总结

---

## 项目概述

Hylog 是一个基于大语言模型的 AI Agent 系统，通过自然对话动态建模用户人格，最终匹配到中国历史上的著名人物（清朝或之前）。

**核心架构**：
- 11 维问题模块（探测手段）→ OCEAN 5 维人格向量（存储状态）→ 人物匹配（输出层）

---

## 一、已完成的任务

### 1. 人格建模模块 (`src/personality/`)

| 文件 | 状态 | 功能 | 代码行数 |
|------|------|------|----------|
| [ocean.py](file:///d:/Hylog/src/personality/ocean.py) | ✅ 完成 | OCEAN 五维人格模型定义，包含维度信息、子维度、高低分特征、验证函数等 | ~290 行 |
| [model.py](file:///d:/Hylog/src/personality/model.py) | ✅ 完成 | 人格向量数据结构定义，包含 `OCEANVector` 和 `Dimension11Vector` 数据类，支持序列化/反序列化 | ~590 行 |
| [updater.py](file:///d:/Hylog/src/personality/updater.py) | ✅ 完成 | 人格更新器，实现 EWMA 算法，支持平滑更新、不确定性管理、收敛判断等 | ~420 行 |
| [__init__.py](file:///d:/Hylog/src/personality/__init__.py) | ✅ 完成 | 模块导出，提供便捷导入接口 | ~40 行 |

**核心功能**：
- OCEAN 五维分数定义（O/C/E/A/N，范围 0.0~1.0，精度 0.01）
- 11 维问题维度定义（社交互动、情绪体验、决策风格等）
- 11 维到 OCEAN 的映射关系
- EWMA 人格更新算法（学习率 0.2，最大变化幅度 0.05）
- 人格收敛判断机制

---

### 2. 问题模块系统 (`src/questions/`)

| 文件 | 状态 | 功能 | 代码行数 |
|------|------|------|----------|
| [generator.py](file:///d:/Hylog/src/questions/generator.py) | ✅ 完成 | 问题生成器核心逻辑，包含 Prompt 构建、结果解析、维度选择策略 | ~200 行 |
| [__init__.py](file:///d:/Hylog/src/questions/__init__.py) | ✅ 完成 | 模块导出，提供便捷函数 | ~80 行 |

#### 11 个维度定义文件

| 文件 | 维度名称 | 映射 OCEAN | 问题数量 |
|------|----------|------------|----------|
| [social.py](file:///d:/Hylog/src/questions/modules/social.py) | 社交互动 | E（外向性） | 8 个 |
| [emotion.py](file:///d:/Hylog/src/questions/modules/emotion.py) | 情绪体验 | N（神经质） | 8 个 |
| [decision.py](file:///d:/Hylog/src/questions/modules/decision.py) | 决策风格 | C、O | 8 个 |
| [values.py](file:///d:/Hylog/src/questions/modules/values.py) | 价值取向 | O、A | 8 个 |
| [self_awareness.py](file:///d:/Hylog/src/questions/modules/self_awareness.py) | 自我认知 | N（神经质） | 8 个 |
| [trust.py](file:///d:/Hylog/src/questions/modules/trust.py) | 人际信任 | A（宜人性） | 8 个 |
| [stress.py](file:///d:/Hylog/src/questions/modules/stress.py) | 压力应对 | N、C | 8 个 |
| [creativity.py](file:///d:/Hylog/src/questions/modules/creativity.py) | 创造探索 | O（开放性） | 8 个 |
| [achievement.py](file:///d:/Hylog/src/questions/modules/achievement.py) | 成就动机 | C（责任心） | 8 个 |
| [life_attitude.py](file:///d:/Hylog/src/questions/modules/life_attitude.py) | 生活态度 | N、E | 8 个 |
| [intimacy.py](file:///d:/Hylog/src/questions/modules/intimacy.py) | 亲密关系 | A、N | 8 个 |

**核心功能**：
- 每个维度包含 8 个经典问题（1+x 模式：先问一个可准确回答的问题，再加一个开放性问题）
- 维度选择策略：高不确定性维度优先 → 探索次数少的维度优先 → 随机选择（10% 概率）
- 三级解析策略：直接解析 JSON → 正则提取 → fallback
- 支持 AI 动态生成问题

---

### 3. LLM 调用模块 (`src/utils/llm.py`)

| 文件 | 状态 | 功能 | 代码行数 |
|------|------|------|----------|
| [llm.py](file:///d:/Hylog/src/utils/llm.py) | ✅ 完成 | 完整的 LLM 调用模块，包含配置管理、成本控制、日志记录、错误处理等 | ~1700 行 |

**核心功能**：
- **配置管理**：支持从 `.env` 文件加载配置，支持智谱 AI、DeepSeek、OpenAI 切换
- **成本控制**：按功能分类统计（问题生成、人格分析、结果解释等），设置每日/每月上限，数据持久化到文件
- **日志记录**：请求日志、响应日志、错误日志，同时输出到控制台和文件，保留 30 天
- **错误处理**：网络错误、API 错误、超时错误、限流错误、JSON 解析错误等，支持重试机制（5 次递增间隔）
- **Token 计数**：使用 tiktoken 计算 token 数量
- **流式输出**：支持流式对话，提升用户体验
- **人格分析**：`analyze_personality()` 方法，分析用户回答并输出 OCEAN 分数，支持跳过无效回答
- **人物分析**：`analyze_character()` 方法，使用联网搜索分析人物，输出 OCEAN 分数和所有展示内容
- **图片生成**：`generate_character_image()` 方法，调用智谱 CogView API 生成人物图片并保存到本地

**便捷函数**：
- `chat()` / `chat_stream()`：对话补全
- `analyze_personality()`：人格分析
- `analyze_character()`：人物分析（联网搜索）
- `generate_character_image()`：图片生成

---

### 4. 数据库模型 (`src/data/models.py`)

| 文件 | 状态 | 功能 | 代码行数 |
|------|------|------|----------|
| [models.py](file:///d:/Hylog/src/data/models.py) | ✅ 完成 | 7 张表的 ORM 定义，使用 SQLAlchemy | ~350 行 |
| [__init__.py](file:///d:/Hylog/src/data/__init__.py) | ✅ 完成 | 数据库连接和初始化 | ~90 行 |

**数据库表结构**：

| 表名 | 字段 | 说明 |
|------|------|------|
| **User** | user_id, phone, password_hash, nickname, avatar, register_time, last_login_time, is_active | 用户基本信息 |
| **Session** | session_id, user_id, start_time, end_time, status, personality_snapshot | 会话信息 |
| **Message** | message_id, session_id, role, content, timestamp, dimension_id | 对话记录 |
| **PersonalitySnapshot** | snapshot_id, session_id, ocean_vector, dim11_vector, uncertainty, timestamp | 人格快照 |
| **Result** | result_id, session_id, character_id, similarity, heat_level, heat_percent, created_at | 匹配结果 |
| **VerificationCode** | code_id, phone, code, expire_time, used | 验证码 |
| **Character** | character_id, name, source, era, description, ocean_vector, image_path, tags, quote, personality_keyword, classic_events, fun_facts, advice, related_books, match_count, is_active, created_at, updated_at | 人物库 |

---

### 5. 人物匹配模块 (`src/matching/`)

| 文件 | 状态 | 功能 | 代码行数 |
|------|------|------|----------|
| [matcher.py](file:///d:/Hylog/src/matching/matcher.py) | ✅ 完成 | 人物数据结构、余弦相似度计算、匹配逻辑、热度等级计算 | ~484 行 |
| [__init__.py](file:///d:/Hylog/src/matching/__init__.py) | ✅ 完成 | 模块导出 | ~120 行 |

**核心功能**：
- `CharacterData` 数据类：人物数据结构，与数据库对应
- `cosine_similarity()`：余弦相似度计算
- `calculate_ocean_similarity()`：用户与人物 OCEAN 向量相似度计算
- `match_character()`：匹配用户与人物库，返回 Top-K 结果
- `get_best_match()`：获取最佳匹配，相似度相同时随机选择
- `calculate_heat_level()`：计算热度等级（5 个等级：最热门、热门、中等、冷门、最冷门）和百分比排名
- `validate_source()`：验证来源类型（当前只支持"历史"）
- `validate_era_for_history()`：验证历史人物时代（清朝或之前）

---

### 6. 人物库预处理脚本 (`scripts/build_character_db.py`)

| 文件 | 状态 | 功能 | 代码行数 |
|------|------|------|----------|
| [build_character_db.py](file:///d:/Hylog/scripts/build_character_db.py) | ✅ 完成 | 批量构建人物库数据 | ~200 行 |

**核心功能**：
- 读取人物名单文件 `data/characters/character_list.json`
- 调用 AI 联网搜索分析每个人物，获取 OCEAN 分数和展示内容
- 调用 AI 生成人物图片，保存到 `data/characters/images/`
- 将所有数据存入数据库
- 支持跳过已存在的人物
- 进度显示和错误处理

---

### 7. 人物名单文件 (`data/characters/character_list.json`)

| 文件 | 状态 | 内容 |
|------|------|------|
| [character_list.json](file:///d:/Hylog/data/characters/character_list.json) | ✅ 完成 | 7 个示例人物：诸葛亮、曹操、李白、苏轼、林黛玉、贾宝玉、孙悟空 |

---

### 8. 配置文件

| 文件 | 状态 | 内容 |
|------|------|------|
| [.env.example](file:///d:/Hylog/.env.example) | ✅ 完成 | 配置文件模板，包含智谱 AI、DeepSeek、OpenAI 的 API 配置 |
| [.env](file:///d:/Hylog/.env) | ✅ 完成 | 实际配置文件（用户需填写 API Key） |
| [.gitignore](file:///d:/Hylog/.gitignore) | ✅ 完成 | Git 忽略配置，保护敏感信息 |

---

### 9. 测试文件

| 文件 | 状态 | 内容 |
|------|------|------|
| [test_llm.py](file:///d:/Hylog/test_llm.py) | ✅ 完成 | LLM 调用测试 |
| [tests/test_personality.py](file:///d:/Hylog/tests/test_personality.py) | ✅ 完成 | 人格模块测试 |
| [tests/test_questions.py](file:///d:/Hylog/tests/test_questions.py) | ✅ 完成 | 问题模块测试 |
| [tests/test_matching.py](file:///d:/Hylog/tests/test_matching.py) | ✅ 完成 | 匹配模块测试 |
| [tests/test_agent.py](file:///d:/Hylog/tests/test_agent.py) | ✅ 完成 | Agent 模块测试 |

---

## 二、待完成的任务

### 1. Agent 调度模块 (`src/agent/`)

**状态**：❌ 未实现（空文件）

**需要实现的功能**：

#### 1.1 状态管理 (`state.py`)

定义 Agent 的状态数据结构：
- 当前人格状态（OCEAN 向量、11 维数据）
- 对话历史（最近 N 轮）
- 当前维度探索次数
- 收敛状态
- 匹配结果

#### 1.2 节点定义 (`nodes.py`)

定义对话流程中的各个节点：
- `start_node`：开始对话
- `generate_question_node`：生成问题
- `process_answer_node`：处理回答
- `update_personality_node`：更新人格
- `check_convergence_node`：检查收敛条件
- `match_character_node`：匹配人物
- `verify_match_node`：双重验证
- `finish_node`：输出结果

#### 1.3 路由逻辑 (`router.py`)

定义节点之间的流转逻辑：
- 根据收敛状态决定是否继续对话
- 根据验证结果决定是否输出结果
- 10% 概率随机探索，避免局部最优

#### 1.4 图定义 (`graph.py`)

使用 LangGraph 定义完整的对话流程图：
- 创建有状态的图
- 添加节点和边
- 定义结束条件

**参考实现**：
```python
# 使用 LangGraph 创建对话流
from langgraph.graph import StateGraph, END

workflow = StateGraph(AgentState)

workflow.add_node("start", start_node)
workflow.add_node("generate_question", generate_question_node)
workflow.add_node("process_answer", process_answer_node)
workflow.add_node("update_personality", update_personality_node)
workflow.add_node("check_convergence", check_convergence_node)
workflow.add_node("match_character", match_character_node)
workflow.add_node("verify_match", verify_match_node)
workflow.add_node("finish", finish_node)

workflow.set_entry_point("start")
workflow.add_edge("start", "generate_question")
workflow.add_edge("generate_question", "process_answer")
workflow.add_edge("process_answer", "update_personality")
workflow.add_edge("update_personality", "check_convergence")

# 收敛判断路由
workflow.add_conditional_edges(
    "check_convergence",
    lambda state: "continue" if not state.converged else "match_character"
)
workflow.add_edge("continue", "generate_question")

workflow.add_edge("match_character", "verify_match")

# 验证结果路由
workflow.add_conditional_edges(
    "verify_match",
    lambda state: "finish" if state.verified else "generate_question"
)

workflow.add_edge("finish", END)

app = workflow.compile()
```

---

### 2. API 路由层 (`src/api/`)

**状态**：❌ 未实现（空文件）

**需要实现的功能**：

#### 2.1 API 入口 (`main.py`)

使用 FastAPI 创建 API 应用：
- 创建 FastAPI 实例
- 配置 CORS
- 注册路由
- 添加异常处理
- 添加健康检查端点

**参考实现**：
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Hylog API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查
@app.get("/health")
async def health():
    return {"status": "ok"}
```

#### 2.2 路由定义 (`routes.py`)

定义所有 API 端点：

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/sessions` | POST | 创建会话 |
| `/api/sessions/{session_id}` | GET | 获取会话信息 |
| `/api/sessions/{session_id}/messages` | POST | 发送消息（核心对话接口） |
| `/api/sessions/{session_id}/messages` | GET | 获取对话历史 |
| `/api/sessions/{session_id}/personality` | GET | 获取人格状态 |
| `/api/sessions/{session_id}/result` | GET | 获取匹配结果 |
| `/api/users/register` | POST | 用户注册 |
| `/api/users/login` | POST | 用户登录 |
| `/api/users/login/sms` | POST | 短信验证码登录 |
| `/api/users/verify-sms` | POST | 发送验证码 |
| `/api/characters` | GET | 获取人物列表 |
| `/api/characters/{character_id}` | GET | 获取人物详情 |

**核心对话接口设计**：
```python
# 请求体
{
    "session_id": "string",
    "content": "用户回答内容",
    "user_id": "string (可选)"
}

# 响应体
{
    "session_id": "string",
    "question": "下一个问题",
    "personality_state": {
        "O": 0.72, "C": 0.65, "E": 0.45, "A": 0.58, "N": 0.32
    },
    "is_finished": false,
    "result": null  # 完成匹配后包含结果
}
```

---

### 3. 前端界面 (`app.py`)

**状态**：❌ 未实现（空文件）

**需要实现的功能**：

#### 3.1 页面结构

使用 Streamlit 构建 MVP 界面：

| 页面 | 功能 |
|------|------|
| **首页** | 欢迎语、开始测试按钮 |
| **对话页面** | 对话历史展示、输入框、AI 回复 |
| **结果页面** | 匹配人物展示（基础信息免费可见，完整信息付费解锁） |

#### 3.2 基础展示（免费可见）

- 人物姓名
- 来源/时代
- 人物图片（AI 生成）
- 相似度百分比
- 简介生平（100-200 字）
- 匹配热度（5 等级 + 百分比排名）

#### 3.3 完整展示（付费/转发解锁）

- 标签（5 个）
- 语录/名言/成语/评价
- 性格关键词
- 经典场景/事件
- 趣味冷知识
- 性格建议
- 相关书籍

#### 3.4 交互功能

- 对话输入和发送
- 进度显示（已回答问题数 / 预计问题数）
- 人格状态可视化（雷达图或柱状图）
- 结果分享功能
- 重新测试功能

**参考实现**：
```python
import streamlit as st
from src.agent import app

# 页面配置
st.set_page_config(
    page_title="Hylog - 认识真实的自己",
    page_icon="🤖",
    layout="wide"
)

# 首页
if "stage" not in st.session_state:
    st.session_state.stage = "home"

if st.session_state.stage == "home":
    st.title("🤖 Hylog - 认识真实的自己")
    st.subheader("通过对话发现你的人格画像")
    if st.button("开始测试"):
        st.session_state.stage = "conversation"
        st.session_state.session_id = create_session()

# 对话页面
elif st.session_state.stage == "conversation":
    # 显示对话历史
    for msg in get_messages(st.session_state.session_id):
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # 输入框
    if prompt := st.chat_input("回答问题..."):
        with st.chat_message("user"):
            st.write(prompt)
        
        # 调用 API
        response = send_message(st.session_state.session_id, prompt)
        
        with st.chat_message("assistant"):
            st.write(response["question"])
        
        # 更新状态
        if response["is_finished"]:
            st.session_state.stage = "result"
            st.session_state.result = response["result"]

# 结果页面
elif st.session_state.stage == "result":
    result = st.session_state.result
    st.title(f"你的匹配人物：{result['character']['name']}")
    # 展示基础信息和完整信息（根据权限）
```

---

### 4. 人物库构建

**状态**：⚠️ 未执行

**需要执行的操作**：

1. **运行预处理脚本**：
   ```bash
   python scripts/build_character_db.py
   ```

2. **添加更多人物**：
   - 编辑 `data/characters/character_list.json`
   - 添加中国历史人物（清朝或之前，不含近现代人物）
   - 建议至少添加 50-100 个人物

3. **验证人物数据**：
   - 检查数据库中的人物数据是否完整
   - 验证 OCEAN 分数是否合理
   - 检查图片是否成功生成

---

### 5. 联网搜索功能验证

**状态**：⚠️ 未验证

**需要验证的内容**：

1. 智谱 AI 的联网搜索功能是否正常工作
2. `analyze_character()` 方法是否能正确搜索人物资料
3. AI 是否能输出完整的 JSON 格式（包含 OCEAN 分数和所有展示内容）

---

### 6. 图片生成功能验证

**状态**：⚠️ 未验证

**需要验证的内容**：

1. 智谱 CogView API 是否能正常调用
2. 图片是否能成功下载并保存到本地
3. 图片质量是否符合要求（中国传统水墨画风格）

---

### 7. 测试用例完善

**状态**：❌ 未实现

**需要添加的测试**：

| 测试文件 | 需要添加的测试 |
|----------|---------------|
| `tests/test_personality.py` | 人格更新算法测试、收敛判断测试 |
| `tests/test_questions.py` | 问题生成测试、维度选择测试 |
| `tests/test_matching.py` | 相似度计算测试、匹配逻辑测试、热度计算测试 |
| `tests/test_agent.py` | 完整对话流程测试 |

---

### 8. 成本监控页面

**状态**：❌ 未实现

**需要实现的功能**：

使用 Streamlit 构建成本监控页面：
- 显示每日/每月成本
- 按功能分类统计（问题生成、人格分析、人物分析、图片生成）
- 成本趋势图表
- 预警提醒（接近每日/每月上限）

---

### 9. 部署准备

**状态**：❌ 未实现

**需要准备的内容**：

1. **Docker 配置**：
   - 创建 `Dockerfile`
   - 创建 `docker-compose.yml`
   - 配置数据库连接

2. **部署脚本**：
   - 创建部署脚本 `deploy.sh`
   - 配置 Nginx 反向代理

3. **环境配置**：
   - 生产环境配置（MySQL 数据库）
   - API Key 安全管理（环境变量或密钥管理服务）

---

## 三、项目进度总结

| 模块 | 状态 | 完成度 |
|------|------|--------|
| 人格建模模块 | ✅ 完成 | 100% |
| 问题模块系统 | ✅ 完成 | 100% |
| LLM 调用模块 | ✅ 完成 | 100% |
| 数据库模型 | ✅ 完成 | 100% |
| 人物匹配模块 | ✅ 完成 | 100% |
| 预处理脚本 | ✅ 完成 | 100% |
| Agent 调度模块 | ❌ 未实现 | 0% |
| API 路由层 | ❌ 未实现 | 0% |
| 前端界面 | ❌ 未实现 | 0% |
| 人物库构建 | ⚠️ 未执行 | 0% |
| 测试用例 | ❌ 未完善 | 30% |
| 部署准备 | ❌ 未实现 | 0% |

---

## 四、后续开发建议

### 优先级排序

| 优先级 | 任务 | 理由 |
|--------|------|------|
| **P0** | 运行预处理脚本构建人物库 | 没有人物库，匹配功能无法测试 |
| **P0** | 实现 Agent 调度模块 | 核心流程控制，连接所有模块 |
| **P0** | 实现 API 路由层 | 提供前后端交互接口 |
| **P1** | 实现前端界面（Streamlit） | 构建 MVP，验证核心流程 |
| **P1** | 添加更多人物（50-100 个） | 提升匹配精度和用户体验 |
| **P2** | 完善测试用例 | 确保代码质量 |
| **P2** | 成本监控页面 | 管理 AI 调用成本 |
| **P3** | Docker 部署配置 | 方便上线部署 |
| **P3** | React 前端重构 | 提升用户体验和扩展性 |

### 开发顺序建议

1. **第 1 阶段**：运行预处理脚本，构建人物库（1-2 天）
2. **第 2 阶段**：实现 Agent 调度模块（3-5 天）
3. **第 3 阶段**：实现 API 路由层（2-3 天）
4. **第 4 阶段**：实现 Streamlit 前端界面（3-5 天）
5. **第 5 阶段**：测试和优化（2-3 天）
6. **第 6 阶段**：部署上线（1-2 天）

---

## 五、技术栈总结

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| AI Agent | LangGraph | - | 状态机、模块路由 |
| LLM | 智谱 AI GLM-4 | - | 人格分析、问题生成、人物分析 |
| 图片生成 | 智谱 CogView-3 | - | 人物图片生成 |
| 数据库 | SQLite（开发）/ MySQL（生产） | - | 数据存储 |
| ORM | SQLAlchemy | 2.0+ | 数据库操作 |
| 后端框架 | FastAPI | 0.100+ | API 接口 |
| 前端 | Streamlit（MVP）/ React（后续） | - | 用户界面 |
| 配置管理 | python-dotenv | - | 环境变量 |
| Token 计数 | tiktoken | - | Token 计算 |
| 网络请求 | requests | - | HTTP 请求 |

---

## 六、关键决策记录

| 决策项 | 决策内容 | 理由 |
|--------|----------|------|
| 匹配方式 | OCEAN 5 维余弦相似度 | 避免文本向量化绕过 OCEAN 模型 |
| 人物库数据来源 | AI 联网搜索分析 | 批量处理大量人物，效率高 |
| 图片存储 | 本地文件夹 | 开发阶段简单，后续可迁移到云存储 |
| 付费解锁 | 后端判断 | 数据安全，用户无法绕过 |
| 热度等级 | 5 个等级 + 百分比排名 | 提供更丰富的热度信息 |
| 展示分层 | 基础免费 + 完整付费 | 商业变现模式 |
| 历史人物限制 | 清朝或之前 | 避免现代人物，保持文化底蕴 |
| 来源类型 | 只有历史人物 | 简化匹配范围，专注真实历史人物的深度分析 |

---

# 📌 项目交接说明（2026-07-19 更新）

> **本章节是给"接手开发的新对话/开发者"看的交接文档。**
> 阅读本章节后，你应当能理解项目当前状态、已完成什么、下一步要做什么、以及踩过的坑。

---

## 🎯 一句话总结当前状态

**后端核心架构 100% 完成，代码全部写好并通过单元验证；但因智谱 AI 余额不足（错误码 429 / 1113），真实 AI 联调尚未进行。下一步是开发前端界面（Streamlit）。**

---

## 📊 整体进度

```
设计  ▓▓▓▓▓▓▓▓▓▓ 100%  架构/维度/算法/表结构
后端  ▓▓▓▓▓▓▓▓▓░  90%  差真实AI联调验证
前端  ░░░░░░░░░░   0%  app.py 还是空的（下一步要做的）
上线  ░░░░░░░░░░   0%  未启动
```

---

## ✅ 已完成的模块（后端全部就绪）

### 1. 数据层 & 模型
- **人格建模** (`src/personality/`)：OCEAN 五维 + 11 维问题维度，EWMA 更新算法
- **数据库** (`src/data/`)：7 张表（User/Session/Message/PersonalitySnapshot/Result/VerificationCode/Character），Session 表新增 `state_json` 字段支持状态恢复
- **人物库**：24 个中国历史人物（先秦~清朝），见 `src/agent/nodes.py` 的 `MOCK_CHARACTERS` 和 `data/characters/character_list.json`

### 2. 核心业务层
- **问题系统** (`src/questions/`)：11 个维度模块 + 问题生成器
- **人物匹配** (`src/matching/`)：OCEAN 余弦相似度匹配，`SOURCE_TYPES = ["历史"]`（只有历史人物）
- **LLM 调用** (`src/utils/llm.py`)：智谱 AI 封装，含成本控制、日志、重试、流式输出
- **Agent 调度** (`src/agent/`)：`ConversationAgent` 主控制器，8 个节点函数

### 3. API 层（FastAPI 后端）
- **入口** (`main.py`)：`uvicorn src.api.main:app`，读 `.env` 的 `API_HOST`/`API_PORT`
- **应用** (`src/api/main.py`)：FastAPI 实例 + CORS + 异常处理 + 健康检查
- **5 个核心接口** (`src/api/routes.py`)：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/sessions` | 创建会话，返回开场白+第一个问题 |
| POST | `/api/sessions/{session_id}/reply` | 提交回答，返回下一个问题或匹配结果 |
| GET | `/api/sessions/{session_id}/state` | 查询人格状态和进度 |
| GET | `/api/sessions/{session_id}/result` | 查询匹配结果（未完成返回 409） |
| GET | `/api/sessions/{session_id}/messages` | 查询对话历史 |

- **数据模型** (`src/api/schemas.py`)：Pydantic 请求/响应模型，answer 长度校验 1~100 字符
- **依赖注入** (`src/api/deps.py`)：`get_db` / `get_mock_flag` / `load_session_or_404`

### 4. 辅助脚本
- **种子脚本** (`scripts/seed_characters.py`)：把 MOCK_CHARACTERS 写入数据库（不调智谱，免费让人物库非空）
- **人物库构建** (`scripts/build_character_db.py`)：调智谱联网分析真实人物（需余额）

---

## 🔌 API 接口规格（前端开发必须看这个）

### 启动后端服务

```bash
# 在项目根目录 D:\Hylog
python main.py
# 服务跑在 http://127.0.0.1:8000
# Swagger 文档 http://127.0.0.1:8000/docs
```

### 核心接口请求/响应示例

#### 1. 创建会话 `POST /api/sessions`

**请求**（body 可选）：
```json
{ "user_id": "test-user-001" }
```
不传 user_id 则用默认假用户（认证功能未上线）。

**响应**：
```json
{
  "session_id": "uuid-...",
  "question": "嗨，我是 Hylog～...（开场白）\n\n---\n\n（AI生成的第一个问题）",
  "message": "...",
  "personality_state": {"O": 0.5, "C": 0.5, "E": 0.5, "A": 0.5, "N": 0.5},
  "progress": {
    "turn": 0,
    "min_rounds": 15,
    "max_rounds": 30,
    "dimension_coverage": "0/11",
    "converged": false
  },
  "is_finished": false,
  "forced_finish": false,
  "result": null
}
```

#### 2. 提交回答 `POST /api/sessions/{session_id}/reply`

**请求**：
```json
{ "answer": "我喜欢一个人安静地看书（1~100字符）" }
```

**响应（对话进行中）**：
```json
{
  "session_id": "uuid-...",
  "question": "（AI生成的下一个问题）",
  "message": "...",
  "personality_state": {"O": 0.62, "C": 0.55, "E": 0.32, "A": 0.58, "N": 0.32},
  "progress": {"turn": 1, "min_rounds": 15, "max_rounds": 30, "dimension_coverage": "1/11", "converged": false},
  "is_finished": false,
  "forced_finish": false,
  "result": null
}
```

**响应（对话完成，匹配到人物）**：
```json
{
  "session_id": "uuid-...",
  "question": "经过 16 轮对话...和你最像的人物是：**苏轼**...相似度 87%。",
  "is_finished": true,
  "forced_finish": false,
  "result": {
    "character": {
      "character_id": "seed-sushi",
      "name": "苏轼",
      "source": "历史",
      "era": "宋朝",
      "description": "北宋文学家...",
      "image_path": "",
      "ocean_vector": {"O": 0.92, "C": 0.65, "E": 0.78, "A": 0.78, "N": 0.30},
      "tags": ["豁达乐观", "旷达超脱", "热爱生活"],
      "quote": "竹杖芒鞋轻胜马，谁怕？...",
      "personality_keyword": "豁达乐观型",
      "classic_events": "", "fun_facts": "", "advice": "", "related_books": ""
    },
    "similarity": 0.87,
    "similarity_percent": 87,
    "heat_level": "热门",
    "heat_percent": 35,
    "is_paid_locked": false
  }
}
```

#### 3. 查状态 `GET /api/sessions/{session_id}/state` / 查结果 `GET /result` / 查历史 `GET /messages`

返回结构与上述响应中的对应部分一致。完整 schema 见 `src/api/schemas.py`。

### 错误码

| 状态码 | 含义 |
|--------|------|
| 200 | 成功 |
| 404 | 会话不存在 |
| 409 | 测试未完成（查 result 时） |
| 422 | 参数校验失败（answer 空/超100字） |
| 503 | AI 服务不可用（智谱失败） |
| 500 | 服务器内部错误 |

---

## 🚧 下一步：开发前端界面（Streamlit）

### 目标文件
`app.py`（项目根目录，目前是空文件）

### 技术选型
**Streamlit**（纯 Python，快速搭建 MVP）。理由：之前已与用户确认先用 Streamlit 验证核心流程，后续再考虑用 React 重构。

### 前端要实现的功能

#### 必做功能（MVP 主链路）
1. **对话界面**：聊天式 UI，用户输入回答 → 调 `POST /reply` → 显示 AI 生成的问题
2. **进度展示**：显示当前轮次（X/30）、维度覆盖率（Y/11）、人格雷达图（OCEAN 五维）
3. **开场白**：调 `POST /sessions` 后展示开场白和第一个问题
4. **结果展示**：测试完成后（`is_finished=true`）展示匹配人物卡片（姓名/朝代/相似度/简介/语录/标签/性格关键词）
5. **会话管理**：用 `session_id` 串联整个对话（存 sessionStorage 或 st.session_state）

#### 建议的 UI 布局
```
┌─────────────────────────────────────────┐
│  Hylog - 认识自己的旅程                    │
├─────────────────────────────────────────┤
│  [对话区域 - 聊天气泡式]                  │
│  AI: 嗨，我是 Hylog～...                  │
│  用户: 我喜欢一个人看书                    │
│  AI: 在朋友聚会中...？                     │
│                                          │
│  [输入框] ___________________________    │
│  [发送按钮]                               │
├─────────────────────────────────────────┤
│  侧边栏：                                 │
│  📊 人格雷达图（OCEAN）                   │
│  📈 进度：第 5/30 轮                      │
│  🎯 维度覆盖：3/11                        │
│  🔄 重新开始                              │
└─────────────────────────────────────────┘
```

#### 调用后端的 Python 代码片段（参考）
```python
import requests

API_BASE = "http://127.0.0.1:8000"

# 创建会话
r = requests.post(f"{API_BASE}/api/sessions", json={"user_id": "test-user"})
data = r.json()
session_id = data["session_id"]
current_question = data["question"]

# 循环对话
while True:
    user_answer = get_user_input()  # 前端获取
    r = requests.post(
        f"{API_BASE}/api/sessions/{session_id}/reply",
        json={"answer": user_answer}
    )
    data = r.json()

    display(data["question"])              # 显示下一个问题
    update_radar(data["personality_state"]) # 更新雷达图
    update_progress(data["progress"])       # 更新进度

    if data["is_finished"]:
        display_result(data["result"])      # 显示匹配结果
        break
```

### 前端开发注意事项
- **前端只通过 HTTP 调后端 API**，不要直接 import `src/` 的模块（前后端解耦）
- **CORS 已配置**：`.env` 的 `CORS_ORIGINS` 默认含 `http://localhost:8501`（Streamlit 默认端口）
- **会话状态管理**：用 Streamlit 的 `st.session_state` 存 `session_id`、对话历史、人格状态
- **输入校验**：前端也应限制 answer 长度 1~100 字符（后端已有 422 兜底）
- **加载状态**：调 `/reply` 时智谱响应慢（可能 5~30 秒），要有 loading 动画

---

## ⚠️ 关键限制：Mock 模式 vs 真实模式

**这是前端开发期间最大的坑，必须看懂：**

### `.env` 的 `USE_MOCK_AGENT` 开关
- `false`（默认）：真实模式，调智谱（**当前余额不足，调不通**）
- `true`：Mock 模式，用假数据，不花钱

### 前端开发期间的建议策略
**前端开发期间建议用 Mock 模式（`USE_MOCK_AGENT=true`）**，原因：
1. 不消耗智谱额度
2. 响应快（不走网络）
3. 能验证 UI 布局和交互逻辑

**但 Mock 模式有一个已知限制**：
- ✅ Mock 模式下 `POST /sessions`（创建会话）能成功
- ❌ Mock 模式下 `POST /reply` 会返回 **404**（因为 Mock 创建会话不写数据库，而 reply 依赖数据库恢复状态）

**所以 Mock 模式下前端能验证**：
- 创建会话的请求/响应流程
- 查询类接口（state/messages/result）
- UI 布局、雷达图、进度条展示

**Mock 模式下前端无法验证**：
- 完整的多轮对话（reply 链路）
- 真实的 AI 问题生成和人格分析

### 待智谱充值后的完整联调
等用户充值智谱后（或改用 `glm-4-flash` 等便宜模型），设 `USE_MOCK_AGENT=false`，就能跑完整流程。

---

## 🧪 已验证的功能（无需重复测试）

这些在本次开发周期已经验证通过，新对话可以信任：

| 验证项 | 验证方式 | 结果 |
|--------|---------|------|
| 所有模块导入 | `python -c "from src.api import app"` | ✅ 无报错 |
| FastAPI 应用启动 | uvicorn 启动 | ✅ 正常监听 |
| 5 个路由注册 | `app.routes` 检查 | ✅ 全部注册 |
| ConversationAgent 状态持久化+恢复 | `create()` → `_persist_state()` → `restore()` | ✅ turn_count/dimension 精确恢复 |
| 只读接口（state/messages/result） | TestClient 调用 | ✅ 返回正确数据 |
| 错误处理（404/409/422） | TestClient 调用 | ✅ 状态码正确 |
| SOURCE_TYPES 校验 | 单元测试 | ✅ 只接受"历史" |
| validate_era_for_history | 各朝代测试 | ✅ 春秋~清朝 True，民国/现代 False |
| MOCK_CHARACTERS 数据 | 24 个人物检查 | ✅ source 全为"历史"，OCEAN 0~1 合法 |
| character_list.json | 与 MOCK 对比 | ✅ 24 个人物名单完全一致 |
| 种子脚本 | 写入数据库 | ✅ 24 个人物入库 |

---

## 🚫 尚未验证的功能（需充值智谱后验证）

| 功能 | 原因 | 验证方法 |
|------|------|---------|
| AI 问题生成质量 | 余额不足 | 充值后 POST /sessions 看 question 字段 |
| AI 人格分析准确性 | 余额不足 | 充值后多轮 reply 看 personality_state 变化 |
| 完整收敛流程（15~30轮） | 余额不足 | 充值后跑完整对话看 is_finished |
| Fallback 降级效果 | 余额不足 | 充值后观察 LLM 失败时的备用问题 |
| 真实人物库 OCEAN 分析 | 余额不足 | 跑 `scripts/build_character_db.py` |

---

## 📁 关键文件索引（接手必读）

### 项目结构
```
D:\Hylog\
├── main.py                    # 根目录启动入口（uvicorn）
├── app.py                     # 【空的】前端入口，下一步要开发
├── .env                       # 环境变量（含智谱API Key，已被 gitignore）
├── .env.example               # 配置模板（可提交）
├── requirements.txt           # 依赖清单
├── README.md                  # 项目简介
├── PROJECT_STATUS.md          # 本文件
├── CHANGELOG.md               # 开发日志（按时间记录所有决策和改动）
├── data/characters/
│   ├── character_list.json    # 24 个历史人物名单
│   └── images/                # 人物图片目录（空，待生成）
├── scripts/
│   ├── seed_characters.py     # 种子脚本（免费写 24 个人物到数据库）
│   └── build_character_db.py  # 真实人物库构建（调智谱，需余额）
└── src/
    ├── api/                   # FastAPI 后端（5个接口）
    ├── agent/                 # Agent 调度（ConversationAgent）
    ├── personality/           # 人格建模（OCEAN + 更新算法）
    ├── questions/             # 问题系统（11个维度）
    ├── matching/              # 人物匹配（余弦相似度）
    ├── data/                  # 数据库模型（7张表）
    └── utils/llm.py           # LLM 调用封装（智谱）
```

### 接手必读的 5 个文件（按重要性排序）
1. **本文件**（PROJECT_STATUS.md）—— 全局进度和交接说明
2. **`CHANGELOG.md` 末尾的 2026-07-07 和 2026-07-19 两条** —— 最近两次开发记录
3. **`src/api/routes.py`** —— API 接口实现（前端对接的依据）
4. **`src/api/schemas.py`** —— 请求/响应数据结构（前端类型定义的依据）
5. **`src/agent/graph.py`** —— ConversationAgent 的 `create()`/`start()`/`reply()`/`restore()` 方法

---

## 🎯 关键决策记录（不要推翻，除非用户明确要求）

| 决策 | 选择 | 理由 |
|------|------|------|
| Agent 框架 | 纯 Python 状态类（非 LangGraph） | Web 多会话友好、流式输出原生支持 |
| 收敛机制 | 收敛即输出，取消双重验证 | 11 维只用于探索，匹配只用 OCEAN |
| 人物来源 | 只有历史人物（清朝或之前） | 用户 2026-07-19 决定，专注真实人物 |
| 状态恢复 | Session 表 state_json 字段 | HTTP 无状态架构的标准做法 |
| 前端技术 | Streamlit（先用 MVP） | 用户确认，后续可升级 React |
| 认证 | 延后，接口预留 user_id | 主链路优先，认证加中间件即可 |
| 流式输出 | 暂不做（非流式先跑通） | 后续加 SSE 不破坏现有接口 |
| 付费分层 | 当前全部返回（is_paid_locked=false） | 上线前再实现分层 |
| 收敛阈值 | 最小15轮/最大30轮/不确定性<0.3 | README 默认值 |

---

## 🐛 已知问题 & 待办

### 待用户处理
- [ ] **智谱充值**：当前余额不足（429/1113），无法进行真实 AI 联调。用户需到 https://open.bigmodel.cn/usercenter/proj-mgr/apikeys 核实并充值（建议 ¥10~20）
- [ ] **或改用便宜模型**：可把 `.env` 的 `ZHIPU_MODEL` 改成 `glm-4-flash` 试试（免费/低价）

### 待开发
- [ ] **前端 app.py**（下一步，见上文"开发前端界面"章节）
- [ ] 用户认证（JWT + 手机号登录）
- [ ] 流式输出（SSE）
- [ ] 人物图片生成（CogView API）
- [ ] 真实人物库 OCEAN 分析（跑 build_character_db.py）

### 已知技术限制
- **Mock 模式下 reply 接口 404**：因 Mock 不落库。前端开发期间只能验证 create 和只读接口
- **Python 3.14.5 + 无虚拟环境**：全局环境，建议后续建 venv 隔离
- **智谱调用超时 60 秒**：`.env` 的 `LLM_TIMEOUT=60`，单次 reply 最长等 60 秒

---

## 💡 给新对话的建议

1. **接手第一步**：先把 `.env` 设为 `USE_MOCK_AGENT=true`，启动后端 `python main.py`，访问 http://127.0.0.1:8000/docs 看 Swagger 文档熟悉接口
2. **前端开发**：在 `app.py` 用 Streamlit 实现，参考上文的 UI 布局和代码片段
3. **遇到智谱调用**：当前余额不足，所有真实 AI 调用会失败并走 fallback。开发前端时用 Mock 模式
4. **改后端代码前**：先读 CHANGELOG.md 的 2026-07-07 条目，理解 API 模块的设计决策
5. **不要重构**：现有代码经过验证，除非有明确 bug 或用户要求，不要推翻已有设计
6. **提问前**：本文件应该已经回答了大部分问题。如果仍有疑问，再问用户

---

**最后更新**：2026-07-19
**当前分支**：main
**最近提交**：d4cad7c（refactor: 人物库改为只有历史人物，扩充到 24 个）
**下一步**：开发前端界面（Streamlit）—— 目标文件 `app.py`