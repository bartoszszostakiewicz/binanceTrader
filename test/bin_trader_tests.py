import unittest
from ...bin_trader.src.binance_api import BinanceTrader

class TestBinanceTraderRealData(unittest.TestCase):

    def setUp(self):
        """
        This method is called before each test to set up necessary variables.
        """
        self.trader = BinanceTrader()

    def test_is_local_peak_real_data(self):
        """
        Test the is_local_peak method using real data from Binance API.
        """
        symbol = 'BTCUSDT'  # Example symbol
        interval = '1h'      # Hourly data
        lookback_period = 5  # Check the last 5 periods for a local peak

        # Run the function to check for a local peak using real market data
        is_peak = self.trader.is_local_peak(symbol, interval=interval, lookback_period=lookback_period)

        # Print the result for verification (True if local peak is detected, False otherwise)
        print(f"Is {symbol} at a local peak? {is_peak}")

        # In real tests, we would check some expected behavior, but due to real-time nature, we just print the result.
        # For now, we can assert it's a boolean value.
        self.assertIsInstance(is_peak, bool)

if __name__ == '__main__':
    unittest.main()
