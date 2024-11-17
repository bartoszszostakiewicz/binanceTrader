from enum import Enum


POOR_ORPHAN   = "poor_orphan"
CRAZY_GIRL    = "crazy_girl"
SENSIBLE_GUY  = "sensible_guy"


FEE_SELL_BINANCE_VALUE = 0.00075
FEE_BUY_BINANCE_VALUE  = 0.00075

MAX_ORDERS_HISTORY_IN_CRYPTO_PAIRS = 25


class TradeState(Enum):
    MONITORING            = 1
    WAITING_FOR_SELL      = 2
    WAITING_FOR_BUY_BACK  = 3

