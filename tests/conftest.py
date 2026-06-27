import re

import pytest
from sqlalchemy.pool import StaticPool

from app import create_app
from app.extensions import db

CSRF_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')


@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            },
            "WTF_CSRF_ENABLED": True,
            "MPESA_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _csrf(client, path="/login"):
    r = client.get(path)
    m = CSRF_RE.search(r.data.decode())
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
    from app.models import Branch, Category, Product, Shop, User

    shop = Shop(name="Test Shop", subscription_status="active")
    db.session.add(shop)
    db.session.flush()

    branch = Branch(shop_id=shop.id, name="Main")
    db.session.add(branch)

    owner = User(shop_id=shop.id, username="owner", role="owner")
    owner.set_password("pass123")
    cashier = User(shop_id=shop.id, username="cashier", role="cashier")
    cashier.set_password("pass123")
    db.session.add_all([owner, cashier])

    cat = Category(shop_id=shop.id, name="Groceries")
    db.session.add(cat)
    db.session.flush()

    product = Product(
        shop_id=shop.id,
        category_id=cat.id,
        name="Milk",
        barcode="9001",
        buying_price=45,
        selling_price=60,
        stock_quantity=50,
    )
    db.session.add(product)
    db.session.commit()
    return {"shop": shop, "product": product, "owner": owner}
