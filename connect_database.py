# connect_database.py
import os
from pymongo import MongoClient


def check_database_connection():

    mongo_uri = os.getenv('MONGO_DB') if os.getenv("DEBUG") == 'False' else os.getenv("MONGO_DB_LOCAL")

    client = MongoClient(mongo_uri)

    try:
        # Проверка подключения
        client.admin.command('ping')
        print('Подключение к базе данных успешно! ✅')
        return True
    except Exception as e:
        print(f'Ошибка подключения к базе данных: {e} 🚫')
        return False
    finally:
        client.close()
