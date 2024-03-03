import re

import nextcord
from nextcord import Intents
from nextcord.ext import commands

from database import Database


class EsBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix='!', intents=Intents.all())
        self.db = Database(self)

    async def on_ready(self):
        print(f'Logged in as {self.user} ({self.user.id})')
        print('------')

    async def resolve_user(self, user_str):
        try:
            if user_id := re.findall(r'<?@?!?(\d{18,20})>?', user_str):
                if user := self.get_user(user_id[0]):
                    return user
                elif user := await self.fetch_user(user_id[0]):
                    return user
            elif username := re.findall(r'(.*)#(\d{4}|0)', user_str):
                if user := nextcord.utils.get(self.get_all_members(), name=username[0][0],
                                              discriminator=int(username[0][1])):
                    return user
        except:
            return None
