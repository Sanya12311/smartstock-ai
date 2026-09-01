from abc import ABC, abstractmethod


class BrokerInterface(ABC):
    """
    Common contract every broker integration must implement, so adding a
    second broker later (Zerodha, Upstox) means writing a new class here,
    not touching the connect/disconnect logic in app/services/broker_service.py.
    """

    @abstractmethod
    def generate_consent(self, app_id: str, app_secret: str, client_id: str) -> dict:
        """Step 1 of the connect flow. Returns at least {'consent_app_id', 'login_url'}."""

    @abstractmethod
    def exchange_token(self, app_id: str, app_secret: str, callback_params: dict) -> dict:
        """Step 3: exchange callback data for an access token.
        Returns at least {'access_token', 'expiry_time', 'broker_client_id'}."""

    @abstractmethod
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
        """Place a real order using the CONNECTED USER's own token/client id
        (never our app-level credentials). Returns {'order_id', 'order_status'}."""

    @abstractmethod
    def get_order_status(self, access_token: str, client_id: str, broker_order_id: str) -> dict:
        """Returns {'order_id', 'order_status'}."""

    @abstractmethod
    def cancel_order(self, access_token: str, client_id: str, broker_order_id: str) -> dict:
        """Cancel a pending order. Returns {'order_id', 'order_status'}."""
