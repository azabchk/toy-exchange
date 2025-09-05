from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import get_current_user, require_admin
from .. import models
from ..schemas import Instrument
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

class BalanceOp(BaseModel):
    user_id: str
    ticker: str
    amount: int

@router.post("/instrument")
def add_instrument(body: Instrument, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    inst = models.Instrument(ticker=body.ticker, name=body.name)
    db.add(inst)
    db.commit()
    return {"success": True}

@router.delete("/instrument/{ticker}")
def delete_instrument(ticker: str, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    inst = db.query(models.Instrument).filter(models.Instrument.ticker==ticker).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Instrument not found")
    db.delete(inst)
    db.commit()
    return {"success": True}

@router.post("/balance/deposit")
def deposit(body: BalanceOp, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    bal = db.query(models.Balance).filter(models.Balance.user_id==body.user_id, models.Balance.ticker==body.ticker).first()
    if not bal:
        bal = models.Balance(user_id=body.user_id, ticker=body.ticker, amount=body.amount)
        db.add(bal)
    else:
        bal.amount += body.amount
    db.commit()
    return {"success": True}

@router.post("/balance/withdraw")
def withdraw(body: BalanceOp, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    bal = db.query(models.Balance).filter(models.Balance.user_id==body.user_id, models.Balance.ticker==body.ticker).first()
    if not bal or bal.amount < body.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    bal.amount -= body.amount
    db.commit()
    return {"success": True}

@router.delete("/user/{user_id}")
def delete_user(user_id: str, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(models.User).filter(models.User.id==user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(u)
    db.commit()
    return {"id": user_id, "name": u.name, "role": u.role.value, "api_key": u.api_key}
