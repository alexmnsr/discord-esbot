import datetime

import nextcord

from utils.classes import AbstractChannel, AbstractUser
from utils.neccessary import is_counting
from utils.online.online_database import OnlineDatabase


class OnlineHandler:
    def __init__(self, mongodb) -> None:
        self.database = OnlineDatabase(mongodb)

    async def reload(self, all_channels):
        current_info = await self.database.get_current_info()
        for channel in all_channels:
            if isinstance(channel, (nextcord.VoiceChannel, nextcord.StageChannel)):
                for member in channel.members:
                    if not (prev_channel := current_info.in_channel(member.id, channel.guild.id)):
                        await self.join(member, channel)
                    elif prev_channel != channel.id:
                        prev_channel_obj = AbstractChannel(id=prev_channel[0], name=prev_channel[1])
                        await self.leave(member, prev_channel_obj)
                        await self.join(member, channel)
                for user in current_info.get_channel_users(channel.id):
                    if user not in [member.id for member in channel.members]:
                        await self.leave(AbstractUser(user, channel.guild), channel)

    async def join(self, member: nextcord.Member,
                   channel) -> None:
        await self.database.add_join_info(member, channel, is_counting(channel))

    async def leave(self, member, channel) -> None:
        await self.database.add_leave_info(member, channel)

    async def get_info(self, is_open, *, user_id, guild_id, date: str = None):
        return await self.database.get_info(is_open, user_id, guild_id,
                                            date if date else datetime.datetime.now().strftime('%d.%m.%Y'))
