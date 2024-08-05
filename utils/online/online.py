import asyncio
import datetime
import importlib

import nextcord

from utils.classes import AbstractChannel, AbstractUser
from utils.neccessary import is_counting, load_buttons
from utils.online.online_database import OnlineDatabase
from typing import Union


class OnlineHandler:
    def __init__(self, client, mongodb, buttons) -> None:
        self.client = client
        self.database = OnlineDatabase(mongodb)
        self.buttons = buttons

    async def reload(self, all_channels):
        await load_buttons(self.client, self.buttons, type_buttons='Online')
        print("Начал обновление онлайна пользователей!")
        current_info = await self.database.get_current_info()
        call_user = 0
        for channel in all_channels:
            if isinstance(channel, (nextcord.VoiceChannel, nextcord.StageChannel)):
                for member in channel.members:
                    if not (prev_channel := current_info.in_channel(member.id, channel.guild.id)):
                        call_user = member.id
                        await self.join(member, channel)
                    elif prev_channel[0] != channel.id:
                        if not call_user == member.id:
                            call_user = member.id
                            prev_channel_obj = AbstractChannel(id=prev_channel[0], name=prev_channel[1])
                            await self.leave(member, prev_channel_obj)
                            await self.join(member, channel)
                for user in current_info.get_channel_users(channel.id):
                    if not user in [member.id for member in channel.members]:
                        if not call_user == user:
                            call_user = user
                            await self.leave(AbstractUser(user, channel.guild), channel)
        print("Обновление онлайна пользователей прошло успешно!")

    async def join(self, member: nextcord.Member,
                   channel) -> None:
        await self.database.add_join_info(member, channel, is_counting(channel))

    async def leave(self, member, channel) -> None:
        await self.database.add_leave_info(member, channel)

    async def get_info(self, is_open, *, user_id, guild_id, date: str = None):
        return await self.database.get_info(is_open, user_id, guild_id,
                                            date if date else datetime.datetime.now().strftime('%d.%m.%Y'))
