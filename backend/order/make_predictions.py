import tensorflow as tf
from matplotlib import pyplot as plt
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.callbacks import ModelCheckpoint, TensorBoard
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from yahoo_fin import stock_info as si
from collections import deque

import os
import numpy as np
import pandas as pd
import random
import time
from product.models import Product

from django.core.mail import send_mail


# set seed, so we can get the same results after rerunning several times
np.random.seed(314)
tf.random.set_seed(314)
random.seed(314)


def shuffle_in_unison(a, b):
    # shuffle two arrays in the same way
    state = np.random.get_state()
    np.random.shuffle(a)
    np.random.set_state(state)
    np.random.shuffle(b)


def load_data(ticker, n_steps=50, scale=True, shuffle=True, lookup_step=1, split_by_date=True,
              test_size=0.2, feature_columns=['adjclose', 'volume', 'open', 'high', 'low']):
    """
    Loads data from Yahoo Finance source, as well as scaling, shuffling, normalizing and splitting.
    Params:
        ticker (str/pd.DataFrame): the ticker you want to load, examples include AAPL, TESL, etc.
        n_steps (int): the historical sequence length (i.e window size) used to predict, default is 50
        scale (bool): whether to scale prices from 0 to 1, default is True
        shuffle (bool): whether to shuffle the dataset (both training & testing), default is True
        lookup_step (int): the future lookup step to predict, default is 1 (e.g next day)
        split_by_date (bool): whether we split the dataset into training/testing by date, setting it
            to False will split datasets in a random way
        test_size (float): ratio for test data, default is 0.2 (20% testing data)
        feature_columns (list): the list of features to use to feed into the model, default is everything grabbed from yahoo_fin
    """
    # see if ticker is already a loaded stock from yahoo finance
    if isinstance(ticker, str):
        # load it from yahoo_fin library
        df = si.get_data(ticker)
    elif isinstance(ticker, pd.DataFrame):
        # already loaded, use it directly
        df = ticker
    else:
        raise TypeError("ticker can be either a str or a `pd.DataFrame` instances")
    # this will contain all the elements we want to return from this function
    result = {}
    # we will also return the original dataframe itself
    result['df'] = df.copy()
    # make sure that the passed feature_columns exist in the dataframe
    for col in feature_columns:
        assert col in df.columns, f"'{col}' does not exist in the dataframe."
    # add date as a column
    if "date" not in df.columns:
        df["date"] = df.index
    if scale:
        column_scaler = {}
        # scale the data (prices) from 0 to 1
        for column in feature_columns:
            scaler = preprocessing.MinMaxScaler()
            df[column] = scaler.fit_transform(np.expand_dims(df[column].values, axis=1))
            column_scaler[column] = scaler
        # add the MinMaxScaler instances to the result returned
        result["column_scaler"] = column_scaler
    # add the target column (label) by shifting by `lookup_step`
    df['future'] = df['adjclose'].shift(-lookup_step)
    # last `lookup_step` columns contains NaN in future column
    # get them before droping NaNs
    last_sequence = np.array(df[feature_columns].tail(lookup_step))
    # drop NaNs
    df.dropna(inplace=True)
    sequence_data = []
    sequences = deque(maxlen=n_steps)
    for entry, target in zip(df[feature_columns + ["date"]].values, df['future'].values):
        sequences.append(entry)
        if len(sequences) == n_steps:
            sequence_data.append([np.array(sequences), target])
    # get the last sequence by appending the last `n_step` sequence with `lookup_step` sequence
    # for instance, if n_steps=50 and lookup_step=10, last_sequence should be of 60 (that is 50+10) length
    # this last_sequence will be used to predict future stock prices that are not available in the dataset
    last_sequence = list([s[:len(feature_columns)] for s in sequences]) + list(last_sequence)
    last_sequence = np.array(last_sequence).astype(np.float32)
    # add to result
    result['last_sequence'] = last_sequence
    # construct the X's and y's
    X, y = [], []
    for seq, target in sequence_data:
        X.append(seq)
        y.append(target)
    # convert to numpy arrays
    X = np.array(X)
    y = np.array(y)
    if split_by_date:
        # split the dataset into training & testing sets by date (not randomly splitting)
        train_samples = int((1 - test_size) * len(X))
        result["X_train"] = X[:train_samples]
        result["y_train"] = y[:train_samples]
        result["X_test"] = X[train_samples:]
        result["y_test"] = y[train_samples:]
        if shuffle:
            # shuffle the datasets for training (if shuffle parameter is set)
            shuffle_in_unison(result["X_train"], result["y_train"])
            shuffle_in_unison(result["X_test"], result["y_test"])
    else:
        # split the dataset randomly
        result["X_train"], result["X_test"], result["y_train"], result["y_test"] = train_test_split(X, y,
                                                                                                    test_size=test_size,
                                                                                                    shuffle=shuffle)
    # get the list of test set dates
    dates = result["X_test"][:, -1, -1]
    # retrieve test features from the original dataframe
    result["test_df"] = result["df"].loc[dates]
    # remove duplicated dates in the testing dataframe
    result["test_df"] = result["test_df"][~result["test_df"].index.duplicated(keep='first')]
    # remove dates from the training/testing sets & convert to float32
    result["X_train"] = result["X_train"][:, :, :len(feature_columns)].astype(np.float32)
    result["X_test"] = result["X_test"][:, :, :len(feature_columns)].astype(np.float32)
    return result


