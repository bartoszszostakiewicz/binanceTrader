import logging
import colorlog

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()

formatter = colorlog.ColoredFormatter(
    '%(asctime)s [%(log_color)s%(levelname)-5s%(reset)s] : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    log_colors={
        'DEBUG': 'yellow',      # Yellow for DEBUG
        'INFO': 'green',        # Green for INFO
        'WARNING': 'yellow',    # Orange-yellow for WARNING
        'ERROR': 'red',         # Red for ERROR
        'CRITICAL': 'white,bg_red',  # White on red for CRITICAL
    }
)

console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

