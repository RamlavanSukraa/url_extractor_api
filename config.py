import configparser
import os
from utils.logger import app_logger

logger = app_logger  # Initialize the logger


_config_data = None

def load_config():
    """
    Load configuration values from the config.ini file.
    """

    global _config_data

    if _config_data is not None:
        return _config_data

    config = configparser.ConfigParser()
    config_file_path = os.path.join(os.path.dirname(__file__), 'config.ini')

    # Check if configuration file exists
    if not os.path.exists(config_file_path):
        logger.error(f"Configuration file not found at {config_file_path}")
        raise FileNotFoundError(f"Configuration file not found at {config_file_path}")

    try:
        config.read(config_file_path)
        logger.info("Loading configuration file...")
        # Parse and return configuration values
        _config_data = {
            'api_key': config['OPENAI']['api_key'],
            'model': config['OPENAI']['model'],
            'emb_model': config['OPENAI']['emb_model'],
            'max_size_mb': float(config['IMAGE']['max_size']),
            'threshold': float(config['Mapping']['threshold'])
        }
        logger.info("Configuration file loaded successfully...")
        return _config_data

    except KeyError as e:
        logger.error(f"Missing required configuration key: {e}")
        raise KeyError(f"Missing required configuration key: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while loading configuration: {str(e)}")
        raise
