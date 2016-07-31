# coding=utf-8

import traceback

from .factory import TradeFactory,price2f

class TradeHandler(object):

    def __init__(self):
        self._factory=TradeFactory()

    def post(self,req,action):
        self.get(req,action)

    def get(self,req,action):
        if action=='show':
            self.show_objects(req)
        elif action=='trade':
            try:
                order_id=self.make_trade(req)
                req.write({'result':True,'order_id':order_id})
            except:
                traceback.print_exc()
                req.write({'result':False})
        elif action=='cancel':
            try:
                self.cancel_order(req)
                req.write({'result':True})
            except:
                traceback.print_exc()
                req.write({'result':False})

    def show_objects(self,req):
        objects=self._factory.get_objects()
        for obj in objects:
            req.write('%s - %s<br/>'%(obj['name'],price2f(obj['score'])))

    def make_trade(self,req):
        object_name=req.get_argument('symbol','')
        if not object_name:
            raise Exception('empty object name')
        price=req.get_argument('price','')
        price=int(price)
        if not self._factory.check_object(object_name,price):
            raise Exception('invalid object name ( or symbol ) [%s] or price [%d]'%(object_name,price))
        amount=req.get_argument('amount','')
        amount=int(amount) # 外部函数会catch这个异常
        if not ( amount>0 and amount<1000):
            raise Exception('invalid amount')
        trade_type=req.get_argument('type','')
        if trade_type=='buy_market':
            return self._factory.buy_market(object_name,amount)
        elif trade_type=='sell_market':
            return self._factory.sell_market(object_name,amount)
        elif trade_type=='buy':
            return self._factory.buy(object_name,amount,price)
        elif trade_type=='sell':
            return self._factory.sell(object_name,amount,price)
        else:
            raise Exception('invalid trade type')

    def cancel_order(self,req):
        order_id=req.get_argument('order_id','')
        order_id=int(order_id)
        self._factory.cancel(order_id)



