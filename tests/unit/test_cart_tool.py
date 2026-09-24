from app.agent import manage_shopping_cart


def test_manage_shopping_cart():
    cart_id = "test_cart_123"

    # 1. Clear cart
    clear_res = manage_shopping_cart(action="clear", cart_id=cart_id)
    assert clear_res["status"] == "success"
    assert clear_res["total_items"] == 0

    # 2. Add item
    add_res = manage_shopping_cart(action="add", product_id="prod-101", quantity=2, cart_id=cart_id)
    assert add_res["status"] == "success"
    assert add_res["total_items"] == 2
    assert add_res["subtotal"] == 399.98

    # 3. View cart
    view_res = manage_shopping_cart(action="view", cart_id=cart_id)
    assert len(view_res["items"]) == 1
    assert view_res["items"][0]["product_id"] == "prod-101"

    # 4. Remove item
    rem_res = manage_shopping_cart(action="remove", product_id="prod-101", quantity=1, cart_id=cart_id)
    assert rem_res["total_items"] == 1
    assert rem_res["subtotal"] == 199.99

    # 5. Clean up
    manage_shopping_cart(action="clear", cart_id=cart_id)
