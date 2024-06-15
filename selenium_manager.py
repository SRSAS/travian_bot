from enum import Enum
import re

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver

from utils import retry, logger, log_execution_time
from database.db_utils import get_login_info

WAIT_TIME = 4

INTERNATIONAL_5 = 'International 5'
EUROPE_100 = 'Europe 100'

INTERNATIONAL_5_URL = 'https://ts5.x1.international.travian.com'
EUROPE_100_URL = 'https://ts100.x10.europe.travian.com'

canonical_server_names = {
    INTERNATIONAL_5: "INTERNATIONAL_5",
    EUROPE_100: "EUROPE_100"
}


# Page names
class PageNames(Enum):
    RESOURCES = 1
    BUILDINGS = 2
    MAP = 3
    STATISTICS = 4
    REPORTS = 5
    MESSAGES = 6
    HERO = 7
    FARM_LIST = 8


url_suffixes = {
    PageNames.RESOURCES: 'dorf1.php',
    PageNames.BUILDINGS: 'dorf2.php',
    PageNames.MAP: 'karte.php',
    PageNames.STATISTICS: 'statistics',
    PageNames.REPORTS: 'report',
    PageNames.MESSAGES: 'messages',
    PageNames.HERO: 'hero',
    PageNames.FARM_LIST: 'build.php?id=39&gid=16&tt=99',
}


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


def get_travian_buildings_data():
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    driver = webdriver.Firefox(options=options)
    driver.get('http://travian.kirilloid.ru/build.php#mb=1&s=1.45')

    requirements = []
    effect = []
    level_info = []

    buildings = driver.find_elements(By.CLASS_NAME, 'build_list__item')

    logger.info(f"Found {len(buildings)} buildings")
    building_count = 0
    for building in buildings:
        if building.get_attribute('style') == 'display: none;':
            continue

        name = building.text
        building.click()

        building_count += 1
        logger.info(f"Processing building number {building_count}: {name}")

        requirements_div = driver.find_element(By.ID, 'data_holder-req')

        levels = str(re.findall(r'\d+', requirements_div.text)).replace('"', "'")
        reqs = (str(list(map(lambda req: req.text, requirements_div.find_elements(By.TAG_NAME, 'a'))))
                .replace('"', "'"))

        requirements.append([name, reqs, levels])

        effect_element = driver.find_element(By.XPATH, '//table[@id="data"]/thead/tr/td[12]')
        ef = effect_element.text
        effect.append([name, ef])

        info_table = driver.find_elements(By.XPATH, '//table[@id="data"]/tbody/tr')
        for row in info_table:
            if get_value(row, 1) == '—':
                continue

            row_values = [name]

            for i in range(7):
                index = i + 1
                row_values.append(get_value(row, index))

            for i in range(10, 13):
                row_values.append(get_value(row, i))

            level_info.append(row_values)

        close_button = driver.find_element(By.ID, 'data_holder-close')
        close_button.click()

    driver.quit()
    logger.info("Driver has been closed")
    return effect, requirements, level_info


def get_travian_troops_data():
    options = webdriver.FirefoxOptions()
    options.add_argument('--headless')
    driver = webdriver.Firefox(options=options)
    driver.get('http://travian.kirilloid.ru/troops.php#s=1.45&tribe=1&s_lvl=1&t_lvl=1&unit=1')

    table = driver.find_element(By.ID, 'main').find_element(By.TAG_NAME, 'tbody').find_elements(By.TAG_NAME, 'tr')[2:]

    statistics = []
    prices = []

    logger.info(f"Found {len(table)} troops")
    count = 0
    for row in table:
        name = get_value(row, 2)

        count += 1
        logger.info(f"Processing troop number {count}: {name}")

        stats = [name]
        price = [name]

        for i in range(3, 15):
            value = get_value(row, i)
            if value == '—':
                value = '0'

            if i < 8:
                stats.append(value)
            else:
                price.append(value)

        statistics.append(stats)
        prices.append(price)

    driver.close()
    logger.info("Driver has been closed")
    return statistics, prices


