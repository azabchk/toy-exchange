# app/auth.py
import os
import logging
from typing import Optional

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from .database import get_db
from . import models

logger = logging.getLogger(__name__)

def _extract_api_key_from_authorization_header(
    authorization: Optional[str] = Header(None, convert_underscores=False)
) -> str:
    """
    Accept:
      - "TOKEN <key>"
      - "Token <key>"
      - "Bearer <key>"
      - "<key>" (raw key)
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) == 1:
        return parts[0]
    return parts[1]


def get_current_user(
    api_key: str = Depends(_extract_api_key_from_authorization_header),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Look up user by api_key. If not found and api_key matches ADMIN_API_KEY env var,
    auto-create a minimal ADMIN user only when ALLOW_ADMIN_AUTO_CREATE=true.
    """
    user = db.query(models.User).filter(models.User.api_key == api_key).first()
    if user:
        return user

    admin_key = os.getenv("ADMIN_API_KEY")
    allow_auto = os.getenv("ALLOW_ADMIN_AUTO_CREATE", "false").lower() == "true"
    if admin_key and api_key == admin_key and allow_auto:
        logger.info("api_key matches ADMIN_API_KEY and ALLOW_ADMIN_AUTO_CREATE=true -> creating admin user")
        try:
            # Resolve admin role attribute (enum or string)
            admin_role_attr = None
            if hasattr(models, "UserRole") and hasattr(models.UserRole, "ADMIN"):
                admin_role_attr = models.UserRole.ADMIN
            elif hasattr(models, "Role") and hasattr(models.Role, "ADMIN"):
                admin_role_attr = models.Role.ADMIN
            else:
                admin_role_attr = getattr(models, "UserRole", "ADMIN")

            admin_user = models.User(
                name=os.getenv("ADMIN_NAME", "admin"),
                role=admin_role_attr,
                api_key=api_key,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            logger.info("created admin user id: %s", getattr(admin_user, "id", "<unknown>"))
            return admin_user
        except Exception:
            logger.exception("failed to create admin user")
            raise HTTPException(status_code=401, detail="Invalid API key")

    raise HTTPException(status_code=401, detail="Invalid API key")


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Ensure the user has ADMIN role. Matches your startup code which uses models.UserRole.ADMIN.
    """
    role = getattr(current_user, "role", None)
    role_value = getattr(role, "value", role)

    admin_enum = getattr(models, "UserRole", None)
    admin_enum_member = getattr(admin_enum, "ADMIN", None) if admin_enum is not None else None

    if role == admin_enum_member or str(role_value).lower() == "admin" or str(role_value).upper() == "ADMIN":
        return current_user

    raise HTTPException(status_code=403, detail="Admin privileges required")
