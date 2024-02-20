import asyncio
import os
import disnake
from bot import commands
from datetime import datetime as dt
from database import execute_operation
from openpyxl import load_workbook

intents = disnake.Intents.default().all()
bot = commands.Bot(command_prefix='/', help_command=None, intents=intents)


async def fill_table():
    id_servers_db = execute_operation('discord-esbot', 'select', 'voice_channels_on_servers', columns='id_server',
                                      group='id_server')
    date = dt.now().strftime("%d-%m-%Y")

    for i in id_servers_db:
        full_way = os.path.join('tables_standart', f'table_{i["id_server"]}.xlsx')

        if os.path.isfile(full_way):
            moderators = execute_operation('discord-esbot', 'select', 'moderator_servers',
                                           columns='*',
                                           where=f'`id_server`={i["id_server"]}')
            if moderators:
                user_info = []
                for record in moderators:
                    role = record.get('role_user', 'MD')  # По умолчанию 'MD', если роль не указана в базе
                    workbook = load_workbook(full_way)

                    try:
                        sheet = workbook[role]
                    except KeyError:
                        print(f"Лист с именем '{role}' не найден в таблице к серверу (ID: {i['id_server']})")
                        continue

                    nickname_user = record.get('nickname_user')
                    user_id = record.get('id_user')
                    server = record.get('id_server')
                    cell_online = record.get('cell_online')
                    cell_nickname = record.get('cell_nickname')
                    cell_access_role = record.get('cell_access_role')
                    cell_denied_role = record.get('cell_denied_role')
                    cell_punishments = record.get('cell_punishments')

                    query = execute_operation('discord-esbot', 'select', 'logs_users_time_on_voice',
                                              columns='*',
                                              where=f'`user_id`={user_id} AND `date` = \'{date}\' AND `id_server`={server}')

                    query_exception = execute_operation('discord-esbot', 'select', 'servers_exceptions', columns='id',
                                                        where=f'`id_server` = {server}')

                    channel_stats = {}
                    total_time = 0

                    for info_user in query:
                        if info_user['id_channel'] not in [exc['id'] for exc in query_exception]:
                            real = info_user['time_leave_voice'] - info_user['time_start']
                            total_time += real

                            channel_name = info_user["name_channel"]
                            channel_stats[channel_name] = channel_stats.get(channel_name, 0) + real



                    sheet[f'{cell_nickname}'] = f'{nickname_user}'
                    sheet[f'{cell_access_role}'] = 5
                    sheet[f'{cell_denied_role}'] = 1
                    sheet[f'{cell_punishments}'] = 1
                    sheet[f'{cell_online}'] = dt.utcfromtimestamp(total_time).strftime("%H:%M:%S    ")
                    user_info.append({'server_id': server,
                                      'message': f'Модератор {nickname_user} ({role}), online: {dt.utcfromtimestamp(total_time).strftime("%H ч. %M м. %S с.")}, access_role: {cell_access_role}, denied_role: {cell_denied_role}, punishments: {cell_punishments}'})
                    workbook.save(full_way)

                online_message = f'Онлайн на сервере за {date}:\n'

                target_channel_ids = [690955874436644965]
# 898582894849699886, 792401745883562035,
                for target_channel_id in target_channel_ids:
                    target_channel = bot.get_channel(target_channel_id)
                    for data in user_info:
                        pass
                    if target_channel:
                        await target_channel.send(online_message)
                    else:
                        print(f"Не удалось найти канал с ID {target_channel_id}")
            else:
                print(f"Для сервера (ID: {i['id_server']}) отсутствуют модераторы в базе данных")
        else:
            print(f"Не найдена таблица к серверу (ID: {i['id_server']})")


@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')
    # Запустите функцию fill_table после успешного запуска бота
    await fill_table()


if __name__ == "__main__":
    bot.run(os.getenv("TOKEN_BOT"))
