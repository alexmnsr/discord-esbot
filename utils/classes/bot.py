from nextcord import Intents
from nextcord.ext import commands

from database import Database


class EsBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix='!', intents=Intents.all())
        self.db = Database()

    async def on_ready(self):
        print(f'Logged in as {self.user} ({self.user.id})')
        print('------')
