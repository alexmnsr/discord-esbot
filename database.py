import ast
import logging
import os
import mysql.connector.pooling
from dotenv import load_dotenv

load_dotenv()

db_pools = {}
for db_name in [os.getenv("DB_NAME_1"), os.getenv("DB_NAME_2"), os.getenv("DB_NAME_3")]:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name=f"db_pool_{db_name}",
        pool_size=5,
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=db_name,
        port=3306,
        charset='utf8mb4',
    )
    db_pools[db_name] = db_pool


def execute_query(conn, query, args=(), commit=False):
    if conn not in db_pools:
        raise ValueError(f"Invalid connection number: {conn}")

    db_conn = db_pools[conn].get_connection()
    cursor = db_conn.cursor(dictionary=True)
    try:
        debug = ast.literal_eval(os.getenv("DEBUG"))
        if debug:
            if args:
                logging.info(f'SQL запрос: {query} || SQL аргументы: {args}')
            else:
                logging.info(f'SQL запрос: {query}')
        cursor.execute(query, args)
        if query.lower().startswith(("select", "show")):
            result = cursor.fetchall()
        else:
            result = None
        if commit:
            db_conn.commit()
        return result
    except mysql.connector.Error as e:
        db_conn.rollback()
        return None
    finally:
        cursor.close()
        db_conn.close()


def execute_operation(conn, operation, table_name, columns='*', where=None, values=None, args=(), commit=False):
    if operation == 'insert':
        columns = ', '.join(values.keys())
        placeholders = ', '.join(['%s'] * len(values))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        args = tuple(values.values())
    elif operation == 'select':
        query = f"SELECT {columns} FROM {table_name}"
        if where:
            query += f" WHERE {where}"
    elif operation == 'update':
        set_clause = ', '.join([f"{column} = %s" for column in values.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        args = tuple(values.values())
    elif operation == 'delete':
        query = f"DELETE FROM {table_name} WHERE {where}"
    else:
        raise ValueError(f"Invalid operation: {operation}")

    return execute_query(conn, query, args, commit=commit)