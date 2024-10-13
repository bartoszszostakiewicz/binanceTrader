from binance.client import Client
import os


# Initialize Binance client
client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))

def limit_buy_order(trading_pair, quantity, buy_price):
    """
    Function to place a limit buy order on Binance exchange.
    
    :param trading_pair: The trading pair, e.g., 'BTCUSDT'
    :param quantity: Amount of cryptocurrency to buy
    :param buy_price: Price at which to buy
    """
    try:
        order = client.create_order(
            symbol=trading_pair,
            side=Client.SIDE_BUY,
            type=Client.ORDER_TYPE_LIMIT,
            timeInForce=Client.TIME_IN_FORCE_GTC,  # Good 'Til Canceled
            quantity=quantity,
            price=str(buy_price)
        )
        print("Buy order placed successfully!")
        return order
    except Exception as e:
        print(f"Error placing buy order: {e}")
        return None

# Example usage:
trading_pair = 'BTCUSDT'  # Trading pair, e.g., Bitcoin/USDT
quantity = 0.001  # Quantity to buy
buy_price = 25000  # Price at which to place the buy order

limit_buy_order(trading_pair, quantity, buy_price)
