from trader.domain.models import SignalType
from datetime import datetime


class AdvancedVirtualBroker:
    def __init__(self, initial_balance=10000.0, spread=0.15, digits=2, leverage=100, contract_size=100,
                 commission_per_lot=3.0, stop_level_points=10):
        # Financial Accounts
        self.balance = initial_balance
        self.equity = initial_balance
        self.margin = 0.0
        self.free_margin = initial_balance
        self.peak_balance = initial_balance
        self.max_drawdown_amount = 0.0
        self.max_drawdown_percent = 0.0

        # Broker Specifications
        self.spread = spread
        self.digits = digits
        self.point = 1 / (10 ** digits)
        self.leverage = leverage
        self.contract_size = contract_size
        self.commission_per_lot = commission_per_lot
        self.stop_level_points = stop_level_points

        # Database
        self.positions = {}  # Dictionary for direct ticket lookup
        self.closed_history = []
        self.ticket_counter = 1

    def normalize(self, price: float) -> float:
        return round(price, self.digits)

    def get_bid_ask(self, price: float):
        return self.normalize(price), self.normalize(price + self.spread)

    def get_positions(self, symbol=None):
        if symbol:
            return [p for p in self.positions.values() if p['symbol'] == symbol]
        return list(self.positions.values())

    def update_market_movement(self, candle):
        if candle.close >= candle.open:
            ticks = [candle.open, candle.low, candle.high, candle.close]
        else:
            ticks = [candle.open, candle.high, candle.low, candle.close]

        for tick_price in ticks:
            bid, ask = self.get_bid_ask(tick_price)
            self._check_sl_tp(bid, ask, candle.timestamp)

        final_bid, final_ask = self.get_bid_ask(candle.close)
        self.update_equity(final_bid, final_ask)

    def _check_sl_tp(self, bid: float, ask: float, timestamp: datetime):
        for ticket, pos in list(self.positions.items()):
            exit_price = None
            reason = ""

            if pos['type'] == SignalType.BUY:
                if pos['sl'] > 0 and bid <= pos['sl']:
                    exit_price = min(pos['sl'], bid)  # Slippage: if bid gapped below SL, exit at bid
                    reason = "SL"
                elif pos['tp'] > 0 and bid >= pos['tp']:
                    exit_price = max(pos['tp'], bid)
                    reason = "TP"
            else:
                if pos['sl'] > 0 and ask >= pos['sl']:
                    exit_price = max(pos['sl'], ask)  # Slippage: if ask gapped above SL, exit at ask
                    reason = "SL"
                elif pos['tp'] > 0 and ask <= pos['tp']:
                    exit_price = min(pos['tp'], ask)
                    reason = "TP"

            if exit_price is not None:
                self.close_position(ticket, exit_price, timestamp, reason, raw_price_provided=False)

    def open_position(self, direction: SignalType, volume: float, raw_price: float, sl: float, tp: float, symbol: str,
                      magic: int, comment: str, timestamp: datetime):
        bid, ask = self.get_bid_ask(raw_price)
        entry_price = ask if direction == SignalType.BUY else bid

        required_margin = (volume * self.contract_size * entry_price) / self.leverage
        commission = volume * self.commission_per_lot

        if self.free_margin < (required_margin + commission):
            print(f"⚠️ Broker Rejected: Insufficient Free Margin. Req: ${required_margin:.2f}")
            return None

        self.balance -= commission

        new_pos = {
            'ticket': self.ticket_counter,
            'magic': magic,
            'type': direction,
            'entry_price': entry_price,
            'volume': volume,
            'sl': self.normalize(sl),
            'tp': self.normalize(tp),
            'open_time': timestamp,
            'symbol': symbol,
            'entry_reason': comment,
            'commission': commission
        }

        self.positions[self.ticket_counter] = new_pos
        self.ticket_counter += 1

        self.margin += required_margin
        self.update_equity(bid, ask)
        return new_pos['ticket']

    def close_position(self, ticket: int, raw_price: float, timestamp: datetime, reason: str,
                       raw_price_provided: bool = True):
        if ticket not in self.positions: return
        pos = self.positions[ticket]

        if raw_price_provided:
            bid, ask = self.get_bid_ask(raw_price)
            exit_price = bid if pos['type'] == SignalType.BUY else ask
        else:
            exit_price = raw_price

        profit = 0
        if pos['type'] == SignalType.BUY:
            profit = (exit_price - pos['entry_price']) * pos['volume'] * self.contract_size
        else:
            profit = (pos['entry_price'] - exit_price) * pos['volume'] * self.contract_size

        self.balance += profit

        released_margin = (pos['volume'] * self.contract_size * pos['entry_price']) / self.leverage
        self.margin = max(0.0, self.margin - released_margin)

        self.closed_history.append({
            **pos,
            'exit_price': self.normalize(exit_price),
            'close_time': timestamp,
            'gross_profit': profit,
            'net_profit': profit - pos['commission'],
            'exit_reason': reason,
            'duration': (timestamp - pos['open_time']).total_seconds() / 60
        })

        del self.positions[ticket]

        if raw_price_provided:
            bid, ask = self.get_bid_ask(raw_price)
            self.update_equity(bid, ask)

    def update_equity(self, current_bid: float, current_ask: float):
        floating_pl = 0.0
        for pos in self.positions.values():
            current_price = current_bid if pos['type'] == SignalType.BUY else current_ask
            if pos['type'] == SignalType.BUY:
                floating_pl += (current_price - pos['entry_price']) * pos['volume'] * self.contract_size
            else:
                floating_pl += (pos['entry_price'] - current_price) * pos['volume'] * self.contract_size

        self.equity = self.balance + floating_pl
        self.free_margin = self.equity - self.margin

        if self.equity > self.peak_balance:
            self.peak_balance = self.equity

        current_drawdown = self.peak_balance - self.equity
        if current_drawdown > self.max_drawdown_amount:
            self.max_drawdown_amount = current_drawdown
            self.max_drawdown_percent = (current_drawdown / self.peak_balance) * 100