from enum import Enum


BALANCES              = "balances"
ASSET                 = "asset"
FREE                  = "free"
LOCKED                = "locked"
SYMBOLS               = "symbols"
SYMBOL                = "symbol"
FILTERS               = "filters"
FILTER_TYPE           = "filterType"
LOT_SIZE              = "LOT_SIZE"
STEP_SIZE             = "stepSize"
NOTIONAL              = "notional"
MIN_NOTIONAL          = "minNotional"
FILLED                = "FILLED"
NEW                   = "NEW"
EXECUTED_QTY          = "executedQty"
PRICE                 = "price"
SIDE                  = "side"
BUY                   = "BUY"
SELL                  = "SELL"
ORDER_ID              = "orderId"
TIME                  = "time"
STATUS                = "status"
WORKING_TIME          = "workingTime"
ORIG_QTY              = "origQty"
CUMMULATIVE_QUOTE_QTY = "cummulativeQuoteQty"
CRYPTO_AMOUNT_FREE    = "crypto_amount_free"
CRYPTO_AMOUNT_LOCKED  = "crypto_amount_locked"

BINANCE_API_KEY    = "BINANCE_API_KEY"
BINANCE_SECRET_KEY = "BINANCE_SECRET_KEY"
FIREBASE_KEY_PATH = "FIREBASE_KEY_PATH"


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

