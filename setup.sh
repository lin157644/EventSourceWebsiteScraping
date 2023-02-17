#!/bin/bash
export PYTHONPATH="/root/EventGo"
cd /root/EventGo/

tmux new-session -d -s discovery_API 'python3 event_source_urls_extraction/app.py'
tmux new-session -d -s page_discovery 'python3 event_source_urls_extraction/page_discovery_worker.py'
tmux new-session -d -s pagination 'python3 automatic_pagination_recognition/queue_worker.py'
