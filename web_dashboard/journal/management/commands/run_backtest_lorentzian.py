import sys

PROJECT_ROOT = r"G:\Trading-System"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from django.core.management.base import BaseCommand
from trader.executor.mt5_executor import MT5Executor
from trader.domain.models import Candle
from trader.agents.lorentzian_agent import LorentzianClassificationAgent
from journal.backtest.virtual_broker import AdvancedVirtualBroker
from journal.backtest.engine import UnifiedEngine
from journal.backtest.utils import save_backtest_results


class Command(BaseCommand):
    help = 'Runs Lorentzian Classification Backtest'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=5, help='Days to backtest')

    def handle(self, *args, **kwargs):
        symbol = "XAUUSD"
        days = kwargs['days']
        balance = 10000
        spread = 0.15
        timeframe = 5  # Lorentzian standard timeframe
        warmup_candles = 2000  # Required for ML Model Training

        mt5 = MT5Executor()
        if not mt5.connect(): return

        print(f"🟣 [Lorentzian] Fetching Data (M{timeframe})...")

        # Calculate total candles: Warmup + Backtest Period
        trading_candles_count = days * (1440 // timeframe)
        total_fetch = trading_candles_count + warmup_candles

        raw_data = mt5.get_historical_data_as_dict(symbol, timeframe, count=total_fetch)
        mt5.shutdown()

        if len(raw_data) < total_fetch:
            print(f"❌ Not enough data. Needed {total_fetch}, got {len(raw_data)}")
            return

        all_candles = [Candle(symbol=symbol, **d) for d in raw_data]

        # Split Data: Training (Warmup) vs. Trading (Backtest)
        training_data = all_candles[:warmup_candles]
        trading_data = all_candles[warmup_candles:]

        # Init Agent
        agent = LorentzianClassificationAgent("Lorentzian_BT", magic_number=5005)

        # ⚠️ CRITICAL: Pre-load history to match Live Mode behavior.
        # In live mode, we fetch 2000 candles *before* the loop starts.
        # Here, we feed the first 2000 candles to the agent's internal memory manually.
        print(f"⚙️ Training Model with {len(training_data)} candles...")
        agent.history = [d.__dict__ for d in training_data]  # Convert to dict as agent expects

        # Init Engine
        broker = AdvancedVirtualBroker(balance, spread, digits=2, stop_level=10)
        engine = UnifiedEngine(agent, broker)

        # Run Simulation on the remaining data
        print(f"🚀 Running Backtest on {len(trading_data)} candles...")
        broker, equity_curve = engine.run(trading_data)

        # Save Results
        save_backtest_results(
            agent.name, symbol, f"M{timeframe}", balance, spread,
            trading_data, broker, equity_curve
        )