from datetime import datetime, timedelta, timezone

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from app.models import Product, Sale
from app.utils import aggregate_sales, get_shop_id, shop_query

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def home():
    if current_user.is_super_admin:
        from flask import redirect, url_for

        return redirect(url_for("admin.shops"))

    shop_id = get_shop_id()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_sales = Sale.query.filter(
        Sale.shop_id == shop_id,
        Sale.created_at >= today_start,
    ).all()

    week_start = today_start - timedelta(days=today_start.weekday())
    week_sales = Sale.query.filter(
        Sale.shop_id == shop_id,
        Sale.created_at >= week_start,
    ).all()

    month_start = today_start.replace(day=1)
    month_sales = Sale.query.filter(
        Sale.shop_id == shop_id,
        Sale.created_at >= month_start,
    ).all()

    today_stats = aggregate_sales(today_sales)
    week_stats = aggregate_sales(week_sales)
    month_stats = aggregate_sales(month_sales)

    products = shop_query(Product).filter_by(is_active=True).all()
    low_stock = [p for p in products if p.is_low_stock]
    total_products = len(products)

    recent_sales = (
        Sale.query.filter_by(shop_id=shop_id)
        .order_by(Sale.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard/home.html",
        today_stats=today_stats,
        week_stats=week_stats,
        month_stats=month_stats,
        low_stock=low_stock,
        total_products=total_products,
        recent_sales=recent_sales,
        shop=current_user.shop,
    )
