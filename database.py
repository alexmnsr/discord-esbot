import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

from utils.button_state import ButtonState
from utils.classes.actions import Actions
from utils.online.online import OnlineHandler
from utils.punishments.punishments import PunishmentsHandler
from utils.roles.roles import RolesHandler

load_dotenv()


class Database:
    def __init__(self, bot):
        self.client = AsyncIOMotorClient(os.getenv('MONGO_DB'))
        self.actions = Actions(self.client['Actions'])
        self.state_buttons = ButtonState(bot, self, self.client['Buttons'])
        self.online_handler = OnlineHandler(bot, self.client['Online'], self.state_buttons)
        self.punishments_handler = PunishmentsHandler(bot, self, self.client['Punishments'], self.state_buttons)
        self.roles_handler = RolesHandler(bot, self, self.client['Roles'], self.client['Buttons'])