def create_model(sequence_length, n_features, units=256, cell=LSTM, n_layers=2, dropout=0.3,
                 loss="mean_absolute_error", optimizer="rmsprop", bidirectional=False):
    model = Sequential()
    for i in range(n_layers):
        if i == 0:
            # first layer
            if bidirectional:
                model.add(Bidirectional(cell(units, return_sequences=True),
                                        batch_input_shape=(None, sequence_length, n_features)))
            else:
                model.add(cell(units, return_sequences=True, batch_input_shape=(None, sequence_length, n_features)))
        elif i == n_layers - 1:
            # last layer
            if bidirectional:
                model.add(Bidirectional(cell(units, return_sequences=False)))
            else:
                model.add(cell(units, return_sequences=False))
        else:
            # hidden layers
            if bidirectional:
                model.add(Bidirectional(cell(units, return_sequences=True)))
            else:
                model.add(cell(units, return_sequences=True))
        # add dropout after each layer
        model.add(Dropout(dropout))
    model.add(Dense(1, activation="linear"))
    model.compile(loss=loss, metrics=["mean_absolute_error"], optimizer=optimizer)
    return model


def plot_graph(test_df):
    """
    This function plots true close price along with predicted close price
    with blue and red colors respectively
    """
    plt.plot(test_df[f'true_adjclose_{LOOKUP_STEP}'], c='b')
    plt.plot(test_df[f'adjclose_{LOOKUP_STEP}'], c='r')
    plt.xlabel("Days")
    plt.ylabel("Price")
    plt.legend(["Actual Price", "Predicted Price"])
    plt.show()


def get_final_df(model, data):
    """
    This function takes the `model` and `data` dict to
    construct a final dataframe that includes the features along
    with true and predicted prices of the testing dataset
    """
    # if predicted future price is higher than the current,
    # then calculate the true future price minus the current price, to get the buy profit
    buy_profit = lambda current, pred_future, true_future: true_future - current if pred_future > current else 0
    # if the predicted future price is lower than the current price,
    # then subtract the true future price from the current price
    sell_profit = lambda current, pred_future, true_future: current - true_future if pred_future < current else 0
    X_test = data["X_test"]
    y_test = data["y_test"]
    # perform prediction and get prices
    y_pred = model.predict_future_price(X_test)
    if SCALE:
        y_test = np.squeeze(data["column_scaler"]["adjclose"].inverse_transform(np.expand_dims(y_test, axis=0)))
        y_pred = np.squeeze(data["column_scaler"]["adjclose"].inverse_transform(y_pred))
    test_df = data["test_df"]
    # add predicted future prices to the dataframe
    test_df[f"adjclose_{LOOKUP_STEP}"] = y_pred
    # add true future prices to the dataframe
    test_df[f"true_adjclose_{LOOKUP_STEP}"] = y_test
    # sort the dataframe by date
    test_df.sort_index(inplace=True)
    final_df = test_df
    # add the buy profit column
    final_df["buy_profit"] = list(map(buy_profit,
                                      final_df["adjclose"],
                                      final_df[f"adjclose_{LOOKUP_STEP}"],
                                      final_df[f"true_adjclose_{LOOKUP_STEP}"])
                                  # since we don't have profit for last sequence, add 0's
                                  )
    # add the sell profit column
    final_df["sell_profit"] = list(map(sell_profit,
                                       final_df["adjclose"],
                                       final_df[f"adjclose_{LOOKUP_STEP}"],
                                       final_df[f"true_adjclose_{LOOKUP_STEP}"])
                                   # since we don't have profit for last sequence, add 0's
                                   )
    return final_df


def predict_future_price(model, data, n_steps, scale):
    # retrieve the last sequence from data
    last_sequence = data["last_sequence"][-n_steps:]
    # expand dimension
    last_sequence = np.expand_dims(last_sequence, axis=0)
    # get the prediction (scaled from 0 to 1)
    prediction = model.predict(last_sequence)
    # get the price (by inverting the scaling)
    if scale:
        predicted_price = data["column_scaler"]["adjclose"].inverse_transform(prediction)[0][0]
    else:
        predicted_price = prediction[0][0]
    return predicted_price


