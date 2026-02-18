import MetaTrader5 as mt5
from datetime import datetime, timedelta
from trader.domain.models import SignalType, Position, Order, Candle


class MT5Executor:
    def __init__(self):
        self.is_connected = False
        self.timeframe_map = {
            1: mt5.TIMEFRAME_M1,
            5: mt5.TIMEFRAME_M5,
            15: mt5.TIMEFRAME_M15,
            60: mt5.TIMEFRAME_H1,
        }
        self.manual_offset_hours = 0

    def connect(self):
        if not mt5.initialize():
            print(f"❌ MT5 Init Failed: {mt5.last_error()}")
            return False
        self.is_connected = True
        print("✅ Connected to MetaTrader 5 (Live)")
        return True

    def shutdown(self):
        if self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            print("✅ MT5 Connection Closed")

    def get_candles(self, symbol: str, timeframe_minutes: int, count: int = 1):
        if not self.is_connected: return []
        tf_constant = self.timeframe_map.get(timeframe_minutes, mt5.TIMEFRAME_M5)
        rates = mt5.copy_rates_from_pos(symbol, tf_constant, 0, count)
        if rates is None or len(rates) == 0: return []

        candle_list = []
        for rate in rates:
            dt_raw = datetime.fromtimestamp(rate['time'])
            dt_corrected = dt_raw + timedelta(hours=self.manual_offset_hours)
            c = Candle(
                symbol=symbol, timestamp=dt_corrected,
                open=rate['open'], high=rate['high'], low=rate['low'],
                close=rate['close'], volume=rate['tick_volume']
            )
            candle_list.append(c)
        return candle_list

    def get_historical_data_as_dict(self, symbol: str, timeframe_minutes: int, count: int = 2000):
        candles = self.get_candles(symbol, timeframe_minutes, count)
        data = []
        for c in candles:
            data.append({
                'open': c.open, 'high': c.high, 'low': c.low,
                'close': c.close, 'volume': c.volume, 'timestamp': c.timestamp
            })
        return data

    def execute_order(self, order_or_signal):
        if not self.is_connected: return

        # Dynamic attribute retrieval (Handles both Order and Signal objects)
        direction = getattr(order_or_signal, 'order_type', getattr(order_or_signal, 'signal_type', None))
        if direction is None: return

        comment_text = getattr(order_or_signal, 'comment', getattr(order_or_signal, 'reason', "AutoTrade"))
        symbol = order_or_signal.symbol
        magic = int(order_or_signal.magic_number)

        # Position Flipping Logic (Hedging)
        open_positions = mt5.positions_get(symbol=symbol)
        if open_positions:
            for pos in open_positions:
                if pos.magic == magic:
                    is_buy_pos = (pos.type == mt5.ORDER_TYPE_BUY)
                    is_sell_pos = (pos.type == mt5.ORDER_TYPE_SELL)
                    is_buy_signal = (direction == SignalType.BUY)
                    is_sell_signal = (direction == SignalType.SELL)

                    if (is_buy_pos and is_sell_signal) or (is_sell_pos and is_buy_signal):
                        print(f"🔄 Flipping Position {pos.ticket}...")
                        self._close_position_by_ticket(pos.ticket, pos.symbol, pos.volume, pos.type, pos.magic)

        # Order Construction
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info: return

        filling_mode = mt5.ORDER_FILLING_FOK
        if (symbol_info.filling_mode & 1) != 0:
            filling_mode = mt5.ORDER_FILLING_FOK
        elif (symbol_info.filling_mode & 2) != 0:
            filling_mode = mt5.ORDER_FILLING_IOC
        else:
            filling_mode = mt5.ORDER_FILLING_RETURN

        mt5_type = mt5.ORDER_TYPE_BUY if direction == SignalType.BUY else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(symbol)
        raw_price = tick.ask if direction == SignalType.BUY else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(order_or_signal.volume),
            "type": mt5_type,
            "price": float(raw_price),
            "sl": float(order_or_signal.stop_loss),
            "tp": float(order_or_signal.take_profit),
            "deviation": 50,
            "magic": magic,
            "comment": str(comment_text)[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err_code = result.retcode if result else "Unknown"
            err_desc = result.comment if result else mt5.last_error()
            print(f"❌ Execution Error: {err_desc} (Code: {err_code})")
        else:
            print(f"🚀 ORDER EXECUTED! Ticket: {result.order}")

    def get_open_positions(self, symbol: str = None):
        if not self.is_connected: return []
        raw = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if not raw: return []

        clean = []
        for pos in raw:
            clean.append(Position(
                ticket=pos.ticket, symbol=pos.symbol,
                type="BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                volume=pos.volume, open_price=pos.price_open,
                current_price=pos.price_current, sl=pos.sl, tp=pos.tp,
                profit=pos.profit, time=datetime.fromtimestamp(pos.time)
            ))
        return clean

    def _close_position_by_ticket(self, ticket, symbol, volume, position_type, magic):
        close_type = mt5.ORDER_TYPE_SELL if position_type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(symbol)
        close_price = tick.bid if close_type == mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": volume,
            "type": close_type, "position": ticket, "price": close_price,
            "deviation": 50, "magic": magic, "comment": "Auto Close/Flip",
            "type_time": mt5.ORDER_TIME_GTC, "type_filling": mt5.ORDER_FILLING_FOK,
        }
        mt5.order_send(request)