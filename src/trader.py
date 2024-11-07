import asyncio
import time
from binance_api import BinanceTrader
from firebase import FirebaseManager
import json
from data_classes import CryptoPair
from collections import defaultdict
from constants import *
from logger import logger
    
VERSION = "1.0.0"

async def main():
    trader = BinanceTrader()
    firebaseManager = FirebaseManager(trader=trader)
    
    logger.debug(f"Public Ip = {trader.get_public_ip()}")

    
    cryptoPairs = firebaseManager.fetch_pairs()
    
    # for cryptoPair in cryptoPairs.pairs:
    #     symbol = cryptoPair.pair  # Replace with your desired symbol
        
    #     print(f"pair = {cryptoPair.pair}")
    #     print(f"pair = {cryptoPair.strategy_allocation[CRAZY_GIRL]}")

    #     print(f"Summary for {symbol}:")
    #     print(f"  Buy Orders Count         : {summary['buy_count']}")
    #     print(f"  Sell Orders Count        : {summary['sell_count']}")
    #     print(f"  Total Bought Quantity    : {summary['total_bought_quantity']}")
    #     print(f"  Total Bought Value       : {summary['total_buy_value']}")
    #     print(f"  Total Sold Quantity      : {summary['total_sold_quantity']}")
    #     print(f"  Total Sold Value         : {summary['total_sell_value']}")
    #     print(f"  Missing quantity         : {summary['quantity_missing']} {cryptoPair.pair}")
    #     print(f"  Value of missing quantit : {summary['quantity_missing'] * trader.get_price(cryptoPair.pair) } {cryptoPair.pair}")
        

    #debug mode pobierz z bazy dany i ustaw tutaj zeby za kazdym razem nie wysylac zapytania do bazy danych! np zmienan globalna lub cos innego

    ###################################################################################################################################################

    while True:
        
        i = 0
        powerStatus = firebaseManager.get_power_status()
        
        #zeruje prawdopodpnie staty do poprawy
        cryptoPairs = firebaseManager.fetch_pairs()
        
        while powerStatus:
            
            # cryptoValue = firebaseManager.get_crypto_value()

            # Tasks for handling strategies for each crypto pair
            strategy_tasks = [
                asyncio.create_task(trader.handle_strategies(cryptoPair=crypto_pair, strategies=cryptoPairs.strategies))
                for crypto_pair in cryptoPairs.pairs
                if (float(crypto_pair.crypto_amount_free) * float(crypto_pair.trading_percentage)) > 0 and crypto_pair.pair == "BTCUSDC"
            ]
            
            
            # # Tasks for monitoring buy orders for each crypto pair
            # monitor_tasks = [
            #     asyncio.create_task(trader.monitor_buy_orders(cryptoPair=crypto_pair))
            #     for crypto_pair in cryptoPairs.pairs
            #     if any(order.order_type == "BUY"  for order in crypto_pair.active_orders)
            # ]
            
          
            
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
            logger.debug(f'iteracja {i}')


        #anuluj wszystkie zlecenia sprzedazy bo nie bedziesz w stanie zrobic zlecen kupna jak power off albo jakos inaczej




if __name__ == "__main__":
    asyncio.run(main())

