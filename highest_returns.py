import MySQLdb as mdb
import datetime as dt
from util import *
from find_events import *
from marketsim import *

def store_highest_returns(startdate=dt.date(2014,01,01), nmax = 30):
 
    prices = get_data(startdate=startdate, enddate=dt.datetime.now(), symbols="all")
    
    # calculate the rate of return of all symbols
    dates = prices.index.tolist()
    returns = 100*(prices.loc[dates[-1]] - prices.loc[dates[0]])/prices.loc[dates[0]]
    returns.sort()
    
    best = returns[-nmax:]

    # store highest returns in DB
    con = mdb.connect(host='localhost', user='root', db='stocks')
    cur = con.cursor()
          
    now = dt.datetime.now()
    column_str  = """ticker, ret, date_added"""  
    insert_str = ("%s, " * 3)[:-2]

    sql = "INSERT INTO best_stocks (%s) VALUES (%s);" % (column_str, insert_str)
    best_stocks = []
    for i in range(nmax):
        cur.execute(sql, (best.index[i], best[i], now))
        con.commit()
        
    return best

def best_returns_crisis(startdate=dt.date(2008,01,01), enddate=dt.date(2009,05,01)):
 
    prices = get_data(startdate=startdate, enddate=enddate, symbols="all")
    
    # calculate the rate of return of all symbols
    dates = prices.index.tolist()
    returns = 100*(prices.loc[dates[-1]] - prices.loc[dates[0]])/prices.loc[dates[0]]
    returns.sort()
    
  
    best_crisis = []
    return_spy = (prices['SPY'][-1] - prices['SPY'][0])/prices['SPY'][0]
    
    symbols = prices.columns.tolist()
    for sym in symbols:
        if sym == 'BRK.B': continue
        if sym == 'FB': continue
        if sym == 'TRIP': continue
        if sym == 'ABBV': continue
  
        events, rec_ev, rec_trans, rec_trans_p, prof_trans = fetch_events(symbols=[sym], startdate=startdate, enddate=enddate)
        if not events: continue
        port = marketsim()
        ret_strategy = (port[-1] - port[0])/port[0]
        if ret_strategy > return_spy:
            best_crisis.append((sym,ret_strategy))

    # # store highest returns in DB
    # con = mdb.connect(host='localhost', user='root', db='stocks')
    # cur = con.cursor()
    #       
    # now = dt.datetime.now()
    # column_str  = """ticker, ret, ret_spy, date_added"""  
    # insert_str = ("%s, " * 4)[:-2]
    # 
    # sql = "INSERT INTO best_crisis (%s) VALUES (%s);" % (column_str, insert_str)
    # for i in range(len(best_crisis)):
    #     cur.execute(sql, (best_crisis[i][0], best_crisis[i][1], ret_spy, now))
    #     con.commit()
        
    return best_crisis, return_spy
    
    
if __name__ == "__main__":
   # best = store_highest_returns()
    best_crisis, ret_spy = best_returns_crisis()