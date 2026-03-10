from yahooquery import Ticker
from curl_cffi import requests
session = requests.Session(impersonate="safari15_3")
t = Ticker("AAPL", session=session, asynchronous=False)
try:
    print(list(t.price.keys()))
except Exception as e:
    print(e)
