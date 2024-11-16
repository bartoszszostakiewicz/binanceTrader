import asyncio
from binance_api import BinanceTrader
from firebase import FirebaseManager
from constants import *
from logger import logger

    
VERSION = "1.0.0"

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
            
            # Tasks for handling strategies for each crypto pair
            strategy_tasks = [
                asyncio.create_task(trader.handle_strategies(cryptoPair=crypto_pair, strategies=cryptoPairs.strategies))
                for crypto_pair in cryptoPairs.pairs
                if (float(crypto_pair.crypto_amount_free) * float(crypto_pair.trading_percentage)) > 0 #and crypto_pair.pair == "WBETHUSDT"
            ]
            
            
            # Combine both strategy and monitoring tasks
            tasks = strategy_tasks

           
            # Check if there are any tasks before waiting
            if tasks:
                # Wait for at least one task to complete
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

