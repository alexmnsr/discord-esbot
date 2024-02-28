import logging
import os

from disnake.ext import commands
from commands.online_users import OnlineCog
from commands.get_info_moderate import GetInfoCog
from events.events_voice import EventCog


class YourBot(commands.Bot):
    debug = os.getenv('DEBUG')
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
                        filename='logging.log' if debug == 'False' else None)
    logger = logging.getLogger(__name__)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_cog(OnlineCog(self))
        self.add_cog(EventCog(self))
        self.add_cog(GetInfoCog(self))
