from tests.conftest import _csrf, _login


def test_register_and_login(client):
    token = _csrf(client)
    r = client.post(
        "/register",
        data={
            "csrf_token": token,
            "shop_name": "New Shop",
            "shop_phone": "0711111111",
            "username": "newowner",
            "password": "secret12",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200

    r = _login(client, "newowner", "secret12")
    assert r.status_code == 200
    assert "/dashboard" in r.request.path


def test_cash_sale_flow(client, seeded):
    _login(client, "cashier", "pass123")
    token = _csrf(client, "/sales/")

    client.post(
        "/sales/cart/add",
        json={"product_id": seeded["product"].id, "quantity": 2},
        headers={"X-CSRFToken": token},
    )

    r = client.post(
        "/sales/checkout",
        data={
            "csrf_token": token,
            "payment_method": "cash",
            "discount_amount": 0,
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "Receipt" in r.data.decode()


def test_mpesa_sale_simulated(client, seeded):
    _login(client, "cashier", "pass123")
    token = _csrf(client, "/sales/")

    client.post(
        "/sales/cart/add",
        json={"product_id": seeded["product"].id, "quantity": 1},
        headers={"X-CSRFToken": token},
    )

    r = client.post(
        "/sales/checkout",
        data={
            "csrf_token": token,
            "payment_method": "mpesa",
            "mpesa_phone": "0712345678",
            "discount_amount": 0,
        },
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert "Receipt" in r.data.decode() or "M-Pesa" in r.data.decode()


def test_subscription_simulated(client, seeded):
    from app.extensions import db

    _login(client, "owner", "pass123")
    token = _csrf(client, "/billing/")

    r = client.post(
        "/billing/subscribe",
        data={
            "csrf_token": token,
            "plan": "starter",
            "phone": "0712345678",
        },
        follow_redirects=True,
    )
    assert r.status_code == 200

    shop = seeded["shop"]
    db.session.refresh(shop)
    assert shop.subscription_plan == "starter"
    assert shop.subscription_status == "active"


def test_normalize_phone():
    from app.services.mpesa import normalize_phone

    assert normalize_phone("0712345678") == "254712345678"
    assert normalize_phone("254712345678") == "254712345678"
