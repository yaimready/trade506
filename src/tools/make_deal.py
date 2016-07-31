#! coding=utf-8

import re
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

def _f2price(f):
    result=re.match('^(\\d+?)\\.(\\d{1,2})$',f)
    if not result:
        raise Exception('float string [%s] can not convert to price'%(f))
    integer_part,float_part=result.groups()
    return int(integer_part)*100+int(float_part)

def make_test():
    while True:
        amount=random.randint(1,100)
        # 浮点数精度不可靠，所有数字都扩大100倍，用于存放第二位的浮点数
        price='%d.%02d'%(random.randint(90,109),random.randint(0,99))
        #trade_type=random.choice(['buy','sell','buy_market','sell_market'])
        trade_type=random.choice(['buy','sell'])
        data={
            'symbol':'YYH',
            'type':trade_type,
            'price':_f2price(price),
            'amount':amount
        }
        try:
            trade_result=make_request('http://localhost:5000/trade.do',data)
        except:
            traceback.print_exc()
            raise
            trade_result={'result':False}
        if trade_result['result']:
            print('trade made , order id is %d , price is %s'%(trade_result['order_id'],price))
        else:
            print('trade failed')
        time.sleep(1)

if __name__=='__main__':
    make_test()
