import time
from binance.client import Client
import json


class BinanceTrader:

    def __init__(self):
        self.client = Client(0, 0)
        self.orders_id = set()
        self.profit = 0.00
        self.buy_orders_set = {}  # Utrzymuj status zleceń kupna

    def get_market_data(self, symbol, interval='1d'):
        """Pobiera dane świecowe"""
        return self.client.get_klines(symbol=symbol, interval=interval)

    def calculate_portfolio_value(self):
        """Oblicza całkowitą wartość portfela w USDT"""
        total_value = 0
        for symbol, balance in portfolio.items():
            if symbol != "USDT":  # Dla każdej kryptowaluty
                current_price = float(self.get_market_data(symbol + 'USDT', '1d')[-1][4])
                total_value += balance['free'] * current_price
        total_value += portfolio['USDT']['free']  # Dodaj USDT do całkowitej wartości
        return total_value

    def sell_all_assets(self):
        """Sprzedaj wszystkie kryptowaluty i przekształć w USDT"""
        for symbol, balance in portfolio.items():
            if symbol != "USDT":
                current_price = float(self.get_market_data(symbol + 'USDT', '1d')[-1][4])
                cypto_amount = balance['free']
                sell_value = balance['free'] * current_price * 0.999  # Uwzględnienie opłaty 0.1%
                portfolio['USDT']['free'] += sell_value  # Dodaj USDT po sprzedaży
                portfolio[symbol]['free'] = 0  # Wyzeruj ilość kryptowaluty
                if cypto_amount > 0.00:
                    print(f"Sprzedano {cypto_amount:20f} {symbol} za {sell_value:.20f} USDT.")
                    # Zapisz, ile kupić z powrotem
                    self.buy_orders_set[symbol] = (current_price * 0.996, cypto_amount)


    def execute_buy_orders(self):
        """Wykonaj zlecenia kupna, jeśli warunki są spełnione"""
        for symbol, (buy_price, quantity) in list(self.buy_orders_set.items()):
            
            current_price = float(self.get_market_data(symbol + 'USDT', '1d')[-1][4])

            print(f"Symbol: {symbol}, Obecna cena: {current_price:.20f}, Cena kupna: {buy_price:.20f}")

            if current_price <= buy_price:  # Jeśli cena spadła do limitu
                total_cost = buy_price * quantity  # Całkowity koszt zakupu
                portfolio['USDT']['free'] -= total_cost  # Odejmij z USDT
                portfolio[symbol]['free'] += quantity  # Dodaj jednostki kryptowaluty
                print(f"Kupiono {quantity} {symbol} po cenie {current_price:.20f}.")
                del self.buy_orders_set[symbol]  # Usuń zlecenie kupna


    def simulate_trading(self):
        """Symulacja ciągłego handlu"""
        while True:
            total_value = self.calculate_portfolio_value()
            print(f"Całkowita wartość portfela: {total_value:.20f} USDT")

            if total_value >= 500:
                self.sell_all_assets()
            else:
                print("Nie osiągnięto progu sprzedaży. Czekam...")

            self.execute_buy_orders()  # Sprawdź, czy należy wykonać zlecenia kupna

            with open('demo_data/portfolio.json', 'w') as json_file:
                json.dump(portfolio, json_file, indent=4)
                json.dump(self.buy_orders_set, json_file, indent=4)

            # Odczekaj 10 sekund przed kolejnym sprawdzeniem
            time.sleep(10)


# Przykładowe portfolio
portfolio = {
    "BTC": {
        "free": 0.00521794,
        "locked": 0.00000000
    },
    "LTC": {
        "free": 0.77942773,
        "locked": 0.00000000
    },
    "ETH": {
        "free": 0.02582904,
        "locked": 0.00000000
    },
    "BNB": {
        "free": 0.00012812,
        "locked": 0.00000000
    },
    "USDT": {
        "free": 0.00000000,
        "locked": 0.00000000
    },
    "XLM": {
        "free": 118.69344324,
        "locked": 0.00000000
    },
    "SHIB": {
        "free": 4713938.83,
        "locked": 0.00
    },
    "WBETH": {
        "free": 0.03132756,
        "locked": 0.00000000
    }
}

# Inicjalizacja klasy i rozpoczęcie symulacji
trader = BinanceTrader()
trader.simulate_trading()
