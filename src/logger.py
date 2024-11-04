import logging


# Utwórz loggera
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Utwórz handlera do konsoli
console_handler = logging.StreamHandler()

# Ustaw format dla handlera
formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(formatter)

# Dodaj handler do loggera
logger.addHandler(console_handler)