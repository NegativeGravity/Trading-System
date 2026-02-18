from abc import ABC, abstractmethod
from typing import Optional
from trader.domain.models import Candle, Signal


class TradingAgent(ABC):
    def __init__(self, name: str, magic_number: int):
        self.name = name
        self.magic_number = magic_number
        self.history = []

    @abstractmethod
    def on_market_data(self, candle: Candle) -> Optional[Signal]:
        pass

    def update_history(self, new_closed_candle: dict):
        self.history.append(new_closed_candle)
        if len(self.history) > 5000:
            self.history.pop(0)