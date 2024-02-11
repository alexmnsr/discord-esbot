import time
from datetime import datetime
from main import bot
from database import execute_operation


@bot.command(name='stats')
async def add_exception(ctx, user_id: int, date: str):
    if user_id and date:
        query = execute_operation('discord-esbot', 'select', 'logs_users_time_on_voice',
                                  columns='*',
                                  where=f'`user_id`={user_id} AND `date` = \'{date}\'')
    else:
        query = execute_operation('discord-esbot', 'select', 'logs_users_time_on_voice',
                                  columns='*',
                                  where=f'`user_id`={ctx.author.id} AND `date` = \'{datetime.utcfromtimestamp(time.time()).strftime("%d-%m-%Y")}\'')
    for info_user in query:
        real = info_user['time_leave_voice'] - info_user['time_start_open']
        print(f'Пользователь {info_user["user_name"]} отсидел в канале ({info_user["name_channel"]}): {datetime.utcfromtimestamp(real).strftime("%H ч. %M мин. %S сек.")}')
    await ctx.send(f'Ваша статистика за сегодня:\n')
