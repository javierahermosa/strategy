import os 
from flask import Flask, render_template, send_from_directory, request, flash, redirect, url_for
import MySQLdb
#from events import *
from marketsim import analysis
from forms import InputForm
from find_events import *
from kalman import *
from util import *
from flask import jsonify

app = Flask(__name__)

app.secret_key = "talca"
app.CSRF_ENABLED = True
app.WTF_CSRF_SECRET_KEY = 'a random string'

app.config.update(
    DEBUG=True
)

con = mdb.connect(host='localhost', user='root', db='stocks')
cur = con.cursor()

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

    
@app.route("/", methods=['GET', 'POST'])
def index():
    #b20 = get_highest_returns()
    #b20ticks = b20.index
    last_update_query = cur.execute("""SELECT MAX(date_added) FROM best_stocks;""")
    last_update = (cur.fetchall())[0][0]
    
    best_query = cur.execute("""SELECT ticker, ret FROM best_stocks \
                    WHERE date_added='%s' ORDER BY ret desc;""" % last_update)
    best_sql = cur.fetchall()
    best = [d for d in best_sql]
    
    rec_query =  cur.execute("""SELECT ticker, date_recommended, type FROM recommended_trades \
                    ORDER BY date_recommended desc LIMIT 1;""")
    rec_sql = cur.fetchall()           
    notifications = [rec for rec in rec_sql]
    recommend = []
    for notif in notifications:
        if (notif[1].year == last_update.year) & (notif[1].month == last_update.month) & (notif[1].day == last_update.day):
            recommend.append(notif)
        
    #ev, rec_ev, rec_trans, rec_trans_p, prof_trans = fetch_events()

    form = InputForm(request.form)
    
    if form.validate_on_submit():
        stock = form.stock.data
        strategy = form.strategy.data
        email = form.email.data
        
        if email:
            insert = """INSERT INTO notifications (email) VALUES ('%s') """ % email
            cur.execute(insert)
            con.commit()
        kalman = kalman_stock([stock])
        if stock == "FB":
            startdate = dt.date(2012,05,18)
            enddate =dt.datetime.now()
        elif stock == "TRIP":
            startdate = dt.date(2011,12,21)
            enddate =dt.datetime.now()
        elif stock == "ABBV":
            startdate = dt.date(2013,01,01)
            enddate =dt.datetime.now()
        else: 
            startdate=dt.date(2008,01,01)
            enddate = dt.date(2009,05,01) 
  
        data_df = get_data(symbols=[stock], startdate=startdate, enddate=enddate)
        return_holding = (data_df.values[-1]-data_df.values[0])*100./data_df.values[0]
        dat = parseDFdata(data_df, stock)
    
        ev, rec_ev, rec_trans, rec_trans_p, prof_trans = fetch_events(symbols=[stock], startdate=startdate, enddate=enddate)  
        
        buy, sell = parseEvents(ev,data_df, stock)

        pos = [b[2] for b in rec_trans_p if b[2] > 0]
        if len(rec_trans_p):
            percent_correct_trans = len(pos)*100./float(len(rec_trans_p))
            last_trans = rec_trans_p[-1]
        else:
            percent_correct_trans = 0
        
        stats = analysis()
        return  render_template('results.html', stock=stock, n_events=len(ev), \
         stats=stats, strategy=strategy, kalman=kalman, percent_correct_trans=percent_correct_trans, \
             last_trans=last_trans, dat=dat, buy=buy, sell=sell, return_holding = return_holding, \
             startdate=startdate, enddate=enddate)
             
    return render_template('index.html', form=form, best=best, recommend=recommend, notifications=notifications)
    
def parseDFdata(priceDF, tick):
    priceDict = []
    dates = priceDF.index.astype(np.int64) // 10**9
    prices = priceDF[tick].values.tolist()
    for i in range(len(dates)):
        price = {'x': dates[i],  'y': prices[i]}
        priceDict.append(price)
    return priceDict

def parseEvents(events, priceDF, tick):
    buy = []
    sell = []
    dates = priceDF[tick][events.keys()].index.astype(np.int64) // 10**9
    price_at_event = priceDF[tick][events.keys()].values
    for i in range(len(dates)):
        price = {'x': dates[i],  'y': price_at_event[i]}
        if events.values()[i][0] == "Buy":
            buy.append(price)
        if events.values()[i][0] == "Sell":
            sell.append(price)
    return buy, sell
    
        

if __name__ == "__main__":
    port = int(os.environ.get("PORT",5000))
    app.run(host='0.0.0.0', port=port)

