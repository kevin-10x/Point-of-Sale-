from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import db
from app.forms import LoginForm, RegisterShopForm
from app.models import Branch, Shop, User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/")
def index():
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.is_active and user.check_password(form.password.data):
            if user.shop_id and user.shop and not user.shop.is_active:
                flash("This shop account has been suspended. Contact support.", "danger")
                return render_template("auth/login.html", form=form)
            login_user(user)
            if user.is_super_admin:
                return redirect(url_for("admin.shops"))
            return redirect(url_for("dashboard.home"))
        flash("Invalid username or password.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterShopForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(username=form.username.data).first()
        if existing:
            flash("Username already taken.", "danger")
            return render_template("auth/register.html", form=form)

        shop = Shop(
            name=form.shop_name.data,
            phone=form.shop_phone.data,
            email=form.shop_email.data,
            address=form.shop_address.data,
            subscription_plan="starter",
            subscription_status="trial",
        )
        db.session.add(shop)
        db.session.flush()

        branch = Branch(shop_id=shop.id, name="Main Branch", address=form.shop_address.data)
        db.session.add(branch)

        owner = User(
            shop_id=shop.id,
            username=form.username.data,
            email=form.email.data,
            role="owner",
        )
        owner.set_password(form.password.data)
        db.session.add(owner)
        db.session.commit()

        flash("Shop registered successfully. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
