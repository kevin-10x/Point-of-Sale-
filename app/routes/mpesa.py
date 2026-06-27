from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.extensions import csrf
from app.models import MpesaPayment
from app.services.payment_handlers import process_stk_callback, query_payment_status
from app.utils import shop_query

mpesa_bp = Blueprint("mpesa", __name__, url_prefix="/api/mpesa")


@mpesa_bp.route("/callback", methods=["POST"])
@csrf.exempt
def stk_callback():
    """Daraja STK push result callback (must be publicly reachable)."""
    payload = request.get_json(silent=True) or {}
    process_stk_callback(payload)
    return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})


@mpesa_bp.route("/status/<int:payment_id>")
@login_required
def payment_status(payment_id):
    payment = shop_query(MpesaPayment).filter_by(id=payment_id).first()
    if not payment:
        return jsonify({"error": "Not found"}), 404

    if payment.status == "pending":
        payment = query_payment_status(payment)

    return jsonify(
        {
            "id": payment.id,
            "status": payment.status,
            "payment_type": payment.payment_type,
            "sale_id": payment.sale_id,
            "result_desc": payment.result_desc,
            "mpesa_receipt": payment.mpesa_receipt_number,
        }
    )
