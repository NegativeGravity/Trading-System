import sys
import os
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware

PROJECT_ROOT = r"G:\Trading-System"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trader.domain.models import Candle
from trader.executor.mt5_executor import MT5Executor
from trader.agents.mtf_sfp_agent import MultiTimeframeSFPAgent
from journal.backtest.virtual_broker import AdvancedVirtualBroker
from journal.backtest.engine import UnifiedEngine
from journal.backtest.chart_generator import generate_trade_chart
from journal.models import BacktestSession, Trade, EquityPoint


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        symbol = "XAUUSD"
        days = 60
        initial_balance = 10000
        spread = 0.15

        mt5 = MT5Executor()
        if not mt5.connect(): return

        print(f"📥 Fetching data for {symbol}...")
        raw_ltf = mt5.get_historical_data_as_dict(symbol, 1, count=days * 1440)
        raw_htf = mt5.get_historical_data_as_dict(symbol, 15, count=days * 100)

        ltf_candles = [Candle(symbol=symbol, **d) for d in raw_ltf]
        htf_candles = [Candle(symbol=symbol, **d) for d in raw_htf]

        agent = MultiTimeframeSFPAgent("SFP_Universal_BT", 888)
        broker = AdvancedVirtualBroker(initial_balance, spread, digits=2, stop_level=20)
        engine = UnifiedEngine(agent, broker)

        print("🚀 Starting Backtest...")
        broker, equity_curve = engine.run(ltf_candles, htf_data=htf_candles)

        with transaction.atomic():
            total_trades = len(broker.closed_history)
            wins = len([t for t in broker.closed_history if t['net_profit'] > 0])
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

            session = BacktestSession.objects.create(
                agent_name=agent.name,
                symbol=symbol,
                timeframe="M1/M15",
                initial_balance=initial_balance,
                spread_points=int(spread * 100),
                start_date=make_aware(ltf_candles[0].timestamp),
                end_date=make_aware(ltf_candles[-1].timestamp),
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

            EquityPoint.objects.bulk_create([
                EquityPoint(
                    session=session,
                    timestamp=make_aware(p['timestamp']),
                    balance=p['balance'],
                    equity=p['equity'],
                    drawdown_percent=p['dd']
                ) for p in equity_curve[::10]
            ])

        # Generate Visualization Chart
        if broker.closed_history:
            generate_trade_chart(ltf_candles, broker.closed_history, symbol)

        print(f"✅ Backtest Finished. Trades: {total_trades} | WinRate: {win_rate:.2f}%")