"""Safaricom M-Pesa Daraja API client (Lipa Na M-Pesa STK Push)."""

import base64
import logging
import re
from datetime import datetime, timezone

import requests
from flask import current_app

logger = logging.getLogger(__name__)

SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"


class MpesaError(Exception):
    def __init__(self, message, response=None):
        super().__init__(message)
        self.response = response


def normalize_phone(phone: str) -> str:
    """Convert Kenyan phone to 2547XXXXXXXX format."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]
    if digits.startswith("254") and len(digits) == 12:
        return digits
    if digits.startswith("7") and len(digits) == 9:
        return "254" + digits
    raise ValueError("Enter a valid Kenyan phone number (e.g. 0712345678)")


class DarajaClient:
    def __init__(self, app=None):
        self._app = app

    def _cfg(self, key, default=None):
        if self._app:
            return self._app.config.get(key, default)
        return current_app.config.get(key, default)

    @property
    def base_url(self):
        env = self._cfg("MPESA_ENVIRONMENT", "sandbox")
        return PRODUCTION_BASE if env == "production" else SANDBOX_BASE

    def is_configured(self):
        return all(
            [
                self._cfg("MPESA_CONSUMER_KEY"),
                self._cfg("MPESA_CONSUMER_SECRET"),
                self._cfg("MPESA_SHORTCODE"),
                self._cfg("MPESA_PASSKEY"),
            ]
        )

    def get_access_token(self) -> str:
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        key = self._cfg("MPESA_CONSUMER_KEY")
        secret = self._cfg("MPESA_CONSUMER_SECRET")
        resp = requests.get(url, auth=(key, secret), timeout=30)
        if resp.status_code != 200:
            raise MpesaError(f"OAuth failed: {resp.text}", resp)
        return resp.json()["access_token"]

    def _password(self) -> tuple[str, str]:
        shortcode = self._cfg("MPESA_SHORTCODE")
        passkey = self._cfg("MPESA_PASSKEY")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        raw = f"{shortcode}{passkey}{timestamp}"
        password = base64.b64encode(raw.encode()).decode()
        return timestamp, password

    def _callback_url(self) -> str:
        explicit = self._cfg("MPESA_CALLBACK_URL")
        if explicit:
            return explicit
        base = self._cfg("APP_BASE_URL", "").rstrip("/")
        return f"{base}/api/mpesa/callback"

    def stk_push(
        self,
        phone: str,
        amount: float,
        account_reference: str,
        description: str,
    ) -> dict:
        phone = normalize_phone(phone)
        amount_int = int(round(amount))
        if amount_int < 1:
            raise ValueError("Amount must be at least KES 1")

        token = self.get_access_token()
        timestamp, password = self._password()
        shortcode = self._cfg("MPESA_SHORTCODE")
        transaction_type = self._cfg("MPESA_TRANSACTION_TYPE", "CustomerPayBillOnline")

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": transaction_type,
            "Amount": amount_int,
            "PartyA": phone,
            "PartyB": shortcode,
            "PhoneNumber": phone,
            "CallBackURL": self._callback_url(),
            "AccountReference": account_reference[:12],
            "TransactionDesc": description[:13],
        }

        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        data = resp.json()

        if resp.status_code != 200 or data.get("ResponseCode") != "0":
            msg = data.get("errorMessage") or data.get("ResponseDescription") or resp.text
            raise MpesaError(f"STK push failed: {msg}", resp)

        return data

    def stk_query(self, checkout_request_id: str) -> dict:
        token = self.get_access_token()
        timestamp, password = self._password()
        shortcode = self._cfg("MPESA_SHORTCODE")

        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        return resp.json()


daraja_client = DarajaClient()
