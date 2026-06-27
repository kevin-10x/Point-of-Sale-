from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask import Blueprint, make_response, render_template, request
from flask_login import current_user, login_required

from app.models import Product, Sale, SaleItem
from app.utils import aggregate_sales, get_shop_id, require_role, shop_query

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _parse_date_range():
    now = datetime.now(timezone.utc)
    start_str = request.args.get("start")
    end_str = request.args.get("end")

    if start_str:
        start = datetime.strptime(start_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if end_str:
        end = datetime.strptime(end_str, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    else:
        end = now

    return start, end


@reports_bp.route("/")
@login_required
@require_role("owner", "manager")
def index():
    if current_user.is_super_admin:
        from flask import abort

        abort(403)

    shop_id = get_shop_id()
    start, end = _parse_date_range()

    sales = (
        Sale.query.filter(
            Sale.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at <= end,
        )
        .order_by(Sale.created_at.desc())
        .all()
    )

    stats = aggregate_sales(sales)

    # Daily breakdown for chart
    daily = defaultdict(lambda: {"revenue": 0, "profit": 0, "count": 0})
    for sale in sales:
        day_key = sale.created_at.strftime("%Y-%m-%d")
        daily[day_key]["revenue"] += sale.total_amount
        daily[day_key]["profit"] += sale.total_profit
        daily[day_key]["count"] += 1

    sorted_days = sorted(daily.keys())
    chart_labels = sorted_days
    chart_revenue = [daily[d]["revenue"] for d in sorted_days]
    chart_profit = [daily[d]["profit"] for d in sorted_days]

    # Best-selling products
    product_stats = defaultdict(lambda: {"name": "", "quantity": 0, "revenue": 0, "profit": 0})
    sale_ids = [s.id for s in sales]
    if sale_ids:
        items = SaleItem.query.filter(SaleItem.sale_id.in_(sale_ids)).all()
        for item in items:
            pid = item.product_id
            if not product_stats[pid]["name"]:
                product = item.product
                product_stats[pid]["name"] = product.name if product else f"Product #{pid}"
            product_stats[pid]["quantity"] += item.quantity
            product_stats[pid]["revenue"] += item.subtotal
            product_stats[pid]["profit"] += item.profit

    top_products = sorted(
        product_stats.values(),
        key=lambda x: x["quantity"],
        reverse=True,
    )[:10]

    top_profit_products = sorted(
        product_stats.values(),
        key=lambda x: x["profit"],
        reverse=True,
    )[:10]

    # Payment method breakdown
    payment_stats = defaultdict(float)
    for sale in sales:
        payment_stats[sale.payment_method or "cash"] += sale.total_amount

    return render_template(
        "reports/index.html",
        stats=stats,
        sales=sales,
        start=start,
        end=end,
        chart_labels=chart_labels,
        chart_revenue=chart_revenue,
        chart_profit=chart_profit,
        top_products=top_products,
        top_profit_products=top_profit_products,
        payment_stats=dict(payment_stats),
    )


@reports_bp.route("/export")
@login_required
@require_role("owner", "manager")
def export_csv():
    shop_id = get_shop_id()
    start, end = _parse_date_range()

    sales = (
        Sale.query.filter(
            Sale.shop_id == shop_id,
            Sale.created_at >= start,
            Sale.created_at <= end,
        )
        .order_by(Sale.created_at.desc())
        .all()
    )

    lines = [
        "sale_id,date,cashier,payment_method,revenue,cost,profit,margin_pct,items"
    ]
    for sale in sales:
        margin = sale.profit_margin
        item_count = sum(i.quantity for i in sale.items)
        cashier_name = sale.cashier.username if sale.cashier else ""
        lines.append(
            f"{sale.id},{sale.created_at.strftime('%Y-%m-%d %H:%M')},"
            f"{cashier_name},{sale.payment_method},"
            f"{sale.total_amount:.2f},{sale.total_cost:.2f},"
            f"{sale.total_profit:.2f},{margin:.2f},{item_count}"
        )

    response = make_response("\n".join(lines))
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=sales_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv"
    )
    return response
