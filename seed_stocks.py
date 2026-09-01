"""
One-off script to seed the `stocks` table with a starter list of Indian
equities. Security IDs were looked up from Dhan's official scrip master
(https://images.dhan.co/api-data/api-scrip-master-detailed.csv) on the
NSE_EQ segment, series "EQ".

Usage (with the virtual environment activated):
    python seed_stocks.py
"""

from app.database import SessionLocal
from app.models.stock import Stock

SEED_STOCKS = [
    {"symbol": "TCS", "name": "Tata Consultancy Services", "security_id": "11536", "segment": "NSE_EQ"},
    {"symbol": "INFY", "name": "Infosys", "security_id": "1594", "segment": "NSE_EQ"},
    {"symbol": "RELIANCE", "name": "Reliance Industries", "security_id": "2885", "segment": "NSE_EQ"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "security_id": "1333", "segment": "NSE_EQ"},
    {"symbol": "SBIN", "name": "State Bank of India", "security_id": "3045", "segment": "NSE_EQ"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank", "security_id": "4963", "segment": "NSE_EQ"},
    # Indices, for the dashboard's Market Summary widget (Phase 17). Dhan
    # treats "index" as its own segment regardless of originating exchange.
    {"symbol": "NIFTY", "name": "Nifty 50", "security_id": "13", "segment": "IDX_I"},
    {"symbol": "BANKNIFTY", "name": "Nifty Bank", "security_id": "25", "segment": "IDX_I"},
    {"symbol": "SENSEX", "name": "Sensex", "security_id": "51", "segment": "IDX_I"},
]


def main() -> None:
    db = SessionLocal()
    try:
        added = 0
        for entry in SEED_STOCKS:
            exists = db.query(Stock).filter(Stock.symbol == entry["symbol"]).first()
            if exists:
                continue
            db.add(
                Stock(
                    symbol=entry["symbol"],
                    name=entry["name"],
                    exchange_segment=entry["segment"],
                    security_id=entry["security_id"],
                )
            )
            added += 1
        db.commit()
        print(f"Seeded {added} new stock(s); {len(SEED_STOCKS) - added} already existed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
