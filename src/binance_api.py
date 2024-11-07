import asyncio
import os
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Dict
from binance.client import Client
from datetime import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import numpy as np
from data_classes import CryptoPair, Order, TradeStrategy
import time
from colorama import Fore, Style, init
import uuid
import requests
from constants import *
from enum import Enum
from logger import logger


def ready_for_release(func):
    func.is_ready = True
    return func

def ok(func):
    func.is_ok = True
    return func

def not_tested(func):
    
    func.not_tested = True
    return func

def temporary_fix(func):
    func.temp_fix=True
    return func

def to_consider(func):
    func.is_to_consider=True
    return func

def doesnt_work(func):
    func.doesnt_work=True
    return func




class BinanceTrader:

    @ready_for_release
    def __init__(self) -> None:
        try:
            # Attempt to retrieve API keys from environment variables
            api_key = os.getenv('BINANCE_API_KEY')
            secret_key = os.getenv('BINANCE_SECRET_KEY')
            
            if not api_key or not secret_key:
                raise ValueError("Binance API keys are missing. Please check that they are set in environment variables.")
            
            # Initialize the Binance client
            self.client = Client(api_key, secret_key)
            self.orders_id = set()
            
            # Initialize colorama for automatic console color reset
            init(autoreset=True)
        
        except ValueError as ve:
            logger.error(f"Initialization error: {ve}")
        except Exception as e:
            logger.exception(f"Error initializing Binance client: {e}")


    @ready_for_release
    def get_price(self, symbol: str) -> dict:
        """Pobiera aktualną cenę dla danego symbolu z Binance API."""
        try:
            price_data = self.client.get_symbol_ticker(symbol=symbol)
            return price_data  # Zwracamy wynik jako słownik z ceną
        except Exception as e:
            logger.exception(f"Błąd podczas pobierania ceny dla symbolu {symbol}: {e}")
            return {}


    @ready_for_release
    def get_tick_size(self, symbol):
        """
        Retrieves the tick size (price step) for a given trading pair symbol.
        
        Args:
            symbol (str): The trading pair symbol, e.g., 'BTCUSDT'.
        
        Returns:
            float: The tick size for the specified symbol.
        
        Raises:
            ValueError: If the tick size could not be retrieved.
        """
        try:
            # Fetch symbol information to retrieve the tick size
            symbol_info = self.client.get_symbol_info(symbol)
            for filter in symbol_info['filters']:
                if filter['filterType'] == 'PRICE_FILTER':
                    logger.debug(f"Tick size for {symbol} = {filter['tickSize']}")
                    return float(filter['tickSize'])
        except Exception as e:
            # Raise an error with details if the tick size retrieval fails
            logger.exception(f"Failed to retrieve tick size for {symbol}")
            raise ValueError(f"Failed to retrieve tick size for {symbol}: {str(e)}")
     
     
    @ready_for_release
    def get_order_status(self, trading_pair, order_id):
        """
        Checking order status
        """
        try:
            order = self.client.get_order(symbol=trading_pair, orderId=order_id)
            return order
        except Exception as e:
            logger.exception(f"Error checking order status: {e}")
            return None


    @ready_for_release
    async def get_open_orders(self, trading_pair):
        """
        Retrieves open orders for a given cryptocurrency trading pair.
        
        Args:
            trading_pair (str): The trading pair symbol, e.g., 'BTCUSDT'.
        
        Returns:
            list: A list of open orders for the specified trading pair.
        """
        try:
            # Fetch the list of open orders for the specified trading pair
            open_orders = self.client.get_open_orders(symbol=trading_pair)
            return open_orders
        except Exception as e:
            # Handle errors by logging them and returning an empty list
            logger.exception(f"Error retrieving open orders for {trading_pair}: {e}")
            return []


    @ready_for_release
    async def cancel_order(self, trading_pair, order_id):
        """
        Cancels an order on Binance for the specified trading pair and order ID.

        Args:
            trading_pair (str): Symbol of the trading pair (e.g., "BTCUSDT").
            order_id (int): ID of the order to be canceled.

        Returns:
            dict or None: Information about the canceled order, or None if the cancellation failed.
        """
        try:
            # Attempt to cancel the order with the specified trading pair and order ID
            response = await self.client.cancel_order(
                symbol=trading_pair,
                orderId=order_id
            )
            logger.info(f"Order {order_id} for {trading_pair} has been canceled.")
            return response
        except Exception as e:
            # Handle errors by logging them and returning None if the cancellation fails
            logger.exception(f"Failed to cancel order {order_id} for {trading_pair}. Error: {e}")
            return None


    @ready_for_release
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
            logger.exception(f"Error retrieving wallet balances: {e}")
            return {}


    @ready_for_release
    def get_value_of_stable_coins_and_crypto(self) -> tuple:
        """
        Calculates the total value of stablecoins and other cryptocurrencies in the wallet using the Binance API.
        
        Returns:
            tuple: Total value of stablecoins and total value of other cryptocurrencies in the wallet.
        """
        # List of stablecoins available on Binance
        stablecoins = ["USDT", "USDC", "BUSD", "DAI", "TUSD", "PAX", "HUSD", "GUSD", "SUSD", "EURS", "USTC"]

        # Fetch wallet balance from Binance
        wallet = self.get_wallet_balances()  # This function should return wallet balance information

        total_stablecoins_value = 0.0
        total_crypto_value = 0.0

        # Iterate through the user's wallet
        for currency, balance in wallet.items():
            free_amount = float(balance.get('free', 0))
            locked_amount = float(balance.get('locked', 0))
            total_amount = free_amount + locked_amount

            if total_amount == 0:
                continue  # Skip if the currency amount is 0

            # Check if the currency is a stablecoin
            if currency in stablecoins:
                total_stablecoins_value += total_amount  # Stablecoins are generally equivalent to 1 USD
            else:
                # Get the price for other cryptocurrencies in USDT
                try:
                    price = self.get_price(currency + "USDT")  # Assuming crypto pairs are listed in USDT
                    total_crypto_value += total_amount * price
                except Exception as e:
                    logger.exception(f"Failed to fetch price for {currency}: {str(e)}")
        
        return total_stablecoins_value, total_crypto_value


    @ready_for_release
    def get_price(self, symbol: str) -> float:
        """
        Retrieves the current price for a given symbol from the Binance API.
        
        Args:
            symbol (str): The trading pair symbol, e.g., 'BTCUSDT'.
        
        Returns:
            float: The current market price for the specified trading pair.
        
        Raises:
            ValueError: If the price cannot be retrieved.
        """
        try:
            # Fetch the current price for the specified trading pair
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            logger.debug(f"Successfully retrieved price for {symbol}")
            return float(ticker["price"])
        except Exception as e:
            # Raise an error if price retrieval fails
            logger.exception(f"Failed to retrieve price for {symbol}")
            raise ValueError(f"Failed to retrieve price for {symbol}: {str(e)}")


    @ready_for_release
    def format_price(self, price, tick_size):
        """
        Rounds the price to the specified tick size.
        
        Args:
            price (float): The price to be formatted.
            tick_size (float): The tick size for rounding.
        
        Returns:
            float or None: The rounded price, or None if the tick_size or price is invalid.
        """
        try:
            # Check if tick_size is a valid value
            if tick_size is None or tick_size == 0:
                logger.error("Error: Invalid tick_size.")
                return None
            
            # Check if price is a valid value
            if price is None:
                logger.error("Error: Invalid price.")
                return None

            # Convert to Decimal and round down to the nearest tick size
            rounded_price = Decimal(price).quantize(Decimal(str(tick_size)), rounding=ROUND_DOWN)
            return float(rounded_price)
        
        except InvalidOperation:
            logger.exception(f"Error: Unable to round price {price} to tick_size {tick_size}")
            return None


    @ready_for_release
    def adjust_order_params(self, quantity, price, trading_pair):
        """
        Adjusts the order parameters (quantity and price) to meet the Binance trading requirements
        for the specified trading pair.

        Args:
            quantity (float): The desired order quantity.
            price (float): The desired order price.
            trading_pair (str): The trading pair, e.g., "BTCUSDT".

        Returns:
            tuple: Adjusted quantity and price as floats, or (None, None) if the order does not meet requirements.
        """
        tick_size = self.get_tick_size(trading_pair)  # Retrieve tick_size for the trading pair
        step_size = self.get_step_size(trading_pair)  # Retrieve step_size for the trading pair
        min_notional = self.get_min_notional(trading_pair)  # Retrieve min_notional for the trading pair

        try:
            # Set price precision according to tick_size
            tick_size_decimal = Decimal(str(tick_size))
            price_precision = abs(tick_size_decimal.as_tuple().exponent)
            price = Decimal(price).quantize(tick_size_decimal, rounding=ROUND_DOWN)
            formatted_price = "{:.{}f}".format(price, price_precision)  # Format price with tick_size precision
            
            # Set quantity precision according to step_size
            step_size_decimal = Decimal(str(step_size))
            quantity_precision = abs(step_size_decimal.as_tuple().exponent)
            quantity = Decimal(quantity).quantize(step_size_decimal, rounding=ROUND_DOWN)
            formatted_quantity = "{:.{}f}".format(quantity, quantity_precision)  # Format quantity with step_size precision

            # Check if the transaction value meets the min_notional requirement
            if Decimal(formatted_quantity) * Decimal(formatted_price) < Decimal(str(min_notional)):
                logger.error(f"Order cannot be placed: transaction value ({Decimal(formatted_quantity) * Decimal(formatted_price)}) is less than min_notional ({min_notional}).")
                return None, None

            # Debugging print statements
            logger.debug(f"Formatted price: {price}, type: {type(price)}")
            logger.debug(f"Formatted quantity: {quantity}, type: {type(quantity)}")

            return float(formatted_quantity), float(formatted_price)

        except Exception as e:
            logger.exception(f"Error adjusting order parameters: {e}")
            return None, None



    @ready_for_release
    def get_step_size(self, symbol):
        """
        Retrieves the step size (LOT_SIZE) for the specified symbol, which is the minimum allowable quantity increment for orders.
        
        Args:
            symbol (str): The cryptocurrency trading pair symbol, e.g., "BTCUSDT".
        
        Returns:
            float: The step size for order quantity, or None if the symbol is not found.
        """
        exchange_info = self.client.get_exchange_info()
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'LOT_SIZE':
                        return float(f['stepSize'])
        # Return None if the symbol is not found
        return None



    @ready_for_release
    def get_min_notional(self, symbol):
        """
        Retrieves the min_notional (minimum allowable trade value) for the specified symbol from the Binance API.
        
        Args:
            symbol (str): The cryptocurrency trading pair symbol, e.g., "BTCUSDT".
        
        Returns:
            float: The min_notional value for the trading pair, or None if not found.
        """
        exchange_info = self.client.get_exchange_info()
        
        for s in exchange_info['symbols']:
            if s['symbol'] == symbol:
                for f in s['filters']:
                    if f['filterType'] == 'NOTIONAL':
                        min_notional = f['minNotional']
                        logger.debug(f"Min_notional for symbol {symbol}: {min_notional}")
                        return float(min_notional)
        
        # Print message if min_notional is not found for the symbol
        logger.error(f"Min_notional not found for symbol {symbol}")
        return None


    @ready_for_release
    def get_public_ip(self):
        """
        Retrieves the public IP address of the current network.

        Returns:
            str or None: The public IP address as a string, or None if the request fails.
        """
        try:
            response = requests.get("https://api.ipify.org?format=json")
            response.raise_for_status()  # Check if the request was successful
            ip = response.json().get("ip")
            return ip
        except requests.RequestException as e:
            # Handle any request-related errors and return None if the IP retrieval fails
            logger.exception(f"Failed to retrieve public IP address: {e}")
            return None


    @ready_for_release
    def analyze_orders(self, symbol: str) -> Dict[str, float]:
        """
        Fetch and analyze active and historical orders for a given symbol from Binance.
        Returns counts, quantities, and total amounts for buy and sell orders.
        """
        buy_count = sell_count = 0
        buy_quantity = sell_quantity = 0.0
        total_buy_value = total_sell_value = 0.0

        # Fetch open orders and calculate quantities
        open_orders = self.client.get_open_orders(symbol=symbol)

        for order in open_orders:
            if order['side'] == "BUY":
                buy_count += 1
                buy_quantity += float(order['origQty'])
            elif order['side'] == "SELL":
                sell_count += 1
                sell_quantity += float(order['origQty'])

        # Fetch all historical orders and calculate filled quantities and values
        all_orders = self.client.get_all_orders(symbol=symbol)

        for order in all_orders:
            if order['status'] == 'FILLED':
                executed_quantity = float(order['executedQty'])
                price = float(order['price'])
                order_value = executed_quantity * price

                if order['side'] == "BUY":
                    buy_count += 1
                    buy_quantity += executed_quantity
                    total_buy_value += order_value
                elif order['side'] == "SELL":
                    sell_count += 1
                    sell_quantity += executed_quantity
                    total_sell_value += order_value

        return {
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_bought_quantity": buy_quantity,
            "total_sold_quantity": sell_quantity,
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "quantity_missing": (sell_quantity - buy_quantity)
        }



    @ready_for_release
    def  calculate_buy_and_sell_price(self, crypto_pair: CryptoPair, strategy: TradeStrategy):
        """
        Calculates the buy and sell prices based on the buy increase indicator and target profit.
        
        Args:
            crypto_pair (CryptoPair): An object containing information about the cryptocurrency pair.
            buy_increase_indicator (float): The indicator for the increase in the buy price (e.g., 0.001 for 0.1% above the current price).
            strategy(str): Strategy for which the buy and sell price are calculated.
            
        Returns:
            tuple: (buy_price, sell_price) - the rounded buy and sell prices according to tick_size.
        """
        
        tick_size = self.get_tick_size(crypto_pair.pair)
        current_price = self.get_price(crypto_pair.pair)
        round_price = lambda price, tick_size: round(price / tick_size) * tick_size
        
        if strategy.name == POOR_ORPHAN:
            sell_price = round_price(price=(current_price * (1 + strategy.buy_increase_indicator)), tick_size=tick_size)
            buy_price = round_price(price=(strategy.profit_target * current_price), tick_size=tick_size)
        elif strategy.name == CRAZY_GIRL:
            sell_price = round_price(price=(current_price * (1 + strategy.buy_increase_indicator)), tick_size=tick_size)
            buy_price = round_price(price=(strategy.profit_target * current_price), tick_size=tick_size)
        elif strategy.name == SENSIBLE_GUY:
            sell_price = round_price(price=(current_price * (1 + strategy.buy_increase_indicator)), tick_size=tick_size)
            buy_price = round_price(price=(strategy.profit_target * current_price), tick_size=tick_size)
        else:
            sell_price = None
            buy_price = None
        
                
        return buy_price, sell_price


    @ready_for_release
    async def handle_strategies(self, cryptoPair: CryptoPair, strategies: Dict[str, TradeStrategy]):
        
        strategy_func_list = [self.poor_orphan, self.crazy_girl, self.sensible_guy]
        strategy_list = [strategies[POOR_ORPHAN], strategies[CRAZY_GIRL], strategies[SENSIBLE_GUY]]
       
        tasks = []
  
        for strategy_func, strategy in zip(strategy_func_list, strategy_list):

            task = asyncio.create_task(
                strategy_func(
                cryptoPair=cryptoPair,
                strategy=strategy
                )
            )
            
            tasks.append(task)
        
        await asyncio.gather(*tasks)







    @temporary_fix
    async def limit_order(self, trading_pair, quantity, price, side=Client.SIDE_SELL):
        """
        Składa zlecenie limit.
        """
        # Twoje trzy liczby, np. 999
        custom_prefix = "999"

        orderId = f"{custom_prefix}_{str(uuid.uuid4())[:8]}"


        if trading_pair == "SHIBUSDT":
            price = "{:.8f}".format(price)
            quantity = Decimal(quantity).quantize(1)
            print("shib")
            print(f'price= {price}')
            print(f'quantity= {quantity}')
        if trading_pair == "XLMUSDT":
            quantity = Decimal(quantity).quantize(1)
            print("xlm")
            print(f'price= {price}')
            print(f'quantity= {quantity}')


        try:
            order = self.client.create_order(
                symbol=trading_pair,
                side=side,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=quantity,
                price=str(price),
                newClientOrderId = orderId,

            )
            logger.info(f"{side.capitalize()} order placed at {price}!")
            return order
        except Exception as e:
            logger.exception(f"Error placing {side} order: {e}")
            return None

    
    @to_consider
    @not_tested
    @temporary_fix #calculating price
    async def monitor_sell_and_buy_back(self, cryptoPair: CryptoPair, sell_quantity, sell_price, buy_price, strategy, timeout=3600):

        trading_pair = cryptoPair.pair
        # Dostosowanie parametrów zlecenia sprzedaży przed złożeniem zamówienia
        sell_quantity, sell_price = self.adjust_order_params(sell_quantity, sell_price, trading_pair)
        
        if sell_quantity is None or sell_price is None:
            print(f"Nie można złożyć zlecenia sprzedaży dla {trading_pair} - niewystarczająca ilość lub cena.")
            return

        # Złóż zlecenie sprzedaży
        sell_order = await self.limit_order(trading_pair, sell_quantity, sell_price, Client.SIDE_SELL)
        if not sell_order:
            print("Nie udało się złożyć zlecenia sprzedaży.", trading_pair)
            return
        
        # ###############################################
        # cryptoPair.add_order( 
        #         Order(
        #         trading_pair, 
        #         sell_order['orderId'],
        #         order_type="SELL",
        #         amount=sell_quantity,
        #         price=sell_price,
        #         timestamp=sell_order['timestamp'],
        #         strategy=strategy,
        #     )
        # )
        # ###############################################

        sell_order_id = sell_order['orderId']
        start_time = time.time()

        while True:
            # Sprawdź czas upłynięcia
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                print(f"Timeout dla zlecenia sprzedaży {sell_order_id}. Anulowanie zlecenia i dostosowanie ceny.")
                
                # Sprawdzenie, czy anulowanie się powiodło
                #tutaj sie wywwala
                cancel_result = await self.cancel_order(trading_pair, sell_order_id)
                if cancel_result is None or cancel_result.get("status") != "CANCELED":
                    print(f"Nie udało się anulować zlecenia {sell_order_id} dla {trading_pair}.")
                    return  # Wyjdź z funkcji, jeśli anulowanie nie powiodło się
                print(f"Anulowano zlecenie sprzedaży")
                return
                
               

            # Monitoruj status zlecenia
            status = self.get_order_status(trading_pair, sell_order_id)
          

            print("="*50)
            print(f" Waiting for Sell Order Execution ".center(50, "="))
            print("="*50)
            print(f" Symbol       : {status['symbol']}")
            print(f" Price        : {status['price']}")
            print(f" Current price: {self.get_price(status['symbol'])}")
            print(f" Quantity     : {status['origQty']}")
            print(f" Total Amount : {float(status['origQty']) * float(status['price']):.2f} USD")
            print(f" Order ID     : {status['orderId']}")
            print("="*50)

            if status['status'] == 'FILLED':
                print(f"Zlecenie sprzedaży {sell_order_id} zostało zrealizowane. Składam zlecenie kupna.")
                
                # ###############################################
                # cryptoPair.remove_order_by_id(sell_order_id)
                # ###############################################
                

                # Ustawienie buy_quantity na sell_quantity, ponieważ chcemy odkupić tę samą ilość
                buy_quantity = sell_quantity
                
                # Dostosowanie ceny kupna do odpowiedniego tick_size
                buy_price = self.format_price(buy_price, self.get_tick_size(trading_pair))
                if buy_quantity is None or buy_price is None:
                    print(f"Nie można złożyć zlecenia kupna dla {trading_pair} - niewystarczająca ilość lub cena.")
                    return

                # Złóż zlecenie kupna po realizacji sprzedaży
                buy_order = await self.limit_order(trading_pair, buy_quantity, buy_price, Client.SIDE_BUY)
                
                if not buy_order:
                    print("Nie udało się złożyć zlecenia kupna")
                    return
                
                # ###############################################
                # cryptoPair.add_order( 
                #     Order(
                #         trading_pair, 
                #         buy_order['orderId'],
                #         order_type="BUY",
                #         amount=buy_quantity,
                #         price=buy_price,
                #         timestamp=buy_order['timestamp'],
                #         strategy=strategy,
                #     )
                # )
                # ###############################################
                
                break

            # Poczekaj 10 sekund przed ponownym sprawdzeniem
            await asyncio.sleep(10)


    @not_tested
    async def monitor_buy_orders(self, cryptoPair: CryptoPair):
        """
        Monitors active buy orders for the specified CryptoPair and removes them
        from active orders once they are filled.
        
        Parameters:
            cryptoPair (CryptoPair): The crypto pair for which buy orders are being monitored.
            timeout (int): The maximum time (in seconds) to wait for an order to fill before stopping the check.
            
        Returns:
            None
        """
       
        
        while True:


            # Go through each active buy order in cryptoPair
            for order in list(cryptoPair.active_orders):  # Use a copy of the list to allow safe removal
                if order.order_type == "BUY":
                    # Fetch the current status of the order
                    status = self.get_order_status(cryptoPair.pair, order.order_id)

                    # Display order information
                    logger.info("="*50)
                    logger.info(f" Monitoring Buy Order ".center(50, "="))
                    logger.info("="*50)
                    logger.info(f" Symbol       : {status['symbol']}")
                    logger.info(f" Buy Price    : {status['price']}")
                    logger.info(f" Current Price: {self.get_price(status['symbol'])}")
                    logger.info(f" Quantity     : {status['origQty']}")
                    logger.info(f" Total Amount : {float(status['origQty']) * float(status['price']):.2f} USD")
                    logger.info(f" Order ID     : {status['orderId']}")
                    logger.info("="*50)

                    # If the order is filled, remove it from active orders and update crypto balance
                    if status['status'] == 'FILLED':
                        logger.debug(f"Buy order {order.order_id} for {cryptoPair.pair} has been filled.")
                        
                        # Remove the filled order
                        cryptoPair.remove_order_by_id(order.order_id)

                        # Update free crypto amount based on the filled buy order
                        cryptoPair.crypto_amount_free += order.amount
                        logger.debug(f"Updated free crypto amount: {cryptoPair.crypto_amount_free}")
                        
                    elif status['status'] == 'CANCELED':
                        # If the order was canceled, remove it as well
                        logger.debug(f"Buy order {order.order_id} was canceled. Removing from active orders.")
                        cryptoPair.remove_order_by_id(order.order_id)

            # Sleep for a few seconds before checking again
            await asyncio.sleep(10)

    
    
    
    
    async def sell(self, cryptoPair: CryptoPair, sell_quantity: float, sell_price: float, strategy: str):
        """
        Places a sell order for a specified cryptocurrency pair and monitors the result.

        Parameters:
        - cryptoPair (CryptoPair): The cryptocurrency pair to be traded.
        - sell_quantity (float): The quantity to be sold.
        - sell_price (float): The price at which to sell the asset.
        - buy_price (float): The price at which to buy back the asset if necessary.
        - strategy (str): The trading strategy associated with this transaction.
        - timeout (int): The maximum time in seconds to wait for the order to be filled.

        Workflow:
        1. Adjusts the order parameters (quantity and price) based on the trading pair.
        2. Checks if the adjusted quantity and price are valid.
        3. Places a limit sell order and monitors the response.
        
        If an error occurs at any step, appropriate error handling is applied, and the function exits.

        Returns:
        - None if the function completes without placing an order or encounters an error.
        """
        
        try:
            trading_pair = cryptoPair.pair

            # Adjust the sell quantity and sell price based on trading requirements for the pair
            sell_quantity, sell_price = self.adjust_order_params(sell_quantity, sell_price, trading_pair)
            
            if sell_quantity is None or sell_price is None:
                logger.error(f"Unable to place sell order for {trading_pair} - insufficient quantity or price.")
                return

            # Attempt to place a sell order
            sell_order = await self.limit_order(trading_pair, sell_quantity, sell_price, Client.SIDE_SELL)
            if not sell_order:
                logger.error(f"Failed to place sell order for {trading_pair}.")
                return
            
            # Log success if order is successfully placed
            logger.info(f"Sell order successfully placed for {trading_pair}. Quantity: {sell_quantity}, Price: {sell_price}")
            
            return sell_order['orderId']

        except Exception as e:
            # Error handling - log or handle specific cases as needed
            logger.exception(f"An error occurred while trying to place a sell order for {cryptoPair.pair}: {str(e)}")

    
    
    async def buy(self, cryptoPair: CryptoPair, buy_quantity: float, buy_price: float, strategy: str):
        """
        Places a buy order for a specified cryptocurrency pair and returns the order ID if successful.

        Parameters:
        - cryptoPair (CryptoPair): The cryptocurrency pair to be traded.
        - buy_quantity (float): The quantity of the asset to buy.
        - buy_price (float): The price at which to buy the asset.
        - strategy (str): The trading strategy associated with this transaction.

        Returns:
        - buy_order['orderId'] if the order is successfully placed.
        - None if the function encounters an error or cannot place the order.
        
        Workflow:
        1. Adjusts the buy price to the appropriate tick size.
        2. Validates that both `buy_quantity` and `buy_price` are valid.
        3. Places a limit buy order and retrieves the order ID if successful.
        
        Exceptions and errors are logged, and the function exits gracefully if any issue occurs.
        """
        
        try:
            # Adjust the sell quantity and sell price based on trading requirements for the pair
            buy_quantity, buy_price = self.adjust_order_params(buy_quantity, buy_price, cryptoPair.pair)
            
            if buy_quantity is None or buy_price is None:
                logger.error(f"Unable to place sell order for {cryptoPair.pair} - insufficient quantity or price.")
                return
            
            
            # Attempt to place a buy order
            buy_order = await self.limit_order(cryptoPair.pair, buy_quantity, buy_price, Client.SIDE_BUY)
            
            if not buy_order:
                logger.error(f"Failed to place buy order for {cryptoPair.pair}.")
                return None

            # Log success and return the buy order ID
            order_id = buy_order['orderId']
            logger.info(f"Buy order successfully placed for {cryptoPair.pair}. Quantity: {buy_quantity}, Price: {buy_price}, Order ID: {order_id}")
            return order_id

        except Exception as e:
            # Error handling - log specific error
            logger.exception(f"An error occurred while trying to place a buy order for {cryptoPair.pair}: {str(e)}")
            return None



       
    @not_tested
    async def poor_orphan(self, cryptoPair: CryptoPair, strategy: TradeStrategy):
        
        current_state = 0 #needs to add logic for get_state
        
        
        
        buy_price, sell_price = self.calculate_buy_and_sell_price(
            crypto_pair=cryptoPair,
            strategy=strategy
        )
        
        logger.debug(f"Strategy: {strategy.name} for {cryptoPair.pair}")
      

        # # Wybierz tylko zlecenia typu SELL powiązane ze strategią "A"
        # buy_orders = [order for order in cryptoPair.active_orders if order.order_type == "BUY" and order.strategy == "A"]
        # # print(f"symbol = {cryptoPair.pair}")
        # # print(buy_orders)
        
        # # # Obsługa pierwszej iteracji - jeśli nie ma zleceń sprzedaży, ustaw timestamp na 0
        # # if buy_orders:
        # #     last_sell_timestamp = max(order.timestamp for order in buy_orders)
        # #     print
        # # else:
        # #     last_sell_timestamp = 0  # brak wcześniejszych zleceń, można od razu złożyć nowe

        # # Sprawdzenie, czy minęło 3600 sekund od ostatniego zlecenia sprzedaży
        # # if time() - last_sell_timestamp >= 3600:
        # # if cryptoPair.pair == "SHIBUSDT":
        # # print("Wykonuje zlecenie sprzedazy dla shiby")
        # # buy_orders = [order for order in cryptoPair.active_orders if order.order_type == "BUY" and order.strategy == "A"]
        # crypto_allocations = self.calculate_crypto_for_all_strategies(cryptoPair)
        
        # crypto_for_strategy = crypto_allocations.get("Strategy A")
        # print(crypto_for_strategy)
        
        
        
        # # # Obliczenie ilości sprzedaży na podstawie liczby wcześniejszych zleceń kupna
        # # sell_quantity = ((pow(2, len(buy_orders))) * (cryptoPair.min_notional / self.get_price(cryptoPair.pair)))

        # if crypto_for_strategy * buy_price > cryptoPair.min_notional:

        #     # Wywołanie funkcji monitorującej zlecenie sprzedaży z podanymi parametrami
        #     await self.monitor_sell_and_buy_back(
        #         cryptoPair=cryptoPair,
        #         sell_quantity=crypto_for_strategy,
        #         sell_price=sell_price,
        #         buy_price=buy_price,
        #         strategy="A"
        #     )
        # # else:
        # #     print(f"Zbyt wcześnie na kolejne zlecenie sprzedaży dla {cryptoPair.pair}.")
    
    
    async def crazy_girl(self, cryptoPair: CryptoPair, strategy: TradeStrategy):
        
        logger.debug(f"Strategy: {strategy.name} for {cryptoPair.pair} state {cryptoPair.current_state[CRAZY_GIRL]}")
        
        if cryptoPair.current_state[CRAZY_GIRL] == TradeState.MONITORING:
           
           
            buy_price, sell_price = self.calculate_buy_and_sell_price(
                crypto_pair=cryptoPair,
                strategy=strategy
            )
            

            quanitity_for_trading = float(cryptoPair.crypto_amount_free) * float(cryptoPair.trading_percentage) * float(cryptoPair.strategy_allocation[CRAZY_GIRL])
            
           
            sell_quantity = quanitity_for_trading * 0.5
    
            
            #tutaj sprawdzam min_notional dla odkupu gut !
            # Sprawdź, czy warunki do sprzedaży są spełnione
            if float(sell_quantity) * float(buy_price) < cryptoPair.min_notional:
              
                cryptoPair.sell_order_id = await self.sell(cryptoPair=cryptoPair, sell_quantity= sell_quantity, sell_price=sell_price, strategy=CRAZY_GIRL)
                
                if(cryptoPair.sell_order_id != None):
                    cryptoPair.buy_price = buy_price
                    cryptoPair.buy_quantity = sell_quantity
                    updated_allocation = float(float(cryptoPair.strategy_allocation[CRAZY_GIRL])) * ((float(sell_quantity) / float(quanitity_for_trading)))
                    cryptoPair.strategy_allocation[CRAZY_GIRL] = updated_allocation
                    logger.info(f"Złożono zlecenie sprzedaży dla {cryptoPair.pair} na cenie {sell_price}")
                
                    # Przechodzimy do stanu WAITING_FOR_SELL
                    cryptoPair.current_state[CRAZY_GIRL] = TradeState.WAITING_FOR_SELL
                    logger.debug(f"Stan {cryptoPair.current_state[CRAZY_GIRL]}")
            else:
                logger.error(f"Nie spełnione warunki sprzedaży")
                
                
          
        elif cryptoPair.current_state[CRAZY_GIRL] == TradeState.WAITING_FOR_SELL:
            
            status = self.get_order_status(cryptoPair.pair, cryptoPair.sell_order_id)


            logger.info("="*50)
            logger.info(f" Waiting for Sell Order Execution ".center(50, "="))
            logger.info("="*50)
            logger.info(f" Symbol       : {status['symbol']}")
            logger.info(f" Price        : {status['price']}")
            logger.info(f" Current price: {self.get_price(status['symbol'])}")
            logger.info(f" Quantity     : {status['origQty']}")
            logger.info(f" Total Amount : {float(status['origQty']) * float(status['price']):.2f} USD")
            logger.info(f" Order ID     : {status['orderId']}")
            logger.info("="*50)
            
           
           
                

            if status['status'] == 'FILLED':
                
                logger.info(f"Zlecenie sprzedaży {cryptoPair.sell_order_id} zostało zrealizowane. Składam zlecenie kupna.")
                
                # ###############################################
                # cryptoPair.remove_order_by_id(sell_order_id)
                # ###############################################
                
                #odkupujemy 
                order_id = await self.buy(cryptoPair=cryptoPair, buy_quantity=cryptoPair.buy_quantity, buy_price=cryptoPair.buy_price, strategy=CRAZY_GIRL)

                if order_id != None:
                    logger.debug("Złożono zlecenie kupna!")
                    cryptoPair.current_state[CRAZY_GIRL] = TradeState.MONITORING
                    cryptoPair.strategy_allocation[CRAZY_GIRL]
                else:
                    logger.error("Nie udało się złożyć zlecenia kupna!")
            
           
           
       
            
            
    
    async def sensible_guy(self, cryptoPair: CryptoPair, strategy: TradeStrategy):
        
        logger.debug(f"Strategy: {strategy.name} for {cryptoPair.pair}")
        
        buy_price, sell_price = self.calculate_buy_and_sell_price(
            crypto_pair=cryptoPair,
            strategy=strategy
        )
        
        
    
    
    

   