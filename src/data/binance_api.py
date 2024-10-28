import asyncio
import os
from binance.client import Client
from datetime import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import numpy as np
from CryptoPair import CryptoPair
import time
from colorama import Fore, Style, init


class BinanceTrader:

    def __init__(self) -> None:
        # Initialize the Binance client using API keys from environment variables
        self.client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
        self.orders_id = set()
        init(autoreset=True)


    def get_price(self, symbol: str) -> dict:
        """Pobiera aktualną cenę dla danego symbolu z Binance API."""
        try:
            price_data = self.client.get_symbol_ticker(symbol=symbol)
            return price_data  # Zwracamy wynik jako słownik z ceną
        except Exception as e:
            print(f"Błąd podczas pobierania ceny dla symbolu {symbol}: {e}")
            return {}

    async def limit_order(self, trading_pair, quantity, price, side=Client.SIDE_SELL):
        """
        Składa zlecenie limit.
        """
        try:
            order = self.client.create_order(
                symbol=trading_pair,
                side=side,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=str(price)
            )
            print(f"{side.capitalize()} order placed at {price}!")
            return order
        except Exception as e:
            print(f"Error placing {side} order: {e}")
            return None

    def get_order_status(self, trading_pair, order_id):
        """
        Sprawdza status zlecenia.
        """
        try:
            order = self.client.get_order(symbol=trading_pair, orderId=order_id)
            return order['status']
        except Exception as e:
            print(f"Error checking order status: {e}")
            return None

    async def get_open_orders(self, trading_pair):
        """
        Pobiera otwarte zlecenia dla danej pary kryptowalut (trading_pair).
        
        Args:
            trading_pair (str): Symbol pary kryptowalut, np. 'BTCUSDT'.
        
        Returns:
            list: Lista otwartych zleceń dla danej pary.
        """
        try:
            # Pobierz listę otwartych zleceń dla podanego symbolu
            open_orders = self.client.get_open_orders(symbol=trading_pair)
            return open_orders
        except Exception as e:
            print(f"Błąd przy pobieraniu otwartych zleceń dla {trading_pair}: {e}")
            return []

    async def monitor_sell_and_buy_back(self, trading_pair, sell_quantity, sell_price, buy_price):
        # Dostosowanie parametrów zlecenia sprzedaży
        sell_quantity, sell_price = self.adjust_order_params(sell_quantity, sell_price, trading_pair)
        if sell_quantity is None or sell_price is None:
            print(f"Nie można złożyć zlecenia dla {trading_pair} - niewystarczająca ilość lub cena.")
            return

        # Złóż zlecenie sprzedaży
        sell_order = await self.limit_order(trading_pair, sell_quantity, sell_price, Client.SIDE_SELL)
        if not sell_order:
            print("Nie udało się złożyć zlecenia sprzedaży.", trading_pair)
            print("quantity", sell_quantity)
            return
        
        sell_order_id = sell_order['orderId']

        # Monitoruj zlecenie sprzedaży
        while True:
            status = self.get_order_status(trading_pair, sell_order_id)

            print("="*50)
            print(f" Waiting for Sell Order Execution ".center(50, "="))
            print("="*50)
            print(f" Symbol       : {status['symbol']}")
            print(f" Price        : {status['price']}")
            print(f" Quantity     : {status['origQty']}")
            print(f" Total Amount : {float(status['origQty']) * float(status['price']):.2f} USD")
            print(f" Order ID     : {status['orderId']}")
            print("="*50)

            if status['status'] == 'FILLED':
                print(f"Zlecenie sprzedaży {sell_order_id} zostało zrealizowane. Składam zlecenie kupna.")
                
                # Dostosowanie parametrów zlecenia kupna
                buy_quantity, buy_price = self.adjust_order_params(sell_quantity, buy_price, trading_pair)
                if buy_quantity is None or buy_price is None:
                    print(f"Nie można złożyć zlecenia kupna dla {trading_pair} - niewystarczająca ilość lub cena.")
                    return
                
                # Złóż zlecenie kupna po realizacji sprzedaży
                await self.limit_order(trading_pair, buy_quantity, buy_price, Client.SIDE_BUY)
                break
            
            # Poczekaj 10 sekund przed ponownym sprawdzeniem
            await asyncio.sleep(10)

    async def monitor_pending_buy_orders(self, trading_pair: CryptoPair):

        show_pending_buy_orders = (len(trading_pair.active_orders) > 0)
        if show_pending_buy_orders:
            # Kolory stonowane: nagłówki w kolorze cyan, wartości w białym kolorze
            print(Fore.CYAN + "="*50)
            print(Fore.YELLOW + " Monitoring Pending Buy Orders ".center(50, "="))
            print(Fore.CYAN + "="*50)
            
            while True:
                open_orders = await self.get_open_orders(trading_pair.pair.replace("/", ""))
                
                if not open_orders:
                    pass
                else:
                    pending_buy_orders = [order for order in open_orders if order['side'] == 'BUY']
                    
                    if not pending_buy_orders:
                        print(Fore.RED + f"No pending buy orders for {trading_pair}.")
                    else:
                        for order in pending_buy_orders:
                            # Styl minimalistyczny, tylko jedna linia w innym kolorze
                            print(f"{Fore.LIGHTBLACK_EX} Symbol       : {Style.RESET_ALL}{order['symbol']}")
                            print(f"{Fore.LIGHTBLACK_EX} Price        : {Style.RESET_ALL}{order['price']}")
                            print(f"{Fore.LIGHTBLACK_EX} Quantity     : {Style.RESET_ALL}{order['origQty']}")
                            print(f"{Fore.LIGHTBLACK_EX} Total Amount : {Fore.YELLOW}{float(order['origQty']) * float(order['price']):.2f} USD")
                            print(f"{Fore.LIGHTBLACK_EX} Order ID     : {Style.RESET_ALL}{order['orderId']}")
                            print(Fore.CYAN + "="*50)
                
                # Poczekaj 10 sekund przed ponownym sprawdzeniem
                await asyncio.sleep(10)

    def get_recent_completed_orders(self, crypto_pair):
        try:
            time_window = 60000

            # Pobierz listę zakończonych zleceń dla danej pary
            completed_orders = crypto_pair.completed_orders
            recent_orders = []

            # Aktualny czas w milisekundach
            current_time = int(time.time() * 1000)

            for order in completed_orders:
                # Sprawdź, czy zlecenie jest wykonane i mieści się w oknie 10 minut
                if order.order_type in ["BUY", "SELL"] and (current_time - order.timestamp <= time_window * 1000):
                    recent_orders.append(order)

            if recent_orders:
                print(f"\n{'='*40}")
                print(f" Zlecenia wykonane w ciągu ostatnich 10 minut dla {crypto_pair.pair} ")
                print(f"{'='*40}\n")
                print(f"{'ID Zlecenia':<15}{'Typ':<10}{'Kwota':<10}{'Cena':<10}{'Czas'}")
                print(f"{'-'*60}")

                for order in recent_orders:
                    order_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(order.timestamp / 1000))
                    print(f"{order.order_id:<15}{order.order_type:<10}{order.amount:<10}{order.price:<10}{order_time}")
            else:
                print(f"\nBrak zleceń wykonanych dla {crypto_pair.pair}.\n")
                print(f"\n{'='*40}")

        except Exception as e:
            print(f"Błąd przy pobieraniu zleceń wykonanych dla {crypto_pair.pair}: {e}")

    def get_tick_size(self,symbol):
        """Pobiera krok cenowy (tick size) dla danego symbolu"""
        try:
            symbol_info = self.client.get_symbol_info(symbol)
            for filter in symbol_info['filters']:
                if filter['filterType'] == 'PRICE_FILTER':
                    return float(filter['tickSize'])
        except Exception as e:
            raise ValueError(f"Nie udało się pobrać tick size dla {symbol}: {str(e)}")

    def fetch_crypto_data(self, symbol, start_date, end_date):
        """
        Function to fetch historical cryptocurrency data from Binance.

        :param symbol: The trading pair symbol, e.g., 'BTCUSDT'
        :param start_date: Start date for fetching data in 'YYYY-MM-DD' format
        :param end_date: End date for fetching data in 'YYYY-MM-DD' format

        :return: DataFrame containing historical TOHLCV data (timestamp, open, high, low, close, volume)
        """
        # Convert dates to UNIX timestamp format
        start_str = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)  # In milliseconds
        end_str = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)

        # Fetch OHLCV (open, high, low, close, volume) data
        klines = self.client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1DAY, start_str, end_str)

        # Process the fetched data
        data = []
        for kline in klines:
            timestamp = datetime.fromtimestamp(kline[0] / 1000)
            open_price = float(kline[1])
            high_price = float(kline[2])
            low_price = float(kline[3])
            close_price = float(kline[4])
            volume = float(kline[5])
            data.append([timestamp, open_price, high_price, low_price, close_price, volume])

        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        return df

    def send_email_notification(self, subject, message, to_email = os.getenv('RECEIVER_EMAIL')):
        """
        Function to send an email notification.

        :param to_email: The recipient's email address
        :param subject: Email subject
        :param message: Email message content
        """
        try:
            from_email = os.getenv('SENDER_EMAIL')
            email_password = os.getenv('SENDER_EMAIL_KEY')

            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject

            # Attach the message
            msg.attach(MIMEText(message, 'plain'))

            # Send the email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(from_email, email_password)
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            server.quit()

            print("Email notification sent successfully!")
        except Exception as e:
            print(f"Error sending email: {e}")

    def get_order_status(self, trading_pair, order_id):
        """
        Function to retrieve the status of a specific order on Binance.

        :param trading_pair: Trading pair symbol, e.g., 'BTCUSDT'
        :param order_id: The unique identifier for the order to check

        :return: The details of the order, including its current status
        """
        try:
            order = self.client.get_order(symbol=trading_pair, orderId=order_id)
            return order
        except Exception as e:
            print(f"Error fetching order status: {e}")
            return None

    def get_wallet_balances(self):
        """
        Function to retrieve wallet balances from Binance.

        :return: A dictionary with asset balances
        """
        try:
            account_info = self.client.get_account()
            balances = account_info['balances']

            wallet_balances = {}
            for balance in balances:
                asset = balance['asset']
                free_amount = balance['free']
                locked_amount = balance['locked']

                # Only include assets with non-zero balance
                if float(free_amount) > 0 or float(locked_amount) > 0:
                    wallet_balances[asset] = {
                        'free': free_amount,
                        'locked': locked_amount
                    }

            return wallet_balances
        except Exception as e:
            print(f"Error retrieving wallet balances: {e}")
            return {}

    def get_all_trading_pairs(self):
        """
        Function to get all trading pairs (symbols) available on Binance.
        """
        try:
            exchange_info = self.client.get_exchange_info()
            symbols = [symbol['symbol'] for symbol in exchange_info['symbols']]
            return symbols
        except Exception as e:
            print(f"Error retrieving trading pairs: {e}")
            return []

    def get_order(self, symbol=None, include_historical=False):
        """
        Retrieve active and historical orders from Binance for a specific symbol.

        Parameters:
        symbol (str): The trading pair symbol for orders (e.g., 'BTCUSDT').
        include_historical (bool): Flag to indicate whether to fetch historical orders.

        Returns:
        dict: A dictionary containing two lists:
            - 'active_orders': List of active orders.
            - 'historical_orders': List of historical orders (if requested).
        """

        try:
            active_orders = self.client.get_open_orders(symbol=symbol)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        # Initialize lists for active and historical orders
        filtered_active_orders = []
        filtered_historical_orders = []

        # Filter active orders by the provided symbol, if any
        for order in active_orders:
            if symbol is None or order['symbol'] == symbol:
                filtered_active_orders.append(order)

        # If the include_historical flag is True and a symbol is provided, fetch historical orders
        if include_historical and symbol:
            historical_orders = self.client.get_all_orders(symbol=symbol)
            # print("Historical orders:", historical_orders)  # Logging for debugging

            # Filter historical orders to include only those that are not active
            for order in historical_orders:
                if order['status'] not in ['NEW', 'PARTIALLY_FILLED']:  # Retrieve only inactive orders
                    filtered_historical_orders.append(order)

        # Return a dictionary with active and historical orders
        return {
            'active_orders': filtered_active_orders,
            'historical_orders': filtered_historical_orders
        }

    def moving_average(self, data, period):
        """
        Calculate simple moving average (SMA).
        
        :param data: List of prices
        :param period: Window size for the moving average
        :return: SMA for the given period
        """
        return np.convolve(data, np.ones(period), 'valid') / period

    def is_on_peak(self, symbol, short_term_window=7, long_term_window=50):
        """
        Check if the cryptocurrency is on a peak (upward trend) or dip (downward trend).
        
        :param symbol: The trading pair (e.g., 'BTCUSDT')
        :param short_term_window: Period for the short-term moving average (default 7 days)
        :param long_term_window: Period for the long-term moving average (default 50 days)
        :return: True if in upward trend (local peak), False if downward trend (local dip)
        """
        data = self.get_historical_data(symbol)
        
        # Calculate moving averages
        short_term_ma = self.moving_average(data, short_term_window)
        long_term_ma = self.moving_average(data, long_term_window)
        
        # Check the most recent values to determine trend
        if short_term_ma[-1] > long_term_ma[-1]:  # Latest short-term MA above long-term MA
            return True  # Local peak (upward trend)
        else:
            return False  # Local dip (downward trend)

    def get_historical_data(self, symbol, interval='1d'):
        """
        Fetch historical price data for a given symbol (cryptocurrency)
        from Binance API.
        
        :param symbol: Trading pair (e.g., 'BTCUSDT')
        :param interval: Interval for data ('1d' for daily candles, '1h' for hourly candles)
        :param lookback: How much historical data to fetch (e.g., '100 days' or '30 minutes')
        :return: List of closing prices
        """
        candles = self.client.get_klines(symbol=symbol, interval=interval)
        closes = [float(candle[4]) for candle in candles]  # Extracting the closing price
        return closes

    def get_value_of_stable_coins_and_crypto(self) -> tuple:
        """
        Oblicza całkowitą wartość stablecoins oraz pozostałych kryptowalut w portfelu przy użyciu Binance API.
        
        Zwraca:
        tuple: Całkowita wartość stablecoins oraz całkowita wartość pozostałych kryptowalut w portfelu.
        """
        # Lista symboli stablecoins dostępnych na Binance
        stablecoins = ["USDT", "USDC", "BUSD", "DAI", "TUSD", "PAX", "HUSD", "GUSD", "SUSD", "EURS", "USTC"]

        # Pobranie balansu portfela z Binance
        wallet = self.get_wallet_balances()  # Ta funkcja powinna zwracać informacje o portfelu

        total_stablecoins_value = 0.0
        total_crypto_value = 0.0

        # Iteracja przez portfel użytkownika
        for currency, balance in wallet.items():
            free_amount = float(balance.get('free', 0))
            locked_amount = float(balance.get('locked', 0))
            total_amount = free_amount + locked_amount

            if total_amount == 0:
                continue  # Jeśli ilość danej waluty jest 0, pomijamy ją

            # Sprawdzamy, czy dany symbol jest stablecoinem
            if currency in stablecoins:
                total_stablecoins_value += total_amount  # Stablecoins są zazwyczaj równowarte 1 USD
            else:
                # Pobieramy cenę dla pozostałych kryptowalut z Binance
                try:
                    price = self.get_price(currency + "USDT")  # Zakładamy, że pary kryptowalutowe są do USDT
                    total_crypto_value += total_amount * price
                except Exception as e:
                    print(f"Nie udało się pobrać ceny dla {currency}: {str(e)}")

        return total_stablecoins_value, total_crypto_value

    def calculate_total_crypto_value(self, holdings):
        """
        Oblicza łączną wartość podanych kryptowalut w USD na podstawie ich aktualnych cen.
        
        :param holdings: Słownik z kryptowalutami i ich ilościami, np. {"BTC": 0.005, "ETH": 0.02}
        :return: Łączna wartość wszystkich kryptowalut w USD
        """
        total_value = 0.0  # Inicjalizujemy sumę wartości
        
        for symbol, amount in holdings.items():
            ticker_symbol = symbol + "USDT"  # Przyjmujemy, że wszystkie pary są do USDT
            ticker = self.client.get_symbol_ticker(symbol=ticker_symbol)
            price = float(ticker['price'])
            value = price * amount
            total_value += value  # Dodajemy wartość danej kryptowaluty do sumy
        
        return total_value  # Zwracamy łączną wartość

    def get_price(self, symbol: str) -> float:
        """
        Pobiera bieżącą cenę dla danego symbolu z Binance API.
        
        Parametry:
        symbol (str): Symbol pary, np. 'BTCUSDT'.
        
        Zwraca:
        float: Bieżąca cena rynkowa dla danej pary.
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            raise ValueError(f"Nie udało się pobrać ceny dla {symbol}: {str(e)}")

    def round_price_to_tick(self, price, tick_size):
        """
        Zaokrągla cenę do najbliższego tick_size.
        
        Args:
            price (float): Cena, którą chcemy zaokrąglić.
            tick_size (float): Wielkość kroku dla ceny.
        
        Returns:
            float: Cena zaokrąglona do najbliższego tick_size.
        """
        return round(price / tick_size) * tick_size

    def adjust_order_params(self, quantity, price, symbol):
        # Pobierz tick_size i minimalną wielkość zlecenia (LOT_SIZE) dla danego symbolu
        tick_size = self.get_tick_size(symbol)
        step_size = self.get_step_size(symbol)
        
        # Sprawdź, czy step_size został poprawnie pobrany
        if step_size is None:
            print(f"Nie udało się pobrać step_size dla symbolu {symbol}")
            return None, None
        
        # Zaokrąglij cenę do tick_size
        price = self.round_price_to_tick(price, tick_size)
        
        # Zaokrąglij ilość do step_size
        quantity = round(quantity / step_size) * step_size
        
        # Sprawdź, czy ilość spełnia minimalne wymagania LOT_SIZE
        if quantity < step_size:
            print(f"Zbyt mała ilość dla symbolu {symbol}: {quantity}, minimalna ilość: {step_size}")
            return None, None
        
        return quantity, price

    def get_step_size(self, symbol):
        """
        Pobiera wielkość kroku dla symbolu (LOT_SIZE), co jest minimalnym dopuszczalnym krokiem ilości zlecenia.
        
        Args:
            symbol (str): Symbol pary kryptowalutowej, np. "BTCUSDT".
        
        Returns:
            float: Wartość kroku dla wielkości zlecenia.
        """
        exchange_info = self.client.get_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        return float(f['stepSize'])
        # Jeśli symbol nie zostanie znaleziony, zwróć None
        return None

    async def strategyA(self, trading_pair, crypto_for_strategyA: float, cryptoValue: float, buy_price: float, sell_price: float):
        
        sell_quantity = crypto_for_strategyA

        print(f"Strategia dla pary: {trading_pair}")
        print(f"Sprzedaż po cenie: {sell_price}, Zakup po cenie: {buy_price}")
        
        await self.monitor_sell_and_buy_back(
            trading_pair=trading_pair,
            sell_quantity=sell_quantity,
            sell_price=sell_price,
            buy_price=buy_price)
          
    def strategyB(self, crypto_for_strategyA:float):
        pass    
    
    def strategyC(self, crypto_for_strategyA:float):
        pass
    
    def strategyD(self, crypto_for_strategyA:float):
        pass

    def strategyE(self, crypto_for_strategyA:float):
        pass
    
    def calculate_buy_and_sell_price(self, crypto_pair, buy_increase_indicator):
        """
        Oblicza cenę kupna i sprzedaży na podstawie wskaźnika wzrostu ceny kupna oraz docelowego zysku.
        
        Args:
            crypto_pair (object): Obiekt z informacjami o parze kryptowalut.
            buy_increase_indicator (float): Wskaźnik zwiększenia ceny kupna (np. 0.001 dla 0.1% powyżej bieżącej ceny).
            
        Returns:
            tuple: (buy_price, sell_price) - ceny kupna i sprzedaży po zaokrągleniu do tick_size.
        """
      
        symbol = crypto_pair.pair.replace("/", "")
        tick_size = self.get_tick_size(symbol)
        
        current_price = self.get_price(symbol)
        
        round_price = lambda price, tick_size: round(price / tick_size) * tick_size
        
        sell_price = round_price(price=(current_price * (1 + buy_increase_indicator)), tick_size=tick_size)
        
        buy_price = round_price(price=(crypto_pair.profit_target * current_price), tick_size=tick_size)
        
        return buy_price, sell_price

    async def handle_strategies(self, cryptoPair: CryptoPair, cryptoValue:float):

        crypto_for_trading = float(cryptoPair.crypto_amount_free) * cryptoPair.trading_percentage
        
        buy_price, sell_price = self.calculate_buy_and_sell_price(crypto_pair=cryptoPair,buy_increase_indicator= 0.001)
        
        # # Obliczanie procentowego stosunku sell_price do buy_price
        # sell_to_buy_percentage = ((sell_price - buy_price) / buy_price) * 100
        # buy_to_sell_percentage = ((buy_price - sell_price) / sell_price) * 100

        # # Wyświetlanie wyników

        # print(f"Symbol: {cryptoPair.pair}")
        # print(f"Buy Price: {buy_price}")
        # print(f"Sell Price: {sell_price}")
        # print(f"Sell Price is {sell_to_buy_percentage:.2f}% higher than Buy Price.")
        # print(f"Buy Price is {abs(buy_to_sell_percentage):.2f}% lower than Sell Price.")

        await self.strategyA(
                    trading_pair=cryptoPair.pair.replace("/",""),
                    crypto_for_strategyA=(float(crypto_for_trading) * float(cryptoPair.strategy_allocation['Strategy A'])), 
                    cryptoValue=cryptoValue,
                    buy_price=buy_price,
                    sell_price=sell_price
                    )
        

            



       



# # Example usage
# trader = BinanceTrader()

# print(trader.handle_strategies)
