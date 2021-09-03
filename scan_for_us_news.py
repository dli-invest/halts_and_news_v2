import pandas as pd
import requests
import time
from yahooquery import Ticker
from io import StringIO
from datetime import datetime, timedelta
NEWS_WINDOW = 24

# download tickers from other project
def get_usd_tickers():
    url = "https://raw.githubusercontent.com/dli-invest/eod_tickers/main/data/us_stock_data.csv?raw=true"
    r = requests.get(url, allow_redirects=True)
    s = r.content
    return pd.read_csv(StringIO(s.decode('utf-8')))


us_tickers = get_usd_tickers()

# filter tickers out by market cap, only really care about super large companies and super small companies
# MARKET CAP < 1 BILLION or greater than 200 BILLION

# Also filter by category
# For yahoo finance tickers, most of the US tickers are missing a prefix
# use pandas to add a new column with the semicolon on the ticker name
# 
# 
# 
desired_tickers = us_tickers.loc[(us_tickers['MarketCap'] >= 500e9) | (us_tickers['MarketCap'] <= 1e8)] 

today = datetime.today()

ticker = Ticker("AABVF")
events = ticker.corporate_events
if isinstance(events, str):
    pass
print(events)
if isinstance(events, dict):
    print("probably rate limited")
    pass
new_events = events.xs("AABVF")
print(new_events.index)
if today in new_events.index:
    print("IT WORKS KINDA")
    print(new_events.loc[today])
    exit(1)
# break

for index, row in desired_tickers.iterrows():
    symbol = row["symbol"]
    # strip semicolon
    symbol = symbol.split(":")[0]
    print(symbol)
    break
    
    