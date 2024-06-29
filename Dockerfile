# Используем базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR bots/discord-esbot

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Открываем порт (если требуется для внешних подключений)
EXPOSE 2356

# Указываем команду для запуска приложения
CMD ["python", "main.py"]