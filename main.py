import time
import disnake
import os
from datetime import datetime as dt
from disnake.ext import commands
from database import execute_operation

bot = commands.Bot(command_prefix='/', help_command=None, intents=disnake.Intents.all())

@bot.command(name='access')
async def access(ctx, cmd, user_id, sys=None):
    if ctx.author.id == 479244541858152449:
        user = await bot.fetch_user(user_id)
        if sys == '-d':
            execute_operation('discord-esbot', 'delete', table_name='personal_access_cmd',
                              where=f'`cmd` = "{cmd}" AND `id_user` = {user_id} AND `server_id` = {ctx.guild.id}', commit=True)
            await ctx.send(
                f'Пользователь {ctx.author.name} забрал персональный доступ к команде "/{cmd}", пользователю {user.name}')
        else:
            values = {
                'cmd': cmd,
                'id_user': user_id,
                'server_id': ctx.guild.id
            }
            execute_operation('discord-esbot', 'insert', 'personal_access_cmd', values=values,
                              commit=True)
            await ctx.send(
                f'Пользователь {ctx.author.name} выдал персональный доступ к команде "/{cmd}", пользователю {user.name}')
    else:
        await ctx.send('Вы не имеете доступа к данной команде.')


@bot.command(name='access_roles')
async def access_role(ctx, cmd, *, role, sys=None):
    if ctx.author.id == 479244541858152449:
        if sys == '-d':
            execute_operation('discord-esbot', 'delete', 'access_roles',
                              where=f'`role`="{role}" AND `server_id`={ctx.guild.id} AND `cmd`="{cmd}"', commit=True)
            await ctx.send(
                f'Пользователь {ctx.author.name} забрал доступ к команде "/{cmd}", у роли "{role}"')
        else:
            values = {
                'role': role,
                'server_id': ctx.guild.id,
                'cmd': cmd
            }
            execute_operation('discord-esbot', 'insert', 'access_roles', values=values,
                              commit=True)
            await ctx.send(
                f'Пользователь {ctx.author.name} выдал  доступ к команде "/{cmd}", пользователям с ролью "{role}"')
    else:
        await ctx.send('Вы не имеете доступа к данной команде.')


@bot.command(name='stats')
async def add_exception(ctx, user_id=None, date=None):
    if is_access_command(ctx, cmd='stats'):
        if user_id is None and date is None:
            user_id = ctx.author.id
            date = dt.now().strftime("%d-%m-%Y")

        query = execute_operation('discord-esbot', 'select', 'logs_users_time_on_voice',
                                  columns='*',
                                  where=f'`user_id`={user_id} AND `date` = \'{date}\' AND `id_server`={ctx.guild.id}')

        query_exception = execute_operation('discord-esbot', 'select', 'servers_exceptions', columns='id',
                                            where=f'`id_server` = {ctx.guild.id}')

        if not query:
            await ctx.send(f'Нет статистики для пользователя {user_id} за {date}')
            return

        channel_stats = {}
        total_time = 0

        for info_user in query:
            if info_user['id_channel'] not in [exc['id'] for exc in query_exception]:
                real = info_user['time_leave_voice'] - info_user['time_start_open']
                total_time += real

                channel_name = info_user["name_channel"]
                channel_stats[channel_name] = channel_stats.get(channel_name, 0) + real

        embed = disnake.Embed(title=f'Статистика {query[0]["user_name"]} за {date}', color=disnake.Color.green())

        for channel, channel_time in channel_stats.items():
            embed.add_field(name=f'В канале "{channel}"',
                            value=f'{dt.utcfromtimestamp(channel_time).strftime("%H ч. %M м. %S с.")}',
                            inline=False)

        embed.add_field(name='Итоговое время в каналах',
                        value=f'{dt.utcfromtimestamp(total_time).strftime("%H ч. %M м. %S с.")}', inline=False)

        await ctx.send(embed=embed)
    else:
        print("Не имеете доступа к данной команде.")


def is_access_command(ctx, cmd):
    role_access = execute_operation('discord-esbot', 'select', 'access_roles', columns='role',
                                    where=f'`server_id`={ctx.guild.id}')
    personal_access = execute_operation('discord-esbot', 'select', 'personal_access_cmd', columns='*',
                                        where=f'`cmd`="{cmd}" AND `id_user`={ctx.author.id}')
    if personal_access and personal_access[0]['id_user'] == ctx.author.id:
        return True
    elif role_access and isinstance(role_access, list):
        if personal_access and personal_access[0]['id_user'] == ctx.author.id:
            return True
        user_roles = set(role.name for role in ctx.author.roles)
        db_roles = set(entry.get('role') for entry in role_access)
        return bool(user_roles.intersection(db_roles))
    else:
        return False


