import asyncio
from binance_api import BinanceManager
from firebase import FirebaseManager
from globals import *
from logger import logger
from utils import get_tag


VERSION = get_tag()


async def main():
    global POWER_STATUS
    global PAIRS

    loop = asyncio.get_event_loop()
    FirebaseManager().setup_signal_handler(loop)
    FirebaseManager().start_listener_in_thread()

    cryptoPairs = BinanceManager().fetch_pairs()

    i = 0

    try:
        while True:
            if POWER_STATUS.power_status:

                tasks = []

                for crypto_pair in cryptoPairs.pairs:

                    crypto_amounts = BinanceManager().get_crypto_amounts(crypto_pair.pair)
                    crypto_pair.crypto_amount_free = crypto_amounts[CRYPTO_AMOUNT_FREE]
                    crypto_pair.crypto_amount_locked = crypto_amounts[CRYPTO_AMOUNT_LOCKED]

                    crypto_pair.value = float(crypto_pair.crypto_amount_free) * float(
                        BinanceManager().get_price(crypto_pair.pair)
                    )

                    if (float(crypto_pair.crypto_amount_free) * float(PAIRS.pairs[crypto_pair.pair]["trading_percentage"])) > crypto_pair.min_notional:
                        tasks.append(
                            asyncio.create_task(
                                BinanceManager().handle_strategies(
                                    cryptoPair=crypto_pair
                                )
                            )
                        )

                if tasks:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                else:
                    logger.info("No tasks to execute, waiting for conditions to be met.")
                    await asyncio.sleep(5)

                FirebaseManager().send_heartbeat(version=VERSION)

                i += 1
                logger.debug(f'Iteration {i}')
            else:
                logger.info(f"Power status is OFF!")
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Main loop cancelled. Cleaning up...")
    finally:
        logger.info("Main function finished execution.")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
    finally:
        logger.info("Program shutdown complete.")
