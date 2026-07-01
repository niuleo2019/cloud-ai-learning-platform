# Vocab App — Codex 优化指令文档

> 本文件由架构师生成，供 Codex 逐条实施。按优先级从高到低排列。
> 项目路径：`vocab-app/`，技术栈：Vue 3 + FastAPI + MySQL + Docker

---

## 一、后端优化（Backend — Python FastAPI）

### 1.1 连接池（最高优先级）

**问题：** `app/infrastructure/database/` 中每次请求都新建 PyMySQL 连接，高并发下会耗尽 MySQL 连接数。

**任务：**
- 在 `app/infrastructure/database/connection.py`（如不存在则新建）中引入 `DBUtils` 的 `PooledDB`，或直接使用 `pymysql` + 手写连接池。
- 推荐方案：安装 `dbutils==3.1.0`，用 `PooledDB(creator=pymysql, maxconnections=10, ...)` 封装。
- 将全局连接池实例通过 FastAPI `lifespan` 事件（`startup` / `shutdown`）管理，不再每次 `connect()`。
- 修改 `requirements.txt` 加入 `dbutils==3.1.0`。

---

### 1.2 统一异常处理 + 错误码

**问题：** 部分路由直接抛 `HTTPException`，没有业务错误码，前端无法区分"密码错误"和"用户不存在"。

**任务：**
- 新建 `app/interfaces/exceptions.py`，定义 `AppException(code: int, message: str)` 业务异常。
- 在 `app/interfaces/responses.py` 中注册 `@app.exception_handler(AppException)`，统一返回：
  ```json
  { "success": false, "code": 40101, "message": "密码错误", "data": null }
  ```
- 错误码规范：`401xx` = 认证类，`403xx` = 权限类，`404xx` = 资源不存在，`422xx` = 参数校验。
- 将 `auth_routes.py`、`word_routes.py`、`review_routes.py` 中的 `HTTPException` 替换为 `AppException`。

---

### 1.3 ReviewPolicy 边界修复

**问题：** `app/domain/services/review_policy.py` 中 stage 超过 5 时没有上限保护，可能导致数组越界。

**任务：**
- 在 `ReviewPolicy.calculate_next` 方法里加断言：`stage = min(stage, len(INTERVALS) - 1)`。
- 为 `known` / `fuzzy` / `unknown` 三个分支分别写单元测试，放到 `backend/tests/test_review_policy.py`。
- 安装 `pytest==8.3.4`，加入 `requirements-dev.txt`。

---

### 1.4 密码强度校验

**问题：** `RegisterRequest` 只校验 email 格式，无密码强度限制，`123456` 这样的弱密码可注册。

**任务：**
- 在 `app/application/schemas/auth_schemas.py` 的 `RegisterRequest` 中，给 `password` 字段加 Pydantic validator：
  ```python
  @field_validator("password")
  def password_strength(cls, v):
      if len(v) < 8:
          raise ValueError("密码至少8位")
      if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
          raise ValueError("密码需包含字母和数字")
      return v
  ```

---

### 1.5 JWT Refresh Token 机制

**问题：** 当前只有 access token，7天到期后用户直接登出，体验差。

**任务：**
- 在 `app/infrastructure/security/jwt_service.py` 中新增 `generate_refresh_token(user_id)`，有效期 30 天。
- 新增 `POST /api/auth/refresh` 路由，接收 `refresh_token`，返回新 `access_token`。
- 数据库 `users` 表新增 `refresh_token VARCHAR(512) NULL` 列，在 `database/schema.sql` 中添加 `ALTER TABLE` 语句。

---

## 二、前端优化（Frontend — Vue 3 + TypeScript）

### 2.1 全局错误拦截 + Toast 提示

**问题：** `frontend/src/shared/api/http.ts` 的 axios 拦截器只处理了 401，其他错误（500、网络断开）没有统一提示。

**任务：**
- 在 `http.ts` 的 `response` 错误拦截器中，按 HTTP status 和业务 `code` 字段分别处理：
  - `401` → 清除 token → 跳转 `/login`
  - `5xx` → Vant `showToast('服务器繁忙，请稍后重试')`
  - 网络断开 → `showToast('网络异常，请检查连接')`
  - 业务错误 → `showToast(error.response.data.message)`
- 用 Vant 的 `showFailToast` 替换 `console.error`。

---

### 2.2 今日复习页 — 卡片翻转动画

**问题：** `frontend/src/pages/reviews/TodayReviewPage.vue` 直接显示单词和释义，没有"先看单词、点击翻转看释义"的记忆流程。

**任务：**
- 重构 `TodayReviewPage.vue`，将卡片改为两面结构：
  - **正面**：显示 `word`（大字体），`source` 标签
  - **背面**：显示 `meaning` + `example`（带引用样式）
