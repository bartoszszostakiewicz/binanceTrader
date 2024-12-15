from dataclasses import dataclass
from typing import Dict
from logger import logger, logging

@dataclass
class Config:
    _logging_level: int = logging.DEBUG

    @property
    def logging_level(self):
        return self._logging_level

    @logging_level.setter
    def logging_level(self, value):
        # Sprawdzanie poprawności poziomu logowania
        valid_levels = {logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL}
        if value not in valid_levels:
            valid_levels_str = {f"{logging.getLevelName(level)} - {level}" for level in valid_levels}
            logger.error(f"Invalid logging level: {value}. Choose one of {', '.join(valid_levels_str)}.")
        else:
            self._logging_level = value
            logger.debug(f"Logging level set to {logging.getLevelName(value)}")

@dataclass
class TradeStrategy:
    name: str
    buy_increase_indicator: float
    profit_target: float
    cooldown: int
    timeout: int

@dataclass
class PowerStatus:
    power_status = False

@dataclass
class Pairs:
    pairs = {
    "BTCUSDC"  : { "strategy_allocation": { "crazy_girl": 1, "poor_orphan": 0, "sensible_guy": 0 }, "trading_percentage": 1 },
    "ETHUSDC"  : { "strategy_allocation": { "crazy_girl": 1, "poor_orphan": 0, "sensible_guy": 0 }, "trading_percentage": 1 },
    "LTCUSDC"  : { "strategy_allocation": { "crazy_girl": 1, "poor_orphan": 0, "sensible_guy": 0 }, "trading_percentage": 1 },
    "WBETHUSDT": { "strategy_allocation": { "crazy_girl": 1, "poor_orphan": 0, "sensible_guy": 0 }, "trading_percentage": 1 },
    "SHIBUSDT" : { "strategy_allocation": { "crazy_girl": 1, "poor_orphan": 0, "sensible_guy": 0 }, "trading_percentage": 1 },
    "XLMUSDT"  : { "strategy_allocation": { "crazy_girl": 1, "poor_orphan": 0, "sensible_guy": 0 }, "trading_percentage": 1 },
}

@dataclass
class Monitoring:
    show_buy_orders = False

@dataclass
class Update:
    update = False
    version = None


class Strategies:
    strategies: Dict[str, TradeStrategy]  = {
    "crazy_girl": TradeStrategy(name="crazy_girl", buy_increase_indicator=0.001, profit_target=0.996, timeout=1000, cooldown=1000),
    "poor_orphan": TradeStrategy(name="poor_orphan", buy_increase_indicator=0.001, profit_target=0.996, timeout=1000, cooldown=1000),
    "sensible_guy": TradeStrategy(name="sensible_guy", buy_increase_indicator=0.001, profit_target=0.996, timeout=1000, cooldown=1000),
}