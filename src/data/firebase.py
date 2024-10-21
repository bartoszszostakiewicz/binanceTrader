import firebase_admin
from firebase_admin import credentials
import firebase_admin.storage
from firebase_admin import db
from firebase_admin import auth
from CryptoPair import Order, CryptoPairs, CryptoPair

dbUrl = 'https://bintrader-ffeeb-default-rtdb.firebaseio.com/'

cred = credentials.Certificate("../../bintrader-ffeeb-firebase-adminsdk-6ytwx-e6e7bfbea8.json")
firebase_admin.initialize_app(cred)




import requests

def login_to_firebase(email, password):
    api_key = 'AIzaSyBECJFlN8QCFGhExZ7VxSACo6iSWKp8FvI'
    url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}'
    
    payload = {
        'email': email,
        'password': password,
        'returnSecureToken': True
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print('Zalogowano pomyślnie!')
        print('Token:', data['idToken'])  # Użyj tokenu do autoryzacji w przyszłych żądaniach
    else:
        print('Błąd logowania:', response.json())


# Przykład użycia

# email = 'pybinance.trader@gmail.com'
# password = 'ahr7aik3rohte3yi'
# login_to_firebase(email, password)



# Przykład użycia
crypto_pair_1 = CryptoPair(
    pair="BTC/USD",
    trading_percentage=50.0,
    strategy_allocation={"Strategy A": 70.0, "Strategy B": 30.0},
    profit_target=10.0,
    crypto_amount=0.5,
    active_orders=[
        Order(order_id="123", order_type="buy", amount=0.1, price=30000, timestamp="2024-10-21 10:00")
    ],
    completed_orders=[
        Order(order_id="122", order_type="buy", amount=0.15, price=29000, timestamp="2024-10-20 09:00")
    ]
)

# Inicjalizacja klasy CryptoPairs
crypto_pairs = CryptoPairs()
crypto_pairs.add_pair(crypto_pair_1)


crypto_pairs.save_to_firebase(dbUrl)

# Odczyt danych z Firebase
crypto_pairs.load_from_firebase(dbUrl)

# Wyświetlenie odczytanych danych

for pair in crypto_pairs.pairs:
    print(f"Para: {pair.pair}, Procent handlowy: {pair.trading_percentage}%")



