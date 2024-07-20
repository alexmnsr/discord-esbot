#!/bin/bash

# Устанавливаем временную зону
RUN apt-get update && apt-get install -y tzdata

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone # test

# Переходим в рабочую директорию вашего проекта внутри контейнера
cd /bots/discord-esbot

# Запускаем основной скрипт вашего приложения
python main.py