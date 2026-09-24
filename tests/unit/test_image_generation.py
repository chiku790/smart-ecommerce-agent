import urllib.request
from unittest.mock import MagicMock
import pytest
from app.agent import generate_product_image, BUCKET_NAME


@pytest.mark.asyncio
async def test_generate_product_image():
    mock_context = MagicMock()
    mock_context.save_artifact = MagicMock()
    res = await generate_product_image(
        prompt="A sleek minimalist wireless headphone on an oak desk, high resolution photo",
        item_name="Wireless Headphones",
        tool_context=mock_context,
    )

    assert res.get("status") == "success"
    assert "public_url" in res
    public_url = res["public_url"]
    assert public_url.startswith(f"https://storage.googleapis.com/{BUCKET_NAME}/")

    # Verify tool_context.save_artifact was called
    mock_context.save_artifact.assert_called_once()

    # Verify HTTP 200 retrieval of public URL
    req = urllib.request.Request(public_url, method="HEAD")
    with urllib.request.urlopen(req, timeout=10) as response:
        assert response.status == 200
