### 🏦 Toy Exchange API

This is a simplified stock exchange backend built using FastAPI, created as an educational project inspired by real-world financial markets. The platform allows users to register, manage their balances, and place buy/sell orders, supporting both market and limit types.

## 🚀 Key Features

User API:

User registration and token-based authentication

Balance inquiries across various instruments

Creating, canceling, and viewing orders (market & limit)

Viewing the order book for different instruments

(Optional) Access to transaction history and candlestick chart data

Admin API:

Managing users (list and delete)

Depositing and withdrawing funds

Adding or delisting instruments (e.g., stocks, bonds, tokens)

Tech Stack:

FastAPI for the backend framework

SQLAlchemy for database ORM

SQLite as the default database (can be replaced with PostgreSQL)

Uvicorn as the ASGI server

Docker support for containerization

## 📦 Installation Guide

To run locally:

git clone https://github.com/azabchk/toy-exchange.git
cd toy-exchange
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt


To start the server:

export DATABASE_URL=sqlite:///./toy_exchange.db
export ADMIN_API_KEY=admin-token-change-me
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


Access the server at: http://127.0.0.1:8000
API docs are available at: http://127.0.0.1:8000/docs

To run with Docker:

docker build -t toy-exchange .
docker run -p 8000:8000 toy-exchange
-----------------
thx
