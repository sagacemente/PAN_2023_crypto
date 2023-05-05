# -*- coding: utf-8 -*-
"""Crypto_Dataset.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Q1SFf-Ye-KNkSatJXEam6oeQHr9A911O
"""

import os
import shutil
import json
import pandas as pd
import tensorflow as tf
import sklearn
from sklearn.preprocessing import OneHotEncoder
from deep_translator import GoogleTranslator


class Dataset:

    def __init__(self, url:str, n_subtask:int, language='it'):
        self.url = url
        self.language = language
        self.subtask = 'subtask' + str(n_subtask)
        
    def fetch_ds_files(self):
        if 'augmented' in self.url:
            self.NAME = 'pan23-profiling-cryptocurrency-influencers-augmented-' + self.language
            self.NAME_ZIP = 'pan23-profiling-cryptocurrency-influencers-augmented-' + self.language + '.zip'
            train_set_archive = tf.keras.utils.get_file(self.NAME_ZIP,self.url,
                                            extract=True, archive_format='zip',cache_dir='.',
                                            cache_subdir='')      
        else:
            self.NAME = 'pan23-profiling-cryptocurrency-influencers'
            train_set_archive = tf.keras.utils.get_file('pan23-profiling-cryptocurrency-influencers.zip',self.url,
                                            extract=True, archive_format='zip',cache_dir='.',
                                            cache_subdir='')

    def organize_ds_folders(self):
        #############   LABELS TRUTH  
        train_truth_file_path = os.getcwd() + '/' + self.NAME + '/' + self.subtask + '/train_truth.json'
        #train_truth_file_path = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers/' + self.subtask + '/train_truth.json'
        f = open(train_truth_file_path, "r")
        self.id_label_dict = {}
        for line in f:
            line = json.loads(line)
            label = line['class']
            user_id = line['twitter user id']
            self.id_label_dict[user_id] = label
        print('id_label_dict',self.id_label_dict)

        #############  TEXTS 
        train_texts_path = os.getcwd() + '/' + self.NAME  + '/' + self.subtask + '/train_text.json'
        #train_texts_path = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers/'  + self.subtask  + '/train_text.json'
        f = open(train_texts_path, "r")
        self.id_texts_dict = {}
        self.tweet_ids_dict = {}
        for line in f:
            line = json.loads(line)            
            texts = line['texts']
            texts = [i['text'] for i in texts]
            texts = ' '.join(texts)
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
    
    def generate_cross_val_sets(self, fold_nr):
      self.train=[]
      self.val=[]
      
      # Percentage start and end of validation subset within full_train_ds.
      val_percentage_end=100
      val_percentage_size=int(100/ fold_nr)  #20
      val_percentage_start= val_percentage_end - val_percentage_size #80
      full_train_ds_size = len(self.ds)
      
      for i in range(0,fold_nr):
        self.train.append(self.ds.take(int(full_train_ds_size*val_percentage_start/100)))
        self.train[i] = self.train[i].concatenate(self.ds.skip(int(full_train_ds_size*val_percentage_end/100)))
        
        self.val.append(self.ds.skip(int(full_train_ds_size*val_percentage_start/100)))
        self.val[i] = self.val[i].take(int(full_train_ds_size*val_percentage_size/100))
        
        val_percentage_start-=val_percentage_size
        val_percentage_end-=val_percentage_size
        
    def clean_samples(self, input_data):
      #tag_url = tf.strings.regex_replace(input_data,'http\S+', 'url')
      #output_data = tf.strings.regex_replace(tag_url,'</documents>', '')
      output_data = input_data
      return output_data #.numpy().decode("utf-8")

    def chunkstring(self, string, length):
      res = list((string[0+i:length+i] for i in range(0, len(string), length)))
      return res

    def enhance_one_sample(self, sample, TARGET='it', return_both=True):  
      preprocessed_text = self.clean_samples(sample)

      #chunk to avoid character limits  
      TOBETRANS = self.chunkstring(preprocessed_text, 4999)
      translated_it = GoogleTranslator(source='en', target=TARGET).translate_batch(TOBETRANS)
      reversed_trans = GoogleTranslator(source=TARGET, target='en').translate_batch(translated_it)
      merged_chunks =' '.join(reversed_trans)
      enhanced_sample = preprocessed_text+merged_chunks
      if return_both == False:
        enhanced_sample = merged_chunks
      return enhanced_sample
    
    def augment_dataset(self, SUBTASKS=['1','2'], TARGET_LANG=['it', 'de']):
      for lang in TARGET_LANG:
        print(lang)
        language = '-augmented-' + lang 
        for subtask in SUBTASKS:      
          subtask = 'subtask' + subtask
          print(subtask)
          #create required folders
          train_truth_path = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers/' + subtask + '/train_truth.json'
          train_texts_path_augmented = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers'+ language + '/'  + subtask 
          train_truth_path_augmented = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers' + language + '/' + subtask + '/train_truth.json'
          if not os.path.exists(train_texts_path_augmented):
            os.makedirs(train_texts_path_augmented)
          if os.path.exists(train_texts_path_augmented):
            shutil.copyfile(train_truth_path, train_truth_path_augmented)
          train_texts_path = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers/'  + subtask  + '/train_text.json'
          f = open(train_texts_path, "r")
          LIST_SAMPLES = []
          c = 0
          for idx, line in enumerate(f):
              print('idx', idx+1)
              line = json.loads(line)            
              texts = line['texts']
              texts = [i['text'] for i in texts]    
              ##### AUGMENTATION #####
              augmented_texts = []
              for tw in texts:
                if len(tw) > 3:
                  augmented = self.enhance_one_sample(tw, TARGET=lang)
                  #print('--> tw\n', tw)
                  #print('--> augmented\n', augmented)
                  #print('######')
                  #c +=1
                else:
                  print('!!!!this ont be augmented !!!! \n', tw)
                  augmented = tw
                augmented_texts.append(augmented)
              d_augmented_texts = [{'text': i} for i in augmented_texts]
              line['texts'] = d_augmented_texts
              LIST_SAMPLES.append(line)
              c +=1
          # write train file augmtented
          PATH_AUGM_TEST_FILE = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers' + language  +'/' + subtask + '/train_text.json' 
          NEW_FILE_NAME = os.getcwd() + '/pan23-profiling-cryptocurrency-influencers' + language
          with open(PATH_AUGM_TEST_FILE, 'w') as fp:
              fp.write('\n'.join(json.dumps(i) for i in LIST_SAMPLES) +
                      '\n')
          #create zip file    
          name_zip = os.getcwd() + '/' + 'pan23-profiling-cryptocurrency-influencers' + language
          print('name_zip \n', name_zip)
          shutil.make_archive(name_zip,'zip','','pan23-profiling-cryptocurrency-influencers' + language)
          print('#### Dataset Created for ', lang, subtask)
        
        
    def build_ds(self,batch_size, left_size=0.8):
      self.fetch_ds_files()
      self.organize_ds_folders()
      self.generate_keras_ds(batch_size, left_size)
