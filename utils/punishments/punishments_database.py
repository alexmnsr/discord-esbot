import datetime

from motor import motor_asyncio

from utils.classes.actions import ActionType


class PunishmentsDatabase:
    def __init__(self, client, global_db, db: motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.mutes = self.db['mutes']
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

    async def give_text_mute(self, user_id, guild_id, moderator_id, reason, duration):
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=str(ActionType.MUTE_TEXT),
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
            'type': 'text',
            'action_id': action_id
        })
        return action_id

    async def give_voice_mute(self, user_id, guild_id, moderator_id, reason, duration):
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=str(ActionType.MUTE_VOICE),
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
            'type': 'voice',
            'action_id': action_id
        })
        return action_id

    async def give_full_mute(self, user_id, guild_id, moderator_id, reason, duration):
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=str(ActionType.MUTE_FULL),
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
            'type': 'full',
            'action_id': action_id
        })
        return action_id

    async def remove_text_mute(self, user_id, guild_id):
        return (await self.mutes.delete_one({
                'user_id': user_id,
                'guild_id': guild_id,
                'type': 'text'
             })).deleted_count == 1

    async def remove_voice_mute(self, user_id, guild_id):
        return (await self.mutes.delete_one({
                'user_id': user_id,
                'guild_id': guild_id,
                'type': 'voice'
             })).deleted_count == 1

    async def remove_full_mute(self, user_id, guild_id):
        await self.remove_voice_mute(user_id, guild_id)
        await self.remove_text_mute(user_id, guild_id)
