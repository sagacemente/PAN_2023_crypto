# PAN_2023_crypto
PAN@CLEF 2023 Submission
Notbooks for the submissions
Move vectorizer inside Simulator --> vectorize each training set in each K-fold
Add Generate_cross_fold_fucntion --> quando passo self.train  self.test --> self.train[i]--> i= i-esima-fold

--> CHECK CHE MACRO F1 DI ROBERTA CORRISPONDA A VERITA'

### TEST --> 
0) roberta original , roberta japanese , roberta IT, DE.. > check quale va meglio. 
a) 5 fold (80-20)
b) 10 fold (90-10)

# BASELINE 
Run baseline su ogni test_fold e comparare con nostro risultato (check se stiamo sopra) 

# Nostro contribuuto 
a) Creare Augmentation.py
b) Espansione --> lingua (tedesco,italiano, japanese e mix-it-de)
