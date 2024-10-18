import pandas as pd
import numpy as np
from binance.client import Client
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
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

# Fetch historical data for BTC/USDT as an example (you can adjust symbol and date range)
symbol = 'BTCUSDT'
interval = Client.KLINE_INTERVAL_1DAY
start_str = '1 Jan, 2020'
end_str = '17 Oct, 2024'

# Fetch data
data = get_historical_data(symbol, interval, start_str, end_str)

###################################################################################################################################################################################################################

#Using talib calculating:
#SMA - 

#dlaczego timeperiod 14 dni ??

# Create Features (Technical Indicators and Price Changes)

#SMA to prosta średnia krocząca, która bierze sumę zamknięć z ostatnich 14 dni i dzieli przez 14, aby uzyskać średnią.
#SMA pozwala wygładzić ruchy cen i pomóc w identyfikacji trendów. Dzięki temu można zauważyć, czy ceny generalnie rosną, czy spadają w analizowanym okresie.
data['SMA'] = talib.SMA(data['close'], timeperiod=14)



#EMA (Exponential Moving Average) – Średnia Krocząca Wykładnicza
#EMA przypisuje większą wagę nowszym cenom, co czyni ją bardziej wrażliwą na zmiany niż SMA.
#EMA szybciej reaguje na zmiany cen, dlatego jest często stosowana w krótkoterminowej analizie.
data['EMA'] = talib.EMA(data['close'], timeperiod=14)

#RSI (Relative Strength Index) – Wskaźnik Siły Względnej
#RSI mierzy prędkość i zmianę ruchów cenowych w ciągu określonego okresu, zazwyczaj 14 dni.
# RSI = 100 - (100/(1+RS))
#RS to stosunek średnich wzrostów do średnich spadków w danym okresie.
#Interpretacja:
#RSI powyżej 70 sugeruje, że aktywo jest wykupione (możliwa korekta w dół).
#RSI poniżej 30 sugeruje, że aktywo jest wyprzedane (możliwy wzrost).
data['RSI'] = talib.RSI(data['close'], timeperiod=14)


#MACD (Moving Average Convergence Divergence) – Zbieżność i Rozbieżność Średnich Kroczących
#MACD to różnica między dwiema wykładniczymi średnimi kroczącymi (zazwyczaj 12 i 26 dni).
#Dodatkowo sygnał MACD to 9-dniowa EMA wskaźnika MACD.
#Interpretacja:
#Gdy MACD przecina linię sygnału od dołu, może to sygnalizować kupno.
#Gdy MACD przecina linię sygnału od góry, może to sygnalizować sprzedaż.
data['MACD'], data['MACD_signal'], data['MACD_hist'] = talib.MACD(data['close'], fastperiod=12, slowperiod=26, signalperiod=9)

#Bollinger Bands – Wstęgi Bollingera
#Wstęgi Bollingera składają się z trzech linii: średniej kroczącej oraz dwóch odchyleń standardowych powyżej i poniżej średniej.
#Interpretacja:
#Gdy cena dotyka górnej wstęgi, może być wykupiona.
#Gdy cena dotyka dolnej wstęgi, może być wyprzedana.
data['Upper_band'], data['Middle_band'], data['Lower_band'] = talib.BBANDS(data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)


#OBV (On-Balance Volume) – Wskaźnik Obrotów Równoważonych
#OBV to wskaźnik obrotu, który łączy wolumen z kierunkiem ceny.
#Jeśli dzisiejsza cena zamknięcia jest wyższa niż wczorajsza, dodajemy dzisiejszy wolumen do OBV.
#Jeśli dzisiejsza cena zamknięcia jest niższa, odejmujemy wolumen.
#OBV rosnący potwierdza trend wzrostowy cen.
#OBV spadający potwierdza trend spadkowy.
data['OBV'] = talib.OBV(data['close'], data['volume'])

# Create Lagged Features
data['pct_change'] = data['close'].pct_change()
data['lagged_return_1'] = data['pct_change'].shift(1)
data['lagged_return_2'] = data['pct_change'].shift(2)
data['lagged_return_3'] = data['pct_change'].shift(3)


# pd.set_option('display.max_rows', None)  # None oznacza brak limitu
# pd.set_option('display.max_columns', None)
# print(data)


# pd.set_option('display.max_columns', None)
# pd.set_option('display.max_colwidth', None)

print(data[['SMA','EMA','RSI','MACD','Upper_band','OBV']].head(50))  # Wyświetli pierwsze 50 wierszy
print(data[['SMA','EMA','RSI','MACD','Upper_band','OBV']].tail(50))  # Wyświetli ostatnie 50 wierszy





# Target: Binary classification if price increased or decreased by 1%
data['target'] = np.where(data['pct_change'] >= 0.01, 1, 0)

# # Drop rows with NaN values caused by lagging
# data.dropna(inplace=True)

# # Select features and target variable
# features = ['SMA', 'EMA', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
#             'Upper_band', 'Middle_band', 'Lower_band', 'OBV', 
#             'lagged_return_1', 'lagged_return_2', 'lagged_return_3']

# X = data[features]
# y = data['target']

