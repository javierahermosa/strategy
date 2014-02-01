import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import os
from pandas import *
import pandas.io.sql as psql
import MySQLdb as mdb
import datetime as dt
import csv
import copy
import numpy as np
import operator
from machine import *
from util import *
import smtplib

def bollinger(data, period=21):
    means = pandas.rolling_mean(data, period, min_periods=period-1)
    std = pandas.rolling_std(data, period, min_periods=period-1)
    upper = means + std
    lower = means - std
    bollinger_val = (data - means) / std
    return  bollinger_val, means, upper, lower

def find_events_bollinger(symbols, data, period=21):
    

    orderfile =  "data/orders_from_event_profiler_bollinger.csv"
    outfile = open(orderfile, "wb")
    fileWriter = csv.writer(outfile, delimiter=',')
    
    eventfilename = "data/events.csv"
    outfile2 = open(eventfilename, "wb")
    eventfile = csv.writer(outfile2, delimiter=',')
    
    bollinger_val, m, u,l = bollinger(data, period=period)
        
    print "Finding Events..."
    df_events = copy.deepcopy(data)
    df_events = df_events * np.NAN
    
    timestamps = data.index
    events = {}
    for sym in symbols:
        for i in range(1, len(timestamps)):
            if bollinger_val[sym].values[i] <= -2.0  and bollinger_val[sym].values[i-1] >=-2.0:# and bollinger_val['SPY'].values[i] >=1.0:
                
                df_events[sym].ix[timestamps[i]] = 1
                events[timestamps[i]] = ("Buy", sym)
                eventfile.writerow([timestamps[i], sym, "Buy"])
                                     
                fileWriter.writerow([int('{:%Y}'.format(timestamps[i])), 
                                     int('{:%m}'.format(timestamps[i])), 
                                     int('{:%d}'.format(timestamps[i])) , sym,"Buy",100])
                if (i+5 < len(timestamps)):
                    fileWriter.writerow([int('{:%Y}'.format(timestamps[i+5])), 
                                         int('{:%m}'.format(timestamps[i+5])), 
                                         int('{:%d}'.format(timestamps[i+5])), sym,"Sell",100])
                else:
                    fileWriter.writerow([int('{:%Y}'.format(timestamps[-1])), 
                                         int('{:%m}'.format(timestamps[-1])), 
                                         int('{:%d}'.format(timestamps[-1])), sym,"Sell",100])
            elif bollinger_val[sym].values[i] >= 1.0  and bollinger_val[sym].values[i-1] <=1.0:
                eventfile.writerow([timestamps[i], sym, "Sell"])
                events[timestamps[i]] = ("Sell", sym)
                                
    outfile.close()
    return events    

def calculate_prob(recent_trans, type="Buy-Sell"):
    all_trans = len(recent_trans)
    df = DataFrame(recent_trans)
    success = df[(df[2].values>0)]
    if type == "Buy-Sell":
        success_t = df[(df[2].values>0) & (df[3] == "Buy-Sell")]
        t =  df[(df[3] == "Buy-Sell")]
    elif type == "Sell-Buy":
        success_t = df[(df[2].values>0) & (df[3] == "Sell-Buy")]
        t =  df[(df[3] == "Sell-Buy")]
    
    pE_S = len(success_t)/float(all_trans)
    pE = 0.5
    pS = len(success)/float(all_trans)
    return pE_S * pS / pE
    
    
def fetch_events(symbols='all',startdate=dt.date(2008,01,01), enddate= dt.datetime.now(), strategy="ma21"):
    
    data = get_data(startdate=startdate, enddate=enddate, symbols=symbols)
    symbols = data.columns.tolist()
    dates = data.index.tolist()
    
    if strategy == "ma21":
        events = find_events_bollinger(symbols, data, period=21)  
    elif strategy == "ma14":
        events = find_events_bollinger(symbols, data, period=14)
    if strategy == "ml":
        events = find_events_machine(symbols, data)
       
    sorted_events = sorted(events.iteritems(), key=operator.itemgetter(0))
    recent_events = sorted_events[-100:]
    
    if dates[-1] in events.keys():
        recommended_trans = events[dates[-1]]
    else: recommended_trans = None
    recent_trans = []
    recent_trans_p = []
    d = DataFrame(data)
    all_trans = 0
    for ev in recent_events:
        t0 = ev[0]
        sym = ev[1][1]
        p0 = d[sym].loc[t0]
        if ev[1][0] == "Buy":
            sell_on = dates.index(t0)+5
            if sell_on < len(dates):
                p5 = d[sym].iloc[sell_on]
                transaction_return = (p5-p0)*100/p0
                all_trans +=1
                #print "Buy-Sell", sym, transaction_return, t0
                trans = (t0, sym, transaction_return, "Buy-Sell")
                recent_trans.append(trans)
                p=calculate_prob(recent_trans, type="Buy-Sell")
                recent_trans_p.append((t0, sym, transaction_return, "Buy-Sell",p))
                
        if ev[1][0] == "Sell":
            p0 = d[sym].loc[t0]
            buy_on = dates.index(t0)+5
            if buy_on < len(dates):
                p5 = d[sym].iloc[buy_on]
                transaction_return = (p5-p0)*100/p0
                all_trans +=1
                trans = (t0, sym, transaction_return, "Sell-Buy")
                recent_trans.append(trans)
                p=calculate_prob(recent_trans,type="Sell-Buy")   
                recent_trans_p.append((t0, sym, transaction_return, "Sell-Buy",p))
                
    most_profitable_recent_trans = sorted(recent_trans, key=lambda student: student[2], reverse=True)[0:5]

    return events, recent_events, recommended_trans, recent_trans_p, most_profitable_recent_trans

