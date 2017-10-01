import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

import multipart
import requests
from bs4 import BeautifulSoup, NavigableString, Comment

from settings import *


class ProxyServer:
    def __init__(self, host, port):
        self.proxy = HTTPServer((host, port), ProxyProcessor)
        self.thread = threading.Thread(target=self.proxy.serve_forever)

    def start(self, is_daemon=False):
        self.thread.daemon = is_daemon
        self.thread.start()

    def stop(self):
        self.proxy.shutdown()


class ProxyProcessor(BaseHTTPRequestHandler):
    direct_link = {PROXY_PORT: BASE_HOST}
    reverse_link = {BASE_HOST: PROXY_PORT}

    def __init__(self, request, client_address, server):
        self._headers_buffer = []
        self.host = self.direct_link[server.server_port]

        if request:
            super().__init__(request, client_address, server)

    def __getattr__(self, item):
        if item in ['do_GET', 'do_POST']:
            return lambda: self.do_command(item)

    @staticmethod
    def get_free_port(port=0):
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            _socket.bind((PROXY_HOST, port))
        except Exception:
            return
        else:
            return _socket.getsockname()[1]
        finally:
            _socket.close()

    # Исправление ошибок парсинга и разметки  страниц
    @staticmethod
    def correct_errors(url, content):
        def in_url(pattern):
            if not isinstance(pattern, list):
                pattern = [pattern]

            return any(x in url for x in pattern)

        # &plus вместо +
        content = re.sub(r'&plus;', r'+', content)

        # Самозакрывающийся тег <option>
        if in_url(['/auth/settings/profile/', '/feedback/']):
            content = re.sub(r'(<option.*?)/>', r'\g<1>>', content)

        # Тег </strong> вместо </p>
        if in_url('/ppg/sandbox/'):
            content = re.sub(r'(<p>[^<]*)</strong>', r'\g<1></p>', content)

        # Перепутаны местами тэги </ul> и </div>
        if in_url('/company/'):
            content = re.sub(r'</li>(\s*)</div>(\s*)</ul>',
                             r'</li>\g<1></ul>\g<2></div>', content
                             )

        # Лишний тег </p>
        if in_url('/info/agreement/'):
            content = content.replace(r'</a>.</p>', r'</a>.')

        return content

    @staticmethod
    def get_link_host(link):
        re_host = re.match(r'https?://([^/:]+)', link)

        if re_host:
            return re_host.group(1)

    @staticmethod
    def get_link_port(link):
        re_port = re.match(r'https?://[^/:]+:(\d+)', link)

        if re_port:
            return int(re_port.group(1))

    def change_direct_link(self, link):
        port = self.get_link_port(link)

        if port and port in self.direct_link:
            host = self.direct_link[port]
            link = re.sub(r'https?://%s:%s' % (PROXY_HOST, port),
                          '%s://%s' % (BASE_PROTO, host), link
                          )

        return link

    def change_reverse_link(self, link):
        host = self.get_link_host(link)

        if host:
            if host in self.reverse_link:
                port = self.reverse_link[host]
            else:
                port = self.make_link(host)

            if port:
                link = re.sub(r'https?://%s' % host,
                              r'http://%s:%s' % (PROXY_HOST, port), link
                              )

        return link

    def make_link(self, host):
        port = self.get_free_port()

        if port:
            ProxyServer(PROXY_HOST, port).start(True)
            self.direct_link[port] = host
            self.reverse_link[host] = port
            return port

    def replace_tm_text(self, tag):
        if isinstance(tag, Comment) or tag.name in SKIP_TAGS:
            return

        if isinstance(tag, NavigableString):
            if tag.strip():
                tag.replace_with(TM_REGSUB.sub(r'\g<1>™', tag))
        else:
            for child in tag.children:
                self.replace_tm_text(child)

    def replace_content(self, response):
        if 'text/' in response.headers['Content-Type']:
            content = response.text

            if 'window.location.href' in content:
                url = re.search(r'window.location.href\s?=\s?\'(.+?)\'',
                                content
                                )

                if url:
                    content = content.replace(url.group(1),
                                              self.change_reverse_link(
                                                  url.group(1))
                                              )

            content = re.sub('https?://%s' % self.host, '', content)

            if self.host == BASE_HOST:
                content = self.correct_errors(response.url, content)
                soup = BeautifulSoup(content, 'html.parser')
                layout_tags = soup.find_all('div', 'layout')

                for layout_tag in layout_tags:
                    self.replace_tm_text(layout_tag)

                content = soup.encode(formatter='html')
        else:
            content = response.content

        if isinstance(content, str):
            content = content.encode()

        return content

    def send_headers(self, response):
        self.send_response_only(response.status_code, response.reason)

        for key, val in response.headers.items():
            if key in DENY_RESPONSE:
                continue

            if key == 'Location':
                val = self.change_reverse_link(val)

            self.send_header(key, val)

        if 'Set-Cookie' in response.headers:
            splited_cookie = re.split(r'(?<!%s), ' % '|'.join(self.weekdayname),
                                      response.headers['Set-Cookie']
                                      )

            for cookie in splited_cookie:
                cookie = cookie.replace(self.host, PROXY_HOST)
                self.send_header('Set-Cookie', cookie)

    def send_error_page(self):
        self._headers_buffer = []
        self.send_response_only(500, 'Internal Server Error')
        self.end_headers()
        self.wfile.write(
            '<h1 align="center">500 Internal Server Error</h1>'.encode()
        )

    def do_command(self, command):
        headers = dict(self.headers)
        del headers['Host']

        if 'Referer' in headers:
            headers['Referer'] = self.change_direct_link(headers['Referer'])

        response = None

        try:
            if command == 'do_GET':
                response = requests.get(
                    '%s://%s%s' % (BASE_PROTO, self.host, self.path),
                    headers=headers,
                    allow_redirects=False
                )
            elif command == 'do_POST':
                files = {}
                data = {}
                length = int(headers.get('Content-Length', 0))

                if '/x-www-form-urlencoded' in headers['Content-Type']:
                    data = self.rfile.read(length)
                    data = parse_qs(data.decode(), keep_blank_values=True)
                elif 'multipart/form-data' in headers['Content-Type']:
                    environ = {'wsgi.input': self.rfile,
                               'CONTENT_LENGTH': length,
                               'CONTENT_TYPE': headers['Content-Type'],
                               'REQUEST_METHOD': 'POST'
                               }
                    data, parse_files = multipart.parse_form_data(environ)

                    for key, val in parse_files.items():
                        files[key] = (val.filename, val.file, val.content_type)

                    del headers['Content-Type']

                response = requests.post(
                    '%s://%s%s' % (BASE_PROTO, self.host, self.path),
                    headers=headers,
                    files=files,
                    data=data,
                    allow_redirects=False
                )
        except requests.RequestException as e:
            print(e)
            self.send_error_page()
            return

        if response:
            content = self.replace_content(response)
            self.send_headers(response)
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error_page()


if __name__ == '__main__':
    ProxyServer(PROXY_HOST, PROXY_PORT).start()
