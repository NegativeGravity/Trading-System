import time
from trader.domain.models import Order


class UnifiedEngine:
    def __init__(self, agent, broker):
        self.agent = agent
        self.broker = broker

    def run(self, ltf_data, htf_data=None):
        """Supports Single and Multi-Timeframe data feeding."""
        equity_curve = []
        htf_idx = 0

        for ltf_candle in ltf_data:
            # Sync HTF candles based on timestamp
            if htf_data:
                while htf_idx < len(htf_data) and htf_data[htf_idx].timestamp <= ltf_candle.timestamp:
                    self.agent.on_htf_candle(htf_data[htf_idx])
                    htf_idx += 1

            # Process LTF candle
            signal = self.agent.on_ltf_candle(ltf_candle)

            if signal:
                self.broker.execute_order(signal, ltf_candle.timestamp)

            self.broker.check_sl_tp(ltf_candle)
            self.broker.update_equity(ltf_candle.close)

            equity_curve.append({
                'timestamp': ltf_candle.timestamp,
                'balance': self.broker.balance,
                'equity': self.broker.equity,
                'dd': self.broker.max_drawdown_percent
            })

        return self.broker, equity_curve