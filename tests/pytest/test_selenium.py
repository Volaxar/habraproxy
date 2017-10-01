import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

from tests.fixtures.fixtures import *


class TestSelenium:
    @pytest.mark.usefixtures('server')
    def test_replacements(self, driver, habra_data):
        link = driver.wait.until(
            ec.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.tabs-level_top > a[href*="/top/"]'))
        )
        assert link.text == habra_data['repl_text']
        assert BASE_HOST not in link.get_attribute('href')

    @pytest.mark.usefixtures('server')
    def test_login(self, driver, habra_data):
        login_bth = driver.wait.until(
            ec.element_to_be_clickable((By.ID, 'login')))
        url = driver.current_url
        login_bth.click()
        driver.wait.until(ec.url_changes(url))
        driver.wait.until(ec.title_is(habra_data['t_title']))
        assert PROXY_HOST in driver.current_url
        email_input = driver.wait.until(
            ec.element_to_be_clickable((By.NAME, 'email')))
        password_input = driver.wait.until(
            ec.element_to_be_clickable((By.NAME, 'password')))
        email_input.send_keys(habra_data['mail'])
        password_input.send_keys(habra_data['password'])
        go_bth = driver.wait.until(ec.element_to_be_clickable((By.NAME, 'go')))
        url = driver.current_url
        go_bth.submit()
        driver.wait.until(ec.url_changes(url))
        driver.wait.until(ec.title_is(habra_data['h_title']))
        assert PROXY_HOST in driver.current_url

    @pytest.mark.usefixtures('server')
    def test_profile_save(self, driver, habra_data):
        user_bth = driver.wait.until(
            ec.element_to_be_clickable(
                (By.CSS_SELECTOR, 'div.dropdown_user > button'))
        )
        user_bth.click()
        pattern = 'a.user-info ~ ul a[href*="/auth/settings/profile/"]'
        profile_link = driver.wait.until(
            ec.element_to_be_clickable((By.CSS_SELECTOR, pattern))
        )
        url = driver.current_url
        profile_link.click()
        driver.wait.until(ec.url_changes(url))
        iframe = driver.wait.until(ec.presence_of_element_located(
            (By.CSS_SELECTOR, 'iframe.iframe_uploader')))
        driver.switch_to.frame(iframe)
        file_input = driver.wait.until(
            ec.element_to_be_clickable((By.ID, 'input_file')))
        file_input.send_keys(os.path.join(os.getcwd(), 'fixtures', 'image.jpg'))
        driver.wait.until(
            ec.presence_of_element_located((By.CSS_SELECTOR, 'div#result a')))
        result = driver.find_element_by_id('result')
        assert result.text == habra_data['file_loaded']
        driver.switch_to.default_content()
        pattern = 'form#profile_settings_form input[type="submit"]'
        submit_btn = driver.wait.until(
            ec.presence_of_element_located((By.CSS_SELECTOR, pattern))
        )
        submit_btn.submit()
        msg_ok = driver.wait.until(
            ec.presence_of_element_located(
                (By.CSS_SELECTOR, 'div#jGrowl div.jGrowl-message'))
        )
        assert msg_ok.text == habra_data['settings_ok']
