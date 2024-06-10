import mysql.connector
from selenium import webdriver
from selenium.webdriver.common.by import By
import re
import logging
import time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

TRAVIAN_DATABASE_NAME = "travian"

BUILDINGS_EFFECT_TABLE_NAME = "buildings_effect"
BUILDINGS_EFFECT_COLUMNS = ["name", "effect"]
BUILDINGS_EFFECT_COLUMNS_TYPES = ["VARCHAR(30) PRIMARY KEY", "VARCHAR(30)"]
BUILDINGS_EFFECT_ADDITIONAL_LINES = ""

BUILDINGS_REQUIREMENTS_TABLE_NAME = "buildings_requirements"
BUILDINGS_REQUIREMENTS_COLUMNS = ["name", "requirements", "levels"]
BUILDINGS_REQUIREMENTS_COLUMNS_TYPES = ["VARCHAR(30) PRIMARY KEY", "VARCHAR(100)", "VARCHAR(100)"]
BUILDINGS_REQUIREMENTS_ADDITIONAL_LINES = f"FOREIGN KEY (name) REFERENCES {BUILDINGS_EFFECT_TABLE_NAME}(name)"

BUILDINGS_LEVEL_INFO_TABLE_NAME = "buildings_level_info"
BUILDINGS_LEVEL_INFO_COLUMNS = ["name", "level", "lumber", "clay", "iron", "crop", "total_cost", "upkeep",
                                "culture_points", "time", "effect_value"]
BUILDINGS_LEVEL_INFO_COLUMNS_TYPES = ["VARCHAR(30) NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL",
                                      "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL",
                                      "VARCHAR(20) NOT NULL", "VARCHAR(20)"]
BUILDINGS_LEVEL_INFO_ADDITIONAL_LINES = ("PRIMARY KEY (name, level),\nFOREIGN KEY (name) REFERENCES"
                                         f" {BUILDINGS_EFFECT_TABLE_NAME}(name)")

TROOPS_STATS_TABLE_NAME = "troops_stats"
TROOPS_STATS_COLUMNS = ["name", "attack", "infantry_defence", "cavalry_defense", "speed", "capacity"]
TROOPS_STATS_COLUMNS_TYPES = ["VARCHAR(30) PRIMARY KEY", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL",
                              "INT NOT NULL"]
TROOPS_STATS_ADDITIONAL_LINES = ""

