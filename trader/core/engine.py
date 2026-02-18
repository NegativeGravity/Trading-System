from typing import List
import uuid
from agents.base import TradingAgent
from domain.models import Candle, Order


class TradingEngine:
    def __init__(self):
        self._agents: List[TradingAgent] = []

    def register_agent(self, agent: TradingAgent):
        self._agents.append(agent)
        print(f"[System] Agent Registered: {agent.name}")

    def process_data(self, candle: Candle) -> List[Order]:  # خروجی شد لیست Order
        orders = []

        for agent in self._agents:
            signal = agent.on_market_data(candle)

            if signal:

                new_order = Order(
                    ticket_id=str(uuid.uuid4())[:8],
                    agent_name=signal.agent_name,
                    symbol=signal.symbol,
                    order_type=signal.signal_type,
                    price=signal.price,
                    volume=signal.volume,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    magic_number=signal.magic_number,
                    comment=f"Reason: {signal.reason}"
                )

                print(f"✅ Signal {signal.agent_name} Converted to Order: {new_order.ticket_id}")
                orders.append(new_order)

        return orders