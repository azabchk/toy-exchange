import enum
import uuid
from sqlalchemy import Column, String, Integer, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    api_key = Column(String, unique=True, nullable=False)

class Instrument(Base):
    __tablename__ = "instruments"
    ticker = Column(String, primary_key=True)
    name = Column(String, nullable=False)

class Balance(Base):
    __tablename__ = "balances"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    ticker = Column(String)
    amount = Column(Integer, default=0)

class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"

class OrderType(str, enum.Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"

class Direction(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"))
    type = Column(Enum(OrderType))
    direction = Column(Enum(Direction))
    ticker = Column(String)
    qty = Column(Integer)
    price = Column(Integer, nullable=True)  # for limit orders
    status = Column(Enum(OrderStatus), default=OrderStatus.NEW)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    filled = Column(Integer, default=0)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker = Column(String)
    amount = Column(Integer)
    price = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
