import os
from pandas import *
import pandas.io.sql as psql
import MySQLdb as mdb
import datetime as dt
import numpy as np
import json

def get_data(startdate=dt.date(2008,01,01), enddate=dt.datetime.now(), symbols="all"):  
    if len(symbols)==1 and symbols[0]=="FB":
          startdate=dt.date(2012,05,18)
    if len(symbols)==1 and symbols[0]=="TRIP":
          startdate=dt.date(2011,12,21)
    if len(symbols)==1 and symbols[0]=="TRIP":
          startdate=dt.date(2013,01,01)
          
    print "getting data...."
    con = mdb.connect(host='localhost', user='root', db='stocks2')
    
    if symbols=="all":
        cur = con.cursor()
        cur.execute("SELECT ticker FROM symbols")
        data = cur.fetchall()
        tickers = [d[0] for d in data]
    else: tickers = symbols
    
    sql = """ SELECT dp.date
                FROM symbols AS sym
                INNER JOIN daily_price as dp
                ON dp.symbol_id = sym.id
                WHERE sym.ticker = 'GOOG'
                AND date >= '%s'
                AND date <= '%s'
                ORDER BY dp.date ASC; """ %(startdate, enddate)
                
    dates =  psql.frame_query(sql, con=con, index_col='date')
    timestamps = dates.index.tolist()    
   
    all_stocks_data =np.zeros((len(timestamps), len(tickers))) 
    all_stocks_data[:][:] = np.NAN

    for i, tick in enumerate(tickers):     
        sql = """ SELECT dp.date, dp.adj_close
                    FROM symbols AS sym
                    INNER JOIN daily_price as dp
                    ON dp.symbol_id = sym.id
                    WHERE sym.ticker = '%s'
                    AND date >= '%s'
                    AND date <= '%s'
                    ORDER BY dp.date ASC; """ %(tick, startdate, enddate)
                    
        stock =  psql.frame_query(sql, con=con, index_col='date')
        
        # not all stocks have data for all times
        if not stock.empty:
            stock_dates = np.reshape(stock.values, len(stock.values))
            all_stocks_data[-len(stock.values):,i] = stock_dates
            
    data = DataFrame(all_stocks_data, index=timestamps, columns=tickers)

    # Remove the NANs from price data   
    data = data.fillna(method = 'ffill')
    data = data.fillna(method = 'bfill')
    data = data.fillna(1.0)
    
    return data
    
def create_stocks_json():

    data = get_data()
    tickers = data.columns.tolist()
        
    with open('static/docs/stocks.json', 'w') as outfile:
      json.dump(tickers, outfile)
    
def get_symbols():
    con = mdb.connect(host='localhost', user='root', db='stocks2')
    with con: 
      cur = con.cursor()
      cur.execute("SELECT ticker FROM symbols")
      data = cur.fetchall()
      tickers = [d[0] for d in data]
      return tickers    
    
