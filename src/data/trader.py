import asyncio
import time
from binance_api import BinanceTrader
from firebase import FirebaseManager
import json
from CryptoPair import CryptoPairs
    
VERSION = "1.0.0"

async def main():
    trader = BinanceTrader()
    firebaseManager = FirebaseManager(trader=trader)

    while True:
        powerStatus = firebaseManager.set_power_status(True)
        powerStatus = firebaseManager.get_power_status()

        while powerStatus:
            cryptoPairs = firebaseManager.fetch_pairs()
            cryptoValue = firebaseManager.get_crypto_value()
            
            tasks = []

            for crypto_pair in cryptoPairs.pairs:

                # trader.get_recent_completed_orders(crypto_pair=crypto_pair)

                if (float(crypto_pair.crypto_amount_free) *float(crypto_pair.trading_percentage)) > 0:
                    tasks.append(asyncio.create_task(trader.handle_strategies(cryptoPair=crypto_pair, cryptoValue=cryptoValue)))

                # tasks.append(asyncio.create_task(trader.monitor_pending_buy_orders(crypto_pair)))
            
            
            firebaseManager.send_heartbeat(version=VERSION)

            powerStatus = firebaseManager.set_power_status(False)
            powerStatus = firebaseManager.get_power_status()
            
            
            await asyncio.gather(*tasks)

        break

if __name__ == "__main__":
    asyncio.run(main())

