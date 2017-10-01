import time

from bs4 import Comment

from tests.fixtures.fixtures import *


@pytest.mark.usefixtures('server')
def test_proxy_connect(socket):
    socket.connect((PROXY_HOST, PROXY_PORT))
    assert socket


class TestReplaceTm:
    @pytest.mark.parametrize(
        'tag_id, expected',
        [
            ('replaced_digits', '123456™'),
            ('replaced_letters', 'abcdef™'),
            ('replaced_alphanumeric', '1abcd6™'),
            ('replaced_in_quotes', '"123456™"')
        ],
        ids=[
            'digits',
            'letters',
            'alphanumeric',
            'in_quotes'
        ]
    )
    def test_replaced_single(self, replace_tm, tag_id, expected):
        content = replace_tm.find(id=tag_id).text.strip()
        assert content == expected

    @pytest.mark.parametrize(
        'tag_id, expected',
        [
            ('replaced_one', ('12345', '123456™', '1234567')),
            ('replaced_all', ('123456™', '123456™', '123456™'))
        ],
        ids=[
            'one',
            'all'
        ]
    )
    def test_replaced_several(self, replace_tm, tag_id, expected):
        content = replace_tm.find(id=tag_id).text.strip()
        content = content.split(' ')

        for i in range(3):
            assert content[i] == expected[i]

    @pytest.mark.parametrize(
        'tag_id, expected',
        [
            ('not_replaced_in_quotes', '"1234"'),
            ('not_replaced_code', '123456'),
            ('not_replaced_script', 'alert("123456");'),
            ('not_replaced_svg', '123456'),
            ('not_replaced_option', '123456'),
            ('not_replaced_outside', '123456')
        ],
        ids=[
            'in_quotes',
            'code',
            'script',
            'svg',
            'option',
            'outside'
        ]
    )
    def test_not_replaced_single(self, replace_tm, tag_id, expected):
        content = replace_tm.find(id=tag_id).text.strip()
        assert content == expected

    def test_not_replaced_comment(self, replace_tm):
        content = replace_tm.find(
            string=lambda tag: isinstance(tag, Comment)).strip()
        assert content == 'not replaced comment 123456'


class TestGetFreePort:
    def test_ok(self, processor):
        port = processor.get_free_port()
        assert 0 < port < 65536

    def test_fail(self, processor, socket):
        port = processor.get_free_port()
        time.sleep(0.1)
        socket.bind((PROXY_HOST, port))
        fail_port = processor.get_free_port(port)
        assert not fail_port


class TestGetLink:
    def test_host(self, processor, get_links):
        expecteds = (BASE_HOST, BASE_HOST, PROXY_HOST, PROXY_HOST)

        for i, link in enumerate(get_links):
            host = processor.get_link_host(link)
            assert host == expecteds[i]

        assert not processor.get_link_host(BASE_HOST)

    def test_port(self, processor, get_links):
        for i, link in enumerate(get_links[:2]):
            port = processor.get_link_port(link)
            assert not port

        for i, link in enumerate(get_links[2:]):
            port = processor.get_link_port(link)
            assert port == PROXY_PORT


class TestMakeLink:
    def test_make_link(self, processor):
        host = 'example.com'
        port = processor.make_link(host)
        assert port in processor.direct_link
        assert host == processor.direct_link[port]
        assert port == processor.reverse_link[host]


class TestChangeLink:
    def test_direct(self, processor, change_links):
        link_ok = processor.change_direct_link(change_links['direct_ok'])
        link_fail = processor.change_direct_link(change_links['direct_fail'])
        assert link_ok == change_links['reverse_ok']
        assert link_fail == change_links['direct_fail']

    def test_reverse(self, processor, change_links):
        link_ok = processor.change_reverse_link(change_links['reverse_ok'])
        assert link_ok == change_links['direct_ok']
        time.sleep(0.1)
        link_new = processor.change_reverse_link(change_links['reverse_new'])
        host = processor.get_link_host(link_new)
        port = processor.get_link_port(link_new)
        assert host == PROXY_HOST
        assert 0 < port < 65536


class TestCorrectErrors:
    @pytest.mark.parametrize(
        'url, content, expected',
        [
            ('/',
             '&plus;&plus;',
             '++'),
            ('/feedback/',
             '<select><option  value="1"/>Общие вопросы</option></select>',
             '<select><option  value="1">Общие вопросы</option></select>'
             ),
            ('/ppg/sandbox/',
             '<p>Text</strong>',
             '<p>Text</p>'
             ),
            ('/company/',
             '</li></div></ul>',
             '</li></ul></div>'
             ),
            ('/info/agreement/',
             '</a>.</p>',
             '</a>.'
             )
        ],
        ids=[
            'plus',
            'self-closing_option',
            'strong_instead_p',
            'confused_ul_div',
            'excess_p'
        ]
    )
    def test_corrections(self, processor, url, content, expected):
        correct = processor.correct_errors(url, content)
        assert correct == expected
