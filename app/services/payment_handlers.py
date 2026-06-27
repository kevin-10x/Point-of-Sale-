"""Complete M-Pesa payments after Daraja callback or STK query."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import current_app

from app.extensions import db
from app.models import MpesaPayment, Shop
from app.services.mpesa import DarajaClient, MpesaError, daraja_client, normalize_phone
from app.utils import create_sale_from_cart

logger = logging.getLogger(__name__)


def _extract_callback_metadata(metadata: dict) -> dict:
    result = {}
    if not metadata:
        return result
    for item in metadata.get("Item", []):
        name = item.get("Name")
        value = item.get("Value")
        if name:
            result[name] = value
    return result


def initiate_sale_payment(
    shop_id,
    cashier_id,
    phone,
    amount,
    cart_items,
    discount_amount=0,
    customer_id=None,
    branch_id=None,
    notes=None,
) -> MpesaPayment:
    phone = normalize_phone(phone)
    payment = MpesaPayment(
        shop_id=shop_id,
        payment_type="sale",
        amount=amount,
        phone_number=phone,
        status="pending",
        cart_json=json.dumps(cart_items),
        cashier_id=cashier_id,
        discount_amount=discount_amount,
        customer_id=customer_id,
        branch_id=branch_id,
        notes=notes,
    )
    db.session.add(payment)
    db.session.flush()

    if current_app.config.get("MPESA_ENABLED") and daraja_client.is_configured():
        try:
            result = daraja_client.stk_push(
                phone=phone,
                amount=amount,
                account_reference=f"SALE{payment.id}",
                description="POS Sale",
            )
            payment.merchant_request_id = result.get("MerchantRequestID")
            payment.checkout_request_id = result.get("CheckoutRequestID")
        except (MpesaError, ValueError) as e:
            payment.status = "failed"
            payment.result_desc = str(e)
            db.session.commit()
            raise
    else:
        # Dev/sandbox without credentials — auto-complete for local testing
        payment.merchant_request_id = f"DEV-{payment.id}"
        payment.checkout_request_id = f"DEV-CHK-{payment.id}"
        payment.status = "completed"
        payment.mpesa_receipt_number = f"DEV{payment.id:06d}"
        payment.result_code = 0
        payment.result_desc = "Simulated payment (MPESA_ENABLED=false)"
        payment.completed_at = datetime.now(timezone.utc)
        finalize_payment(payment)

    db.session.commit()
    return payment


def initiate_subscription_payment(shop_id, user_id, phone, plan: str) -> MpesaPayment:
    plans = current_app.config["SUBSCRIPTION_PLANS"]
    if plan not in plans:
        raise ValueError("Invalid subscription plan")

    amount = plans[plan]["price"]
    phone = normalize_phone(phone)

    payment = MpesaPayment(
        shop_id=shop_id,
        payment_type="subscription",
        amount=amount,
        phone_number=phone,
        status="pending",
        subscription_plan=plan,
        cashier_id=user_id,
    )
    db.session.add(payment)
    db.session.flush()

    if current_app.config.get("MPESA_ENABLED") and daraja_client.is_configured():
        try:
            result = daraja_client.stk_push(
                phone=phone,
                amount=amount,
                account_reference=f"SUB{shop_id}",
                description=f"Plan {plan}",
            )
            payment.merchant_request_id = result.get("MerchantRequestID")
            payment.checkout_request_id = result.get("CheckoutRequestID")
        except (MpesaError, ValueError) as e:
            payment.status = "failed"
            payment.result_desc = str(e)
            db.session.commit()
            raise
    else:
        payment.merchant_request_id = f"DEV-SUB-{payment.id}"
        payment.checkout_request_id = f"DEV-SUB-CHK-{payment.id}"
        payment.status = "completed"
        payment.mpesa_receipt_number = f"SUB{payment.id:06d}"
        payment.result_code = 0
        payment.result_desc = "Simulated subscription payment"
        payment.completed_at = datetime.now(timezone.utc)
        finalize_payment(payment)

    db.session.commit()
    return payment


def finalize_payment(payment: MpesaPayment) -> Optional[int]:
    """Create sale or activate subscription for a completed payment.

    NOTE: Caller is responsible for the final commit.
    """
    if payment.status == "completed":
        if payment.payment_type == "sale" and payment.sale_id:
            return payment.sale_id
        if payment.payment_type == "subscription" and payment.sale_id is None:
            # Already completed subscription — nothing more to do
            if payment.payment_type == "subscription":
                return None

    if payment.payment_type == "sale":
        cart = json.loads(payment.cart_json or "[]")
        if not cart:
            logger.warning("finalize_payment: empty cart for payment %s", payment.id)
            return None
        try:
            sale = create_sale_from_cart(
                cart_items=cart,
                cashier_id=payment.cashier_id,
                shop_id=payment.shop_id,
                payment_method="mpesa",
                discount_amount=payment.discount_amount or 0,
                customer_id=payment.customer_id,
                branch_id=payment.branch_id,
                notes=payment.notes,
                mpesa_receipt_number=payment.mpesa_receipt_number,
            )
            payment.sale_id = sale.id
            return sale.id
        except ValueError as e:
            logger.error("finalize_payment sale creation failed: %s", e)
            payment.status = "failed"
            payment.result_desc = str(e)
            db.session.commit()
            return None

    elif payment.payment_type == "subscription":
        shop = db.session.get(Shop, payment.shop_id)
        if shop and payment.subscription_plan:
            shop.subscription_plan = payment.subscription_plan
            shop.subscription_status = "active"
            days = current_app.config.get("SUBSCRIPTION_PERIOD_DAYS", 30)
            now = datetime.now(timezone.utc)
            base = shop.subscription_expires_at
            if base and base > now:
                shop.subscription_expires_at = base + timedelta(days=days)
            else:
                shop.subscription_expires_at = now + timedelta(days=days)

    payment.status = "completed"
    if not payment.completed_at:
        payment.completed_at = datetime.now(timezone.utc)
    return payment.sale_id


def process_stk_callback(payload: dict) -> Optional[MpesaPayment]:
    body = payload.get("Body", {})
    stk = body.get("stkCallback", {})
    checkout_id = stk.get("CheckoutRequestID")
    if not checkout_id:
        return None

    payment = MpesaPayment.query.filter_by(checkout_request_id=checkout_id).first()
    if not payment:
        logger.warning("Mpesa callback for unknown checkout: %s", checkout_id)
        return None

    if payment.status == "completed":
        return payment

    result_code = stk.get("ResultCode")
    payment.result_code = result_code
    payment.result_desc = stk.get("ResultDesc")

    if result_code == 0:
        meta = _extract_callback_metadata(stk.get("CallbackMetadata"))
        payment.mpesa_receipt_number = meta.get("MpesaReceiptNumber")
        payment.status = "completed"
        payment.completed_at = datetime.now(timezone.utc)
        finalize_payment(payment)
        db.session.commit()
    else:
        payment.status = "failed"
        db.session.commit()

    return payment


def query_payment_status(payment: MpesaPayment) -> MpesaPayment:
    if payment.status != "pending" or not payment.checkout_request_id:
        return payment

    if not current_app.config.get("MPESA_ENABLED") or not daraja_client.is_configured():
        return payment

    if payment.checkout_request_id.startswith("DEV"):
        return payment

    try:
        result = daraja_client.stk_query(payment.checkout_request_id)
        result_code = result.get("ResultCode")
        if result_code == "0":
            payment.status = "completed"
            payment.result_code = 0
            payment.result_desc = result.get("ResultDesc")
            payment.mpesa_receipt_number = result.get("MpesaReceiptNumber") or payment.mpesa_receipt_number
            payment.completed_at = datetime.now(timezone.utc)
            finalize_payment(payment)
            db.session.commit()
        elif result_code and str(result_code) != "1032":
            payment.status = "failed"
            payment.result_desc = result.get("ResultDesc")
            db.session.commit()
    except MpesaError as e:
        logger.error("STK query failed: %s", e)

    return payment
