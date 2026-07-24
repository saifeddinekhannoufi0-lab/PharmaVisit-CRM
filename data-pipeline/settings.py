# Scrapy settings for the PharmaVisit data pipeline
# Scrapy docs: https://docs.scrapy.org/en/latest/topics/settings.html

BOT_NAME = "pharmavisit_scraper"
SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"

# ── Nominatim ToS compliance ──────────────────────────────────────────────────
# We use a descriptive User-Agent as required by Nominatim's usage policy.
USER_AGENT = "PharmaVisitCRM/1.0 DataPipeline (contact@pharmavisit.ma)"

# Obey robots.txt by default
ROBOTSTXT_OBEY = True

# ── Rate limiting ─────────────────────────────────────────────────────────────
# 1 request every 2 seconds — polite scraping
DOWNLOAD_DELAY = 2
RANDOMIZE_DOWNLOAD_DELAY = True  # actual delay = 1–3s (more human-like)
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# ── Auto-throttle ─────────────────────────────────────────────────────────────
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# ── Output ────────────────────────────────────────────────────────────────────
# Note: FEED_URI/FEED_FORMAT deprecated in Scrapy 2.4+; use FEEDS dict instead
FEEDS = {
    "output/raw_doctors.csv": {"format": "csv", "encoding": "utf-8", "overwrite": True},
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
