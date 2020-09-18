import pickle

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Embedding
from tensorflow.keras.preprocessing import sequence
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras import backend as K
from collections import OrderedDict
import numpy as np
import os
import json
import pandas
import optparse

def train(csv_file, out_folder):
    print("Preparing training dataset...")
    dataframe = pandas.read_csv(csv_file, engine='python', quotechar='|', header=None)
    dataset = dataframe.sample(frac=1).values
    
    # Preprocess dataset
    X = dataset[:,0]
    Y = dataset[:,1]

    for index, item in enumerate(X):
        # Quick hack to space out json elements
        reqJson = json.loads(item, object_pairs_hook=OrderedDict)
        X[index] = json.dumps(reqJson, separators=(',', ':'))

    tokenizer = Tokenizer(filters='\t\n', char_level=True)
    tokenizer.fit_on_texts(X)

    # Extract and save word dictionary
    word_dict_file = ('%s/build/word-dictionary.json' % out_folder)

    if not os.path.exists(os.path.dirname(word_dict_file)):
        os.makedirs(os.path.dirname(word_dict_file))

    with open(word_dict_file, 'w') as outfile:
        json.dump(tokenizer.word_index, outfile, ensure_ascii=False)

    # Save tokenizer
    tokenizer_file = '%s/build/tokenizer.pkl' % out_folder
    if not os.path.exists(os.path.dirname(tokenizer_file)):
        os.makedirs(os.path.dirname(tokenizer_file))

    with open(tokenizer_file, 'wb') as handle:
        pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)

    num_words = len(tokenizer.word_index)+1
    X = tokenizer.texts_to_sequences(X)

    max_payload_length = 1024
    train_size = int(len(dataset) * .75)

    X_processed = sequence.pad_sequences(X, maxlen=max_payload_length)
    X_train, X_test = np.array(X_processed[0:train_size], dtype=np.float), np.array(X_processed[train_size:len(X_processed)], dtype=np.float)
    Y_train, Y_test = np.array(Y[0:train_size], dtype=np.float), np.array(Y[train_size:len(Y)], dtype=np.float)

    print("Training dataset ready.")
    model = Sequential()
    model.add(Embedding(num_words, 32, input_length=max_payload_length))
    model.add(Dropout(0.5))
    if has_gpu is not None:
      model.add(CuDNNLSTM(64))
    else:
      model.add(LSTM(64, recurrent_dropout=0.5))
    model.add(Dropout(0.5))
    model.add(Dense(1, activation='sigmoid'))
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
    print(model.summary())
    model.fit(X_train, Y_train, validation_split=0.25, epochs=1, batch_size=128)
    score, acc = model.evaluate(X_test, Y_test, verbose=1, batch_size=128)

    print("Model Accuracy: {:0.2f}%".format(acc * 100))
    
    # Save model
    model.save_weights('%s/privapi-lstm-weights.h5' % out_folder)
    model.save('%s/privapi-lstm-model.h5' % out_folder)
    with open('%s/privapi-lstm-model.json' % out_folder, 'w') as outfile:
        outfile.write(model.to_json())


if __name__ == '__main__':
    basedir = os.path.join(os.path.dirname(__file__), os.pardir)
    parser = optparse.OptionParser()
    parser.add_option('-t', '--training', action="store", dest="file", help="input CSV file")
    parser.add_option('-o', '--output', action="store", dest="out", help="output folder")

    options, args = parser.parse_args()

    if options.file is not None:
        csv_file = options.file
    else:
        basedir = os.path.join(os.path.dirname(__file__), os.pardir)
        csv_file = '%s/data/training.csv' % basedir

    if options.out is not None:
        out_folder = options.out
    else:
        basedir = os.path.join(os.path.dirname(__file__), os.pardir)
        out_folder = '%s/out' % basedir
    
    has_gpu = None
 #   if len(K._get_available_gpus()) > 0:
 #       from keras.layers import CuDNNLSTM
 #       has_gpu = True

    train(csv_file, out_folder)
