import pandas as pd
import requests
import time
import dateparser
import json
import os
from cad_tickers.sedar.tsx import get_news_and_events
from io import StringIO
from datetime import datetime, timedelta
import pytz

NEWS_WINDOW = 24


def make_discord_request(embeds = []):
    data = {}
    data["embeds"] = embeds
    resp = requests.post(
        discord_url, data=json.dumps(data), headers={"Content-Type": "application/json"}
    )
    print(resp.content)

def map_news_to_discord(news_item: dict, symbol):
    web_title = news_item.get("headline", "").\
        replace('.', '').\
        replace(':', '').\
        replace('(', '').\
        replace(')', '').\
        replace(',', '').\
        replace('$', '').\
        replace('%', '').\
        replace('-', '').\
        replace(" ", "_")
    webmoney_url = f"{base_news_url}/{symbol}/news/{news_item.get('newsid')}/{web_title}"

    source = news_item.get("source")
    provider_url = "https://quotemedia.com"
    if source.lower().find("newswire") == -1:
        provider_url = "https://www.newswire.ca"
    elif source.lower().find("accesswire"):
        provider_url = "https://www.accesswire.com/newsroom/"

    return {
        "title": news_item.get("headline"),
        "url": webmoney_url,
        "description": news_item.get("description"),
        "timestamp": news_item.get("datetime"),
        "author": {
            "name": news_item.get("source"),
            "url": provider_url
        }
    }

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

desired_tickers = desired_tickers.head(1000)

base_news_url = "https://money.tmx.com/en/quote"

discord_url = os.getenv("DISCORD_WEBHOOK")
if discord_url == None:
    print('DISCORD_WEBHOOK Missing')
    exit(1)

items_to_send = []
utc=pytz.UTC
# rate limit of discord is 2 seconds
for index, row in desired_tickers.iterrows():
    symbol = row["symbol"]
    data = get_news_and_events(symbol, 1, 3)
    news = data.get("news", [])
    if len(news) == 0:
        continue
    else:
        for news_item in news:
            news_date = dateparser.parse(news_item.get("datetime"))
            now = utc.localize(datetime.now())
            # grab news within 24 hours
            #earliest_send_time = (now-timedelta(hours=int(NEWS_WINDOW))) 
            # challenge.datetime_end = utc.localize(challenge.datetime_end) 
            if now-timedelta(hours=int(NEWS_WINDOW)) <= news_date <= now:
                mapped_item = map_news_to_discord(news_item, symbol)
                print("appending", mapped_item)
                items_to_send.append(mapped_item)
            else:
                break
    # clear cache 
    if len(items_to_send) >= 9:
        make_discord_request(items_to_send)
        items_to_send = []
        time.sleep(2)
    time.sleep(0.1)

if len(items_to_send) > 0:
    make_discord_request(items_to_send)
