import re

import nextcord
from nextcord import Intents
from nextcord.ext import commands

from database import Database
from utils.classes.vk.bot import VKBot, BotStatus


class EsBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix='MANSORY', intents=Intents.all())
        self.db = Database(self)
        self.vk = VKBot()
        self.buttons = self.db.state_buttons
        self.deleted_messages = []
        self.status_message = "Бот запущен ⚠"

    async def on_ready(self):
        await BotStatus(self.vk).send_status(message=self.status_message, status=BotStatus.WARNING)
        print(f'Бот загружен "{self.user}" (ID: {self.user.id})')
        print('------')

    async def on_application_command_error(self, interaction: nextcord.Interaction, error: nextcord.ApplicationError):
        if isinstance(error, nextcord.ApplicationCheckFailure):
            return
        raise error

    async def resolve_user(self, user_str, guild: nextcord.Guild = None):
        try:
            if isinstance(user_str, int):
                if guild and (user := await guild.fetch_member(user_str)):
                    return user
                if guild and (user := self.get_user(user_str)):
                    return user
            elif user_id := re.findall(r'<?@?!?(\d{18,20})>?', user_str):
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
        except Exception as e:
            await self.vk.nt_error(f'Получение пользователя resolved_user: {e}')
            return None
