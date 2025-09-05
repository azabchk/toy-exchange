import os
import tempfile
from fastapi.testclient import TestClient

# point the app to a temporary sqlite file
from app import main as app_main


def setup_module(module):
    # create a temp DB file
    tmp = tempfile.NamedTemporaryFile(prefix="test_toy_exchange_", delete=False)
    tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"
    os.environ["ADMIN_API_KEY"] = "test-admin-token"

    # reload modules: app_main already created tables during import;
    # to be safe we call create_all again
    from app.database import engine, Base
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    # remove the temp DB file
    dburl = os.environ.get("DATABASE_URL")
    if dburl and dburl.startswith("sqlite:///"):
        path = dburl.replace("sqlite:///", "")
        try:
            os.remove(path)
        except Exception:
            pass


def test_register_deposit_order_flow():
    client = TestClient(app_main.app)

    # register user
    r = client.post("/api/v1/public/register", json={"name": "bob"})
    assert r.status_code == 200
    data = r.json()
    assert "api_key" in data
    user_id = data["id"]
    user_key = data["api_key"]

    # deposit as admin
    r = client.post(
        "/api/v1/admin/balance/deposit",
        headers={"Authorization": f"TOKEN {os.environ['ADMIN_API_KEY']}"},
        json={"user_id": user_id, "ticker": "BTC", "amount": 10},
    )
    assert r.status_code == 200
    assert r.json().get("success") is True

    # place a limit buy
    r = client.post(
        "/api/v1/order",
        headers={"Authorization": f"TOKEN {user_key}"},
        json={"direction": "BUY", "ticker": "BTC", "qty": 1, "price": 100},
    )
    assert r.status_code == 200
    oid = r.json().get("order_id")
    assert oid

    # place a market sell to match
    r = client.post(
        "/api/v1/order",
        headers={"Authorization": f"TOKEN {user_key}"},
        json={"direction": "SELL", "ticker": "BTC", "qty": 1},
    )
    assert r.status_code == 200

    # check transactions
    r = client.get("/api/v1/public/transactions/BTC")
    assert r.status_code == 200
    txs = r.json()
    assert isinstance(txs, list)
    assert len(txs) >= 1
