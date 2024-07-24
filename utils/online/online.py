import datetime

import nextcord

from utils.classes import AbstractChannel, AbstractUser
from utils.neccessary import is_counting
from utils.online.online_database import OnlineDatabase
from typing import Union


class OnlineHandler:
    def __init__(self, mongodb) -> None:
        self.database = OnlineDatabase(mongodb)

    async def reload(self, all_channels):
        current_info = await self.database.get_current_info()
        for channel in all_channels:
            if isinstance(channel, (nextcord.VoiceChannel, nextcord.StageChannel)):
                current_members_ids = {member.id for member in channel.members}

                for member in channel.members:
                    prev_channel = current_info.in_channel(member.id, channel.guild.id)
                    if not prev_channel:
                        try:
                            await self.join(member, channel)
                        except Exception as e:
                            print(f"Ошибка при входе пользователя {member.name} в канал {channel.name}: {e}")
                    elif prev_channel != channel.id:
                        prev_channel_obj = AbstractChannel(id=prev_channel[0], name=prev_channel[1])
                        try:
                            await self.leave(member, prev_channel_obj)
                            await self.join(member, channel)
                        except Exception as e:
                            print(
                                f"Ошибка при перемещении пользователя {member.name} из канала {prev_channel_obj.name} в канал {channel.name}: {e}")

                db_channel_users = set(current_info.get_channel_users(channel.id))
                for user_id in db_channel_users:
                    if user_id not in current_members_ids:
                        try:
                            await self.leave(AbstractUser(user_id, channel.guild), channel)
                        except Exception as e:
                            print(f"Ошибка при выходе пользователя {user_id} из канала {channel.name}: {e}")

    async def join(self, member: nextcord.Member, channel: Union[nextcord.VoiceChannel, nextcord.StageChannel]) -> None:
        try:
            await self.database.add_join_info(member, channel, is_counting(channel))
        except Exception as e:
            print(f"Ошибка при добавлении информации о входе пользователя {member.name} в канал {channel.name}: {e}")

    async def leave(self, member: nextcord.Member,
                    channel: Union[nextcord.VoiceChannel, nextcord.StageChannel]) -> None:
        try:
            await self.database.add_leave_info(member, channel)
        except Exception as e:
            print(f"Ошибка при добавлении информации о выходе пользователя {member.name} из канала {channel.name}: {e}")

    async def get_info(self, is_open: bool, *, user_id: int, guild_id: int, date: str = None):
        date_str = date if date else datetime.datetime.now().strftime('%d.%m.%Y')
        try:
            return await self.database.get_info(is_open, user_id, guild_id, date_str)
        except Exception as e:
            print(f"Ошибка при получении информации для пользователя {user_id} в гильдии {guild_id}: {e}")
            return None
