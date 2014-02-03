import os
from pandas import *
import pandas.io.sql as psql
import MySQLdb as mdb
import datetime as dt
import subprocess
import csv
import copy
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import talib
from talib.abstract import *
from sklearn.ensemble import RandomForestClassifier
from util import *
from find_events import *


con = mdb.connect(host='localhost', user='root', db='stocks2')

def get_ticker_data(tick, startdate = dt.date(2008,01,01)):
    sql = """ SELECT dp.date, dp.adj_close, dp.high, dp.low, dp.volume
                FROM symbols AS sym
                INNER JOIN daily_price as dp
                ON dp.symbol_id = sym.id
                WHERE sym.ticker = '%s'
                AND date > '%s'
                ORDER BY dp.date ASC; """ %(tick, startdate)
                
    query =  psql.frame_query(sql, con=con, index_col='date')
    return query
    
def calculate_indicators(data):
    prices = data['adj_close'].values
    sma21 = talib.SMA(prices, timeperiod=21)
    sma14 = talib.SMA(prices, timeperiod=14)
    rsi21 = talib.RSI(prices,timeperiod=21)
    rsi14 = talib.RSI(prices,timeperiod=14)
    roc21 = talib.ROC(prices,timeperiod=21)
    roc14 = talib.ROC(prices,timeperiod=14)
    bbands = talib.BBANDS(prices, timeperiod=14)
    slowk, slowd = talib.STOCH(low=data['low'].values, high=data['high'].values, close=data['adj_close'].values)
    vol = data['volume']
    dVdt_df = vol.shift(1)/vol - 1
    dVdt = dVdt_df.values
    d = DataFrame({'sma21': sma21/100, \
                   'sma14': sma14/100, \
                   'rsi21': rsi21/100, \
                   'rsi14': rsi14/100, \
                   'roc21': roc21/100, \
                   'roc14': roc14/100, \
                   'slowk': slowk/100, \
                   'slowd': slowd/100, \
                   'dVdt': dVdt}, index=data.index)
    return d

def fillnans(df):
    df = df.fillna(method = 'ffill') 
    df = df.fillna(method = 'bfill')
    df = df.fillna(1.0)
    return df   
    

def generate_sets(gset="train"):
   
    if gset == "train":
        outfile = open("data/train.csv", "wb")
    elif gset == "test":
        outfile = open("data/test.csv", "wb")
    startdate = dt.date(2008,01,01)
    enddate = dt.datetime.now()
     
    print "getting data...."
    con = mdb.connect(host='localhost', user='root', db='stocks2')
    cur = con.cursor()
    cur.execute("SELECT ticker FROM symbols")
    data = cur.fetchall()
    tickers = [d[0] for d in data]
       
    sql = """ SELECT dp.date
                FROM symbols AS sym
                INNER JOIN daily_price as dp
                ON dp.symbol_id = sym.id
                WHERE sym.ticker = 'GOOG'
                AND date > '%s'
                ORDER BY dp.date ASC; """ %(startdate)
                
    dates =  psql.frame_query(sql, con=con, index_col='date')
    timestamps = dates.index.tolist()    
   
    all_stocks_data =np.zeros((len(timestamps), len(tickers))) 
    all_stocks_data[:][:] = np.NAN
    keys = ['date', 'adj_close', 'high', 'low', 'volume']

    for i, tick in enumerate(tickers):   
        if gset == "test" and i < 50: continue  
        query = get_ticker_data(tick, startdate=startdate)
        if not query.empty:
            data = DataFrame(query, columns=keys, index=query.index)
            d = calculate_indicators(data)
            data_tick = DataFrame(data['adj_close'].values, columns=[tick], index=data.index)
            bollinger_val, means, upper, lower = bollinger(data_tick)
            events = find_events_bollinger([tick], data_tick, period=21)
            # events = get_stock_events(tick, startdate=startdate, enddate=enddate)
            event_times = events.keys()
            event_type = events.values()
            d['boll'] = Series(bollinger_val[tick].values, index = d.index)
            d['target'] = Series(0, index = d.index)
            
            features = copy.deepcopy(d)
            features = fillnans(features.loc[event_times])
            
            for (k,date) in enumerate(event_times):
                if (k+5 < len(timestamps)):
                    delta =  data_tick[tick][event_times[-1]] - data_tick[tick][event_times[k]] 
                else:
                    delta =  data_tick[tick][event_times[k+5]] - data_tick[tick][event_times[k]] 
                
                if delta > 0: features['target'][date] =  1
                if delta < 0: features['target'][date] = -1
                    
                #delta_date = delta[date]
                # if event_type[k] == "Buy":
     #                if delta > 0: features['target'][date] = 1
     #            if event_type[k] == "Sell":
     #                if delta < 0: features['target'][date] = -1 
                  
            if gset=="train": 
                features.to_csv(outfile, sep='\t', header=False)
                if i==50: break
            if gset=="test" and i > 50:
                features.to_csv(outfile, sep='\t', header=False)
                if i==100: break
    return features

