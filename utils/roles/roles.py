import re

nickname_regex = re.compile(r'^[A-Z][a-z]+(?:_[A-Z][a-z]+)?_[A-Z][a-z]+$')


class RolesHandler:
    def __init__(self, client, global_db, mongodb) -> None:
        self.client = client

    @staticmethod
    def check_nickname(nickname):
        return nickname_regex.match(nickname)

    async def request_role(self, user, guild):
        ...
