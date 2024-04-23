import datetime
import enum

from motor import motor_asyncio


class ActionType(enum.Enum):
    BAN_LOCAL = 'ban_local'
    BAN_GLOBAL = 'ban_global'
    WARN_LOCAL = 'warn_local'
    TIME_WARN = 'warn_time'
    MUTE_TEXT = 'mute_text'
    MUTE_VOICE = 'mute_voice'
    MUTE_FULL = 'mute_full'
    ROLES = 'roles_action'


class Actions:
    def __init__(self, db: motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.actions = self.db['list']

    async def add_action(self, *, user_id, guild_id, moderator_id, action_type, payload):
        action_id = await self.actions.count_documents({}) + 1000
        await self.actions.insert_one({
            'user_id': user_id,
            'guild_id': guild_id,
            'moderator_id': moderator_id,
            'action_type': str(action_type),
            'payload': payload,
            '_id': action_id,
            'time': datetime.datetime.now(),
        })
        return action_id

    async def get_punishments(self, type_punishment, *, user_id=None, guild_id=None):
        query = {'user_id': user_id}
        if guild_id:
            query['guild_id'] = guild_id
        if type_punishment != 'FULL':
            query['action_type'] = 'ActionType.' + type_punishment

        punishments = await self.actions.find(query).to_list(length=None)
        return punishments

    @staticmethod
    async def send_log(action_id, guild, embed):
        embed.set_footer(text=f'ID: {action_id}')
        log_channel = [channel for channel in guild.channels if "наказани" in channel.name][0]
        await log_channel.send(embed=embed)
