import os
from fastapi import FastAPI
from .database import engine, Base, SessionLocal
from .routers import public, balance, order, admin
from . import models


# create DB tables (simple approach)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Toy Exchange API", version="0.1.0")

# include routers
app.include_router(public.router)
app.include_router(balance.router)
app.include_router(order.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"message": "Toy Exchange API. See /docs for OpenAPI UI."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def ensure_admin_exists():
    """
    If ADMIN_API_KEY is set in env, ensure there is a user with that api_key and ADMIN role.
    This is idempotent and safe for local/dev use.
    """
    api_key = os.getenv("ADMIN_API_KEY")
    if not api_key:
        return

    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.api_key == api_key).first()
        if not admin:
            admin = models.User(
                name=os.getenv("ADMIN_NAME", "admin"),
                role=models.UserRole.ADMIN,
                api_key=api_key,
            )
            db.add(admin)
            db.commit()
            print(f"[startup] created admin user: {admin.id}")
        else:
            # ensure role is ADMIN
            if admin.role != models.UserRole.ADMIN:
                admin.role = models.UserRole.ADMIN
                db.commit()
                print(f"[startup] promoted user {admin.id} to ADMIN")
    finally:
        db.close()
