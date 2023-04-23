# -*- coding: utf-8 -*-
"""Crypto_Dataset.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Q1SFf-Ye-KNkSatJXEam6oeQHr9A911O
"""

import os
import json
import pandas as pd
import tensorflow as tf
import sklearn
from sklearn.preprocessing import OneHotEncoder


class Dataset:

    def __init__(self, url:str, n_subtask:int):
        self.url = url
        self.subtask = 'subtask' + str(n_subtask)
        
    def fetch_ds_files(self):
        train_set_archive = tf.keras.utils.get_file('pan23-profiling-cryptocurrency-influencers.zip',self.url,
                                            extract=True, archive_format='zip',cache_dir='.',
                                            cache_subdir='')

    def organize_ds_folders(self):
        #############   LABELS TRUTH  
        train_truth_file_path = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers/' + self.subtask + '/train_truth.json'
        f = open(train_truth_file_path, "r")
        self.id_label_dict = {}
        for line in f:
            line = json.loads(line)
            label = line['class']
            user_id = line['twitter user id']
            self.id_label_dict[user_id] = label
        print('id_label_dict',self.id_label_dict)

        #############  TEXTS 
        train_texts_path = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers/'  + self.subtask  + '/train_text.json'
        f = open(train_texts_path, "r")
        self.id_texts_dict = {}
        self.tweet_ids_dict = {}
        for line in f:
            line = json.loads(line)            
            texts = line['texts']
            texts = [i['text'] for i in texts]
            texts = '<NEWTW>'.join(texts)
            user_id = line['twitter user id']
            self.id_texts_dict[user_id] = texts
            #create object with {user_id : [tweet_ids_list1, tweet_ids_list2]}
            ids =  line['tweet ids']  #list of dict
            ids =  [i['tweet id'] for i in ids ]
            self.tweet_ids_dict[user_id] = ids
        #print('id_texts_dict', self.id_texts_dict)
        #print('tweet_ids_dict', self.tweet_ids_dict)
        #Create DataFrame object with samples
        self.df_texts = pd.DataFrame.from_dict(self.id_texts_dict, orient='index', columns=['text'])
        self.df_labels = pd.DataFrame.from_dict(self.id_label_dict, orient='index', columns=['label'])
        #one-hot-encode
        X = self.df_labels['label'].values.reshape(-1, 1)
        enc = OneHotEncoder().fit(X)
        X = enc.transform(X).toarray() #.reshape(-1,5)
        self.df_labels['label'] = X 
        #Label as number [1,2,3,4....]        
        #self.df_labels['label'] = pd.Categorical(self.df_labels['label']).codes
        #Dataframe texts and label
        self.df = pd.concat([self.df_texts, self.df_labels], axis=1)
    
    def generate_keras_ds(self, batch_size, left_size=0.8):
        X = self.df_texts
        self.nlabels = int(len(set(self.id_label_dict.values())))
        Y = self.df_labels.values.reshape(-1,1,self.nlabels)
        self.ds = tf.data.Dataset.from_tensor_slices((X, Y))
        self.train_set, self.test_set = tf.keras.utils.split_dataset(self.ds, left_size=left_size)
        print('num labels',  self.nlabels)
        # for row in self.train_set.take(3):
        #   print(row)
        # for row in self.test_set.take(3):
        #   print(row)
        # SHUFLLE
        #self.train_set = self.train_set.shuffle(len(self.train_set),seed=1, reshuffle_each_iteration=False)
        #self.test_set =  self.test_set.shuffle(len(self.test_set),seed=1, reshuffle_each_iteration=False)
    
    # def clean_df(self, clean):
    #   return []

    def get_train_test_df(self, train_size=0.8):
      self.df_texts = pd.DataFrame.from_dict(self.id_texts_dict, orient='index', columns=['text'])
      self.df_labels = pd.DataFrame.from_dict(self.id_label_dict, orient='index', columns=['label'])      
      self.df_labels['label'] = pd.Categorical(self.df_labels['label']).codes
      self.df = pd.concat([self.df_texts, self.df_labels], axis=1)  
      #self.df = self.df.sample(frac=1) #shuffle Dataset 
      last_idx_train = int(len(self.df)*train_size)
      self.train_df = self.df[:last_idx_train]
      self.train_df.columns = ["text", "labels"]
      self.test_df = self.df[last_idx_train:]
      self.test_df.columns = ["text", "labels"]
      return self.train_df , self.test_df

    def build_ds(self,batch_size, left_size=0.8):
      self.fetch_ds_files()
      self.organize_ds_folders()
      self.generate_keras_ds(batch_size, left_size)