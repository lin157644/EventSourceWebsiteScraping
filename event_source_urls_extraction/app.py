from fastapi import FastAPI
import uvicorn
import validators
from utils.load_env import RABBIT_ACCOUNT, RABBIT_PASSWORD, RABBIT_HOST, RABBIT_PORT, SOURCE_QUEUE
from utils.pika_queue import PikaQueue
from EvaluateMultitaskModelAPI import DiscoveryAgent

app = FastAPI()
agent = DiscoveryAgent()
source_queue = PikaQueue(RABBIT_HOST, RABBIT_PORT,
                         RABBIT_ACCOUNT, RABBIT_PASSWORD)


@app.get('/create_discovery_agent')
def create_event_source_discovery(source_link: str):
    if validators.url(source_link):
        source_queue.AddToQueue(SOURCE_QUEUE, source_link)
    return 200


@app.get('/get_event_source')
def get_event_source_link(source_link: str):
    if validators.url(source_link):
        urls = agent.Step(source_link, 0.7836282583958368, True)
    return urls[0]


if __name__ == "__main__":
    uvicorn.run(app='app:app', host="0.0.0.0",
                port=8000, reload=True, debug=True)
