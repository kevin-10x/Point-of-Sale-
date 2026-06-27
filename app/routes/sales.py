import json

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Branch, Customer, MpesaPayment, Product, Sale
from app.services.mpesa import MpesaError
from app.services.payment_handlers import initiate_sale_payment
from app.utils import calculate_sale_totals, create_sale_from_cart, get_shop_id, shop_query

sales_bp = Blueprint("sales", __name__, url_prefix="/sales")


def _get_cart():
    return session.get("cart", [])


def _set_cart(cart):
    session["cart"] = cart
    session.modified = True


@sales_bp.route("/")
@login_required
def index():
    if current_user.is_super_admin:
        from flask import abort

        abort(403)

    shop_id = get_shop_id()
    products = (
        shop_query(Product)
        .filter_by(is_active=True)
        .filter(Product.stock_quantity > 0)
        .order_by(Product.name)
        .all()
    )
    customers = shop_query(Customer).order_by(Customer.name).all()
    branches = shop_query(Branch).filter_by(is_active=True).order_by(Branch.name).all()
    cart = _get_cart()

    cart_details = []
    cart_total = 0.0
    for item in cart:
        product = db.session.get(Product, item["product_id"])
        if product and product.shop_id == shop_id:
            subtotal = product.selling_price * item["quantity"]
            cart_total += subtotal
            cart_details.append(
                {
                    "product_id": product.id,
                    "name": product.name,
                    "price": product.selling_price,
                    "quantity": item["quantity"],
                    "subtotal": subtotal,
                    "stock": product.stock_quantity,
                }
            )

    from flask import current_app

    return render_template(
        "sales/index.html",
        products=products,
        customers=customers,
        branches=branches,
        cart=cart_details,
        cart_total=cart_total,
        mpesa_enabled=current_app.config.get("MPESA_ENABLED"),
    )


@sales_bp.route("/search")
@login_required
def search_products():
    q = request.args.get("q", "").strip()
    shop_id = get_shop_id()

    if not q:
        return jsonify([])

    products = (
        Product.query.filter(
            Product.shop_id == shop_id,
            Product.is_active == True,
            Product.stock_quantity > 0,
            db.or_(
                Product.name.ilike(f"%{q}%"),
                Product.barcode.ilike(f"%{q}%"),
            ),
        )
        .limit(20)
        .all()
    )

    return jsonify(
        [
            {
                "id": p.id,
                "name": p.name,
                "barcode": p.barcode,
                "price": p.selling_price,
                "stock": p.stock_quantity,
            }
            for p in products
        ]
    )


@sales_bp.route("/cart/add", methods=["POST"])
@login_required
def add_to_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))

    product = shop_query(Product).filter_by(id=product_id, is_active=True).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    if quantity <= 0:
        return jsonify({"error": "Invalid quantity"}), 400

    cart = _get_cart()
    found = False
    for item in cart:
        if item["product_id"] == product_id:
            new_qty = item["quantity"] + quantity
            if new_qty > product.stock_quantity:
                return jsonify({"error": f"Only {product.stock_quantity} in stock"}), 400
            item["quantity"] = new_qty
            found = True
            break

    if not found:
        if quantity > product.stock_quantity:
            return jsonify({"error": f"Only {product.stock_quantity} in stock"}), 400
        cart.append({"product_id": product_id, "quantity": quantity})

    _set_cart(cart)
    return jsonify({"success": True, "cart_count": sum(i["quantity"] for i in cart)})


@sales_bp.route("/cart/update", methods=["POST"])
@login_required
def update_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 0))

    product = shop_query(Product).filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    cart = _get_cart()
    if quantity <= 0:
        cart = [i for i in cart if i["product_id"] != product_id]
    else:
        if quantity > product.stock_quantity:
            return jsonify({"error": f"Only {product.stock_quantity} in stock"}), 400
        for item in cart:
            if item["product_id"] == product_id:
                item["quantity"] = quantity
                break

    _set_cart(cart)
    return jsonify({"success": True})


@sales_bp.route("/cart/remove", methods=["POST"])
@login_required
def remove_from_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    cart = [i for i in _get_cart() if i["product_id"] != product_id]
    _set_cart(cart)
    return jsonify({"success": True})


@sales_bp.route("/cart/clear", methods=["POST"])
@login_required
def clear_cart():
    _set_cart([])
    return jsonify({"success": True})


@sales_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    cart = _get_cart()
    if not cart:
        flash("Cart is empty.", "warning")
        return redirect(url_for("sales.index"))

    payment_method = request.form.get("payment_method", "cash")
    discount_amount = float(request.form.get("discount_amount", 0) or 0)
    customer_id = request.form.get("customer_id")
    branch_id = request.form.get("branch_id")
    notes = request.form.get("notes")
    mpesa_phone = request.form.get("mpesa_phone", "").strip()

    customer_id = int(customer_id) if customer_id else None
    branch_id = int(branch_id) if branch_id else None

    if payment_method == "mpesa":
        total_amount, _, _, _ = calculate_sale_totals(cart)
        pay_amount = max(0, total_amount - discount_amount)
        if pay_amount < 1:
            flash("M-Pesa amount must be at least KES 1.", "warning")
            return redirect(url_for("sales.index"))
        if not mpesa_phone:
            flash("Enter customer M-Pesa phone number.", "danger")
            return redirect(url_for("sales.index"))

        try:
            payment = initiate_sale_payment(
                shop_id=get_shop_id(),
                cashier_id=current_user.id,
                phone=mpesa_phone,
                amount=pay_amount,
                cart_items=cart,
                discount_amount=discount_amount,
                customer_id=customer_id,
                branch_id=branch_id,
                notes=notes,
            )
            if payment.status == "completed":
                _set_cart([])
                flash("M-Pesa payment received. Sale completed.", "success")
                return redirect(url_for("sales.receipt", sale_id=payment.sale_id))
            return redirect(url_for("sales.mpesa_pending", payment_id=payment.id))
        except (ValueError, MpesaError) as e:
            flash(str(e), "danger")
            return redirect(url_for("sales.index"))

    try:
        sale = create_sale_from_cart(
            cart_items=cart,
            cashier_id=current_user.id,
            shop_id=get_shop_id(),
            payment_method=payment_method,
            discount_amount=discount_amount,
            customer_id=customer_id,
            branch_id=branch_id,
            notes=notes,
        )
        _set_cart([])
        flash("Sale completed successfully.", "success")
        return redirect(url_for("sales.receipt", sale_id=sale.id))
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("sales.index"))
    except Exception:
        db.session.rollback()
        flash("Checkout failed. Please try again.", "danger")
        return redirect(url_for("sales.index"))


@sales_bp.route("/mpesa/<int:payment_id>")
@login_required
def mpesa_pending(payment_id):
    payment = shop_query(MpesaPayment).filter_by(id=payment_id, payment_type="sale").first_or_404()
    return render_template("sales/mpesa_pending.html", payment=payment)


@sales_bp.route("/receipt/<int:sale_id>")
@login_required
def receipt(sale_id):
    sale = shop_query(Sale).filter_by(id=sale_id).first_or_404()
    return render_template("sales/receipt.html", sale=sale, shop=current_user.shop)


@sales_bp.route("/history")
@login_required
def history():
    sales_list = (
        shop_query(Sale)
        .order_by(Sale.created_at.desc())
        .limit(100)
        .all()
    )
    return render_template("sales/history.html", sales=sales_list)
