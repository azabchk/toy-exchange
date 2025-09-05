# app/matching.py
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, and_
from typing import List

from . import models

CASH_TICKER = "RUB"


def _get_balance(db: Session, user_id: str, ticker: str) -> models.Balance:
    b = db.query(models.Balance).filter(models.Balance.user_id == user_id, models.Balance.ticker == ticker).with_for_update().first()
    if not b:
        b = models.Balance(user_id=user_id, ticker=ticker, amount=0)
        db.add(b)
        db.flush()
    return b


def match_order(db: Session, taker: models.Order) -> List[models.Transaction]:
    """
    Simplified matching engine:
      - For BUY taker: match against lowest price SELL makers.
      - For SELL taker: match against highest price BUY makers.
    Assumptions:
      - SELL orders reserve ticker qty at creation (their Balance already decremented).
      - BUY LIMIT orders reserve RUB at creation (their RUB Balance already decremented).
      - Market orders may not have reserves; if they do not match, leftover remains.
    Returns list of created Transaction objects.
    """
    created_trades = []

    # compute remaining qty on taker
    remaining = taker.qty - taker.filled

    while remaining > 0:
        # Build maker query depending on taker direction
        if taker.direction == models.Direction.BUY:
            # match against SELL orders with best (lowest) price
            if taker.type == models.OrderType.LIMIT:
                makers_q = db.query(models.Order).filter(
                    models.Order.ticker == taker.ticker,
                    models.Order.direction == models.Direction.SELL,
                    models.Order.status == models.OrderStatus.NEW,
                    models.Order.qty - models.Order.filled > 0,
                    models.Order.price <= taker.price
                ).order_by(asc(models.Order.price), asc(models.Order.timestamp)).with_for_update()
            else:
                makers_q = db.query(models.Order).filter(
                    models.Order.ticker == taker.ticker,
                    models.Order.direction == models.Direction.SELL,
                    models.Order.status == models.OrderStatus.NEW,
                    models.Order.qty - models.Order.filled > 0
                ).order_by(asc(models.Order.price), asc(models.Order.timestamp)).with_for_update()
        else:  # taker is SELL
            if taker.type == models.OrderType.LIMIT:
                makers_q = db.query(models.Order).filter(
                    models.Order.ticker == taker.ticker,
                    models.Order.direction == models.Direction.BUY,
                    models.Order.status == models.OrderStatus.NEW,
                    models.Order.qty - models.Order.filled > 0,
                    models.Order.price >= taker.price
                ).order_by(desc(models.Order.price), asc(models.Order.timestamp)).with_for_update()
            else:
                makers_q = db.query(models.Order).filter(
                    models.Order.ticker == taker.ticker,
                    models.Order.direction == models.Direction.BUY,
                    models.Order.status == models.OrderStatus.NEW,
                    models.Order.qty - models.Order.filled > 0
                ).order_by(desc(models.Order.price), asc(models.Order.timestamp)).with_for_update()

        maker = makers_q.first()
        if not maker:
            break

        maker_remaining = maker.qty - maker.filled
        trade_qty = min(remaining, maker_remaining)

        # Determine trade price:
        # - If maker has price (limit), use maker.price
        # - else if taker has price (limit), use taker.price
        # - else can't determine -> skip
        trade_price = None
        if maker.price is not None:
            trade_price = int(maker.price)
        elif taker.price is not None:
            trade_price = int(taker.price)
        else:
            # both market orders — we cannot set a price deterministically here.
            # In a simple setup, decline to match two pure market orders.
            break

        # Perform balance transfers
        # buyer_user_id, seller_user_id
        if taker.direction == models.Direction.BUY:
            buyer_id = taker.user_id
            seller_id = maker.user_id
        else:
            buyer_id = maker.user_id
            seller_id = taker.user_id

        total_rub = trade_price * trade_qty

        # Get / lock balances for both parties
        # Buyer: increase ticker balance; if buy was reserved (LIMIT), their RUB already deducted on order creation.
        buyer_ticker_balance = _get_balance(db, buyer_id, taker.ticker)
        seller_rub_balance = _get_balance(db, seller_id, CASH_TICKER)

        # If maker was BUY and reserved RUB upfront (for limit buy) we need to capture funds:
        # For simplicity we assume RUB for limit buys was already reserved when the buy order was placed (we decremented RUB).
        # For SELL side, at order creation we decremented seller's ticker balance to reserve.

        # Credit buyer's ticker balance
        buyer_ticker_balance.amount += trade_qty

        # Credit seller's RUB balance by total_rub
        seller_rub_balance.amount += total_rub

        # Update filled amounts and statuses
        maker.filled += trade_qty
        if maker.filled >= maker.qty:
            maker.status = models.OrderStatus.EXECUTED

        taker.filled += trade_qty
        if taker.filled >= taker.qty:
            taker.status = models.OrderStatus.EXECUTED

        # Persist a Transaction record (for history)
        tx = models.Transaction(
            ticker=taker.ticker,
            amount=trade_qty,
            price=trade_price
        )
        db.add(tx)
        # flush so id/timestamp is set
        db.flush()
        created_trades.append(tx)

        # Update remaining for loop
        remaining = taker.qty - taker.filled

        # Commit not here — caller will commit; but flush so other queries see updates
        db.flush()

    # If after matching taker still has remaining > 0 and is a BUY LIMIT we should release unspent RUB for leftover qty
    if taker.direction == models.Direction.BUY and taker.type == models.OrderType.LIMIT:
        leftover = taker.qty - taker.filled
        if leftover > 0:
            # calculate reserved originally: taker.price * taker.qty
            reserved_total = (taker.price or 0) * taker.qty
            spent_total = sum((t.price * t.amount) for t in created_trades) if created_trades else 0
            refund = reserved_total - spent_total
            if refund > 0:
                # refund back to taker RUB balance
                taker_rub = _get_balance(db, taker.user_id, CASH_TICKER)
                taker_rub.amount += refund
                db.flush()

    return created_trades
