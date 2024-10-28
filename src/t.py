import requests
import pandas as pd
import matplotlib.pyplot as plt

# Lista symboli kryptowalut, które nas interesują
symbols = ['BTCUSDC', 'ETHUSDC','SHIBUSDC','LTCUSDC','XLMUSDC', 'BNBUSDC', 'SOLUSDC', 'ADAUSDC', 'MATICUSDC', 'XRPUSDC', 'AVAXUSDC']

# Funkcja do pobierania danych historycznych z Binance API
def get_binance_data(symbol, interval='1d', limit=1000):
    base_url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    response = requests.get(base_url, params=params)
    data = response.json()
    
    # Konwersja danych na DataFrame
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume',
        'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # Używamy tylko kolumny 'close' i 'timestamp'
    df['close'] = df['close'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df[['timestamp', 'close']]

# 
# Pobieranie dan
# ych dla wszystkich kryptowalut
crypto_data = {}
for symbol in symbols:
    crypto_data[symbol] = get_binance_data(symbol)

# Obliczanie dziennej zmienności procentowej dla każdej kryptowaluty
percentage_changes = {}
for symbol, data in crypto_data.items():
    data['percent_change'] = data['close'].pct_change() * 100  # Procentowa zmiana ceny
    percentage_changes[symbol] = data[['timestamp', 'percent_change']]

# Rysowanie wykresu dziennej zmienności procentowej
plt.figure(figsize=(12, 8))

for symbol, data in percentage_changes.items():
    plt.plot(data['timestamp'], data['percent_change'], label=symbol)

plt.title('Dzienna zmienność procentowa wybranych kryptowalut')
plt.xlabel('Data')
plt.ylabel('Zmiana procentowa (%)')
plt.legend(loc='upper right')
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()

plt.show()
