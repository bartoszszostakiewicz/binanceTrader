from enum import Enum
from typing import Dict
from observable import *


#########################################################################################
#GLOBAL VARIABLES START
#########################################################################################
LOGGING_LEVEL = Config()
POWER_STATUS = PowerStatus()
STRATEGIES = Strategies()
PAIRS = Pairs()
MONITORING = Monitoring()
#########################################################################################
#GLOBAL VARIABLES END
#########################################################################################

#########################################################################################
#FIREBASE PATH VARIABLES START
#########################################################################################
DATABASE_PATH                   = "/CryptoTrading"
POWER_STATUS_PATH               = DATABASE_PATH + "/__Power__"
CONFIG_PATH                     = DATABASE_PATH + "/Config"
HEARTBEAT_PATH                  = DATABASE_PATH + "/Heartbeat"
ORDERS_PATH                     = DATABASE_PATH + "/Orders"
PAIRS_PATH                      = CONFIG_PATH   + "/Pairs"
STRATEGIES_PATH                 = CONFIG_PATH   + "/Strategies"
LOGGING_VARIABLE_PATH           = CONFIG_PATH   + "/LOGGING_LEVEL"
MONITORING_PATH                 = CONFIG_PATH   + "/ShowBuyOrders"
WALLET_PATH                     = CONFIG_PATH   + "/Wallet"
PROFIT_PATH                     = WALLET_PATH   + "/Profit"
#########################################################################################
#FIREBASE PATH VARIABLES END
#########################################################################################

BALANCES              = "balances"
ASSET                 = "asset"
AMOUNT                = "amount"
SELL_PRICE            = "sell_price"
BUY_PRICE             = "buy_price"
TIMESTAMP             = "timestamp"
STRATEGY              = "strategy"
PROFIT                = "profit"
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
PENDING               = "PENDING"
EXECUTED_QTY          = "executedQty"
PRICE                 = "price"
SIDE                  = "side"
BUY                   = "BUY"
SELL                  = "SELL"
ORDER_ID              = "orderId"
ORDER_TYPE            = "order_type"
TIME                  = "time"
STATUS                = "status"
WORKING_TIME          = "workingTime"
ORIG_QTY              = "origQty"
CUMMULATIVE_QUOTE_QTY = "cummulativeQuoteQty"
CRYPTO_AMOUNT_FREE    = "crypto_amount_free"
CRYPTO_AMOUNT_LOCKED  = "crypto_amount_locked"
CANCELED              = "CANCELED"

BINANCE_API_KEY       = "BINANCE_API_KEY"
BINANCE_SECRET_KEY    = "BINANCE_SECRET_KEY"
FIREBASE_KEY_PATH     = "FIREBASE_KEY_PATH"


POOR_ORPHAN   = "poor_orphan"
CRAZY_GIRL    = "crazy_girl"
SENSIBLE_GUY  = "sensible_guy"


FEE_SELL_BINANCE_VALUE = 0.00075
FEE_BUY_BINANCE_VALUE  = 0.00075

PRICE_TRESHOLD = 0.25

MAX_ORDERS_HISTORY_IN_CRYPTO_PAIRS = 25


class TradeState(Enum):
    MONITORING      = 1
    SELLING         = 2
    COOLDOWN        = 3


