import os
from binance.client import Client
from datetime import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json


class BinanceTrader:

    def __init__(self) -> None:
        # Initialize the Binance client using API keys from environment variables
        self.client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))
        self.orders_id = set()
        self.profit = 0.00

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

    def is_local_peak(self, symbol, interval='1h', lookback_period=5):
        """
        Function to determine if the current price of a cryptocurrency is a local peak.

        :param symbol: The trading pair symbol, e.g., 'BTCUSDT'
        :param interval: Time interval for historical data (default is '1h')
        :param lookback_period: Number of periods to check for a local peak (default is 5)

        :return: True if the current price is a local peak, otherwise False
        """
        try:
            interval_to_days = {
                '1h': 1 / 24,
                '1d': 1,
                '1w': 7,
                '1M': 30,
                '1Y': 365
            }
            days = lookback_period * interval_to_days.get(interval, 1)
            klines = self.client.get_historical_klines(symbol, interval, f"{days} days ago UTC")

            closing_prices = [float(kline[4]) for kline in klines]
            current_price = closing_prices[-1]

            is_peak = all(current_price > closing_prices[-(i + 2)] for i in range(lookback_period))
            return is_peak
        except Exception as e:
            print(f"Error determining local peak: {e}")
            return False

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

    def notify_if_worth_buying(self, symbol):
        """
        Function that checks if it's worth buying a cryptocurrency (based on local peak check)
        and sends an email notification if true.

        :param symbol: The trading pair symbol, e.g., 'BTCUSDT'

        """
        if self.is_local_peak(symbol):
            subject = f"Opportunity to buy {symbol}"
            message = f"The price of {symbol} is at a local peak. It might be a good time to buy."
            self.send_email_notification(subject, message)
        else:
            print(f"No buying opportunity for {symbol} at the moment.")

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

    def notify_if_worth_buying_all_symbols(self, interval='1h', lookback_period=5):
        """
        Function to check if it's worth buying any cryptocurrency and send email notifications.
        """
        symbols = self.get_all_trading_pairs()
        for symbol in symbols:
            if self.is_local_peak(symbol, interval, lookback_period):
                subject = f"Opportunity to buy {symbol}"
                message = f"The price of {symbol} is at a local peak. It might be a good time to buy."
                self.send_email_notification(subject, message)
            else:
                print(f"No buying opportunity for {symbol} at the moment.")

    # def get_orders(self, trading_pair=None, order_status="all"):
    #     """
    #     Function to retrieve open or all orders for a specific trading pair or all symbols.
        
    #     :param trading_pair: Optional. The trading pair symbol, e.g., 'BTCUSDT'. If None, fetches for all symbols.
    #     :param order_status: Optional. Specifies whether to fetch 'open', 'all', or 'closed' orders. Default is 'all'.
        
    #     :return: List of orders.
    #     """
    #     try:
    #         orders = []
            
    #         # Fetch open orders if order_status is 'open'
    #         if order_status == "open":
    #             if trading_pair:
    #                 orders = self.client.get_open_orders(symbol=trading_pair)
    #             else:
    #                 orders = self.client.get_open_orders()  # Fetch open orders for all symbols
            
    #         # Fetch all orders if order_status is 'all' or closed orders if order_status is 'closed'
    #         elif order_status in ["all", "closed"]:
    #             symbols = [trading_pair] if trading_pair else self.get_all_trading_pairs()
                
    #             for symbol in symbols:
    #                 all_orders = self.client.get_all_orders(symbol=symbol)
                    
    #                 # Filter closed orders if needed
    #                 if order_status == "closed":
    #                     closed_orders = [order for order in all_orders if order['status'] in ['FILLED', 'CANCELED']]
    #                     orders.extend(closed_orders)
    #                 else:
    #                     orders.extend(all_orders)
            
    #         # Return the retrieved orders
    #         return orders
        
    #     except Exception as e:
    #         print(f"Error retrieving orders: {e}")
    #         return []

    def get_orders(self, include_historical=False):

        
        # Pobierz aktywne zlecenia
        active_orders = self.client.get_open_orders()
        
        buy_orders = []
        sell_orders = []
        
        for order in active_orders:
            if order['side'] == 'BUY':
                buy_orders.append(order)
            elif order['side'] == 'SELL':
                sell_orders.append(order)

        # Jeśli flaga include_historical jest True, pobierz także stare zlecenia
        if include_historical:
            historical_orders = self.client.get_all_orders()

            for order in historical_orders:
                if order['status'] not in ['NEW', 'PARTIALLY_FILLED']:  # Pobieramy tylko nieaktywne zlecenia
                    if order['side'] == 'BUY':
                        buy_orders.append(order)
                    elif order['side'] == 'SELL':
                        sell_orders.append(order)
        
        return {'buy_orders': buy_orders, 'sell_orders': sell_orders}

# Example usage
trader = BinanceTrader()

# Example: Check if it's worth buying BTC and send an email if true
# trader.notify_if_worth_buying('BTCUSDT')

# print(trader.get_order_status())

print(json.dumps(trader.get_orders(True),indent=4))
