from trader.domain.models import SignalType


class AdvancedVirtualBroker:
    def __init__(self, initial_balance=10000.0, spread=0.15, digits=2, stop_level=0):
        self.balance = initial_balance
        self.equity = initial_balance
        self.spread = spread
        self.digits = digits
        self.stop_level_points = stop_level
        self.point = 1 / (10 ** digits)

        self.positions = []
        self.closed_history = []
        self.peak_balance = initial_balance
        self.max_drawdown_percent = 0.0
        self.max_drawdown_amount = 0.0
        self.ticket_counter = 1

    def _normalize(self, price):
        return round(price, self.digits)

    def _is_stop_level_valid(self, price, sl, tp, direction):
        """Simulates MT5 Broker Stop Level restrictions."""
        min_dist = (self.stop_level_points * self.point) + self.spread
        if direction == SignalType.BUY:
            if sl > 0 and (price - sl) < min_dist: return False
            if tp > 0 and (tp - price) < min_dist: return False
        else:
            if sl > 0 and (sl - price) < min_dist: return False
            if tp > 0 and (price - tp) < min_dist: return False
        return True

    def execute_order(self, order_or_signal, timestamp):
        """
        Handles execution for both 'Order' and 'Signal' objects.
        Matches MT5Executor logic 100%.
        """
        # 1. Determine Direction (Handle both Order and Signal objects)
        direction = getattr(order_or_signal, 'order_type', getattr(order_or_signal, 'signal_type', None))

        if direction is None:
            print("❌ Error: Valid direction not found in object.")
            return

        # 2. Extract common attributes
        volume = order_or_signal.volume
        sl_raw = order_or_signal.stop_loss
        tp_raw = order_or_signal.take_profit
        symbol = order_or_signal.symbol
        comment = getattr(order_or_signal, 'comment', getattr(order_or_signal, 'reason', "Auto"))
        base_price = order_or_signal.price

        # 3. Handle Flipping (Hedging Logic)
        for pos in list(self.positions):
            if pos['type'] != direction:
                # Close opposite positions using the signal price as a proxy for market price
                self.close_position(pos, base_price, timestamp, "Signal Flip")

        # 4. Calculate Entry Prices
        ask = self._normalize(base_price + self.spread)
        bid = self._normalize(base_price)

        entry_p = ask if direction == SignalType.BUY else bid

        # 5. Validate & Normalize SL/TP
        sl = self._normalize(sl_raw)
        tp = self._normalize(tp_raw)

        # Reset invalid stops to 0 (Simulating broker rejection)
        if not self._is_stop_level_valid(entry_p, sl, tp, direction):
            sl, tp = 0.0, 0.0

            # 6. Open New Position
        self.positions.append({
            'ticket': self.ticket_counter,
            'type': direction,
            'entry_price': entry_p,
            'volume': volume,
            'sl': sl, 'tp': tp,
            'open_time': timestamp,
            'symbol': symbol,
            'entry_reason': comment,
        })
        self.ticket_counter += 1

    def check_sl_tp(self, candle):
        """Checks if High/Low hit SL or TP."""
        ask_low = self._normalize(candle.low + self.spread)
        ask_high = self._normalize(candle.high + self.spread)
        bid_low = self._normalize(candle.low)
        bid_high = self._normalize(candle.high)

        for pos in list(self.positions):
            exit_p, reason = None, ""
            if pos['type'] == SignalType.BUY:
                if pos['sl'] > 0 and bid_low <= pos['sl']:
                    exit_p, reason = pos['sl'], "SL"
                elif pos['tp'] > 0 and bid_high >= pos['tp']:
                    exit_p, reason = pos['tp'], "TP"
            else:
                if pos['sl'] > 0 and ask_high >= pos['sl']:
                    exit_p, reason = pos['sl'], "SL"
                elif pos['tp'] > 0 and ask_low <= pos['tp']:
                    exit_p, reason = pos['tp'], "TP"

            if exit_p: self.close_position(pos, exit_p, candle.timestamp, reason)

    def close_position(self, pos, price, timestamp, reason):
        multiplier = 100 if "XAU" in pos['symbol'] else 100000
        side = 1 if pos['type'] == SignalType.BUY else -1
        profit = (price - pos['entry_price']) * side * pos['volume'] * multiplier
        self.balance += profit

        self.closed_history.append({
            **pos,
            'exit_price': self._normalize(price),
            'close_time': timestamp,
            'net_profit': profit,
            'gross_profit': profit,
            'exit_reason': reason,
            'duration': (timestamp - pos['open_time']).total_seconds() / 60
        })
        self.positions.remove(pos)

    def update_equity(self, current_close):
        floating_pl = 0
        for pos in self.positions:
            side = 1 if pos['type'] == SignalType.BUY else -1
            price = current_close if pos['type'] == SignalType.BUY else (current_close + self.spread)
            floating_pl += (price - pos['entry_price']) * side * pos['volume'] * 100

        self.equity = self.balance + floating_pl
        self.peak_balance = max(self.peak_balance, self.equity)
        dd = self.peak_balance - self.equity
        self.max_drawdown_amount = max(self.max_drawdown_amount, dd)
        self.max_drawdown_percent = max(self.max_drawdown_percent, (dd / self.peak_balance) * 100)