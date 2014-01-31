import datetime as dt
import sys
import matplotlib.pyplot as plt
import csv
import os
import subprocess
from util import *

def marketsim():
    V0=10000
    orderfile = "orders_from_event_profiler_bollinger.csv"
    valuesfile = "values_event_profiler_bollinger.csv"
    
    orders = np.loadtxt(orderfile, dtype=[('year',int),('month',int), ('day',int),
    ('symbols',str, 25),('trans',str, 25), ('nstocks',int)], delimiter=',')
    n_orders = len(orders['year'])
    
    # get the list of symbols
    symbols = []
    date_order_csv = []
    
    for i in range(n_orders):
        if (orders['symbols'][i] not in symbols):
            symbols.append(orders['symbols'][i])		
        date_order = dt.datetime(orders['year'][i],orders['month'][i],orders['day'][i])
        date_order_csv.append('{:%Y-%m-%d}'.format(date_order))
        
    # sort orders by date
    sorted_date_order_csv = []
    idx_sort = np.argsort(date_order_csv)
    sorted_orders = orders.copy()
    for i in range(n_orders):
        sorted_date_order_csv.append(date_order_csv[idx_sort[i]])
        sorted_orders['year'][i] = orders['year'][idx_sort[i]]
        sorted_orders['month'][i] = orders['month'][idx_sort[i]]
        sorted_orders['day'][i] = orders['day'][idx_sort[i]]
        sorted_orders['symbols'][i] = orders['symbols'][idx_sort[i]]
        sorted_orders['trans'][i] = orders['trans'][idx_sort[i]]
        sorted_orders['nstocks'][i] = orders['nstocks'][idx_sort[i]]
        
    startdate =  dt.datetime(sorted_orders['year'][0],sorted_orders['month'][0],sorted_orders['day'][0])
    
    data = get_data(startdate=startdate, enddate=dt.datetime.now(), symbols=symbols)
    print symbols
    nall = len(data)
    all_dates = []
    timestamps = list(data.index)
    for i in range(nall): 
        date = '{:%Y-%m-%d}'.format(timestamps[i])
        all_dates.append(date)   
    
    own = np.zeros(data.shape)
    cash = np.zeros(nall) + V0
    
    for i in range(n_orders):
        idx_date = all_dates.index(sorted_date_order_csv[i]) 
        idx_symbol = symbols.index(sorted_orders['symbols'][i])
        
        if  (sorted_orders['trans'][i] == "Buy"):
            own[idx_date:,idx_symbol] += sorted_orders['nstocks'][i]
            cash[idx_date:] -= sorted_orders['nstocks'][i] * data.values[idx_date,idx_symbol]
        if (sorted_orders['trans'][i] == "Sell"):
            own[idx_date:,idx_symbol] -= sorted_orders['nstocks'][i]	 
            cash[idx_date:] += sorted_orders['nstocks'][i] * data.values[idx_date,idx_symbol]
    
    value = own * data
    total_value = value.sum(axis=1)
    port_values = cash + total_value
    
    return port_values

def analysis():
        
     port_values = marketsim()
     returns  = port_values/port_values.shift(1) - 1
     total_earned = (port_values[-1]-port_values[0])*100./port_values[0]
     print "Total Earned:", total_earned
     cumulative_daily_returns_fund = np.cumprod(returns + 1,axis=0)
     print "Total Return of Fund:", cumulative_daily_returns_fund[-1]
     fund_sd = np.std(returns)
     print "Standard Deviation of Fund:", fund_sd  
     fund_ave = np.mean(returns)
     print "Average Daily Return of Fund:", fund_ave  
     sharpe_ratio =  np.sqrt(252) * fund_ave / fund_sd
     print "Sharpe Ratio of Fund:", sharpe_ratio
     
     stats = [total_earned, fund_sd, sharpe_ratio]
     return stats   
     
if __name__ == "__main__":
   #port_values = marketsim()
   stats = analysis() 
   print stats
        
            
            