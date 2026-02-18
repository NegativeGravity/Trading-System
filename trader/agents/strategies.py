import pandas as pd
from agents.base import TradingAgent
from domain.models import Candle, Signal, SignalType
from core.indicators import TechnicalAnalysis


class TrendFollowerAgent(TradingAgent):

    def __init__(self, name: str, magic_number: int):
        super().__init__(name, magic_number)
        self.history = []

    def on_market_data(self, candle: Candle) -> Signal | None:
        self.history.append(candle.__dict__)

        if len(self.history) > 200:
            self.history.pop(0)

        if len(self.history) < 55: return None

        df = pd.DataFrame(self.history)
        TechnicalAnalysis.add_ema(df, length=50, column_name='ema_50')
        TechnicalAnalysis.add_rsi(df, length=14, column_name='rsi')
        TechnicalAnalysis.add_atr(df, length=14, column_name='atr')

        last_row = df.iloc[-1]
        price = candle.close
        ema = last_row['ema_50']
        rsi = last_row['rsi']
        atr = last_row['atr']

        if price > ema and 50 < rsi < 70:
            sl = price - 10
            tp = price + 10

            return Signal(
                agent_name=self.name,
                symbol=candle.symbol,
                signal_type=SignalType.BUY,
                price=price,
                reason=f"Trend Follower Agent",
                magic_number=self.magic_number,
                volume=0.01,
                stop_loss=round(sl, 2),
                take_profit=round(tp, 2)
            )

        return None


class PanicSellerAgent(TradingAgent):

    def __init__(self, name: str, magic_number: int):
        super().__init__(name, magic_number)
        self.history = []

    def on_market_data(self, candle: Candle) -> Signal | None:
        self.history.append(candle.__dict__)
        if len(self.history) > 100: self.history.pop(0)
        if len(self.history) < 20: return None

        df = pd.DataFrame(self.history)
        TechnicalAnalysis.add_rsi(df, length=14)
        rsi = df['rsi'].iloc[-1]

        if rsi > 80:
            return Signal(
                agent_name=self.name,
                symbol=candle.symbol,
                signal_type=SignalType.SELL,
                price=candle.close,
                reason=f"Panic Sell! RSI is {rsi:.1f}",
                magic_number=self.magic_number,
                volume=0.02,
                stop_loss=round(candle.close * 1.005, 5),
                take_profit=round(candle.close * 0.095, 5)
            )
        return None