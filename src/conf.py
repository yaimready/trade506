import os
import sys

app_settings={
    'debug':True,
    'cookie_secret':'abcd',
}

app_options={
    'port':{'default':5000},
}

if hasattr(sys, 'frozen'):
  pypath = os.path.dirname(sys.executable)
else:
  pypath = os.path.dirname(__file__)

log_path=lambda f:os.path.join(pypath,'logs',f)

app_logfiles={
    'tornado.general':log_path('tornado_general.log'),
    'tornado.application':log_path('tornado_application.log'),
    'tornado.access':log_path('tornado_access.log'),
    'mino':log_path('mino.log'),
    'trade':log_path('trade.log'),
    'order':log_path('order.log')
}

js_path=os.path.abspath(os.path.join(pypath,'static/js'))

app_staticpaths={
    '/static/js/(.*)':js_path,
}