TROOPS_PRICES_TABLE_NAME = "troops_prices"
TROOPS_PRICES_COLUMNS = ["name", "lumber", "clay", "iron", "crop", "total_cost", "upkeep", "time"]
TROOPS_PRICES_COLUMNS_TYPES = ["VARCHAR(30) PRIMARY KEY", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL",
                               "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "VARCHAR(20) NOT NULL"]
TROOPS_PRICES_ADDITIONAL_LINES = f"FOREIGN KEY (name) REFERENCES {TROOPS_STATS_TABLE_NAME}(name)"


def setup_database(cursor):
    if not database_exists(cursor, TRAVIAN_DATABASE_NAME):
        logger.info("Creating travian database")
        cursor.execute(f"CREATE DATABASE {TRAVIAN_DATABASE_NAME}")

    logger.info("Travian database present")

    if not table_exists(cursor, TRAVIAN_DATABASE_NAME, BUILDINGS_EFFECT_TABLE_NAME):
        create_table(cursor, BUILDINGS_EFFECT_TABLE_NAME, BUILDINGS_EFFECT_COLUMNS,
                     BUILDINGS_REQUIREMENTS_COLUMNS_TYPES, BUILDINGS_EFFECT_ADDITIONAL_LINES)

    if not table_exists(cursor, TRAVIAN_DATABASE_NAME, BUILDINGS_REQUIREMENTS_TABLE_NAME):
        create_table(cursor, BUILDINGS_REQUIREMENTS_TABLE_NAME, BUILDINGS_REQUIREMENTS_COLUMNS,
                     BUILDINGS_REQUIREMENTS_COLUMNS_TYPES, BUILDINGS_REQUIREMENTS_ADDITIONAL_LINES)

    if not table_exists(cursor, TRAVIAN_DATABASE_NAME, BUILDINGS_LEVEL_INFO_TABLE_NAME):
        create_table(cursor, BUILDINGS_LEVEL_INFO_TABLE_NAME, BUILDINGS_LEVEL_INFO_COLUMNS,
                     BUILDINGS_LEVEL_INFO_COLUMNS_TYPES, BUILDINGS_LEVEL_INFO_ADDITIONAL_LINES)

    if not table_exists(cursor, TRAVIAN_DATABASE_NAME, TROOPS_STATS_TABLE_NAME):
        create_table(cursor, TROOPS_STATS_TABLE_NAME, TROOPS_STATS_COLUMNS,
                     TROOPS_STATS_COLUMNS_TYPES, TROOPS_STATS_ADDITIONAL_LINES)

    if not table_exists(cursor, TRAVIAN_DATABASE_NAME, TROOPS_PRICES_TABLE_NAME):
        create_table(cursor, TROOPS_PRICES_TABLE_NAME, TROOPS_PRICES_COLUMNS,
                     TROOPS_PRICES_COLUMNS_TYPES, TROOPS_PRICES_ADDITIONAL_LINES)

    logger.info("All tables present")

    if not table_has_columns(cursor, TRAVIAN_DATABASE_NAME, BUILDINGS_REQUIREMENTS_TABLE_NAME,
                             BUILDINGS_REQUIREMENTS_COLUMNS):
        logger.info(f"Table {BUILDINGS_REQUIREMENTS_TABLE_NAME} has incorrect columns")

        cursor.execute(f"DROP TABLE {BUILDINGS_REQUIREMENTS_TABLE_NAME}")

        create_table(cursor, BUILDINGS_REQUIREMENTS_TABLE_NAME, BUILDINGS_REQUIREMENTS_COLUMNS,
                     BUILDINGS_REQUIREMENTS_COLUMNS_TYPES, BUILDINGS_REQUIREMENTS_ADDITIONAL_LINES)

    if not table_has_columns(cursor, TRAVIAN_DATABASE_NAME, BUILDINGS_LEVEL_INFO_TABLE_NAME,
                             BUILDINGS_LEVEL_INFO_COLUMNS):
        logger.info(f"Table {BUILDINGS_LEVEL_INFO_TABLE_NAME} has incorrect columns")

        cursor.execute(f"DROP TABLE {BUILDINGS_LEVEL_INFO_TABLE_NAME}")

        create_table(cursor, BUILDINGS_LEVEL_INFO_TABLE_NAME, BUILDINGS_LEVEL_INFO_COLUMNS,
                     BUILDINGS_LEVEL_INFO_COLUMNS_TYPES, BUILDINGS_LEVEL_INFO_ADDITIONAL_LINES)

    if not table_has_columns(cursor, TRAVIAN_DATABASE_NAME, BUILDINGS_EFFECT_TABLE_NAME, BUILDINGS_EFFECT_COLUMNS):
        logger.info(f"Table {BUILDINGS_EFFECT_TABLE_NAME} has incorrect columns")

        cursor.execute(f"DROP TABLE {BUILDINGS_REQUIREMENTS_TABLE_NAME}")
        cursor.execute(f"DROP TABLE {BUILDINGS_LEVEL_INFO_TABLE_NAME}")
        cursor.execute(f"DROP TABLE {BUILDINGS_EFFECT_TABLE_NAME}")

        create_table(cursor, BUILDINGS_REQUIREMENTS_TABLE_NAME, BUILDINGS_REQUIREMENTS_COLUMNS,
                     BUILDINGS_REQUIREMENTS_COLUMNS_TYPES, BUILDINGS_REQUIREMENTS_ADDITIONAL_LINES)
        create_table(cursor, BUILDINGS_LEVEL_INFO_TABLE_NAME, BUILDINGS_LEVEL_INFO_COLUMNS,
                     BUILDINGS_LEVEL_INFO_COLUMNS_TYPES, BUILDINGS_LEVEL_INFO_ADDITIONAL_LINES)
        create_table(cursor, BUILDINGS_EFFECT_TABLE_NAME, BUILDINGS_EFFECT_COLUMNS,
                     BUILDINGS_REQUIREMENTS_COLUMNS_TYPES, BUILDINGS_EFFECT_ADDITIONAL_LINES)

    if not table_has_columns(cursor, TRAVIAN_DATABASE_NAME, TROOPS_PRICES_TABLE_NAME, TROOPS_PRICES_COLUMNS):
        logger.info(f"Table {TROOPS_PRICES_TABLE_NAME} has incorrect columns")

        cursor.execute(f"DROP TABLE {TROOPS_PRICES_TABLE_NAME}")

        create_table(cursor, TROOPS_PRICES_TABLE_NAME, TROOPS_PRICES_COLUMNS,
                     TROOPS_PRICES_COLUMNS_TYPES, TROOPS_PRICES_ADDITIONAL_LINES)

    if not table_has_columns(cursor, TRAVIAN_DATABASE_NAME, TROOPS_STATS_TABLE_NAME, TROOPS_STATS_COLUMNS):
        logger.info(f"Table {TROOPS_STATS_TABLE_NAME} has incorrect columns")

        cursor.execute(f"DROP TABLE {TROOPS_PRICES_TABLE_NAME}")
        cursor.execute(f"DROP TABLE {TROOPS_STATS_TABLE_NAME}")

        create_table(cursor, TROOPS_PRICES_TABLE_NAME, TROOPS_PRICES_COLUMNS,
                     TROOPS_PRICES_COLUMNS_TYPES, TROOPS_PRICES_ADDITIONAL_LINES)
        create_table(cursor, TROOPS_STATS_TABLE_NAME, TROOPS_STATS_COLUMNS, TROOPS_STATS_COLUMNS_TYPES,
                     TROOPS_STATS_ADDITIONAL_LINES)

    logger.info("All tables with correct columns present")


def get_database_credentials():
    with open("db_credentials.txt", "r") as file:
        return file.readline()[:-1], file.readline()


def table_has_columns(cursor, database, table, columns):
    cursor.execute(f"USE {database}")
    query = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    """

    values = (database, table)

    cursor.execute(query, values)
    table_columns = cursor.fetchall()
    return set(map(lambda element: (element,), columns)) == set(table_columns)


def table_exists(cursor, database, table):
    cursor.execute(f"USE {database}")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    return (table,) in tables


def database_exists(cursor, database_name):
    cursor.execute("SHOW DATABASES")
    databases = cursor.fetchall()
    return (database_name,) in databases


def create_table(cursor, table_name, columns, column_types, additional_lines):
    logger.info(f"Creating {table_name} database")
    query_beginning = f"CREATE TABLE {table_name} ("

    query_end = ")"

    query = query_beginning
    for i in range(len(columns)):
        query += f"\n {columns[i]} {column_types[i]}"
        if not i == len(columns) - 1:
            query += ","

    if additional_lines:
        query += ","
        query += additional_lines
    query += query_end

    cursor.execute(query)


def get_travian_buildings_data():
    driver = webdriver.Firefox()
    driver.get('http://travian.kirilloid.ru/build.php#mb=1&s=1.45')

    buildings_requirements = []
    buildings_effect = []
    buildings_level_info = []

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
        requirements = (str(list(map(lambda req: req.text, requirements_div.find_elements(By.TAG_NAME, 'a'))))
                        .replace('"', "'"))

        buildings_requirements.append([name, requirements, levels])

        effect_element = driver.find_element(By.XPATH, '//table[@id="data"]/thead/tr/td[12]')
        effect = effect_element.text
        buildings_effect.append([name, effect])

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

            buildings_level_info.append(row_values)

        close_button = driver.find_element(By.ID, 'data_holder-close')
        close_button.click()

    driver.quit()
    logger.info("Driver has been closed")
    return buildings_effect, buildings_requirements, buildings_level_info


def get_travian_troops_data():
    driver = webdriver.Firefox()
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


def insert_into(cursor, table, columns, values):
    cols = "("
    for col in columns:
        cols += col + ","
    cols = cols[:-1] + ")"

    vals = "("
    for val in values:
        vals += '"' + val + '"' + ","
    vals = vals[:-1] + ")"

    query = f"INSERT INTO {table} {cols} VALUES {vals}"
    logger.info(query)
    cursor.execute(query)


def load_table(cursor, table_name, table_columns, entries):
    logger.info(f"Loading {table_name} table")
    for entry in entries:
        insert_into(cursor, table_name, table_columns, entry)


def load_database():
    start_time = time.time()

    db_user, db_password = get_database_credentials()
    logger.info(f"Database user: {db_user}")

    conn = mysql.connector.connect(
        host="localhost",
        user=db_user,
        password=db_password,
    )

    cursor = conn.cursor()

    logger.info("Database connection established")
    logger.info("Starting database setup")

    setup_database(cursor)

    logger.info("Fetching travian data")

#    effects, requirements, levels = get_travian_buildings_data()
    stats, prices = get_travian_troops_data()

    logger.info("Loading database tables")

#    load_table(cursor, BUILDINGS_EFFECT_TABLE_NAME, BUILDINGS_EFFECT_COLUMNS, effects)
#    load_table(cursor, BUILDINGS_REQUIREMENTS_TABLE_NAME, BUILDINGS_REQUIREMENTS_COLUMNS, requirements)
#    load_table(cursor, BUILDINGS_LEVEL_INFO_TABLE_NAME, BUILDINGS_LEVEL_INFO_COLUMNS, levels)

    load_table(cursor, TROOPS_STATS_TABLE_NAME, TROOPS_STATS_COLUMNS, stats)
    load_table(cursor, TROOPS_PRICES_TABLE_NAME, TROOPS_PRICES_COLUMNS, prices)

    conn.commit()

    cursor.close()
    conn.close()
    logger.info("Exiting function")

    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f'Total execution time: {execution_time:4f} seconds')


load_database()
