import datetime

import nextcord

from utils.neccessary import get_dict_of_time_intervals, mashup_info, seconds_to_time


class CurrentInfo:
    def __init__(self, current_users) -> None:
        self.current_users = current_users

    def in_channel(self, user_id, guild_id):
        for user in self.current_users:
            if user['user_id'] == user_id and user['guild_id'] == guild_id:
                return user['channel_id'], user['channel_name']
        return False

    def get_channel_users(self, channel_id):
        return [user['user_id'] for user in self.current_users if user['channel_id'] == channel_id]


class ChannelInfo:
    def __init__(self, channel_id, channel_name, seconds, is_counting):
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.seconds = seconds
        self.is_counting = is_counting


class DateInfo:
    def __init__(self, all_online):
        self._total = 0
        self.channels = []
        for row in all_online:
            self._total += row['seconds']
            self.channels.append(ChannelInfo(
                row['channel_id'], row['channel_name'], row['seconds'], row['is_counting']
            ))

    @property
    def total_time(self):
        return seconds_to_time(self._total)

    def __str__(self):
        return '\n'.join([f'🔹 {channel.channel_name}: {seconds_to_time(channel.seconds)}' for channel in self.channels])


class OnlineDatabase:
    def __init__(self, db):
        self.db = db
        self.current_online = self.db['current_online']
        self.all_online = self.db['all_online']

    async def get_current_info(self):
        return CurrentInfo(await self.get_current_users())

    async def get_current_users(self):
        return await self.current_online.find({}).to_list(length=None)

    async def pop_current_info(self, user_id: int, channel_id: int):
        current_info = await self.current_online.find_one({
            'user_id': user_id,
            'channel_id': channel_id
        })

        if not current_info:
            return

        await self.current_online.delete_one({
            'user_id': user_id,
            'channel_id': channel_id
        })
        return current_info

    async def add_join_info(self, member: nextcord.Member,
                            channel,
                            is_counting: bool):
        await self.current_online.insert_one({
            'user_id': member.id,
            'guild_id': member.guild.id,
            'channel_id': channel.id,
            'channel_name': channel.name,
            'join_time': datetime.datetime.now(),
            'is_counting': is_counting
        })

    async def add_leave_info(self, member: nextcord.Member,
                             channel):
        now = datetime.datetime.now()

        current_info = await self.pop_current_info(member.id, channel.id)
        if not current_info:
            return

        intervals: dict[str, int] = get_dict_of_time_intervals(current_info['join_time'], now)
        for date, seconds in intervals.items():
            await self.all_online.update_one({
                'user_id': member.id,
                'guild_id': member.guild.id,
                'channel_id': channel.id,
                'channel_name': channel.name,
                'date': date
            }, {
                '$set': {'is_counting': current_info['is_counting']},
                '$inc': {'seconds': seconds}
            }, upsert=True)

    async def get_info(self, is_open: bool, user_id: int, guild_id: int, date: str = None):
        all_online = await self.all_online.find({
            "user_id": user_id, "guild_id": guild_id, "date": date, "is_counting": is_open if is_open else {"$exists": True}
        }).to_list(length=None)
        current_online = await self.current_online.find_one({
            "user_id": user_id, "guild_id": guild_id, "is_counting": is_open if is_open else {"$exists": True}
        })

        if current_online:
            all_online = mashup_info(all_online, current_online, date)
        return DateInfo(all_online)