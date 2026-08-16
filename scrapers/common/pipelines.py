"""
Pipeline order:
  1. ValidationPipeline      — validate against canonical schema
  2. DeduplicationPipeline   — skip already-seen listing_ids within a run
  3. JsonLinesExportPipeline — write validated items to timestamped .jsonl file
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from scrapy.exceptions import DropItem

from scrapers.common.schema import ListingItem

logger = logging.getLogger(__name__)


class ValidationPipeline:
    def __init__(self):
        self.validated = 0
        self.dropped = 0
        self.crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        return instance

    def process_item(self, item: dict):
        try:
            listing = ListingItem(**item)
            self.validated += 1
            return listing.model_dump(mode="json")
        except ValidationError as e:
            self.dropped += 1
            errors = e.errors()
            error_details = []
            for error in errors:
                field = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                error_details.append(f"{field}: {msg}")
            logger.warning(
                f"[Validation] Dropped item — URL: {item.get('url', 'N/A')} | "
                f"Errors: {'; '.join(error_details)}"
            )
            raise DropItem(f"Validation failed: {'; '.join(error_details)}")

    def close_spider(self):
        spider_name = self.crawler.spider.name if self.crawler else "Unknown"
        logger.info(
            f"[{spider_name}] ValidationPipeline: "
            f"validated={self.validated}, dropped={self.dropped}"
        )


class DeduplicationPipeline:
    def __init__(self):
        self.seen_ids: set[str] = set()
        self.duplicates = 0
        self.crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        return instance

    def __fingerprint(self, item: dict) -> str:
        key = f"{item.get('source')}::{item.get('listing_id')}"
        return hashlib.sha256(key.encode()).hexdigest()

    def process_item(self, item: dict) -> dict:
        fp = self.__fingerprint(item)
        if fp in self.seen_ids:
            self.duplicates += 1
            raise DropItem(
                f"Duplicate listing_id={item.get('listing_id')} "
                f"source={item.get('source')}"
            )
        else:
            self.seen_ids.add(fp)
            return item

    def close_spider(self):
        spider_name = self.crawler.spider.name if self.crawler else "Unknown"
        logger.info(
            f"[{spider_name}] DeduplicationPipeline: "
            f"duplicated_dropped={self.duplicates},"
        )


class JsonLinesExportPipeline:
    BASE_DIR = Path(os.getenv("RAW_DATA_DIR", "data/raw"))

    def __init__(self):
        self._file: dict[str, any] = {}
        self._counts: dict[str, int] = {}
        self._run_ts = datetime.now(tz=datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        return instance

    def open_spider(self):
        spider = self.crawler.spider
        source = getattr(spider, "source_name", spider.name)
        out_dir = self.BASE_DIR / source
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{self._run_ts}.jsonl"
        self._file[spider.name] = open(out_path, "w", encoding="utf-8")  # noqa: SIM115
        self._counts[spider.name] = 0
        logger.info(f"[{spider.name}] Writing output to {out_path}")

    def process_item(self, item: dict) -> dict:
        spider = self.crawler.spider
        f = self._file.get(spider.name)
        if f:
            f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
            self._counts[spider.name] = self._counts.get(spider.name, 0) + 1
        return item

    def close_spider(self):
        spider = self.crawler.spider
        f = self._file.pop(spider.name, None)
        if f:
            f.close()
        count = self._counts.get(spider.name, 0)
        logger.info(f"[{spider.name}] JsonLinesExportPipeline: wrote {count} items")


class MetricsPipeline:
    """
    Maintain per-spider counters for Prometheus exposition.
    """

    METRICS_PATH = Path(os.getenv("METRICS_DIR", "data/metrics"))

    def __init__(self):
        self._metrics: dict[str, dict] = {}
        self.crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        instance = cls()
        instance.crawler = crawler
        return instance

    def open_spider(self):
        spider = self.crawler.spider
        self._metrics[spider.name] = {
            "items_scraped": 0,
            "items_dropped": 0,
            "source": getattr(spider, "source_name", spider.name),
            "started_at": datetime.now(tz=datetime.timezone.utc).isoformat(),
        }

    def process_item(self, item):
        spider = self.crawler.spider
        if spider.name in self._metrics:
            self._metrics[spider.name]["items_scraped"] += 1
        return item

    def close_spider(self):
        spider = self.crawler.spider
        m = self._metrics.get(spider.name, {})
        m["finished_at"] = datetime.now(tz=datetime.timezone.utc).isoformat()

        self.METRICS_PATH.mkdir(parents=True, exist_ok=True)
        out = self.METRICS_PATH / f"{spider.name}_metrics.json"
        with open(out, "w") as f:
            json.dump(m, f, indent=2)
        logger.info(f"[{spider.name}] Metrics written to {out}")
