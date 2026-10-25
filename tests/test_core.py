from pathlib import Path

from deal_watcher.core import Deal, WatchItem, fetch_feed, matches, parse_price


def test_parse_price_uses_dollar_price_and_handles_commas():
    assert parse_price("Laptop was $1,399.99, now $999.00") == 999.00
    assert parse_price("Save 20% today") is None


def test_match_requires_every_keyword_target_and_retailer():
    item = WatchItem("Sony headphones", ("sony", "wh-1000xm6"), 300, ("bestbuy",))
    deal = Deal("Sony WH-1000XM6 headphones", 299.99, "bestbuy", "https://x", "")
    assert matches(item, deal)
    assert not matches(item, Deal(deal.title, 300.01, "bestbuy", deal.link, ""))
    assert not matches(item, Deal(deal.title, 299.99, "amazon", deal.link, ""))


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
