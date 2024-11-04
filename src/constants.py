from enum import Enum


POOR_ORPHAN = "poor_orphan"
CRAZY_GIRL = "crazy_girl"
SENSIBLE_GUY = "sensible_guy"

class TradeState(Enum):
    MONITORING = 1
    WAITING_FOR_SELL = 2
    WAITING_FOR_BUY_BACK = 3