- 使用 CSS `transform: rotateY(180deg)` + `transition: 0.6s` 实现翻转效果。
- 点击卡片才翻转，翻转后才显示「认识 / 模糊 / 不认识」三个按钮。
- 当天复习进度显示：`{已完成} / {总数}` 进度条（Vant `van-progress`）。

---

### 2.3 单词列表 — 搜索 + 分页

**问题：** `frontend/src/pages/words/WordListPage.vue` 无搜索，词量大时需要滚动查找。

**任务：**
- 顶部加 Vant `van-search` 组件，本地 `filter` 单词数组（不需要后端接口）。
- 使用 `van-list` 组件的 `infinite scroll` 模式，每次渲染 20 条，滚动到底加载更多。
- 每个单词卡片右上角加「复习阶段」徽章（Vant `van-badge`），阶段 0-5 用不同颜色区分：
  - 0 = 灰色（新单词）
  - 1-2 = 橙色（初学）
  - 3-4 = 蓝色（巩固）
  - 5 = 绿色（已掌握）

---

### 2.4 首页 Dashboard — 数据可视化

**问题：** `frontend/src/pages/home/` 的 Dashboard 只有文字数字，缺乏视觉吸引力。

**任务：**
- 安装 `echarts` (^5.5.1) 或更轻量的 `chart.js` (^4.4.7) + `vue-chartjs`。
- 在 Dashboard 加入：
  1. **环形图**：已掌握 (stage5) / 学习中 (stage1-4) / 新词 (stage0) 占比
  2. **7日复习柱状图**：过去7天每天完成的复习数量（需后端新增 `GET /api/reviews/stats` 接口返回）
- 保持 Vant 风格，图表宽度 `100%`，高度固定 `200px`。

---

### 2.5 添加单词页 — 表单体验优化

**问题：** `frontend/src/pages/words/AddWordPage.vue` 提交后页面不清空，也没有添加成功的视觉反馈。

**任务：**
- 提交成功后：弹出 Vant `showSuccessToast('添加成功！')`，延迟 1.5s 后清空表单。
- `source` 字段改为 Vant `van-picker` 下拉选择（预置选项：IELTS Listening / Reading / Writing / Speaking / 自定义），支持手动输入。
- 添加字数统计：`meaning` 字段下方实时显示 `{length}/200`。

---

### 2.6 Pinia 状态管理（可选但推荐）

**问题：** 目前词库数据在多个页面间独立 fetch，切换页面会重复请求。

**任务：**
- 安装 `pinia` (^2.2.6)，在 `main.ts` 注册。
- 新建 `frontend/src/stores/wordStore.ts`：
  ```typescript
  export const useWordStore = defineStore('words', () => {
    const words = ref<Word[]>([])
    const loaded = ref(false)
    async function fetchWords() {
      if (loaded.value) return
      words.value = await wordApi.getWords()
      loaded.value = true
    }
    return { words, loaded, fetchWords }
  })
  ```
- `WordListPage` 和 `Dashboard` 共享同一份缓存，避免重复请求。
- 添加/删除单词后本地更新 store，不重新 fetch。

---

## 三、数据库优化（MySQL）

### 3.1 缺失索引

**任务：** 在 `database/schema.sql` 中追加：
```sql
-- 按单词文本搜索（支持前端搜索功能扩展到后端）
ALTER TABLE words ADD INDEX idx_words_word (word);

-- 复习统计查询：按用户+时间范围统计完成数
ALTER TABLE review_records ADD INDEX idx_review_last_review (user_id, last_review_at);
```

---

### 3.2 软删除（Soft Delete）

**问题：** 当前 `DELETE /api/words/{id}` 是物理删除，无法恢复误删单词。

**任务：**
- `words` 表新增 `deleted_at DATETIME NULL DEFAULT NULL`。
- `database/schema.sql` 增加 `ALTER TABLE words ADD COLUMN deleted_at DATETIME NULL DEFAULT NULL`。
- `MySQLWordRepository` 的查询全部加 `WHERE deleted_at IS NULL`。
- `DELETE` 操作改为 `UPDATE words SET deleted_at = NOW() WHERE id = ?`。
- 前端「我的单词本」页加「回收站」入口（可选，后续实现）。

---

## 四、Docker & DevOps 优化

### 4.1 生产环境 Dockerfile

**问题：** 当前 `frontend/Dockerfile` 用 Vite dev server，不适合生产部署。

**任务：**
- 新建 `frontend/Dockerfile.prod`，使用多阶段构建：
  ```dockerfile
  # Stage 1: build
  FROM node:20-alpine AS builder
  WORKDIR /app
  COPY package*.json ./
  RUN npm ci
  COPY . .
  RUN npm run build

  # Stage 2: serve
  FROM nginx:alpine
  COPY --from=builder /app/dist /usr/share/nginx/html
  COPY nginx.conf /etc/nginx/conf.d/default.conf
  EXPOSE 80
  ```
