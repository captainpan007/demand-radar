# Demand Radar（需求雷达）

每日自动爬取开发者社区的真实需求信号，用 AI 评分筛选，生成可执行的产品机会报告，帮助独立开发者找到值得做的产品方向。

## 解决什么问题

独立开发者最大的痛点不是"不会做"，而是"不知道做什么"。Hacker News、Product Hunt、IndieHackers 等社区每天有大量用户在抱怨问题、寻找工具，但这些信号散落各处，人工筛选效率极低。Demand Radar 自动化了这个过程：爬取 → 清洗 → AI 评分 → 生成报告。

## 技术架构

```
数据源 → 爬虫层 → 去重清洗 → AI评分 → 中文翻译 → PostgreSQL → FastAPI Web UI
```

**Pipeline 四阶段：**

1. **爬取**（`scrapers/`）：HN（Algolia API）、Product Hunt（GraphQL API）、IndieHackers（Playwright 无头浏览器）
2. **清洗**（`processor/cleaner.py`）：MD5 去重、截断过长内容
3. **AI 评分**（`processor/ai_filter.py`）：调用 DeepSeek-V3，4维评分体系（痛感 0-3 + 付费意愿 0-3 + 可执行性 0-2 + 触达清晰度 0-2，满分10），低于6分淘汰，附带硬性否决规则（无付费先例/需要团队/大厂已覆盖/实体商品）
4. **中文翻译**（`processor/translator.py`）：用 DeepSeek 批量翻译8个字段，支持中英双语切换

**每条通过筛选的需求包含：**
- `demand_summary`：一句话痛点总结
- `target_user`：目标用户画像
- `commercial_score`：商业化评分（6-10）
- `score_detail`：四维明细分
- `product_idea`：最小可行产品形态
- `build_days`：预估开发天数
- `tool_plan`：推荐 AI 工具组合（从8个工具库中选2-4个）
- `cost_estimate`：API 成本估算
- `biggest_risk`：最大执行风险

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI + Uvicorn |
| 模板引擎 | Jinja2（暗色卡片网格 UI，支持 EN/ZH 切换）|
| 数据库 | PostgreSQL（Railway 托管），本地开发可用 SQLite |
| AI | DeepSeek-V3（评分 + 翻译，OpenAI-compatible API）|
| 爬虫 | httpx + Playwright（IndieHackers）|
| 认证 | Google OAuth（Authlib）|
| 支付 | Lemon Squeezy（$9/月订阅，webhook 回调）|
| 定时任务 | APScheduler（每日 UTC 06:00）|
| 部署 | Railway（Docker，自动部署）|
| 落地页 | GitHub Pages（`docs/index.html`）|

## 商业模式（三级访问）

| 层级 | 权限 |
|---|---|
| 游客 | 看 3 条 |
| 免费用户（Google 登录）| 看 5 条 |
| Pro 用户（$9/月）| 全部内容 + 历史报告 + 关键词搜索 |

## 项目结构

```
demand-radar/
├── app.py                  # FastAPI 主应用（路由、中间件、admin API）
├── pipeline.py             # 爬取 pipeline 编排（4阶段）
├── config.py               # 环境变量 + 常量配置
├── database.py             # SQLAlchemy 模型（User/Session/Subscription/Demand）
├── storage.py              # DB 读写层（save/query/search）
├── models.py               # 数据类（RawItem, DemandItem）
├── auth.py                 # Google OAuth 登录/登出
├── webhook.py              # Lemon Squeezy 支付回调
├── scrapers/
│   ├── hn.py               # Hacker News（Algolia API）
│   ├── producthunt.py      # Product Hunt（GraphQL）
│   ├── indiehackers.py     # IndieHackers（Playwright）
│   ├── reddit.py           # Reddit（PRAW，未激活）
│   └── g2.py               # G2 Reviews（Playwright，未激活）
├── processor/
│   ├── cleaner.py          # 去重 + 清洗
│   ├── ai_filter.py        # DeepSeek AI 评分（5并发）
│   └── translator.py       # DeepSeek 中文翻译（5并发）
├── reporter/
│   ├── template.html       # 主报告页（卡片网格 UI）
│   ├── pricing.html        # 定价页
│   └── search.html         # 搜索页
├── docs/
│   └── index.html          # GitHub Pages 落地页
├── Dockerfile              # 生产镜像
├── railway.toml            # Railway 部署配置
└── requirements.txt        # Python 依赖
```

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 配置环境变量（复制 .env.example 或手动设置）
export DEEPSEEK_API_KEY="..."
export PRODUCTHUNT_API_KEY="..."

# 本地运行（SQLite，无需 PostgreSQL）
python app.py
# 访问 http://localhost:8000
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | AI 评分 + 翻译 |
| `PRODUCTHUNT_API_KEY` | 是 | Product Hunt 数据源 |
| `GOOGLE_CLIENT_ID` | 是 | OAuth 登录 |
| `GOOGLE_CLIENT_SECRET` | 是 | OAuth 登录 |
| `SECRET_KEY` | 是 | Session 加密 |
| `BASE_URL` | 是 | 生产 URL |
| `LEMON_SQUEEZY_CHECKOUT_URL` | 是 | 支付链接 |
| `LEMON_SQUEEZY_SIGNING_SECRET` | 是 | Webhook 签名验证 |
| `ADMIN_TOKEN` | 是 | Admin API 鉴权 |
| `DATABASE_URL` | 否 | PostgreSQL 连接串（Railway 自动注入，留空则用 SQLite）|

## Admin API

```bash
# 触发 pipeline（后台运行，立即返回）
curl -X POST https://<your-domain>/admin/run-pipeline \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# 删除今日数据并重跑
curl -X POST https://<your-domain>/admin/rerun-today \
  -H "Authorization: Bearer <ADMIN_TOKEN>"

# 查看 pipeline 状态
curl https://<your-domain>/admin/pipeline-status \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

## 当前状态（2026-03-11）

- **已上线**：https://demand-radar-production.up.railway.app
- **落地页**：GitHub Pages
- **活跃数据源**：HN、Product Hunt、IndieHackers
- **日产出**：约 44 条合格需求信号（从 ~99 条原始数据中筛选）
- **已完成安全审计**：webhook 签名验证、admin 端点鉴权、cookie Secure 标志、ILIKE 注入防护
- **待做**：速率限制、过期 session 清理、Reddit/G2 数据源激活
