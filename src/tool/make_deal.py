#! coding=utf-8

from __future__ import division

import json
import urllib
import urllib2
import random
import time
import traceback

def make_request(url,data):
    data=urllib.urlencode(data)
    resp=urllib2.urlopen(url,data)
    if resp.getcode()!=200:
        raise Exception('request failed')
    return json.loads(resp.read())

while True:
    amount=random.randint(1,100)
    # 浮点数精度不可靠，所有数字都扩大100倍，用于存放第二位的浮点数
    price=random.randint(9000,11000)
    #trade_type=random.choice(['buy','sell','buy_market','sell_market'])
    trade_type=random.choice(['buy','sell'])
    data={
        'symbol':'YYH',
        'type':trade_type,
        'price':price,
        'amount':amount
    }
    try:
        trade_result=make_request('http://localhost:5000/trade.do',data)
    except:
        traceback.print_exc()
        raise
        trade_result={'result':False}
    if trade_result['result']:
        print('trade made , order id is %d , price is %d'%(trade_result['order_id'],price))
    else:
        print('trade failed')
    time.sleep(1)
