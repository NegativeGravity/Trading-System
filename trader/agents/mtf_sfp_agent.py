import numpy as np
from typing import Optional, List, Dict
from trader.agents.base import TradingAgent
from trader.domain.models import Candle, Signal, SignalType

class MultiTimeframeSFPAgent(TradingAgent):
    def __init__(self, name: str, magic_number: int):
        super().__init__(name, magic_number)
        self.htf_pivot_len = 5
        self.htf_pivots_high: List[float] = []
        self.htf_pivots_low: List[float] = []
        self.htf_history: List[Candle] = []
        self.ltf_pivot_len = 3
        self.ltf_history: List[Candle] = []
        self.ltf_recent_highs: List[Dict] = []
        self.ltf_recent_lows: List[Dict] = []
        self.active_setup = None
        self.max_choch_wait_candles = 45

    def on_market_data(self, candle: Candle):
        pass

    def on_htf_candle(self, candle: Candle):
        self.htf_history.append(candle)
        if len(self.htf_history) > 200: self.htf_history.pop(0)
        self._update_htf_pivots()
        if self.active_setup is None:
            self._check_htf_sfp(candle)

    def _update_htf_pivots(self):
        if len(self.htf_history) < self.htf_pivot_len * 2 + 1: return
        idx = len(self.htf_history) - 1 - self.htf_pivot_len
        candidate = self.htf_history[idx]
        window = self.htf_history[idx - self.htf_pivot_len: idx + self.htf_pivot_len + 1]
        is_high = all(c.high <= candidate.high for c in window)
        is_low = all(c.low >= candidate.low for c in window)
        if is_high:
            if not self.htf_pivots_high or candidate.high != self.htf_pivots_high[-1]:
                self.htf_pivots_high.append(candidate.high)
        if is_low:
            if not self.htf_pivots_low or candidate.low != self.htf_pivots_low[-1]:
                self.htf_pivots_low.append(candidate.low)

    def _check_htf_sfp(self, candle: Candle):
        for pivot in self.htf_pivots_high[-3:]:
            if candle.high > pivot and candle.close < pivot:
                self.active_setup = {
                    'type': 'BEARISH', 'pivot_level': pivot,
                    'sfp_candle': candle, 'ltf_candles_passed': 0
                }
                return
        for pivot in self.htf_pivots_low[-3:]:
            if candle.low < pivot and candle.close > pivot:
                self.active_setup = {
                    'type': 'BULLISH', 'pivot_level': pivot,
                    'sfp_candle': candle, 'ltf_candles_passed': 0
                }
                return

    def on_ltf_candle(self, candle: Candle) -> Optional[Signal]:
        self.ltf_history.append(candle)
        if len(self.ltf_history) > 100: self.ltf_history.pop(0)
        self.update_ltf_structure()
        if self.active_setup:
            return self._check_ltf_choch(candle)
        return None

    def update_ltf_structure(self):
        if len(self.ltf_history) < self.ltf_pivot_len * 2 + 1: return
        idx = len(self.ltf_history) - 1 - self.ltf_pivot_len
        candidate = self.ltf_history[idx]
        window = self.ltf_history[idx - self.ltf_pivot_len: idx + self.ltf_pivot_len + 1]
        if all(c.high <= candidate.high for c in window):
            self.ltf_recent_highs.append({'price': candidate.high, 'time': candidate.timestamp})
        if all(c.low >= candidate.low for c in window):
            self.ltf_recent_lows.append({'price': candidate.low, 'time': candidate.timestamp})

    def _check_ltf_choch(self, current_candle: Candle) -> Optional[Signal]:
        self.active_setup['ltf_candles_passed'] += 1
        if self.active_setup['ltf_candles_passed'] > self.max_choch_wait_candles:
            self.active_setup = None
            return None
        setup_type = self.active_setup['type']
        if setup_type == 'BEARISH':
            if not self.ltf_recent_lows: return None
            last_low_struct = self.ltf_recent_lows[-1]['price']
            if current_candle.close < last_low_struct:
                return self._execute_trade(current_candle, SignalType.SELL)
        elif setup_type == 'BULLISH':
            if not self.ltf_recent_highs: return None
            last_high_struct = self.ltf_recent_highs[-1]['price']
            if current_candle.close > last_high_struct:
                return self._execute_trade(current_candle, SignalType.BUY)
        return None

    def _execute_trade(self, candle: Candle, signal_type: SignalType) -> Signal:
        entry_price = candle.close
        sl = 0.0
        tp = 0.0
        htf_sfp_candle = self.active_setup['sfp_candle']

        if signal_type == SignalType.SELL:
            if self.ltf_recent_highs:
                last_pivot_high = self.ltf_recent_highs[-1]['price']
                sl = last_pivot_high + (last_pivot_high * 0.0005)
            else:
                sl = htf_sfp_candle.high + (htf_sfp_candle.high * 0.0005)
            risk = abs(sl - entry_price)
            tp = entry_price - (risk * 2)
        else:
            if self.ltf_recent_lows:
                last_pivot_low = self.ltf_recent_lows[-1]['price']
                sl = last_pivot_low - (last_pivot_low * 0.0005)
            else:
                sl = htf_sfp_candle.low - (htf_sfp_candle.low * 0.0005)
            risk = abs(entry_price - sl)
            tp = entry_price + (risk * 2)

        self.active_setup = None
        return Signal(
            agent_name=self.name, symbol=candle.symbol, signal_type=signal_type,
            price=entry_price, reason="SFP + LTF Pivot SL", magic_number=self.magic_number,
            volume=0.01, stop_loss=round(sl, 2), take_profit=round(tp, 2)
        )