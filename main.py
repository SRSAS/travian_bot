from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import time
import logging
from functools import wraps
import threading

TRAVIAN_EUROPE_URL = 'https://ts4.x1.europe.travian.com'
TRAVIAN_INTERNATIONAL_URL = 'https://ts4.x1.international.travian.com'
NUMBER_OF_FARM_LISTS = 2

# LOGGING
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


# WRAPPERS
def log_execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logger.info(f'Function {func.__name__} executed in {execution_time:.4f} seconds')
        return result
    return wrapper


def retry(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.info(f'Function {func.__name__} failed, with error {e}. Retrying...')
    return wrapper


def run_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
    return wrapper


# SELENIUM UTILS
def switch_window(driver):
    original_window_handle = driver.current_window_handle
    for window_handle in driver.window_handles:
        if window_handle != original_window_handle:
            driver.switch_to.window(window_handle)
            break
    return original_window_handle


def highlight(element, driver):
    original_style = element.get_attribute('style')
    new_style = "background: yellow; border: 2px solid red;"
    driver.execute_script(f"arguments[0].setAttribute('style', '{new_style}')", element)
    return original_style


def unhighlight(element, original_style, driver):
    driver.execute_script(f"arguments[0].setAttribute('style', '{original_style}')", element)


def scroll_into_view(driver, element):
    driver.execute_script("arguments[0].scrollIntoView(true);", element)


# FILE READING
def get_travian_login_info():
    with open('travian_login_info.txt', 'r') as login_file:
        return login_file.readline()[:-1], login_file.readline()[:-1]


# PAGE NAVIGATION
def login(driver, username, password):
    name_field = driver.find_element(By.NAME, 'name')
    password_field = driver.find_element(By.NAME, 'password')
    
    name_field.send_keys(username)
    password_field.send_keys(password)

    login_button = driver.find_element(By.XPATH, '//button[@value="Login"]')
    login_button.click()


def navigate_to_farm_lists(driver):
    buildings_button = driver.find_element(By.XPATH, '//a[@class="village buildingView "]')
    buildings_button.click()

    rally_point_button = driver.find_element(By.XPATH, '//div[@data-name="Rally Point"]/a')
    rally_point_button.click()

    farm_lists_button = driver.find_element(By.XPATH, '//div[@class="content  favor  favorKey99"]/a')
    farm_lists_button.click()


# ELEMENTS FETCHING
@retry
def get_farm_list(index, wait):
    return wait.until(
        EC.presence_of_element_located((By.XPATH,
                                        '//div[@id="rallyPointFarmList"]/div[@class="villageWrapper "]'
                                        f'/div[@data-sortindex="{index}"]'
                                        '/div'))
    )


@retry
def get_farms(farm_list):
    farm_list_rows = farm_list.find_elements(By.XPATH, './div[@class="slotsWrapper formV2"]/table/tbody/tr')
    return [row for row in farm_list_rows if (lambda element: element.get_attribute('class'))(row)]


@retry
def get_farm_list_name(farm_list):
    return farm_list.find_elements(By.XPATH, './div[@class="farmListHeader]'
                                             '/div[@class="farmListName"]/div[@class="name"]').text


@retry
def get_farm_link(farm):
    return farm.find_element(By.XPATH, './td[3]/a')


# FARM OPERATIONS
@retry
def open_farm_link_in_new_tab(driver, farm_link, wait):
    action = webdriver.ActionChains(driver)
    action.key_down(Keys.CONTROL).click(farm_link).key_up(Keys.CONTROL).perform()
    wait.until(EC.number_of_windows_to_be(2))


@retry
def farm_is_undefended(wait):
    troops = wait.until(
        EC.presence_of_element_located((By.XPATH, '//table[@id="troop_info"]/tbody/tr[1]/td'))
    )
    return troops.text == 'none'


def select_farm_if_undefended(farm, wait, driver):
    scroll_into_view(driver, farm)
    original_style = highlight(farm, driver)

    farm_link = get_farm_link(farm)
    open_farm_link_in_new_tab(driver, farm_link, wait)
    original_window_handle = switch_window(driver)

    undefended = farm_is_undefended(wait)

    driver.close()
    driver.switch_to.window(original_window_handle)

    if undefended:
        checkbox = farm.find_element(By.XPATH, './td[1]/label/input')
        checkbox.click()

    unhighlight(farm, original_style, driver)


def select_undefended_farms(farms, wait, driver):
    for farm in farms:
        select_farm_if_undefended(farm, wait, driver)


# COMMANDS
def select_farms_command(server_url, wait, driver):
    @log_execution_time
    def select_farms():
        driver.get(server_url)

        username, password = get_travian_login_info()
        password += '"'

        login(driver, username, password)
        navigate_to_farm_lists(driver)

        for i in range(NUMBER_OF_FARM_LISTS):
            farm_list = get_farm_list(i + 1, wait)
            farms = get_farms(farm_list)
            select_undefended_farms(farms, wait, driver)

        return True
    return select_farms


def double_command(driver_one, wait_one, driver_two, wait_two):
    @log_execution_time
    def double_server_select_farm_command():
        thread_one = threading.Thread(target=select_farms_command(TRAVIAN_EUROPE_URL, wait_one, driver_one))
        thread_two = threading.Thread(target=select_farms_command(TRAVIAN_INTERNATIONAL_URL, wait_two, driver_two))

        thread_one.start()
        thread_two.start()

    return double_server_select_farm_command


def quit_app(driver):
    def close_windows_and_quit():
        driver.quit()
        return False
    return close_windows_and_quit


# UI
def print_usage(commands):
    print('Please introduce a valid command.')
    print('Available commands:')
    for command in commands.keys():
        print(f'\t{command}')


def wait_for_command(commands):
    while True:
        command = input()
        if command in commands:
            return commands[command]()
        else:
            print('Invalid command.')
            print_usage(commands)


def main():
    logger.info('hi')

    driver_one = webdriver.Firefox()
    wait_one = WebDriverWait(driver_one, 2)

    commands = {
        'europe': select_farms_command(TRAVIAN_EUROPE_URL, wait_one, driver_one),
        'international': select_farms_command(TRAVIAN_INTERNATIONAL_URL, wait_one, driver_one),
        'close window': driver_one.close,
        'quit': quit_app(driver_one),
    }

    print_usage(commands)
    while wait_for_command(commands):
        pass


if __name__ == "__main__":
    main()
