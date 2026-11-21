# Vocab App MVP

手机端优先的全栈背单词 App。第一阶段实现最小可用版本：注册、登录、添加单词、词库、今日复习、艾宾浩斯复习阶段推进。

现在后端改为 Python + FastAPI，并按轻量 DDD 分层组织。前端接口不变，所以 Vue 页面可以继续使用。

## 1. 项目目录结构

```text
vocab-app/
├── frontend/                     # Vue3 + TypeScript + Vite + Vant
│   └── src/
│       ├── app/                  # App 级配置：router、layout
│       ├── features/             # 业务功能：auth、words、reviews
│       ├── pages/                # 路由页面：home、auth、words、reviews、me
│       └── shared/               # 通用能力：api、styles、types
├── backend/                      # Python + FastAPI + DDD
│   ├── app/
│   │   ├── domain/               # 领域层：实体、仓储接口、复习规则
│   │   ├── application/          # 应用层：注册、登录、单词、复习用例
│   │   ├── infrastructure/       # 基础设施层：MySQL、JWT、密码哈希
│   │   └── interfaces/           # 接口层：HTTP 路由、依赖注入、统一响应
│   ├── scripts/                  # 测试账号脚本
│   ├── requirements.txt
│   └── Dockerfile
├── database/
│   └── schema.sql                # MySQL 建表 SQL
├── docker-compose.yml
└── README.md
```

你应该学习：前端用 `app / features / pages / shared`，后端用 DDD 的 `domain / application / infrastructure / interfaces`。两边都不是为了复杂，而是为了让简历项目看起来有清晰边界。

## 2. 前端目录怎么读

当前前端结构更接近澳洲中小型团队常见的 Vue 项目写法：

```text
src/
├── app/
│   ├── layouts/                  # App 外壳，例如底部 TabBar
│   └── router/                   # 路由表和登录守卫
├── features/
│   ├── auth/                     # 登录注册相关 API 和 token store
│   ├── words/                    # 单词相关 API 和后续业务组件
│   └── reviews/                  # 复习相关 API 和后续业务组件
├── pages/
│   ├── auth/                     # LoginPage、RegisterPage
│   ├── home/                     # HomePage
│   ├── words/                    # AddWordPage、WordListPage
│   ├── reviews/                  # TodayReviewPage
│   └── me/                       # MePage
└── shared/
    ├── api/                      # axios 实例、统一请求处理
    ├── styles/                   # 全局样式
    └── types/                    # 通用 TypeScript 类型
```

你应该学习：`pages` 只负责页面组合，`features` 放具体业务能力，`shared` 放可复用工具。这样以后加“错词本”“复习历史”时，不会把所有代码都塞进 `views`。

## OpenCV / OCR 图片提词功能

本项目新增了一个面向 Cloud + Edge 场景的图片提词 Demo，用来展示“边缘采集 -> 后端处理 -> 前端展示”的数据流。

### 功能入口

登录后进入首页，点击：

```text
Extract words from image / 图片提取单词
```

页面路径：

```text
/vision
```

用户可以上传截图、书页、路牌或英文材料图片，后端会：

1. 使用 OpenCV 解码图片
2. 转灰度图
3. 放大低分辨率图片
4. 降噪
5. 自适应阈值处理
6. 使用 Tesseract OCR 识别英文文本
7. 从 OCR 文本中提取英文单词候选

### 后端接口

```http
POST /api/vision/extract-words
Content-Type: multipart/form-data
Authorization: Bearer <token>

image=<file>
```

返回示例：

```json
{
  "success": true,
  "data": {
    "text": "Evidence suggests that...",
    "words": [
      { "word": "evidence", "count": 1 },
      { "word": "suggests", "count": 1 }
    ],
    "preprocessing": ["decode", "grayscale", "upscale", "denoise", "adaptive-threshold"],
    "engine": "opencv + tesseract"
  },
  "message": "Words extracted from image"
}
```

### 本地运行要求

Python 依赖：

```bash
pip install -r backend/requirements.txt
```

如果直接在本机运行后端，还需要安装 Tesseract OCR 引擎。

Docker 后端镜像已经在 `backend/Dockerfile` 中安装：

```text
tesseract-ocr
```

所以推荐通过 Docker 运行：

```bash
docker compose up --build
```

### 简历表达

这个功能可以在简历里描述为：

```text
Implemented an image-based vocabulary ingestion workflow using Python, OpenCV preprocessing, Tesseract OCR and FastAPI, simulating an edge-to-cloud data capture pipeline.
```

## 3. 前端初始化命令

如果从零手动创建：

```bash
mkdir vocab-app
cd vocab-app
npm create vite@latest frontend -- --template vue-ts
cd frontend
npm install
npm install vant axios vue-router
```

当前项目已经生成好，运行：

```bash
cd vocab-app/frontend
npm install
npm run dev
```

你应该学习：Vite 负责本地开发服务器和打包，Vue Router 负责页面切换，Vant 提供移动端组件。

## 4. 后端初始化命令

如果从零手动创建 Python 后端：

```bash
mkdir backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install fastapi "uvicorn[standard]" pymysql python-dotenv pydantic-settings bcrypt "python-jose[cryptography]" email-validator
```

当前项目已经生成好，运行：

```bash
cd vocab-app/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
```