@bot.event
async def on_ready():
    try:
        for guild in bot.guilds:
            name_server = guild.name
            id_server = guild.id
            print(f'Бот загрузился на сервер {name_server} (ID: {id_server})\n{bot.user.name} (ID: {bot.user.id})')
            try:
                channels_table = execute_operation('discord-esbot', 'select', 'voice_channels_on_servers',
                                                   columns='id_channel', where=f'`id_server`={id_server}')

                if channels_table is not None:
                    server_channels = [id['id_channel'] for id in channels_table]

                    for channel in guild.voice_channels:
                        values = {
                            'id_channel': channel.id,
                            'name_channel': channel.name,
                            'id_server': id_server
                        }
                        try:
                            if values['id_channel'] not in server_channels:
                                # Проверка наличия канала перед вставкой
                                execute_operation('discord-esbot', 'insert', 'voice_channels_on_servers', values=values,
                                                  commit=True)
                                server_channels.append(
                                    values['id_channel'])  # Добавление в список для последующей проверки
                        except Exception as e:
                            print(f'Произошла ошибка при обработке голосовых каналов: {e}')
                else:
                    # Вставка данных, если нет данных в channels_table
                    for channel in guild.voice_channels:
                        values = {
                            'id_channel': channel.id,
                            'name_channel': channel.name,
                            'id_server': id_server
                        }
                        try:
                            execute_operation('discord-esbot', 'insert', 'voice_channels_on_servers', values=values,
                                              commit=True)
                        except Exception as e:
                            print(f'Произошла ошибка при обработке голосовых каналов: {e}')
            except Exception as e:
                print(f'Произошла ошибка при выполнении запроса к базе данных: {e}')
    except Exception as e:
        print(f'Произошла ошибка при выводе информации о сервере: {e}')


user_time = []


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        first_connect_voice = await user_join_voice(member, after)
        print('Зашел в канал:', member.name)
        user_time.append(first_connect_voice[0])
    elif before.channel and after.channel:
        if await change_voice_parametrs(before, after):
            return
        if len(user_time):
            await user_move_voice(user_time[0], member, after, before)
        else:
            print('Нет там столько')
        connect = await user_join_voice(member, before)
        user_time.append(connect[0])
    elif before.channel is not None and after.channel is None:
        if len(user_time):
            await user_leaved_voice(user_time[0], member, after, before)
        else:
            print('Нет там столько')
    else:
        print('Ошибка!')


async def change_voice_parametrs(before, after):
    if before.self_mute != after.self_mute:
        return True
    if before.self_deaf != after.self_deaf:
        return True
    return False


async def user_join_voice(member, before):
    exceptions_table = execute_operation('discord-esbot', 'select', 'servers_exceptions',
                                         columns='id')
    unix_time = time.time() + 3 * 60 * 60
    time_join_open = unix_time
    return [time_join_open, member.name, member.id, before.channel.id, before.channel.name]


async def user_move_voice(time_start_open, member, after, before):
    unix_time = time.time() + 3 * 60 * 60
    values = {
        'user_id': member.id,
        'user_name': member.name,
        'id_server': member.guild.id,
        'time_start_open': time_start_open,
        'time_leave_voice': unix_time,
        'id_channel': before.channel.id,
        'name_channel': before.channel.name,
        'date': dt.now().strftime("%d-%m-%Y")
    }
    execute_operation('discord-esbot', 'select', 'servers_exceptions', columns='id')
    execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values, commit=True)
    user_time.clear()


async def user_leaved_voice(time_start_open, member, after, before):
    unix_time = time.time() + 3 * 60 * 60
    values = {
        'user_id': member.id,
        'user_name': member.name,
        'id_server': member.guild.id,
        'time_start_open': time_start_open,
        'time_leave_voice': unix_time,
        'id_channel': before.channel.id,
        'name_channel': before.channel.name,
        'date': dt.now().strftime("%d-%m-%Y")
    }
    execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values, commit=True)
    time_leave_open = unix_time - time_start_open
    print(
        f'Пользователь вышел из голосовых чатов:\nВремя проведенное в каналах: {dt.utcfromtimestamp(time_leave_open).strftime("%H ч. %M мин. %S сек.")}')
    user_time.clear()
    return [time_leave_open, member.name, member.id, before.channel.id, before.channel.name]


bot.run(os.getenv("TOKEN_BOT"))
