# AI 学习助手（Agent）功能说明

> 状态（2026-11-21）：代码、单元测试、前端页面已完成；**尚未用真实 API Key 联调**。
> 配好 `ANTHROPIC_API_KEY` 后按下面「怎么运行」验证一遍。

---

## 1. 做了什么

在原来的背单词 App 里加了一个 **AI 学习助手**。用户用自然语言提要求，Agent 自己决定调用哪些工具来完成，例如：

| 用户说 | Agent 会做什么 |
|---|---|
| retention 是什么意思？给我一个例句 | 调 `lookup_word` 查词 → 用查到的释义回答 |
| 我今天有哪些词要复习？ | 调 `get_due_reviews` → 列出今天到期的词 |
| 帮我把 resilient 和 allocate 存到词库 | 查两个词 → 检查词库有没有 → 调 `add_word` 保存（自动生成复习记录） |

**和普通聊天机器人的区别**：它不是只会"说"，而是能读写你自己的数据（词库、复习记录），而且每一步都走后端已有的业务代码。

---

## 2. 整体流程

```text
手机页面 /agent
   │  POST /api/agent/chat   { message, history }   (带 JWT)
   ▼
agent_routes.py  ──>  AgentService.chat()
                         │
                         │  ① 把消息 + 工具列表发给 Claude
                         ▼
                      Claude 回复：
                        - 要调用工具（stop_reason = "tool_use"）
                        - 或直接给出答案（stop_reason = "end_turn"）
                         │
           需要工具 ──>  ② AgentTools 执行工具（查词 / 查词库 / 加词 / 查复习）
                         │     └─ 复用 WordService、ReviewService、词典
                         │  ③ 把工具结果发回 Claude
                         │  ④ 重复 ①–③，最多 8 轮
                         ▼
                      最终回答 + 本次调用了哪些工具 + token 用量
```

这就是 Agent 的核心：**模型决定下一步做什么，代码负责真正执行，并把结果反馈给模型**。

---

## 3. 新增和修改的文件

### 后端（沿用 DDD 分层）

| 层 | 文件 | 作用 |
|---|---|---|
| application | `app/application/services/agent_service.py` | **核心**：系统提示词、4 个工具定义、工具执行器 `AgentTools`、Agent 循环 `AgentService` |
| infrastructure | `app/infrastructure/llm/claude_client.py` | 封装 Claude API：模型、effort、缓存、错误转换 |
| infrastructure | `app/infrastructure/dictionary/online_dictionary.py` | 后端在线词典查询（Longman 本地查不到时用） |
| interfaces | `app/interfaces/http/routes/agent_routes.py` | 新接口 `POST /api/agent/chat` |
| interfaces | `app/interfaces/http/dependencies.py` | 依赖注入：组装 `AgentService`，用户 ID 从 JWT 取 |
| — | `app/application/schemas.py` | 请求格式 `AgentChatRequest`、`ChatTurn` |
| — | `app/infrastructure/config/settings.py` | 新配置：`ANTHROPIC_API_KEY`、`AGENT_MODEL`、`AGENT_EFFORT` |
| — | `app/main.py` | 注册 `/api/agent` 路由 |
| — | `requirements.txt` | 新依赖 `anthropic==2.12.0` |
| — | `.env.example` | 新增 3 个配置示例 |
| tests | `tests/test_agent_service.py` | 8 个单元测试（用假的 Claude，不花钱） |

### 前端

| 文件 | 作用 |
|---|---|
| `src/features/agent/api/agentApi.ts` | 调用 `/api/agent/chat`，超时放宽到 90 秒 |
| `src/pages/agent/AgentChatPage.vue` | 手机聊天页：示例问题、消息气泡、工具调用标签、"思考中"状态、新对话 |
| `src/app/router/index.ts` | 新路由 `/agent` |
| `src/pages/home/HomePage.vue` | 首页搜索框旁边加了聊天按钮（在拍照按钮旁边） |
| `src/shared/model/settingsStore.ts` | 中英文文案 |

---

## 4. 四个工具

| 工具 | 输入 | 做什么 | 复用的代码 |
|---|---|---|---|
| `lookup_word` | word | 先查本地 Longman，没有再查在线词典 | `longman_dictionary.py` + `online_dictionary.py` |
| `search_my_words` | query（可为空） | 搜当前用户词库，返回释义、复习阶段、下次复习时间 | `WordService.list_words` |
| `add_word` | word, meaning, example | 保存单词，同时生成今天要复习的记录 | `WordService.create_word` |
| `get_due_reviews` | 无 | 列出今天到期的复习词 | `ReviewService.list_today_reviews` |

工具定义都开了 `strict: true`，保证模型给出的参数严格符合格式。

---

## 5. 安全设计（面试重点）

1. **用户隔离**：用户 ID 来自登录的 JWT，在创建 `AgentTools` 时就固定了；模型的参数里**根本没有** user_id，所以它不可能读写别人的数据。
2. **最小权限**：故意**不提供**删除单词、标记复习完成的工具。Agent 最多只能"加"，不能"删"或"改"。
3. **防重复**：加词前检查词库，已存在就返回 "already in library"，不会重复添加。
4. **数量上限**：一条消息最多加 10 个词；Agent 循环最多 8 轮，防止死循环和费用失控。
5. **出错不崩溃**：工具出错（参数不对、未知工具）时把错误作为 `is_error` 结果返回给模型，让它自己解释或换个做法。
6. **提示词约束**：只有用户明确说"保存/添加"时才加词；释义必须先查词典，不许编。

---

## 6. 几个技术细节

