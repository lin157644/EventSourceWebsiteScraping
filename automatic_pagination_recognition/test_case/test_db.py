from utils.database import event_source_awaiting_check, event_source_extraction
from bson.objectid import ObjectId
from datetime import datetime


def test_add_page():
    new_component = {"tid": ObjectId(), "url": "https://123.com", "urls": ["https://456.com", "https://789.com"],
                     "created_time": datetime.now()}
    result = event_source_awaiting_check.add_page(new_component)
    print(result)


def find_unchecked_page():
    results = event_source_awaiting_check.retrieve_pages()
    for result in results:
        print(result)


def delete_db_page():
    option = input("Select DB 1: event_source_extraction, 2:event_source_awaiting_check")
    confirm = input("Do you really want to delete DB datas??")
    if type(confirm) is str and confirm == "y":
        if type(option) is str:
            if option == "1":
                confirm = input("Do you really want to delete DB datas????")
                if type(confirm) is str and confirm == "y":
                    print("Delete event_source_extraction datas")
                    results = event_source_extraction.retrieve_pages()
                    print("Delete", len(results), "datas")
                    for result in results:
                        event_source_extraction.delete_page(result["tid"])
                    return
            elif option == "2":
                confirm = input("Do you really want to delete DB datas????")
                if type(confirm) is str and confirm == "y":
                    print("Delete event_source_awaiting_check datas")
                    results = event_source_awaiting_check.retrieve_pages()
                    print("Delete", len(results), "datas")
                    for result in results:
                        event_source_awaiting_check.delete_page(result["tid"])
                    return
    print("Safe Protection! No data delete!")


if __name__ == '__main__':
    # test_add_page()
    # find_unchecked_page()
    # delete_db_page()
    pass
