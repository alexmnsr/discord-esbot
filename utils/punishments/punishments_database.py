import datetime

import nextcord
from bson import ObjectId
from motor import motor_asyncio

from utils.classes.actions import ActionType


class PunishmentsDatabase:
    def __init__(self, client, global_db, db: motor_asyncio.AsyncIOMotorDatabase):
        self.client = client
        self.db = db
        self.mutes = self.db['mutes']
        self.bans = self.db['bans']
        self.warns = self.db['warns']
        self.block_channel = self.db['block_channels']
        self.actions = global_db.actions

    async def get_mutes(self, user_id=None, guild_id=None):
        query = {}
        if user_id:
            query['user_id'] = user_id
        if guild_id:
            query['guild_id'] = guild_id
        return await self.mutes.find(query).to_list(length=None)

    async def get_bans(self, user_id=None, guild_id=None):
        query = {}
        if user_id:
            query['user_id'] = user_id
        if guild_id:
            query['guild_id'] = guild_id
        return await self.bans.find(query).to_list(length=None)

    async def get_warns(self, user_id=None, guild_id=None):
        query = {}
        if user_id:
            query['user_id'] = user_id
        if guild_id:
            query['guild_id'] = guild_id
        return await self.warns.find(query).to_list(length=None)

    async def get_text_mute(self, *, user_id=None, guild_id=None, action_id=None):
        return await self.mutes.find_one({
                                             'user_id': user_id,
                                             'guild_id': guild_id,
                                             'type': "text"
                                         } if not action_id else {'_id': ObjectId(action_id)})

    async def get_voice_mute(self, *, user_id=None, guild_id=None, action_id=None):
        return await self.mutes.find_one({
                                             'user_id': user_id,
                                             'guild_id': guild_id,
                                             'type': "voice"
                                         } if not action_id else {'_id': ObjectId(action_id)})

    async def get_full_mute(self, *, user_id=None, guild_id=None, action_id=None):
        return await self.mutes.find_one({
                                             'user_id': user_id,
                                             'guild_id': guild_id,
                                             'type': "full"
                                         } if not action_id else {'_id': ObjectId(action_id)})

    async def give_mute(self, user_id, guild_id, moderator_id, reason, duration, mute_type, *, jump_url):
        if isinstance(user_id, nextcord.user.User):
            user_id = user_id['id']
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=mute_type,
            payload={
                'reason': reason,
                'duration': duration,
                'jump_url': jump_url
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
            'jump_url': jump_url
        })
        return action_id

    async def give_text_mute(self, user_id, guild_id, moderator_id, reason, duration, jump_url):
        return await self.give_mute(user_id, guild_id, moderator_id, reason, duration, ActionType.MUTE_TEXT,
                                    jump_url=jump_url)

    async def give_voice_mute(self, user_id, guild_id, moderator_id, reason, duration, jump_url):
        return await self.give_mute(user_id, guild_id, moderator_id, reason, duration, ActionType.MUTE_VOICE,
                                    jump_url=jump_url)

    async def give_full_mute(self, user_id, guild_id, moderator_id, reason, duration, jump_url):
        return await self.give_mute(user_id, guild_id, moderator_id, reason, duration, ActionType.MUTE_FULL,
                                    jump_url=jump_url)

    async def remove_mute(self, user_id, guild_id, mute_type, moderator=None):
        await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator.id,
            action_type=ActionType.UNMUTE_LOCAL,
            payload={

            }
        )
        return (await self.mutes.delete_one({
            'user_id': user_id,
            'guild_id': guild_id,
            'type': mute_type.name.split('_')[1].lower()
        })).deleted_count == 1

    async def cancel(self, user_id, guild_id, moderator_id):
        if isinstance(moderator_id, nextcord.Member):
            moderator_id = moderator_id.id
        await self.actions.delete_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id
        )
        await self.actions.add_action(
            user_id=None,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=ActionType.RECHECKING_CANCEL,
            payload={
            }
        )
        return True

    async def remove_text_mute(self, user_id, guild_id, moderator=0):
        return await self.remove_mute(user_id, guild_id, ActionType.MUTE_TEXT, moderator=moderator)

    async def remove_voice_mute(self, user_id, guild_id, moderator=0):
        return await self.remove_mute(user_id, guild_id, ActionType.MUTE_VOICE, moderator=moderator)

    async def remove_full_mute(self, user_id, guild_id, moderator=0):
        return await self.remove_mute(user_id, guild_id, ActionType.MUTE_FULL, moderator=moderator)

    async def give_warn(self, user_id, guild_id, moderator_id, reason, warn_type, approve_moderator=None, *, jump_url):
        if isinstance(user_id, nextcord.user.User):
            user_id = user_id['id']
        if approve_moderator is not None:
            await self.actions.add_action(
                user_id=user_id,
                guild_id=guild_id,
                moderator_id=approve_moderator,
                action_type=ActionType.APPROVE_WARN,
                payload={
                    'jump_url': jump_url
                }
            )
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=warn_type,
            payload={
                'reason': reason,
                'jump_url': jump_url
            }
        )
        await self.warns.insert_one({
            'user_id': user_id,
            'guild_id': guild_id,
            'moderator_id': moderator_id,
            'reason': reason,
            'given_at': datetime.datetime.now(),
            'type': str(warn_type)
        })
        return action_id

    async def get_warn(self, *, action_id=None):
        try:
            if isinstance(action_id, str) and len(action_id) == 24:
                action_id = ObjectId(action_id)
            elif isinstance(action_id, str):
                action_id = int(action_id)
            print(action_id)
            return await self.warns.find_one({'_id': action_id})
        except:
            print(f"Invalid action_id format")
            return None

    async def remove_warn(self, *, user_id=None, guild_id=None, moderator=None, action_id=None):
        await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator.id,
            action_type=ActionType.UNWARN_LOCAL,
            payload={

            }
        )
        return await self.warns.delete_one({
                                               'user_id': user_id,
                                               'guild_id': guild_id
                                           } if not action_id else {'_id': ObjectId(action_id)})

    async def remove_warns(self, *, user_id=None, guild_id=None):
        return await self.warns.delete_many({
            'user_id': user_id,
            'guild_id': guild_id
        })

    async def give_ban(self, user_id, guild_id, moderator_id, reason, duration, ban_type, *, approve_moderator=None,
                       jump_url):
        if isinstance(user_id, nextcord.user.User):
            user_id = user_id['id']
        if approve_moderator is not None:
            await self.actions.add_action(
                user_id=user_id,
                guild_id=guild_id,
                moderator_id=approve_moderator,
                action_type=ActionType.APPROVE_BAN,
                payload={
                    'jump_url': jump_url
                }
            )
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            approve_punishment=approve_moderator,
            action_type=ban_type,
            payload={
                'reason': reason,
                'duration': duration,
                'jump_url': jump_url
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
            'jump_url': jump_url
        })
        return action_id

    async def get_ban(self, *, user_id=None, guild_id=None, action_id=None):
        return await self.bans.find_one({
                                            'user_id': user_id,
                                            'guild_id': guild_id
                                        } if not action_id else {'_id': ObjectId(action_id)})

    async def remove_ban(self, *, user_id=None, guild_id=None, action_id=None, moderator_id=None, type_ban=None):
        await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=ActionType.UNBAN_LOCAL,
            payload={
                'reason': 'end time punishment'
            }
        )
        return await self.bans.delete_one({
                                              'user_id': user_id,
                                              'guild_id': guild_id
                                          } if not action_id else {'_id': ObjectId(action_id)})

    async def give_block_channel(self, user_id, guild_id, moderator_id, reason, duration, category):
        action_id = await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=ActionType.BLOCK_CHANNEL,
            payload={
                'reason': reason,
                'duration': duration,
                'category': category
            }
        )

        await self.block_channel.insert_one({
            'user_id': user_id,
            'guild_id': guild_id,
            'moderator_id': moderator_id,
            'reason': reason,
            'duration': duration,
            'given_at': datetime.datetime.now(),
            'type': ActionType.BLOCK_CHANNEL.name.split('_')[1].lower(),
            'category': category
        })
        return action_id

    async def remove_block_channel(self, *, user_id=None, guild_id=None, action_id=None, moderator_id=None):
        await self.actions.add_action(
            user_id=user_id,
            guild_id=guild_id,
            moderator_id=moderator_id,
            action_type=ActionType.REMOVE_BLOCKCHANNEL,
            payload={
                'time': 'end time punishment'
            }
        )
        return await self.block_channel.delete_one({
                                                       'user_id': user_id,
                                                       'guild_id': guild_id
                                                   } if not action_id else {'_id': ObjectId(action_id)})