def notify(rec):
    print "notifying..."
    if rec:
        con = mdb.connect(host='localhost', user='root', db='stocks')
        cur = con.cursor()
        
        # add to DB 
        now = dt.datetime.now()
        column_str  = """ticker, date_recommended, type"""  
        insert_str = ("%s, " * 3)[:-2]
        sql = "INSERT INTO recommended_trades (%s) VALUES (%s);" % (column_str, insert_str)
        cur.execute(sql, (rec[1], now, rec[0]))
        con.commit()
        
        cur.execute("SELECT email FROM notifications")
        query = cur.fetchall()
        emails = [q[0] for q in query]
        
        SMTPserver = 'smtp.gmail.com'
        sender = 'javiguedes@gmail.com'
                    
        for email in emails:
            from_addrs = 'javiguedes@gmail.com'
            to_addrs  = email
            msg = "\r\n".join([
              "From: %s",
              "To: %s",
              "Subject: Strategy Recommendation",
              "",
              "Strategy recommends you to %s %s TODAY!"
              ]) % (from_addrs, to_addrs, rec[0], rec[1])
              
            username = 'javiguedes'
            password = 'anacoreta1234'
            server = smtplib.SMTP('smtp.gmail.com')
            server.ehlo()
            server.starttls()
            server.login(username,password)
            
            try:
                server.sendmail(from_addrs, to_addrs, msg)
            
            except Exception, exc:
                sys.exit( "mail failed; %s" % str(exc) )
            
            server.quit()   
        return 1
    else: return 0

def plot_events(sym, startdate=dt.date(2008,01,01), enddate=dt.datetime.now(), period=21, plot_events=True):
    
    print "plotting " + sym
    print startdate, enddate
    data = get_data(startdate = startdate, enddate=enddate, symbols=[sym])
    bollinger_val, means, upper, lower = bollinger(data)
    events, rec_ev, rec_trans, rec_trans_p, prof_trans = fetch_events(symbols = [sym])
    
    event_times = events.keys()
    event_type = events.values()
    
    
    fig = plt.figure(figsize=(10,8))

    ax = fig.add_subplot(211)
    ax.plot(data.index,data[sym].values,label=sym, alpha=0.8, lw=2)
    ax.set_xlim(xmin=data.index[0], xmax=data.index[-1])
    ax.yaxis.set_major_locator(MaxNLocator(prune='both'))
    ax.legend(['Events'], loc=2, fancybox=True)
    
    plt.ylabel('Adjusted Close')
    ax1 = fig.add_subplot(212)
    ax1.set_ylim(-4,4)
    ax1.set_xlim(xmin=data.index[0], xmax=data.index[-1])
    ax1.plot(data.index,np.ones(len(data.index)),'--',lw=2, color="LightGray")
    ax1.plot(data.index,np.ones(len(data.index))*-1,'--',lw=2, color="LightGray")
    ax1.plot(data.index,np.ones(len(data.index))*2,':',lw=2, color="LightGray")
    ax1.plot(data.index,np.ones(len(data.index))*-2,':',lw=2, color="LightGray")
    
    if plot_events and events: ax1.vlines(event_times, -4,4, color="Green")
    
    plt.subplots_adjust(hspace=0.001)
    fig.autofmt_xdate(rotation=15)
    bv_sym = bollinger_val[sym].values
    test_nan = bv_sym[np.logical_not(np.isnan(bv_sym))]
    p_sym, = ax1.plot(data.index,bollinger_val[sym].values, color="Gray", lw=1.5)
    ax.legend([sym,'Moving Average'], loc=2, fancybox=True)
    plt.xlabel('Date')
    plt.ylabel('Normalized Price')

    if plot_events:
        image = 'static/img/bollinger/bollinger_'+sym+'.png'
    else:
        image = 'static/img/bollinger/bollinger_'+sym+'_ne.png'
    plt.savefig(image, format="png", dpi=300 )
    
    return
    
                             
if __name__ == "__main__":
    
    startdate = dt.date(2008,01,01)   
    # enddate = dt.date(2009,04,01)
    events, rec_ev, rec_trans, rec_trans_p, prof_trans = fetch_events(startdate=startdate, enddate= dt.datetime.now())
    #if notify(rec_trans): print "NOTIFIED!"
    
    data = get_data(startdate=startdate, enddate= dt.datetime.now())
    symbols = data.columns.tolist()
    for sym in symbols:
        print sym
        if sym != "BRK.B":
            plot_events(sym, startdate=startdate, enddate=dt.datetime.now(), period=21, plot_events=True)
            plot_events(sym, startdate=startdate, enddate=dt.datetime.now(), period=21, plot_events=False)
    
    

 
    
    
    