from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas
from ..auth import get_current_user
from ..matching import match_order
from typing import Any

router = APIRouter(prefix="/api/v1", tags=["order"])

@router.post("/order", response_model=schemas.CreateOrderResponse)
def create_order(body: dict, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # body may be LimitOrderBody or MarketOrderBody
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")
    if "price" in body:
        otype = models.OrderType.LIMIT
    else:
        otype = models.OrderType.MARKET
    order = models.Order(user_id=user.id, type=otype, direction=models.Direction(body["direction"]), ticker=body["ticker"], qty=body["qty"], price=body.get("price"))
    db.add(order)
    db.flush()
    # run matching in same transaction
    txs = match_order(db, order)
    db.commit()
    return {"order_id": order.id}

@router.get("/order")
def list_orders(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")
    orders = db.query(models.Order).filter(models.Order.user_id==user.id).all()
    results = []
    for o in orders:
        results.append({
            "id": o.id, "status": o.status.value, "user_id": o.user_id, "timestamp": o.timestamp.isoformat(), "body":{"direction": o.direction.value, "ticker": o.ticker, "qty": o.qty, "price": o.price}, "filled": o.filled
        })
    return results

@router.get("/order/{order_id}")
def get_order(order_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")
    o = db.query(models.Order).filter(models.Order.id==order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": o.id, "status": o.status.value, "user_id": o.user_id, "timestamp": o.timestamp.isoformat(), "body":{"direction": o.direction.value, "ticker": o.ticker, "qty": o.qty, "price": o.price}, "filled": o.filled
    }

@router.delete("/order/{order_id}")
def cancel_order(order_id: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Auth required")
    o = db.query(models.Order).filter(models.Order.id==order_id, models.Order.user_id==user.id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Order not found")
    if o.status in [models.OrderStatus.EXECUTED, models.OrderStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Cannot cancel")
    o.status = models.OrderStatus.CANCELLED
    db.commit()
    return {"success": True}