# # Split the data into training and testing sets
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# # Normalize the data (optional, but useful for some models)
# scaler = StandardScaler()
# X_train_scaled = scaler.fit_transform(X_train)
# X_test_scaled = scaler.transform(X_test)

# # Random Forest Classifier
# param_grid = {
#     'n_estimators': [50, 100, 200],
#     'max_depth': [5, 10, 20, None],
#     'min_samples_split': [2, 5, 10],
#     'min_samples_leaf': [1, 2, 4]
# }
# rf_model = RandomForestClassifier(random_state=42)
# grid_search = GridSearchCV(estimator=rf_model, param_grid=param_grid, cv=5, n_jobs=-1, verbose=2)
# grid_search.fit(X_train_scaled, y_train)

# # Best Random Forest parameters
# rf_best_model = grid_search.best_estimator_
# rf_best_model.fit(X_train_scaled, y_train)

# # Predict and Evaluate
# y_pred_rf = rf_best_model.predict(X_test_scaled)
# rf_accuracy = accuracy_score(y_test, y_pred_rf)
# print(f"Random Forest Accuracy: {rf_accuracy:.2f}")

# # XGBoost Classifier
# xgb_model = XGBClassifier(n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42)
# xgb_model.fit(X_train_scaled, y_train)

# # Predict and Evaluate
# y_pred_xgb = xgb_model.predict(X_test_scaled)
# xgb_accuracy = accuracy_score(y_test, y_pred_xgb)
# print(f"XGBoost Accuracy: {xgb_accuracy:.2f}")

# # Cross-Validation
# cv_scores_rf = cross_val_score(rf_best_model, X_train_scaled, y_train, cv=5)
# print(f"Cross-Validation Accuracy (Random Forest): {np.mean(cv_scores_rf):.2f}")

# cv_scores_xgb = cross_val_score(xgb_model, X_train_scaled, y_train, cv=5)
# print(f"Cross-Validation Accuracy (XGBoost): {np.mean(cv_scores_xgb):.2f}")












# # Wybranie cech i przygotowanie ostatniego dnia na prognozę
# X_new = data[features].iloc[-1:]  # Bierzemy ostatni wiersz danych (dzisiaj)

# # Sprawdzenie, czy są braki
# if X_new.isna().sum().sum() > 0:
#     X_new.fillna(method='ffill', inplace=True)

# # Normalizacja nowych danych
# X_new_scaled = scaler.transform(X_new)

# # Prognozowanie na jutro
# rf_pred = rf_best_model.predict(X_new_scaled)
# xgb_pred = xgb_model.predict(X_new_scaled)

# # Interpretacja wyniku
# rf_pred_text = "Price will increase by 1%+" if rf_pred[0] == 1 else "Price will not increase by 1%"
# xgb_pred_text = "Price will increase by 1%+" if xgb_pred[0] == 1 else "Price will not increase by 1%"

# # Wypisanie prognozy na jutro
# print(f"Predictions for BTC/USDT Price Movement (next day prediction):")
# print(f"Date: {pd.to_datetime(data['timestamp'].iloc[-1], unit='ms').date()}")
# print(f"Random Forest Prediction: {rf_pred_text}")
# print(f"XGBoost Prediction: {xgb_pred_text}")



# # Ostatni dzień z danych, aby przewidzieć 15 października
# latest_data = data.iloc[-1]

# # Przygotuj nowy wiersz dla 15 października
# new_row = {
#     'SMA': talib.SMA(data['close'], timeperiod=14)[-1],
#     'EMA': talib.EMA(data['close'], timeperiod=14)[-1],
#     'RSI': talib.RSI(data['close'], timeperiod=14)[-1],
#     'MACD': talib.MACD(data['close'], fastperiod=12, slowperiod=26, signalperiod=9)[0][-1],
#     'MACD_signal': talib.MACD(data['close'], fastperiod=12, slowperiod=26, signalperiod=9)[1][-1],
#     'MACD_hist': talib.MACD(data['close'], fastperiod=12, slowperiod=26, signalperiod=9)[2][-1],
#     'Upper_band': talib.BBANDS(data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)[0][-1],
#     'Middle_band': talib.BBANDS(data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)[1][-1],
#     'Lower_band': talib.BBANDS(data['close'], timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)[2][-1],
#     'OBV': talib.OBV(data['close'], data['volume'])[-1],
#     'lagged_return_1': latest_data['pct_change'],
#     'lagged_return_2': data['pct_change'].shift(1).iloc[-1],
#     'lagged_return_3': data['pct_change'].shift(2).iloc[-1]
# }

# # Przekształcenie nowego wiersza do DataFrame
# X_new = pd.DataFrame([new_row])

# # Normalizacja nowego wiersza
# X_new_scaled = scaler.transform(X_new)

# # Przewidywanie
# rf_prediction = rf_best_model.predict(X_new_scaled)[0]
# xgb_prediction = xgb_model.predict(X_new_scaled)[0]

# # Interpretacja wyników
# print("Predictions for BTC/USDT Price Movement on 2024-10-15:")
# print(f"Random Forest Prediction: Price will {'increase by 1%+' if rf_prediction == 1 else 'not increase by 1%'}")
# print(f"XGBoost Prediction: Price will {'increase by 1%+' if xgb_prediction == 1 else 'not increase by 1%'}")