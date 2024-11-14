# config.py

import configparser
from utils.logger import app_logger  
import os


def load_config():
    config = configparser.ConfigParser()
    config_file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_file_path)

    return {
        'api_key': config['OPENAI']['api_key'],
        'model': config['OPENAI']['model'],
        'emb_model': config['OPENAI']['emb_model'],
        'max_size_mb': float(config['IMAGE']['max_size']),
        'threshold' : float(config['Mapping']['threshold'])
    }

