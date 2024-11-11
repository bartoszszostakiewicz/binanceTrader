import asyncio
from binance_api import BinanceTrader
from firebase import FirebaseManager
from constants import *
from logger import logger
    
VERSION = "1.0.0"

async def main():
    trader = BinanceTrader()
    firebaseManager = FirebaseManager(trader=trader)
    
    logger.debug(f"Public Ip = {trader.get_public_ip()}")
    
    cryptoPairs = firebaseManager.fetch_pairs()
    
    
    
    # for cryptoPair in cryptoPairs.pairs:
    #     symbol = cryptoPair.pair  
        
    #     summary = trader.analyze_orders(cryptoPair.pair)
        
    #     print(f"pair = {cryptoPair.pair}")

    #     print(f"Summary for {symbol}:")
    #     print(f"  Buy Orders Count         : {summary['buy_count']}")
    #     print(f"  Sell Orders Count        : {summary['sell_count']}")
    #     print(f"  Total Bought Quantity    : {summary['total_bought_quantity']}")
    #     print(f"  Total Bought Value       : {summary['total_buy_value']}")
    #     print(f"  Total Sold Quantity      : {summary['total_sold_quantity']}")
    #     print(f"  Total Sold Value         : {summary['total_sell_value']}")
    #     print(f"  Missing quantity         : {summary['quantity_missing']} {cryptoPair.pair}")
    #     print(f"  Value of missing quantit : {summary['quantity_missing'] * trader.get_price(cryptoPair.pair) } {cryptoPair.pair}")
        


    while True:
        
        i = 0
        powerStatus = firebaseManager.get_power_status()
        cryptoPairs = firebaseManager.fetch_pairs()
        
        
        while powerStatus:
            
            # Tasks for handling strategies for each crypto pair
            strategy_tasks = [
                asyncio.create_task(trader.handle_strategies(cryptoPair=crypto_pair, strategies=cryptoPairs.strategies))
                for crypto_pair in cryptoPairs.pairs
                if (float(crypto_pair.crypto_amount_free) * float(crypto_pair.trading_percentage)) > 0 #and crypto_pair.pair == "ETHUSDC"
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

