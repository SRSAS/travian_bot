from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

TRAVIAN_URL = 'https://ts4.x1.international.travian.com'
NUMBER_OF_FARMLISTS = 4

def get_travian_login_info():
    with open('travian_login_info.txt', 'r') as login_file:
        return login_file.readline()[:-1], login_file.readline()[:-1]

def login(driver):
    username, password = get_travian_login_info()

    name_field = driver.find_element(By.NAME, 'name')
    password_field = driver.find_element(By.NAME, 'password')
    
    name_field.send_keys(username)
    password_field.send_keys(password)

    login_button = driver.find_element(By.XPATH, '//button[@value="Login"]')
    login_button.click()

def navigate_to_farmlists(driver):
    buildings_button = driver.find_element(By.XPATH, '//a[@class="village buildingView "]')
    buildings_button.click()

    rally_point_button = driver.find_element(By.XPATH, '//div[@data-name="Rally Point"]/a')
    rally_point_button.click()

    farm_lists_button = driver.find_element(By.XPATH, '//div[@class="content  favor  favorKey99"]/a')
    farm_lists_button.click()

def open_farmlink_in_new_tab(driver, farm_link, wait):
    action = webdriver.ActionChains(driver)
    action.key_down(Keys.CONTROL).click(farm_link).key_up(Keys.CONTROL).perform()
    wait.until(EC.number_of_windows_to_be(2))

def scroll_into_view(driver, element):
    driver.execute_script("arguments[0].scrollIntoView(true);", element)

def switch_to_second_window(driver):
    original_window_handle = driver.current_window_handle
    for window_handle in driver.window_handles:
        if window_handle != original_window_handle:
            driver.switch_to.window(window_handle)
            break
    return original_window_handle

def highlight(element, driver, duration=2):
    original_style = element.get_attribute('style')
    new_style = "background: yellow; border: 2px solid red;"
    driver.execute_script(f"arguments[0].setAttribute('style', '{new_style}')", element)
    time.sleep(duration)
    driver.execute_script(f"arguments[0].setAttribute('style', '{original_style}')", element)


def main():
    driver = webdriver.Firefox()
    driver.get(TRAVIAN_URL)

    login(driver)
    navigate_to_farmlists(driver)

    wait = WebDriverWait(driver, 10)

    for i in range(NUMBER_OF_FARMLISTS):
        index = i + 1
        farmlist = wait.until(
                EC.presence_of_element_located((By.XPATH, f'//div[@id="rallyPointFarmList"]/div[@class="villageWrapper "]/div[@data-sortindex="{index}"]/div/div[@class="slotsWrapper formV2"]/table/tbody'))
                )
        farms = farmlist.find_elements(By.TAG_NAME, 'tr')
        print(len(farms))
        selected_farms = []
        num = 0
        for farm in farms:
            scroll_into_view(driver, farm)
            num += 1
            highlight(farm, driver)
            print(f"Row {num}: Class = " + str(farm.get_attribute('class')))
            if not farm.get_attribute('class'):
                continue

            farm_link = farm.find_element(By.XPATH, './td[3]/a')
            open_farmlink_in_new_tab(driver, farm_link, wait)
            original_window_handle = switch_to_second_window(driver)

            troops = wait.until(
                    EC.presence_of_element_located((By.XPATH, '//table[@id="troop_info"]/tbody/tr[1]/td'))
                    )
            highlight(troops, driver)

            troops_text = troops.text

            driver.close()
            driver.switch_to.window(original_window_handle)
            
            if troops_text == "none":
                checkbox = farm.find_element(By.XPATH, './td[1]/label/input')
                checkbox.click()


    while True:
        if input() == 'q':
            break
    driver.close()

if __name__ == "__main__":
    main()
