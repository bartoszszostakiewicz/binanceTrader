import time
import winsound  # Do generowania dźwięku na Windowsie
from binance_api import BinanceTrader

# Funkcja do wysyłania powiadomienia e-mail i generowania dźwięku
def notify_and_sound(trader, subject, message):
    trader.send_email_notification(subject, message)
    print("Notification sent!")
    winsound.Beep(1000, 500)  # 1000 Hz przez 500 ms (piknięcie)

# Główna funkcja programu
def main():
    trader = BinanceTrader()


    # Ustawienia użytkownika
    target_profit_percent = 10  # Chcemy sprzedać w cenie o 10% wyższej od kupna
    


    while True:
        try:
            # 1. Pobierz aktualne zasoby w portfelu
            wallet_balances = trader.get_wallet_balances()
            print(f"Current wallet balances: {wallet_balances}")

            for asset, balance in wallet_balances.items():
                # Sprawdzamy tylko zasoby, które nie są USDT lub BUSD, bo to są stablecoiny
                if asset not in ['USDT', 'BUSD'] and float(balance['free']) > 0:
                    symbol = f"{asset}USDT"
                    
                    # 2. Sprawdzamy, czy zasób jest w lokalnym szczycie
                    if trader.is_local_peak(symbol, interval='1h', lookback_period=5):
                        # 3. Sprzedajemy zasób (sprzedaż w peak'u)
                        quantity_to_sell = float(balance['free'])
                        current_price = float(trader.client.get_symbol_ticker(symbol=symbol)['price'])
                        trader.limit_order(symbol, quantity_to_sell, current_price, side=trader.client.SIDE_SELL)

                        # 4. Ustawiamy zlecenie kupna z celem 10% zysku (take profit)
                        buy_price = current_price * (1 - target_profit_percent / 100)
                        trader.limit_order(symbol, quantity_to_sell, buy_price, side=trader.client.SIDE_BUY)

                        # 5. Powiadomienia e-mail i dźwięk
                        message = f"Sold {quantity_to_sell} {asset} at {current_price}. Placed buy order at {buy_price}."
                        notify_and_sound(trader, email_to_notify, f"Sold {asset}", message)

            # Odświeżenie danych co godzinę (3600 sekund)
            time.sleep(3600)

        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)  # Jeśli wystąpił błąd, czekamy minutę i próbujemy ponownie


if __name__ == "__main__":
    main()
