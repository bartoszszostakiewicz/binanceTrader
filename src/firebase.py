from typing import List
import firebase_admin
from firebase_admin import credentials, db
import requests
from binance_api import BinanceTrader
from data_classes import Order, CryptoPairs, CryptoPair, Heartbeat, TradeStrategy
from constants import *
from logger import logger


 


class FirebaseManager:

    def __init__(self, trader: BinanceTrader):
        
        self.trader = trader
        self.dbUrl = 'https://bintrader-ffeeb-default-rtdb.firebaseio.com/'

        try:
            # Ustawienie ścieżki do pliku z poświadczeniami Firebase
            self.cred = credentials.Certificate("C:/GitWorkspace/binanceTrader/bintrader-ffeeb-firebase-adminsdk-6ytwx-e6e7bfbea8.json")
            
            # Inicjalizacja Firebase
            firebase_admin.initialize_app(self.cred)
            logger.debug("Firebase initialized successfully.")

            # Ustawienie referencji do bazy danych
            self.ref = db.reference("/CryptoTrading", url=self.dbUrl)
            logger.debug("Firebase database reference set successfully.")
        
        except FileNotFoundError as e:
            # Logowanie błędu, jeśli plik poświadczeń nie zostanie znaleziony
            logger.error("Firebase credentials file not found.")
            raise ValueError(f"Failed to initialize Firebase: {str(e)}")
        
        
        except Exception as e:
            # Logowanie innych błędów
            logger.exception("An unexpected error occurred during Firebase initialization.")
            raise ValueError(f"Failed to initialize Firebase: {str(e)}")
    
    def login_to_firebase(self, email, password):
        api_key = 'AIzaSyBECJFlN8QCFGhExZ7VxSACo6iSWKp8FvI'
        url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}'
        
        payload = {
            'email': email,
            'password': password,
            'returnSecureToken': True
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            logger.debug('Zalogowano pomyślnie!')
            logger.debug('Token:', data['idToken'])
        else:
            logger.error('Błąd logowania:', response.json())

    def get_power_status(self):
        self.ref = db.reference("/CryptoTrading/__Power__", url=self.dbUrl)
        return self.ref.get()
    
    def set_power_status(self,status: bool):
        self.ref = db.reference("/CryptoTrading/__Power__", url=self.dbUrl)
        self.ref.set(status)
        
    def get_debug_mode(self):
        self.ref = db.reference("/CryptoTrading/Config/Debug", url=self.dbUrl)
        return self.ref.get()
    
    def set_debug_mode(self,status: bool):
        self.ref = db.reference("/CryptoTrading/Config/Debug", url=self.dbUrl)
        self.ref.set(status)
        
    def get_monitor_orders(self):
        self.ref = db.reference("/CryptoTrading/Config/OrdersMonitoring", url=self.dbUrl)
        return self.ref.get()
    
    def set_monitor_orders(self,status: bool):
        self.ref = db.reference("/CryptoTrading/Config/OrdersMonitoring", url=self.dbUrl)
        self.ref.set(status)
    
    def update_profit(self, profit: float):
        ref_profit = db.reference("/CryptoTrading/Wallet/Profit", url=self.dbUrl)
        ref_profit.set(profit)

    def update_value(self, values: tuple):
        stablecoin_value, crypto_value = values
        total_value = stablecoin_value + crypto_value

        ref_profit = db.reference("/CryptoTrading/Wallet/StablecoinsValue", url=self.dbUrl)
        ref_profit.set(stablecoin_value)
        ref_profit = db.reference("/CryptoTrading/Wallet/CryptoValue", url=self.dbUrl)
        ref_profit.set(crypto_value)
        ref_profit = db.reference("/CryptoTrading/Wallet/TotalValue", url=self.dbUrl)
        ref_profit.set(total_value)

    def get_crypto_value(self):
        """
        Pobiera wartość kryptowalut z bazy danych Firebase.
        
        :return: Wartość kryptowalut przechowywana w Firebase
        """
        ref_crypto_value = db.reference("/CryptoTrading/CryptoValue", url=self.dbUrl)
        crypto_value = ref_crypto_value.get()
        return crypto_value
    
    def get_pairs(self):
        self.ref = db.reference("/CryptoTrading/Pairs", url=self.dbUrl)
        return self.ref.get()

    def update_value_for_pair(self, pair_name: str, value: float):
        """Updates the value of a cryptocurrency pair in Firebase."""
        ref_value = self.ref.child(f"{pair_name}/value")  # Removed extra "Pairs"
        ref_value.set(value)

    def update_min_notional(self, pair_name: str, min_notional: float):
        """Updates the minimum notional of a cryptocurrency pair in Firebase."""
        ref_min_notional = self.ref.child(f"{pair_name}/min_notional")  # Removed extra "Pairs"
        ref_min_notional.set(min_notional)

    def update_active_orders(self, pair_name: str, active_orders: list):
        """Updates the active orders of a cryptocurrency pair in Firebase."""
        ref_active_orders = self.ref.child(f"{pair_name}/active_orders")  # Removed extra "Pairs"
        ref_active_orders.set(active_orders)

    def update_completed_orders(self, pair_name: str, completed_orders: list):
        """Updates the completed orders of a cryptocurrency pair in Firebase."""
        ref_completed_orders = self.ref.child(f"{pair_name}/completed_orders")  # Removed extra "Pairs"
        ref_completed_orders.set(completed_orders)

    def update_crypto_amount(self, pair_name: str, crypto_amount_locked: float, crypto_amount_free: float):
        """Updates the free and locked cryptocurrency amounts of a pair in Firebase."""
        ref_crypto_amount_locked = self.ref.child(f"{pair_name}/crypto_amount_locked")  # Removed extra "Pairs"
        ref_crypto_amount_free = self.ref.child(f"{pair_name}/crypto_amount_free")  # Removed extra "Pairs"
        ref_crypto_amount_locked.set(crypto_amount_locked)
        ref_crypto_amount_free.set(crypto_amount_free)

    def update_profit_for_pair(self, pair_name: str, profit: float):
        """Updates the profit of a cryptocurrency pair in Firebase."""
        ref_profit = self.ref.child(f"{pair_name}/profit")  # Removed extra "Pairs"
        ref_profit.set(profit)

    

    def get_value(self, pair: str, amount: float) -> float:
        # Example calculation of value (price could be fetched from an API or cache)
        price = self.trader.get_price(pair)  # Assuming you have access to a price method
        return float(amount) * price

    def fetch_pairs(self) -> CryptoPairs: 
        data = self.get_pairs()
        wallet = self.trader.get_wallet_balances()
        profit = 0
        crypto_pairs = CryptoPairs()  # Create a CryptoPairs object

        # Iterate through the data fetched from Firebase
        for pair_name, pair_data in data.items():
                    
            # Update data fetched from Binance to Firebase
            if pair_name[:-4] in wallet:
                balance = wallet[pair_name[:-4]]
                pair_data['crypto_amount_free'] = balance['free']
                pair_data['crypto_amount_locked'] = balance['locked']

                # Calculate the value of the asset (free and locked cryptocurrency)
                free_value = self.get_value(pair_name, pair_data['crypto_amount_free'])
                locked_value = self.get_value(pair_name, pair_data['crypto_amount_locked'])
                total_value = free_value + locked_value

                # Minimum trading value
                min_notional = self.trader.get_min_notional(pair_name)

                # Update Firebase data
                self.update_crypto_amount(pair_name, pair_data['crypto_amount_locked'], pair_data['crypto_amount_free'])
                self.update_min_notional(pair_name, min_notional)
                self.update_value_for_pair(pair_name, total_value)
                


                # Create a CryptoPair object
                crypto_pair = CryptoPair(
                    pair=pair_name,
                    trading_percentage=pair_data.get('trading_percentage', 0),
                    strategy_allocation=pair_data.get('strategy_allocation', {}),
                    profit_target=pair_data.get('profit_target', 0),
                    crypto_amount_free=pair_data['crypto_amount_free'],
                    crypto_amount_locked=pair_data['crypto_amount_locked'],
                    active_orders=[],
                    completed_orders=[],
                    min_notional=min_notional,
                    profit=0,
                    value=total_value,
                    tick_size=self.trader.get_tick_size(symbol=pair_name),
                    step_size=self.trader.get_step_size(symbol=pair_name)
                )

                # Add CryptoPair to the list
                crypto_pairs.pairs.append(crypto_pair)
        
        for strategy in self.get_strategies():
            crypto_pairs.add_strategy(strategy)
        

        # Update total profit and overall value in Firebase
        self.update_profit(profit=0)
        self.update_value(self.trader.get_value_of_stable_coins_and_crypto())

        # Return the list of cryptocurrency pairs
        return crypto_pairs

    def send_heartbeat(self ,status="OK", version="1.0.0", custom_message="All systems operational"):
        heartbeat = Heartbeat.create_heartbeat(status=status, version=version, custom_message=custom_message)
        
        # Konwersja obiektu Heartbeat do słownika
        heartbeat_data = {
            "timestamp": heartbeat.timestamp.isoformat().replace("T"," | "),
            "status": heartbeat.status,
            "version": heartbeat.version,
            "cpu_load": heartbeat.cpu_load,
            "memory_usage": heartbeat.memory_usage,
            "custom_message": heartbeat.custom_message
        }

        # Wysyłanie danych do Firebase, nadpisując istniejący wpis
        self.ref = db.reference("/CryptoTrading/Heartbeat", url=self.dbUrl)
        self.ref.set(heartbeat_data)  # Użycie set, aby nadpisać dane

    def get_strategies(self) -> List[TradeStrategy]:
        """
        Fetches trading strategies from the Firebase database and returns them as a list of TradeStrategy objects.

        Returns:
            List[TradeStrategy]: A list of strategies fetched from the database.
        """
        self.ref = db.reference("/CryptoTrading", url=self.dbUrl)
        strategies_ref = self.ref.child("Strategies")
        strategies_data = strategies_ref.get()

        strategies = []
        if strategies_data:
            for strategy_name, strategy_info in strategies_data.items():
                if isinstance(strategy_info, dict):
                    buy_increase_indicator = strategy_info.get("buy_increase_indicator", 0.0)
                    profit_target = strategy_info.get("profit_target", 0.0)
                    strategy = TradeStrategy(name=strategy_name, 
                                             buy_increase_indicator=buy_increase_indicator, 
                                             profit_target=profit_target)
                    strategies.append(strategy)
                else:
                    logger.error(f"Unexpected data type for strategy: {type(strategy_info)}")
        else:
            logger.error("No strategies found in the database.")

        return strategies
    
