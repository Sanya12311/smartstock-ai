from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.brokers.dhan_broker import DhanBrokerError
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.broker import (
    BrokerConnectionStart,
    BrokerCredentials,
    BrokerFundsOut,
    BrokerHoldingOut,
    BrokerLoginUrl,
    BrokerStatus,
)
from app.services import broker_service

router = APIRouter(prefix="/broker", tags=["Broker"])


@router.post("/connect/start", response_model=BrokerConnectionStart)
def start_broker_connection(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    account = broker_service.start_connection(db, current_user)
    redirect_uri = f"{settings.APP_BASE_URL}/broker/connect/callback/{account.connection_token}"
    return {
        "connection_token": account.connection_token,
        "redirect_uri_to_register": redirect_uri,
        "instructions": (
            "Go to web.dhan.co -> profile icon -> Access DhanHQ APIs -> toggle to 'API Key' mode. "
            "Create a new app using the EXACT Redirect URL above, then submit the generated App ID "
            "and App Secret via POST /broker/connect/credentials."
        ),
    }


@router.post("/connect/credentials", response_model=BrokerLoginUrl)
def submit_broker_credentials(
    payload: BrokerCredentials,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return broker_service.submit_credentials(
            db,
            current_user,
            payload.connection_token,
            payload.dhan_client_id,
            payload.app_id,
            payload.app_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DhanBrokerError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Dhan connection failed: {exc}"
        )


@router.get("/connect/callback/{connection_token}", response_class=HTMLResponse)
def broker_callback(connection_token: str, request: Request, db: Session = Depends(get_db)):
    """
    Hit directly by the user's browser after they approve on Dhan's site —
    it cannot carry our normal Authorization header, so there's no auth
    dependency here; identity comes from the unguessable connection_token.
    """
    try:
        broker_service.complete_connection(db, connection_token, dict(request.query_params))
        return (
            "<html><body><h2>Broker connected successfully.</h2>"
            "<p>You can close this tab and return to SmartStock AI.</p></body></html>"
        )
    except (ValueError, DhanBrokerError) as exc:
        return HTMLResponse(
            content=f"<html><body><h2>Broker connection failed.</h2><p>{exc}</p></body></html>",
            status_code=400,
        )


@router.get("/status", response_model=BrokerStatus)
def get_broker_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = broker_service.get_status(db, current_user)
    if account is None:
        return BrokerStatus(broker_name="DHAN", status="NOT_CONNECTED")
    return account


@router.delete("/disconnect", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_broker(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    broker_service.disconnect(db, current_user)


@router.get("/holdings", response_model=List[BrokerHoldingOut])
def get_broker_holdings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Real demat holdings pulled live from Dhan — distinct from the manually-entered Portfolio page."""
    try:
        return broker_service.get_holdings(db, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DhanBrokerError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Dhan request failed: {exc}")


@router.get("/funds", response_model=BrokerFundsOut)
def get_broker_funds(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Real account balance/margin limits pulled live from Dhan."""
    try:
        return broker_service.get_funds(db, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except DhanBrokerError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Dhan request failed: {exc}")
