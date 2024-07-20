#!/bin/bash

# Устанавливаем временную зону
ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime
echo "Europe/Moscow" > /etc/timezone

# Переходим в рабочую директорию вашего проекта внутри контейнера
cd /bots/discord-esbot

# Запускаем основной скрипт вашего приложения
python main.py