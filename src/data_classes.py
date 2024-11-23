from dataclasses import dataclass, field
import time
from typing import List, Dict
from firebase_admin import db
from datetime import datetime
import psutil
from logger import logger
from constants import *


@dataclass
class Order:
    symbol: str # Symbol zlecenia
    order_id: str  # ID zlecenia
    order_type: str  # Typ zlecenia, np. "buy" lub "sell"
    amount: float  # Ilość kryptowaluty w zleceniu
    sell_price: float  # Cena za jednostkę kryptowaluty
    buy_price: float
    timestamp: str  # Czas złożenia zlecenia
    strategy: str # Strategia z jaka zostalo zlozone zlecenie
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
    pair: str  # Para kryptowalut, np. BTC/USD
    value: float #wartosc crypto w USD
    trading_percentage: float  # Procent portfela, który jest handlowany tą parą
    strategy_allocation: Dict[str, float]  # Podział procentowy na strategie
    profit_target: float  # Procentowy zysk, przy którym sprzedajemy
    crypto_amount_free: float  # Ilość posiadanej kryptowaluty do tradingu
    crypto_amount_locked :float #Ilość posiadanej kryptowaluty która jest aktulanie zablokowana w transakcjach
    orders: List[Order] = field(default_factory=list)  # Lista aktywnych zleceń
    profit: float = 0.0 #Zysk na tradingu danej pary
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
            "trading_percentage": self.trading_percentage,
            "strategy_allocation": self.strategy_allocation,
            "profit_target": self.profit_target,
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
        Ustawia nowy status dla zlecenia o podanym order_id w obiekcie CryptoPair.

        Parameters:
            order_id (str): ID zlecenia, którego status ma zostać zmieniony.
            status (str): Nowy status, który zostanie ustawiony.
        """
        for order in self.orders:
            if order.order_id == order_id:
                order.status = status
                order.timestamp = int(time.time() * 1000)
                logger.debug(f"Order with ID {order_id} status changed to {status}.")
                return  order
        logger.warning(f"No order found with ID {order_id}.")



@dataclass
class TradeStrategy:
    name: str
    buy_increase_indicator: float
    profit_target: float

    def save_to_firebase(self, dbUrl: str):
        ref = db.reference("/CryptoTrading/Strategies", url=dbUrl)

        # Prepare the data to send
        data_to_send = {
            "buy_increase_indicator": self.buy_increase_indicator,
            "profit_target": self.profit_target
        }

        # Check if any strategies already exist
        existing_data = ref.get()

        if existing_data is None:
            # If there is no existing data, create a new entry
            ref.child(self.name).set(data_to_send)
            print(f"Added new strategy: {self.name} with data: {data_to_send}")
        else:
            # Iterate through existing data
            existing_strategy_names = existing_data.keys()

            if self.name in existing_strategy_names:
                print(f"Strategy {self.name} already exists, not adding.")
            else:
                # If the strategy does not exist, add it to the existing data
                ref.child(self.name).set(data_to_send)
                print(f"Added new strategy: {self.name} with data: {data_to_send} to existing data.")

@dataclass
class Heartbeat:
    timestamp: datetime
    status: str
    version: str
    cpu_load: list  
    memory_usage: float
    custom_message: str = ""

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
    def create_heartbeat(status: str, version: str, custom_message: str):
        system_metrics = Heartbeat.collect_system_metrics()  # Używamy bezpośrednio Heartbeat
        return Heartbeat(  # Tworzymy instancję Heartbeat
            timestamp=datetime.now(),
            status=status,
            version=version,
            cpu_load=system_metrics["cpu_per_core"],
            memory_usage=system_metrics["memory_usage"],
            custom_message=custom_message
        )

@dataclass
class CryptoPairs:
    pairs: List[CryptoPair] = field(default_factory=list)  # Lista par kryptowalutowych
    strategies: Dict[str, TradeStrategy] = field(default_factory=dict)

    def add_strategy(self, strategy: TradeStrategy):
        self.strategies[strategy.name] = strategy

    def add_pair(self, crypto_pair: CryptoPair):
        self.pairs.append(crypto_pair)


    def save_to_firebase(self, dbUrl: str):
        ref = db.reference("/CryptoTrading/Pairs", url=dbUrl)

        for pair in self.pairs:
            pair_key = pair.pair  # Use the pair name as the key
            data_to_send = {
                CRYPTO_AMOUNT_FREE: pair.crypto_amount_free,
                CRYPTO_AMOUNT_LOCKED: pair.crypto_amount_locked,
                "min_notional": pair.min_notional,
                "profit": pair.profit,
                "profit_target": pair.profit_target,
                "trading_percentage": pair.trading_percentage,
                "value": pair.value,
                "strategy_allocation": {
                    "poor_orphan": pair.strategy_allocation.get("poor_orphan", 0.4),  # Change names as needed
                    "crazy_girl": pair.strategy_allocation.get("crazy_girl", 0.2),
                    "sensible_guy": pair.strategy_allocation.get("sensible_guy", 0.4)
                }
            }

            # Set the data under the pair name in Firebase
            ref.child(pair_key).set(data_to_send)
            print(f"Added pair data for {pair_key}: {data_to_send}")
