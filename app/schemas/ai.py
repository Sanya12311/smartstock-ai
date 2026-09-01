from typing import Any, Dict

from pydantic import BaseModel


class StockExplanation(BaseModel):
    symbol: str
    context: Dict[str, Any]
    explanation: str
    disclaimer: str
