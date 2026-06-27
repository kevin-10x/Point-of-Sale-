from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.forms import BranchForm, CategoryForm, CustomerForm, ProductForm, UserForm
from app.models import Branch, Category, Customer, Product, User
from app.utils import get_shop_id, require_role, shop_query

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


def _populate_category_choices(form):
    categories = shop_query(Category).order_by(Category.name).all()
    form.category_id.choices = [(0, "— No category —")] + [(c.id, c.name) for c in categories]


@inventory_bp.route("/")
@login_required
def index():
    if current_user.is_super_admin:
        from flask import abort

        abort(403)

    products = shop_query(Product).order_by(Product.name).all()
    categories = shop_query(Category).order_by(Category.name).all()
    low_stock_count = sum(1 for p in products if p.is_active and p.is_low_stock)

    return render_template(
        "inventory/index.html",
        products=products,
        categories=categories,
        low_stock_count=low_stock_count,
    )


@inventory_bp.route("/products/add", methods=["GET", "POST"])
@login_required
@require_role("owner", "manager")
def add_product():
    form = ProductForm()
    _populate_category_choices(form)

    if form.validate_on_submit():
        shop_id = get_shop_id()
        barcode = form.barcode.data or None

        if barcode:
            existing = Product.query.filter_by(shop_id=shop_id, barcode=barcode).first()
            if existing:
                flash("A product with this barcode already exists.", "danger")
                return render_template("inventory/product_form.html", form=form, title="Add Product")

        category_id = form.category_id.data if form.category_id.data else None

        product = Product(
            shop_id=shop_id,
            name=form.name.data,
            barcode=barcode,
            category_id=category_id,
            buying_price=form.buying_price.data,
            selling_price=form.selling_price.data,
            stock_quantity=form.stock_quantity.data,
            low_stock_threshold=form.low_stock_threshold.data,
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully.", "success")
        return redirect(url_for("inventory.index"))

    return render_template("inventory/product_form.html", form=form, title="Add Product")


@inventory_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@require_role("owner", "manager")
def edit_product(product_id):
    shop_id = get_shop_id()
    product = shop_query(Product).filter_by(id=product_id).first_or_404()
    form = ProductForm(obj=product)
    _populate_category_choices(form)
    if product.category_id:
        form.category_id.data = product.category_id

    if form.validate_on_submit():
        barcode = form.barcode.data or None
        if barcode:
            existing = Product.query.filter_by(shop_id=shop_id, barcode=barcode).first()
            if existing and existing.id != product.id:
                flash("A product with this barcode already exists.", "danger")
                return render_template(
                    "inventory/product_form.html",
                    form=form,
                    title="Edit Product",
                    product=product,
                )

        product.name = form.name.data
        product.barcode = barcode
        product.category_id = form.category_id.data if form.category_id.data else None
        product.buying_price = form.buying_price.data
        product.selling_price = form.selling_price.data
        product.stock_quantity = form.stock_quantity.data
        product.low_stock_threshold = form.low_stock_threshold.data
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("inventory.index"))

    return render_template(
        "inventory/product_form.html",
        form=form,
        title="Edit Product",
        product=product,
    )


@inventory_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
@require_role("owner", "manager")
def delete_product(product_id):
    product = shop_query(Product).filter_by(id=product_id).first_or_404()
    product.is_active = False
    db.session.commit()
    flash("Product deactivated.", "info")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/categories/add", methods=["POST"])
@login_required
@require_role("owner", "manager")
def add_category():
    form = CategoryForm()
    if form.validate_on_submit():
        category = Category(shop_id=get_shop_id(), name=form.name.data)
        db.session.add(category)
        db.session.commit()
        flash("Category added.", "success")
    else:
        flash("Invalid category name.", "danger")
    return redirect(url_for("inventory.index"))


@inventory_bp.route("/customers")
@login_required
def customers():
    customers_list = shop_query(Customer).order_by(Customer.name).all()
    form = CustomerForm()
    return render_template("inventory/customers.html", customers=customers_list, form=form)


@inventory_bp.route("/customers/add", methods=["POST"])
@login_required
def add_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            shop_id=get_shop_id(),
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
        )
        db.session.add(customer)
        db.session.commit()
        flash("Customer added.", "success")
    else:
        flash("Could not add customer.", "danger")
    return redirect(url_for("inventory.customers"))


@inventory_bp.route("/branches")
@login_required
@require_role("owner", "manager")
def branches():
    branches_list = shop_query(Branch).order_by(Branch.name).all()
    form = BranchForm()
    return render_template("inventory/branches.html", branches=branches_list, form=form)


@inventory_bp.route("/branches/add", methods=["POST"])
@login_required
@require_role("owner")
def add_branch():
    form = BranchForm()
    if form.validate_on_submit():
        branch = Branch(
            shop_id=get_shop_id(),
            name=form.name.data,
            address=form.address.data,
        )
        db.session.add(branch)
        db.session.commit()
        flash("Branch added.", "success")
    else:
        flash("Could not add branch.", "danger")
    return redirect(url_for("inventory.branches"))


@inventory_bp.route("/users")
@login_required
@require_role("owner")
def users():
    shop_id = get_shop_id()
    users_list = User.query.filter_by(shop_id=shop_id).order_by(User.username).all()
    form = UserForm()
    return render_template("inventory/users.html", users=users_list, form=form)


@inventory_bp.route("/users/add", methods=["POST"])
@login_required
@require_role("owner")
def add_user():
    form = UserForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(username=form.username.data).first()
        if existing:
            flash("Username already taken.", "danger")
            return redirect(url_for("inventory.users"))

        user = User(
            shop_id=get_shop_id(),
            username=form.username.data,
            email=form.email.data,
            role=form.role.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("User created.", "success")
    else:
        flash("Could not create user.", "danger")
    return redirect(url_for("inventory.users"))
