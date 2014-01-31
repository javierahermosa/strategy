import datetime
from datetime import timedelta
import MySQLdb as mdb
import urllib2
import urllib

con = mdb.connect(host='localhost', user='root', db='stocks')

# Get ticker list from database
def obtain_list_of_db_tickers():
  with con: 
    cur = con.cursor()
    cur.execute("SELECT id, ticker FROM symbols")
    data = cur.fetchall()
    return [(d[0], d[1]) for d in data]

# Obtains data from Yahoo Finance returns and a list of tuples.
def get_daily_historic_data_yahoo(ticker,
                      start_date=(2000,1,1)):
    
    #end_date=datetime.date.today().timetuple()[0:3])
    _now =datetime.datetime.now();
    miss_ctr=0;
                      
    params= urllib.urlencode ({'a':start_date[1]-1, 'b':start_date[2], 'c':start_date[0], 'd':_now.month, 'e':_now.day, 'f':_now.year, 's': ticker})
    url = "http://ichart.finance.yahoo.com/table.csv?%s" % params
    
    try:
        yf_data = urllib2.urlopen(url).readlines()[1:] # Ignore the header
        prices = []
        for y in yf_data:
            p = y.strip().split(',')
            prices.append( (datetime.datetime.strptime(p[0], '%Y-%m-%d'),
                      p[1], p[2], p[3], p[4], p[5], p[6]) )
                      
        return prices

    except urllib2.HTTPError:
        miss_ctr += 1
        print "Unable to fetch data for stock: {0} at {1}".format(ticker, url)
    except urllib2.URLError:
        miss_ctr += 1
        print "URL Error for stock: {0} at {1}".format(ticker, url)
    
    

# Insert historical prices in DB
def insert_daily_data_into_db(symbol_id, daily_data):
  """Takes a list of tuples of daily data and adds it to the
  MySQL database. Appends the vendor ID and symbol ID to the data.

  daily_data: List of tuples of the OHLC data (with 
  adj_close and volume)"""
  
  # Create the time now
  now = datetime.datetime.now()

  # Amend the data to include the symbol ID
  daily_data = [(symbol_id, d[0], d[1], d[2], d[3], d[4], d[5], d[6], now) for d in daily_data]

  # Create the insert strings
  column_str = """symbol_id, date, open, high, low, close, volume, adj_close, last_update"""
  insert_str = ("%s, " * 9)[:-2]
  final_str = "INSERT INTO daily_price (%s) VALUES (%s)" % (column_str, insert_str)

  # Using the MySQL connection, carry out an INSERT INTO for every symbol
  with con: 
    cur = con.cursor()
    cur.executemany(final_str, daily_data)
    con.commit()
    
def insert_to_db_scratch():
    
    tickers = obtain_list_of_db_tickers()
    
    for t in tickers:
      print "Adding data for %s" % t[1]
      yf_data = get_daily_historic_data_yahoo(t[1])
      if yf_data:
          insert_daily_data_into_db(t[0], yf_data)
    print "Done."
    
def update_db():
    con = mdb.connect(host='localhost', user='root', db='stocks')
    sql = """SELECT last_update FROM daily_price AS dp ORDER BY dp.last_update DESC LIMIT 1;"""
    cur = con.cursor()
  
    # get last update
    cur.execute(sql)
    data = cur.fetchall()
    last_update = [d[0] for d in data]
  
    # get symbols
    tickers = obtain_list_of_db_tickers()
    today = datetime.datetime.today()
    startdate = last_update[0] + timedelta(days=1)
    if startdate < today:
        startdate = (int('{:%Y}'.format(startdate)), int('{:%m}'.format(startdate)), int('{:%d}'.format(startdate)))
        for t in tickers:
           print "Adding data for %s" % t[1]
           yf_data = get_daily_historic_data_yahoo(t[1], start_date=startdate)
           if yf_data:
               insert_daily_data_into_db(t[0], yf_data)
        print "DB is up to date."
    else: print "Nothing to do. DB is up to date."    
    
if __name__ == "__main__":
    update_db()