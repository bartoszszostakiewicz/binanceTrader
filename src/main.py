import asyncio
from logger import logger
from utils import get_tag
from trader import Trader
from globals import POWER_STATUS

VERSION = get_tag()


async def main():
    global POWER_STATUS

    trader = Trader()
    cryptoPairs = trader.start_trade()

    iteration = 0

    while True:
        if POWER_STATUS.power_status:
            await trader.run_trading_cycle(cryptoPairs, VERSION)
            iteration += 1
            logger.debug(f"Iteration {iteration}")
        else:
            logger.info("Power status is OFF. Waiting...")
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except asyncio.CancelledError:
        logger.info("Main loop cancelled. Cleaning up...")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
    finally:
        logger.info("Program shutdown complete.")