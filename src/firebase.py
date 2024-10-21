import firebase_admin
from firebase_admin import credentials
import firebase_admin.storage
from firebase_admin import db
from firebase_admin import auth

dbUrl = 'https://bintrader-ffeeb-default-rtdb.firebaseio.com/'

cred = credentials.Certificate("../bintrader-ffeeb-firebase-adminsdk-6ytwx-e6e7bfbea8.json")
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





ref = db.reference("/Books/Best_Sellers", url=dbUrl)
import json
with open("demo_data/book_info.json", "r") as f:
    file_contents = json.load(f)

for key, value in file_contents.items():
    ref.push().set(value)
