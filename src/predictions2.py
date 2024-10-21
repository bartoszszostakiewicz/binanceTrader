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
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])
    return df

# Pobranie nowych danych do przewidywania
symbol = 'BTCUSDT'
interval = Client.KLINE_INTERVAL_1DAY
start_str = '1 Oct, 2020'  # Ustaw odpowiedni zakres
end_str = '13 Oct, 2024'

# Pobierz dane
new_data = get_historical_data(symbol, interval, start_str, end_str)

# Tworzenie wskaźników technicznych na nowych danych
new_data['SMA'] = talib.SMA(new_data['close'], timeperiod=14)
new_data['EMA'] = talib.EMA(new_data['close'], timeperiod=14)
new_data['RSI'] = talib.RSI(new_data['close'], timeperiod=14)
new_data['MACD'], new_data['MACD_signal'], new_data['MACD_hist'] = talib.MACD(new_data['close'], fastperiod=12, slowperiod=26, signalperiod=9)
new_data['Upper_band'], new_data['Middle_band'], new_data['Lower_band'] = talib.BBANDS(new_data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
new_data['OBV'] = talib.OBV(new_data['close'], new_data['volume'])

# Stworzenie opóźnionych zmiennych
new_data['pct_change'] = new_data['close'].pct_change()
new_data['lagged_return_1'] = new_data['pct_change'].shift(1)
new_data['lagged_return_2'] = new_data['pct_change'].shift(2)
new_data['lagged_return_3'] = new_data['pct_change'].shift(3)

# Usunięcie wierszy z brakującymi danymi
new_data.dropna(inplace=True)

# Zdefiniowanie cech
features = ['SMA', 'EMA', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
            'Upper_band', 'Middle_band', 'Lower_band', 'OBV', 
            'lagged_return_1', 'lagged_return_2', 'lagged_return_3']

X_new = new_data[features]

# Normalizacja danych (używamy skalera wytrenowanego wcześniej)
scaler = StandardScaler()
X_new_scaled = scaler.fit_transform(X_new)  # Upewnij się, że masz zapisaną instancję skalera z wcześniejszego treningu

# Załaduj wytrenowane modele (Random Forest i XGBoost)
# Tutaj powinieneś wczytać wcześniej wytrenowane modele, np. za pomocą pickle
import pickle

# Załaduj model Random Forest
with open('rf_best_model.pkl', 'rb') as f:
    rf_best_model = pickle.load(f)

# Załaduj model XGBoost
with open('xgb_model.pkl', 'rb') as f:
    xgb_model = pickle.load(f)

# Prognozowanie za pomocą modelu Random Forest
predictions_rf = rf_best_model.predict(X_new_scaled)

# Prognozowanie za pomocą modelu XGBoost
predictions_xgb = xgb_model.predict(X_new_scaled)

# Wyświetlenie prognoz
print("Prognozy (Random Forest):", predictions_rf)
print("Prognozy (XGBoost):", predictions_xgb)
