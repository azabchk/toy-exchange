from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

class NewUser(BaseModel):
    name: str = Field(..., min_length=3)

class UserOut(BaseModel):
    id: str
    name: str
    role: str
    api_key: str

class Instrument(BaseModel):
    name: str
    ticker: str

class Level(BaseModel):
    price: int
    qty: int

class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]

class LimitOrderBody(BaseModel):
    direction: str
    ticker: str
    qty: int = Field(..., ge=1)
    price: int = Field(..., gt=0)

class MarketOrderBody(BaseModel):
    direction: str
    ticker: str
    qty: int = Field(..., ge=1)

class CreateOrderResponse(BaseModel):
    success: bool = True
    order_id: str

class Ok(BaseModel):
    success: bool = True
    
class Transaction(BaseModel):
    id: int
    ticker: str
    price: float
    quantity: int
    side: str  # "buy" or "sell"
    timestamp: datetime

    class Config:
        orm_mode = True