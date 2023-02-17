from datetime import datetime, timedelta

import validators
from bson import ObjectId

from db_connection import *
from utils.pika_queue import PikaQueue
from utils.load_env import RABBIT_ACCOUNT, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT, EVENT_QUEUE
from utils.database import event_source_awaiting_check, event_source_extraction


# recognition: add urls to event_queue, makes it been executing pagination recognition.
# Input: event_urls (list of input urls to be recognition)
# Output: start_time (when recognition starts), invalid_urls (list of urls failed validator's check)
def recognition(event_urls):
    event_queue = PikaQueue(RABBIT_HOST, RABBIT_PORT, RABBIT_ACCOUNT, RABBIT_PASSWORD)

    print("Recognition Start Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("URLs:", len(event_urls))
    print("Adding urls to Event_queue...")
    for url in event_urls:
        if validators.url(url):
            data = {
                'url': url,
                'tag': "multi_page_failed"
            }
            event_queue.AddToQueue(EVENT_QUEUE, data)
        else:
            print("Invalid ", url)
    print("Finish adding url to Event_queue...")


# check_result: find previous recognition results which failed in DCADE task, makes it redo in MDR task
# Output: start_time (when recognition starts), invalid_urls (list of urls failed validator's check)
def check_result():
    queue_collection = get_queue_collection()
    page_collection = get_auto_extraction_collection()
    etl_extractors_collection = get_extractors_collection()
    etl_auto_extraction_urls_collection = get_auto_extraction_urls_collection()

    success_count = 0
    pass_count = 0
    failed_count = 0
    created_extractors_sns = []
    predict_record = []
    build_success = []
    build_success_urls = []
    build_failed = []
    build_failed_urls = []
    failed_urls_count = 0

    single_page_status = {
        "URLs": 0,  # number of URL requests
        "APIs": 0,  # number of ETL extractors
        "RecordSets": 0,  # number of ETL extractors had valid set
        "Filters": 0,  # extractors had urls result in set
        "Posts": 0  # number of in set URLs
    }
    multiple_page_status = {
        "URLs": 0,  # number of URL requests
        "APIs": 0,  # number of ETL extractors
        "RecordSets": 0,  # number of ETL extractors had valid set
        "Filters": 0,  # extractors had urls result in set
        "Posts": 0  # number of in set URLs
    }

    try:
        print("Searching result in DB...")
        unchecked_pages = event_source_awaiting_check.retrieve_pages()
        for unchecked_page in unchecked_pages:
            post = page_collection.find_one({'tid': ObjectId(unchecked_page['tid'])})
            if post:
                new_data = {"tid": ObjectId(unchecked_page['tid']), "serialNumber": post['serialNumber'],
                            "status": post['status'], "message": post['message'], "url": unchecked_page['url'],
                            "urls": unchecked_page['urls'], "created_time": post['createdDateTime'] + timedelta(hours=8)}
                event_source_extraction.add_page(new_data)
                if not event_source_awaiting_check.delete_page(unchecked_page['tid']):
                    print("Remove awaiting data failed", unchecked_page['tid'])
                queue_post = queue_collection.find_one({'tid': post['tid']})
                page_type = None
                if queue_post:
                    if len(queue_post['urls']) == 0:
                        single_page_status['URLs'] += 1
                        predict_record.append(1)
                        page_type = "singleListPage"
                    else:
                        multiple_page_status['URLs'] += 1
                        predict_record.append(0)
                        page_type = "detailPage"
                if post['status'] != 'Failed':
                    if post['status'] == 'Success':
                        success_count += 1
                    else:
                        pass_count += 1
                    etl_post = etl_extractors_collection.find_one({'serialNumber': post['serialNumber']})
                    if etl_post:
                        if page_type == 'detailPage' and len(etl_post['setsColumns']) < 2:
                            failed_urls_count += len(etl_post['urls'])
                            build_failed_urls.extend(etl_post['urls'])
                            build_failed.append(post['serialNumber'])
                        else:
                            build_success_urls.extend(etl_post['urls'])
                            build_success.append(post['serialNumber'])
                    created_extractors_sns.append(post['serialNumber'])
                else:
                    failed_count += 1
    except Exception as e:
        print(e)

    print("Predicted:", success_count + failed_count + pass_count, "Failed:", failed_count)

    for url in build_failed_urls:
        if not validators.url(url):
            print("Invalid URL (build_failed_urls):", url)
            build_failed_urls.remove(url)

    for url in build_success_urls:
        if not validators.url(url):
            print("Invalid URL (build_success_urls):", url)
            build_success_urls.remove(url)

    print("Build Success Extractors: ", len(build_success))
    print("Success URLs : ", len(build_success_urls))
    print("Build Failed Extractors: ", len(build_failed))
    print("Failed URLs : ", len(build_failed_urls))

    success_extractors = []
    for _serialNumber in created_extractors_sns:
        post = etl_extractors_collection.find_one({"serialNumber": _serialNumber})
        if post['pageType'] == 'singleListPage':
            single_page_status['APIs'] += 1
            if len(post['setsColumns']) > 0:
                single_page_status['RecordSets'] += 1
                success_extractors.append(_serialNumber)
        elif post['pageType'] == 'detailPage':
            multiple_page_status['APIs'] += 1
            if len(post['setsColumns']) > 1:
                multiple_page_status['RecordSets'] += 1
                success_extractors.append(_serialNumber)

    for _serialNumber in success_extractors:
        post = etl_auto_extraction_urls_collection.find_one({"serialNumber": _serialNumber})
        extractor = etl_extractors_collection.find_one({"serialNumber": _serialNumber})
        if post:
            if extractor['pageType'] == 'singleListPage':
                single_page_status['Filters'] += 1
                single_page_status['Posts'] += len(post['urls'])
            else:
                multiple_page_status['Filters'] += 1
                multiple_page_status['Posts'] += len(post['urls'])

    if single_page_status['URLs'] != 0:
        print("Single Page Status (MDR):", single_page_status)
    if multiple_page_status['URLs'] != 0:
        print("Multiple Page Status (DCADE):", multiple_page_status)

    return build_success_urls, build_failed_urls


if __name__ == '__main__':
    success_urls, failed_urls = check_result()
    recognition(failed_urls)
    # TODO: check_result should use cronjob to repeat work
    pass
