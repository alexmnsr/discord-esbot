# Используем базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /bots/discord-esbot

# Устанавливаем переменную окружения TZ для временной зоны
ENV TZ=Europe/Moscow

# Обновляем систему и устанавливаем tzdata для установки временной зоны
RUN apt-get update && \
    apt-get install -y tzdata

# Устанавливаем временную зону
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

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

# Устанавливаем точку входа
ENTRYPOINT ["./entrypoint.sh"]
