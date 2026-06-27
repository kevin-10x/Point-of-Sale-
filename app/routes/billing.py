from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.models import MpesaPayment
from app.services.payment_handlers import initiate_subscription_payment
from app.services.mpesa import MpesaError
from app.utils import get_shop_id, require_role

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


@billing_bp.route("/")
@login_required
@require_role("owner")
def index():
    from flask import current_app

    shop = current_user.shop
    plans = current_app.config["SUBSCRIPTION_PLANS"]
    recent = (
        MpesaPayment.query.filter_by(shop_id=shop.id, payment_type="subscription")
        .order_by(MpesaPayment.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "billing/index.html",
        shop=shop,
        plans=plans,
        recent_payments=recent,
        mpesa_enabled=current_app.config.get("MPESA_ENABLED"),
    )


@billing_bp.route("/subscribe", methods=["POST"])
@login_required
@require_role("owner")
def subscribe():
    plan = request.form.get("plan")
    phone = request.form.get("phone", "").strip()

    if not phone:
        flash("Enter your M-Pesa phone number.", "danger")
        return redirect(url_for("billing.index"))

    try:
        payment = initiate_subscription_payment(
            shop_id=get_shop_id(),
            user_id=current_user.id,
            phone=phone,
            plan=plan,
        )
        if payment.status == "completed":
            flash("Subscription activated successfully.", "success")
            return redirect(url_for("billing.index"))
        return redirect(url_for("billing.pending", payment_id=payment.id))
    except (ValueError, MpesaError) as e:
        flash(str(e), "danger")
        return redirect(url_for("billing.index"))


@billing_bp.route("/pending/<int:payment_id>")
@login_required
@require_role("owner")
def pending(payment_id):
    payment = MpesaPayment.query.filter_by(
        id=payment_id,
        shop_id=get_shop_id(),
        payment_type="subscription",
    ).first_or_404()
    return render_template("billing/pending.html", payment=payment)
