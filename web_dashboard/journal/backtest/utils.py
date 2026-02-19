import logging
from typing import List, Dict, Any
from django.db import transaction
from django.utils.timezone import make_aware
from journal.models import BacktestSession, Trade, EquityPoint
from journal.backtest.chart_generator import export_tv_data

logger = logging.getLogger(__name__)

def save_backtest_results(
    agent_name: str, symbol: str, timeframe: str, initial_balance: float,
    spread: float, candles: List[Any], broker: Any, equity_curve: List[Dict[str, Any]]
) -> None:
    if not broker.closed_history:
        return

    total_trades = len(broker.closed_history)
    winning_trades = [t for t in broker.closed_history if t['net_profit'] > 0]
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0

    try:
        with transaction.atomic():
            session = BacktestSession.objects.create(
                agent_name=agent_name,
                symbol=symbol,
                timeframe=timeframe,
                initial_balance=initial_balance,
                spread_points=int(spread * 100),
                start_date=make_aware(candles[0].timestamp),
                end_date=make_aware(candles[-1].timestamp),
                final_balance=broker.balance,
                net_profit=broker.balance - initial_balance,
                max_drawdown_percent=broker.max_drawdown_percent,
                max_drawdown_amount=broker.max_drawdown_amount,
                win_rate=win_rate,
                total_trades=total_trades
            )

            Trade.objects.bulk_create([
                Trade(
                    session=session,
                    ticket=t['ticket'],
                    direction=t['type'].name,
                    entry_price=t['entry_price'],
                    exit_price=t['exit_price'],
                    sl=t.get('sl', 0.0),
                    tp=t.get('tp', 0.0),
                    volume=t['volume'],
                    gross_profit=t['gross_profit'],
                    net_profit=t['net_profit'],
                    open_time=make_aware(t['open_time']),
                    close_time=make_aware(t['close_time']),
                    duration_minutes=t['duration'],
                    entry_reason=t['entry_reason'],
                    exit_reason=t['exit_reason']
                ) for t in broker.closed_history
            ], batch_size=1000)

            step = max(1, len(equity_curve) // 1000)
            EquityPoint.objects.bulk_create([
                EquityPoint(
                    session=session,
                    timestamp=make_aware(p['timestamp']),
                    balance=p['balance'],
                    equity=p['equity'],
                    drawdown_percent=p['dd']
                ) for p in equity_curve[::step]
            ], batch_size=2000)

        export_tv_data(session.id, candles, broker.closed_history)

    except Exception as e:
        logger.error(f"Failed to save backtest results: {str(e)}")