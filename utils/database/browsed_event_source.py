from pymongo import MongoClient
from utils.load_env import MONGO_USER, MONGO_PASSWORD, MONGO_PORT_EVENT_GO, DATABASE_EVENT_GO, \
    BROWSED_EVENT_SOURCE_COLLECTION, MONGO_HOST_EVENT_GO
from datetime import datetime, timedelta

# print(f"Loading settings, database:{DATABASE_EVENT_GO}, collection:{BROWSED_EVENT_SOURCE_COLLECTION}")

MONGO_DETAILS = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST_EVENT_GO}:{MONGO_PORT_EVENT_GO}"
client = MongoClient(MONGO_DETAILS)
database = client[DATABASE_EVENT_GO]
page_collection = database.get_collection(BROWSED_EVENT_SOURCE_COLLECTION)


# add page_domain and event source page in database
def add_page(page_data: dict):
    page_collection.insert_one(page_data)


def find_page_domain(url):
    if page_collection.count_documents({"page_domain": url}) > 0:
        return True
    return False


# return DB event source page url
def return_already_find(url):
    results = page_collection.find({"page_domain": url})
    already_find = []
    for result in results:
        already_find.append(result['click_url'])
    already_find = list(filter(None, already_find))
    return already_find


# delete expired event source page url from database
def delete_page(url):
    results = page_collection.find({"page_domain": url})
    expiration_time = datetime.now() - timedelta(days=7)
    for result in results:
        if result['created_time'] < expiration_time:
            page_collection.delete_one({"_id": result['_id']})
        else:
            return False
    return True


def update_page(url):
    return delete_page(url)


def update_last_used_time(url):
    page_collection.update_many({"page_domain": url}, {"$set": {"last_used_time": datetime.now()}})
