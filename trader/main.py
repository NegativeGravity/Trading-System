import time
import sys
from datetime import datetime
import pandas as pd

from core.engine import TradingEngine
from executor.mt5_executor import MT5Executor
from domain.models import Candle, SignalType, Order
from agents.lorentzian_agent import LorentzianClassificationAgent
from agents.mtf_sfp_agent import MultiTimeframeSFPAgent

SYMBOL_NAME = "XAUUSD"


def dict_to_candle(c_data):
    return Candle(
        timestamp=c_data['timestamp'],
        open=c_data['open'],
        high=c_data['high'],
        low=c_data['low'],
        close=c_data['close'],
        volume=c_data['volume'],
        symbol=SYMBOL_NAME
    )


if __name__ == "__main__":
    executor = MT5Executor()
    if not executor.connect():
        sys.exit()

    engine = TradingEngine()

    ml_agent = LorentzianClassificationAgent("Lorentzian-1M", magic_number=5005)
    mtf_sfp_agent = MultiTimeframeSFPAgent("MTF-SFP-Bot", magic_number=8888)

    engine.register_agent(ml_agent)
    engine.register_agent(mtf_sfp_agent)

    print(f"Loading Historical Data for {SYMBOL_NAME}...")

    # Load 15m Data (HTF SFP)
    hist_15m = executor.get_historical_data_as_dict(SYMBOL_NAME, timeframe_minutes=15, count=500)
    if hist_15m:
        print(f"Loaded {len(hist_15m)} candles for HTF SFP.")
        for data in hist_15m:
            mtf_sfp_agent.on_htf_candle(dict_to_candle(data))

    # Load 1m Data (Lorentzian & LTF SFP)
    hist_1m = executor.get_historical_data_as_dict(SYMBOL_NAME, timeframe_minutes=1, count=2000)
    if hist_1m:
        print(f"Loaded {len(hist_1m)} candles for Lorentzian & LTF SFP.")
        ml_agent.history = hist_1m.copy()
        for data in hist_1m:
            c = dict_to_candle(data)
            mtf_sfp_agent.ltf_history.append(c)
            mtf_sfp_agent.update_ltf_structure()

    print("Data Loaded. Starting 1M & 15M Loop...")

    last_time_1m = datetime.min
    last_time_15m = datetime.min

    if hist_1m: last_time_1m = hist_1m[-1]['timestamp']
    if hist_15m: last_time_15m = hist_15m[-1]['timestamp']

    try:
        while True:
            # --- 1 Minute Loop ---
            candles_1m = executor.get_candles(SYMBOL_NAME, timeframe_minutes=1, count=1)

            if candles_1m:
                curr_1m = candles_1m[0]

                open_positions = executor.get_open_positions(SYMBOL_NAME)
                pos_str = " | ".join([str(p.ticket) for p in open_positions]) if open_positions else "No Positions"
                print(f"\rPrice: {curr_1m.close:.2f} | {pos_str}", end="")

                if curr_1m.timestamp > last_time_1m:
                    closed_1m_list = executor.get_candles(SYMBOL_NAME, timeframe_minutes=1, count=2)

                    if len(closed_1m_list) >= 2:
                        just_closed_1m = closed_1m_list[0]

                        # 1. Process Lorentzian (Engine handles history update)
                        orders = engine.process_data(just_closed_1m)
                        if orders:
                            for order in orders:
                                print(f"\n⚡ LORENTZIAN SIGNAL: {order.order_type.name}")
                                executor.execute_order(order)

                        # 2. Process SFP
                        sfp_signal = mtf_sfp_agent.on_ltf_candle(just_closed_1m)
                        if sfp_signal:
                            print(f"\n🎯 SFP SIGNAL: {sfp_signal.signal_type.name}")
                            sfp_order = Order(
                                agent_name=sfp_signal.agent_name,
                                symbol=sfp_signal.symbol,
                                order_type=sfp_signal.signal_type,
                                price=sfp_signal.price,
                                volume=sfp_signal.volume,
                                stop_loss=sfp_signal.stop_loss,
                                take_profit=sfp_signal.take_profit,
                                magic_number=sfp_signal.magic_number,
                                comment=sfp_signal.reason,
                                ticket_id=0
                            )
                            executor.execute_order(sfp_order)

                    last_time_1m = curr_1m.timestamp

            # --- 15 Minute Loop ---
            candles_15m = executor.get_candles(SYMBOL_NAME, timeframe_minutes=15, count=1)

            if candles_15m and candles_15m[0].timestamp > last_time_15m:
                curr_15m = candles_15m[0]
                print(f"\n📅 New 15m Bar: {curr_15m.timestamp}")

                closed_15m_list = executor.get_candles(SYMBOL_NAME, timeframe_minutes=15, count=2)
                if len(closed_15m_list) >= 2:
                    just_closed_15m = closed_15m_list[0]
                    mtf_sfp_agent.on_htf_candle(just_closed_15m)

                last_time_15m = curr_15m.timestamp

            sys.stdout.flush()
            time.sleep(1)

    except KeyboardInterrupt:
        executor.shutdown()
        print("\nBot Stopped.")