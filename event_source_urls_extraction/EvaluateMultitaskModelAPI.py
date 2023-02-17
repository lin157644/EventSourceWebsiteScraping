import time

from func_timeout import func_timeout, FunctionTimedOut
import pandas as pd
import numpy as np
import os
import tensorflow as tf
import tensorflow_hub as hub
import copy
from src import PolicyDeepthEnvFixCoordinate
from Preprocess.Tokenize import Tokenize
import validators
from urllib.parse import urlparse
from datetime import datetime
from utils.database.browsed_event_source import add_page, find_page_domain, return_already_find, update_page, \
    update_last_used_time

try:
    from bert.tokenization.bert_tokenization import FullTokenizer
except:
    from bert.tokenization import FullTokenizer
from src import Tool

tf.get_logger().setLevel('WARN')
config = Tool.LoadConfig(os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.ini")))
os.environ['CUDA_VISIBLE_DEVICES'] = ''
USE_DATABASE = True


class DiscoveryAgent:
    def __init__(self):
        self.agentmodel = tf.keras.models.load_model(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                  config['PaperModelSettings']['discovery_model_path']))
        # model link: https://tfhub.dev/tensorflow/bert_multi_cased_L-12_H-768_A-12/4
        self.bertlayer = hub.KerasLayer(os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                                  "bert_multi_cased_L-12_H-768_A-12_4")),
                                        trainable=False)
        self.tagtokenize = Tokenize()
        self.tagtokenize.LoadObj(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                              config['TagTokenize']['vocab_file']))
        self.env = PolicyDeepthEnvFixCoordinate.Env(pd.DataFrame({'Event Source Page URL': []}), negativeReward=-0.1)

    def GetLeaveFeature(self, leaveIndex, trainFeatures):
        leaveFeatures = [[], [], [], [], [], [], [], [], [], [], [], [], [], [], []]
        for index in leaveIndex:
            i = 0
            tmp = index
            while tmp >= len(trainFeatures[i]):
                tmp -= len(trainFeatures[i])
                i += 1
            leaveFeatures[i].append(trainFeatures[i][tmp])
        leaveFeatures = [l for l in leaveFeatures if l != []]
        return leaveFeatures

    def CleanAlreadyClick(self, features, hrefindex, alreadyClick):
        ats = []
        hrefs = []
        coor = []
        features = copy.deepcopy(features)
        popiIndex = []
        popjIndex = []
        newalreadyclick = []
        for click in alreadyClick:
            try:
                newalreadyclick.append(click[click.index(":"):])
            except:
                newalreadyclick.append(click)
        newalreadyClick = newalreadyclick
        # print('******************************new:{}'.format(alreadyClick))
        for i in reversed(range(len(features))):
            for j in reversed(range(len(features[i]))):
                try:
                    if features[i][j][hrefindex][features[i][j][hrefindex].index(':'):] in newalreadyClick:
                        popjIndex.append(j)
                        popiIndex.append(i)
                except:
                    if features[i][j][hrefindex] in alreadyClick:
                        popjIndex.append(j)
                        popiIndex.append(i)
        for i, j in zip(popiIndex, popjIndex):
            features[i].pop(j)
        return features

    def Step(self, url, threshold, dynamicstep):
        database_time = 0
        crawler_time = 0
        model_time = 0
        deepth = 3
        leaveTrainFeatures = []
        alreadyClickHrefs = []
        alreadyClickATs = []
        predictvalue = []
        domain = urlparse(url).netloc
        # print("domain page:", domain)
        # Database time
        start_time = time.time()
        if USE_DATABASE and find_page_domain(domain):
            print("find previous result")
            update_last_used_time(domain)
            print("update last used_time")
            if not update_page(domain):
                print("use previous result")
                return return_already_find(domain)
            else:
                print('need update data')
        database_time += time.time() - start_time
        print("New Task Create")
        # Crawler time
        try:
            start_time = time.time()
            print('Event source page discovery reset')
            AT, HREFS, coordinate, tagpaths = func_timeout(10000, self.env.reset, args=(url, None, True))
            print('finish click all anchor node')
            # alreadyClickHrefs.append(self.env.currentURL)
            coordinate = list(coordinate)
        except FunctionTimedOut:
            print("Function Timeout")
            crawler_time += time.time() - start_time
            return [], [database_time, crawler_time, model_time]
        # assert len(AT) == len(coordinate) == len(HREFS) == len(tagpaths)
        assert len(AT) == len(HREFS) == len(tagpaths)
        if len(AT) == 0:
            print("No Anchor Node In Given Page")
            crawler_time += time.time() - start_time
            return [], [database_time, crawler_time, model_time]
        crawler_time += time.time() - start_time
        # Model time
        try:
            start_time = time.time()
            atembedding, neighborcoordinate, tagid, tagindex = Tool.ProcessFeatures(AT, coordinate, tagpaths,
                                                                                    self.tagtokenize, self.bertlayer,
                                                                                    config)
            leaveTrainFeatures.append(list(zip(atembedding, tagid, tagindex, HREFS, AT)))
        except Exception as e:
            print(e)
            print('My Config', str(config.get('BertTokenize', 'vocab_file')))
            model_time += time.time() - start_time
            return [], [database_time, crawler_time, model_time]
        step = 0
        model_time += time.time() - start_time
        while True:
            start_time = time.time()
            print('event source discovery go to step2, continuous check event source page')
            if (not dynamicstep and step == deepth) or (dynamicstep and step == 10):
                model_time += time.time() - start_time
                break
            actionIndex, leaveATIndex, clickhref, predvalue, maxpro = Tool.GetActionIndex(self.agentmodel,
                                                                                          leaveTrainFeatures, 3,
                                                                                          [0, 1, 2], alreadyClickHrefs,
                                                                                          False)  # not same
            if maxpro < threshold and dynamicstep:
                firdimension, secdimension = Tool.ConvertToTwoDimensionIndex(actionIndex, leaveTrainFeatures)
                # print('clickAT:{},Pred:{}'.format(leaveTrainFeatures[firdimension][secdimension][4],predvalue))
                model_time += time.time() - start_time
                break  # not same
            step += 1
            predictvalue.append(predvalue)
            firdimension, secdimension = Tool.ConvertToTwoDimensionIndex(actionIndex, leaveTrainFeatures)
            alreadyClickATs.append(leaveTrainFeatures[firdimension][secdimension][4])
            # print('homepage:{},already:{},now:{},click AT:{}, toHREFS:{},predvalue:{}'.format(url,alreadyClickHrefs, alreadyClickHrefs[-1],leaveTrainFeatures[firdimension][secdimension][4],clickhref,predvalue))
            alreadyClickHrefs.append(clickhref)
            model_time += time.time() - start_time
            # Crawler time
            try:
                start_time = time.time()
                tmpAT, tmpHREFS, tmpcoordinate, tmptagpath = func_timeout(10000, self.env.step, args=(clickhref, True))
                tmpcoordinate = list(tmpcoordinate)
            except FunctionTimedOut:
                crawler_time += time.time() - start_time
                break
            crawler_time += time.time() - start_time
            if (len(tmpAT) == 0):
                break
            # Model time
            start_time = time.time()
            tmpatembedding, tmpneighborcoordinate, tmptagid, tmptagindex = Tool.ProcessFeatures(tmpAT, tmpcoordinate,
                                                                                                tmptagpath,
                                                                                                self.tagtokenize,
                                                                                                self.bertlayer, config)
            leaveFeatures = self.GetLeaveFeature(leaveATIndex, leaveTrainFeatures)
            atembedding, neighborcoordinate, tagid, tagindex, HREFS, AT = tmpatembedding, tmpneighborcoordinate, tmptagid, tmptagindex, tmpHREFS, tmpAT
            leaveTrainFeatures = leaveFeatures + [list(zip(atembedding, tagid, tagindex, HREFS, AT))]
            leaveTrainFeatures = self.CleanAlreadyClick(leaveTrainFeatures, 3, alreadyClickHrefs)
            model_time += time.time() - start_time
            # assert len(AT) == len(neighborcoordinate) == len(HREFS) == len(tmptagpath)
            assert len(AT) == len(HREFS) == len(tmptagpath)
        alreadyClickHrefs = list(filter(None, alreadyClickHrefs))
        # print("alreadyClickHrefs: ", alreadyClickHrefs)
        # print("predictvalue:", predictvalue)
        if USE_DATABASE:
            start_time = time.time()
            print("save result to DB")
            if len(alreadyClickHrefs) == 0:
                add_page({"page_domain": domain,
                          "click_url": "",
                          "created_time": datetime.now(),
                          "last_used_time": datetime.now(),
                          "click_url_prob": "0"
                          })
            else:
                for url, value in zip(alreadyClickHrefs, predictvalue):
                    if validators.url(url):
                        # print('url:{}, value:{}'.format(url, str(value)))
                        add_page({"page_domain": domain,
                                  "click_url": url,
                                  "created_time": datetime.now(),
                                  "last_used_time": datetime.now(),
                                  "click_url_prob": str(value)
                                  })
            database_time += time.time() - start_time
        start_time = time.time()
        crawler_time += time.time() - start_time
        return alreadyClickHrefs, [database_time, crawler_time, model_time]

    def GetAnchorTextValue(self, url, anchortexts):
        anchortexts = anchortexts.split(',')
        deepth = 1
        leaveTrainFeatures = []
        try:
            AT, HREFS, coordinate, tagpaths = func_timeout(10000, self.env.reset, args=(url, None, True))
            coordinate = list(coordinate)
            atembedding, neighborcoordinate, tagid, tagindex = Tool.ProcessFeatures(AT, coordinate, tagpaths,
                                                                                    self.tagtokenize, self.bertlayer,
                                                                                    config)
            leaveTrainFeatures.append(list(zip(atembedding, tagid, tagindex, HREFS, AT)))
            coordinate = list(coordinate)
        except FunctionTimedOut:
            return '0'
        actionvalues = self.GetActionValues(self.agentmodel, leaveTrainFeatures, 3, [0, 1, 2])  # [0]
        prob = []
        for i in range(len(anchortexts)):
            prob.append(-1)
        for index, text in enumerate(anchortexts):
            print(text in AT, text)
            if text in AT:
                prob[index] = float(actionvalues[AT.index(text)])
        return {'Click Prob': prob, "Click AT": anchortexts}

    def GetActionValues(self, model, allfeatures, hrefindex, trainfeatureindexs):
        predvalue = []
        ats = []
        for batch in copy.deepcopy(allfeatures):
            features = zip(*batch)  # features = list(zip(*batch))
            features = [np.array(f) for index, f in enumerate(features) if index in trainfeatureindexs]
            if len(features) == 0:
                continue
            atpredd, _ = self.agentmodel(features)
            predvalue += list(atpredd[:, 0])
        return predvalue

    def quit(self):
        self.env.quit_driver()
