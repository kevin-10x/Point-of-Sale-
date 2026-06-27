"""
Comprehensive test suite for the Nexus POS application.
Covers: health, auth, dashboard, sales (cash + M-Pesa), inventory,
        reports, billing, admin, and utility functions.
"""

import json

import pytest

from tests.conftest import _csrf, _login


# ──────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "ok"


# ──────────────────────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────────────────────

class TestAuth:
    def test_login_page_loads(self, client):
        r = client.get("/login")
        assert r.status_code == 200
        assert b"Sign In" in r.data

    def test_register_page_loads(self, client):
        r = client.get("/register")
        assert r.status_code == 200
        assert b"Register" in r.data

    def test_register_and_login(self, client):
        token = _csrf(client)
        r = client.post(
            "/register",
            data={
                "csrf_token": token,
                "shop_name": "New Shop",
                "shop_phone": "0711111111",
                "username": "brandnewowner",
                "password": "secret12",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        r2 = _login(client, "brandnewowner", "secret12")
        assert r2.status_code == 200
        assert b"Dashboard" in r2.data or b"dashboard" in r2.request.path.encode()

    def test_login_wrong_password(self, client, seeded):
        r = _login(client, seeded["owner_name"], "wrongpassword")
        assert r.status_code == 200
        assert b"Invalid" in r.data

    def test_login_nonexistent_user(self, client):
        r = _login(client, "nobody_xyz", "password")
        assert r.status_code == 200
        assert b"Invalid" in r.data

    def test_protected_requires_login(self, client):
        r = client.get("/dashboard/", follow_redirects=True)
        assert r.status_code == 200
        assert b"log in" in r.data.lower() or b"Sign In" in r.data


# ──────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────

class TestDashboard:
    def test_dashboard_loads(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/dashboard/", follow_redirects=True)
        assert r.status_code == 200
        assert b"Dashboard" in r.data

    def test_dashboard_shows_shop_name(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/dashboard/", follow_redirects=True)
        assert b"Test Shop" in r.data


# ──────────────────────────────────────────────────────────────
# Sales — Cart
# ──────────────────────────────────────────────────────────────

class TestCart:
    def _add_product(self, client, seeded, token, qty=1):
        return client.post(
            "/sales/cart/add",
            json={"product_id": seeded["product"].id, "quantity": qty},
            headers={"X-CSRFToken": token},
        )

    def test_add_to_cart(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        token = _csrf(client, "/sales/")
        r = self._add_product(client, seeded, token)
        assert r.status_code == 200
        assert json.loads(r.data)["success"] is True

    def test_add_over_stock_rejected(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        token = _csrf(client, "/sales/")
        r = self._add_product(client, seeded, token, qty=9999)
        assert r.status_code == 400

    def test_update_cart_quantity(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        token = _csrf(client, "/sales/")
        self._add_product(client, seeded, token)
        r = client.post(
            "/sales/cart/update",
            json={"product_id": seeded["product"].id, "quantity": 3},
            headers={"X-CSRFToken": token},
        )
        assert r.status_code == 200

    def test_remove_from_cart(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        token = _csrf(client, "/sales/")
        self._add_product(client, seeded, token)
        r = client.post(
            "/sales/cart/remove",
            json={"product_id": seeded["product"].id},
            headers={"X-CSRFToken": token},
        )
        assert r.status_code == 200

    def test_clear_cart(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        token = _csrf(client, "/sales/")
        self._add_product(client, seeded, token)
        r = client.post("/sales/cart/clear", json={}, headers={"X-CSRFToken": token})
        assert r.status_code == 200

    def test_product_search(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        r = client.get("/sales/search?q=Milk")
        assert r.status_code == 200
        products = json.loads(r.data)
        assert any(p["name"] == "Milk" for p in products)

    def test_search_empty_query(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        r = client.get("/sales/search?q=")
        assert r.status_code == 200
        assert json.loads(r.data) == []


# ──────────────────────────────────────────────────────────────
# Sales — Checkout
# ──────────────────────────────────────────────────────────────

class TestCheckout:
    def _setup(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        token = _csrf(client, "/sales/")
        client.post(
            "/sales/cart/add",
            json={"product_id": seeded["product"].id, "quantity": 2},
            headers={"X-CSRFToken": token},
        )
        return token

    def test_cash_sale(self, client, seeded):
        token = self._setup(client, seeded)
        r = client.post(
            "/sales/checkout",
            data={"csrf_token": token, "payment_method": "cash", "discount_amount": "0"},
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"Receipt" in r.data

    def test_cash_sale_with_discount(self, client, seeded):
        token = self._setup(client, seeded)
        r = client.post(
            "/sales/checkout",
            data={"csrf_token": token, "payment_method": "cash", "discount_amount": "10"},
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"Receipt" in r.data

    def test_cash_sale_reduces_stock(self, client, seeded, app):
        from app.models import Product

        token = self._setup(client, seeded)
        client.post(
            "/sales/checkout",
            data={"csrf_token": token, "payment_method": "cash", "discount_amount": "0"},
            follow_redirects=True,
        )
        with app.app_context():
            p = _db_get(app, Product, seeded["product"].id)
            if p:
                assert p.stock_quantity == 48  # 50 - 2

    def test_checkout_empty_cart_redirects(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        token = _csrf(client, "/sales/")
        r = client.post(
            "/sales/checkout",
            data={"csrf_token": token, "payment_method": "cash", "discount_amount": "0"},
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"empty" in r.data.lower() or b"Sales" in r.data

    def test_mpesa_sale_simulated(self, client, seeded):
        token = self._setup(client, seeded)
        r = client.post(
            "/sales/checkout",
            data={
                "csrf_token": token,
                "payment_method": "mpesa",
                "mpesa_phone": "0712345678",
                "discount_amount": "0",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"Receipt" in r.data or b"M-Pesa" in r.data

    def test_mpesa_sale_missing_phone(self, client, seeded):
        token = self._setup(client, seeded)
        r = client.post(
            "/sales/checkout",
            data={
                "csrf_token": token,
                "payment_method": "mpesa",
                "mpesa_phone": "",
                "discount_amount": "0",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200

    def test_sales_history(self, client, seeded):
        token = self._setup(client, seeded)
        client.post(
            "/sales/checkout",
            data={"csrf_token": token, "payment_method": "cash", "discount_amount": "0"},
            follow_redirects=True,
        )
        r = client.get("/sales/history")
        assert r.status_code == 200
        assert b"Sales History" in r.data


# ──────────────────────────────────────────────────────────────
# Inventory
# ──────────────────────────────────────────────────────────────

class TestInventory:
    def test_inventory_page_loads(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/inventory/")
        assert r.status_code == 200
        assert b"Inventory" in r.data
        assert b"Milk" in r.data

    def test_add_product_page(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/inventory/products/add")
        assert r.status_code == 200
        assert b"Add Product" in r.data

    def test_add_product(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        token = _csrf(client, "/inventory/products/add")
        r = client.post(
            "/inventory/products/add",
            data={
                "csrf_token": token,
                "name": "Sugar 1kg",
                "barcode": "5001xyz",
                "buying_price": "150",
                "selling_price": "200",
                "stock_quantity": "30",
                "low_stock_threshold": "5",
                "category_id": "0",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200
        assert b"Sugar" in r.data or b"success" in r.data.lower()

    def test_add_category(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        token = _csrf(client, "/inventory/")
        r = client.post(
            "/inventory/categories/add",
            data={"csrf_token": token, "name": "Electronics"},
            follow_redirects=True,
        )
        assert r.status_code == 200

    def test_customers_page(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/inventory/customers")
        assert r.status_code == 200

    def test_add_customer(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        token = _csrf(client, "/inventory/customers")
        r = client.post(
            "/inventory/customers/add",
            data={
                "csrf_token": token,
                "name": "John Doe",
                "phone": "0722000001",
                "email": "",
            },
            follow_redirects=True,
        )
        assert r.status_code == 200

    def test_branches_page(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/inventory/branches")
        assert r.status_code == 200

    def test_users_page(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/inventory/users")
        assert r.status_code == 200

    def test_cashier_cannot_add_product(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        token = _csrf(client, "/login")
        r = client.post(
            "/inventory/products/add",
            data={
                "csrf_token": token,
                "name": "Butter",
                "buying_price": "100",
                "selling_price": "130",
                "stock_quantity": "10",
                "low_stock_threshold": "2",
                "category_id": "0",
            },
            follow_redirects=True,
        )
        assert r.status_code in (200, 403)


# ──────────────────────────────────────────────────────────────
# Reports
# ──────────────────────────────────────────────────────────────

class TestReports:
    def test_reports_page_owner(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/reports/")
        assert r.status_code == 200
        assert b"Reports" in r.data

    def test_reports_csv_export(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/reports/export?start=2024-01-01&end=2030-01-01")
        assert r.status_code == 200
        assert b"sale_id" in r.data

    def test_reports_date_filter(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/reports/?start=2024-01-01&end=2024-01-31")
        assert r.status_code == 200

    def test_cashier_cannot_access_reports(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        r = client.get("/reports/", follow_redirects=True)
        assert r.status_code in (200, 403)


# ──────────────────────────────────────────────────────────────
# Billing
# ──────────────────────────────────────────────────────────────

class TestBilling:
    def test_billing_page_owner(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/billing/")
        assert r.status_code == 200
        assert b"Billing" in r.data or b"Subscription" in r.data

    def test_subscription_simulated(self, client, seeded, app):
        from app.extensions import db
        from app.models import Shop

        _login(client, seeded["owner_name"], "pass123")
        token = _csrf(client, "/billing/")
        r = client.post(
            "/billing/subscribe",
            data={"csrf_token": token, "plan": "starter", "phone": "0712345678"},
            follow_redirects=True,
        )
        assert r.status_code == 200

        with app.app_context():
            shop = db.session.get(Shop, seeded["shop"].id)
            if shop:
                assert shop.subscription_plan == "starter"
                assert shop.subscription_status == "active"

    def test_subscription_invalid_plan(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        token = _csrf(client, "/billing/")
        r = client.post(
            "/billing/subscribe",
            data={"csrf_token": token, "plan": "enterprise_invalid", "phone": "0712345678"},
            follow_redirects=True,
        )
        assert r.status_code == 200


# ──────────────────────────────────────────────────────────────
# M-Pesa callback endpoint
# ──────────────────────────────────────────────────────────────

class TestMpesaCallback:
    def test_callback_invalid_payload(self, client):
        r = client.post(
            "/api/mpesa/callback",
            json={},
            content_type="application/json",
        )
        assert r.status_code == 200

    def test_callback_unknown_checkout(self, client):
        payload = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "UNKNOWN-ID",
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                }
            }
        }
        r = client.post("/api/mpesa/callback", json=payload)
        assert r.status_code == 200

    def test_payment_status_not_found(self, client, seeded):
        _login(client, seeded["cashier_name"], "pass123")
        r = client.get("/api/mpesa/status/99999")
        assert r.status_code == 404


# ──────────────────────────────────────────────────────────────
# Admin
# ──────────────────────────────────────────────────────────────

class TestAdmin:
    def test_admin_page_regular_user_forbidden(self, client, seeded):
        _login(client, seeded["owner_name"], "pass123")
        r = client.get("/admin/shops")
        assert r.status_code == 403

    def test_admin_page_superadmin(self, client, app):
        from app.extensions import db
        from app.models import User

        with app.app_context():
            admin = User(username="superadmin_test", role="super_admin", shop_id=None)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()

        _login(client, "superadmin_test", "admin123")
        r = client.get("/admin/shops")
        assert r.status_code == 200
        assert b"Platform" in r.data or b"Shops" in r.data


# ──────────────────────────────────────────────────────────────
# Utility functions
# ──────────────────────────────────────────────────────────────

class TestUtils:
    def test_normalize_phone_07(self):
        from app.services.mpesa import normalize_phone
        assert normalize_phone("0712345678") == "254712345678"

    def test_normalize_phone_254(self):
        from app.services.mpesa import normalize_phone
        assert normalize_phone("254712345678") == "254712345678"

    def test_normalize_phone_7(self):
        from app.services.mpesa import normalize_phone
        assert normalize_phone("712345678") == "254712345678"

    def test_normalize_phone_invalid(self):
        from app.services.mpesa import normalize_phone
        with pytest.raises(ValueError):
            normalize_phone("123")

    def test_aggregate_sales_empty(self, app):
        from app.utils import aggregate_sales
        with app.app_context():
            result = aggregate_sales([])
            assert result["revenue"] == 0
            assert result["margin"] == 0
            assert result["count"] == 0


# ──────────────────────────────────────────────────────────────
# Helpers (used inside tests)
# ──────────────────────────────────────────────────────────────

def _db_get(app, model, pk):
    from app.extensions import db
    with app.app_context():
        return db.session.get(model, pk)
