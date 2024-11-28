from dataclasses import dataclass, field
import time
from typing import List, Dict
from datetime import datetime
import psutil
from logger import logger
from globals import *

@dataclass
class Order:
    symbol: str
    order_id: str
    order_type: str
    amount: float
    sell_price: float
    buy_price: float
    timestamp: str
    strategy: str
    status: str

    def to_dict(self):
        return {
            SYMBOL: self.symbol,
            "order_id": self.order_id,
            "order_type": self.order_type,
            "amount": self.amount,
            "sell_price": self.sell_price,
            "buy_price": self.buy_price,
            "timestamp": self.timestamp,
            "strategy": self.strategy,
            STATUS: self.status,
        }

@dataclass
class CryptoPair:
    pair: str
    value: float
    crypto_amount_free: float
    crypto_amount_locked :float
    orders: List[Order] = field(default_factory=list)
    profit: float = 0.0
    min_notional: float = 0.0
    tick_size: float = 0.0
    step_size: float = 0.0
    current_state: Dict[str, TradeState] = field(default_factory=lambda: {
        CRAZY_GIRL   : TradeState.MONITORING,
        SENSIBLE_GUY : TradeState.MONITORING,
        POOR_ORPHAN  : TradeState.MONITORING,
    })

    def to_dict(self):
        return {
            "pair": self.pair,
            CRYPTO_AMOUNT_FREE: self.crypto_amount_free,
            CRYPTO_AMOUNT_LOCKED: self.crypto_amount_locked,
            "profit": self.profit,
            "orders": [order.to_dict() for order in self.orders],
        }

    def add_order(self, order: Order):
        self.orders.append(order)

        if len(self.orders) > MAX_ORDERS_HISTORY_IN_CRYPTO_PAIRS:
            self.orders.pop(0)

        return order

    def set_status(self, order_id: str, status: str):
        """
        Sets a new status for the order with the given order_id in the CryptoPair object.

        Parameters:
            order_id (str): ID of the order whose status is to be changed.
            status (str): The new status that will be set.
        """
        for order in self.orders:
            if order.order_id == order_id:
                order.status = status
                order.timestamp = int(time.time() * 1000)
                logger.debug(f"Order with ID {order_id} status changed to {status}.")
                return  order
        logger.warning(f"No order found with ID {order_id}.")

@dataclass
class Heartbeat:
    timestamp: datetime
    status: str
    version: str
    cpu_load: list
    memory_usage: float

    @staticmethod
    def collect_system_metrics():
        # Pobranie aktualnych danych systemowych
        cpu_per_core = psutil.cpu_percent(percpu=True, interval=1)  # Zużycie CPU na każdy rdzeń
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.used / (1024 ** 2)  # Zużycie pamięci w MB

        return {
            "cpu_per_core": cpu_per_core,
            "memory_usage": memory_usage
        }

    @staticmethod
    def create_heartbeat(status: str, version: str):
        system_metrics = Heartbeat.collect_system_metrics()  # Używamy bezpośrednio Heartbeat
        return Heartbeat(  # Tworzymy instancję Heartbeat
            timestamp=datetime.now(),
            status=status,
            version=version,
            cpu_load=system_metrics["cpu_per_core"],
            memory_usage=system_metrics["memory_usage"],
        )

@dataclass
class CryptoPairs:
    pairs: List[CryptoPair] = field(default_factory=list)