import requests
import talib
import numpy as np
from binance.client import Client
import os

from send_email import send_email


# Przykład użycia klasy BinanceTrader
import time


class BinanceTrader:

    def __init__(self):
        self.client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
        self.orders_id = set()
        self.profit = 0.00

    def get_market_data(self, symbol, interval='1d'):
        """Pobiera dane świecowe"""
        return self.client.get_klines(symbol=symbol, interval=interval)

    def calculate_indicators(self, market_data):
        """Liczy RSI i MACD"""
        close_prices = np.array([float(candle[4]) for candle in market_data])
        rsi = talib.RSI(close_prices, timeperiod=14)
        macd, macd_signal, macd_hist = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
        return rsi[-1], macd[-1], macd_signal[-1]


    def check_active_orders(self, symbol):
        """Sprawdza aktywne zlecenia"""
        orders = self.client.get_open_orders(symbol=symbol)
        return orders

    def make_decision(self, symbol):
        """Decyduje, czy kupować/sprzedawać na podstawie wskaźników"""
        data = self.get_market_data(symbol)
        rsi, macd, macd_signal = self.calculate_indicators(data)
        
        if rsi > 70 and macd < macd_signal:
            send_email("SELL","Wskaźniki wskazują na sprzedaż!")
            print("Wskaźniki wskazują na sprzedaż!")
        elif rsi < 30 and macd > macd_signal:
            send_email("BUY","Wskaźniki wskazują na zakup!")
            print("Wskaźniki wskazują na zakup!")
        else:
            print("nic")

    def get_all_symbols(self):
        """Pobiera wszystkie dostępne symbole z Binance"""
        exchange_info = self.client.get_exchange_info()
        symbols = [s['symbol'] for s in exchange_info['symbols']]
        return symbols


trader = BinanceTrader()


# Ustaw symbol dla kryptowaluty, którą chcesz handlować
symbols = trader.get_all_symbols()

# Sprawdzenie aktywnych zleceń
# Pętla decyzyjna co 15 minut dla każdego symbolu
while True:
    for symbol in symbols:
        trader.make_decision(symbol)
        print(f"Podjęto decyzję na podstawie wskaźników dla {symbol}.")
    
    # Odczekaj 15 minut przed ponownym sprawdzeniem
    time.sleep(900)