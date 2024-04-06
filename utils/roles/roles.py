import re

from motor.core import AgnosticCollection

nickname_regex = re.compile(r'^[A-Z][a-z]+(?:_[A-Z][a-z]+)?_[A-Z][a-z]+$')


class RolesHandler:
    def __init__(self, client, global_db, mongodb: AgnosticCollection) -> None:
        self.client = client
        self.mongo = mongodb["Requests"]

    @staticmethod
    def check_nickname(nickname):
        return nickname_regex.match(nickname)

    async def request_role(self, user, guild):
        info = {"user": user.id, "guild": guild.id}

        if await self.mongo.count_documents(info):
            return False

        await self.mongo.insert_one(info)
        return True

    async def remove_request(self, user, guild):
        info = {"user": user.id, "guild": guild.id}
        if not await self.mongo.count_documents(info):
            return False

        await self.mongo.delete_one(info)
        return True
