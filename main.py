from datetime import datetime
import json
import os
import websocket
import pandas as pd
import threading
import time

low_prediction = 0
high_prediction = 0
short_entry_point = 0
long_entry_point = 0
last_prediction_data_length = 0

this_current_candle_has_problem = False
current_balance = 10000
index = 1
isPositionOpen = False
stop_loss_price = 0
position_info = {}
position_df = pd.DataFrame();

file_path = 'C:\\Users\\Pixel\\PycharmProjects\\telegramsender\\predictions.xlsx'

last_modified_time = None

def check_file_modification():
    global last_modified_time
    current_modified_time = os.path.getmtime(file_path)
    if last_modified_time is None or current_modified_time != last_modified_time:
        last_modified_time = current_modified_time
        print("File has been modified!")
        load_predictionList()  # Dosyadaki veriyi yeniden yükle
    else:
        pass

def find_long_entry():
    global long_entry_point
    long_entry_point = (low_prediction * 1000) / 999
    return long_entry_point

def find_short_entry():
    global  short_entry_point
    short_entry_point = (high_prediction * 1000) / 1001
    return  short_entry_point

def find_short_profit():
    h_rate = (short_entry_point-low_prediction)/short_entry_point
    return h_rate

def find_long_profit():
    rate = (high_prediction-long_entry_point)/long_entry_point
    return rate



def load_predictionList():
    global low_prediction,high_prediction,last_prediction_data_length,this_current_candle_has_problem
    try:
        predictionsListDf=pd.read_excel("predictions.xlsx")
        if(len(predictionsListDf) > 0):
            last_prediction_data_length = len(predictionsListDf)
            high_column_name = "High_Prediction"
            low_column_name = "Low_Prediction"
            last_value_of_high = predictionsListDf.iloc[-1][high_column_name]
            last_value_of_low = predictionsListDf.iloc[-1][low_column_name]
            low_prediction = float(last_value_of_low)
            high_prediction = float(last_value_of_high)
            this_current_candle_has_problem = False
        else:
            high_prediction = 0
            low_prediction = 0
    except ValueError:
        print("predictions.xlsx file hasn't data.")


def is_a_signal(current_price):
    if high_prediction == 0 and low_prediction == 0:
        return False
    if current_price <= low_prediction and current_price >= high_prediction:
        return False
    if high_prediction <= low_prediction:
        return False
    short_entry = find_short_entry()
    long_entry = find_long_entry()
    if long_entry >= short_entry:
        return False

    short_profit_rate = find_short_profit()
    long_profit_rate = find_long_profit()
    if long_profit_rate >= 0.0015 and short_profit_rate >= 0.0015:
        return True
    return False

def on_message(ws, message):
    global isPositionOpen,current_balance,position_df,index,stop_loss_price,position_info,this_current_candle_has_problem
    data = json.loads(message)
    price = float( data['p'])

    if(price > high_prediction or price < low_prediction):
        this_current_candle_has_problem = True

    if isPositionOpen == True:
        if(position_info['position_direction'] == "long" and price >= position_info["take-profit"]):
            position_info['result'] = 'Success'
            current_balance =  current_balance + (abs(price - position_info['price'])/position_info['price']) * current_balance
            isPositionOpen = False

        elif (position_info['position_direction'] == "long" and price <  position_info['stop-loss']):
            position_info['result'] = 'Failed'
            current_balance = current_balance - (abs(price - position_info['price'])/position_info['price']) * current_balance
            isPositionOpen = False

        elif(position_info["position_direction"] == "short" and price <=  position_info["take-profit"]):
            position_info['result'] = 'Success'
            current_balance = current_balance + (abs(position_info['price'] - price)/position_info['price']) * current_balance
            isPositionOpen = False

        elif (position_info['position_direction'] == "short" and price > position_info['stop-loss']):
            position_info['result'] = 'Failed'
            current_balance = current_balance - (abs(position_info['price'] - price)/position_info['price']) * current_balance
            isPositionOpen = False

        if isPositionOpen == False:
            current_balance_str = format(current_balance, ".2f")
            current_balance = float(current_balance_str)
            position_info[ "position_stop_price"]=price
            position_info["Last_Balance"] = current_balance
            position_info["close-time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            position_df = position_df._append(position_info, ignore_index=True)
            position_df.to_excel("positions.xlsx")
            print("posizyon kapatıldı")
            this_current_candle_has_problem = True


    elif isPositionOpen == False and high_prediction != 0 and low_prediction != 0 and high_prediction > low_prediction and this_current_candle_has_problem != True:
        signalCheck = is_a_signal(price)
        if signalCheck:
            if price <= long_entry_point and price > low_prediction :
                print("Long pozisyon açıldı")
                isPositionOpen = True
                position_info = {
                    "index": index,
                    "price": price,
                    "stop-loss": low_prediction,
                    "take-profit": high_prediction,
                    "result": "",
                    "balance":current_balance,
                    "position_direction":"long",
                    "position_stop_price":0,
                    "start-time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                index = index + 1



            elif price >= short_entry_point and price < high_prediction :
                print("Short pozisyon açıldı")
                isPositionOpen = True
                position_info = {
                    "index": index,
                    "price": price,
                    "stop-loss": high_prediction,
                    "take-profit": low_prediction,
                    "result": "",
                    "balance": current_balance,
                    "position_direction": "short",
                    "start-time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "position_stop_price":0
                }
                index = index + 1

def on_error(ws, error):
    print(error)
def on_close(ws):
    print("### Bağlantı kapandı ###")
    time.sleep(10)
    print("### Tekrar bağlanmaya çalışıyor ###")
    start_websocket(socket)
def on_open(ws):
    print("### Bağlantı açıldı ###")

# WebSocket URL'si (btcusdt@trade, her işlemde fiyat bilgisi alır)
socket = "wss://stream.binance.com:9443/ws/btcusdt@trade"


# ws = websocket.WebSocketApp(socket, on_message=on_message, on_error=on_error, on_close=on_close)
# ws.on_open = on_open
# ws.run_forever()

# WebSocket istemcisi oluşturma ve başlatma
def start_websocket(socket):
    ws = websocket.WebSocketApp(socket, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()


def file_check_thread():
    while True:
        check_file_modification()
        time.sleep(1)  # 1 saniyede bir dosya değişikliğini kontrol et



# Observer iş parçacığı
file_thread = threading.Thread(target=file_check_thread)
file_thread.start()

# WebSocket istemcisi iş parçacığı
websocket_thread = threading.Thread(target=start_websocket, args=(socket,))
websocket_thread.start()

file_thread.join()
websocket_thread.join()


