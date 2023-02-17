import sys
import time

sys.path.append("..")

from EvaluateMultitaskModelAPI import DiscoveryAgent

start_time = time.time()
agent = DiscoveryAgent()
urls, time_list = agent.Step("https://www.sow.org.tw/event", 0.7836282583958368, True)
urls = agent.Step("http://changelife.org.tw", 0.7836282583958368, True)
urls = agent.Step("http://meetpets.org.tw", 0.7836282583958368, True)
urls = agent.Step("https://www.ncu.edu.tw/tw/events/index.php", 0.7836282583958368, True)
agent.quit()
print(f"{(time.time() - start_time):8.2f}s {urls}")
# print(f"database_time: {(time_list[0]):8.2f}s crawler_time: {(time_list[1]):8.2f}s model_time: {(time_list[2]):8.2f}s")