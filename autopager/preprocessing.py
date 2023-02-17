#!/usr/bin/env python
# coding: utf-8

# # HTML Downloader and Preprocessor

# In[5]:


import os
import re
import sys
import requests
import numpy as np
import parsel
import pathlib
from urllib.parse import urlparse
sys.path.insert(0, '..')
from autopager.htmlutils import get_every_button_and_a
from autopager.model import page_to_features


# In[6]:


from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import ssl
WINDOW_SIZE = "1920,1080"

options = Options()
options.use_chromium = True
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument(f"--window-size={WINDOW_SIZE}")
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

ssl._create_default_https_context = ssl._create_unverified_context


# In[7]:


import time


# In[8]:


DEFAULT_PROJECT_FOLDER = os.path.abspath('..')


# In[9]:


DEFAULT_PREDICT_FOLDER = os.path.abspath('..') + '/predict_folder'


# In[10]:


DEFAULT_MODEL_FOLDER = os.path.abspath('..') + '/models'


# In[11]:


IS_CONTAIN_BUTTON = True


# In[12]:


NB_TO_PY = False


# In[13]:


SCROLL_PAUSE_TIME = 1


# In[14]:


def _scrollToButtom(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")


# In[15]:


def _get_html_from_selenium(url):
    browser = Chrome(service=Service(ChromeDriverManager().install()), options=options)
    browser.implicitly_wait(10)
    browser.set_page_load_timeout(30)
    # 在瀏覽器打上網址連入
    browser.get(url)
    _scrollToButtom(browser)
    time.sleep(SCROLL_PAUSE_TIME)
    html = browser.page_source
    browser.quit()
    return html


# In[16]:


def generate_page_component(url):
    html = _get_html_from_selenium(url)
    url_obj = urlparse(url)
    return {
        "html": html,
        "parseObj": url_obj,
    }


# In[17]:


def get_selectors_from_file(html):
    sel = parsel.Selector(html)
    links = get_every_button_and_a(sel)
    xseq = page_to_features(links)
    return xseq


# In[18]:


if __name__ == '__main__':
    # _get_html_from_selenium("http://www.google.com")

    # If NB_TO_PY is true, than we convert this book to .py file
    if NB_TO_PY:
        get_ipython().system('jupyter nbconvert --to script preprocessing.ipynb')
    else:
        test_url = "https://kktix.com/events"
        page = generate_page_component(test_url)
        xseq = get_selectors_from_file(page["html"])
        print(xseq[:5])

