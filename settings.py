import re

BASE_PROTO = 'https'
BASE_HOST = 'habrahabr.ru'
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 8000

TM_REGSUB = re.compile(r'\b(\w{6})\b')

DENY_RESPONSE = [
    'Vary',
    'Content-Encoding',
    'Transfer-Encoding',
    'Connection',
    'Set-Cookie',
]

SKIP_TAGS = ['code', 'script', 'svg', 'select']
