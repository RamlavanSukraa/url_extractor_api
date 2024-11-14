# logger.py

import logging

def setup_logger(name, level=logging.INFO):
    
    # Set up a logger that writes only to the console.
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler()  # Create a console handler
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicate logs
    if not logger.hasHandlers():
        logger.addHandler(console_handler)

    return logger

# Example logger instance
app_logger = setup_logger('app_logger')
app_logger.info('Logger initialized')
