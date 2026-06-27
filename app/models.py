from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Shop(db.Model):
    __tablename__ = "shops"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.String(255))
    subscription_plan = db.Column(db.String(20), default="starter")
    subscription_status = db.Column(db.String(20), default="trial")
    subscription_expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    branches = db.relationship("Branch", back_populates="shop", lazy="dynamic")
    users = db.relationship("User", back_populates="shop", lazy="dynamic")
    products = db.relationship("Product", back_populates="shop", lazy="dynamic")
    sales = db.relationship("Sale", back_populates="shop", lazy="dynamic")
    customers = db.relationship("Customer", back_populates="shop", lazy="dynamic")

    def __repr__(self):
        return f"<Shop {self.name}>"


class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    shop = db.relationship("Shop", back_populates="branches")
    sales = db.relationship("Sale", back_populates="branch", lazy="dynamic")

    def __repr__(self):
        return f"<Branch {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    ROLES = ("super_admin", "owner", "manager", "cashier")

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="cashier")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    shop = db.relationship("Shop", back_populates="users")
    sales = db.relationship("Sale", back_populates="cashier", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_super_admin(self):
        return self.role == "super_admin"

    @property
    def is_owner(self):
        return self.role == "owner"

    @property
    def is_manager(self):
        return self.role in ("owner", "manager")

    @property
    def can_manage_inventory(self):
        return self.role in ("super_admin", "owner", "manager")

    @property
    def can_view_reports(self):
        return self.role in ("super_admin", "owner", "manager")

    def __repr__(self):
        return f"<User {self.username}>"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    shop = db.relationship("Shop")
    products = db.relationship("Product", back_populates="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.name}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    name = db.Column(db.String(200), nullable=False)
    barcode = db.Column(db.String(100))
    buying_price = db.Column(db.Float, nullable=False, default=0)
    selling_price = db.Column(db.Float, nullable=False, default=0)
    stock_quantity = db.Column(db.Integer, default=0)
    low_stock_threshold = db.Column(db.Integer, default=5)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    shop = db.relationship("Shop", back_populates="products")
    category = db.relationship("Category", back_populates="products")

    __table_args__ = (
        db.UniqueConstraint("shop_id", "barcode", name="uq_shop_barcode"),
    )

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold

    @property
    def profit_margin(self):
        if self.selling_price <= 0:
            return 0
        return ((self.selling_price - self.buying_price) / self.selling_price) * 100

    def __repr__(self):
        return f"<Product {self.name}>"


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    loyalty_points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)

    shop = db.relationship("Shop", back_populates="customers")
    sales = db.relationship("Sale", back_populates="customer", lazy="dynamic")

    def __repr__(self):
        return f"<Customer {self.name}>"


class Sale(db.Model):
    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True)
    cashier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    total_cost = db.Column(db.Float, nullable=False, default=0)
    total_profit = db.Column(db.Float, nullable=False, default=0)
    discount_amount = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(50), default="cash")
    mpesa_receipt_number = db.Column(db.String(50), nullable=True)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)

    shop = db.relationship("Shop", back_populates="sales")
    branch = db.relationship("Branch", back_populates="sales")
    customer = db.relationship("Customer", back_populates="sales")
    cashier = db.relationship("User", back_populates="sales")
    items = db.relationship(
        "SaleItem",
        back_populates="sale",
        lazy="joined",
        cascade="all, delete-orphan",
    )

    @property
    def profit_margin(self):
        if self.total_amount <= 0:
            return 0
        return (self.total_profit / self.total_amount) * 100

    def __repr__(self):
        return f"<Sale {self.id}>"


class SaleItem(db.Model):
    __tablename__ = "sale_items"

    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    buying_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)
    cost_subtotal = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)

    sale = db.relationship("Sale", back_populates="items")
    product = db.relationship("Product")

    def __repr__(self):
        return f"<SaleItem sale={self.sale_id} product={self.product_id}>"


class MpesaPayment(db.Model):
    """Tracks M-Pesa STK push requests for sales and subscriptions."""

    __tablename__ = "mpesa_payments"

    PAYMENT_TYPES = ("sale", "subscription")
    STATUSES = ("pending", "completed", "failed", "cancelled")

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.Integer, db.ForeignKey("shops.id"), nullable=False)
    payment_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="pending")
    merchant_request_id = db.Column(db.String(100))
    checkout_request_id = db.Column(db.String(100), unique=True, index=True)
    mpesa_receipt_number = db.Column(db.String(50))
    result_code = db.Column(db.Integer)
    result_desc = db.Column(db.String(255))
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=True)
    subscription_plan = db.Column(db.String(20), nullable=True)
    cart_json = db.Column(db.Text)
    cashier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    discount_amount = db.Column(db.Float, default=0)
    customer_id = db.Column(db.Integer, nullable=True)
    branch_id = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    shop = db.relationship("Shop")
    sale = db.relationship("Sale")
    cashier = db.relationship("User")

    def __repr__(self):
        return f"<MpesaPayment {self.id} {self.payment_type} {self.status}>"
