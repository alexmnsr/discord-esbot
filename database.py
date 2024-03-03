from motor.motor_asyncio import AsyncIOMotorClient

import config
from utils.classes.actions import Actions
from utils.online.online import OnlineHandler
from utils.punishments.punishments import PunishmentsHandler


class Database:
    def __init__(self, bot):
        self.client = AsyncIOMotorClient(config.mongo)
        self.actions = Actions(self.client['Actions'])
        self.online_handler = OnlineHandler(self.client['Online'])
        self.punishments_handler = PunishmentsHandler(bot, self, self.client['Punishments'])
