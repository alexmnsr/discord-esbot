# Используем базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /bots/discord-esbot

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Копируем entrypoint.sh в контейнер и устанавливаем права на выполнение
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Устанавливаем точку входа
ENTRYPOINT ["./entrypoint.sh"]