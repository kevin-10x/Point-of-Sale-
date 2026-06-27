"""Shared helpers for shop-scoped queries and profit calculations."""

from datetime import datetime, timezone
from functools import wraps

from flask import abort
from flask_login import current_user

from app.extensions import db
from app.models import Product, Sale, SaleItem


def shop_query(model):
    """Return a base query filtered to the current user's shop."""
    if current_user.is_super_admin:
        return model.query
    if not current_user.shop_id:
        abort(403)
    return model.query.filter_by(shop_id=current_user.shop_id)


def get_shop_id():
    if current_user.is_super_admin:
        return None
    if not current_user.shop_id:
        abort(403)
    return current_user.shop_id


def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if current_user.is_super_admin:
                return fn(*args, **kwargs)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def calculate_sale_totals(cart_items):
    """Build sale line items from cart dicts with product_id and quantity."""
    total_amount = 0.0
    total_cost = 0.0
    line_items = []

    for item in cart_items:
        product = db.session.get(Product, item["product_id"])
        if not product:
            continue
        qty = int(item["quantity"])
        if qty <= 0:
            continue

        selling = product.selling_price
        buying = product.buying_price
        subtotal = selling * qty
        cost_subtotal = buying * qty
        profit = subtotal - cost_subtotal

        total_amount += subtotal
        total_cost += cost_subtotal

        line_items.append(
            {
                "product": product,
                "quantity": qty,
                "buying_price": buying,
                "selling_price": selling,
                "subtotal": subtotal,
                "cost_subtotal": cost_subtotal,
                "profit": profit,
            }
        )

    total_profit = total_amount - total_cost
    return total_amount, total_cost, total_profit, line_items


def create_sale_from_cart(
    cart_items,
    cashier_id,
    shop_id,
    payment_method,
    discount_amount=0,
    customer_id=None,
    branch_id=None,
    notes=None,
    mpesa_receipt_number=None,
):
    total_amount, total_cost, total_profit, line_items = calculate_sale_totals(cart_items)

    if discount_amount > total_amount:
        discount_amount = total_amount

    total_amount -= discount_amount
    # Profit reduced proportionally by discount (simple gross profit adjustment)
    if total_amount + discount_amount > 0:
        profit_ratio = total_profit / (total_amount + discount_amount)
        total_profit = total_amount * profit_ratio

    sale = Sale(
        shop_id=shop_id,
        branch_id=branch_id,
        customer_id=customer_id,
        cashier_id=cashier_id,
        total_amount=total_amount,
        total_cost=total_cost,
        total_profit=total_profit,
        discount_amount=discount_amount,
        payment_method=payment_method,
        mpesa_receipt_number=mpesa_receipt_number,
        notes=notes,
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(sale)
    db.session.flush()

    for line in line_items:
        product = line["product"]
        qty = line["quantity"]

        if product.stock_quantity < qty:
            raise ValueError(f"Insufficient stock for {product.name}")

        product.stock_quantity -= qty

        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=qty,
            buying_price=line["buying_price"],
            selling_price=line["selling_price"],
            subtotal=line["subtotal"],
            cost_subtotal=line["cost_subtotal"],
            profit=line["profit"],
        )
        db.session.add(sale_item)

    db.session.commit()
    return sale


def aggregate_sales(sales_query):
    revenue = sum(s.total_amount for s in sales_query)
    cost = sum(s.total_cost for s in sales_query)
    profit = sum(s.total_profit for s in sales_query)
    margin = (profit / revenue * 100) if revenue > 0 else 0
    return {
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "margin": margin,
        "count": len(sales_query),
    }
