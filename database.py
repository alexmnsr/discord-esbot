import os

from motor.motor_asyncio import AsyncIOMotorClient

from utils.classes.actions import Actions
from utils.online.online import OnlineHandler
from utils.punishments.punishments import PunishmentsHandler
from utils.roles.roles import RolesHandler

from dotenv import load_dotenv

load_dotenv()


class Database:
    def __init__(self, bot):
        self.client = AsyncIOMotorClient(os.getenv('MONGO_DB'))
        self.actions = Actions(self.client['Actions'])
        self.online_handler = OnlineHandler(self.client['Online'])
        self.punishments_handler = PunishmentsHandler(bot, self, self.client['Punishments'])
        self.roles_handler = RolesHandler(bot, self, self.client['Roles'])
