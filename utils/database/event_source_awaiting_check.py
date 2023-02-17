from pymongo import MongoClient
from bson.objectid import ObjectId
from utils.load_env import MONGO_HOST_EVENT_GO, MONGO_USER, MONGO_PASSWORD, MONGO_PORT_EVENT_GO, DATABASE_EVENT_GO, \
    EVENT_SOURCE_AWAITING_CHECK_COLLECTION

MONGO_DETAILS = f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST_EVENT_GO}:{MONGO_PORT_EVENT_GO}"

client = MongoClient(MONGO_DETAILS)

database = client[DATABASE_EVENT_GO]

page_collection = database.get_collection(EVENT_SOURCE_AWAITING_CHECK_COLLECTION)


# helpers
def page_helper(page) -> dict:
    return {
        "tid": str(page["tid"]),
        "url": page["url"],
        "urls": page["urls"],
        "created_time": page["created_time"],
    }


# Retrieve all pages present in the database
def retrieve_pages():
    pages = []
    for page in page_collection.find():
        pages.append(page_helper(page))
    return pages


def add_page(page_data: dict) -> dict:
    status_data = {"status": False, "tid": None}
    try:
        new_page = page_collection.find_one({"tid": ObjectId(page_data['tid'])})
        if new_page is None:
            page_collection.insert_one(page_data)
            new_page = page_collection.find_one({"tid": ObjectId(page_data['tid'])})
            status_data = {"status": True, "tid": str(new_page["tid"])}
    except Exception as e:
        print("An exception occurred @add_page::", e)
    return status_data


# Retrieve a page with a matching ID
def retrieve_page(tid: str) -> dict:
    page = page_collection.find_one({"tid": ObjectId(tid)})
    if page:
        return page_helper(page)


# Update a page with a matching ID
def update_page(tid: str, data: dict):
    # Return false if an empty request body is sent.
    if len(data) < 1:
        return False
    try:
        page = page_collection.find_one({"tid": ObjectId(tid)})
        if page:
            updated_page = page_collection.update_one(
                {"tid": ObjectId(tid)}, {"$set": data}
            )
            if updated_page:
                return True
    except Exception as e:
        print("An exception occurred @update_page::", e)
    return False


# Delete a page from the database
def delete_page(tid: str):
    page = page_collection.find_one({"tid": ObjectId(tid)})
    if page:
        page_collection.delete_one({"tid": ObjectId(tid)})
        return True
    return False
