import logging
from disnake.ext import commands
from commands.online_users import OnlineCog
from events.events_voice import EventCog

class YourBot(commands.Bot):
    debug = False
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
                        filename='logging.log' if not debug else None)
    logger = logging.getLogger(__name__)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_cog(OnlineCog(self))
        self.add_cog(EventCog(self))