if __name__ == "__main__":    
#def machine(tick, startdate=dt.date(2008,01,01), enddate = dt.datetime.now()):
    if __name__ == "__main__":    
        tick='SPY'
        generate_sets("train")
        generate_sets("test")
        startdate=dt.date(2008,01,01)
        enddate = dt.datetime.now()
        query = get_ticker_data(tick, startdate=startdate)
        keys = ['date', 'adj_close', 'high', 'low', 'volume']
    
        if not query.empty:
            data = DataFrame(query, columns=keys, index=query.index)
            d = calculate_indicators(data)
            data_tick = DataFrame(data['adj_close'].values, columns=[tick], index=data.index)
            bollinger_val, means, upper, lower = bollinger(data_tick)
            events = find_events_bollinger([tick], data_tick, period=21)

            event_times = events.keys()
            event_type = events.values()
            d['boll'] = Series(bollinger_val[tick].values, index = d.index)
        
            features = d
            features = fillnans(features)
        
            try:
               with open('data/train.csv'):
                   pass   
            except IOError:
               dtrain = generate_sets(gset="train")
             
            try:
                with open('data/test.csv'):
                    pass   
            except IOError:
                dtrain = generate_sets(gset="test")
                
            print "predicting....."    
            dataset = np.genfromtxt(open('data/train.csv','r'), delimiter='\t')
            target = [x[11] for x in dataset]
            train = [x[1:11] for x in dataset]
            rf = RandomForestClassifier(n_estimators=100)
            rf.fit(train, target)
            
            
            dataset2 = np.genfromtxt(open('data/test.csv','r'), delimiter='\t')
            test = [x[1:11] for x in dataset2]
            target2 = [x[11] for x in dataset2]

            model1=rf.predict(test)
        
            eventfilename =  "data/events_machine.csv"
            outfile2 = open(eventfilename, "wb")
            eventfile = csv.writer(outfile2, delimiter=',')
        
            orderfile = "data/orders_from_event_profiler_machine.csv"
            outfile = open(orderfile, "wb")
            fileWriter = csv.writer(outfile, delimiter=',')
                           
            test2 = features[:][['sma21','sma14','rsi21','rsi14','roc21','roc14','slowk','slowd','dVdt','boll']].values
            model2 = rf.predict(test2)
            events = {}
            timestamps = list(d.index)
            for i in range(len(timestamps)): 
            
                if model2[i] == 1.0:
 
                    events[timestamps[i]] = "Buy"
                    eventfile.writerow([timestamps[i], tick, "Buy"])
                                     
                    fileWriter.writerow([int('{:%Y}'.format(timestamps[i])), 
                                         int('{:%m}'.format(timestamps[i])), 
                                         int('{:%d}'.format(timestamps[i])) , tick,"Buy",100])
                    if (i+5 < len(timestamps)):
                        fileWriter.writerow([int('{:%Y}'.format(timestamps[i+5])), 
                                             int('{:%m}'.format(timestamps[i+5])), 
                                             int('{:%d}'.format(timestamps[i+5])), tick,"Sell",100])
                    else:
                        fileWriter.writerow([int('{:%Y}'.format(timestamps[-1])), 
                                             int('{:%m}'.format(timestamps[-1])), 
                                             int('{:%d}'.format(timestamps[-1])), tick,"Sell",100])
                elif model2[i] == -1:
                    eventfile.writerow([timestamps[i], tick, "Sell"])
                    events[timestamps[i]] = "Sell"
                   
                    fileWriter.writerow([int('{:%Y}'.format(timestamps[i])), 
                                         int('{:%m}'.format(timestamps[i])), 
                                         int('{:%d}'.format(timestamps[i])) , tick,"Sell",100])
                    if (i+5 < len(timestamps)):
                        fileWriter.writerow([int('{:%Y}'.format(timestamps[i+5])), 
                                             int('{:%m}'.format(timestamps[i+5])), 
                                             int('{:%d}'.format(timestamps[i+5])), tick,"Buy",100])
                    else:
                        fileWriter.writerow([int('{:%Y}'.format(timestamps[-1])), 
                                             int('{:%m}'.format(timestamps[-1])), 
                                             int('{:%d}'.format(timestamps[-1])), tick,"Buy",100])   

        #return events    
    
