import mysql.connector
from utils import logger


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


def drop_table(cursor, database, table_name):
    cursor.execute(f"USE {database}")
    cursor.execute(f"DROP TABLE {table_name}")


def recreate_table(cursor, database, table_name, columns, column_types, additional_lines):
    drop_table(cursor, database, table_name)
    create_table(cursor, database, table_name, columns, column_types, additional_lines)


def recreate_table_if_columns_dont_match(cursor, database, table_name, columns, column_types, additional_lines,
                                         precedences=None):
    if not table_matches_columns(cursor, database, table_name, columns):
        logger.info(f"Table {table_name} has incorrect columns")
        if precedences:
            for precedence in precedences:
                recreate_table(cursor, database, **precedence)
        recreate_table(cursor, database, table_name, columns, column_types, additional_lines)

    logger.info(f"Table {table_name} has the correct columns")


def get_database_credentials():
    with open("db_credentials.txt", "r") as file:
        return file.readline()[:-1], file.readline()


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


def load_table_if_empty(cursor, database, table_name, table_columns, entries):
    if is_empty(cursor, database, table_name):
        load_table(cursor, table_name, table_columns, entries)
    logger.info(f"Table {table_name} already has entries")


def is_empty(cursor, database, table_name):
    cursor.execute(f"USE {database}")
    cursor.execute(f"SELECT * FROM {table_name}")
    return bool(cursor.fetchall())


def get_login_info(server):
    db_user, db_password = get_database_credentials()
    conn = mysql.connector.connect(
        host="localhost",
        user=db_user,
        password=db_password,
    )

    cursor = conn.cursor()
    cursor.execute("USE travian_login_info")
    cursor.execute(f"SELECT * FROM info WHERE server = '{server}'")

    credentials = cursor.fetchone()
    return credentials[0], credentials[1]
