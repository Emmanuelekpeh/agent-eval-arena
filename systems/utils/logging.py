import logging
import os
import sys
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Set up logging format
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

# Create a formatter
formatter = logging.Formatter(log_format, date_format)

# Create file handler with timestamp in filename
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(logs_dir, f'battle_arena_{timestamp}.log')
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)  # More detailed logs in file

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.DEBUG) # Set console level to DEBUG

# Configure root logger using basicConfig
logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler])

# Get a logger instance (optional, can use logging directly)
logger = logging.getLogger(__name__) # Can now use logging.getLogger('some_name') or just logging.debug(), etc.

def set_log_level(level):
    """
    Set the logging level for the root logger and handlers.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.getLogger().setLevel(level)
    console_handler.setLevel(level)
    # Note: File handler level remains DEBUG unless changed here
    
def log_exception(e):
    """
    Log an exception with traceback using the root logger.
    
    Args:
        e: Exception to log
    """
    import traceback
    logging.error(f"Exception: {str(e)}")
    logging.error(traceback.format_exc()) 