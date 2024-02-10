import disnake
import time
import os
from disnake.ext import commands
from database import execute_operation, execute_query

bot = commands.Bot(command_prefix='/', help_command=None, intents=disnake.Intents.all())


@bot.command(name='add_exception')
async def add_exception(ctx):
    await ctx.send(f'Привет, {ctx.author.name}!')


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


@bot.event
async def on_voice_state_update(member, before, after):
    global time_join
    global time_difference
    global time_exception
    time_exception = []
    last_joins = {}
    if before.channel is None and after.channel is not None:
        time_join = time.time()
        last_join_time = time_join
        last_joins[after.channel.id] = time_join
        print(f'Заход {member} "{after.channel.name}": {round(last_join_time, 2)}')
    elif before.channel is not None and after.channel is not None:
        if before.channel.id != after.channel.id:
            try:
                time_leave = time.time()
                time_difference = time_leave - time_join
                exceptions_table = execute_operation('discord-esbot', 'select', 'servers_exceptions',
                                                     columns='id')
                for id in exceptions_table:
                    if id['id'] == after.channel.id:
                        time_exception.append(time_difference)
                        break
                else:
                    if before.channel.id != after.channel.id:
                        print(f'Перезаход в другой канал {member} "{after.channel.name}": {round(time_difference, 2)}')
            except:
                print('Ошибка')
    elif before.channel is not None and after.channel is None:
        hours, remainder = divmod(int(time_difference), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(time_exception)
        print(
            f'Пользователь {member} покинул голосовые каналы.\nВремя проведенное в открытых каналах: {hours} часов, {minutes} минут, {seconds} секунд.\nВремя проведенное в закрытых каналах: {time_exception}')


bot.run(os.getenv("TOKEN_BOT"))
