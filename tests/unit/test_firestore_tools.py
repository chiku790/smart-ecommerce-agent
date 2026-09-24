from app.agent import add_product, get_product_details, search_products, update_product_stock


def test_firestore_product_workflow():
    test_id = "prod-test-999"

    # Add product
    result = add_product(
        product_id=test_id,
        name="Test Wireless Earbuds",
        category="Electronics",
        price=49.99,
        stock=10,
        description="High quality test earbuds",
    )
    assert result["status"] == "success"

    # Get product details
    details = get_product_details(test_id)
    assert details["name"] == "Test Wireless Earbuds"
    assert details["price"] == 49.99

    # Search products
    search_res = search_products(query="Earbuds", category="Electronics")
    assert any(p["id"] == test_id for p in search_res)

    # Update stock
    stock_res = update_product_stock(test_id, -2)
    assert stock_res["new_stock"] == 8

    # Clean up test doc
    from app.agent import get_firestore_db
    get_firestore_db().collection("products").document(test_id).delete()
