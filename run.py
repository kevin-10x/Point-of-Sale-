import os

from dotenv import load_dotenv

from app import create_app
from app.extensions import db

load_dotenv()

app = create_app()


@app.cli.command("upgrade-db")
def upgrade_db():
    """Create missing tables/columns on an existing database."""
    from sqlalchemy import inspect, text

    db.create_all()

    inspector = inspect(db.engine)
    if "shops" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("shops")}
        if "subscription_expires_at" not in cols:
            db.session.execute(text("ALTER TABLE shops ADD COLUMN subscription_expires_at DATETIME"))
    if "sales" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("sales")}
        if "mpesa_receipt_number" not in cols:
            db.session.execute(text("ALTER TABLE sales ADD COLUMN mpesa_receipt_number VARCHAR(50)"))

    db.session.commit()
    print("Database upgraded.")


@app.cli.command("init-db")
def init_db():
    """Create tables and seed super admin."""
    from app.models import User

    db.create_all()

    admin_username = os.environ.get("SUPER_ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("SUPER_ADMIN_PASSWORD", "admin123")

    existing = User.query.filter_by(username=admin_username).first()
    if not existing:
        admin = User(username=admin_username, role="super_admin", shop_id=None)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Super admin created: {admin_username}")
    else:
        print("Super admin already exists.")

    print("Database initialized.")


@app.cli.command("seed-demo")
def seed_demo():
    """Seed a demo shop with sample products."""
    from app.models import Branch, Category, Product, Shop, User

    shop_name = "Kipkoech Supermarket"
    shop = Shop.query.filter_by(name=shop_name).first()
    if shop:
        print("Demo shop already exists.")
        return

    shop = Shop(
        name=shop_name,
        phone="0712345678",
        email="owner@kipkoech.com",
        address="Eldoret, Kenya",
        subscription_plan="standard",
        subscription_status="active",
    )
    db.session.add(shop)
    db.session.flush()

    branch = Branch(shop_id=shop.id, name="Eldoret Branch", address="Eldoret CBD")
    db.session.add(branch)

    owner = User(shop_id=shop.id, username="kipkoech", email="owner@kipkoech.com", role="owner")
    owner.set_password("password123")
    db.session.add(owner)

    cashier = User(shop_id=shop.id, username="cashier1", role="cashier")
    cashier.set_password("password123")
    db.session.add(cashier)

    categories = {}
    for name in ("Beverages", "Bakery", "Groceries"):
        cat = Category(shop_id=shop.id, name=name)
        db.session.add(cat)
        db.session.flush()
        categories[name] = cat

    sample_products = [
        ("Milk", "1001", "Beverages", 45, 60, 100),
        ("Bread", "1002", "Bakery", 50, 70, 80),
        ("Sugar 1kg", "1003", "Groceries", 180, 220, 50),
        ("Cooking Oil 1L", "1004", "Groceries", 280, 350, 40),
        ("Rice 2kg", "1005", "Groceries", 320, 400, 60),
    ]

    for name, barcode, cat_name, buy, sell, stock in sample_products:
        product = Product(
            shop_id=shop.id,
            category_id=categories[cat_name].id,
            name=name,
            barcode=barcode,
            buying_price=buy,
            selling_price=sell,
            stock_quantity=stock,
        )
        db.session.add(product)

    db.session.commit()
    print("Demo shop seeded. Login: kipkoech / password123 or cashier1 / password123")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
