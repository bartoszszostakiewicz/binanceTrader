import logging
import colorlog

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a StreamHandler for the console
console_handler = logging.StreamHandler()

# Create a formatter with color support and improved style
formatter = colorlog.ColoredFormatter(
    '%(asctime)s [%(log_color)s%(levelname)-5s%(reset)s] : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',  # Add timestamps for better context
    log_colors={
        'DEBUG': 'yellow',      # Yellow for DEBUG
        'INFO': 'green',        # Green for INFO
        'WARNING': 'yellow',    # Orange-yellow for WARNING
        'ERROR': 'red',         # Red for ERROR
        'CRITICAL': 'white,bg_red',  # White on red for CRITICAL
    }
)

# Set the formatter for the console handler
console_handler.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(console_handler)

