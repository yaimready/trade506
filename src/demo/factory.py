# coding=utf-8


'''

--- 表结构 ---

trade_object {
    
    name 交易标的
    score 成交价

}

trade_order {

    object_name 交易标的名称
    type 交易类型 buy = 买入 sell = 卖出
    price 挂单价格
    amount 交易数量
    complete 交易是否完成？0 = 未交易完成 1 ＝ 交易完成
    changed_amount 已交易数量
    canceled_amount 撤销的数量，用于记录部分成交

}

--- 撮合成交 ---

撮合成交的前提是买入价必须大于或等于卖出价。也就是价格优先原则。
撮合价格计算方法：
撮合成交的前提是：买入价（A）必须大于或等于卖出价（B），即A>B。
计算依据：计算机在撮合时实际上是依据前一笔成交价而定出最新成交价的。
假设：前一笔的成交价格为C，最新成交价为D；
则，当
A<=C时，D=A；（如果前一笔成交价高于 或等于买入价，则最新成交价就是买入价）
B>=C时，D=B；（如果前一笔成交价低于或等于卖出价，则最新成交价就是卖出价）
B<C<A时，D=C；（如果前一笔成交价在卖出价与买入价 之间，则最新成交价就是前一笔的成交价）
撮合价的优点：既显示了公平性，又使成交价格具有相对连续性，避免了不必要的无规律跳跃。


'''


import traceback
import logging
import sqlite3

def price2f(integer):
    integer_part=integer/100
    float_part=integer%100
    float_fill='0' if float_part<10 else ''
    return '%d.%s%d'%(integer_part,float_fill,float_part)

class MissingTradeObjectException(Exception):
    pass

