import sys

PROJECT_ROOT = r"G:\Trading-System"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from django.core.management.base import BaseCommand
from trader.executor.mt5_executor import MT5Executor
from trader.domain.models import Candle
from trader.agents.mtf_sfp_agent import MultiTimeframeSFPAgent
from journal.backtest.virtual_broker import AdvancedVirtualBroker
from journal.backtest.engine import UnifiedEngine
from journal.backtest.utils import save_backtest_results


class Command(BaseCommand):
    help = 'Runs SFP Multi-Timeframe Backtest'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=3, help='Days to backtest')

    def handle(self, *args, **kwargs):
        symbol = "XAUUSD"
        days = kwargs['days']
        balance = 10000
        spread = 0.15

        mt5 = MT5Executor()
        if not mt5.connect(): return

        print(f"🔵 [SFP] Fetching Data for {days} days...")

        # Load HTF (15m) and LTF (1m) data
        raw_ltf = mt5.get_historical_data_as_dict(symbol, 1, count=days * 1440)
        raw_htf = mt5.get_historical_data_as_dict(symbol, 15, count=days * 100)
        mt5.shutdown()

        if not raw_ltf or not raw_htf:
            print("❌ Not enough data.")
            return

        ltf_candles = [Candle(symbol=symbol, **d) for d in raw_ltf]
        htf_candles = [Candle(symbol=symbol, **d) for d in raw_htf]

        # Init Agent & Engine
        agent = MultiTimeframeSFPAgent("SFP_Backtest", 888)
        broker = AdvancedVirtualBroker(balance, spread, digits=2, stop_level=10)
        engine = UnifiedEngine(agent, broker)

        # Run Multi-Timeframe Simulation
        print("🚀 Running Engine...")
        broker, equity_curve = engine.run(ltf_candles, htf_data=htf_candles)

        # Save Results
        save_backtest_results(
            agent.name, symbol, "M1/M15", balance, spread,
            ltf_candles, broker, equity_curve
        )