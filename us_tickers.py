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

from lxml.html import fromstring
import requests
from itertools import cycle
import traceback
def get_proxies():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies = set()
    for i in parser.xpath('//tbody/tr')[:10]:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
    proxies.add(proxy)
    return proxies

#If you are copy pasting proxy ips, put in the list below
#proxies = ['121.129.127.209:80', '124.41.215.238:45169', '185.93.3.123:8080', '194.182.64.67:3128', '106.0.38.174:8080', '163.172.175.210:3128', '13.92.196.150:8080']
proxies = get_proxies()
proxy_pool = cycle(proxies)
valid_proxies = []
proxy_on = 0
url = 'https://httpbin.org/ip'
for i in range(1,11):
    #Get a proxy from the pool
    proxy = next(proxy_pool)
    print("Request #%d"%i)
    try:
        response = requests.get(url,proxies={"http": proxy, "https": proxy})
        print(response.json())
        valid_proxies.append(proxy)
    except:
#Most free proxies will often get connection errors. You will have retry the entire request using another proxy to work. 
#We will just skip retries as its beyond the scope of this tutorial and we are only downloading a single url 
    print("Skipping. Connnection error")

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
    try:
        data = get_news_and_events(symbol, 1, 3)
    except Exception as e:
        os.environ["HTTP_PROXY"] = valid_proxies[proxy_on]
        os.environ["HTTPS_PROXY"] = valid_proxies[proxy_on]
        proxy_on = proxy_on + 1
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
        time.sleep(1)
    time.sleep(0.6)

if len(items_to_send) > 0:
    make_discord_request(items_to_send)
