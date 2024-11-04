from dataclasses import dataclass, field
from typing import List, Dict
from firebase_admin import db
from datetime import datetime
import psutil

from constants import TradeState


@dataclass
class Order:
    symbol: str # Symbol zlecenia
    order_id: str  # ID zlecenia
    order_type: str  # Typ zlecenia, np. "buy" lub "sell"
    amount: float  # Ilość kryptowaluty w zleceniu
    price: float  # Cena za jednostkę kryptowaluty
    timestamp: str  # Czas złożenia zlecenia
    strategy: str # Strategia z jaka zostalo zlozone zlecenie

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "order_id": self.order_id,
            "order_type": self.order_type,
            "amount": self.amount,
            "price": self.price,
            "timestamp": self.timestamp,
            "strategy": self.strategy,
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
    active_orders: List[Order] = field(default_factory=list)  # Lista aktywnych zleceń
    completed_orders: List[Order] = field(default_factory=list)  # Lista wykonanych zleceń
    profit: float = 0.0 #Zysk na tradingu danej pary
    min_notional: float = 0.0
    ############################################################################
    sell_order_id: str  = ""    #order id dla ktorego musimy zrobic odkup
    buy_price: float = 0.0 #cena odkupu
    sell_price: float = 0.0 #cena sprzedaży
    buy_quantity: float = 0.0 #ilosc odkupu
    ############################################################################
    current_state: Dict[str, TradeState] = field(default_factory=lambda: {
        'crazy_girl': TradeState.MONITORING,
        'sensible_guy': TradeState.MONITORING,
        'poor_orphan': TradeState.MONITORING,
    })

    # def __post_init__(self):
    #     # Sprawdzamy, czy suma alokacji strategii wynosi 100% handlowanej części
    #     total_strategy_percentage = sum(self.strategy_allocation.values())
    #     if total_strategy_percentage != 1:
    #         raise ValueError(f"Suma strategii wynosi {total_strategy_percentage}%, a powinna wynosić 100%.")

    def to_dict(self):
        return {
            "pair": self.pair,
            "trading_percentage": self.trading_percentage,
            "strategy_allocation": self.strategy_allocation,
            "profit_target": self.profit_target,
            "crypto_amount_free": self.crypto_amount_free,
            "crypto_amount_locked": self.crypto_amount_locked,
            "profit": self.profit,
            "active_orders": [order.to_dict() for order in self.active_orders],
            "completed_orders": [order.to_dict() for order in self.completed_orders],
        }

    def add_order(self, order: Order):
        self.active_orders.append(order)

    def remove_order_by_id(self, order_id: str):
        order_to_remove = next((order for order in self.active_orders if order.order_id == order_id), None)
        self.active_orders.remove(order_to_remove)
 
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
                "crypto_amount_free": pair.crypto_amount_free,
                "crypto_amount_locked": pair.crypto_amount_locked,
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
       
