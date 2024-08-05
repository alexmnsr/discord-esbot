import datetime
import re

import nextcord
from motor.core import AgnosticCollection

from utils.classes.actions import ActionType

nickname_regex = re.compile(r'^[A-Z][a-z]+(?:_[A-Z][a-z]+)?_[A-Z][a-z]+$')


class RolesHandler:
    def __init__(self, client, global_db, mongodb: AgnosticCollection, buttons) -> None:
        self.client = client
        self.mongo = mongodb["Requests"]
        self.moder_mongo = mongodb["Review"]
        self.actions = global_db.actions
        self.db_buttons = buttons["Roles"]

    @staticmethod
    def check_nickname(nickname):
        return nickname_regex.match(nickname)

    async def request_role(self, user: nextcord.Member, guild: nextcord.Guild):
        info = {"user": user.id, "guild": guild.id}

        if await self.mongo.count_documents(info):
            return False

        await self.mongo.insert_one(info)

        return True

    async def cancel(self, action_id, moderator_id, guild_id):
        await self.actions.delete_action(
            action_id=action_id
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

    async def remove_request(self, user, guild, approve, cancel, *, moderator_id=None, role=None, rang=None, nick=None):
        action_id = None
        if not cancel:
            info = {"user": user.id, "guild": guild.id}
            if not await self.mongo.count_documents(info):
                return False

            await self.mongo.delete_one(info)

        if moderator_id:
            if cancel:
                return await self.actions.update_action(
                    user_id=user.id,
                    guild_id=guild.id,
                    moderator_id=moderator_id,
                    action_type=ActionType.RECHECKING_CANCEL,
                    payload={
                        'role': role,
                        'rang': rang,
                        'nick': nick
                    }
                )
            await self.moder_mongo.update_one(
                {'moder_id': moderator_id, 'guild': guild.id, 'date': datetime.datetime.now().strftime('%d.%m.%Y')},
                {'$push': {'roles_approved' if approve else 'roles_rejected': user.id}},
                upsert=True
            )

            action_id = await self.actions.add_action(
                user_id=user.id,
                guild_id=guild.id,
                moderator_id=moderator_id,
                action_type=ActionType.ROLE_APPROVE if approve else ActionType.ROLE_REJECT,
                payload={
                    'role': role,
                    'rang': rang,
                    'nick': nick
                }
            )

        return action_id
