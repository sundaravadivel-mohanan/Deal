from pathlib import Path

from deal_watcher.core import Deal, WatchItem, fetch_feed, infer_retailer, matches, parse_price
from deal_watcher.notify import send_digest


def test_parse_price_uses_dollar_price_and_handles_commas():
    assert parse_price("Laptop was $1,399.99, now $999.00") == 999.00
    assert parse_price("Save 20% today") is None


def test_match_requires_every_keyword_target_and_retailer():
    item = WatchItem("Sony headphones", ("sony", "wh-1000xm6"), 300, ("bestbuy",))
    deal = Deal("Sony WH-1000XM6 headphones", 299.99, "bestbuy", "https://x", "")
    assert matches(item, deal)
    assert not matches(item, Deal(deal.title, 300.01, "bestbuy", deal.link, ""))
    assert not matches(item, Deal(deal.title, 299.99, "amazon", deal.link, ""))


def test_ps5_keyword_matches_playstation_5_spelling():
    item = WatchItem("PS5 Console", ("ps5", "console"), 600, ("target",))
    deal = Deal("PlayStation 5 console bundle", 599.99, "target", "https://x", "")
    assert matches(item, deal)


def test_feed_fixture_is_parsed(monkeypatch):
    class Response:
        content = Path("tests/fixtures/deals.xml").read_bytes()
        def raise_for_status(self): pass
    class Session:
        def get(self, *args, **kwargs): return Response()
    deals = fetch_feed("https://example.test/rss", Session())
    assert len(deals) == 2
    assert deals[0].retailer == "bestbuy"
    assert deals[0].price == 299.99


def test_costco_is_inferred_from_its_url():
    assert infer_retailer("Nintendo Switch 2", "https://www.costco.com/example.html") == "costco"


def test_github_issue_notification_mentions_configured_user(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self): pass

    def post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setenv("NOTIFICATION_CHANNEL", "github_issue")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_NOTIFY_USER", "sundaravadivel-mohanan")
    monkeypatch.setattr("deal_watcher.notify.requests.post", post)
    send_digest([{"item": "Switch 2", "price": 449.99, "target": 449.99,
                  "retailer": "costco", "link": "https://example.test", "lowest": True}])
    assert captured["url"] == "https://api.github.com/repos/owner/repo/issues"
    assert captured["json"]["body"].startswith("@sundaravadivel-mohanan")
