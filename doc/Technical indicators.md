# Opis wskaźników technicznych użytych w analizie

W tej sekcji znajdziesz szczegółowy opis wskaźników technicznych, które zostały użyte do analizy danych BTC/USDT.

## 1. **SMA (Simple Moving Average) – Prosta Średnia Krocząca**

SMA to średnia z cen zamknięcia z ostatnich \(N\) dni. Jest to wskaźnik trendu, który pomaga zidentyfikować ogólny kierunek cen.

### Wzór:
\[
SMA = \frac{C_1 + C_2 + ... + C_N}{N}
\]
Gdzie:
- \(C_1, C_2, ..., C_N\) to ceny zamknięcia z ostatnich \(N\) dni.
- \(N\) to liczba dni.

### Interpretacja:
- Cena powyżej SMA może sugerować trend wzrostowy.
- Cena poniżej SMA może sugerować trend spadkowy.

### Przykład w Pythonie:
```python
data['SMA'] = talib.SMA(data['close'], timeperiod=14)
