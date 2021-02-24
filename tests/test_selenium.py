from random import choices
from string import ascii_lowercase
from subprocess import check_output
from time import sleep

import pytest
import yaml
from selenium import webdriver
from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait


@pytest.fixture()
def driver(request):
    status = yaml.load(check_output(['juju', 'status', '--format=yaml']))
    endpoint = status['applications']['jupyter-ui']['address']
    url = f'http://{endpoint}.xip.io:5000/jupyter/'
    options = Options()
    options.add_argument("--headless")

    with webdriver.Firefox(options=options) as driver:
        wait = WebDriverWait(driver, 180, 1, (JavascriptException, StopIteration))
        # Go to URL and log in
        for _ in range(60):
            try:
                driver.get(url)
                break
            except WebDriverException:
                sleep(5)
        else:
            driver.get(url)

        yield driver, wait, url

        driver.get_screenshot_as_file(f'/tmp/selenium-{request.node.name}.png')


def test_notebook(driver):
    driver, wait, url = driver

    notebook_name = 'ci-test-' + ''.join(choices(ascii_lowercase, k=10))

    # Click "New Server" button
    driver.find_element_by_id("add-nb").click()
    wait.until(url_to_be(url + 'new'))

    # Enter server name
    name_input = driver.find_element_by_id('mat-input-0')
    name_input.send_keys(notebook_name)
    name_input.click()

    driver.find_element_by_css_selector('button[type="submit"]').click()
    wait.until(url_to_be(url))

    # We're waiting for a row to show up that represents our notebook and also
    # has a green checkmark circle on the left, which means the notebook has finished
    # spinning up. If we grab just the plain text of each row, the green checkmark circle
    # is represented as `check_circle`.

    # row = wait.until(
    #     lambda d: next(
    #         row
    #         for row in d.find_elements_by_css_selector('.mat-row')
    #         if f'check_circle\n{notebook_name}' in row.text
    #     )
    # )
    row = wait.until(
        lambda d: next(
            row for row in d.find_elements_by_css_selector('.mat-row') if notebook_name in row.text
        )
    )
    # Delete notebook
    row.find_element_by_css_selector('button:last-child').click()
    driver.find_element_by_css_selector('.yes').click()
    row = wait.until_not(
        lambda d: next(
            row
            for row in d.find_elements_by_css_selector('.mat-row')
            if f'check_circle\n{notebook_name}' in row.text
        )
    )
