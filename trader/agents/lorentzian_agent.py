import numpy as np
import pandas as pd
from typing import Optional, Tuple
from trader.agents.base import TradingAgent
from trader.domain.models import Candle, Signal, SignalType
from trader.core.indicators import TechnicalAnalysis

class LorentzianClassificationAgent(TradingAgent):
    def __init__(self, name: str, magic_number: int):
        super().__init__(name, magic_number)
        self.neighbors_count = 8
        self.max_bars_back = 2000
        self.lookahead = 4
        self.kernel_h = 8.0
        self.kernel_r = 8.0
        self.kernel_x = 25
        self.last_signal_type = None

    def _calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        TechnicalAnalysis.add_rsi(df, length=14, column_name='f1')
        TechnicalAnalysis.add_wavetrend(df, chlen=10, avg=21, column_name='f2')
        TechnicalAnalysis.add_cci(df, length=20, column_name='f3')
        TechnicalAnalysis.add_adx_value(df, length=20, column_name='f4')
        TechnicalAnalysis.add_rsi(df, length=9, column_name='f5')
        TechnicalAnalysis.add_ema(df, length=200, column_name='ema_200')
        return df

    def _rational_quadratic_kernel(self, source_series: pd.Series, h: float, r: float) -> Tuple[float, float]:
        current_idx = len(source_series) - 1
        window_size = min(len(source_series), 100)
        y_hats = []
        for target_i in [current_idx, current_idx - 1]:
            numerator = 0.0
            denominator = 0.0
            start_j = max(0, target_i - window_size)
            for j in range(start_j, target_i + 1):
                y = source_series.iloc[j]
                distance_sq = (target_i - j) ** 2
                weight = (1 + distance_sq / (2 * r * h * h)) ** (-r)
                numerator += weight * y
                denominator += weight
            y_hats.append(numerator / denominator if denominator != 0 else 0.0)
        return y_hats[0], y_hats[1]

    def on_market_data(self, candle: Candle) -> Optional[Signal]:
        self.history.append({
            'open': candle.open, 'high': candle.high, 'low': candle.low,
            'close': candle.close, 'volume': candle.volume, 'timestamp': candle.timestamp
        })
        if len(self.history) > self.max_bars_back + 100: self.history.pop(0)
        if len(self.history) < 250: return None

        df = pd.DataFrame(self.history)
        df = self._calculate_features(df)
        df.dropna(inplace=True)
        if len(df) < self.neighbors_count + self.lookahead: return None

        df['future_close'] = df['close'].shift(-self.lookahead)
        train_df = df.dropna(subset=['future_close']).copy()
        train_df['label'] = np.where(train_df['future_close'] > train_df['close'], 1,
                                     np.where(train_df['future_close'] < train_df['close'], -1, 0))

        current_row = df.iloc[-1]
        feature_cols = ['f1', 'f2', 'f3', 'f4', 'f5']
        current_feats = current_row[feature_cols].values.astype(float)
        train_feats = train_df[feature_cols].values.astype(float)

        distances = np.sum(np.log1p(np.abs(train_feats - current_feats)), axis=1)
        train_df['distance'] = distances
        train_df.sort_values('distance', ascending=True, inplace=True)
        neighbors = train_df.iloc[:self.neighbors_count]
        prediction_score = neighbors['label'].sum()

        price = current_row['close']
        ema_200 = current_row['ema_200']
        adx_value = current_row['f4']
        is_uptrend = price > ema_200
        is_downtrend = price < ema_200
        is_volatile = adx_value > 20

        k_current, k_prev = self._rational_quadratic_kernel(df['close'], self.kernel_h, self.kernel_r)
        is_kernel_bullish = k_current > k_prev
        is_kernel_bearish = k_current < k_prev

        # DEBUG LOG
        print(f"\n📊 ANALYSIS [{candle.timestamp.strftime('%H:%M')}]: Score={prediction_score} | ADX={adx_value:.1f} | Kernel={'UP' if is_kernel_bullish else 'DOWN'}")

        final_signal = None
        if prediction_score > 0:
            if not is_uptrend: print("   ⛔ Skipped BUY: Price below EMA200")
            elif not is_kernel_bullish: print("   ⛔ Skipped BUY: Kernel is Bearish")
            elif not is_volatile: print(f"   ⛔ Skipped BUY: Low Volatility ({adx_value:.1f})")
            else:
                final_signal = SignalType.BUY
                print("   ✅ BUY SIGNAL CONFIRMED!")
        elif prediction_score < 0:
            if not is_downtrend: print("   ⛔ Skipped SELL: Price above EMA200")
            elif not is_kernel_bearish: print("   ⛔ Skipped SELL: Kernel is Bullish")
            elif not is_volatile: print(f"   ⛔ Skipped SELL: Low Volatility ({adx_value:.1f})")
            else:
                final_signal = SignalType.SELL
                print("   ✅ SELL SIGNAL CONFIRMED!")
        else:
             print("   ⚪ Neutral Prediction (Score 0)")

        if self.last_signal_type == SignalType.BUY:
            if prediction_score < 0 or is_kernel_bearish:
                self.last_signal_type = None
                return self._create_signal(candle, SignalType.SELL, is_exit=True)
        elif self.last_signal_type == SignalType.SELL:
            if prediction_score > 0 or is_kernel_bullish:
                self.last_signal_type = None
                return self._create_signal(candle, SignalType.BUY, is_exit=True)

        if final_signal and final_signal != self.last_signal_type:
            self.last_signal_type = final_signal
            return self._create_signal(candle, final_signal, is_exit=False)

        return None

    def _create_signal(self, candle: Candle, signal_type: SignalType, is_exit: bool) -> Signal:
        price = candle.close
        sl_pct = 0.005
        tp_pct = 0.015
        if signal_type == SignalType.BUY:
            sl = round(price * (1 - sl_pct), 2)
            tp = round(price * (1 + tp_pct), 2)
        else:
            sl = round(price * (1 + sl_pct), 2)
            tp = round(price * (1 - tp_pct), 2)

        reason = "Exit/Flip" if is_exit else "Lorentzian Entry"
        return Signal(
            agent_name=self.name, symbol=candle.symbol, signal_type=signal_type,
            price=price, reason=reason, magic_number=self.magic_number,
            volume=0.01, stop_loss=sl, take_profit=tp
        )