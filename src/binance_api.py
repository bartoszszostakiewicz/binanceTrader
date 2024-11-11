import asyncio
import os
from decimal import Decimal, ROUND_DOWN, InvalidOperation
from typing import Dict
from binance.client import Client
from datetime import datetime
from data_classes import CryptoPair, Order, TradeStrategy
from colorama import Fore, Style, init
import requests
from constants import *
from logger import logger


class BinanceTrader:

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

    def get_price(self, symbol: str) -> dict:
        """Pobiera aktualną cenę dla danego symbolu z Binance API."""
        try:
            price_data = self.client.get_symbol_ticker(symbol=symbol)
            return price_data  # Zwracamy wynik jako słownik z ceną
        except Exception as e:
            logger.exception(f"Błąd podczas pobierania ceny dla symbolu {symbol}: {e}")
            return {}

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
            response = self.client.cancel_order(
                symbol=trading_pair,
                orderId=order_id
            )
            logger.info(f"Order {order_id} for {trading_pair} has been canceled.")
            return response
        except Exception as e:
            # Handle errors by logging them and returning None if the cancellation fails
            logger.exception(f"Failed to cancel order {order_id} for {trading_pair}. Error: {e}")
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
            logger.exception(f"Error retrieving wallet balances: {e}")
            return {}

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
                    price = self.get_price(currency + "USDT")  # Assuming crypto pairs are listed in USDT to jest zle
                    total_crypto_value += total_amount * price
                except Exception as e:
                    logger.exception(f"Failed to fetch price for {currency}: {str(e)}")
        
        logger.debug(f"Crypto value      :{total_crypto_value}")
        logger.info(f"Stablecoins value :{total_stablecoins_value}")
        
        return total_stablecoins_value, total_crypto_value

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
                        logger.debug(f"Step size for {symbol} = {f['stepSize']}")
                        return float(f['stepSize'])
        logger.error(f"Failed to retrieve step size for {symbol}")
        return None

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

    def calculate_buy_and_sell_price(self, crypto_pair: CryptoPair, strategy: TradeStrategy):
        """
        Calculates the buy and sell prices based on the buy increase indicator and target profit.
        
        Args:
            crypto_pair (CryptoPair): An object containing information about the cryptocurrency pair.
            strategy(TradeStrategy): Strategy for which the buy and sell price are calculated.
            
        Returns:
            tuple: (buy_price, sell_price) - the rounded buy and sell prices according to tick_size.
        """
        
        tick_size = crypto_pair.tick_size
        current_price = self.get_price(crypto_pair.pair)
        round_price = lambda price, tick_size: round(price / tick_size) * tick_size
        

        sell_price = round_price(price=(current_price * (1 + strategy.buy_increase_indicator)), tick_size=tick_size)
        buy_price = round_price(price=(strategy.profit_target * current_price), tick_size=tick_size)

                
        return buy_price, sell_price

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
   
    async def limit_order(self, cryptoPair: CryptoPair, quantity: float, price: float, side: str):

        try:
            # Set price precision according to tick_size
            tick_size_decimal = Decimal(str(cryptoPair.tick_size))
            price_precision = abs(tick_size_decimal.as_tuple().exponent)
            price = Decimal(price).quantize(tick_size_decimal, rounding=ROUND_DOWN)
            formatted_price = "{:.{}f}".format(price, price_precision)  # Format price with tick_size precision
            
            # Set quantity precision according to step_size
            step_size_decimal = Decimal(str(cryptoPair.step_size))
            quantity_precision = abs(step_size_decimal.as_tuple().exponent)
            quantity = Decimal(quantity).quantize(step_size_decimal, rounding=ROUND_DOWN)
            
            # Jeśli step_size = 1.0, wymuszenie liczby całkowitej na ilości
            if cryptoPair.step_size == 1:
                quantity = int(quantity)
                formatted_quantity = str(quantity)
            else:
                formatted_quantity = "{:.{}f}".format(quantity, quantity_precision)  # Format quantity with step_size precision

            # Check if the transaction value meets the min_notional requirement
            if Decimal(formatted_quantity) * Decimal(formatted_price) < Decimal(str(cryptoPair.min_notional)):
                logger.error(f"Order for {cryptoPair.pair} cannot be placed: transaction value ({Decimal(formatted_quantity) * Decimal(formatted_price)}) is less than min_notional ({cryptoPair.min_notional}).")
                return None, None

            # Debugging print statements
            logger.debug(f"Formatted price: {formatted_price}, type: {type(formatted_price)}")
            logger.debug(f"Formatted quantity: {formatted_quantity}, type: {type(formatted_quantity)}")
            
            # Logowanie parametrów i ich typów przed wywołaniem create_order
            logger.debug(f"Placing order for {cryptoPair.pair}: {side.capitalize()} order with price: {formatted_price} (type: {type(formatted_price)}), quantity: {formatted_quantity} (type: {type(formatted_quantity)})")

            # Przekazujemy sformatowane wartości jako stringi
            order = self.client.create_order(
                symbol=cryptoPair.pair,
                side=side,
                type=Client.ORDER_TYPE_LIMIT,
                timeInForce=Client.TIME_IN_FORCE_GTC,
                quantity=formatted_quantity,
                price=str(formatted_price),
            )
            logger.info(f"{side.capitalize()} order placed at {formatted_price}!")
            return order
        
        except Exception as e:
            logger.error(f"Error placing {side} order for {cryptoPair.pair}: {e}")
            return None

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

    async def crazy_girl(self, cryptoPair: CryptoPair, strategy: TradeStrategy, timeout: int = 1000, cooldown_period = 3600):
            
        logger.debug(f"Strategy: {strategy.name} for {cryptoPair.pair} - Current state: {cryptoPair.current_state[CRAZY_GIRL]}")
        
        if cryptoPair.current_state[CRAZY_GIRL] == TradeState.MONITORING:
            
            ######################################################################3
            #nie działa,
            # Retrieve the last active sell order for the CRAZY_GIRL strategy
            last_sell_order = next(
                (order for order in cryptoPair.active_orders if order.strategy == CRAZY_GIRL and order.order_type == Client.SIDE_SELL), 
                None
            )
            
            
            # Check if cooldown period has elapsed since the last sell order
            if last_sell_order:
                logger.debug(f"Last sell order for {cryptoPair.pair}: {last_sell_order}")
                last_order_time = datetime.fromtimestamp(int(last_sell_order.timestamp) / 1000)
                elapsed_time = datetime.now() - last_order_time
                if elapsed_time < cooldown_period:
                    logger.info(f"Cooldown active for {cryptoPair.pair} - Waiting {cooldown_period - elapsed_time} before next order.")
                    return  # Exit if within cooldown period
            else:
                logger.debug(f"Last order is none!")
            ###################################################################
            
            buy_price, sell_price = self.calculate_buy_and_sell_price(
                crypto_pair=cryptoPair,
                strategy=strategy
            )
            
            quantity_for_trading = float(cryptoPair.crypto_amount_free) * float(cryptoPair.trading_percentage) * float(cryptoPair.strategy_allocation[CRAZY_GIRL])
            sell_quantity = quantity_for_trading 
            
            price_order = float(sell_quantity) * float(buy_price)
            
            # Check if the order value is less than min_notional
            if price_order < cryptoPair.min_notional:
                logger.info(f"Cannot place sell order for {cryptoPair.pair}: order value ({price_order}) is less than min_notional ({cryptoPair.min_notional}).")
                logger.debug(f"Required min_notional for {cryptoPair.pair}: is {cryptoPair.min_notional}, but calculated order value is {price_order}.")
                
            # Check if the order value exceeds available balance
            elif price_order >= cryptoPair.value:
                logger.info(f"Cannot place sell order for {cryptoPair.pair}: order value ({price_order}) exceeds available balance ({cryptoPair.value}).")
                logger.debug(f"Calculated order value for {cryptoPair.pair}: ({price_order}) is higher than available balance ({cryptoPair.value}).")

            else:
                sell_order = await self.limit_order(
                    cryptoPair=cryptoPair,
                    quantity=sell_quantity,
                    price=sell_price,
                    side=Client.SIDE_SELL
                )

                if sell_order:
                    cryptoPair.add_order(
                        Order(
                            symbol=sell_order['symbol'],
                            order_id=sell_order['orderId'],
                            sell_price=sell_order['price'],
                            buy_price= buy_price,
                            order_type=sell_order['side'],
                            amount=float(sell_order['origQty']),
                            timestamp=sell_order['workingTime'],
                            strategy=CRAZY_GIRL,
                        )    
                    )
                    
                    logger.info(f"Sell order placed for {cryptoPair.pair} at price {sell_price}")

                    # Setting state to WAITING_FOR_SELL
                    cryptoPair.current_state[CRAZY_GIRL] = TradeState.WAITING_FOR_SELL
                    logger.debug(f"State after placing sell order for {cryptoPair.pair}: {cryptoPair.current_state[CRAZY_GIRL]}")

        elif cryptoPair.current_state[CRAZY_GIRL] == TradeState.WAITING_FOR_SELL:
            
            logger.debug(f"Active orders: {cryptoPair.active_orders}")
            
            # Retrieving active sell order from `activeOrders`
            active_order = next(
                (order for order in cryptoPair.active_orders if order.strategy == CRAZY_GIRL), 
                None
            )
            
            status = self.get_order_status(cryptoPair.pair, order_id=active_order.order_id)
            
            # Checking if time has exceeded timeout
            elapsed_time = (datetime.now() - datetime.fromtimestamp(int(active_order.timestamp) / 1000)).total_seconds()
            
            if elapsed_time > timeout:
                # Canceling the sell order due to timeout
                canceled_order = await self.cancel_order(cryptoPair.pair, active_order.order_id)
                if canceled_order:
                    cryptoPair.move_order_to_completed(order_id=active_order.order_id)
                    logger.warning(f"Sell order {active_order.order_id} for {cryptoPair.pair} canceled due to timeout.")
                    cryptoPair.current_state[CRAZY_GIRL] = TradeState.MONITORING
                else:
                    logger.error(f"Failed to cancel sell order {active_order.order_id} for {cryptoPair.pair} due to timeout.")
                return

            # Logging order status information
            logger.info("="*50)
            logger.info(f" Waiting for sell order execution for {cryptoPair.pair} ".center(50, "="))
            logger.info("="*50)
            logger.info(f" Symbol       : {status['symbol']}")
            logger.info(f" Price        : {status['price']}")
            logger.info(f" Current Price: {self.get_price(status['symbol'])}")
            logger.info(f" Quantity     : {status['origQty']}")
            logger.info(f" Value        : {float(status['origQty']) * float(status['price']):.2f} USD")
            logger.info(f" Order ID     : {status['orderId']}")
            logger.info("="*50)

            if status['status'] == 'FILLED':
                logger.info(f"Sell order {active_order.order_id} for {cryptoPair.pair} completed. Placing buy order.")

                cryptoPair.move_order_to_completed(active_order.order_id)
                
                if active_order:
                    
                    buy_order = await self.limit_order(
                        cryptoPair=cryptoPair, 
                        quantity=active_order.amount, 
                        price=active_order.buy_price, 
                        side=Client.SIDE_BUY
                    )

                    if buy_order:
                        logger.info(f"Buy order placed for {cryptoPair.pair}!")
                        cryptoPair.current_state[CRAZY_GIRL] = TradeState.MONITORING
                        cryptoPair.add_order(
                            Order(
                                symbol=buy_order['symbol'],
                                order_id=buy_order['orderId'],
                                order_type=buy_order['side'],
                                amount=float(buy_order['origQty']),
                                timestamp=datetime.fromtimestamp(float(buy_order['workingTime'])/100).strftime('%Y-%m-%d %H:%M:%S'),
                                strategy=CRAZY_GIRL,
                            )    
                        )
                        logger.debug(f"Current strategy allocation for {cryptoPair.pair}: {cryptoPair.strategy_allocation[CRAZY_GIRL]}")
                    else:
                        logger.error(f"Failed to place buy order for {cryptoPair.pair}!")

    async def sensible_guy(self, cryptoPair: CryptoPair, strategy: TradeStrategy, timeout: int = 1000):
        
        logger.debug(f"Strategy: {strategy.name} for {cryptoPair.pair} state {cryptoPair.current_state[SENSIBLE_GUY]}")

    async def poor_orphan(self, cryptoPair: CryptoPair, strategy: TradeStrategy, timeout: int = 1000):
        
        logger.debug(f"Strategy: {strategy.name} for {cryptoPair.pair} state {cryptoPair.current_state[SENSIBLE_GUY]}")
