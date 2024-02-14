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
                              where=f'`cmd` = "{cmd}" AND `id_user` = {user_id} AND `server_id` = {ctx.guild.id}',
                              commit=True)
            embed = disnake.Embed(
                title=f'Снятие личного доступа',
                description=f'Команда: /{cmd}\n↳ Пользователь: {user.name} (ID: {user_id})',
                color=disnake.Color.red())
            await ctx.send(embed=embed)
        else:
            values = {
                'cmd': cmd,
                'id_user': user_id,
                'server_id': ctx.guild.id
            }
            execute_operation('discord-esbot', 'insert', 'personal_access_cmd', values=values,
                              commit=True)
            embed = disnake.Embed(
                title=f'Выдача личного доступа',
                description=f'Команда: /{cmd}\n↳ Пользователь: {user.name} (ID: {user_id})',
                color=disnake.Color.red())
            await ctx.send(embed=embed)
    else:
        await ctx.send('Вы не имеете доступа к данной команде.')


@bot.command(name='access_roles')
async def access_role(ctx, cmd, *, role, sys):
    if ctx.author.id == 479244541858152449:
        if sys == '-d':
            execute_operation('discord-esbot', 'delete', 'access_roles',
                              where=f'`role`="{role}" AND `server_id`={ctx.guild.id} AND `cmd`="{cmd}"', commit=True)
            embed = disnake.Embed(
                title=f'Снятие доступа по роли',
                description=f'Команда: /{cmd}\n↳ Роль: {role}',
                color=disnake.Color.red())
            await ctx.send(embed=embed)
        else:
            values = {
                'role': role,
                'server_id': ctx.guild.id,
                'cmd': cmd
            }
            execute_operation('discord-esbot', 'insert', 'access_roles', values=values,
                              commit=True)
            embed = disnake.Embed(
                title=f'Выдача доступа по роли',
                description=f'Команда: /{cmd}\n↳ Роль: {role}',
                color=disnake.Color.red())
            await ctx.send(embed=embed)
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
            await ctx.send(f'Нет статистики за {date} для пользователя (ID: {user_id})')
            return

        channel_stats = {}
        total_time = 0

        for info_user in query:
            if info_user['id_channel'] not in [exc['id'] for exc in query_exception]:
                real = info_user['time_leave_voice'] - info_user['time_start']
                total_time += real

                channel_name = info_user["name_channel"]
                channel_stats[channel_name] = channel_stats.get(channel_name, 0) + real

        embed = disnake.Embed(title=f'Статистика {query[0]["user_name"]} за {date}', color=disnake.Color.green())

        for channel, channel_time in channel_stats.items():
            embed.add_field(name=f'В канале "{channel}":',
                            value=f'{dt.utcfromtimestamp(channel_time).strftime("%H ч. %M м. %S с.")}',
                            inline=False)

        embed.add_field(name='Итоговое время в каналах:',
                        value=f'{dt.utcfromtimestamp(total_time).strftime("%H ч. %M м. %S с.")}', inline=False)

        await ctx.send(embed=embed)
    else:
        print("Не имеете доступа к данной команде")


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


join_channel = []


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        await user_join_voice(member, after)
        # print(f'Пользователь {member.name} зашел в канал "{after.channel.name}"\nВремя захода: {dt.now().strftime("%H:%M:%S %d-%m-%Y")}')
    elif before.channel and after.channel:
        if await change_voice_parametrs(before, after):
            return
        else:
            await user_move_voice(member, before, after)
    elif before.channel is not None and after.channel is None:
        await user_leaved_voice(member, before)
    else:
        print('Ошибка!')


async def change_voice_parametrs(before, after):
    if before.self_mute != after.self_mute:
        return True
    if before.self_deaf != after.self_deaf:
        return True
    if before.self_video != after.self_video:
        return True
    if before.mute != after.mute:
        return True
    if before.deaf != after.deaf:
        return True
    if before.self_stream != after.self_stream:
        return True
    return False


async def user_join_voice(member, after):
    time_join = time.time() + 3 * 60 * 60
    join_channel.append({member.id: time_join})
    return [time_join, member.name, member.id, after.channel.id, after.channel.name]


async def user_move_voice(member, before, after):
    unix_time = time.time() + 3 * 60 * 60
    try:
        values = {
            'user_id': member.id,
            'user_name': member.name,
            'id_server': member.guild.id,
            'time_start': await get_join_info(member.id),
            'time_leave_voice': unix_time,
            'id_channel': before.channel.id,
            'name_channel': before.channel.name,
            'date': dt.now().strftime("%d-%m-%Y")
        }
        # print('MOVE: ', values)
        execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values, commit=True)
        # print(f'Пользователь {member.name} переместился из "{before.channel.name}" в "{after.channel.name}"')
        for item in join_channel:
            if member.id in item:
                join_channel.remove(item)
                break
        await user_join_voice(member, after)
    except IndexError as e:
        print(f"Ошибка leave_voice : {e}")


async def get_join_info(member_id):
    for entry in join_channel:
        if member_id in entry:
            return entry[member_id]
    return None


async def user_leaved_voice(member, before):
    try:
        unix_time = time.time() + 3 * 60 * 60
        values = {
            'user_id': member.id,
            'user_name': member.name,
            'id_server': member.guild.id,
            'time_start': await get_join_info(member.id),
            'time_leave_voice': unix_time,
            'id_channel': before.channel.id,
            'name_channel': before.channel.name,
            'date': dt.now().strftime("%d-%m-%Y")
        }
        # print('LEAVED: ', values)
        execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values, commit=True)
        # print(f'Пользователь {member.name} вышел.\nВремя выхода: {dt.now().strftime("%H:%M:%S %d-%m-%Y")}')
        for item in join_channel:
            if member.id in item:
                join_channel.remove(item)
                break
    except IndexError as e:
        print(f"Ошибка leave_voice : {e}")
    return


bot.run(os.getenv("TOKEN_BOT"))
