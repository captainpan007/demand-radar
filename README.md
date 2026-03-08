# 需求雷达 Demand Radar

从 Hacker News、Reddit、G2 抓取内容，用 Claude AI 过滤有商业潜力的产品需求，生成 HTML 报告。

## 快速开始

```bash
cd demand-radar
pip install -r requirements.txt
# 首次使用 G2 需安装浏览器: playwright install chromium
set MOONSHOT_API_KEY=your_key
python main.py
```

仅配置 `MOONSHOT_API_KEY` 即可运行（HN 无需 Key）。报告输出到 `output/demand-radar-YYYY-MM-DD.html`。

## 环境变量

| 变量 | 说明 |
|------|------|
| MOONSHOT_API_KEY | 必填，Kimi API，AI 过滤 |
| REDDIT_CLIENT_ID | 可选，Reddit API |
| REDDIT_CLIENT_SECRET | 可选 |
| REDDIT_UA | 可选，默认 demand-radar/1.0 |

## 目录结构

```
demand-radar/
├── main.py          # 主入口
├── config.py        # 配置
├── models.py        # 数据模型
├── scrapers/        # HN、Reddit、G2 抓取
├── processor/       # 清洗、AI 过滤
├── reporter/        # HTML 报告
└── output/          # 报告输出
```
