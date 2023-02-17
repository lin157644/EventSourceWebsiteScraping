#!/usr/bin/env python
# coding: utf-8

# In[1]:


import pickle
import os
import numpy as np
from bs4 import BeautifulSoup
from url_normalize import url_normalize
import urllib
from urllib.parse import urljoin, urlparse
from src import URLTool
from src import StringTool
import tensorflow as tf
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from sklearn.preprocessing import MinMaxScaler
import ssl
import copy

WINDOW_SIZE = "1920,1080"
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument(f"--window-size={WINDOW_SIZE}")
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument("--lang=zh-tw")
ssl._create_default_https_context = ssl._create_unverified_context


# In[7]:


class Env():
    # def __init__(self, train_group, window_len, negativeReward=0.3, rewardweight = 0.1):
    def __init__(self, train_group, negativeReward=-0.1, rewardweight=0.1):
        self.homepage = ""
        self.currentURL = ""
        self.anchorText = []
        self.tagPath = []
        self.hrefs = []
        self.coordinates = []
        # self.positivePages = #[i+'/' if i[-1]!='/' else i for i in list(train_group['Event Source Page URL'])]
        self.positivePages = URLTool.GetNormalizaUrl(list(train_group[
                                                              'Event Source Page URL']))  # ['http'+i[5:] if i[0:5]=='https' else i for i in self.positivePages]
        self.train_group = train_group
        self.negativeReward = negativeReward
        self.rewardweight = rewardweight
        self.web = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.web.set_page_load_timeout(30)
        self.web.implicitly_wait(5)
        if os.path.isfile('PageScore_olddata.pkl'):
            with open('PageScore_olddata.pkl', 'rb') as f:
                self.pageScore = pickle.load(f)
        else:
            self.pageScore = {}
        self.pageScore = {}

    def LeaveThisURL(self, page, href):
        if not URLTool.IsUrlString(href):
            href = urljoin(page, href)
            if not URLTool.IsUrlString(href):
                return False
        return True

    def GetCoordinate(self, element):
        text = []
        while element.size['width'] == 0:
            element = element.find_element(By.XPATH, '..')
        x = element.location['x']
        y = element.location['y']
        width = element.size['width']
        height = element.size['height']
        return x, y, width, height

    def GetTagPath(self, element):
        nowtag = element.tag_name
        thispath = [nowtag]
        while True:
            try:
                element = element.find_element(By.XPATH, '..')
                thispath.append(element.tag_name)
            except Exception as e:
                break
        thispath = list(reversed(thispath))
        return thispath

    def get_tag_path(self, element):
        tag_path = [element.name]
        while True:
            try:
                element = element.parent
                tag_path.append(element.name)
            except Exception:
                break
        tag_path.remove('[document]')
        return list(reversed(tag_path))

    def GetTagDeepth(self, element):
        depth = 0
        while True:
            try:
                element = element.find_element(By.XPATH, '..')
                depth += 1
            except Exception as e:
                break
        return depth

    def GetPositiveHrefIndex(self, hrefs):
        hrefs = URLTool.GetNormalizaUrl(hrefs)
        positiveIndexs = []
        for index, href in enumerate(hrefs):
            if href in self.positivePages:
                positiveIndexs.append(index)
        return positiveIndexs

    def GetHrefsContentAndHrefs(self, page=None, gettagpath=False, tagpathwithouttree=True):
        hrefs = []
        coordinates = []
        tagPaths = []
        text = []
        try:
            self.web.get(page)
            html = self.web.page_source
            page = self.web.current_url
        except Exception as e:
            print("Cannot Open:", e)
            if gettagpath:
                return [], [], [], []
            return [], [], []
        parse_html = BeautifulSoup(html, 'html.parser')
        elems = parse_html.find_all(href=True)
        # elems = self.web.find_elements_by_xpath("//*[@href]")
        preprocessnum = 0
        print(f"Current Total Anchors: {len(elems)}...")
        for elem in elems:
            preprocessnum += 1
            # print('{}/total:{}'.format(preprocessnum, len(elems)))
            try:
                tag_text = elem.getText()
                tag_href = elem['href']
                if tag_text == '':
                    continue
                if not self.LeaveThisURL(page, tag_href):
                    continue
                else:
                    tag_href = urljoin(page, tag_href)
                if tag_href == '' or '#' in tag_href:
                    continue
                text.append(StringTool.CleanString(tag_text))
                hrefs.append(tag_href)
                if gettagpath:
                    tagPaths.append(self.get_tag_path(elem))
                # if elem.get_attribute('textContent') == '':
                #     continue
                # if not self.LeaveThisURL(page, elem.get_attribute("href")):
                #     continue
                # href = elem.get_attribute("href")
                # if href == '' or '#' in href:
                #     continue
                # coordinates.append(self.GetCoordinate(elem))
                # text.append(StringTool.CleanString(elem.get_attribute('textContent')))
                # # print(StringTool.CleanString(elem.get_attribute('textContent')))
                # hrefs.append(href)
                # if gettagpath:
                #     tmpelem = elem
                #     tagPaths.append(self.GetTagPath(elem))
            except Exception as e:
                print(e)
                continue
        coordinates = self.NormalizeCoordinate(coordinates)
        # print("text:", text)
        # print("hrefs:", hrefs)
        # print("coordinates:", coordinates)
        # print("tagPaths:", tagPaths)
        if not gettagpath:
            return text, hrefs, coordinates
        else:
            return text, hrefs, coordinates, tagPaths

    def NormalizeCoordinate(self, coordinates):
        if (len(list(coordinates)) == 0):
            return []
        Xs, Ys, widths, heights = zip(*list(coordinates))
        minx = min(Xs)
        maxx = max(Xs)
        miny = min(Ys)
        maxy = max(Ys)
        if (maxx - minx != 0 and maxy - miny != 0):
            rate = (maxy - miny) / (maxx - minx)
        else:
            return coordinates
        scaler = MinMaxScaler((0, 1))
        newX = scaler.fit_transform(np.array(Xs).reshape((np.array(Xs).shape[0], 1)))[:, 0]
        xscale = scaler.scale_[0]
        scaler = MinMaxScaler((0, rate))
        newY = scaler.fit_transform(np.array(Ys).reshape((np.array(Ys).shape[0], 1)))[:, 0]
        yscale = scaler.scale_[0]  # xscale * rate
        newWidths = [w * xscale for w in widths]
        newHeights = [h * yscale for h in heights]
        coordinate = zip(newX, newY, newWidths, newHeights)
        return coordinate

    def GetCurrentURL(self):
        return self.currentURL

    def reset(self, homepage, url=None, gettagpath=False, tagpathwithouttree=True):
        self.homepage = homepage
        if url is None:
            if gettagpath:
                self.anchorText, self.hrefs, self.coordinates, self.tagPath = self.GetHrefsContentAndHrefs(homepage,
                                                                                                           gettagpath=gettagpath,
                                                                                                           tagpathwithouttree=tagpathwithouttree)  # set self.currentURL
            else:
                self.anchorText, self.hrefs, self.coordinates = self.GetHrefsContentAndHrefs(homepage,
                                                                                             gettagpath=gettagpath,
                                                                                             tagpathwithouttree=tagpathwithouttree)
            self.homepage = self.currentURL
        else:
            if gettagpath:
                self.anchorText, self.hrefs, self.coordinates, self.tagPath = self.GetHrefsContentAndHrefs(homepage,
                                                                                                           gettagpath=gettagpath,
                                                                                                           tagpathwithouttree=tagpathwithouttree)  # set self.currentURL
            else:
                self.anchorText, self.hrefs, self.coordinates = self.GetHrefsContentAndHrefs(homepage,
                                                                                             gettagpath=gettagpath,
                                                                                             tagpathwithouttree=tagpathwithouttree)
        if gettagpath:
            return self._next_observationWithCoordinateandTagPath()
        else:
            return self._next_observationWithCoordinate()

    def GetPositivePage(self):
        return self.positivePages

    def GetAnsAndDiscountedReward(self, hrefs, dynamicReward=False, negativeReward=None, positiveReward=None):
        if negativeReward is None:
            negativeReward = -1  # 0.1
        if positiveReward is None:
            positiveReward = 1
        ans = []
        rewards = []
        hrefs = URLTool.GetNormalizaUrl(hrefs)
        for index in range(len(hrefs)):
            if (hrefs[index] in self.positivePages):
                ans.append(1)
                rewards.append(positiveReward)
            else:
                rewards.append(negativeReward)
                ans.append(0)
        if dynamicReward:
            # rewardsdynamic = []
            rewards = []
            for index in range(len(hrefs)):
                if os.path.isfile('PageScore_olddata.pkl'):
                    with open('PageScore_olddata.pkl', 'rb') as f:
                        self.pageScore = pickle.load(f)
                if (hrefs[index] not in self.pageScore.keys()):
                    score = float(self.GetPageScore(hrefs[index]))
                    self.pageScore[hrefs[index]] = score
                    rewards.append(score)
                    with open('PageScore_olddata.pkl', 'wb') as f:
                        pickle.dump(self.pageScore, f, pickle.HIGHEST_PROTOCOL)
                else:
                    score = self.pageScore[hrefs[index]]
                    rewards.append(score)
        discountedRewards = rewards.copy()
        for i in range(len(rewards) - 1):
            reward = rewards[i]
            for j in range(i + 1, len(rewards)):
                reward += (self.rewardweight ** j) * rewards[j]
            discountedRewards[i] = reward
        return ans, discountedRewards

    def GetAns(self, hrefs):
        ans = []
        hrefs = URLTool.GetNormalizaUrl(hrefs)
        for index in range(len(hrefs)):
            if hrefs[index] == '':
                continue
            if (hrefs[index][-1] != '/'):
                hrefs[index] += '/'
            if ("https" == hrefs[index][0:5]):
                hrefs[index] = "http" + hrefs[index][5:]
            if (hrefs[index] in self.positivePages):
                ans.append(1)
            else:
                ans.append(0)
        return ans

    """def _next_observation(self):
        return self.anchorText, self.hrefs"""

    def _next_observationWithCoordinateandTagPath(self):
        return self.anchorText, self.hrefs, self.coordinates, self.tagPath

    def _next_observationWithCoordinate(self):
        return self.anchorText, self.hrefs, self.coordinates

    def step(self, href, gettagpath=False, newtagpathwithtree=False):
        nowscheme = urlparse(self.currentURL).scheme
        stepparse = urlparse(href)  # .scheme
        if (stepparse.query != ''):
            stephref = nowscheme + "://" + stepparse.netloc + stepparse.path + stepparse.params + '?' + stepparse.query
        else:
            stephref = nowscheme + "://" + stepparse.netloc + stepparse.path + stepparse.params
        self._take_action(href, gettagpath=gettagpath, newtagpathwithtree=newtagpathwithtree)
        if gettagpath:
            return self._next_observationWithCoordinateandTagPath()
        else:
            return self._next_observationWithCoordinate()

    def _take_action(self, href, gettagpath=False, newtagpathwithtree=False):
        self.currentURL = href
        if gettagpath:
            self.anchorText, self.hrefs, self.coordinates, self.tagPath = self.GetHrefsContentAndHrefs(href,
                                                                                                       gettagpath=gettagpath,
                                                                                                       tagpathwithouttree=newtagpathwithtree)
        else:
            self.anchorText, self.hrefs, self.coordinates = self.GetHrefsContentAndHrefs(href,
                                                                                         gettagpath=gettagpath)  # set self.currentURL

    def GetAnchorText(self):
        return self.anchorText

    def quit_driver(self):
        self.web.quit()
        print("Quit Webdriver")


if __name__ == '__main__':
    # print(URLTool.IsUrlString("www.ymsnp.gov.tw/main_ch/docList.aspx?uid=1583&pid=18&rn=-13693"))
    import pandas as pd

    a = Env(pd.DataFrame({"Event Source Page URL": []}), negativeReward=-0.1)
    b, c, d, e = a.GetHrefsContentAndHrefs("https://www.travel.taipei", gettagpath=True)
    # a.reset("https://chromedriver.chromium.org/downloads")
