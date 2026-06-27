from sqlalchemy import func

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Sale, Shop, User

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/shops")
@login_required
def shops():
    from flask_login import current_user

    if not current_user.is_super_admin:
        from flask import abort

        abort(403)

    shops_list = Shop.query.order_by(Shop.created_at.desc()).all()
    total_shops = len(shops_list)
    active_shops = sum(1 for s in shops_list if s.is_active)
    total_users = User.query.filter(User.shop_id.isnot(None)).count()
    total_sales = Sale.query.count()
    platform_revenue = db.session.query(func.sum(Sale.total_amount)).scalar() or 0

    return render_template(
        "admin/shops.html",
        shops=shops_list,
        total_shops=total_shops,
        active_shops=active_shops,
        total_users=total_users,
        total_sales=total_sales,
        platform_revenue=platform_revenue,
    )


@admin_bp.route("/shops/<int:shop_id>/toggle", methods=["POST"])
@login_required
def toggle_shop(shop_id):
    from flask_login import current_user

    if not current_user.is_super_admin:
        from flask import abort

        abort(403)

    shop = Shop.query.get_or_404(shop_id)
    shop.is_active = not shop.is_active
    status = "activated" if shop.is_active else "suspended"
    db.session.commit()
    flash(f"Shop {shop.name} {status}.", "success")
    return redirect(url_for("admin.shops"))


@admin_bp.route("/shops/<int:shop_id>/subscription", methods=["POST"])
@login_required
def update_subscription(shop_id):
    from flask_login import current_user

    if not current_user.is_super_admin:
        from flask import abort

        abort(403)

    from flask import request

    shop = Shop.query.get_or_404(shop_id)
    shop.subscription_plan = request.form.get("subscription_plan", shop.subscription_plan)
    shop.subscription_status = request.form.get("subscription_status", shop.subscription_status)
    db.session.commit()
    flash(f"Subscription updated for {shop.name}.", "success")
    return redirect(url_for("admin.shops"))
