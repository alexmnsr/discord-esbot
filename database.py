from motor.motor_asyncio import AsyncIOMotorClient

import config
from utils.online import OnlineHandler


class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(config.mongo)
        self.online_handler = OnlineHandler(self.client['TestRadmir'])
