from sqlalchemy.orm import Session
from . import models
from typing import List, Tuple

def get_orderbook_levels(db: Session, ticker: str, limit: int = 10):
    # build simple L2: aggregate by price
    bids = db.query(models.Order).filter(models.Order.ticker==ticker, models.Order.direction==models.Direction.BUY, models.Order.status==models.OrderStatus.NEW, models.Order.type==models.OrderType.LIMIT).all()
    asks = db.query(models.Order).filter(models.Order.ticker==ticker, models.Order.direction==models.Direction.SELL, models.Order.status==models.OrderStatus.NEW, models.Order.type==models.OrderType.LIMIT).all()

    def aggregate(orders, reverse=False):
        book = {}
        for o in orders:
            book[o.price] = book.get(o.price, 0) + (o.qty - o.filled)
        items = sorted(book.items(), key=lambda x: x[0], reverse=reverse)
        return [{"price": p, "qty": q} for p,q in items[:limit]]

    return {"bid_levels": aggregate(bids, reverse=True), "ask_levels": aggregate(asks, reverse=False)}

def match_order(db: Session, order: models.Order) -> List[models.Transaction]:
    """
    Very simple matching:
    - For MARKET BUY: consume cheapest asks.
    - For MARKET SELL: consume highest bids.
    - For LIMIT order: attempt to match against opposing side respecting price.
    Returns list of created Transaction objects (persisted inside db).
    Note: atomicity should be ensured by SQL transaction in caller.
    """
    txs = []
    remaining = order.qty - order.filled
    if remaining <= 0:
        return txs

    if order.type == models.OrderType.MARKET:
        # match against best orders
        opposite = db.query(models.Order).filter(models.Order.ticker==order.ticker, models.Order.direction != order.direction, models.Order.status==models.OrderStatus.NEW).order_by(models.Order.price.asc() if order.direction==models.Direction.BUY else models.Order.price.desc()).all()
    else:
        if order.direction == models.Direction.BUY:
            # buy limit - match asks with price <= order.price
            opposite = db.query(models.Order).filter(models.Order.ticker==order.ticker, models.Order.direction==models.Direction.SELL, models.Order.status==models.OrderStatus.NEW, models.Order.price<=order.price).order_by(models.Order.price.asc()).all()
        else:
            opposite = db.query(models.Order).filter(models.Order.ticker==order.ticker, models.Order.direction==models.Direction.BUY, models.Order.status==models.OrderStatus.NEW, models.Order.price>=order.price).order_by(models.Order.price.desc()).all()

    for opp in opposite:
        if remaining <= 0:
            break
        available = opp.qty - opp.filled
        if available <= 0:
            continue
        traded = min(available, remaining)
        # transaction price: use opp.price if limit, otherwise use opp.price
        price = opp.price if opp.price is not None else order.price or 0
        tx = models.Transaction(ticker=order.ticker, amount=traded, price=price)
        db.add(tx)
        txs.append(tx)
        # update fills
        opp.filled += traded
        if opp.filled >= opp.qty:
            opp.status = models.OrderStatus.EXECUTED
        else:
            opp.status = models.OrderStatus.PARTIALLY_EXECUTED
        remaining -= traded

    # update order fill
    order.filled = order.qty - remaining
    if order.filled >= order.qty:
        order.status = models.OrderStatus.EXECUTED
    elif order.filled > 0:
        order.status = models.OrderStatus.PARTIALLY_EXECUTED

    db.flush()
    return txs
