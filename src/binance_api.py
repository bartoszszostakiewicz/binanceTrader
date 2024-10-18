import os
from binance.client import Client
from datetime import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import numpy as np
import json


class BinanceTrader:

    def __init__(self) -> None:
        # Initialize the Binance client using API keys from environment variables
        self.client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
        self.orders_id = set()
        self.profit = 0.00

        self.working_percentage = 0.3
        self.buy_percentage = 0.1
        self.sell_percentage = 0.1

    def limit_order(self, trading_pair, quantity, buy_price, type=Client.ORDER_TYPE_LIMIT, side=Client.SIDE_BUY):
        """
        Function to place a limit buy or sell order on Binance exchange.

        :param trading_pair: The trading pair, e.g., 'BTCUSDT'
        :param quantity: Amount of cryptocurrency to buy or sell
        :param buy_price: Price at which to buy or sell
        :param type: Order type (default: limit order)
        :param side: Buy or sell order (default: buy)
        
        :return: Order details if successfully placed, otherwise None
        """
        try:
            order = self.client.create_order(
                symbol=trading_pair,
                side=side,
                type=type,
                timeInForce=Client.TIME_IN_FORCE_GTC,  # Good 'Til Canceled
                quantity=quantity,
                price=str(buy_price)
            )
            print(f"{side.capitalize()} order placed successfully!")
            self.orders_id.add(order['orderId'])
            return order
        except Exception as e:
            print(f"Error placing {side} order: {e}")
            return None

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

    def get_orders(self, symbol=None, include_historical=False):
        """
        Retrieve active and historical orders from Binance.

        Parameters:
        symbol (str): The trading pair symbol for historical orders (e.g., 'BTCUSDT').
        include_historical (bool): Flag to indicate whether to fetch historical orders.

        Returns:
        dict: A dictionary containing two lists:
            - 'buy_orders': List of active and/or historical buy orders.
            - 'sell_orders': List of active and/or historical sell orders.
        """

        # Fetch active orders from Binance
        active_orders = self.client.get_open_orders()

        buy_orders = []
        sell_orders = []
        
        # Separate active orders into buy and sell lists
        for order in active_orders:
            if order['side'] == 'BUY':
                buy_orders.append(order)
            elif order['side'] == 'SELL':
                sell_orders.append(order)

        # If the include_historical flag is True and a symbol is provided, fetch historical orders
        if include_historical and symbol:
            historical_orders = self.client.get_all_orders(symbol=symbol)
            print("Historical orders:", historical_orders)  # Logging for debugging

            # Filter historical orders to include only those that are not active
            for order in historical_orders:
                if order['status'] not in ['NEW', 'PARTIALLY_FILLED']:  # Retrieve only inactive orders
                    if order['side'] == 'BUY':
                        buy_orders.append(order)
                    elif order['side'] == 'SELL':
                        sell_orders.append(order)
        
        # Return a dictionary with buy and sell orders
        return {'buy_orders': buy_orders, 'sell_orders': sell_orders}

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

# Example usage
trader = BinanceTrader()

print(json.dumps(trader.get_orders(),indent=4))
