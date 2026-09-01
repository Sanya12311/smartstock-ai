import pytest
from starlette.websockets import WebSocketDisconnect


def test_market_ws_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/market?token=garbage"):
            pass


def test_market_ws_accepts_valid_token_and_sends_snapshot(client, auth_headers, test_user):
    token = auth_headers["Authorization"].split(" ")[1]
    with client.websocket_connect(f"/ws/market?token={token}") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "snapshot"
        assert data["data"] == {}  # empty cache, honest — no fabricated ticks


def test_market_ws_requires_token_param(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/market"):
            pass


def test_notifications_ws_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/notifications?token=garbage"):
            pass


def test_notifications_ws_accepts_valid_token(client, auth_headers, test_user):
    token = auth_headers["Authorization"].split(" ")[1]
    with client.websocket_connect(f"/ws/notifications?token={token}") as websocket:
        # Connection succeeding without being immediately closed is the
        # signal here — this endpoint doesn't send an initial message.
        websocket.close()
