import os
from dotenv import load_dotenv

# Жёстко удаляем прокси-переменные до всего остального
for proxy_var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 
                   'ALL_PROXY', 'all_proxy', 'SOCKS_PROXY', 'socks_proxy',
                   'REQUEST_CA_BUNDLE', 'CURL_CA_BUNDLE']:
    os.environ.pop(proxy_var, None)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
STEAM_API_KEY = os.getenv('STEAM_API_KEY')

# Прокси для Telegram в России
PROXY_URL = "http://127.0.0.1:10809"