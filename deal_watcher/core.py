from __future__ import annotations

import csv
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import feedparser
import requests
import yaml

USER_AGENT = "NovemberTechDealWatcher/1.0 (+https://github.com/your-org/november-tech-deal-watcher)"
DEFAULT_FEEDS = (
    "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
)
RETAILERS = ("amazon", "bestbuy", "walmart", "target")


@dataclass(frozen=True)
class WatchItem:
    name: str
    keywords: tuple[str, ...]
    target_price: float
    retailers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Deal:
    title: str
    price: float
    retailer: str
    link: str
    timestamp: str


def load_watchlist(path: Path) -> list[WatchItem]:
    data = yaml.safe_load(path.read_text()) or {}
    items = []
    for raw in data.get("items", []):
        try:
            item = WatchItem(
                name=str(raw["name"]),
                keywords=tuple(str(word).lower() for word in raw["keywords"]),
                target_price=float(raw["target_price"]),
                retailers=tuple(str(store).lower() for store in raw.get("retailers", [])),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"Invalid watchlist entry: {raw!r}") from error
        if not item.keywords:
            raise ValueError(f"Watchlist item {item.name!r} has no keywords")
        items.append(item)
    return items


def parse_price(text: str) -> float | None:
    """Return the first plausible USD sale price from a feed title."""
    # Avoid treating coupon percentages, storage sizes, and MSRP ranges as prices.
    candidates = re.findall(r"(?<![\w.])\$\s*(\d{1,5}(?:,\d{3})*(?:\.\d{1,2})?)", text)
    if not candidates:
        return None
    return float(candidates[-1].replace(",", ""))


def infer_retailer(title: str, link: str) -> str:
    value = f"{title} {urlparse(link).netloc}".lower().replace("-", "")
    for retailer in RETAILERS:
        if retailer.replace("-", "") in value:
            return retailer
    return "unknown"


def matches(item: WatchItem, deal: Deal) -> bool:
    title = deal.title.lower()
    return (
        all(keyword in title for keyword in item.keywords)
        and deal.price <= item.target_price
        and (not item.retailers or deal.retailer in item.retailers)
    )


def fetch_feed(url: str, session: requests.Session) -> list[Deal]:
    response = session.get(url, timeout=20)
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"Malformed feed: {parsed.bozo_exception}")
    deals = []
    for entry in parsed.entries:
        title = str(entry.get("title", "")).strip()
        link = str(entry.get("link", "")).strip()
        price = parse_price(title)
        if not title or not link or price is None:
            continue
        deals.append(Deal(
            title=title,
            price=price,
            retailer=infer_retailer(title, link),
            link=link,
            timestamp=str(entry.get("published", entry.get("updated", ""))),
        ))
    return deals


def load_seen(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {str(link): float(price) for link, price in raw.items()}


def write_seen(path: Path, seen: dict[str, float]) -> None:
    path.write_text(json.dumps(seen, indent=2, sort_keys=True) + "\n")


def historical_low(path: Path, item_name: str) -> float | None:
    if not path.exists():
        return None
    prices = []
    with path.open(newline="") as file:
        for row in csv.DictReader(file):
            if row.get("item") == item_name:
                try:
                    prices.append(float(row["price"]))
                except (KeyError, ValueError):
                    continue
    return min(prices) if prices else None


def append_history(path: Path, rows: Iterable[tuple[str, Deal]]) -> None:
    exists = path.exists()
    with path.open("a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["date", "item", "retailer", "price"])
        if not exists:
            writer.writeheader()
        date = datetime.now(timezone.utc).date().isoformat()
        for item_name, deal in rows:
            writer.writerow({"date": date, "item": item_name, "retailer": deal.retailer, "price": f"{deal.price:.2f}"})


def collect_matches(items: list[WatchItem], feed_urls: Iterable[str], logger: logging.Logger) -> list[tuple[WatchItem, Deal]]:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    deals: list[Deal] = []
    for url in feed_urls:
        try:
            deals.extend(fetch_feed(url, session))
        except (requests.RequestException, ValueError) as error:
            logger.warning("Skipping failed source %s: %s", url, error)
    return [(item, deal) for item in items for deal in deals if matches(item, deal)]
