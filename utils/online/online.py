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
        return True

    async def join(self, member: nextcord.Member,
                   channel, transition=False) -> None:
        if not transition:
            try:
                log_channel, embed = self.send_embed_online(member=member, channel=channel, join=True)
                await log_channel.send(embed=embed)
            except:
                pass
        await self.database.add_join_info(member, channel, is_counting(channel))

    async def leave(self, member, channel, transition=False) -> None:
        if not transition:
            try:
                log_channel, embed = self.send_embed_online(member=member, channel=channel, leave=True)
                await log_channel.send(embed=embed)
            except:
                pass
        await self.database.add_leave_info(member, channel)

    async def get_info(self, is_open, *, user_id, guild_id, date: str = None):
        return await self.database.get_info(is_open, user_id, guild_id,
                                            date if date else datetime.datetime.now().strftime('%d.%m.%Y'))

    @staticmethod
    def send_embed_online(member: nextcord.Member, channel: nextcord.VoiceChannel, join=False, leave=False):
        if join:
            message = f'Участник {member.mention} вошел в канал "{channel.name}" (ID канала: {channel.id})'
        elif leave:
            message = f'Участник {member.mention} покинул канал "{channel.name}" (ID канала: {channel.id})'
        else:
            return
        embed = nextcord.Embed(title='Лог Онлайн', color=nextcord.Color.dark_purple())
        embed.add_field(name='', value=message)
        embed.set_author(name=member.display_name, icon_url=member.avatar.url)
        embed.set_footer(text=f'ID участника: {member.id} | {datetime.datetime.now().strftime("%H:%M:%S")}',
                         icon_url=member.avatar.url)
        log_channel = [channel for channel in member.guild.channels if "логи-голосовых-esbot" in channel.name][0]
        return log_channel, embed
