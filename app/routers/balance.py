from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import get_current_user
from .. import models

router = APIRouter(prefix="/api/v1", tags=["balance"])

@router.get("/balance")
def get_balances(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        return {}
    bals = db.query(models.Balance).filter(models.Balance.user_id==user.id).all()
    res = {}
    for b in bals:
        res[b.ticker] = b.amount
    return res
