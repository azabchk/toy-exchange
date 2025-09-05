from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .database import get_db
from . import models
from typing import Optional

def get_token_header(authorization: Optional[str] = Header(None)):
    # Accept header like: Authorization: TOKEN <token>
    if authorization is None:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].upper() == "TOKEN":
        return parts[1]
    raise HTTPException(status_code=400, detail="Bad Authorization header format")

def get_current_user(token: Optional[str] = Depends(get_token_header), db: Session = Depends(get_db)) -> Optional[models.User]:
    if token is None:
        return None
    user = db.query(models.User).filter(models.User.api_key == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API token")
    return user

def require_admin(user: models.User = Depends(get_current_user)):
    if not user or user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user
