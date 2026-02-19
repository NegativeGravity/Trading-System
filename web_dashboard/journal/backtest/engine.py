from trader.domain.models import SignalType


class UnifiedEngine:
    def __init__(self, agent, broker):
        self.agent = agent
        self.broker = broker

    def _execute_signal_as_executor(self, signal, timestamp, fallback_price):
        direction = getattr(signal, 'order_type', getattr(signal, 'signal_type', None))
        if direction is None: return

        symbol = signal.symbol
        magic = signal.magic_number
        raw_price = signal.price if signal.price > 0 else fallback_price

        open_positions = self.broker.get_positions(symbol=symbol)
        for pos in open_positions:
            if pos['magic'] == magic and pos['type'] != direction:
                self.broker.close_position(
                    ticket=pos['ticket'],
                    raw_price=raw_price,
                    timestamp=timestamp,
                    reason="Auto Flip"
                )

        stop_lvl = (self.broker.stop_level_points * self.broker.point) + self.broker.spread
        sl = signal.stop_loss
        tp = signal.take_profit
        bid, ask = self.broker.get_bid_ask(raw_price)

        if direction == SignalType.BUY:
            if sl > 0: sl = min(sl, bid - stop_lvl)
            if tp > 0: tp = max(tp, ask + stop_lvl)
        else:
            if sl > 0: sl = max(sl, ask + stop_lvl)
            if tp > 0: tp = min(tp, bid - stop_lvl)

        self.broker.open_position(
            direction=direction,
            volume=signal.volume,
            raw_price=raw_price,
            sl=sl,
            tp=tp,
            symbol=symbol,
            magic=magic,
            comment=getattr(signal, 'reason', "Auto"),
            timestamp=timestamp
        )

    def run(self, ltf_data, htf_data=None, step_method='on_market_data'):
        equity_curve = []
        htf_idx = 0

        is_mtf = hasattr(self.agent, 'on_htf_candle') and htf_data is not None

        if not hasattr(self.agent, step_method):
            raise AttributeError(f"Agent '{self.agent.name}' is missing the method: {step_method}()")

        process_method = getattr(self.agent, step_method)
        print(f"🚀 Engine Acting as Executor for {self.agent.name} using {step_method}()...")

        for ltf_candle in ltf_data:
            if is_mtf:
                while htf_idx < len(htf_data) and htf_data[htf_idx].timestamp <= ltf_candle.timestamp:
                    self.agent.on_htf_candle(htf_data[htf_idx])
                    htf_idx += 1

            self.broker.update_market_movement(ltf_candle)

            signal = process_method(ltf_candle)

            if signal:
                if isinstance(signal, list):
                    for s in signal:
                        if s: self._execute_signal_as_executor(s, ltf_candle.timestamp, ltf_candle.close)
                else:
                    self._execute_signal_as_executor(signal, ltf_candle.timestamp, ltf_candle.close)

            equity_curve.append({
                'timestamp': ltf_candle.timestamp,
                'balance': self.broker.balance,
                'equity': self.broker.equity,
                'dd': self.broker.max_drawdown_percent
            })

        return self.broker, equity_curve