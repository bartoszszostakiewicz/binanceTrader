import asyncio
from binance_api import BinanceTrader
from firebase import FirebaseManager
from constants import *
from logger import logger


VERSION = "1.0.1"

async def main():

    firebaseManager = FirebaseManager()
    trader = BinanceTrader()


    cryptoPairs = firebaseManager.fetch_pairs()


    for crypto_pair in cryptoPairs.pairs:
        trader.analyze_orders(crypto_pair.pair)



    while True:

        i = 0
        powerStatus = firebaseManager.get_power_status()

        cryptoPairs = firebaseManager.fetch_pairs()


        while powerStatus:

            strategy_tasks = []

            for crypto_pair in cryptoPairs.pairs:
                crypto_amounts = firebaseManager.get_crypto_amounts(crypto_pair.pair)
                crypto_pair.crypto_amount_free = crypto_amounts['crypto_amount_free']
                crypto_pair.crypto_amount_locked = crypto_amounts['crypto_amount_locked']
                crypto_pair.value = float(crypto_pair.crypto_amount_free) * float(BinanceTrader().get_price(crypto_pair.pair))


                if (float(crypto_pair.crypto_amount_free) * float(crypto_pair.trading_percentage)) > 0 and crypto_pair.pair == "SHIBUSDT":
                    strategy_tasks.append(
                        asyncio.create_task(
                            trader.handle_strategies(cryptoPair=crypto_pair, strategies=cryptoPairs.strategies)
                        )
                    )

            tasks = strategy_tasks


            if tasks:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            else:
                logger.info("No tasks to execute, waiting for conditions to be met.")
                await asyncio.sleep(5)


            firebaseManager.send_heartbeat(version=VERSION)
            powerStatus = firebaseManager.get_power_status()


            i += 1
            logger.debug(f'Iteration {i}')



if __name__ == "__main__":
    asyncio.run(main())

