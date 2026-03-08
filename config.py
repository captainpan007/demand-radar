import os

MOONSHOT_API_KEY = os.environ.get("MOONSHOT_API_KEY", "")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_UA = os.environ.get("REDDIT_UA", "demand-radar/1.0")
HN_API_URL = "https://hn.algolia.com/api/v1/search"
HN_SEARCH_TERMS = ["Ask HN: Is there a tool", "Ask HN: why is there no", "I wish there was", "anyone know a tool for"]
G2_CATEGORIES = ["marketing-automation", "seo", "project-management"]
G2_DELAY_MIN = 2
G2_DELAY_MAX = 4
AI_STEP2_DELAY = 0.5
AI_MIN_SCORE = 6
