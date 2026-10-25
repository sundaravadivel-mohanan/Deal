# November Tech Deal Watcher

A feed-first, self-hosted watcher for Black Friday (November 27, 2026) and Cyber Monday (November 30, 2026). It looks for watchlist matches at or below your price target, keeps a local price history, and sends one digest per run only when there are new or lower-priced matches.

## Setup

1. Install Python 3.12 and dependencies: `python -m pip install -r requirements-dev.txt`.
2. Replace the commented example in `watchlist.yaml` with your products. A deal must contain **every** keyword in its title, meet the target price, and (when specified) match an allowed retailer.
3. Test locally: `python -m pytest`.
4. Run locally: `python main.py`. With no notification channel set, a matching digest prints to stdout.

The initial source is Slickdeals' frontpage RSS. Add approved RSS feeds or official retailer/API feeds with repeated `--feed URL` flags, or set the `DEAL_FEEDS` repository variable to a comma-separated list. The watcher intentionally does not scrape retailer pages or sites that block automated collection. A broken source is logged and does not stop other sources.

## Notifications and GitHub Actions

The workflow runs every six hours from November 20 through November 30 (UTC), plus on-demand. Add one of these secret sets in GitHub Actions:

| Channel | Required secrets |
| --- | --- |
| Microsoft Teams | `NOTIFICATION_CHANNEL=teams`, `TEAMS_WEBHOOK_URL` |
| SMTP email | `NOTIFICATION_CHANNEL=smtp`, `SMTP_HOST`, `SMTP_PORT` (optional; defaults to 465), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TO` |

The workflow commits `data/seen.json` and `data/price_history.csv` back to the repository. `seen.json` records the lowest alert price per entry URL, so a previously alerted item only alerts again if its price drops. `price_history.csv` records `date,item,retailer,price`; each alert says whether it beats the prior historical low for that item.

GitHub may delay scheduled workflows during periods of high load. Its cron times are UTC; choose feeds and schedule expectations accordingly. The workflow has `contents: write` permission, so enable read/write workflow permissions in the repository Actions settings if it is disabled.

## Safety and source policy

Requests identify themselves with a descriptive User-Agent, use a 20-second timeout, and only collect configured RSS/approved HTTP sources. It has no account login, buying, or bot-protection bypass behavior. Do not add sources whose robots.txt or terms prohibit automated access.
