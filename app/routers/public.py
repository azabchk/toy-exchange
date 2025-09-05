# app/routers/public.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
import uuid
import os

router = APIRouter(prefix="/api/v1/public", tags=["public"])

@router.post("/register", response_model=schemas.UserOut)
def register(body: schemas.NewUser, db: Session = Depends(get_db)):
    api_key = f"key-{uuid.uuid4()}"
    user = models.User(name=body.name, api_key=api_key)
    db.add(user)
    # initial balance example: give user some RUB
    db.flush()
    bal = models.Balance(user_id=user.id, ticker="RUB", amount=100000)
    db.add(bal)
    db.commit()
    return {"id": user.id, "name": user.name, "role": user.role.value, "api_key": user.api_key}

@router.get("/instrument", response_model=list[schemas.Instrument])
def list_instruments(db: Session = Depends(get_db)):
    instruments = db.query(models.Instrument).all()
    return [{"name": i.name, "ticker": i.ticker} for i in instruments]

@router.get("/orderbook/{ticker}", response_model=schemas.L2OrderBook)
def get_orderbook(ticker: str, limit: int = 10, db: Session = Depends(get_db)):
    from ..matching import get_orderbook_levels
    return get_orderbook_levels(db, ticker, limit=limit)

@router.get("/transactions/{ticker}", response_model=list[schemas.TransactionOut])
def get_transactions(ticker: str, limit: int = 10, db: Session = Depends(get_db)):
    txs = db.query(models.Transaction).filter(models.Transaction.ticker==ticker).order_by(models.Transaction.timestamp.desc()).limit(limit).all()
    return [{"id": t.id, "ticker": t.ticker, "amount": t.amount, "price": t.price, "timestamp": t.timestamp.isoformat() if t.timestamp else None} for t in txs]
