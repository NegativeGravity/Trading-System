import sys
from django.core.management.base import BaseCommand

PROJECT_ROOT = r"G:\Trading-System"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trader.executor.mt5_executor import MT5Executor
from trader.domain.models import Candle
from trader.agents.mtf_sfp_agent import MultiTimeframeSFPAgent
from journal.backtest.virtual_broker import AdvancedVirtualBroker
from journal.backtest.engine import UnifiedEngine
from journal.backtest.utils import save_backtest_results

class Command(BaseCommand):
    help = 'Runs SFP Multi-Timeframe Strategy Backtest'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=60)

    def handle(self, *args, **kwargs):
        symbol = "XAUUSD"
        days = kwargs.get('days', 60)
        balance = 10000.0
        spread = 0.15

        mt5 = MT5Executor()
        if not mt5.connect():
            return

        raw_ltf = mt5.get_historical_data_as_dict(symbol, 1, count=days * 1440)
        raw_htf = mt5.get_historical_data_as_dict(symbol, 15, count=days * 100)
        mt5.shutdown()

        if not raw_ltf or not raw_htf:
            return

        ltf_candles = [Candle(symbol=symbol, **d) for d in raw_ltf]
        htf_candles = [Candle(symbol=symbol, **d) for d in raw_htf]

        agent = MultiTimeframeSFPAgent("SFP_Backtest", 888)
        broker = AdvancedVirtualBroker(
            initial_balance=balance,
            spread=spread,
            digits=2,
            stop_level_points=10
        )
        engine = UnifiedEngine(agent, broker)

        broker, equity_curve = engine.run(
            ltf_data=ltf_candles,
            htf_data=htf_candles,
            step_method='on_ltf_candle'
        )

        save_backtest_results(
            agent.name, symbol, "M1/M15", balance, spread,
            ltf_candles, broker, equity_curve
        )