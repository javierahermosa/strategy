import datetime
import lxml.html
import MySQLdb as mdb

from math import ceil

def get_from_wiki():
  now = datetime.datetime.utcnow()
  page = lxml.html.parse('http://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
  symbolslist = page.xpath('//table[1]/tr')[1:]

  symbols = []
  for symbol in symbolslist:
    tds = symbol.getchildren()
    sd = {'ticker': tds[0].getchildren()[0].text,
        'name': tds[1].getchildren()[0].text,
        'sector': tds[3].text,
        'subsector': tds[4].text,
        'headquarters': tds[5].getchildren()[0].text}
    # Create a tuple (for the DB format) and append to the list
    symbols.append( (sd['ticker'], sd['name'], sd['sector'], sd['subsector'], sd['headquarters'], now) )
  symbols.append(('SPY', 'SP500', 'compilation', 'many', 'None', now))
  return symbols

def insert(symbols):
  con = mdb.connect(host='localhost', user='root', db='stocks')

  # Create the insert strings
  column_str = "ticker, name, sector, subsector,  headquarters, last_updated"
  insert_str = ("%s, " * 6)[:-2]
  final_str = "INSERT INTO symbols (%s) VALUES (%s)" % (column_str, insert_str)
  print final_str, len(symbols)

  # Insert each symbol
  with con: 
    cur = con.cursor()
    # This line avoids the MySQL MAX_PACKET_SIZE
    # Although of course it could be set larger!
    for i in range(0, int(ceil(len(symbols) / 100.0))):
      cur.executemany(final_str, symbols[i*100:(i+1)*100-1])
    con.commit()
    
if __name__ == "__main__":
   symbols = get_from_wiki()
   #insert(symbols) 
    
  