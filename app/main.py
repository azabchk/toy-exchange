from fastapi import FastAPI
from .database import engine, Base
from .routers import public, balance, order, admin
import os

# create DB tables (simple approach)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Toy Exchange API", version="0.1.0")

app.include_router(public.router)
app.include_router(balance.router)
app.include_router(order.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"message": "Toy Exchange API. See /docs for OpenAPI UI."}
