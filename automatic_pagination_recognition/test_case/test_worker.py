import validators
from utils.pika_queue import PikaQueue
from utils.load_env import RABBIT_ACCOUNT, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT, EVENT_QUEUE

event_queue = PikaQueue(RABBIT_HOST, RABBIT_PORT, RABBIT_ACCOUNT, RABBIT_PASSWORD)
print("EVENT_QUEUE: ", EVENT_QUEUE)

test_pages = [
    'http://www.travelinstyle.com.tw/media_p1.html',
]

print("Adding urls to Event_queue...")

for url in test_pages:
    if validators.url(url):
        print(url)
        data = {
            'url': url,
            'tag': "event_source_url"
        }
        event_queue.AddToQueue(EVENT_QUEUE, data)
    else:
        print(url)

event_queue.Close()
print("Finish adding url to Event_queue...")