- 新建 `frontend/nginx.conf`，加入 `try_files $uri /index.html`（SPA 路由支持）和 gzip 压缩。
- `docker-compose.yml` 中新增 `prod` profile，用 `Dockerfile.prod`。

---

### 4.2 健康检查

**任务：** 在 `docker-compose.yml` 中给三个服务加 `healthcheck`：
```yaml
# MySQL
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
  interval: 10s
  timeout: 5s
  retries: 5

# Backend
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
  interval: 15s
  timeout: 5s
  retries: 3
```

---

### 4.3 GitHub Actions CI

**任务：** 新建 `.github/workflows/ci.yml`：
```yaml
name: CI
on: [push, pull_request]
jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r vocab-app/backend/requirements.txt -r vocab-app/backend/requirements-dev.txt
      - run: pytest vocab-app/backend/tests/ -v

  frontend-typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd vocab-app/frontend && npm ci && npm run build
```

---

## 五、配图生成提示词（Image Generation Prompts）

以下提示词用于为 vocab app 各页面生成配套插图，风格统一为：**扁平化插画，莫兰迪色系，圆角元素，适合移动端教育类 App**。

---

### 5.1 首页 / Dashboard 空状态插图

**用途：** 当用户新注册、词库为空时展示的引导插图

```
Flat illustration of a young student sitting at a desk with a large empty notebook open in front of them, a cup of tea beside them, soft morning light coming through a window. Muted pastel colors (sage green, dusty rose, warm beige). Clean minimal style, no text. Mobile app empty state illustration. 2:3 ratio.
```

---

### 5.2 今日复习 — 零任务完成庆祝插图

**用途：** 当天复习全部完成时的成就动效配图

```
Flat illustration of a cheerful character holding a trophy, surrounded by floating stars and confetti in soft colors (lavender, mint, peach). Celebratory mood, clean white background. Educational app success screen illustration. No text. Rounded friendly style.
```

---

### 5.3 单词卡片正面 — 思考状态插图（小图标）

**用途：** 复习卡片正面（还没翻转时）右上角的装饰性小图标

```
Minimal flat icon of a lightbulb with a small question mark inside, soft yellow glow effect, rounded edges. Muted golden yellow color. 1:1 ratio, transparent background. Mobile UI decorative icon style.
```

---

### 5.4 记忆遗忘曲线图示

**用途：** 应用介绍页或 onboarding 中解释艾宾浩斯遗忘曲线

```
Clean educational infographic illustration of the Ebbinghaus forgetting curve, showing a smooth descending curve with review checkpoints that reset memory retention upward. Flat design, soft blue and green tones, minimalist axes labels (no specific numbers). Mobile-friendly horizontal layout. No excessive detail.
```

---

### 5.5 单词本空状态插图

**用途：** 单词列表为空时的引导页

```
Flat illustration of an open book with flowers growing out of the pages, soft botanical style. Pastel color palette (mint, blush, ivory). Gentle and inviting mood suggesting "start adding words". No text. Centered composition for mobile screen.
```

---

### 5.6 个人中心页头部背景

**用途：** Me / Profile 页顶部渐变背景装饰插图

```
Abstract flat illustration banner with geometric botanical elements — small leaves, dots, soft arcs. Horizontal layout 3:1 ratio. Colors: sage green to teal gradient with ivory accents. Minimal, non-distracting, suitable as a profile page header background.
```

---

### 5.7 App 图标（Icon）

**用途：** 应用 Logo / 浏览器 favicon

```
App icon design: a stylized open book with a small brain or neural network pattern on the page, suggesting vocabulary learning and memory. Rounded square shape. Color: deep teal (#2A7A6F) background with white icon. Clean, modern, memorable. 1024x1024px.
```

---

## 六、实施顺序建议（Codex 执行优先级）

| 优先级 | 任务 | 估计工时 |
|--------|------|---------|
| P0 | 1.1 数据库连接池 | 1h |
| P0 | 1.2 统一异常处理 | 1h |
| P0 | 2.1 全局错误拦截 | 0.5h |
| P1 | 2.2 卡片翻转动画 | 2h |
| P1 | 1.3 ReviewPolicy 单测 | 1h |
| P1 | 2.3 搜索+分页 | 1.5h |
| P1 | 3.1 数据库索引 | 0.25h |
| P2 | 2.4 Dashboard 图表 | 2h |
| P2 | 1.5 Refresh Token | 2h |
| P2 | 2.6 Pinia 状态管理 | 2h |
| P3 | 4.1 生产 Dockerfile | 1h |
| P3 | 4.3 GitHub Actions CI | 1h |
| P3 | 3.2 软删除 | 1.5h |

---

*文件由架构师于 2026-06-20 生成。Codex 请逐条执行，完成后可删除本文件。*
