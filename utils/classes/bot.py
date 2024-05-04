import re

import nextcord
from nextcord import Intents
from nextcord.ext import commands

from database import Database
from utils.roles.role_info import StartView, ReviewView


class EsBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix='MANSORY', intents=Intents.all())
        self.db = Database(self)
        self.is_view_initialised = False
        self.deleted_messages = []

    async def on_ready(self):
        if not self.is_view_initialised:
            self.is_view_initialised = True
            self.add_view(StartView(self.db.roles_handler))
            self.add_view(ReviewView(self.db.roles_handler))

        print(f'Logged in as {self.user} ({self.user.id})')
        print('------')

        # user = await self.fetch_user(479244541858152449)
        # dm = await user.create_dm()
        # async for message in dm.history(limit=None):
        #     if message.author.id == self.user.id:
        #         print('удалено')
        #         await message.delete()

    async def resolve_user(self, user_str, guild=None):
        try:
            if user_id := re.findall(r'<?@?!?(\d{18,20})>?', user_str):
                if guild and (user := guild.get_member(int(user_id[0]))):
                    return user
                if user := self.get_user(int(user_id[0])):
                    return user
                elif user := await self.fetch_user(int(user_id[0])):
                    return user
            elif username := re.findall(r'(.*)#(\d{4}|0)', user_str):
                if user := nextcord.utils.get(self.get_all_members(), name=username[0][0],
                                              discriminator=int(username[0][1])):
                    return user
        except:
            return None
