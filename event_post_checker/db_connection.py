from pymongo import MongoClient
from utils.load_env import *


def get_database_event_go():
    client = MongoClient(f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST_EVENT_GO}:{MONGO_PORT_EVENT_GO}")
    return client[DATABASE_PAGE]


def get_database_page():
    client = MongoClient(f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST_PAGE}:{MONGO_PORT_PAGE}")
    return client[DATABASE_PAGE]


def get_database_etl():
    client = MongoClient(f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST_ETL}:{MONGO_PORT_ETL}")
    return client[DATABASE_ETL]


def get_queue_collection():
    return get_database_page().get_collection(QUEUE_COLLECTION)


def get_auto_extraction_collection():
    return get_database_page().get_collection(AUTO_EXTRACTION_COLLECTION)


def get_extractors_collection():
    return get_database_etl().get_collection(EXTRACTOR_COLLECTION)


def get_auto_extraction_urls_collection():
    return get_database_etl().get_collection(AUTO_EXTRACTION_URL_COLLECTION)


def get_temp_extracted_data_collection():
    return get_database_etl().get_collection(TEMP_EXTRACTED_DATA_COLLECTION)
