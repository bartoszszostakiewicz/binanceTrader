import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from binance.client import Client
import talib  # For technical indicators

# Initialize Binance client
client = Client(api_key='YOUR_API_KEY', api_secret='YOUR_SECRET')

def get_historical_data(symbol, interval='1d'):
    """Fetch historical data from Binance."""
    klines = client.get_klines(symbol=symbol, interval=interval)
    data = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume', 
        'close_time', 'quote_asset_volume', 'number_of_trades', 
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    data['close'] = data['close'].astype(float)
    return data

def create_features(data):
    """Feature engineering: calculate price change percentage and technical indicators."""
    data['pct_change'] = data['close'].pct_change() * 100
    data['label'] = np.where(data['pct_change'].shift(-1) > 1, 1, 0)
    
    # Adding technical indicators as features
    data['SMA'] = talib.SMA(data['close'], timeperiod=14)  # Simple Moving Average
    data['RSI'] = talib.RSI(data['close'], timeperiod=14)  # Relative Strength Index
    data.dropna(inplace=True)
    
    return data

def train_model(data):
    """Train the binary classifier."""
    X = data[['SMA', 'RSI']]
    y = data['label']
    
    # Split into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train Random Forest Classifier
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    
    # Evaluate the model
    predictions = model.predict(X_test)
    accuracy = accuracy_score(y_test, predictions)
    print(f"Model Accuracy: {accuracy:.2f}")
    
    return model

# Fetch historical data for a specific symbol (e.g., BTCUSDT)
data = get_historical_data('BTCUSDT')

# Create features and labels
data = create_features(data)

# Train the model
model = train_model(data)

# You can now use the model to predict future price movements based on real-time data!
