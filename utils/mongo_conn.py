import urllib.parse
import re  # Added to sanitize the URI if needed
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from config import load_mongo, app_logger

# Initialize a variable to store the client and collection
_mongo_client = None
_mongo_collection = None

def connect_to_mongo(file_path=None, section='database'):
    global _mongo_client, _mongo_collection

    try:
        if _mongo_client is None or _mongo_collection is None:
            # Load configuration data
            config_data = load_mongo(file_path, section)
            mongodb_uri = config_data['MONGODB_URI']

            if config_data.get('MONGODB_USERNAME') and config_data.get('MONGODB_PASSWORD'):
                # Use credentials for remote databases
                username = urllib.parse.quote_plus(config_data['MONGODB_USERNAME'])
                password = urllib.parse.quote_plus(config_data['MONGODB_PASSWORD'])
                uri_without_credentials = re.sub(r'//.*?@', '//', mongodb_uri)
                mongodb_uri = f"mongodb://{username}:{password}@{uri_without_credentials.split('://')[1]}"
                app_logger.info("Connecting to MongoDB with credentials.")
            else:
                # Use URI as-is for local or unsecured databases
                app_logger.info("Connecting to MongoDB without credentials.")

            # Connect to MongoDB
            _mongo_client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
            db = _mongo_client[config_data['DATABASE_NAME']]
            _mongo_collection = db[config_data['COLLECTION_NAME']]
            app_logger.info(f"Database {config_data['DATABASE_NAME']} and collection {config_data['COLLECTION_NAME']} connected successfully!")

        # Return the existing connection if already initialized
        return _mongo_client, _mongo_collection

    except ServerSelectionTimeoutError as e:
        app_logger.error(f"MongoDB server selection timeout: {e}")
        raise
    except PyMongoError as e:
        app_logger.error(f"MongoDB connection error: {e}")
        raise
    except Exception as e:
        app_logger.error(f"An unexpected error occurred while connecting to MongoDB: {e}")
        raise