- **模型**：默认 `claude-opus-5-5`，`effort: low`（聊天场景要快、要省）。可在 `.env` 里改。
- **Prompt caching**：请求带 `cache_control`，同一次对话的多轮工具调用里，系统提示词和工具列表这些不变的部分会被缓存，降低成本。
- **安全拒答时的备用模型**：开启了 `fallbacks: "default"`，如果模型出于安全原因拒绝回答，API 会自动换备用模型重试。在 `claude_client.py` 里可以去掉。
- **多工具并行**：Claude 一次可能要求调用多个工具（比如同时查两个词），所有结果放在**同一条**消息里发回去。
- **对话历史**：前端只把之前的纯文本对话发给后端（最多 20 条）；工具调用细节只在当前这次请求里使用。这样后端是无状态的，也不用存聊天记录。
- **错误码**：未配置 Key → 503（50310）；Key 无效 → 503（50311）；限流 → 429；Agent 步数过多 → 508（50820）。

---

## 7. 怎么运行

1. 在 https://console.anthropic.com 创建 API Key（API 费用和 Claude.ai 订阅分开计费）。
2. 在 `backend/.env` 加一行（这个文件已在 `.gitignore` 里，不会上传）：
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. 重启后端：`docker restart vocab_backend`
   （以后重建镜像用 `docker compose up -d --build backend`，会按 `requirements.txt` 装好 `anthropic`）
4. 手机或浏览器打开首页 → 搜索框旁的聊天按钮 → 试试：
   - `retention 是什么意思？`
   - `我今天有哪些词要复习？`
   - `帮我把 resilient 和 allocate 存到词库` → 然后去「词库」和「复习」页确认

## 8. 测试

```bash
docker exec vocab_backend python -m pytest -q tests
```

当前结果：**17 passed**（原有 9 个 + Agent 新增 8 个）。Agent 测试覆盖：

- 不调工具直接回答
- 查词 → 加词的完整循环，且加的是**登录用户**的词
- 已存在的词不重复添加
- 未知工具（如 `delete_word`）返回错误结果而不是崩溃
- 多个工具调用在一条消息里一起返回
- 超过 8 轮自动停止
- 安全拒答时返回友好提示
- 对话历史格式规整（必须以用户开头、角色交替）

---

## 9. 还没做的（下一步）

| 优先级 | 内容 |
|---|---|
| 1 | **用真实 Key 联调**，记录每条消息的 token 用量和耗时 |
| 2 | **Eval 测试集**：准备 20–30 条真实指令，自动检查 Agent 有没有调对工具、有没有误加词 |
| 3 | 流式输出（SSE），回答逐字显示；页面显示"正在查词…"等实时进度 |
| 4 | 把图片 OCR 也做成工具：拍照 → Agent 挑出生词 → 确认后批量保存 |
| 5 | 根据"不认识/模糊"多的词出题、生成例句 |
| 6 | MCP Server：让 Claude Desktop 等外部 AI 客户端也能管理词库 |

---

## 10. 面试时怎么讲（2 分钟版）

1. **背景**：我做了一个背单词 App，后来加了 AI 助手，让用户用一句话完成"查词 + 存词库 + 看复习"。
2. **架构**：用 Claude API 的 tool calling，自己实现 Agent 循环；工具直接复用后端 DDD 应用层的服务，所以 AI 走的是和页面一样的业务规则。
3. **难点和取舍**：
   - 为什么不让模型直接写 SQL？→ 安全和数据隔离，工具只暴露必要能力。
   - 为什么不给删除工具？→ 最小权限，误删代价大。
   - 怎么防止死循环和费用失控？→ 轮数上限、加词上限、低 effort、prompt caching。
4. **测试**：用假的 LLM 客户端写单元测试，不花钱也能验证循环逻辑。

> 简历上写的数字（准确率、成本、耗时）必须是你自己联调和跑 eval 后真实测出来的。

---

## 11. 学习规划 Agent（Study-planning agent）

> 状态：代码、单元测试（6 个）、前端页面已完成；**尚未用真实 API Key 联调**。

**做什么**：根据学习者自己的数据，生成"今天学什么"的计划。

1. 每次听写 / 复述提交后，前端把成绩、漏掉的词、听错的词（期望 vs 实际）发到 `POST /api/planner/attempts`，存进 `practice_attempts` 表。
2. 用户在「复习」页点 **AI 今日学习计划**，选择今天有多少分钟（可选填重点），调用 `POST /api/planner/plan`。
3. Agent 循环（与 AI 助手相同的模式）：
   - `get_learning_snapshot`：词库数量、今日到期、复习阶段分布、近 7 天听力次数和平均分
   - `get_listening_mistakes(days)`：最常漏掉的词、最常听错的词、最弱的句子（含 material_id / sentence_index）
   - `get_due_reviews`：今天到期的单词
   - `save_study_plan(summary, tasks)`：最后调用一次，保存计划
4. 计划页显示 Agent 的分析和任务清单；点任务直接跳到对应页面（复习页 / 听力某一句的听写或复述 / 查词），可以打勾，进度保存在 `study_plans` 表。

**可靠性设计**

| 风险 | 做法 |
|---|---|
| 编造句子 | `save_study_plan` 校验 material_id / sentence_index 必须属于当前用户且存在，否则返回 `is_error`，让模型改正 |
| 越权 | user_id 来自 JWT，工具参数里没有 user_id |
| 不保存就结束 | 没调用 `save_study_plan` 视为失败，返回错误而不是假装成功 |
| 失控 | 最多 8 轮；任务最多 8 个；每个任务 1–60 分钟 |
| 时区 | 计划按手机本地日期保存（前端传 date），不用服务器 UTC 日期 |

代码：`backend/app/application/services/planner_service.py`，分析逻辑 `backend/app/domain/services/practice_analysis.py`，测试 `backend/tests/test_planner.py`。
