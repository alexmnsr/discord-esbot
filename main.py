from datetime import datetime
import disnake
import time
import os
from disnake.ext import commands
from database import execute_operation, execute_query

bot = commands.Bot(command_prefix='/', help_command=None, intents=disnake.Intents.all())

#123
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
        print(
            f'Пользователь {info_user["user_name"]} отсидел в канале ({info_user["name_channel"]}): {datetime.utcfromtimestamp(real).strftime("%H ч. %M мин. %S сек.")}')
    await ctx.send(f'Ваша статистика за сегодня:\n')


@bot.event
async def on_ready():
    for guild in bot.guilds:
        name_server = guild.name
        id_server = guild.id
    print(f'Бот загрузился на сервер {name_server} (ID: {id_server})\n{bot.user.name} (ID: {bot.user.id})')
    voice_channel_list = []
    for guild in bot.guilds:
        for channel in guild.voice_channels:
            voice_channel_list.append([channel.name, channel.id])
            values = {
                'id_channel': channel.id,
                'name_channel': channel.name,
                'id_server': id_server
            }
            try:
                channels = []
                channels_table = execute_operation('discord-esbot', 'select', 'voice_channels_on_servers',
                                                   columns='id_channel', where=f'id_server="{values["id_server"]}"')
                for id in channels_table:
                    channels.append(id['id_channel'])
                if values['id_channel'] not in channels:
                    execute_operation('discord-esbot', 'insert', 'voice_channels_on_servers', values=values,
                                      commit=True)
            except:
                print('Произошла ошибка при отправке запроса MySql')


user_time = []


@bot.event
async def on_voice_state_update(member, before, after):
    if after.self_mute and before.self_mute and after.self_deaf and before.self_deaf:
        return
    elif before.channel is None and after.channel is not None:
        first_connect_voice = await user_join_voice(member, after)
        print('Зашел в канал:', member.name)
        user_time.append(first_connect_voice[0])
        user_time.append(first_connect_voice[1])
    elif before.channel and after.channel:
        await user_move_voice(user_time[0], user_time[1], member, after, before)
        connect = await user_join_voice(member, before)
        user_time.append(connect[0])
        user_time.append(connect[1])
    elif before.channel is not None and after.channel is None:
        await user_leaved_voice(user_time[0], user_time[1], member, after, before)
    else:
        print('Ошибка!')


async def user_join_voice(member, before):
    exceptions_table = execute_operation('discord-esbot', 'select', 'servers_exceptions',
                                         columns='id')
    if before.channel.id == exceptions_table[0]['id']:
        time_join_open = 0
        time_join_close = time.time()
    else:
        time_join_open = time.time()
        time_join_close = 0
    return [time_join_open, time_join_close, member.name, member.id, before.channel.id, before.channel.name]


async def user_move_voice(time_start_open, time_start_close, member, after, before):
    id_server = [guild.id for guild in bot.guilds]
    values = {
        'user_id': member.id,
        'user_name': member.name,
        'id_server': id_server[0],
        'time_start_open': time_start_open,
        'time_start_close': time_start_close,
        'time_leave_voice': time.time(),
        'id_channel': before.channel.id,
        'name_channel': before.channel.name,
        'date': datetime.utcfromtimestamp(time.time()).strftime("%d-%m-%Y")
    }
    execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values, commit=True)
    exceptions_table = execute_operation('discord-esbot', 'select', 'servers_exceptions',
                                         columns='id')
    if after.channel.id == exceptions_table[0]['id']:
        print('Вы перешли в закрытый канал, учет времени закончен.')
    elif before.channel.id != exceptions_table[0]['id']:
        print(
            f'{member.name} провел в "{before.channel.name}" ({time.time() - time_start_open}), перешли в {after.channel.name} (открытый), учет времени продолжен.')
    user_time.clear()


async def user_leaved_voice(time_start_open, time_start_close, member, after, before):
    id_server = [guild.id for guild in bot.guilds]
    values = {
        'user_id': member.id,
        'user_name': member.name,
        'id_server': id_server[0],
        'time_start_open': time_start_open,
        'time_start_close': time_start_close,
        'time_leave_voice': time.time(),
        'id_channel': before.channel.id,
        'name_channel': before.channel.name,
        'date': datetime.utcfromtimestamp(time.time()).strftime("%d-%m-%Y")
    }
    execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values, commit=True)
    if time_start_close != 0:
        time_leave_open = 0
        time_leave_close = time.time() - time_start_close
    elif time_start_open != 0:
        time_leave_open = time.time() - time_start_open
        time_leave_close = 0
    else:
        time_leave_open = time.time() - time_start_open
        time_leave_close = time.time() - time_start_close
    print(
        f'Пользователь вышел из голосовых чатов:\nВремя проведенное в каналах: {datetime.utcfromtimestamp(time_leave_open).strftime("%H ч. %M мин. %S сек.")} (Закрытые: {datetime.utcfromtimestamp(time_leave_close).strftime("%H ч. %M мин. %S сек.")})')
    user_time.clear()
    return [time_leave_open, time_leave_close, member.name, member.id, before.channel.id, before.channel.name]


bot.run(os.getenv("TOKEN_BOT"))
