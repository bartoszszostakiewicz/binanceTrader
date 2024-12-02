import asyncio
import os
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Optional
from binance.client import Client
from datetime import datetime, timedelta
from data_classes import CryptoPair, CryptoPairs, Order
from observable import TradeStrategy
from colorama import Fore, Style, init
from globals import *
from logger import logger


class BinanceManager:

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(BinanceManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:

        if self._initialized:
            return
        self._initialized = True 

        try:
            # Attempt to retrieve API keys from environment variables
            api_key = os.getenv(BINANCE_API_KEY)
            secret_key = os.getenv(BINANCE_SECRET_KEY)

            if not api_key or not secret_key:
                raise ValueError("Binance API keys are missing. Please check that they are set in environment variables.")

            # Initialize the Binance client
            self.client = Client(api_key, secret_key)
            self.orders_id = set()

            logger.debug(f"Binance Trader successfully intializated!")

            # Initialize colorama for automatic console color reset
            init(autoreset=True)

        except ValueError as ve:
            logger.error(f"Initialization error: {ve}")
        except Exception as e:
            logger.exception(f"Error initializing Binance client: {e}")

    def get_price(self, symbol: str) -> dict:
        """Gets the current price for a given symbol from the Binance API."""
        try:
            price_data = self.client.get_symbol_ticker(symbol=symbol)
            return price_data  # Zwracamy wynik jako słownik z ceną
        except Exception as e:
            logger.exception(f"Error getting price for symbol {symbol}: {e}")
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
            for filter in symbol_info[FILTERS]:
                if filter[FILTER_TYPE] == 'PRICE_FILTER':
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
            balances = account_info[BALANCES]

            wallet_balances = {}
            for balance in balances:
                asset = balance[ASSET]
                free_amount = balance[FREE]
                locked_amount = balance[LOCKED]

                # Only include assets with non-zero balance
                if float(free_amount) > 0 or float(locked_amount) > 0:
                    wallet_balances[asset] = {
                        FREE: free_amount,
                        LOCKED: locked_amount
                    }

            return wallet_balances
        except Exception as e:
            logger.exception(f"Error retrieving wallet balances: {e}")
            return {}

    def get_value(self, pair: str, amount: float) -> float:
        price = self.get_price(pair) 
        return float(amount) * price

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
            free_amount = float(balance.get(FREE, 0))
            locked_amount = float(balance.get(LOCKED, 0))
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
        logger.debug(f"Stablecoins value :{total_stablecoins_value}")

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
            return float(ticker[PRICE])
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
        for s in exchange_info[SYMBOLS]:
            if s[SYMBOL] == symbol:
                for f in s[FILTERS]:
                    if f[FILTER_TYPE] == LOT_SIZE:
                        logger.debug(f"Step size for {symbol} = {f[STEP_SIZE]}")
                        return float(f[STEP_SIZE])
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

        for s in exchange_info[SYMBOLS]:
            if s[SYMBOL] == symbol:
                for f in s[FILTERS]:
                    if f[FILTER_TYPE] == 'NOTIONAL':
                        min_notional = f[MIN_NOTIONAL]
                        logger.debug(f"Min_notional for symbol {symbol}: {min_notional}")
                        return float(min_notional)

        # Print message if min_notional is not found for the symbol
        logger.error(f"Min_notional not found for symbol {symbol}")
        return None

    def analyze_orders(self, symbol: str, add_missing_orders: bool = False) -> Dict[str, float]:
        """
        Fetch and analyze active and historical orders for a given symbol from Binance.
        Returns counts, quantities, and total amounts for buy and sell orders, including estimated fees.
        """
        buy_count = sell_count = 0
        buy_quantity = sell_quantity = 0.0

        pending_buy_count = pending_sell_count = 0
        pending_buy_quantity = pending_sell_quantity = 0.0

        pending_total_buy_value = pending_total_sell_value = 0.0

        total_buy_value = total_sell_value = 0.0
        estimated_buy_fee = estimated_sell_fee = 0.0

        # Fetch all historical orders and calculate filled quantities, values, and estimated fees
        all_orders = self.client.get_all_orders(symbol=symbol)

        for order in all_orders:

            if order[STATUS] == FILLED:
                executed_quantity = float(order[EXECUTED_QTY])
                price = float(order[PRICE])

                if price == 0:
                    if executed_quantity > 0:
                        price = float(order[CUMMULATIVE_QUOTE_QTY]) / executed_quantity

                order_value = executed_quantity * price

                if order[SIDE] == BUY:
                    fee = order_value * FEE_BUY_BINANCE_VALUE

                    buy_count += 1
                    buy_quantity += executed_quantity
                    total_buy_value += order_value
                    estimated_buy_fee += fee

                    if add_missing_orders:
                        from firebase import FirebaseManager
                        FirebaseManager().add_order_to_firebase(
                            Order(
                                symbol=symbol,
                                order_id=order[ORDER_ID],
                                order_type=order[SIDE],
                                amount=executed_quantity,
                                sell_price=0.0,
                                buy_price=price,
                                timestamp=order[TIME],
                                strategy='',
                                status=order[STATUS],
                                profit=0,
                            )
                        )

                elif order[SIDE] == SELL:
                    fee = order_value * FEE_SELL_BINANCE_VALUE

                    sell_count += 1
                    sell_quantity += executed_quantity
                    total_sell_value += order_value
                    estimated_sell_fee += fee

                    if add_missing_orders:
                        from firebase import FirebaseManager
                        FirebaseManager().add_order_to_firebase(
                            Order(
                                symbol=symbol,
                                order_id=order[ORDER_ID],
                                order_type=order[SIDE],
                                amount=executed_quantity,
                                sell_price=price,
                                buy_price=0.0,
                                timestamp=order[TIME],
                                strategy='',
                                status=order[STATUS],
                                profit=0,
                            )
                        )

            elif order[STATUS] == NEW:
                origQty_quantity = float(order[ORIG_QTY])
                price = float(order[PRICE])
                order_value = origQty_quantity * price

                if order[SIDE] == BUY:

                    fee = order_value * FEE_BUY_BINANCE_VALUE

                    pending_buy_count += 1
                    pending_buy_quantity += origQty_quantity
                    pending_total_buy_value += order_value
                    estimated_buy_fee += fee
                elif order[SIDE] == SELL:

                    fee = order_value * FEE_SELL_BINANCE_VALUE

                    pending_sell_count += 1
                    pending_sell_quantity += origQty_quantity
                    pending_total_sell_value += order_value
                    estimated_sell_fee += fee

                if add_missing_orders:
                    from firebase import FirebaseManager
                    FirebaseManager().add_order_to_firebase(
                        Order(
                            symbol=symbol,
                            order_id=order[ORDER_ID],
                            order_type=order[SIDE],
                            amount=float(order[ORIG_QTY]),
                            sell_price=float(order[PRICE]) if order[SIDE] == SELL else 0.0,
                            buy_price=float(order[PRICE]) if order[SIDE] == BUY else 0.0,
                            timestamp=order[TIME],
                            strategy='',
                            status=order[STATUS],
                            profit=0,
                        )
                    )


        COLUMN_WIDTH = 50
        SEPARATOR = " | "


        missing_quantity = max(0, (sell_quantity + pending_sell_quantity) - (buy_quantity + pending_buy_quantity))


        missing_value = missing_quantity * self.get_price(symbol=symbol)

        profit = (
            total_sell_value -
            total_buy_value -
            (estimated_buy_fee + estimated_sell_fee)
        )

        estimated_profit = (
            (total_sell_value + pending_total_sell_value) -
            (total_buy_value + pending_total_buy_value) -
            (estimated_buy_fee + estimated_sell_fee)
        )


        estimated_profit -= missing_value


        logger.info("=" * (2 * COLUMN_WIDTH + len(SEPARATOR)))
        logger.info(f"Summary for {symbol} ".center(2 * COLUMN_WIDTH + len(SEPARATOR), "="))
        logger.info("=" * (2 * COLUMN_WIDTH + len(SEPARATOR)))


        logger.info(f"{'Completed Orders':<{COLUMN_WIDTH}}{'Pending Orders':<{COLUMN_WIDTH}}")
        logger.info("-" * (2 * COLUMN_WIDTH + len(SEPARATOR)))


        logger.info(f"Buy Orders Count           : {buy_count:<{COLUMN_WIDTH - 30}}{SEPARATOR:<{COLUMN_WIDTH - 40}}Pending Buy Orders Count   : {pending_buy_count}")
        logger.info(f"Sell Orders Count          : {sell_count:<{COLUMN_WIDTH - 30}}{SEPARATOR:<{COLUMN_WIDTH - 40}}Pending Sell Orders Count  : {pending_sell_count}")
        logger.info(f"Total Bought Quantity      : {buy_quantity:<{COLUMN_WIDTH - 30}.8f}{SEPARATOR:<{COLUMN_WIDTH - 40}}Pending Buy Quantity       : {pending_buy_quantity:.8f}")
        logger.info(f"Total Sold Quantity        : {sell_quantity:<{COLUMN_WIDTH - 30}.8f}{SEPARATOR:<{COLUMN_WIDTH - 40}}Pending Sell Quantity      : {pending_sell_quantity:.8f}")
        logger.info(f"Total Bought Value         : {total_buy_value:<{COLUMN_WIDTH - 30}.8f}{SEPARATOR:<{COLUMN_WIDTH - 40}}Pending Total Buy Value    : {pending_total_buy_value:.8f}")
        logger.info(f"Total Sold Value           : {total_sell_value:<{COLUMN_WIDTH - 30}.8f}{SEPARATOR:<{COLUMN_WIDTH - 40}}Pending Total Sell Value   : {pending_total_sell_value:.8f}")
        logger.info(f"Estimated Buy Fees         : {estimated_buy_fee:<{COLUMN_WIDTH - 30}.8f}")
        logger.info(f"Estimated Sell Fees        : {estimated_sell_fee:<{COLUMN_WIDTH - 30}.8f}")

        logger.info(f"Missing Quantity           : {missing_quantity:.8f}")
        logger.info(f"Value of Missing Quantity  : {missing_value:.8f} USD")
        logger.info(f"Estimated Profit           : {estimated_profit:.8f} USD")


        return {
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_bought_quantity": buy_quantity,
            "total_sold_quantity": sell_quantity,
            "total_buy_value": total_buy_value,
            "total_sell_value": total_sell_value,
            "quantity_missing": (sell_quantity - buy_quantity),
            "estimated_buy_fee": estimated_buy_fee,
            "estimated_sell_fee": estimated_sell_fee
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

    def fetch_pairs(self) -> CryptoPairs: 
        global PAIRS
        wallet = self.get_wallet_balances()
        crypto_pairs = CryptoPairs()

        for pair_name, _ in PAIRS.pairs.items():
            if pair_name[:-4] in wallet:
                balance = wallet[pair_name[:-4]]

                free_value = self.get_value(pair_name, balance[FREE])
                locked_value = self.get_value(pair_name, balance[LOCKED])

                logger.debug(f"Free   value for {pair_name}: {free_value}")
                logger.debug(f"Locked value for {pair_name}: {locked_value}")

                total_value = free_value + locked_value

                min_notional = self.get_min_notional(pair_name)

                crypto_pair = CryptoPair(
                    pair=pair_name,
                    crypto_amount_free=free_value,
                    crypto_amount_locked=locked_value,
                    orders=[],
                    min_notional=min_notional,
                    profit=0,
                    value=total_value,
                    tick_size=self.get_tick_size(symbol=pair_name),
                    step_size=self.get_step_size(symbol=pair_name)
                )

                crypto_pairs.pairs.append(crypto_pair)

        return crypto_pairs

    def get_crypto_amounts(self, pair_name: str) -> dict:
        """
        Fetches the `crypto_amount_free` and `crypto_amount_locked` for a given cryptocurrency pair 
        using cached wallet balances.

        Args:
            pair_name (str): The name of the cryptocurrency pair (e.g., 'BTCUSDT').

        Returns:
            dict: A dictionary containing `crypto_amount_free` and `crypto_amount_locked`.
        """

        wallet = self.get_wallet_balances()

        crypto_symbol = pair_name[:-4]  

        if crypto_symbol in wallet:
            balance = wallet[crypto_symbol]
            return {
                CRYPTO_AMOUNT_FREE: balance[FREE],
                CRYPTO_AMOUNT_LOCKED: balance[LOCKED]
            }
        else:
            return {
                CRYPTO_AMOUNT_FREE: 0,
                CRYPTO_AMOUNT_LOCKED: 0
            }

    async def limit_order(self, cryptoPair: CryptoPair, quantity: float, price: float, side: str):

        try:
            tick_size_decimal = Decimal(str(cryptoPair.tick_size))
            price_precision = abs(tick_size_decimal.as_tuple().exponent)
            price = Decimal(price).quantize(tick_size_decimal, rounding=ROUND_DOWN)
            formatted_price = "{:.{}f}".format(price, price_precision)  

            step_size_decimal = Decimal(str(cryptoPair.step_size))
            quantity_precision = abs(step_size_decimal.as_tuple().exponent)
            quantity = Decimal(quantity).quantize(step_size_decimal, rounding=ROUND_DOWN)

            if cryptoPair.step_size == 1:
                quantity = int(quantity)
                formatted_quantity = str(quantity)
            else:
                formatted_quantity = "{:.{}f}".format(quantity, quantity_precision)

            if Decimal(formatted_quantity) * Decimal(formatted_price) < Decimal(str(cryptoPair.min_notional)):
                logger.error(f"Order for {cryptoPair.pair} cannot be placed: transaction value ({Decimal(formatted_quantity) * Decimal(formatted_price)}) is less than min_notional ({cryptoPair.min_notional}).")
                return None, None

            logger.debug(f"Formatted price: {formatted_price}, type: {type(formatted_price)}")
            logger.debug(f"Formatted quantity: {formatted_quantity}, type: {type(formatted_quantity)}")

            logger.debug(f"Placing order for {cryptoPair.pair}: {side.capitalize()} order with price: {formatted_price} (type: {type(formatted_price)}), quantity: {formatted_quantity} (type: {type(formatted_quantity)})")

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

    def print_order(self, pair: str, status):
        side = SELL if status[SIDE] == SELL else BUY if status[SIDE] == BUY else None

        logger.info("="*50)
        logger.info(f" Waiting for {side} order execution for {pair} ".center(50, "="))
        logger.info("="*50)
        logger.info(f" Symbol       : {status[SYMBOL]}")
        logger.info(f" Price        : {status[PRICE]}")
        logger.info(f" Current Price: {self.get_price(status[SYMBOL]):.10f}")
        logger.info(f" Quantity     : {status[ORIG_QTY]}")
        logger.info(f" Value        : {float(status[ORIG_QTY]) * float(status[PRICE]):.2f} USD")
        logger.info(f" Order ID     : {status[ORDER_ID]}")

    def monitor_buy_orders(self, cryptoPair: CryptoPair, strategy: TradeStrategy):
        """
        Monitors all buy orders for a crypto pair. Updates Firebase if statuses change.

        Parameters:
            cryptoPair (CryptoPair): The crypto pair object being monitored.
            strategy (TradeStrategy): The strategy object associated with the buy orders.
        """
        global MONITORING

        from firebase import FirebaseManager

        buy_orders = [
            order for order in cryptoPair.orders
            if order.strategy == strategy.name and order.order_type == Client.SIDE_BUY
        ]

        active_buy_counter = 0

        for order in buy_orders:
            current_status = self.get_order_status(cryptoPair.pair, order_id=order.order_id)

            if current_status[STATUS] != order.status:

                order.status = current_status[STATUS]

                from firebase import FirebaseManager
                FirebaseManager().add_order_to_firebase(
                    cryptoPair.set_status(order_id=order.order_id, status=FILLED)
                )

                if order.status == FILLED:
                    logger.info(f"Buy order {order.order_id} for {cryptoPair.pair} filled.")
                else:
                    active_buy_counter += 1
            elif current_status[STATUS] != FILLED:
                if MONITORING.show_buy_orders:
                    self.print_order(pair=cryptoPair.pair, status=current_status)

            logger.info(f"Monitoring buy orders for {cryptoPair.pair} ({strategy.name}). Total buy orders: {active_buy_counter}")

    async def handle_strategies(self, cryptoPair: CryptoPair):
        global STRATEGIES
        global PAIRS
        strategy_list = [STRATEGIES.strategies[POOR_ORPHAN], STRATEGIES.strategies[CRAZY_GIRL], STRATEGIES.strategies[SENSIBLE_GUY]]

        tasks = []

        for strategy in strategy_list:
            allocation = float(PAIRS.pairs[cryptoPair.pair]['strategy_allocation'][strategy.name])
            if allocation > 0:
                logger.debug(f"Creating task for strategy {strategy.name} on pair {cryptoPair.pair} with allocation {allocation}")

                task = asyncio.create_task(
                    self.process_strategy(
                        cryptoPair=cryptoPair,
                        strategy=strategy
                    )
                )
            tasks.append(task)
        else:
            logger.debug(f"Skipping strategy {strategy.name} for pair {cryptoPair.pair} due to zero allocation")


        await asyncio.gather(*tasks)

    async def process_strategy(self, cryptoPair: CryptoPair, strategy: TradeStrategy):
        global PAIRS

        logger.debug(f"Strategy: {strategy.name} for {cryptoPair.pair} - Current state: {cryptoPair.current_state[strategy.name]}")

        self.monitor_buy_orders(cryptoPair=cryptoPair, strategy=strategy)

        if cryptoPair.current_state[strategy.name] == TradeState.MONITORING:

            buy_price, sell_price = self.calculate_buy_and_sell_price(
                crypto_pair=cryptoPair,
                strategy=strategy
            )

            quantity_for_trading = 0

            if strategy.name == CRAZY_GIRL:
                quantity_for_trading = float(cryptoPair.crypto_amount_free) * float(PAIRS.pairs[cryptoPair.pair]["trading_percentage"]) * float(PAIRS.pairs[cryptoPair.pair]['strategy_allocation'][strategy.name])
            elif strategy.name == SENSIBLE_GUY:
                quantity_for_trading = float(cryptoPair.crypto_amount_free) * float(PAIRS.pairs[cryptoPair.pair]["trading_percentage"]) * float(PAIRS.pairs[cryptoPair.pair]['strategy_allocation'][strategy.name])
            elif strategy.name == POOR_ORPHAN:
                quantity_for_trading = (cryptoPair.min_notional + PRICE_TRESHOLD) / self.get_price(cryptoPair.pair)

            logger.debug(f"Quantity_for_trading = {quantity_for_trading}.")

            sell_quantity = quantity_for_trading
            price_order = float(sell_quantity) * float(buy_price)

            logger.debug(f"Crypto free   amount: {cryptoPair.crypto_amount_free} {cryptoPair.pair[:-4]}")
            logger.debug(f"Crypto locked amount: {cryptoPair.crypto_amount_locked} {cryptoPair.pair[:-4]}")

            # Check if the order value is less than min_notional
            if price_order < cryptoPair.min_notional:
                logger.debug(f"Cannot place sell order for {cryptoPair.pair}: order value ({price_order}) is less than min_notional ({cryptoPair.min_notional}).")
                logger.debug(f"Required min_notional for {cryptoPair.pair}: is {cryptoPair.min_notional}, but calculated order value is {price_order}.")

            # Check if the order value exceeds available balance

            elif price_order >= cryptoPair.value:
                logger.debug(f"Cannot place sell order for {cryptoPair.pair}: order value ({price_order}) exceeds available balance ({cryptoPair.value}).")
                logger.debug(f"Calculated order value for {cryptoPair.pair}: ({price_order}) is higher than available balance ({cryptoPair.value}).")

            else:
                sell_order = await self.limit_order(
                    cryptoPair=cryptoPair,
                    quantity=sell_quantity,
                    price=sell_price,
                    side=Client.SIDE_SELL
                )

                if sell_order:
                    from firebase import FirebaseManager
                    FirebaseManager().add_order_to_firebase(
                        cryptoPair.add_order(
                            Order(
                                symbol=sell_order[SYMBOL],
                                order_id=sell_order[ORDER_ID],
                                sell_price=sell_order[PRICE],
                                buy_price= buy_price,
                                order_type=sell_order[SIDE],
                                amount=float(sell_order[ORIG_QTY]),
                                timestamp=sell_order[WORKING_TIME],
                                strategy=strategy.name,
                                status=sell_order[STATUS],
                                profit = 0,
                            )
                        )
                    )

                    logger.info(f"Sell order placed for {cryptoPair.pair} at price {sell_price}")

                    # Setting state to SELLING
                    cryptoPair.current_state[strategy.name] = TradeState.SELLING
                    logger.debug(f"State after placing sell order for {cryptoPair.pair}: {cryptoPair.current_state[strategy.name]}")

        elif cryptoPair.current_state[strategy.name] == TradeState.SELLING:

            logger.debug(f"Active orders count: {len(cryptoPair.orders)}")

            # Retrieving active sell order from `activeOrders`
            active_order: Optional[Order] = max(
                (
                    order for order in cryptoPair.orders 
                    if order.strategy == strategy.name and order.timestamp
                ),
                key=lambda order: (
                    datetime.strptime(order.timestamp, '%Y-%m-%d %H:%M:%S').timestamp() 
                    if isinstance(order.timestamp, str) else order.timestamp
                ),
                default=None
            )

            status = self.get_order_status(cryptoPair.pair, order_id=active_order.order_id)

            # Checking if time has exceeded timeout
            elapsed_time = (datetime.now() - datetime.fromtimestamp(int(active_order.timestamp) / 1000)).total_seconds()

            self.print_order(cryptoPair.pair, status=status)

            if elapsed_time > strategy.timeout:
                # Canceling the sell order due to timeout
                canceled_order = await self.cancel_order(cryptoPair.pair, active_order.order_id)
                if canceled_order:
                    from firebase import FirebaseManager
                    FirebaseManager().add_order_to_firebase(
                        cryptoPair.set_status(order_id=active_order.order_id, status=CANCELED)
                    )
                    logger.warning(f"Sell order {active_order.order_id} for {cryptoPair.pair} canceled due to timeout.")
                    cryptoPair.current_state[strategy.name] = TradeState.COOLDOWN
                else:
                    logger.error(f"Failed to cancel sell order {active_order.order_id} for {cryptoPair.pair} due to timeout.")
                return
            else:
                logger.info(f" Expired      : {strategy.timeout - elapsed_time}")
            logger.info("="*50)

            if status[STATUS] == FILLED:
                logger.info(f"Sell order {active_order.order_id} for {cryptoPair.pair} completed. Placing buy order.")


                from firebase import FirebaseManager
                FirebaseManager().add_order_to_firebase(
                    cryptoPair.set_status(order_id=active_order.order_id, status=FILLED)
                )


                if active_order:

                    buy_order = await self.limit_order(
                        cryptoPair=cryptoPair,
                        quantity=active_order.amount,
                        price=active_order.buy_price,
                        side=Client.SIDE_BUY
                    )

                    if buy_order:

                        logger.info(f"Buy order placed for {cryptoPair.pair}!")
                        cryptoPair.current_state[strategy.name] = TradeState.COOLDOWN
                        sell_fee = float(buy_order[ORIG_QTY]) * float(active_order.sell_price) * float(FEE_SELL_BINANCE_VALUE)
                        buy_fee = float(buy_order[ORIG_QTY]) * float(active_order.buy_price) * float(FEE_SELL_BINANCE_VALUE)
                        total_fees = sell_fee + buy_fee
                        FirebaseManager().add_order_to_firebase(
                            cryptoPair.add_order(
                                Order(
                                    symbol=buy_order[SYMBOL],
                                    order_id=buy_order[ORDER_ID],
                                    order_type=buy_order[SIDE],
                                    amount=float(buy_order[ORIG_QTY]),
                                    sell_price=active_order.sell_price,
                                    buy_price=active_order.buy_price,
                                    timestamp=datetime.fromtimestamp(float(buy_order[WORKING_TIME])/100).strftime('%Y-%m-%d %H:%M:%S'),
                                    strategy=strategy.name,
                                    status=buy_order[STATUS],
                                    profit = ((float(active_order.sell_price)*float(buy_order[ORIG_QTY])) - (float(active_order.buy_price)*float(buy_order[ORIG_QTY]))) - total_fees,
                                )
                            )
                        )
                        logger.debug(f"Current strategy allocation for {cryptoPair.pair}: {PAIRS.pairs[cryptoPair.pair]['strategy_allocation'][strategy.name]}")
                    else:
                        logger.error(f"Failed to place buy order for {cryptoPair.pair}!")

        elif cryptoPair.current_state[strategy.name] == TradeState.COOLDOWN:

            last_sell_order: Optional[Order] = max(
                (
                    order 
                    for order in cryptoPair.orders 
                    if order.strategy == strategy.name 
                    and order.order_type == Client.SIDE_SELL 
                    and order.status == FILLED
                ),
                key=lambda order: order.timestamp,
                default=None
            )

            latest_buy_order: Optional[Order] = max(
                (
                    order
                    for order in cryptoPair.orders
                    if order.strategy == strategy.name
                    and order.order_type == Client.SIDE_BUY
                    and isinstance(order.timestamp, int)
                ),
                key=lambda order: order.timestamp,
                default=None
            )

            logger.debug(f"Latest active order id:{latest_buy_order.order_id}")

            if last_sell_order:
                last_order_time = datetime.fromtimestamp(int(last_sell_order.timestamp) / 1000)
                elapsed_time = datetime.now() - last_order_time

                cooldown_timedelta = timedelta(seconds=strategy.cooldown)

                if elapsed_time < cooldown_timedelta:
                    remaining_time = cooldown_timedelta - elapsed_time
                    logger.info(f"Cooldown active for {cryptoPair.pair} - Waiting {remaining_time} before next order.")
                else:
                    cryptoPair.current_state[strategy.name] = TradeState.MONITORING
            else:
                logger.debug(f"No last sell order found for {cryptoPair.pair}.")

            if latest_buy_order:
                logger.debug(f"Active buy order for {cryptoPair.pair}: {latest_buy_order}")

                status = self.get_order_status(cryptoPair.pair, order_id=latest_buy_order.order_id)
                if status[STATUS] == FILLED:
                    logger.info(f"Buy order {latest_buy_order.order_id} for {cryptoPair.pair} completed during cooldown.")

                    from firebase import FirebaseManager
                    FirebaseManager().add_order_to_firebase(
                        cryptoPair.set_status(order_id=latest_buy_order.order_id, status=FILLED)
                    )

                    cryptoPair.current_state[strategy.name] = TradeState.MONITORING
                    logger.info(f"Cooldown interrupted for {cryptoPair.pair}. Switching back to monitoring.")
