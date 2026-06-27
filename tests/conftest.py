import re
import uuid

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.extensions import db as _db

CSRF_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')


@pytest.fixture(scope="function")
def app():
    """Function-scoped app with fresh in-memory SQLite for each test."""
    application = create_app()
    application.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            },
            "WTF_CSRF_ENABLED": True,
            "MPESA_ENABLED": False,
            "SECRET_KEY": "test-secret-key",
            "SERVER_NAME": None,
        }
    )
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _csrf(client, path="/login"):
    r = client.get(path)
    m = CSRF_RE.search(r.data.decode())
    assert m, f"No CSRF token found at {path}"
    return m.group(1)


def _login(client, username, password):
    token = _csrf(client)
    return client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token},
        follow_redirects=True,
    )


@pytest.fixture
def seeded(app):
    """Create a shop with owner, cashier, branch, and one product."""
    from app.models import Branch, Category, Product, Shop, User

    # Use unique suffix per fixture call to avoid username conflicts
    suffix = uuid.uuid4().hex[:6]

    shop = Shop(name=f"Test Shop {suffix}", subscription_status="active")
    _db.session.add(shop)
    _db.session.flush()

    branch = Branch(shop_id=shop.id, name="Main")
    _db.session.add(branch)

    owner = User(shop_id=shop.id, username=f"owner_{suffix}", role="owner")
    owner.set_password("pass123")
    cashier = User(shop_id=shop.id, username=f"cashier_{suffix}", role="cashier")
    cashier.set_password("pass123")
    _db.session.add_all([owner, cashier])

    cat = Category(shop_id=shop.id, name="Groceries")
    _db.session.add(cat)
    _db.session.flush()

    product = Product(
        shop_id=shop.id,
        category_id=cat.id,
        name="Milk",
        barcode=f"9001{suffix}",
        buying_price=45,
        selling_price=60,
        stock_quantity=50,
    )
    _db.session.add(product)
    _db.session.commit()

    return {
        "shop": shop,
        "product": product,
        "owner": owner,
        "owner_name": owner.username,
        "cashier": cashier,
        "cashier_name": cashier.username,
        "branch": branch,
    }
