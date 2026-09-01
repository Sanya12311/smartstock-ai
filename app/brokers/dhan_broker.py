"""
DhanHQ broker integration implementing the "Individual API Key & Secret"
3-step consent flow. Verified against official docs
(https://dhanhq.co/docs/v2/authentication/), August 2026.

This is NOT the "Partner" OAuth flow, which requires a formal business
approval from Dhan and lets any stranger click "Login with Dhan" without
prior setup. This individual-mode flow requires each user to first
generate their own app_id/app_secret on web.dhan.co using a Redirect URL
we assign them — see app/services/broker_service.py for the full sequence.
"""

import requests

from app.brokers.base import BrokerInterface

AUTH_BASE_URL = "https://auth.dhan.co"
API_BASE_URL = "https://api.dhan.co/v2"
REQUEST_TIMEOUT_SECONDS = 10


class DhanBrokerError(Exception):
    """Raised when a Dhan consent, token-exchange, or order API call fails."""


class DhanBroker(BrokerInterface):
    def generate_consent(self, app_id: str, app_secret: str, client_id: str) -> dict:
        url = f"{AUTH_BASE_URL}/app/generate-consent"
        try:
            response = requests.post(
                url,
                params={"client_id": client_id},
                headers={"app_id": app_id, "app_secret": app_secret},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise DhanBrokerError(f"Failed to generate Dhan consent: {exc}") from exc

        body = response.json()
        consent_app_id = body.get("consentAppId")
        if not consent_app_id:
            raise DhanBrokerError(f"Unexpected Dhan consent response: {body}")

        login_url = f"{AUTH_BASE_URL}/login/consentApp-login?consentAppId={consent_app_id}"
        return {"consent_app_id": consent_app_id, "login_url": login_url}

    def exchange_token(self, app_id: str, app_secret: str, callback_params: dict) -> dict:
        token_id = callback_params.get("tokenId")
        if not token_id:
            raise DhanBrokerError("Missing tokenId in Dhan callback")

        url = f"{AUTH_BASE_URL}/app/consumeApp-consent"
        try:
            response = requests.post(
                url,
                params={"tokenId": token_id},
                headers={"app_id": app_id, "app_secret": app_secret},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise DhanBrokerError(f"Failed to exchange Dhan consent token: {exc}") from exc

        body = response.json()
        access_token = body.get("accessToken")
        if not access_token:
            raise DhanBrokerError(f"Unexpected Dhan token exchange response: {body}")

        return {
            "access_token": access_token,
            "expiry_time": body.get("expiryTime"),
            "broker_client_id": body.get("dhanClientId"),
        }

    @staticmethod
    def _order_headers(access_token: str, client_id: str) -> dict:
        # Verified against dhanhq/_order.py + dhan_http.py: the connected
        # user's own access-token and client-id, NOT our app-level Dhan
        # credentials used for market data elsewhere in this app.
        return {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def place_order(
        self,
        access_token: str,
        client_id: str,
        security_id: str,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product_type: str,
        price: float,
    ) -> dict:
        url = f"{API_BASE_URL}/orders"
        payload = {
            "transactionType": transaction_type.upper(),
            "exchangeSegment": exchange_segment.upper(),
            "productType": product_type.upper(),
            "orderType": order_type.upper(),
            "validity": "DAY",
            "securityId": security_id,
            "quantity": int(quantity),
            "disclosedQuantity": 0,
            "price": float(price),
            "triggerPrice": 0.0,
        }
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._order_headers(access_token, client_id),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise DhanBrokerError(f"Order placement failed: {exc}") from exc

        body = response.json()
        order_id = body.get("orderId")
        if not order_id:
            raise DhanBrokerError(f"Unexpected order placement response: {body}")
        return {"order_id": order_id, "order_status": body.get("orderStatus", "PENDING")}

    def get_order_status(self, access_token: str, client_id: str, broker_order_id: str) -> dict:
        url = f"{API_BASE_URL}/orders/{broker_order_id}"
        try:
            response = requests.get(
                url, headers=self._order_headers(access_token, client_id), timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise DhanBrokerError(f"Order status check failed: {exc}") from exc

        body = response.json()
        return {"order_id": body.get("orderId"), "order_status": body.get("orderStatus")}

    def cancel_order(self, access_token: str, client_id: str, broker_order_id: str) -> dict:
        url = f"{API_BASE_URL}/orders/{broker_order_id}"
        try:
            response = requests.delete(
                url, headers=self._order_headers(access_token, client_id), timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise DhanBrokerError(f"Order cancellation failed: {exc}") from exc

        body = response.json()
        return {"order_id": body.get("orderId"), "order_status": body.get("orderStatus", "CANCELLED")}

    def modify_order(
        self,
        access_token: str,
        client_id: str,
        broker_order_id: str,
        order_type: str,
        quantity: int,
        price: float,
    ) -> dict:
        url = f"{API_BASE_URL}/orders/{broker_order_id}"
        payload = {
            "dhanClientId": client_id,
            "orderId": broker_order_id,
            "orderType": order_type.upper(),
            # Only ever LIMIT orders on a plain CNC delivery order (see place_order) —
            # legName is only meaningful for Bracket/Cover order legs, which this app
            # never places, so "NA" per Dhan's convention for non-BO/CO orders.
            "legName": "NA",
            "quantity": int(quantity),
            "price": float(price),
            "disclosedQuantity": 0,
            "triggerPrice": 0.0,
            "validity": "DAY",
        }
        try:
            response = requests.put(
                url,
                json=payload,
                headers=self._order_headers(access_token, client_id),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise DhanBrokerError(f"Order modification failed: {exc}") from exc

        body = response.json()
        return {"order_id": body.get("orderId"), "order_status": body.get("orderStatus", "PENDING")}

    def get_holdings(self, access_token: str, client_id: str) -> list:
        url = f"{API_BASE_URL}/holdings"
        try:
            response = requests.get(
                url, headers=self._order_headers(access_token, client_id), timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise DhanBrokerError(f"Failed to fetch holdings: {exc}") from exc

        body = response.json()
        return [
            {
                "exchange": item.get("exchange"),
                "trading_symbol": item.get("tradingSymbol"),
                "security_id": item.get("securityId"),
                "isin": item.get("isin"),
                "total_qty": item.get("totalQty"),
                "dp_qty": item.get("dpQty"),
                "t1_qty": item.get("t1Qty"),
                "available_qty": item.get("availableQty"),
                "collateral_qty": item.get("collateralQty"),
                "avg_cost_price": item.get("avgCostPrice"),
            }
            for item in body
        ]

    def get_fund_limits(self, access_token: str, client_id: str) -> dict:
        url = f"{API_BASE_URL}/fundlimit"
        try:
            response = requests.get(
                url, headers=self._order_headers(access_token, client_id), timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise DhanBrokerError(f"Failed to fetch fund limits: {exc}") from exc

        body = response.json()
        return {
            # Dhan's own API spells these fields "availabelBalance" / "receiveableAmount" (typos in their JSON) —
            # normalized here to correctly-spelled snake_case for the rest of this app.
            "available_balance": body.get("availabelBalance"),
            "sod_limit": body.get("sodLimit"),
            "collateral_amount": body.get("collateralAmount"),
            "receivable_amount": body.get("receiveableAmount"),
            "utilized_amount": body.get("utilizedAmount"),
            "blocked_payout_amount": body.get("blockedPayoutAmount"),
            "withdrawable_balance": body.get("withdrawableBalance"),
        }
