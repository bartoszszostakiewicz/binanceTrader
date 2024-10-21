from dataclasses import dataclass, field
from typing import List, Dict
from firebase_admin import db



@dataclass
class Order:
    order_id: str  # ID zlecenia
    order_type: str  # Typ zlecenia, np. "buy" lub "sell"
    amount: float  # Ilość kryptowaluty w zleceniu
    price: float  # Cena za jednostkę kryptowaluty
    timestamp: str  # Czas złożenia zlecenia

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "order_type": self.order_type,
            "amount": self.amount,
            "price": self.price,
            "timestamp": self.timestamp,
        }

@dataclass
class CryptoPair:
    pair: str  # Para kryptowalut, np. BTC/USD
    trading_percentage: float  # Procent portfela, który jest handlowany tą parą
    strategy_allocation: Dict[str, float]  # Podział procentowy na strategie
    profit_target: float  # Procentowy zysk, przy którym sprzedajemy
    crypto_amount: float  # Ilość posiadanej kryptowaluty do tradingu
    active_orders: List[Order] = field(default_factory=list)  # Lista aktywnych zleceń
    completed_orders: List[Order] = field(default_factory=list)  # Lista wykonanych zleceń
    profit: float = 0.0 #Zysk na tradingu danej pary

    def __post_init__(self):
        # Sprawdzamy, czy suma alokacji strategii wynosi 100% handlowanej części
        total_strategy_percentage = sum(self.strategy_allocation.values())
        if total_strategy_percentage != 100:
            raise ValueError(f"Suma strategii wynosi {total_strategy_percentage}%, a powinna wynosić 100%.")

    def to_dict(self):
        return {
            "pair": self.pair,
            "trading_percentage": self.trading_percentage,
            "strategy_allocation": self.strategy_allocation,
            "profit_target": self.profit_target,
            "crypto_amount": self.crypto_amount,
            "profit": [self.profit],
            "active_orders": [order.to_dict() for order in self.active_orders],
            "completed_orders": [order.to_dict() for order in self.completed_orders],
        }

@dataclass
class CryptoPairs:
    pairs: List[CryptoPair] = field(default_factory=list)  # Lista par kryptowalutowych
     

    # Metoda do dodania nowej pary
    def add_pair(self, crypto_pair: CryptoPair):
        self.pairs.append(crypto_pair)

    # Zapis danych do Firebase
    def save_to_firebase(self, dbUrl: str):
        ref = db.reference("/CryptoTrading/Pairs", url=dbUrl)

        # Sprawdzamy, czy już istnieją pary
        existing_data = ref.get()
        
        if existing_data is None:
            # Jeśli brak danych, to tworzymy nową instancję
            data_to_send = {
                "pairs": [pair.to_dict() for pair in self.pairs]  # Używamy metody to_dict
            }
            ref.push().set(data_to_send)
            print(f"Dodano nową instancję: {data_to_send}")
            return
        
        # Iterujemy przez istniejące dane
        for item_id, item_data in existing_data.items():
            existing_pairs = item_data.get('pairs', [])
            existing_pair_names = [p.get('pair') for p in existing_pairs]  # Przygotowujemy listę istniejących par
            
            for pair in self.pairs:
                if pair.pair in existing_pair_names:
                    print(f"Para {pair.pair} już istnieje, nie dodawanie.")
                else:
                    # Jeśli para nie istnieje, dodajemy ją do istniejącej instancji
                    existing_pairs.append(pair.to_dict())
                    print(f"Dodano nową parę: {pair.to_dict()} do istniejącej instancji.")

          
            ref.child(item_id).set(item_data)  # Uaktualniamy dane w Firebase
           

    def load_from_firebase(self, dbUrl: str):
        ref = db.reference("/CryptoTrading/Pairs", url=dbUrl)
        data = ref.get()

        if data:
            # Odczytujemy dane i przypisujemy je do obiektu
            for item_key, item_value in data.items():
                print(f"Item Key: {item_key}, Item Value: {item_value}")  # Debugging line
                if isinstance(item_value, dict):  # Sprawdzamy, czy item_value jest słownikiem
                    pairs_data = item_value.get("pairs", [])
                    self.pairs = [CryptoPair(**pair_data) for pair_data in pairs_data]
                else:
                    print(f"Unexpected item_value type: {type(item_value)}")  # Informacja o typie
        else:
            print("Brak danych w bazie.")
