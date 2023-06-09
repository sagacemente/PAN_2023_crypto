# -*- coding: utf-8 -*-
"""predictions_pan_crypto.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10qfP4TYPNQN5ksnJtggxyp_XZinfc3rD
"""

import numpy as np
import torch
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import losses
import os
import pandas as pd
import json
from urllib import request
from simpletransformers.classification import ClassificationModel, ClassificationArgs

# save sipletransformer model https://stackoverflow.com/questions/62271872/how-do-you-load-a-simpletransformers-model-from-a-checkpoint
# multiple metrics in simpletransformer https://stackoverflow.com/questions/69996505/reporting-other-metrics-during-training-evaluation-simpletransformers

### LOAD MODEL
dict_labels = {'macro':0.0,
                'mega': 1.0,
                'micro':2.0,
                'nano':3.0,
               'no influencer': 4.0,
                }
path_to_model = os.getcwd() + '/outputs'
model  = ClassificationModel("electra", "path_to_model")


#LOAD FILE 
n_sub = 1
subtask = 'subtask' + str(n_sub) 
train_texts_path = os.getcwd() + '/' + subtask + '/train_text.json'  # '$inputDataset/train_text.json'

f = open(train_texts_path, "r")
id_texts_dict = {}
tweet_ids_dict = {}
l_tw_id = []  # From test.json file
for line in f:
    line = json.loads(line)            
    texts = line['texts']
    texts = [i['text'] for i in texts]
    texts = ' '.join(texts)
    user_id = line['twitter user id']
    l_tw_id.append(user_id)

    id_texts_dict[user_id] = texts
    ids =  line['tweet ids']  #list of dict
    ids =  [i['tweet id'] for i in ids ]
    tweet_ids_dict[user_id] = ids
#print('id_texts_dict', id_texts_dict)
#print('tweet_ids_dict', tweet_ids_dict)
#Create DataFrame object with samples
df_texts = pd.DataFrame.from_dict(id_texts_dict, orient='index', columns=['text'])


to_be_predicted = df_texts 
predictions, raw_outputs = model.predict(to_be_predicted)

l_probs = [max(raw_outputs[i]) for i in range(raw_outputs.shape[0])]
l_class = []
for idx, i in enumerate(predictions): 
  #print(i)
  #print(list(dict_labels.keys())[list(dict_labels.values()).index(predictions[idx])])
  class_name = list(dict_labels.keys())[list(dict_labels.values()).index(predictions[idx])]
  l_class.append(class_name)
#print(l_probs)
#print(l_class)

L_LINES = []
for idx, prb in enumerate(l_probs):
  pred_class = l_class[idx] 
  tw_id = l_tw_id[idx]
  line = {"twitter user id": tw_id,"class":pred_class , "probability": prb}
  L_LINES.append(line)

# write output file
with open(os.getcwd() +'/' + subtask + '.json', 'w') as fp:
  fp.write('\n'.join(json.dumps(i) for i in L_LINES) +
            '\n')