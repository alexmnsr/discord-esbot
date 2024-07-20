# Используем базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /bots/discord-esbot

# Устанавливаем переменную окружения TZ для временной зоны
ENV TZ=Europe/Moscow

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN apt-get update && \
    apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    echo "Europe/Moscow" > /etc/timezone && \
    apt-get clean

# Копируем директорию cogs
COPY cogs ./bots/discord-esbot/cogs

# Копируем весь проект
COPY . .

# Копируем entrypoint.sh в контейнер
COPY entrypoint.sh .

# Устанавливаем точку входа
ENTRYPOINT ["./entrypoint.sh"]