class TradeFactory(object):

    def __init__(self):
        self._db=sqlite3.connect('trade.db',isolation_level=None)
        self._load_data()
        self._trade_logger=logging.getLogger('trade')
        self._order_logger=logging.getLogger('order')

    def _load_data(self):
        sql='create table if not exists trade_object(id integer primary key,name varchar(50) unique'
        sql+=',score int,max_score int,min_score int);'
        self._db.execute(sql);
        sql='create table if not exists trade_order(id integer primary key'
        sql+=',object_name varchar(50),type varchar(50),price int,amount int,complete int,changed_amount int,canceled_amount int);'
        self._db.execute(sql)
        # 浮点数精度不可靠，所有数字都扩大100倍，用于存放第二位的浮点数
        self._db.execute('replace into trade_object(name,score,max_score,min_score) values (?,?,?,?);',('YYH',10000,11000,9000))

    def get_objects(self):
        cursor=self._db.execute('select name,score from trade_object')
        rows=cursor.fetchall()
        cursor.close()
        result=[]
        for name,score in rows:
            result.append({'name':name,'score':score})
        return result

    def check_object(self,name,price):
        cursor=self._db.execute('select max_score,min_score from trade_object where name=?',(name,))
        max_score,min_score=cursor.fetchone()
        cursor.close()
        return price<max_score and price>=min_score

    def get_score(self,name):
        cursor=self._db.execute('select score from trade_object where name=?',(name,))
        score,=cursor.fetchone()
        cursor.close()
        return score

    def _set_score(self,name,val):
        self._db.execute('update trade_object set score=? where name=?',(val,name))

    def _get_cheapest_sell(self,name,buy_price):
        sql='select id,price,amount-changed_amount,amount from trade_order where complete=0 and type=? and price<=? order by price asc limit 0,1'
        # 选取价格比你出价尽可能低且正在卖出的订单
        cursor=self._db.execute(sql,('sell',buy_price))
        row=cursor.fetchone()
        if row is None:
            return None
        else:
            id,price,amount,total_amount=row
            return {
                'id':id,
                'price':price,
                'amount':amount,
                'total_amount':total_amount
            }

    def _get_highest_buy(self,name,sell_price):
        sql='select id,price,amount-changed_amount,amount from trade_order where complete=0 and type=? and price>=? order by price desc limit 0,1'
        # 选取价格比你出价尽可能高且正在买入的订单
        cursor=self._db.execute(sql,('buy',sell_price))
        row=cursor.fetchone()
        if row is None:
            return None
        else:
            id,price,amount,total_amount=row
            return {
                'id':id,
                'price':price,
                'amount':amount,
                'total_amount':total_amount
            }

    def _update_order_amount(self,order_id,add_amount):
        self._db.execute('update trade_order set changed_amount=changed_amount+? where id=?',(add_amount,order_id))
        self._db.execute('update trade_order set complete=1 where id=? and changed_amount==amount;',(order_id,))

    def _make_trade(self,order_from,amount,prices):
        sell_price,buy_price,score=prices
        if buy_price<=score:
            new_score=buy_price
        elif sell_price>=score:
            new_score=sell_price
        else:
            new_score=score
        print('make_trade --> buy=%s,sell=%s,score=%s,new_score=%s'%(price2f(buy_price),price2f(sell_price),price2f(score),price2f(new_score)))
        if order_from:
            self._update_order_amount(order_from,amount)
        return new_score

    def _create_order(self,name,trade_type,amount,price,complete=0,canceled_amount=0):
        sql='insert into trade_order(object_name,type,amount,price,complete,changed_amount,canceled_amount)'
        sql+=' values (?,?,?,?,?,?,?)'
        if complete==1:
            changed_amount=amount
        else:
            changed_amount=0
        cursor=self._db.execute(sql,(name,trade_type,amount,price,complete,changed_amount,canceled_amount))
        order_id=cursor.lastrowid
        cursor.close()
        return order_id

    def _log_trade(self,price,amount):
        self._trade_logger.info('price is %s,amount is %d'%(price2f(price),amount))

    def _log_order(self,order_id,amount,status):
        cursor=self._db.execute('select object_name,type,price from trade_order where id=?',(order_id,))
        row=cursor.fetchone()
        cursor.close()
        if row is None:
            return
        name,trade_type,price=row
        verb_table={
            'part_deal':'partly',
            'part_cancel':'partly cancel',
            'full_deal':'totally',
            'full_cancel':'totally cancel'
        }
        self._order_logger.info('somebody %s %s [%s] with [%s] price , amount is %d'%(verb_table[status],trade_type,name,price2f(price),amount))

    def _buy(self,name,amount,buy_price=None):
        buy_amount=amount
        # score为成交价，市价订单和成交价一致
        score=self.get_score(name)
        if buy_price is None:
            buy_price=score
        # 获取价格比你出价便宜的订单
        sell=self._get_cheapest_sell(name,buy_price)
        if sell is None:
            raise MissingTradeObjectException('buy failed')
        # 价格元组，依次为卖方、买方、上一成交价
        prices=sell['price'],buy_price,score
        if buy_amount<=sell['amount']:
            # 成交后，得出新的成交价
            score=self._make_trade(sell['id'],buy_amount,prices)
            status='part_deal' if sell['total_amount']!=buy_amount else 'full_deal'
            self._log_order(sell['id'],buy_amount,status)
            self._log_trade(score,buy_amount)
            buy_amount=0
        else:
            # 买入的超过卖出的数量，全部买入
            score=self._make_trade(sell['id'],sell['amount'],prices)
            status='part_deal' if sell['total_amount']!=sell['amount'] else 'full_deal'
            self._log_order(sell['id'],sell['amount'],status)
            self._log_trade(score,sell['amount'])
            buy_amount=buy_amount-sell['amount']
        # 保存最后的成交价
        self._set_score(name,score)
        # 返回成交价和还未买入的数量
        return score,buy_amount

    def buy_market(self,name,amount):
        score,buy_amount=self._buy(name,amount,None)
        order_id=self._create_order(name,'buy_market',amount-buy_amount,score,1,buy_amount)
        # 记录被撤销的剩余交易
        if buy_amount:
            self._log_order(order_id,amount-buy_amount,'part_deal')
            self._log_order(order_id,buy_amount,'part_cancel')
        else:
            self._log_order(order_id,amount,'full_deal')
        return order_id

    def _sell(self,name,amount,sell_price):
        sell_amount=amount
        score=self.get_score(name)
        buy=self._get_highest_buy(name,sell_price)
        if buy is None:
            raise MissingTradeObjectException('sell failed')
        # 价格元组，依次为卖方、买方、上一成交价
        prices=sell_price,buy['price'],score
        if sell_amount<=buy['amount']:
            # 成交后，得出新的成交价
            score=self._make_trade(buy['id'],sell_amount,prices)
            status='part_deal' if buy['total_amount']!=sell_amount else 'full_deal'
            self._log_order(buy['id'],sell_amount,status)
            self._log_trade(score,sell_amount)
            sell_amount=0
        else:
            # 卖出的超过买入的数量，全部卖出
            score=self._make_trade(buy['id'],buy['amount'],prices)
            status='part_deal' if buy['total_amount']!=buy['amount'] else 'full_deal'
            self._log_order(buy['id'],buy['amount'],status)
            self._log_trade(score,buy['amount'])
            sell_amount=sell_amount-buy['amount']
        # 保存最后的成交价
        self._set_score(name,score)
        # 返回成交价和还未卖出的数量
        return score,sell_amount

    def sell_market(self,name,amount):
        score,sell_amount=self._sell(name,amount,None)
        order_id=self._create_order(name,'sell_market',amount-sell_amount,score,1,sell_amount)
        # 记录被撤销的剩余交易
        if sell_amount:
            self._log_order(order_id,amount-sell_amount,'part_deal')
            self._log_order(order_id,sell_amount,'part_cancel')
        else:
            self._log_order(order_id,amount,'full_deal')
        return order_id

    def buy(self,name,amount,price):
        try:
            score,buy_amount=self._buy(name,amount,price)
            trade_ok=True
        except MissingTradeObjectException:
            trade_ok=False
        if trade_ok:
            if buy_amount:
                order_id=self._create_order(name,'buy',amount,price,0,buy_amount)
                self._log_order(order_id,amount-buy_amount,'part_deal')
                self._update_order_amount(order_id,amount-buy_amount)
                return order_id
            else:
                order_id=self._create_order(name,'buy',amount,price,1)
                self._log_order(order_id,amount,'full_deal')
                return order_id
        else:
            return self._create_order(name,'buy',amount,price,0)

    def sell(self,name,amount,price):
        try:
            score,sell_amount=self._sell(name,amount,price)
            trade_ok=True
        except MissingTradeObjectException:
            trade_ok=False
        if trade_ok:
            if sell_amount:
                order_id=self._create_order(name,'sell',amount,price,0,sell_amount)
                self._log_order(order_id,amount-sell_amount,'part_deal')
                self._update_order_amount(order_id,amount-sell_amount)
                return order_id
            else:
                order_id=self._create_order(name,'sell',amount,price,1)
                self._log_order(order_id,amount,'full_deal')
                return order_id
        else:
            return self._create_order(name,'sell',amount,price,0)

    def cancel(self,order_id):
        cursor=self._db.execute('select amount,changed_amount from trade_order where id=? and complete=0',(order_id,))
        row=cursor.fetchone()
        cursor.close()
        if row is None:
            raise Exception('trade has been made')
        amount,changed_amount=row
        if changed_amount==0:
            self._log_order(order_id,amount,'full_cancel')
        else:
            self._log_order(order_id,amount-changed_amount,'part_cancel')
        # 如果无交易，则完全撤销。
        # 否则部分成交，剩余撤销
        self._db.execute('update trade_order set canceled_amount=amount-changed_amount,amount=changed_amount,complete=1 where id=?',(order_id,))