def get_future_price(ticker, n_steps=50, scale=True, shuffle=True, lookup_step=1, split_by_date=True,
                     test_size=0.2, feature_columns=['adjclose', 'volume', 'open', 'high', 'low'],
                     sequence_length=50, n_features=5, units=256, cell=LSTM, n_layers=2, dropout=0.3,
                     loss="mean_absolute_error", optimizer="rmsprop", bidirectional=False, epochs=3,
                     batch_size=64
                     ):
    # create these folders if they does not exist
    if not os.path.isdir("results"):
        os.mkdir("results")
    if not os.path.isdir("logs"):
        os.mkdir("logs")
    if not os.path.isdir("data"):
        os.mkdir("data")

    date_now = time.strftime("%Y-%m-%d")
    scale_str = f"sc-{int(scale)}"
    shuffle_str = f"sh-{int(shuffle)}"
    split_by_date_str = f"sbd-{int(split_by_date)}"
    ticker_data_filename = os.path.join("data", f"{ticker}_{date_now}.csv")

    # load the data
    data = load_data(ticker, n_steps, scale=scale, split_by_date=split_by_date,
                     shuffle=shuffle, lookup_step=lookup_step, test_size=test_size,
                     feature_columns=feature_columns)

    # construct the model
    model = create_model(sequence_length, n_features, loss=loss, units=units, cell=cell, n_layers=n_layers,
                         dropout=dropout, optimizer=optimizer, bidirectional=bidirectional)

    # model name to save, making it as unique as possible based on parameters
    model_name = f"{date_now}_{ticker}_{shuffle_str}-{scale_str}-{split_by_date_str}-{loss}-{optimizer}-{cell.__name__}-seq-{n_steps}-step-{lookup_step}-layers-{n_layers}-units-{units}"
    if bidirectional:
        model_name += "-b"

    model_path = os.path.join("results", model_name) + ".h5"

    if os.path.exists(model_path):
        # load optimal model weights from results folder
        model.load_weights(model_path)
    else:
        # save the dataframe
        data["df"].to_csv(ticker_data_filename)

        # some tensorflow callbacks
        checkpointer = ModelCheckpoint(os.path.join("results", model_name + ".h5"), save_weights_only=True,
                                       save_best_only=True,
                                       verbose=1)
        tensorboard = TensorBoard(log_dir=os.path.join("logs", model_name))
        # train the model and save the weights whenever we see
        # a new optimal model using ModelCheckpoint
        history = model.fit(data["X_train"], data["y_train"],
                            batch_size=batch_size,
                            epochs=epochs,
                            validation_data=(data["X_test"], data["y_test"]),
                            callbacks=[checkpointer, tensorboard],
                            verbose=1)

    # evaluate the model
    loss, mae = model.evaluate(data["X_test"], data["y_test"], verbose=0)
    # calculate the mean absolute error (inverse scaling)
    if scale:
        mean_absolute_error = data["column_scaler"]["adjclose"].inverse_transform([[mae]])[0][0]
    else:
        mean_absolute_error = mae

    # predict the future price

    predicted_price = predict_future_price(model, data, n_steps, scale)

    return predicted_price


def process_order(order_items, source_mail, destination_mail, user_name, user_surname, order_date, order_time):
    message = ""
    for item in order_items:
        product_id = item.product_Id.product_Id
        product = Product.objects.filter(product_Id=product_id)
        quantity = item.quantity
        message = ""
        predicted_price = 0
        if product[0].product_category.category_id == "it_companies":
            if product[0].product_Name == "Oracle":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "IBM":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "Epam":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "Apple":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "Microsoft":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            else:
                print("No such product in it_companies category.")
        elif product[0].product_category.category_id == "food_manufacturing":
            if product[0].product_Name == "Nestl??":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "Danone":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "Kraft Heinz":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            else:
                print("No such product in food_manufacturing category.")
        elif product[0].product_category.category_id == "automobile_manufacturing":
            if product[0].product_Name == "Tesla":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "Toyota Motor":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "General Motors":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "Volkswagen":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            else:
                print("No such product in automobile_manufacturing category.")
        elif product[0].product_category.category_id == "global_healthcare":
            if product[0].product_Name == "Johnson & Johnson":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "UnitedHealth Group":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            elif product[0].product_Name == "Roche Holding":
                predicted_price = get_future_price(ticker=product[0].product_Ticker, lookup_step=quantity)
            else:
                print("No such product in global_healthcare category.")
        else:
            print("No such category in categories list.")
        if predicted_price:
            message += f"??????????????: {product[0].product_Name}." \
                       f"\n?????????????????? ????????????????: {product[0].product_category.category_id}.\n" \
                       f"\n???????????????????? ???????? ?????? ???????????????? ????????????????: {quantity}.\n" \
                       f"??????????????????: ?????????????????? ?????????? {product[0].product_Name} ?????????? {quantity} ????. ???????????????? {predicted_price:.2f}$.\n\n"
    subject = f'?????????????? ???????????????????????? {user_name} {user_surname}, ???????????????????? {order_date}, {order_time}.'
    send_mail(subject=subject, message=message, from_email=source_mail,
              recipient_list=[destination_mail])


if __name__ == "__main__":
    # Lookup step, 1 is the next day
    LOOKUP_STEP = 15

    # stock market ticker
    ticker = "AAPL"

    print(
        f"Future price after {LOOKUP_STEP} days is {get_future_price(ticker=ticker, lookup_step=LOOKUP_STEP, epochs=300):.2f}$")
