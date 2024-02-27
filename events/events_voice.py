import time
import json
import aiofiles
from disnake.ext import commands
from database import execute_operation
from datetime import datetime as dt


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.load_join_channel_data()

    def load_join_channel_data(self):
        try:
            with open('voice_data.json', 'r') as file:
                self.bot.join_channel = [{int(k): v for k, v in entry.items()} for entry in json.load(file)]
        except (json.JSONDecodeError, FileNotFoundError):
            self.bot.join_channel = []

    async def change_voice_parameters(self, before, after):
        parameters_to_check = ['self_mute', 'self_deaf', 'self_video', 'mute', 'deaf', 'self_stream']
        return any(getattr(before, param) != getattr(after, param) for param in parameters_to_check)

    async def user_join_voice(self, member, after):
        time_join = time.time() + 3 * 60 * 60
        self.bot.join_channel.append({member.id: time_join})
        return [time_join, member.name, member.id, after.channel.id, after.channel.name]

    async def user_move_voice(self, member, before, after):
        access = False
        try:
            unix_time = time.time() + 3 * 60 * 60
            time_start = await self.get_join_info(member.id)
            moderator_info = execute_operation('discord-esbot', 'select', 'moderator_servers', columns='id_user',
                                               where=f'`id_server` = {member.guild.id}')
            for i in moderator_info:
                if i['id_user'] == member.id:
                    access = True
                    break
            if not await self.get_exception(member, before):
                if time_start is not None and moderator_info is not None and access:
                    if dt.fromtimestamp(time_start).strftime('%Y-%m-%d') != dt.fromtimestamp(unix_time).strftime(
                            '%Y-%m-%d'):
                        midnight_start = dt.fromtimestamp(time_start).replace(hour=23, minute=59, second=59)
                        midnight_leave = dt.fromtimestamp(unix_time).replace(hour=0, minute=0, second=1)
                        time_start_first_day = time_start
                        time_leave_first_day = midnight_start.timestamp()
                        time_start_next_day = (midnight_leave).timestamp()

                        values_first_day = {
                            'user_id': member.id,
                            'user_name': member.name,
                            'id_server': member.guild.id,
                            'time_start': time_start_first_day,
                            'time_leave_voice': time_leave_first_day,
                            'id_channel': before.channel.id,
                            'name_channel': before.channel.name,
                            'date': dt.fromtimestamp(time_start_first_day).strftime("%d-%m-%Y")
                        }

                        values_next_day = {
                            'user_id': member.id,
                            'user_name': member.name,
                            'id_server': member.guild.id,
                            'time_start': time_start_next_day,
                            'time_leave_voice': unix_time,
                            'id_channel': before.channel.id,
                            'name_channel': before.channel.name,
                            'date': dt.fromtimestamp(time_start_next_day).strftime("%d-%m-%Y")
                        }

                        execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice',
                                          values=values_first_day,
                                          commit=True)
                        execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values_next_day,
                                          commit=True)
                    else:
                        values = {
                            'user_id': member.id,
                            'user_name': member.name,
                            'id_server': member.guild.id,
                            'time_start': time_start,
                            'time_leave_voice': unix_time,
                            'id_channel': before.channel.id,
                            'name_channel': before.channel.name,
                            'date': dt.fromtimestamp(time_start).strftime("%d-%m-%Y")
                        }

                        execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values,
                                          commit=True)

            for item in self.bot.join_channel:
                if member.id in item:
                    self.bot.join_channel.remove(item)
                    break
            await self.user_join_voice(member, after)
        except IndexError as e:
            print(f"Ошибка move_voice : {e}")

    async def user_leaved_voice(self, member, before):
        access = False
        try:
            unix_time = time.time() + 3 * 60 * 60
            time_start = await self.get_join_info(member.id)
            moderator_info = execute_operation('discord-esbot', 'select', 'moderator_servers', columns='id_user',
                                               where=f'`id_server` = {member.guild.id}')
            for i in moderator_info:
                if i['id_user'] == member.id:
                    access = True
                    break
            if not await self.get_exception(member, before):
                if time_start is not None and moderator_info is not None and access:
                    if dt.fromtimestamp(time_start).strftime('%Y-%m-%d') != dt.fromtimestamp(unix_time).strftime(
                            '%Y-%m-%d'):
                        midnight_start = dt.fromtimestamp(time_start).replace(hour=23, minute=59, second=59)
                        midnight_leave = dt.fromtimestamp(unix_time).replace(hour=0, minute=0, second=1)
                        time_start_first_day = time_start
                        time_leave_first_day = midnight_start.timestamp()
                        time_start_next_day = (midnight_leave).timestamp()

                        values_first_day = {
                            'user_id': member.id,
                            'user_name': member.name,
                            'id_server': member.guild.id,
                            'time_start': time_start_first_day,
                            'time_leave_voice': time_leave_first_day,
                            'id_channel': before.channel.id,
                            'name_channel': before.channel.name,
                            'date': dt.fromtimestamp(time_start_first_day).strftime("%d-%m-%Y")
                        }

                        values_next_day = {
                            'user_id': member.id,
                            'user_name': member.name,
                            'id_server': member.guild.id,
                            'time_start': time_start_next_day,
                            'time_leave_voice': unix_time,
                            'id_channel': before.channel.id,
                            'name_channel': before.channel.name,
                            'date': dt.fromtimestamp(time_start_next_day).strftime("%d-%m-%Y")
                        }

                        execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice',
                                          values=values_first_day,
                                          commit=True)
                        execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values_next_day,
                                          commit=True)
                    else:
                        values = {
                            'user_id': member.id,
                            'user_name': member.name,
                            'id_server': member.guild.id,
                            'time_start': time_start,
                            'time_leave_voice': unix_time,
                            'id_channel': before.channel.id,
                            'name_channel': before.channel.name,
                            'date': dt.fromtimestamp(time_start).strftime("%d-%m-%Y")
                        }

                        execute_operation('discord-esbot', 'insert', 'logs_users_time_on_voice', values=values,
                                          commit=True)

            for item in self.bot.join_channel:
                if member.id in item:
                    self.bot.join_channel.remove(item)
                    break
        except IndexError as e:
            print(f"Ошибка leave_voice : {e}")
        return

    async def get_join_info(self, member_id):
        for entry in self.bot.join_channel:
            if member_id in entry:
                return entry[member_id]
        return None

    async def get_exception(self, member, before):
        query_exception = execute_operation('discord-esbot', 'select', 'servers_exceptions', columns='id',
                                            where=f'`id_server` = {member.guild.id}')
        for i in query_exception:
            if i['id'] == before.channel.id:
                return True
        else:
            return False

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            for guild in self.bot.guilds:
                name_server = guild.name
                id_server = guild.id
                print(
                    f'Бот загрузился на сервер {name_server} (ID: {id_server})\n{self.bot.user.name} (ID: {self.bot.user.id})')
                try:
                    channels_table = execute_operation('discord-esbot', 'select', 'voice_channels_on_servers',
                                                       columns='id_channel', where=f'`id_server`={id_server}')

                    server_channels = [id['id_channel'] for id in channels_table] if channels_table else []

                    for channel in guild.voice_channels:
                        values = {
                            'id_channel': channel.id,
                            'name_channel': channel.name,
                            'id_server': id_server
                        }
                        try:
                            if values['id_channel'] not in server_channels:
                                execute_operation('discord-esbot', 'insert', 'voice_channels_on_servers', values=values,
                                                  commit=True)
                                server_channels.append(values['id_channel'])
                        except Exception as e:
                            print(f'Error processing voice channels: {e}')
                except Exception as e:
                    print(f'Error executing database query: {e}')
        except Exception as e:
            print(f'Error displaying server information: {e}')

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel is not None:
            await self.user_join_voice(member, after)
        elif before.channel and after.channel:
            if await self.change_voice_parameters(before, after):
                return
            else:
                await self.user_move_voice(member, before, after)
        elif before.channel is not None and after.channel is None:
            await self.user_leaved_voice(member, before)
        else:
            print('Error!')
        await self.write_to_file(self.bot.join_channel)

    async def write_to_file(self, data):
        async with aiofiles.open('events/voice_data.json', 'w') as file:
            await file.write(json.dumps(data, indent=2))
