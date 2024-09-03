# Используем базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /bots/discord-esbot

# Устанавливаем переменную окружения TZ для временной зоны
ENV TZ=Europe/Moscow

# Устанавливаем временную зону и устанавливаем cron для задач
RUN apt-get update && \
    apt-get install -y tzdata cron && \
    ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    echo "Europe/Moscow" > /etc/timezone && \
    apt-get clean

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем директорию cogs
COPY cogs ./bots/discord-esbot/cogs

# Копируем весь проект
COPY . .

# Копируем entrypoint.sh в контейнер
COPY entrypoint.sh .

RUN chmod +x entrypoint.sh

# Создаем скрипт для бэкапа
RUN echo '#!/bin/bash\n'\
'TIMESTAMP=$(date +%F-%H%M)\n'\
'BACKUP_DIR=/backup/$TIMESTAMP\n'\
'MONGO_HOST=mongo\n'\
'MONGO_PORT=27017\n'\
'MONGO_USER=${MONGO_LOGIN}\n'\
'MONGO_PASS=${MONGO_PASSWORD}\n'\
'MONGO_DB=your_database_name\n'\
'mkdir -p $BACKUP_DIR\n'\
'mongodump --host $MONGO_HOST --port $MONGO_PORT --username $MONGO_USER --password $MONGO_PASS --db $MONGO_DB --out $BACKUP_DIR\n'\
'find /backup/* -mtime +7 -exec rm -rf {} \;'\
> /usr/local/bin/backup.sh && chmod +x /usr/local/bin/backup.sh

# Добавляем задание в cron для выполнения скрипта каждый день в 23:59 по МСК
RUN echo "59 23 * * * root /usr/local/bin/backup.sh >> /var/log/cron.log 2>&1" > /etc/crontab

# Запускаем cron вместе с приложением
CMD cron && ./entrypoint.sh