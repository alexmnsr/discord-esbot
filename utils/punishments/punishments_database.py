import datetime

from motor import motor_asyncio

from utils.classes.actions import ActionType


class PunishmentsDatabase:
    def __init__(self, client, global_db, db: motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.mutes = self.db['mutes']
        self.bans = self.db['bans']
        self.actions = global_db.actions

    async def get_mutes(self):
        return await self.mutes.find({}).to_list(length=None)

    async def get_text_mute(self, *, user_id=None, guild_id=None, action_id=None):
        return await self.mutes.find_one({
                                             'user_id': user_id,
                                             'guild_id': guild_id,
                                             'type': 'text'
                                         } if not action_id else {'action_id': action_id})

    async def get_voice_mute(self, *, user_id=None, guild_id=None, action_id=None):
        return await self.mutes.find_one({
                                             'user_id': user_id,
                                             'guild_id': guild_id,
                                             'type': 'voice'
                                         } if not action_id else {'action_id': action_id})

    async def get_full_mute(self, *, user_id=None, guild_id=None, action_id=None):
        return await self.mutes.find_one({
                                             'user_id': user_id,
                                             'guild_id': guild_id,
                                             'type': 'full'
                                         } if not action_id else {'action_id': action_id})

    async def give_mute(self, user_id, guild_id, moderator_id, reason, duration, mute_type):
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=str(mute_type),
            payload={
                'reason': reason,
                'duration': duration
            }
        )

        await self.mutes.insert_one({
            'user_id': user_id,
            'guild_id': guild_id,
            'moderator_id': moderator_id,
            'reason': reason,
            'duration': duration,
            'given_at': datetime.datetime.now(),
            'type': mute_type.name.split('_')[1].lower(),
            'action_id': action_id
        })
        return action_id

    async def give_text_mute(self, user_id, guild_id, moderator_id, reason, duration):
        return await self.give_mute(user_id, guild_id, moderator_id, reason, duration, ActionType.MUTE_TEXT)

    async def give_voice_mute(self, user_id, guild_id, moderator_id, reason, duration):
        return await self.give_mute(user_id, guild_id, moderator_id, reason, duration, ActionType.MUTE_VOICE)

    async def give_full_mute(self, user_id, guild_id, moderator_id, reason, duration):
        return await self.give_mute(user_id, guild_id, moderator_id, reason, duration, ActionType.MUTE_FULL)

    async def remove_mute(self, user_id, guild_id, mute_type):
        return (await self.mutes.delete_one({
            'user_id': user_id,
            'guild_id': guild_id,
            'type': mute_type.name.split('_')[1].lower()
        })).deleted_count == 1

    async def remove_text_mute(self, user_id, guild_id):
        return await self.remove_mute(user_id, guild_id, ActionType.MUTE_TEXT)

    async def remove_voice_mute(self, user_id, guild_id):
        return await self.remove_mute(user_id, guild_id, ActionType.MUTE_VOICE)

    async def remove_full_mute(self, user_id, guild_id):
        return await self.remove_mute(user_id, guild_id, ActionType.MUTE_FULL)

    async def give_ban(self, user_id, guild_id, moderator_id, reason, duration, ban_type):
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=str(ban_type),
            payload={
                'reason': reason,
                'duration': duration
            }
        )

        await self.bans.insert_one({
            'user_id': user_id,
            'guild_id': guild_id,
            'moderator_id': moderator_id,
            'reason': reason,
            'duration': duration,
            'given_at': datetime.datetime.now(),
            'type': ban_type.name.split('_')[1].lower(),
            'action_id': action_id
        })
        return action_id

    async def get_ban(self, *, user_id=None, guild_id=None, action_id=None, type_ban=None):
        return await self.bans.find_one({
                                            'user_id': user_id,
                                            'guild_id': guild_id,
                                            'type': type_ban
                                        } if not action_id else {'action_id': action_id})

    async def remove_ban(self, *, user_id=None, guild_id=None, action_id=None, type_ban=None):
        return await self.bans.delete_one({
                                              'user_id': user_id,
                                              'guild_id': guild_id,
                                              'type': type_ban
                                          } if not action_id else {'action_id': action_id})
