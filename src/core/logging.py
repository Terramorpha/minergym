import logging
import os
from datetime import datetime

def setup_logger(name='root', *, filename=None):
    """
    Sets up and returns a logger that writes to both console and a file in logs directory.
    
    Args:
        name (str): Name of the logger (default: 'root')
        filename (str, optional): Specific filename for the log file. If None, generates a timestamp-based name.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # If no filename provided, create one with timestamp
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{name}.log"
    
    # Create full path for log file
    log_file = os.path.join('logs', filename)
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Only configure logger if it hasn't been configured before
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create formatters
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger 
