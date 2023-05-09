# -*- coding: utf-8 -*-
"""Simulator_KFold.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Q2Wjl_bgpeRCHD0eYF2_p7IdMq9b3L9Q
"""

import numpy as np
import torch
import tensorflow as tf
from tensorflow.keras import layers
from tensorflow.keras import losses
import tensorflow_addons as tfa
import os
import pandas as pd
import json
import sklearn
from sklearn.preprocessing import OneHotEncoder
from urllib import request
from simpletransformers.classification import ClassificationModel, ClassificationArgs
from sklearn.model_selection import KFold, StratifiedKFold

# Import class Vectorizer
module_url = f"https://raw.githubusercontent.com/sagacemente/PAN_2023_crypto/main/crypto_vectorzer.py"
module_name = module_url.split('/')[-1]
print(f'Fetching {module_url}')
with request.urlopen(module_url) as f, open(module_name,'w') as outf:
  a = f.read()
  outf.write(a.decode('utf-8'))
from crypto_vectorzer import Vectorizer

class Simulator:
  ''' import Vectorizer must be inside the Simulator.py file'''

  def __init__(self, model, num_fold, nr_epochs, ds, vectorize_layer=[], num_labels=5):
    self.num_labels = num_labels
    self.model = model
    self.num_fold = num_fold
    self.nr_epochs = nr_epochs
    self.ds = ds  ## take only the ds
    self.vectorize_layer = vectorize_layer
    self.setup()    

  # Prior data and model setups before running.
  def setup(self):    
    # To store maximum accuracy for each run.
    self.runs_accuracy = []    
    # Dictionary size.
    #self.max_features=len(self.vectorize_layer.get_vocabulary()) + 1
    # Now specific setup parameters setup for each model
    if self.model=="cnn":
      self.setup_shallow()
      print("\nSetup for shallow model completed.")
    
    if self.model == 'roberta' or 'electra' or 'xlnet':
      self.setup_transformer()
      print("\nSetup for Roberta completed.")

  def setup_shallow(self):
    # Word embedding dimensions.
    self.embedding_dim = 100
    #For reproducibility.
    #tf.random.set_seed(1)

  def setup_transformer(self):
    #Convert train and test keras DS into DFs.
    #self.train_df, self.test_df = self.ds.get_train_test_df()
    #added some parameters
    self.kf = KFold(n_splits = 5, shuffle = True, random_state = 2)

  def run(self):
    if self.model == "cnn":
      self.run_cnn()
    elif self.model == 'roberta' or 'electra' or 'xlnet':
      self.run_roberta()

  def run_cnn(self):
    METRICS = [
      tf.keras.metrics.CategoricalAccuracy(name='acc'),
      tfa.metrics.F1Score(num_classes=self.num_labels,
                          average='micro',   # macro does NOT work https://stackoverflow.com/questions/74811734/tensorflow-macro-f1-score-for-multiclass-and-also-for-binary-classification
                          name='f1', 
                          dtype=tf.float32
                          )
               ]
    FOLD_ACCURACIES = []
    for fold_nr in range(0,self.num_fold):
      tf.random.set_seed(fold_nr)
      # TO DO LIKE THIS BELOW
      #vct_layer_obj = self.ds.L_VECTORIZER[fold_nr]
      
      vct_layer_obj = Vectorizer(self.ds.train[fold_nr])
      max_features=len(vct_layer_obj.vectorize_layer.get_vocabulary()) + 1
      print('max_features', max_features)      
      print("Fold nr.: ", fold_nr)
      seed = fold_nr
      print("Used seed: ", seed)
      train_text = self.ds.train[fold_nr].map(lambda x, y: x)
      vct_layer_obj.vectorize_layer.adapt(train_text)
      current_train_ds_batched= self.ds.train[fold_nr].batch(1)
              
      initializer=tf.keras.initializers.GlorotUniform(seed=seed)
      model = tf.keras.Sequential([
                                  tf.keras.Input(shape=(1,), dtype=tf.string),
                                  vct_layer_obj.vectorize_layer,  #CHANGE THIS
                                  #embedding_layer,
                                  layers.Embedding(len(vct_layer_obj.vectorize_layer.get_vocabulary()) + 1,self.embedding_dim,embeddings_initializer=initializer),                     
                                  #layers.Dropout(0.2),
                                  layers.Conv1D(64,36,kernel_initializer=initializer,bias_initializer='zeros',activation='relu'),
                                  layers.MaxPooling1D(4),                                  
                                  layers.GlobalAveragePooling1D(),
                                  #layers.GlobalMaxPooling1D(),
                                  layers.Dense(self.num_labels, activation='softmax', kernel_initializer=initializer,bias_initializer='zeros'),
                                  layers.Reshape((1,self.num_labels), input_shape=(self.num_labels))
                                  ])
        
      opt = tf.keras.optimizers.Adam()
      model.compile(loss='categorical_crossentropy', optimizer='RMSprop', metrics=METRICS) 
      #print(model.summary())
      history = model.fit(current_train_ds_batched,
                          validation_data=self.ds.val[fold_nr],#.batch(1),
                          epochs=self.nr_epochs,
                          shuffle=False,
                          verbose=1)       
      accuracy = history.history['val_acc']

  def run_roberta(self):
    #functions defined inside one function
    def f1(y_true, y_pred):
      TP = np.sum(np.multiply([i==True for i in y_pred], y_true))
      TN = np.sum(np.multiply([i==False for i in y_pred], [not(j) for j in y_true]))
      FP = np.sum(np.multiply([i==True for i in y_pred], [not(j) for j in y_true]))
      FN = np.sum(np.multiply([i==False for i in y_pred], y_true))
      precision = TP/(TP+FP)
      recall = TP/(TP+FN)
      if precision != 0 and recall != 0:
        f1 = (2 * precision * recall) / (precision + recall)
      else:
        f1 = 0
      return f1
    def f1_macro(y_true, y_pred):
      macro = []
      for i in np.unique(y_true):
        modified_true = [i==j for j in y_true]
        modified_pred = [i==j for j in y_pred]
        score = f1(modified_true, modified_pred)
        macro.append(score)
      return np.mean(macro)
    
    self.metric = f1_macro
    cuda_available = torch.cuda.is_available()

    model_args = ClassificationArgs(num_train_epochs=2, 
                                    overwrite_output_dir=True,
                                    manual_seed = 4,
                                    use_multiprocessing = True,
                                    train_batch_size = 16,
                                    eval_batch_size = 1,
                                    no_save=True, 
                                    no_cache=True)

    runs_accuracy = []
    
    kf = StratifiedKFold(n_splits = self.num_fold, shuffle = True, random_state = 2)
    #kf = KFold(n_splits = self.num_fold, shuffle = True, random_state = 2)
    self.df_all = pd.concat([self.ds.train_df,self.ds.test_df],axis=0)
    inputs = self.df_all['text'].values
    targets = self.df_all['labels'].values
    c = 0
    for train, test in kf.split(inputs, targets):    
      c+= 1
      print('FOLD NUM', c)
      X_train_fold_array, Y_train_fold_array = inputs[train], targets[train]
      X_test_fold_array, Y_test_fold_array = inputs[test], targets[test]
      #print(type(X_train_fold_array), X_train_fold_array.shape)
      self.df_train_fold = pd.DataFrame([X_train_fold_array, Y_train_fold_array]).T
      self.df_test_fold = pd.DataFrame(data=[X_test_fold_array, Y_test_fold_array]).T
      #print('df_test_fold',self.df_test_fold)
      
      tokenizer_dict =  {"electra":'google/electra-base-discriminator',
                   "roberta":'roberta-base',
                   "xlnet":'xlnet-base-cased'}
      tokenizer = tokenizer_dict[self.model]
      
      epochs_accuracy=[]
      model = ClassificationModel(self.model, 
                                      tokenizer, 
                                      args = model_args, 
                                      num_labels=self.num_labels, 
                                      use_cuda=cuda_available,
                                      )
      for epoch in range (0,self.nr_epochs):
        print("\nEPOCH NUMBER: ", epoch)
        # train model
        print("\nNOW TRAIN THE MODEL.")
        model.train_model(self.df_train_fold,
                          show_running_loss=True,
                          acc=self.metric,
                          verbose=False)
        print("\nNOW EVALUATE THE TEST DF.")
        # Evaluate the model
        result, model_outputs, wrong_predictions = model.eval_model(self.df_test_fold,
                                                                    acc=self.metric
                                                                    )
        # Results on test set.
        print(result)
        macrof1 = result['acc']
        print("Macro F1 on test set is:",macrof1,"\n\n")
        epochs_accuracy.append(macrof1)

      print('Accuracy Over epochs',epochs_accuracy)
      runs_accuracy.append(max(epochs_accuracy))   
  

    runs_accuracy.sort()
    print("\n\n Over all runs maximum accuracies are:", runs_accuracy)
    # print("The median is:",runs_accuracy[2])
    # if (runs_accuracy[2]-runs_accuracy[0])>(runs_accuracy[4]-runs_accuracy[2]):
    #   max_range_from_median = runs_accuracy[2]-runs_accuracy[0]
    # else:
    #   max_range_from_median = runs_accuracy[4]-runs_accuracy[2]
    # final_result = str(runs_accuracy[2])+" +/- "+ str(max_range_from_median)
    final_result = max(runs_accuracy)
    median = np.median(runs_accuracy)
    print("RoBERTa MAX Accuracy Score on Test set -> ",final_result)
    print("RoBERTa median Accuracy Score on Test set -> ",median)
