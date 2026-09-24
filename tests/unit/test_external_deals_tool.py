from app.agent import fetch_external_deals


def test_fetch_external_deals():
    deals = fetch_external_deals(limit=3)
    assert isinstance(deals, list)
    assert len(deals) > 0
    first_deal = deals[0]
    assert "title" in first_deal
    assert "price" in first_deal
    assert "id" in first_deal
