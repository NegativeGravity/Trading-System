from django.db import transaction
from django.utils.timezone import make_aware
from journal.models import BacktestSession, Trade, EquityPoint
from journal.backtest.chart_generator import generate_trade_chart

def save_backtest_results(agent_name, symbol, timeframe, initial_balance, spread, candles, broker, equity_curve):
    """
    Persists backtest results to the SQLite database and generates the HTML chart.
    """
    if not broker.closed_history:
        print("⚠️ No trades to save.")
        return

    with transaction.atomic():
        total_trades = len(broker.closed_history)
        wins = len([t for t in broker.closed_history if t['net_profit'] > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        # Create Session Record
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

        # Bulk Create Trades
        Trade.objects.bulk_create([
            Trade(
                session=session,
                ticket=t['ticket'],
                direction=t['type'].name,
                entry_price=t['entry_price'],
                exit_price=t['exit_price'],
                sl=t.get('sl', 0),
                tp=t.get('tp', 0),
                volume=t['volume'],
                gross_profit=t['gross_profit'],
                net_profit=t['net_profit'],
                open_time=make_aware(t['open_time']),
                close_time=make_aware(t['close_time']),
                duration_minutes=t['duration'],
                entry_reason=t['entry_reason'],
                exit_reason=t['exit_reason']
            ) for t in broker.closed_history
        ])

        # Bulk Create Equity Curve Points (Downsampled)
        step = max(1, len(equity_curve) // 500)
        EquityPoint.objects.bulk_create([
            EquityPoint(
                session=session,
                timestamp=make_aware(p['timestamp']),
                balance=p['balance'],
                equity=p['equity'],
                drawdown_percent=p['dd']
            ) for p in equity_curve[::step]
        ])

    # Generate Standalone HTML Chart
    filename = f"chart_{agent_name}_{symbol}.html"
    generate_trade_chart(candles, broker.closed_history, symbol, filename=filename)
    print(f"✅ Results Saved. Trades: {total_trades} | WinRate: {win_rate:.2f}%")