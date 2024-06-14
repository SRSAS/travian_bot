import mysql.connector
import time

from db_utils import *
from selenium_manager import get_travian_buildings_data, get_travian_troops_data

TRAVIAN_DATABASE_NAME = "travian"

buildings_effect = {
    "table_name": "buildings_effect",
    "columns": ["name", "effect"],
    "column_types": ["VARCHAR(30) PRIMARY KEY", "VARCHAR(30)"],
    "additional_lines": ""
}

buildings_requirements = {
    "table_name": "buildings_requirements",
    "columns": ["name", "requirements", "levels"],
    "column_types": ["VARCHAR(30) PRIMARY KEY", "VARCHAR(100)", "VARCHAR(100)"],
    "additional_lines": f"FOREIGN KEY (name) REFERENCES {buildings_effect['table_name']}(name)"
}

buildings_level_info = {
    "table_name": "buildings_level_info",
    "columns": ["name", "level", "lumber", "clay", "iron", "crop", "total_cost", "upkeep", "culture_points",
                "time", "effect_value"],
    "column_types": ["VARCHAR(30) NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL",
                     "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "VARCHAR(20) NOT NULL",
                     "VARCHAR(20)"],
    "additional_lines": f"PRIMARY KEY (name, level),\nFOREIGN KEY (name) REFERENCES {buildings_effect['table_name']}"
                        f"(name)"
}

troops_stats = {
    "table_name": "troops_stats",
    "columns": ["name", "attack", "infantry_defence", "cavalry_defense", "speed", "capacity"],
    "column_types": ["VARCHAR(30) PRIMARY KEY", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL",
                     "INT NOT NULL"],
    "additional_lines": ""
}

troops_prices = {
    "table_name": "troops_prices",
    "columns": ["name", "lumber", "clay", "iron", "crop", "total_cost", "upkeep", "time"],
    "column_types": ["VARCHAR(30) PRIMARY KEY", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL", "INT NOT NULL",
                     "INT NOT NULL", "INT NOT NULL", "VARCHAR(20) NOT NULL"],
    "additional_lines": f"FOREIGN KEY (name) REFERENCES {troops_stats['table_name']}(name)"
}


def setup_database(cursor):
    if not database_exists(cursor, TRAVIAN_DATABASE_NAME):
        logger.info("Creating travian database")
        cursor.execute(f"CREATE DATABASE {TRAVIAN_DATABASE_NAME}")

    logger.info("Travian database present")

    create_table_if_doesnt_exist(cursor, TRAVIAN_DATABASE_NAME, **buildings_effect)
    create_table_if_doesnt_exist(cursor, TRAVIAN_DATABASE_NAME, **buildings_requirements)
    create_table_if_doesnt_exist(cursor, TRAVIAN_DATABASE_NAME, **buildings_level_info)
    create_table_if_doesnt_exist(cursor, TRAVIAN_DATABASE_NAME, **troops_stats)
    create_table_if_doesnt_exist(cursor, TRAVIAN_DATABASE_NAME, **troops_prices)

    logger.info("All tables present")

    buildings_effect_precedences = {"precedences": [buildings_effect, buildings_requirements]}
    troops_stats_precedences = {"precedences": [troops_prices]}

    recreate_table_if_columns_dont_match(cursor, TRAVIAN_DATABASE_NAME, **buildings_requirements)
    recreate_table_if_columns_dont_match(cursor, TRAVIAN_DATABASE_NAME, **buildings_level_info)
    recreate_table_if_columns_dont_match(cursor, TRAVIAN_DATABASE_NAME, **buildings_effect,
                                         **buildings_effect_precedences)
    recreate_table_if_columns_dont_match(cursor, TRAVIAN_DATABASE_NAME, **troops_prices)
    recreate_table_if_columns_dont_match(cursor, TRAVIAN_DATABASE_NAME, **troops_stats, **troops_stats_precedences)

    logger.info("All tables with correct columns present")


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

    effects, requirements, levels = get_travian_buildings_data()
    stats, prices = get_travian_troops_data()

    logger.info("Loading database tables")

    load_table_if_empty(cursor, buildings_effect["table_name"], buildings_effect["columns"], effects)
    load_table_if_empty(cursor, buildings_requirements["table_name"], buildings_requirements["columns"], requirements)
    load_table_if_empty(cursor, buildings_level_info["table_name"], buildings_level_info["columns"], levels)

    load_table_if_empty(cursor, troops_stats["table_name"], troops_stats["columns"], stats)
    load_table_if_empty(cursor, troops_prices["table_name"], troops_prices["columns"], prices)

    conn.commit()

    cursor.close()
    conn.close()
    logger.info("Exiting function")

    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f'Total execution time: {execution_time:4f} seconds')


load_database()
