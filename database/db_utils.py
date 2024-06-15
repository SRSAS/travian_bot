import os
import logging
import mysql.connector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Travian Database Logger")


def get_connection_to_database():
    db_user, db_password = get_database_credentials()
    logger.debug(f"Database user: {db_user}")

    return mysql.connector.connect(
        host="localhost",
        user=db_user,
        password=db_password,
    )


def table_matches_columns(cursor, database, table, columns):
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


def create_table_if_doesnt_exist(cursor, database, table_name, columns, column_types, additional_lines):
    if not table_exists(cursor, database, table_name):
        create_table(cursor, database, table_name, columns, column_types, additional_lines)


def create_table(cursor, database, table_name, columns, column_types, additional_lines):
    cursor.execute(f"USE {database}")

    logger.debug(f"Creating {table_name} database")
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


def drop_table(cursor, database, table_name):
    cursor.execute(f"USE {database}")
    cursor.execute(f"DROP TABLE {table_name}")


def recreate_table(cursor, database, table_name, columns, column_types, additional_lines):
    drop_table(cursor, database, table_name)
    create_table(cursor, database, table_name, columns, column_types, additional_lines)


def recreate_table_if_columns_dont_match(cursor, database, table_name, columns, column_types, additional_lines,
                                         precedences=None):
    if not table_matches_columns(cursor, database, table_name, columns):
        logger.debug(f"Table {table_name} has incorrect columns")
        if precedences:
            for precedence in precedences:
                recreate_table(cursor, database, **precedence)
        recreate_table(cursor, database, table_name, columns, column_types, additional_lines)

    logger.debug(f"Table {table_name} has the correct columns")


def get_database_credentials():
    logger.debug("Fetching database credentials")
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "db_credentials.txt")
    if not os.path.isfile(file_path):
        logger.error("Database credentials file doesn't exist")
        return None, None
    try:
        with open(file_path, "r") as file:
            logger.debug("Database credentials file open")
            return file.readline()[:-1], file.readline()
    except FileNotFoundError as fnf:
        logger.error("Database credentials file not found")
        logger.error(f"Error: {fnf}")
    except IOError as ioe:
        logger.error("IOError while trying to read the credentials file")
        logger.error(f"Error: {ioe}")
    except Exception as err:
        logger.error("Unexpected error while trying to read the credentials file")
        logger.error(f"Error: {err}")


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
    logger.debug(query)
    cursor.execute(query)


def load_table(cursor, table_name, table_columns, entries):
    logger.debug(f"Loading {table_name} table")
    for entry in entries:
        insert_into(cursor, table_name, table_columns, entry)


def load_table_if_empty(cursor, database, table_name, table_columns, entries):
    if is_empty(cursor, database, table_name):
        load_table(cursor, table_name, table_columns, entries)
    else:
        logger.debug(f"Table {table_name} already has entries")


def is_empty(cursor, database, table_name):
    cursor.execute(f"USE {database}")
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0] == 0


def get_login_info(server):
    db_user, db_password = get_database_credentials()

    logger.debug(f"Fetching login info for {server}")
    logger.debug(f"Logging with user {db_user}, and password {db_password}")

    conn = mysql.connector.connect(
        host="localhost",
        user=db_user,
        password=db_password,
    )
    logger.debug(f"Connected to {conn}")

    cursor = conn.cursor()

    cursor.execute("USE travian_login_info")
    cursor.execute(f"SELECT * FROM info WHERE server = '{server}'")

    credentials = cursor.fetchone()
    return credentials[0], credentials[1]


def build_info_dict(result):
    return {
            "lumber": result[2],
            "clay": result[3],
            "iron": result[4],
            "crop": result[5],
            "total_cost": result[6],
            "upkeep": result[7],
            "culture_points": result[8],
            "time": result[9],
            "effect_value": result[10],
        }


def get_building_level_info(cursor, building, level, get_all_previous_levels=False):
    cursor.execute("USE travian")
    if not get_all_previous_levels:
        cursor.execute(f"SELECT * FROM buildings_level_info WHERE building = '{building} AND level = {level}'")
        result = cursor.fetchone()

        return build_info_dict(result)
    else:
        cursor.execute(f"SELECT * FROM buildings_level_info WHERE building = '{building}'")
        results = cursor.fetchall()[:level - 1]

        info = []
        for result in results:
            info.append(build_info_dict(result))

        return info


def get_building_effect(cursor, building):
    cursor.execute("USE travian")
    cursor.execute(f"SELECT effect FROM buildings_effect WHERE name = {building}")
    return cursor.fetchone()[0]


def get_building_effect_value(cursor, building, level):
    cursor.execute("USE travian")
    cursor.execute(f"SELECT effect_value FROM buildings_level_info WHERE name = {building} AND level = {level}")
    return cursor.fetchone()[0]


def get_troop_price(cursor, troop):
    cursor.execute("USE travian")
    cursor.execute(f"SELECT * FROM troops_prices WHERE name = {troop}")

    result = cursor.fetchone()

    return {
        "lumber": result[1],
        "clay": result[2],
        "iron": result[3],
        "crop": result[4],
        "total_cost": result[5],
        "upkeep": result[6],
        "time": result[7],
    }
