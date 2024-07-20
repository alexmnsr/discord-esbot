# Используем базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /bots/discord-esbot

# Устанавливаем переменную окружения TZ для временной зоны
ENV TZ=Europe/Moscow

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем временную зону
RUN apt-get update
RUN apt-get install -y tzdata
RUN ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime
RUN echo "Europe/Moscow" > /etc/timezone

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
