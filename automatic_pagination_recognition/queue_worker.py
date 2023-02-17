import json
import os
import sys
from datetime import datetime

import validators
from bson.objectid import ObjectId
from urllib.parse import urlparse
import logging

from autopager.autopager import get_shared_autopager
from autopager.preprocessing import generate_page_component
from utils.database import event_source_awaiting_check, queue_result
from utils.load_env import RABBIT_ACCOUNT, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT, EVENT_QUEUE
from utils.pika_publisher import publish_message, publish_error
from utils.pika_queue import PikaQueue

MAX_EXTRACTOR_URLS = 25
QUEUE_NAME = EVENT_QUEUE


def main():
    # working_queue.DeclareQueue(QUEUE_NAME)
    def callback(ch, method, properties, body):
        decoded_data = json.loads(body.decode())
        decoded_url = decoded_data['url']
        decoded_tag = decoded_data['tag']
        try:
            if decoded_tag == 'event_post_urls':
                if len(decoded_url) > 1:
                    event_post_workflow(decoded_url)
            else:
                decoded_url = decoded_url.strip('"')
                print(" [x] Received %r" % decoded_url)
                if validators.url(decoded_url):
                    if decoded_tag == 'multi_page_failed':
                        multi_page_failed_workflow(decoded_url)
                    elif decoded_tag == 'event_source_url':
                        event_source_workflow(decoded_url)
                else:
                    print("Not a valid url, pass task.")
        except Exception as e:
            if QUEUE_NAME == EVENT_QUEUE:
                publish_error(decoded_url)
            print(f"Error! url: {decoded_url} ({e})")
        print(" [x] Done")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def event_source_workflow(page_url):
        _uid = ObjectId()
        page_urls = [page_url]
        page_domain = urlparse(page_url).netloc

        # finding pagination information
        logging.info("Executing Pagination Recognition...")
        autopager = get_shared_autopager()
        page_component = generate_page_component(page_url)
        result_urls = autopager.urls(page_component["html"], page_url, direct=True, prev=False, next=False)
        result_urls = list(set(result_urls))

        # check if result urls is valid
        print("Checking result_urls...")
        for url in result_urls:
            if not validators.url(url):
                print("Invalid： ", url)
            elif urlparse(url).netloc != page_domain:
                print("Not The Same Domain: ", url)
            elif url not in page_urls:
                page_urls.append(url)

        # check result urls amounts prevent exceed ETL limits
        if len(page_urls) > MAX_EXTRACTOR_URLS:
            print("Reduce page_urls data. (page_urls exceeds the limit)")
            page_urls = page_urls[:MAX_EXTRACTOR_URLS]

        # add result to MongoDB
        new_data = {"tid": _uid, "url": page_urls[0], "urls": page_urls[1:], "created_time": datetime.now()}
        page_result = queue_result.add_page(new_data)
        if page_result["status"] is True and page_result["tid"] is not None:
            page_result = event_source_awaiting_check.add_page(new_data)
            publish_result(page_result)


    def multi_page_failed_workflow(page_url):
        _uid = ObjectId()

        # add result to MongoDB
        new_data = {"tid": _uid, "url": page_url, "urls": [], "created_time": datetime.now()}
        page_result = queue_result.add_page(new_data)
        if page_result["status"] is True and page_result["tid"] is not None:
            page_result = event_source_awaiting_check.add_page(new_data)
            publish_result(page_result)

    def event_post_workflow(event_post_urls):
        _uid = ObjectId()
        event_post_urls = list(set(event_post_urls))

        # check result urls amounts prevent exceed ETL limits
        if len(event_post_urls) > MAX_EXTRACTOR_URLS:
            print("Reduce event_post_urls data. (event_post_urls exceeds the limit.)")
            event_post_urls = event_post_urls[:MAX_EXTRACTOR_URLS]

        # add result to MongoDB
        new_data = {"tid": _uid, "url": event_post_urls[0], "urls": event_post_urls[1:], "created_time": datetime.now()}
        page_result = queue_result.add_page(new_data)
        if page_result["status"] is True and page_result["tid"] is not None:
            page_result = event_source_awaiting_check.add_page(new_data)
            publish_result(page_result)

    def publish_result(result: dict):
        if result["status"] is False or result["tid"] is None:
            print("Failed! Bypass this url.")
        else:
            if QUEUE_NAME == EVENT_QUEUE:
                print("Publish to ExtractQueue.")
                publish_message(result["tid"])
            print("Success! result tid: ", result["tid"])

    working_queue.GetFromQueue(QUEUE_NAME, callback, False)


def nothing(ch, method, properties, body):
    print(body)


if __name__ == "__main__":
    try:
        working_queue = PikaQueue(RABBIT_HOST, RABBIT_PORT,
                                  RABBIT_ACCOUNT, RABBIT_PASSWORD)
    except Exception as e:
        print(f"Problem occurred when connected to RabbitMQ ({e})")
    try:
        print("Start consuming EventGO data")
        main()
    except KeyboardInterrupt:
        print("Interrupted, stop consuming data...")
        working_queue.Close()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