你应该学习：FastAPI 负责 HTTP API；PyMySQL 负责连接 MySQL；bcrypt 负责密码哈希；python-jose 负责 JWT。

## 5. Python DDD 后端怎么读

推荐阅读顺序：

```text
interfaces/http/routes/auth_routes.py
application/services/auth_service.py
domain/repositories/user_repository.py
infrastructure/repositories/mysql_user_repository.py
infrastructure/security/password_hasher.py
infrastructure/security/jwt_service.py
```

对应职责：

- `interfaces`：接收 HTTP 请求，返回统一 JSON。
- `application`：组织一个具体用例，例如注册、登录、添加单词。
- `domain`：描述核心业务规则，例如艾宾浩斯复习策略。
- `infrastructure`：实现 MySQL 查询、JWT、密码加密等技术细节。

你应该学习：路由不直接写 SQL，业务规则不依赖 FastAPI，这样项目更像真实简历项目。

## 6. 数据库 SQL

数据库脚本：

```text
database/schema.sql
```

核心表：

- `users`：保存用户账号和加密后的密码。
- `words`：保存当前用户的单词、释义、例句、来源。
- `review_records`：保存每个单词的复习阶段、上次复习时间、下次复习时间。

你应该学习：`words.user_id` 和 `review_records.user_id` 用来隔离不同用户的数据。

## 7. 后端接口

统一响应格式：

```json
{
  "success": true,
  "data": {},
  "message": ""
}
```

已实现接口：

```text
POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/me
GET    /api/words
POST   /api/words
PUT    /api/words/:id
DELETE /api/words/:id
GET    /api/reviews/today
POST   /api/reviews/:wordId/submit
```

需要登录的接口要带请求头：

```text
Authorization: Bearer <token>
```

你应该学习：前端保存 token，Axios 拦截器自动带上 token，后端 `get_current_user` 负责验证 token。

## 8. 艾宾浩斯复习规则

复习间隔：

```text
0 天、1 天、3 天、7 天、15 天、30 天
```

实现逻辑：

- 新增单词：`review_stage = 0`，`next_review_at = NOW()`，今天就能复习。
- 点击“认识”：进入下一阶段，并按新阶段计算下次复习时间。
- 点击“模糊”：阶段不变，明天继续复习。
- 点击“不认识”：回到第 1 阶段，明天重新复习。

代码位置：

```text
backend/app/domain/services/review_policy.py
```

你应该学习：复习规则属于核心业务，所以放在 `domain`，而不是放在路由或数据库代码里。

## 9. Docker 本地运行

先启动 Docker Desktop，然后运行：

```bash
cd vocab-app
docker compose up --build
```

访问：

```text
前端：http://localhost:5173
后端：http://localhost:3000/api/health
接口文档：http://localhost:3000/docs
MySQL：localhost:3307
```

创建测试账号：

```bash
docker compose exec backend python scripts/seed_test_user.py
```

你应该学习：Docker Compose 同时启动 MySQL、Python 后端、Vue 前端。后续加 Nginx 时，可以把前端构建结果交给 Nginx 托管。

## 10. 不用 Docker 的本地运行

先启动 MySQL，并执行：

```bash
mysql -uroot -p < database/schema.sql
```

后端：

```bash
cd vocab-app/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/seed_test_user.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
```

前端：

```bash
cd vocab-app/frontend
npm install
npm run dev
```

访问：

```text
http://localhost:5173
```

你应该学习：前端 Vite 通过 `vite.config.ts` 把 `/api` 代理到后端，所以页面里不用写死后端地址。

Navicat 连接 Docker MySQL 时使用：

```text
Host: localhost
Port: 3307
User: root
Password: rootpassword
Database: vocab_app
```

注意：Docker 外部用 `3307`，但后端容器内部仍然用 `DB_PORT=3306` 连接 `mysql` 服务，这是 Docker 网络的内部端口。

## 11. 测试账号和测试流程

测试账号：

```text
email: test@example.com
password: 123456
```

测试流程：

1. 打开 `http://localhost:5173`。
2. 使用测试账号登录，或者注册一个新账号。
3. 进入“首页”，点击“添加单词”。
4. 添加一个单词，例如：
   - word: evidence
   - meaning: 证据；迹象
   - example: There is clear evidence that practice improves memory.
   - source: IELTS Reading
5. 进入“词库”，确认单词出现。
6. 点击单词可修改；左滑单词可删除。
7. 进入“复习”，点击“认识 / 模糊 / 不认识”。
8. 回到首页，观察“待复习单词”数量变化。

你应该学习：从页面操作开始，跟踪前端 `api` 文件、后端 route、application service、repository，最后看数据库表的变化。

## 12. 第一阶段不要做的事

本 MVP 暂时不加入：

- AI 自动生成例句
- Prometheus 监控
- Kubernetes
- Nginx
- 复杂统计图表

下一阶段适合做：

- 单词搜索
- 复习历史
- 错词本
- Docker 生产构建
- Nginx 反向代理
- GitHub Actions CI

## Longman 离线词典

项目已经接入 `GET /api/dictionary/lookup?word=evidence`，前端单词查询会优先读取本地 Longman 数据，再退回在线词典。

完整 `.mdx/.mdd` 导入步骤见：

```text
docs/longman-offline-dictionary.md
```
