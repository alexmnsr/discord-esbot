import os
from pymongo import MongoClient

mongo_uri = 'mongodb://alex:TFSBvgm_ZugUCOv8Op4U@mongo/admin'
client = MongoClient(mongo_uri)

try:
    # Проверка подключения
    client.admin.command('ping')
    print('Подключение успешно!')
except Exception as e:
    print(f'Ошибка подключения: {e}')
finally:
    client.close()  # Исправил close на маленькую букву