import firebase_admin
from firebase_admin import credentials, db
import requests
from binance_api import BinanceTrader
from CryptoPair import Order,CryptoPairs,CryptoPair
from Heartbeat import Heartbeat

class FirebaseManager:

    def __init__(self, trader: BinanceTrader):
        self.trader = trader
        self.dbUrl = 'https://bintrader-ffeeb-default-rtdb.firebaseio.com/'
        self.cred = credentials.Certificate("../../bintrader-ffeeb-firebase-adminsdk-6ytwx-e6e7bfbea8.json")
        firebase_admin.initialize_app(self.cred)
        self.ref = db.reference("/CryptoTrading", url=self.dbUrl)
    
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
            print('Zalogowano pomyślnie!')
            print('Token:', data['idToken'])
        else:
            print('Błąd logowania:', response.json())

    def get_power_status(self):
        self.ref = db.reference("/CryptoTrading/Power", url=self.dbUrl)
        return self.ref.get()
    
    def set_power_status(self,status: bool):
        self.ref = db.reference("/CryptoTrading/Power", url=self.dbUrl)
        self.ref.set(status)
    
    def get_pairs(self):
        self.ref = db.reference("/CryptoTrading/Pairs", url=self.dbUrl)
        return self.ref.get()

    def update_active_orders(self, user_id, pair_index, active_orders):
        ref_active_orders = self.ref.child(f"{user_id}/pairs/{pair_index}/active_orders")
        ref_active_orders.set(active_orders)

    def update_completed_orders(self, user_id, pair_index, completed_orders):
        ref_completed_orders = self.ref.child(f"{user_id}/pairs/{pair_index}/completed_orders")
        ref_completed_orders.set(completed_orders)

    def update_crypto_amount(self, user_id, pair_index, crypto_amount_locked: float, crypto_amount_free: float):
        ref_crypto_amount_locked = self.ref.child(f"{user_id}/pairs/{pair_index}/crypto_amount_locked")
        ref_crypto_amount_free = self.ref.child(f"{user_id}/pairs/{pair_index}/crypto_amount_free")
        ref_crypto_amount_locked.set(crypto_amount_locked)
        ref_crypto_amount_free.set(crypto_amount_free)

    def update_profit_for_pair(self, user_id, pair_index, profit: float):
        ref_profit = self.ref.child(f"{user_id}/pairs/{pair_index}/profit")
        ref_profit.set(profit)

    def update_profit(self, profit: float):
        ref_profit = db.reference("/CryptoTrading/Profit", url=self.dbUrl)
        ref_profit.set(profit)

    def update_value(self, values: tuple):
        stablecoin_value, crypto_value = values
        total_value = stablecoin_value + crypto_value

        ref_profit = db.reference("/CryptoTrading/StablecoinsValue", url=self.dbUrl)
        ref_profit.set(stablecoin_value)
        ref_profit = db.reference("/CryptoTrading/CryptoValue", url=self.dbUrl)
        ref_profit.set(crypto_value)
        ref_profit = db.reference("/CryptoTrading/TotalValue", url=self.dbUrl)
        ref_profit.set(total_value)

    def get_crypto_value(self):
        """
        Pobiera wartość kryptowalut z bazy danych Firebase.
        
        :return: Wartość kryptowalut przechowywana w Firebase
        """
        ref_crypto_value = db.reference("/CryptoTrading/CryptoValue", url=self.dbUrl)
        crypto_value = ref_crypto_value.get()
        return crypto_value

    def handle_orders(self, orders, existing_orders, order_type):
        updated_orders = existing_orders.copy()
        
        for order in orders:

            order_exists = False
            for existing_order in existing_orders:
                if existing_order['order_id'] == order['orderId']:
                    order_exists = True
                    break

            if not order_exists:
                
                if float(order['price']) == 0.0:
                    order['price'] = float(order['cummulativeQuoteQty']) / float(order['origQty'])

                new_order = Order(
                    symbol=order['symbol'],
                    order_id=order['orderId'],
                    order_type=order['side'],
                    amount=order['origQty'],
                    price=order['price'],
                    timestamp=order['time'],
                    strategy="",
                )
                
                updated_orders.append(new_order.to_dict())
                print(f"Zamówienie {new_order.order_id} dodane do {order_type} zamówień.")

        return updated_orders

    def calculate_profit(self, completed_orders):
        buy_orders = []
        sell_orders = []
        total_profit = 0.0
        #zle oblicza dla shiby z powodu kupna na rynku zamiast zlecenia limit
        # Oddziel zamówienia kupna i sprzedaży
        for order in completed_orders:
            if order['status'] == 'FILLED':  # Sprawdzamy tylko zrealizowane zlecenia
                # Jeżeli cena wynosi 0, obliczamy ją jako iloraz cummulativeQuoteQty/origQty
                if float(order['price']) == 0.0 and float(order['origQty']) > 0.0:
                    order['price'] = float(order['cummulativeQuoteQty']) / float(order['origQty'])

                if order['side'].lower() == 'buy':
                    buy_orders.append(order)
                elif order['side'].lower() == 'sell':
                    sell_orders.append(order)


        # Iterujemy po zleceniach sprzedaży i szukamy odpowiedniego zakupu
        for sell_order in sell_orders:
            sell_price = float(sell_order['price'])
            sell_amount = float(sell_order['origQty'])

            # Szukamy odpowiadającego zlecenia kupna
            for buy_order in buy_orders:
                buy_price = float(buy_order['price'])
                buy_amount = float(buy_order['origQty'])

                # Sprawdzamy, ile można dopasować sprzedanych jednostek do kupionych
                if buy_amount > 0:
                    matched_amount = min(sell_amount, buy_amount)

                    # Obliczamy zysk tylko dla dopasowanej ilości jednostek
                    profit = (sell_price - buy_price) * matched_amount
                    total_profit += profit

                    # Aktualizujemy ilości
                    sell_amount -= matched_amount
                    buy_order['origQty'] = buy_amount - matched_amount  # Zmniejszamy ilość w kupnie

                    if sell_amount == 0:
                        break  # Jeśli sprzedaliśmy całość, przechodzimy do następnego zamówienia sprzedaży

        return total_profit

    def update_value_for_pair(self, user_id: str, pair_index: int, value: float):
        """Aktualizuje wartość pary kryptowalut w Firebase."""
        ref_profit = self.ref.child(f"{user_id}/pairs/{pair_index}/value")
        ref_profit.set(value)
        # print(f"Zaktualizowano wartość dla pary o indeksie {pair_index} na {value}")

    def get_value(self, symbol: str, amount: float) -> float:
        """Oblicza wartość danego symbolu w oparciu o jego ilość i aktualną cenę."""
        try:
            # Pobieramy aktualną cenę za pomocą funkcji get_price, która zwraca float
            price = self.trader.get_price(symbol=symbol)

            # Konwersja ilości na float, jeśli jest stringiem (zawsze dbamy o to, że amount jest floatem)
            amount = float(amount)

            # Obliczamy wartość: cena * ilość
            value = price * amount
            return value

        except ValueError as ve:
            print(f"Błąd wartości: {ve}")  # Obsługa błędów związanych z konwersją
            return 0.0
        except Exception as e:
            print(f"Błąd: Nie udało się obliczyć wartości dla {symbol}. Szczegóły: {e}")
            return 0.0
 
    def fetch_pairs(self) -> CryptoPairs:
        data = self.get_pairs()
        wallet = self.trader.get_wallet_balances()

        profit = 0
        crypto_pairs = CryptoPairs()  # Tworzymy obiekt CryptoPairs

        # Iteracja przez dane
        for user_id, user_data in data.items():
            for pair_index, pair_data in enumerate(user_data['pairs']):
                pair = pair_data['pair']

                # Aktualizacja ilości
                for currency, balance in wallet.items():
                    if pair.split("/")[0] == currency:
                        pair_data['crypto_amount_free'] = balance['free']
                        pair_data['crypto_amount_locked'] = balance['locked']

                        orders = self.trader.get_order(symbol=pair.replace("/", ""), include_historical=True)

                        active_orders = pair_data.get('active_orders', [])
                        completed_orders = pair_data.get('completed_orders', [])

                        # Obsługa aktywnych i zakończonych zamówień
                        active_orders = self.handle_orders(orders['active_orders'], active_orders, "aktywnych")
                        completed_orders = self.handle_orders(orders['historical_orders'], completed_orders, "historycznych")

                        # Oblicz profit
                        profit_pair = self.calculate_profit(orders['historical_orders'])

                        # Obliczenie wartości waloru (wolnej i zablokowanej kryptowaluty)
                        free_value = self.get_value(pair.split("/")[0] + pair.split("/")[1], pair_data['crypto_amount_free'])
                        locked_value = self.get_value(pair.split("/")[0] + pair.split("/")[1], pair_data['crypto_amount_locked'])
                        total_value = free_value + locked_value

                        # Aktualizacja bazy danych
                        self.update_active_orders(user_id, pair_index, active_orders)
                        self.update_completed_orders(user_id, pair_index, completed_orders)
                        self.update_crypto_amount(user_id, pair_index, pair_data['crypto_amount_locked'], pair_data['crypto_amount_free'])
                        self.update_profit_for_pair(user_id, pair_index, profit_pair)
                        
                        # Aktualizacja wartości waloru w Firebase
                        self.update_value_for_pair(user_id, pair_index, total_value)

                        # Dodajemy profit do całkowitego zysku
                        profit = profit + profit_pair
                       
                        # Tworzymy obiekt CryptoPair
                        crypto_pair = CryptoPair(
                            pair=pair,
                            trading_percentage=pair_data.get('trading_percentage', 0),
                            strategy_allocation=pair_data.get('strategy_allocation', {}),
                            profit_target=pair_data.get('profit_target', 0),
                            crypto_amount_free=pair_data['crypto_amount_free'],
                            crypto_amount_locked=pair_data['crypto_amount_locked'],
                            active_orders=[Order(
                                symbol=pair.replace("/", ""),  # Dodajemy symbol do każdego zlecenia
                                order_id=order['order_id'],
                                order_type=order['order_type'],
                                amount=order['amount'],
                                price=order['price'],
                                timestamp=order['timestamp'],
                                strategy=""
                            ) for order in active_orders],
                            completed_orders=[Order(
                                symbol=pair.replace("/", ""),  # Dodajemy symbol do każdego zlecenia
                                order_id=order['order_id'],
                                order_type=order['order_type'],
                                amount=order['amount'],
                                price=order['price'],
                                timestamp=order['timestamp'],
                                strategy=""
                            ) for order in completed_orders],
                            profit=profit_pair,
                            value=total_value  # Dodajemy wartość do CryptoPair
                        )

                        # Dodajemy CryptoPair do listy
                        crypto_pairs.pairs.append(crypto_pair)

        # Aktualizacja całkowitego profitu w Firebase
        self.update_profit(profit=profit)
        self.update_value(self.trader.get_value_of_stable_coins_and_crypto())
        # Zwracamy listę par kryptowalut
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

# # # Przykład użycia
# if __name__ == "__main__":
#     trader = BinanceTrader()  # Zainicjalizuj swojego tradera
#     fb = FirebaseManager(trader=trader)
#     fb.fetch_pairs()

#     fb.set_power_status(True)