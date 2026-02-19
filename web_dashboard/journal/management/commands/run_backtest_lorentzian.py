import sys
from django.core.management.base import BaseCommand

PROJECT_ROOT = r"G:\Trading-System"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from trader.executor.mt5_executor import MT5Executor
from trader.domain.models import Candle
from trader.agents.lorentzian_agent import LorentzianClassificationAgent
from journal.backtest.virtual_broker import AdvancedVirtualBroker
from journal.backtest.engine import UnifiedEngine
from journal.backtest.utils import save_backtest_results

class Command(BaseCommand):
    help = 'Runs Lorentzian Classification Machine Learning Backtest'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=60)
        parser.add_argument('--tf', type=int, default=5)

    def handle(self, *args, **kwargs):
        symbol = "XAUUSD"
        days = kwargs.get('days', 60)
        timeframe = kwargs.get('tf', 5)
        balance = 10000.0
        spread = 0.15
        warmup_candles = 2000

        mt5 = MT5Executor()
        if not mt5.connect():
            return

        trading_candles_count = days * (1440 // timeframe)
        total_fetch = trading_candles_count + warmup_candles

        raw_data = mt5.get_historical_data_as_dict(symbol, timeframe, count=total_fetch)
        mt5.shutdown()

        if len(raw_data) < total_fetch:
            return

        all_candles = [Candle(symbol=symbol, **d) for d in raw_data]
        training_data = all_candles[:warmup_candles]
        trading_data = all_candles[warmup_candles:]

        agent = LorentzianClassificationAgent("Lorentzian_BT", magic_number=5005)
        agent.history = [{
            'open': c.open, 'high': c.high, 'low': c.low,
            'close': c.close, 'volume': c.volume, 'timestamp': c.timestamp
        } for c in training_data]

        broker = AdvancedVirtualBroker(
            initial_balance=balance,
            spread=spread,
            digits=2,
            stop_level_points=10
        )
        engine = UnifiedEngine(agent, broker)

        broker, equity_curve = engine.run(
            ltf_data=trading_data,
            step_method='on_market_data'
        )

        save_backtest_results(
            agent.name, symbol, f"M{timeframe}", balance, spread,
            trading_data, broker, equity_curve
        )