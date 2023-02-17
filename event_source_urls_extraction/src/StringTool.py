from tensorflow.keras.preprocessing.sequence import pad_sequences
import numpy as np
import os

try:
    from bert.tokenization.bert_tokenization import FullTokenizer
except:
    from bert.tokenization import FullTokenizer


def CleanString(string):
    cleantext = string.replace('\n', '')
    cleantext = cleantext.replace('\t', '')
    cleantext = cleantext.replace('\r', '')
    cleantext = cleantext.replace(' ', '')
    return cleantext


def ConvertListToID(data, config):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                        config['BertTokenize']['vocab_file'])
    tokenizer = FullTokenizer(vocab_file=path, do_lower_case=True)
    sep_id = int(np.array([tokenizer.convert_tokens_to_ids(["[SEP]"])])[0])
    cls_id = int(np.array([tokenizer.convert_tokens_to_ids(["[CLS]"])])[0])
    output = []
    for d in data:
        hi = tokenizer.tokenize(d)
        tmp = [cls_id] + list(tokenizer.convert_tokens_to_ids(hi)) + [sep_id]
        output.append(tmp)
    return output


def GetAnchorTextToken(data, config):
    return ConvertListToID(data, config)


def GetTextListEmbedding(anchorTexts, bertlayer, config):
    text = GetAnchorTextToken(anchorTexts, config)
    text = pad_sequences(text, maxlen=10, dtype=np.int32, padding='post', truncating='post')
    feature_embedding = bertlayer({"input_word_ids": text, "input_mask": np.ones(shape=text.shape, dtype=np.int32),
                                   "input_type_ids": np.zeros(shape=text.shape, dtype=np.int32)})[
        "pooled_output"].numpy()  # textMap[str(anchorTexts)]
    return feature_embedding
