# app/routers/order.py
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import Any

from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user
from ..matching import match_order

router = APIRouter(prefix="/api/v1", tags=["order"])

CASH_TICKER = "RUB"  # fiat cash ticker


def _get_or_create_balance(db: Session, user_id: str, ticker: str) -> models.Balance:
    """Fetch a balance row or create it if missing"""
    bal = (
        db.query(models.Balance)
        .filter(models.Balance.user_id == user_id, models.Balance.ticker == ticker)
        .first()
    )
    if not bal:
        bal = models.Balance(user_id=user_id, ticker=ticker, amount=0)
        db.add(bal)
        db.flush()
    return bal


@router.post("/order", response_model=schemas.CreateOrderResponse)
def create_order(body: dict, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a new order.
    Supports both Limit and Market orders.
    Balances are reserved at creation time:
      - BUY LIMIT: reserve RUB = price * qty
      - BUY MARKET: no reservation (match immediately)
      - SELL: reserve qty of ticker
    """
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")

    # validate body
    if "price" in body and body.get("price") is not None:
        order_body = schemas.LimitOrderBody(**body)
        otype = models.OrderType.LIMIT
    else:
        order_body = schemas.MarketOrderBody(**body)
        otype = models.OrderType.MARKET

    direction = models.Direction(order_body.direction)
    ticker = order_body.ticker
    qty = int(order_body.qty)
    price = int(getattr(order_body, "price", None)) if getattr(order_body, "price", None) is not None else None

    # Reserve balances
    if direction == models.Direction.BUY:
        if otype == models.OrderType.LIMIT:
            required = price * qty
            rub_bal = _get_or_create_balance(db, user.id, CASH_TICKER)
            if rub_bal.amount < required:
                raise HTTPException(status_code=400, detail="Insufficient RUB balance to place buy order")
            rub_bal.amount -= required
            db.flush()
    else:  # SELL
        user_bal = _get_or_create_balance(db, user.id, ticker)
        if user_bal.amount < qty:
            raise HTTPException(status_code=400, detail=f"Insufficient {ticker} balance to place sell order")
        user_bal.amount -= qty
        db.flush()

    # Create order
    order = models.Order(
        user_id=user.id,
        type=otype,
        direction=direction,
        ticker=ticker,
        qty=qty,
        price=price,
        status=models.OrderStatus.NEW,
        filled=0,
    )
    db.add(order)
    db.flush()

    # Run matching
    trades = match_order(db, order)
    db.commit()

    return {"success": True, "order_id": order.id}


@router.get("/orders", response_model=list[schemas.OrderOut])
def list_orders(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all orders for the authenticated user"""
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")
    orders = db.query(models.Order).filter(models.Order.user_id == user.id).all()
    return [
        {
            "id": o.id,
            "status": o.status.value,
            "user_id": o.user_id,
            "timestamp": o.timestamp,
            "body": {
                "direction": o.direction.value,
                "ticker": o.ticker,
                "qty": o.qty,
                "price": o.price,
            },
            "filled": o.filled,
        }
        for o in orders
    ]


@router.get("/order/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: str = Path(..., description="Order UUID"),
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get details of a specific order"""
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")
    o = db.query(models.Order).filter(models.Order.id == order_id, models.Order.user_id == user.id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": o.id,
        "status": o.status.value,
        "user_id": o.user_id,
        "timestamp": o.timestamp,
        "body": {
            "direction": o.direction.value,
            "ticker": o.ticker,
            "qty": o.qty,
            "price": o.price,
        },
        "filled": o.filled,
    }


@router.delete("/order/{order_id}", response_model=schemas.Ok)
def cancel_order(
    order_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel an active order and refund unfilled reserved balances.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")

    o = (
        db.query(models.Order)
        .filter(models.Order.id == order_id, models.Order.user_id == user.id)
        .first()
    )
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")

    if o.status in [models.OrderStatus.CANCELLED, models.OrderStatus.EXECUTED]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")

    unfilled_qty = o.qty - o.filled

    if unfilled_qty > 0:
        if o.direction == models.Direction.BUY:
            if o.price:  # refund RUB for unfilled part
                refund = unfilled_qty * o.price
                bal = _get_or_create_balance(db, user.id, CASH_TICKER)
                bal.amount += refund
        else:  # SELL refund ticker qty
            bal = _get_or_create_balance(db, user.id, o.ticker)
            bal.amount += unfilled_qty

    o.status = models.OrderStatus.CANCELLED
    db.commit()
    return {"success": True}
