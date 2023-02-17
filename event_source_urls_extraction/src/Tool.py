import configparser
import pickle
import json
import copy
import numpy as np
import tensorflow as tf
import logging
try:
    from src import StringTool
except:
    import StringTool
import random


def LoadConfig(confilefile):
    config = configparser.ConfigParser()
    config.read(confilefile)
    return config


def SaveList(filename, listinfo):
    with open(f"{filename}.txt", "wb") as fp:
        pickle.dump(listinfo, fp)


def LoadList(filename):
    with open(f"{filename}.txt", "rb") as fp:
        return pickle.load(fp)


def SaveObj(filename, data):
    f = open(filename + '.txt', 'w')
    json.dump(data, f)


def LoadObj(filename):
    f = open(filename + '.txt', 'r')
    return json.load(f)


def ConvertToTwoDimensionIndex(index, convertedlist):
    i = 0
    while index >= len(list(convertedlist[i])):
        index -= len(list(convertedlist[i]))
        i += 1
    return i, index


def GetActionIndex(model, allfeatures, hrefindex, trainfeatureindexs, alreadyClicks, randomjump, epison=0):
    if randomjump:
        if int(epison) == int(0):
            assert IndexError("Epison is zero, but random jump")
    predvalue = []
    predvalue_list = []
    for batch in copy.deepcopy(allfeatures):
        features = zip(*batch)
        features = [np.array(f) for index, f in enumerate(features) if index in trainfeatureindexs]
        if len(features) == 0:
            continue
        atpredd, _ = model(features)
        predvalue += list(atpredd[:, 0])
    # save predvalue in log
    for tensor_num in list(predvalue):
        predvalue_list.append(tensor_num.numpy())
    originalactionIndexs = list(tf.argsort(predvalue, axis=-1, direction='DESCENDING').numpy())
    leaveATIndex = list(originalactionIndexs[1:11])
    if (len(originalactionIndexs) > 1):
        if (predvalue[originalactionIndexs[0]] == predvalue[originalactionIndexs[1]]):
            sameindex = []
            maxnumber = predvalue[originalactionIndexs[0]]
            for i in originalactionIndexs:
                if (maxnumber == predvalue[i]):
                    sameindex.append(i)
                else:
                    break
            originalactionIndex = originalactionIndexs[random.sample(sameindex, 1)[0]]
        else:
            originalactionIndex = originalactionIndexs[0]
    else:
        originalactionIndex = originalactionIndexs[0]

    actionIndex = originalactionIndex  # np.random.choice(np.arange(0, len(predvalue)), p=p)#originalactionIndex
    if (randomjump):
        if (random.randint(0, 10) / 10 <= epison):
            actionIndex = random.sample(list(range(0, len(predvalue))), 1)[0]
    firstdi, secdi = ConvertToTwoDimensionIndex(actionIndex, allfeatures)
    if (actionIndex in leaveATIndex):
        leaveATIndex.remove(actionIndex)
    for index in leaveATIndex:
        if (allfeatures[firstdi][secdi][hrefindex] in alreadyClicks):
            leaveATIndex.remove(index)
    for i in range(10 - len(leaveATIndex)):
        try:
            leaveATIndex.append(originalactionIndexs[10 + i])
        except:
            continue
    clickhref = allfeatures[firstdi][secdi][hrefindex]
    clickvalue = predvalue[actionIndex]
    # save url in log
    urls = []
    for index in originalactionIndexs:
        firstdi, secdi = ConvertToTwoDimensionIndex(index, allfeatures)
        # print('allfeatures[firstdi][secdi][hrefindex]',allfeatures[firstdi][secdi][hrefindex])
        urls.append(allfeatures[firstdi][secdi][hrefindex])
    candidate_click_anchors = []
    for url, probability in zip(urls, predvalue_list):
        click_anchor = {}
        click_anchor["key"] = url
        click_anchor["value"] =probability.astype(np.float64)
        candidate_click_anchors.append(click_anchor)
    # logging.info('current url:{},priority queue:{}'.format(clickhref, candidate_click_anchors))
    data = {
        'current url': clickhref,
        'priority queue': candidate_click_anchors
    }
    with open('ploicyLog/candidate_click_anchors.json', 'a', encoding='utf-8') as file:
        file.writelines('\n')
        json.dump(data, file, ensure_ascii=False)
    return actionIndex, leaveATIndex, clickhref, clickvalue.numpy(), predvalue[originalactionIndex].numpy()


def ProcessFeatures(at, coordinate, tagpath, tagtokenize, bertlayer, config):
    if len(coordinate) == 0:
        coo = []
        tagid = GetTokenTagPath(tagpath, tagtokenize)
        tagid = tf.repeat(np.array([tagid]), len(tagid), axis=0).numpy()
    else:
        coo = GetCoordinateNeighbor(coordinate)
        tagid = GetTokenTagPath(tagpath, tagtokenize)
        tagid = tf.repeat(np.array([tagid]), len(coo), axis=0).numpy()
    return StringTool.GetTextListEmbedding(at, bertlayer, config), list(coo), list(tagid), GetIndexMetrix(
        tagid.shape)


def GetTokenTagPath(path, tagtokenize):
    ids = [tagtokenize.GetIDs(tmp) for tmp in path]
    tagoutput = np.zeros((len(ids), tagtokenize.GetDictLength()))
    for i in range(len(ids)):
        tagoutput[i] = np.bincount(ids[i], minlength=tagtokenize.GetDictLength())
    return tagoutput


def GetIndexMetrix(tagshape):
    shape = (tagshape[0], tagshape[1], 36)
    index = np.zeros(shape)
    # print('shape:{}'.format(shape))
    for i in range(shape[0]):
        index[i][i] = 1
    return index


def GetCoordinateNeighbor(coordinate):
    neighborCoordinate = []
    for nowIndex in range(len(coordinate)):
        tmpInfor = []  # list(coordinate[nowIndex])
        tmpInfor.extend(list(coordinate[nowIndex]))
        assert len(tmpInfor) == 4
        previousIndex = nowIndex - 1
        nextIndex = nowIndex + 1
        if (previousIndex >= 0):
            for previous, now in zip(coordinate[previousIndex], coordinate[nowIndex]):
                tmpInfor.append(now - previous)
        else:
            for j in range(len(coordinate[nowIndex])):
                tmpInfor.append(0)
        assert len(tmpInfor) == 8
        if (nextIndex < len(coordinate)):
            for nextn, now in zip(coordinate[nextIndex], coordinate[nowIndex]):
                tmpInfor.append(now - nextn)
        else:
            for j in range(len(coordinate[nowIndex])):
                tmpInfor.append(0)
        assert len(tmpInfor) == 12
        neighborCoordinate.append(list(tmpInfor))
    return neighborCoordinate
