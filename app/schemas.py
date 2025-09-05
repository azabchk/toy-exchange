# app/schemas.py
from __future__ import annotations
from pydantic import BaseModel, Field
from pydantic import ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# Use Pydantic v2 config to allow model creation from ORM objects
# (replaces orm_mode = True in v1)
BASE_MODEL_CONFIG = {"from_attributes": True}


class NewUser(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    name: str = Field(..., min_length=3)


class UserOut(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    id: str
    name: str
    role: str
    api_key: str


class Instrument(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    name: str
    ticker: str


class Level(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    price: int
    qty: int


class L2OrderBook(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    bid_levels: List[Level]
    ask_levels: List[Level]


class LimitOrderBody(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    direction: str
    ticker: str
    qty: int = Field(..., ge=1)
    price: int = Field(..., gt=0)


class MarketOrderBody(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    direction: str
    ticker: str
    qty: int = Field(..., ge=1)


class CreateOrderResponse(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    success: bool = True
    order_id: str


class Ok(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    success: bool = True


#
# Objects returned by public/admin endpoints (DB-derived)
# Add Transaction, Order, Balance, OrderDetail schemas so responses can be validated
#


class TransactionOut(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    id: Optional[str]
    ticker: str
    amount: int
    price: int
    timestamp: Optional[datetime]


class BalanceOut(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    id: Optional[str]
    user_id: str
    ticker: str
    amount: int


class OrderBody(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    direction: str
    ticker: str
    qty: int
    price: Optional[int] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(**BASE_MODEL_CONFIG)
    id: Optional[str]
    status: str
    user_id: Optional[str]
    timestamp: Optional[datetime]
    body: OrderBody
    filled: int = 0


# Generic list responses if you want typed lists in handlers
# Example: response_model=List[TransactionOut]
