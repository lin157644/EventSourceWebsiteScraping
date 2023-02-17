import time

from utils.pika_queue import PikaQueue
from utils.load_env import RABBIT_ACCOUNT, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT, SOURCE_QUEUE, EVENT_QUEUE
from EvaluateMultitaskModelAPI import DiscoveryAgent
import os
import sys
import pandas as pd
import validators
import logging
FORMAT = '%(asctime)s %(levelname)s: %(message)s'
try:
    working_queue = PikaQueue(RABBIT_HOST, RABBIT_PORT, RABBIT_ACCOUNT, RABBIT_PASSWORD)
except Exception as e:
    print(f"Problem occured when connected to RabbitMQ ({e})")

PASS_TO_PAGINATION = True  # allow passing url to automatic pagination recognition
OUTPUT_FILE_PATH = "test_1000_pages.csv"  # event source urls output file path name
SAVE_TO_EVNET_SOURCE_URLS_FILE = False  # allow save event source url to file
zero_count = 0
agent = DiscoveryAgent()


def main():
    def callback(ch, method, properties, body):
        try:
            decoded_url = body.decode()
            decoded_url = decoded_url.strip('"')
            print("decoded_url:", decoded_url)
            event_source_url = discoveryEventSourcePage(decoded_url)
            if len(event_source_url) == 0:
                global zero_count
                zero_count += 1
            if PASS_TO_PAGINATION:
                add_to_new_queue(event_source_url)
            else:
                print("Skip passing URL to event_queue!!!")
            if SAVE_TO_EVNET_SOURCE_URLS_FILE:
                save_as_csv(event_source_url)
        except Exception as e:
            print("EventSourcePage discovery Failed")
        finally:
            print("EventSourcePage discovery Done!")
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def discoveryEventSourcePage(url):
        start_time = time.time()
        try:
            # urls = agent.Step(url, 0.8025579568586851, True)
            urls, cost_time_buffer = agent.Step(url, 0.7836282583958368, True)
            # print(urls)
            if type(urls) != list:
                urls = []
        except Exception as e:
            urls = []
        finally:
            time_cost["total"].append((time.time() - start_time))
            time_cost["database"].append(cost_time_buffer[0])
            time_cost["crawler"].append(cost_time_buffer[1])
            time_cost["model"].append(cost_time_buffer[2])
            time_cost_url.append(url)
            event_source_links.append(len(urls))
            print(f"{(time.time() - start_time):8.2f}s {urls}")
        return urls

    def add_to_new_queue(event_source_url):
        print("Adding urls to Event_queue...")
        for url in event_source_url:
            if validators.url(url):
                data = {
                    'url': url,
                    'tag': "event_source_url"
                }
                working_queue.AddToQueue(EVENT_QUEUE, data)
            else:
                print(url)
        print("Finish adding url to Event_queue...")

    def save_as_csv(event_source_url):
        if len(event_source_url) > 0:
            # check file exists or creates it before adding urls
            if not os.path.exists(OUTPUT_FILE_PATH):
                df = pd.DataFrame({"websites": []})
                df.to_csv(OUTPUT_FILE_PATH, index=False, encoding='utf-8-sig')
            urls = pd.DataFrame(data=event_source_url)
            urls.to_csv(OUTPUT_FILE_PATH, mode='a', index=False, header=False, encoding='utf-8-sig')
        print("Finish adding url to", OUTPUT_FILE_PATH, "...")

    working_queue.GetFromQueue(SOURCE_QUEUE, callback, False)


if __name__ == "__main__":
    try:
        print("Start consuming event source data")
        time_cost = {"total": [], "database": [], "crawler": [], "model": []}
        time_cost_url = []
        event_source_links = []
        path = 'ploicyLog'
        if not os.path.exists(path):
            os.makedirs(path)
        main()
        # logging.getLogger('').handlers = []  ## 把 handlers 清掉，走設定好的logging.basicConfig
        # logging.basicConfig(level=logging.INFO, filename='ploicyLog/candidate_url.log', filemode='a',
        #                     format=FORMAT)
    except KeyboardInterrupt:
        print("Interrupted, stop consuming data...")
        print("There are", zero_count, "pages with no event source!")
    finally:
        df = pd.DataFrame({"webpage": time_cost_url, "total cost time": time_cost["total"],
                           "cost time (database)": time_cost["database"], "cost time (crawler)": time_cost["crawler"],
                           "cost time (model)": time_cost["model"], "event source links": event_source_links})
        df.to_csv("cost_time.csv", index=False, encoding='utf-8-sig')
        agent.quit()
        working_queue.Close()
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

