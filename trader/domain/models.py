from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Candle:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class Signal:
    agent_name: str
    symbol: str
    signal_type: SignalType
    price: float
    reason: str
    magic_number: int
    volume: float
    stop_loss: float
    take_profit: float

@dataclass
class Order:
    agent_name: str
    symbol: str
    order_type: SignalType
    price: float
    volume: float
    stop_loss: float
    take_profit: float
    magic_number: int
    comment: str
    ticket_id: int = 0  # Default 0 for new orders

@dataclass
class Position:
    ticket: int
    symbol: str
    type: str
    volume: float
    open_price: float
    current_price: float
    sl: float
    tp: float
    profit: float
    time: datetime