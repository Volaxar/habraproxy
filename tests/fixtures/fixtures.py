import socket as s

import pytest
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

from main import ProxyServer, ProxyProcessor
from settings import *


@pytest.fixture(scope='module', name='server')
def fixture_server():
    _server = ProxyServer(PROXY_HOST, PROXY_PORT)
    _server.start()
    yield
    _server.stop()


@pytest.fixture(name='socket')
def fixture_socket():
    _socket = s.socket(s.AF_INET, s.SOCK_STREAM)
    yield _socket
    _socket.close()


@pytest.fixture(scope='module', name='processor')
def fixture_processor():
    class StubServer:
        def __init__(self):
            self.server_port = PROXY_PORT

    processor = ProxyProcessor(None, None, StubServer())
    yield processor


@pytest.fixture(scope='class', name='replace_tm')
def fixture_replace_tm(processor):
    f = open(r'./fixtures/main.html')
    _soup = BeautifulSoup(f.read(), 'html.parser')
    f.close()
    body_tag = _soup.find('div', 'layout')
    processor.replace_tm_text(body_tag)
    yield _soup


@pytest.fixture(name='get_links')
def fixture_get_links():
    yield (
        '%s://%s' % (BASE_PROTO, BASE_HOST),
        '%s://%s/top/' % (BASE_PROTO, BASE_HOST),
        'http://%s:%s' % (PROXY_HOST, PROXY_PORT),
        'http://%s:%s/top/' % (PROXY_HOST, PROXY_PORT)
    )


@pytest.fixture(name='change_links')
def fixture_change_links():
    yield {
        'direct_ok': 'http://%s:%s/' % (PROXY_HOST, PROXY_PORT),
        'direct_fail': 'http://%s:8001/' % PROXY_HOST,
        'reverse_ok': '%s://%s/' % (BASE_PROTO, BASE_HOST),
        'reverse_new': 'https://tmtm.ru/'
    }


@pytest.fixture(scope='module', name='driver')
def fixture_driver():
    driver = webdriver.Chrome('./drivers/chromedriver.exe')
    driver.wait = WebDriverWait(driver, 10)
    driver.maximize_window()
    driver.delete_all_cookies()
    driver.get('http://%s:%s/' % (PROXY_HOST, PROXY_PORT))
    yield driver
    driver.quit()


@pytest.fixture(scope='module', name='habra_data')
def fixture_habra_data():
    yield {
        'repl_text': 'ЛУЧШИЕ™',
        'mail': 'volaxar@mail.ru',
        'password': 'ouwR@0S%OGaLEOkk5$3r#lO$!Q9D',
        'h_title': 'Лучшие публикации за сутки / Хабрахабр',
        't_title': 'Центр авторизации — TM ID',
        'file_loaded': 'Файл загружен. Загрузить другой?',
        'settings_ok': 'Новые настройки успешно сохранились'
    }
