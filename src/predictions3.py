import pandas as pd
import numpy as np
from binance.client import Client
from sklearn.preprocessing import StandardScaler
import talib

# API Keys (replace with your own)
api_key = 'YOUR_BINANCE_API_KEY'
api_secret = 'YOUR_BINANCE_API_SECRET'

# Initialize Binance Client
client = Client(api_key, api_secret)

# Function to fetch historical data from Binance
def get_historical_data(symbol, interval, start_str, end_str):
    """Fetch historical data from Binance"""
    klines = client.get_historical_klines(symbol, interval, start_str, end_str)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                       'close_time', 'quote_asset_volume', 'number_of_trades', 
                                       'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    # Convert to numeric values
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])
    return df

# Fetch new historical data (adjust symbol and date range if needed)
symbol = 'BTCUSDT'
interval = Client.KLINE_INTERVAL_1DAY
start_str = '1 Sep, 2024'  # Fetch the most recent data
end_str = '13 Oct, 2024'

# Fetch new data
new_data = get_historical_data(symbol, interval, start_str, end_str)

# Create Features (Technical Indicators and Price Changes)
new_data['SMA'] = talib.SMA(new_data['close'], timeperiod=14)
new_data['EMA'] = talib.EMA(new_data['close'], timeperiod=14)
new_data['RSI'] = talib.RSI(new_data['close'], timeperiod=14)
new_data['MACD'], new_data['MACD_signal'], new_data['MACD_hist'] = talib.MACD(new_data['close'], fastperiod=12, slowperiod=26, signalperiod=9)
new_data['Upper_band'], new_data['Middle_band'], new_data['Lower_band'] = talib.BBANDS(new_data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
new_data['OBV'] = talib.OBV(new_data['close'], new_data['volume'])

# Create Lagged Features
new_data['pct_change'] = new_data['close'].pct_change()
new_data['lagged_return_1'] = new_data['pct_change'].shift(1)
new_data['lagged_return_2'] = new_data['pct_change'].shift(2)
new_data['lagged_return_3'] = new_data['pct_change'].shift(3)

# Drop rows with NaN values caused by lagging
new_data.dropna(inplace=True)

# Select the same features used during training
features = ['SMA', 'EMA', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
            'Upper_band', 'Middle_band', 'Lower_band', 'OBV', 
            'lagged_return_1', 'lagged_return_2', 'lagged_return_3']

X_new = new_data[features]

# Make sure to scale the new data using the same scaler
X_new_scaled = scaler.transform(X_new)

# Predict with Random Forest
y_pred_rf_new = rf_best_model.predict(X_new_scaled)

# Predict with XGBoost
y_pred_xgb_new = xgb_model.predict(X_new_scaled)

# Interpret predictions
new_data['rf_prediction'] = y_pred_rf_new
new_data['xgb_prediction'] = y_pred_xgb_new

# Print the results with explanations
print("Predictions for BTC/USDT Price Movement (next day prediction):")
for index, row in new_data.tail(10).iterrows():  # Show the last 10 rows of predictions
    date = pd.to_datetime(row['timestamp'], unit='ms').date()
    close_price = row['close']
    rf_pred = 'Price will increase by 1%+' if row['rf_prediction'] == 1 else 'Price will not increase by 1%'
    xgb_pred = 'Price will increase by 1%+' if row['xgb_prediction'] == 1 else 'Price will not increase by 1%'
    
    print(f"Date: {date}, Close Price: {close_price:.2f}")
    print(f"Random Forest Prediction: {rf_pred}")
    print(f"XGBoost Prediction: {xgb_pred}")
    print('-' * 50)
