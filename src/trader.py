import asyncio
from copy import copy
from datetime import datetime, timedelta
from data_classes import CryptoPair, CryptoPairs, Order
from firebase import FirebaseManager
from globals import *
from binance_api import BinanceManager
from binance.client import Client


class Trader:

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Trader, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:

        if self._initialized:
            return
        self._initialized = True

    def start_trade(self) -> CryptoPairs:
        loop = asyncio.get_event_loop()
        FirebaseManager().setup_firebase(loop)
        cryptoPairs = BinanceManager().fetch_pairs()

        for cryptoPair in cryptoPairs.pairs:
            BinanceManager().analyze_orders(cryptoPair.pair, add_missing_orders=False)

        return cryptoPairs

    async def run_trading_cycle(self, cryptoPairs, version):
        tasks = []
        for crypto_pair in cryptoPairs.pairs:
            self.update_crypto_amounts(crypto_pair)
            tasks.append(asyncio.create_task(self.handle_strategies(crypto_pair)))

        if tasks:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        else:
            logger.info("No tasks to execute, waiting for conditions to be met.")
            await asyncio.sleep(5)

        FirebaseManager().send_heartbeat(version=version)

    def update_crypto_amounts(self, crypto_pair: CryptoPair):
        crypto_amounts = BinanceManager().get_crypto_amounts(crypto_pair.pair)
        crypto_pair.crypto_amount_free = crypto_amounts[CRYPTO_AMOUNT_FREE]
        crypto_pair.crypto_amount_locked = crypto_amounts[CRYPTO_AMOUNT_LOCKED]

    def calculate_quantity(self, strategy: TradeStrategy, cryptoPair: CryptoPair):
        global PAIRS

        logger.debug(f"Calculating quantity for trading for {cryptoPair.pair}.")

        quantity_of_crypto = ((cryptoPair.min_notional * strategy.multiplier)) / BinanceManager().get_price(cryptoPair.pair)

        logger.debug(f"{cryptoPair.pair} for trading: {quantity_of_crypto}.")

        return quantity_of_crypto

    async def handle_strategies(self, cryptoPair: CryptoPair):
        global STRATEGIES
        global PAIRS
        strategy_list = [STRATEGIES.strategies[POOR_ORPHAN], STRATEGIES.strategies[CRAZY_GIRL], STRATEGIES.strategies[SENSIBLE_GUY]]

        tasks = []

        for strategy in strategy_list:
            allocation = float(PAIRS.pairs[cryptoPair.pair]['strategy_allocation'][strategy.name])

            cryptoPair.value = float(cryptoPair.crypto_amount_free) * float(
                BinanceManager().get_price(cryptoPair.pair)
            )

            if allocation * cryptoPair.value > cryptoPair.min_notional:

                logger.debug(f"Creating task for strategy {strategy.name} on pair {cryptoPair.pair} with allocation {allocation}")

                task = asyncio.create_task(
                    self.process_strategy(
                        cryptoPair=cryptoPair,
                        strategy=strategy
                    )
                )
                tasks.append(task)
            else:
                logger.debug(f"Skipping strategy {strategy.name} for pair {cryptoPair.pair} due to insufficient value in wallet.")

        await asyncio.gather(*tasks)

    async def process_strategy(self, cryptoPair: CryptoPair, strategy: TradeStrategy):
        global PAIRS

        logger.debug(f"Strategy: {strategy.name} for {cryptoPair.pair} - Current state: {cryptoPair.current_state[strategy.name]}")

        BinanceManager().monitor_buy_orders(cryptoPair=cryptoPair, strategy=strategy)

        if cryptoPair.current_state[strategy.name] == TradeState.MONITORING:

            buy_price, sell_price = BinanceManager().calculate_buy_and_sell_price(crypto_pair=cryptoPair, strategy=strategy)
            quantity_of_crypto = self.calculate_quantity(strategy=strategy, cryptoPair=cryptoPair)

            if BinanceManager().validate_price_order(cryptoPair=cryptoPair, quantity_of_crypto=quantity_of_crypto, buy_price=buy_price):

                sell_order = await BinanceManager().limit_order(
                    cryptoPair=cryptoPair,
                    quantity=quantity_of_crypto,
                    price=sell_price,
                    side=Client.SIDE_SELL
                )

                if sell_order:

                    cryptoPair.active_sell_order = Order(
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

                    from firebase import FirebaseManager
                    FirebaseManager().add_order_to_firebase(cryptoPair.active_sell_order)

                    logger.info(f"Sell order placed for {cryptoPair.pair} at price {sell_price}")

                    cryptoPair.current_state[strategy.name] = TradeState.SELLING
                    logger.debug(f"State after placing sell order for {cryptoPair.pair}: {cryptoPair.current_state[strategy.name]}")

        elif cryptoPair.current_state[strategy.name] == TradeState.SELLING:

            sell_order = BinanceManager().get_order_status(cryptoPair.pair, order_id=cryptoPair.active_sell_order.order_id)

            elapsed_time = (datetime.now() - datetime.fromtimestamp(int(cryptoPair.active_sell_order.timestamp) / 1000)).total_seconds()

            BinanceManager().print_order(cryptoPair.pair, sell_order=sell_order)

            if elapsed_time > strategy.timeout:
                canceled_order = await BinanceManager().cancel_order(cryptoPair.pair, cryptoPair.active_sell_order.order_id)
                if canceled_order == FILLED:
                    logger.debug(f"Cannot cancel order {cryptoPair.active_sell_order.order_id} already filled")
                elif canceled_order:
                    cryptoPair.active_sell_order.status = CANCELED
                    from firebase import FirebaseManager
                    logger.info(f"Active_sell_order marking as cancelled in db {cryptoPair.active_sell_order}")
                    FirebaseManager().add_order_to_firebase(
                        cryptoPair.active_sell_order
                    )
                    logger.warning(f"Sell order {cryptoPair.active_sell_order.order_id} for {cryptoPair.pair} canceled due to timeout.")
                    cryptoPair.current_state[strategy.name] = TradeState.MONITORING
                    return
                else:
                    logger.error(f"Failed to cancel sell order {cryptoPair.active_sell_order.order_id} for {cryptoPair.pair} due to timeout.")
            else:
                logger.info(f" Expired      : {strategy.timeout - elapsed_time}")
            logger.info("="*50)

            if sell_order[STATUS] == FILLED:

                logger.info(f"Sell order {cryptoPair.active_sell_order.order_id} for {cryptoPair.pair} completed. Placing buy order.")

                cryptoPair.executed_sell_order = copy(cryptoPair.active_sell_order)
                cryptoPair.executed_sell_order.status = FILLED

                from firebase import FirebaseManager
                FirebaseManager().add_order_to_firebase(
                    cryptoPair.executed_sell_order
                )

                buy_order = await BinanceManager().limit_order(
                    cryptoPair=cryptoPair,
                    quantity=cryptoPair.active_sell_order.amount,
                    price=cryptoPair.active_sell_order.buy_price,
                    side=Client.SIDE_BUY
                )

                if buy_order:

                    logger.info(f"Buy order placed for {cryptoPair.pair}!")

                    sell_fee = float(buy_order[ORIG_QTY]) * float(cryptoPair.active_sell_order.sell_price) * float(FEE_SELL_BINANCE_VALUE)
                    buy_fee = float(buy_order[ORIG_QTY]) * float(cryptoPair.active_sell_order.buy_price) * float(FEE_SELL_BINANCE_VALUE)
                    total_fees = sell_fee + buy_fee

                    cryptoPair.active_buy_order = Order(
                                symbol=buy_order[SYMBOL],
                                order_id=buy_order[ORDER_ID],
                                order_type=buy_order[SIDE],
                                amount=float(buy_order[ORIG_QTY]),
                                sell_price=cryptoPair.active_sell_order.sell_price,
                                buy_price=cryptoPair.active_sell_order.buy_price,
                                timestamp=datetime.fromtimestamp(float(buy_order[WORKING_TIME])/100).strftime('%Y-%m-%d %H:%M:%S'),
                                strategy=strategy.name,
                                status=buy_order[STATUS],
                                profit = ((float(cryptoPair.active_sell_order.sell_price)*float(buy_order[ORIG_QTY])) - (float(cryptoPair.active_sell_order.buy_price)*float(buy_order[ORIG_QTY]))) - total_fees,
                            )

                    FirebaseManager().add_order_to_firebase(
                        cryptoPair.add_order(
                            cryptoPair.active_buy_order
                            )
                    )
                    cryptoPair.current_state[strategy.name] = TradeState.COOLDOWN
                    logger.debug(f"Current strategy allocation for {cryptoPair.pair}: {PAIRS.pairs[cryptoPair.pair]['strategy_allocation'][strategy.name]}")
                else:
                    logger.error(f"Failed to place buy order for {cryptoPair.pair}!")

        elif cryptoPair.current_state[strategy.name] == TradeState.COOLDOWN:

            if cryptoPair.executed_sell_order:

                last_order_time = datetime.fromtimestamp(int(cryptoPair.executed_sell_order.timestamp) / 1000)
                elapsed_time = datetime.now() - last_order_time

                cooldown_timedelta = timedelta(seconds=strategy.cooldown)

                if elapsed_time < cooldown_timedelta:
                    remaining_time = cooldown_timedelta - elapsed_time
                    logger.info(f"Cooldown active for {cryptoPair.pair} - Waiting {remaining_time} before next order.")
                else:
                    cryptoPair.current_state[strategy.name] = TradeState.MONITORING
            else:
                logger.debug(f"No last sell order found for {cryptoPair.pair}.")

            if cryptoPair.active_buy_order:

                logger.debug(f"Active buy order for {cryptoPair.pair}: {cryptoPair.active_buy_order}")

                status = BinanceManager().get_order_status(cryptoPair.pair, order_id=cryptoPair.active_buy_order.order_id)
                if status[STATUS] == FILLED:
                    logger.info(f"Buy order {cryptoPair.active_buy_order.order_id} for {cryptoPair.pair} completed during cooldown.")

                    from firebase import FirebaseManager
                    FirebaseManager().add_order_to_firebase(
                        cryptoPair.set_status(order_id=cryptoPair.active_buy_order.order_id, status=FILLED)
                    )

                    cryptoPair.current_state[strategy.name] = TradeState.MONITORING
                    logger.info(f"Cooldown interrupted for {cryptoPair.pair}. Switching back to monitoring.")