import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_UA = os.environ.get("REDDIT_UA", "demand-radar/1.0")
HN_API_URL = "https://hn.algolia.com/api/v1/search"
HN_SEARCH_TERMS = ["Ask HN: Is there a tool", "Ask HN: why is there no", "I wish there was", "anyone know a tool for"]
G2_CATEGORIES = ["marketing-automation", "seo", "project-management"]
G2_DELAY_MIN = 2
G2_DELAY_MAX = 4
AI_STEP2_DELAY = 0.5
AI_MIN_SCORE = 6  # 0-10 scale; items below 6 are filtered out

AI_TOOLS = [
    {"name": "Claude Code", "specialty": "complex business logic, API integration, security-sensitive code, algorithms hard to describe in plain language", "best_for": "core backend logic, data processing pipelines, third-party service integration"},
    {"name": "Cursor", "specialty": "UI components, repetitive code, project scaffolding, multi-file edits", "best_for": "frontend interfaces, CRUD features, styling"},
    {"name": "Gemini", "specialty": "very long context, large document analysis, auxiliary tasks within free tier", "best_for": "document processing, market research analysis, content generation"},
    {"name": "Windsurf", "specialty": "large-scale refactors, cross-file understanding, codebase-level changes", "best_for": "legacy code refactoring, large project iteration"},
    {"name": "Bolt.new", "specialty": "rapid prototyping, landing pages, simple full-stack tools", "best_for": "MVP validation, landing pages, simple SaaS prototypes"},
    {"name": "Firecrawl", "specialty": "web scraping, structured data extraction, site content harvesting", "best_for": "data-collection products, competitor monitoring, content aggregation"},
    {"name": "v0", "specialty": "fast UI component generation, Tailwind layouts, React components", "best_for": "quickly generating high-quality frontend components"},
    {"name": "Replit", "specialty": "online deployment, fast launch, small tools with no local environment needed", "best_for": "small products that need quick deployment validation"},
]

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
PRODUCTHUNT_API_KEY = os.environ.get("PRODUCTHUNT_API_KEY", "")

# Web app
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

# Lemon Squeezy
LEMON_SQUEEZY_SIGNING_SECRET = os.environ.get("LEMON_SQUEEZY_SIGNING_SECRET", "")
LEMON_SQUEEZY_CHECKOUT_URL = os.environ.get("LEMON_SQUEEZY_CHECKOUT_URL", "")

# Access limits
VISITOR_LIMIT = 3
FREE_LIMIT = 5
