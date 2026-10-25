from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path

from deal_watcher.core import DEFAULT_FEEDS, append_history, collect_matches, historical_low, load_seen, load_watchlist, write_seen
from deal_watcher.notify import send_digest


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch RSS feeds for targeted tech deals.")
    parser.add_argument("--watchlist", type=Path, default=Path("watchlist.yaml"))
    parser.add_argument("--state-dir", type=Path, default=Path("data"))
    parser.add_argument("--feed", action="append", dest="feeds", help="RSS URL (repeatable)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    items = load_watchlist(args.watchlist)
    if not items:
        logger.warning("Watchlist is empty; nothing to monitor.")
        return 0
    args.state_dir.mkdir(parents=True, exist_ok=True)
    seen_path, history_path = args.state_dir / "seen.json", args.state_dir / "price_history.csv"
    configured_feeds = args.feeds or [feed.strip() for feed in os.getenv("DEAL_FEEDS", "").split(",") if feed.strip()]
    feeds = configured_feeds or list(DEFAULT_FEEDS)
    candidates = collect_matches(items, feeds, logger)
    seen = load_seen(seen_path)
    alerts, history_rows = [], []
    for item, deal in candidates:
        history_rows.append((item.name, deal))
        previous_alert = seen.get(deal.link)
        if previous_alert is not None and deal.price >= previous_alert:
            continue
        prior_low = historical_low(history_path, item.name)
        alerts.append({
            "item": item.name, "price": deal.price, "target": item.target_price,
            "retailer": deal.retailer, "link": deal.link,
            "lowest": prior_low is None or deal.price < prior_low,
        })
        seen[deal.link] = deal.price
    append_history(history_path, history_rows)
    write_seen(seen_path, seen)
    send_digest(alerts)
    logger.info("Processed %d candidate(s), sent %d alert(s).", len(candidates), len(alerts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
