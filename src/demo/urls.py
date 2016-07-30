from . import views

urlpatterns=[
    ('/',views.TradeHandler,'show'),
    ('/trade.do',views.TradeHandler,'trade'),
    ('/cancel_order.do',views.TradeHandler,'cancel')
    ]
