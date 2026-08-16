"""
Custom Scrapy middlewares for the TuniCars scraping layer.

Middlewares included:
  - RotatingUserAgentMiddleware   : randomize User-Agent per request
  - SmartRetryMiddleware          : exponential backoff with jitter on 429/5xx
  - RateLimitMiddleware           : per-domain request throttle
  - PlaywrightFallbackMiddleware  : flag JS-heavy pages for Playwright rendering
"""

from __future__ import annotations

import logging
import random
import time

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.http import Request, Response
from scrapy.utils.response import response_status_message

logger = logging.getLogger(__name__)


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
]


class RotatingUserAgentMiddleware:
    def process_request(self, request: Request) -> None:
        request.headers["User-Agent"] = random.choice(USER_AGENTS)  # nosec B311
        request.headers.setdefault(
            "Accept-Language", "fr-TN,fr;q=0.9,ar-TN;q=0.8,en;q=0.7"
        )
        request.headers.setdefault(
            "Accept",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
            "image/webp,*/*;q=0.8",
        )


class SmartRetryMiddleware(RetryMiddleware):
    """
    Extends Scrapy's built-in RetryMiddleware with:
      - Exponential backoff + random jitter on 429 / 503
      - Configurable max-wait cap
      - Per-spider retry stat counters
    """

    def __init__(self, crawler):
        super().__init__(crawler.settings)
        self.crawler = crawler

        self.BACKOFF_BASE = 2  # seconds — base for exponential calc
        self.BACKOFF_MAX = 120  # seconds — upper cap
        self.JITTER_RANGE = 5  # seconds — random noise added to backoff

        self.RETRY_HTTP_CODES = {429, 500, 502, 503, 504, 522, 524}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_response(
        self, request: Request, response: Response
    ) -> Request | Response:
        if response.status in self.RETRY_HTTP_CODES:
            spider = self.crawler.spider
            retry_count = request.meta.get("retry_times", 0)
            wait = min(
                self.BACKOFF_BASE**retry_count
                + random.uniform(0, self.JITTER_RANGE),  # nosec B311
                self.BACKOFF_MAX,
            )
            logger.warning(
                f"[{spider.name}] HTTP {response.status} on {request.url} "
                f"— retry #{retry_count + 1}, waiting {wait:.1f}s"
            )
            time.sleep(wait)
            return (
                self.retry(request, response_status_message(response.status), spider)
                or response
            )

        return response

    def process_exception(
        self, request: Request, exception: Exception
    ) -> Request | None:
        spider = self.crawler.spider
        retry_count = request.meta.get("retry_times", 0)
        wait = min(
            self.BACKOFF_BASE**retry_count
            + random.uniform(0, self.JITTER_RANGE),  # nosec B311
            self.BACKOFF_MAX,
        )
        logger.warning(
            f"[{spider.name}] Exception {type(exception).__name__} on {request.url} "
            f"— retry #{retry_count + 1}, waiting {wait:.1f}s"
        )
        time.sleep(wait)
        return super().process_exception(request, exception)


class RateLimitMiddleware:
    """
    Enforce per-domain minimum delay between requests.
    Configured via spider's DOMAIN_DELAYS dict or falls back to
    DOWNLOAD_DELAY in settings.
    """

    DEFAULT_DELAY = 3.0  # seconds

    def __init__(self, default_delay: float = DEFAULT_DELAY):
        self.default_delay = default_delay
        self._last_request_time: dict[str, float] = {}
        self.spider = None

    @classmethod
    def from_crawler(cls, crawler):
        delay = crawler.settings.getfloat("DOWNLOAD_DELAY", cls.DEFAULT_DELAY)
        instance = cls(default_delay=delay)
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        return instance

    def spider_opened(self, spider):
        self.spider = spider

    def process_request(self, request: Request) -> None:
        domain = request.url.split("/")[2]
        domain_delays: dict = (
            getattr(self.spider, "DOMAIN_DELAYS", {}) if self.spider else {}
        )
        delay = domain_delays.get(domain, self.default_delay)

        last = self._last_request_time.get(domain, 0)
        elapsed = time.monotonic() - last
        if elapsed < delay:
            sleep_time = delay - elapsed + random.uniform(0, 1.0)  # nosec B311
            time.sleep(sleep_time)

        self._last_request_time[domain] = time.monotonic()


class PlaywrightFallbackMiddleware:
    """
    This is a safety net for spiders that don't explicitly
    use scrapy-playwright — it detects accidental JS pages.
    """

    def __init__(self):
        self.spider = None

        self.MIN_BODY_SIZE = 500
        self.JS_MARKERS = [
            b'<div id="root"></div>',
            b'<div id="app"></div>',
            b"__NEXT_DATA__",
            b"window.__NUXT__",
        ]

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        crawler.signals.connect(instance.spider_opened, signal=signals.spider_opened)
        return instance

    def spider_opened(self, spider):
        self.spider = spider

    def process_response(
        self, request: Request, response: Response
    ) -> Request | Response:
        if request.meta.get("playwright"):
            return response

        spider_name = self.spider.name if self.spider else "unknown"
        body = response.body
        is_empty_shell = len(body) < self.MIN_BODY_SIZE
        has_js_marker = any(marker in body for marker in self.JS_MARKERS)

        if is_empty_shell or has_js_marker:
            logger.info(
                f"[{spider_name}] JS-rendered page detected at {request.url} "
                "— re-queuing with Playwright"
            )
            new_request = request.replace(
                meta={
                    **request.meta,
                    "playwright": True,
                    "playwright_include_page": True,
                }
            )
            return new_request

        return response


class StatsLoggerMiddleware:
    """Emit per-spider per-domain request counters for Prometheus scraping."""

    def __init__(self):
        self.counts: dict[str, int] = {}
        self.spider = None

    @classmethod
    def from_crawler(cls, crawler):
        ext = cls()
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_opened(self, spider):
        self.spider = spider

    def process_response(self, request: Request, response: Response) -> Response:
        spider_name = self.spider.name if self.spider else "unknown"
        domain = request.url.split("/")[2]
        key = f"{spider_name}::{domain}::{response.status}"
        self.counts[key] = self.counts.get(key, 0) + 1
        return response

    def spider_closed(self, spider):
        for key, count in self.counts.items():
            logger.info(f"[stats] {key} = {count}")