def get_value(row, col):
    return row.find_element(By.XPATH, f'./td[{col}]').text


@retry
def get_farm_lists(village_wrapper):
    return village_wrapper.find_elements(By.XPATH, './div[contains(@class, "dropContainer")]/div')


@retry
def get_farm_list_village_name(village_wrapper):
    return village_wrapper.find_element(By.XPATH, './div[1]/div').text


@retry
def get_farms(farm_list):
    farm_list_rows = farm_list.find_elements(By.XPATH, './div[@class="slotsWrapper formV2"]/table/tbody/tr')
    return [row for row in farm_list_rows if (lambda element: element.get_attribute('class'))(row)]


@retry
def get_farm_list_name(farm_list):
    return farm_list.find_element(By.XPATH, './div[@class="farmListHeader"]'
                                            '/div[@class="farmListName"]/div[@class="name"]').text


@retry
def get_farm_link(farm):
    return farm.find_element(By.XPATH, './td[3]/a')


class SeleniumManager:
    servers = {
        EUROPE_100: EUROPE_100_URL,
        INTERNATIONAL_5: INTERNATIONAL_5_URL
    }

    def __init__(self):
        self.drivers = {
            EUROPE_100: None,
            INTERNATIONAL_5: None
        }
        self.waits = {
            EUROPE_100: None,
            INTERNATIONAL_5: None
        }
        self.is_logged_in = {
            EUROPE_100: False,
            INTERNATIONAL_5: False
        }

    @staticmethod
    def build_url(server, page):
        if server not in SeleniumManager.servers.keys():
            logger.error(f"Server {server} not valid")
            return None

        return SeleniumManager.servers[server] + '/' + url_suffixes[page]

    # PAGE NAVIGATION
    def login(self, server):
        logger.info(f"Logging into {server}")
        driver = self.get_driver(server)
        logger.debug("Driver acquired")

        if not driver:
            logger.error("Could not get driver")
            return

        username, password = get_login_info(canonical_server_names[server])
        logger.info(f"Logging into {username}, with password {password}")

        name_field = driver.find_element(By.NAME, 'name')
        password_field = driver.find_element(By.NAME, 'password')

        name_field.send_keys(username)
        password_field.send_keys(password)

        login_button = driver.find_element(By.XPATH, '//button[@value="Login"]')
        login_button.click()
        self.is_logged_in[server] = True

    def is_valid_server(self, server):
        return server in self.servers.keys()

    def get_driver(self, server):
        if not self.is_valid_server(server):
            logger.error(f"Server {server} not valid")
            return None

        if not self.drivers[server]:
            logger.info(f"Driver for {server} doesn't exist")
            logger.info("Creating new driver")
            driver = webdriver.Firefox()
            driver.get(SeleniumManager.servers[server])
            self.drivers[server] = driver
            return driver
        return self.drivers[server]

    def close_driver(self, server):
        if not self.is_valid_server(server):
            logger.error(f"Server {server} not valid")
            return None

        driver = self.drivers[server]
        if not driver:
            return
        driver.quit()
        self.drivers[server] = None

        wait = self.waits[server]
        if not wait:
            return
        self.waits[server] = None

    def get_logged_in_driver(self, server):
        driver = self.get_driver(server)
        if driver and not self.is_logged_in[server]:
            self.login(server)
        return driver

    def get_wait(self, server):
        if not self.is_valid_server(server):
            logger.error(f"Server {server} not valid")
            return None

        if self.waits[server]:
            return self.waits[server]

        driver = self.get_driver(server)
        wait = WebDriverWait(driver, WAIT_TIME)
        self.waits[server] = wait
        return wait

    def navigate_to(self, server, page):
        if not self.is_valid_server(server):
            logger.error(f"Server {server} not valid")
            return None

        url = self.build_url(server, page)
        driver = self.get_logged_in_driver(server)
        if not driver:
            return

        if driver.current_url != url:
            driver.get(url)

    # ELEMENTS FETCHING
    @retry
    def get_farm_list(self, server, index):
        self.navigate_to(server, PageNames.FARM_LIST)

        wait = self.get_wait(server)
        return wait.until(
            EC.presence_of_element_located((By.XPATH,
                                            '//div[@id="rallyPointFarmList"]/div[@class="villageWrapper "]'
                                            f'/div[@data-sortindex="{index}"]'
                                            '/div'))
        )

    def get_all_farm_lists_by_village(self, server):
        self.navigate_to(server, PageNames.FARM_LIST)
        wait = self.get_wait(server)

        farm_lists_by_village = {}
        villages = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, 'villageWrapper'))
        )

        def parse_village(village):
            village_name = get_farm_list_village_name(village)
            farm_lists = get_farm_lists(village)
            farms_by_name = {}

            def parse_farm_list(farm_list):
                farm_list_name = get_farm_list_name(farm_list)
                farms = get_farms(farm_list)
                farms_by_name[farm_list_name] = farms

            for f_l in farm_lists:
                parse_farm_list(f_l)
            farm_lists_by_village[village_name] = farms_by_name

        for v in villages:
            parse_village(v)

        return farm_lists_by_village

    @retry
    def get_building_slots(self, server):
        self.navigate_to(server, PageNames.BUILDINGS)
        wait = self.get_wait(server)

        village_content = wait.until(
            EC.presence_of_element_located((By.ID, 'villageContent'))
        )
        return village_content.find_elements(By.TAG_NAME, 'div')

    @retry
    def get_building_list(self, server):
        self.navigate_to(server, PageNames.BUILDINGS)
        wait = self.get_wait(server)

        return wait.until(
            EC.presence_of_all_elements_located((By.ID, 'buildingList'))
        )

    """ Must be called after navigating to building """
    @retry
    def get_building_upgrade_button(self, wait):
        return wait.until(
            EC.presence_of_element_located(
                (By.XPATH, f"//div[contains(@class, 'upgradeButtonsContainer')]/div[1]/button"))
        )

    # FARM OPERATIONS
    @retry
    def open_farm_link_in_new_tab(self, server, farm_link):
        driver = self.get_logged_in_driver(server)
        wait = self.get_wait(server)

        action = webdriver.ActionChains(driver)
        action.key_down(Keys.CONTROL).click(farm_link).key_up(Keys.CONTROL).perform()
        wait.until(EC.number_of_windows_to_be(2))

    """ Must be called after navigating to farm location """
    @retry
    def farm_is_undefended(self, server):
        wait = self.get_wait(server)

        troops = wait.until(
            EC.presence_of_element_located((By.XPATH, '//table[@id="troop_info"]/tbody/tr[1]/td'))
        )
        return troops.text == 'none'

    def select_farm_if_undefended(self, server, farm):
        driver = self.get_logged_in_driver(server)

        scroll_into_view(driver, farm)
        original_style = highlight(farm, driver)

        farm_link = get_farm_link(farm)
        self.open_farm_link_in_new_tab(server, farm_link)
        original_window_handle = switch_window(driver)

        undefended = self.farm_is_undefended(server)

        driver.close()
        driver.switch_to.window(original_window_handle)

        if undefended:
            checkbox = farm.find_element(By.XPATH, './td[1]/label/input')
            checkbox.click()

        unhighlight(farm, original_style, driver)

    def select_undefended_farms(self, server, farms):
        for farm in farms:
            self.select_farm_if_undefended(server, farm)

    @log_execution_time
    def select_undefended_oases_farms(self, server):
        farm_lists_by_village = self.get_all_farm_lists_by_village(server)

        for _, farms_by_name in farm_lists_by_village.items():
            for name, farms in farms_by_name.items():
                if "oases" in name:
                    self.select_undefended_farms(server, farms)
