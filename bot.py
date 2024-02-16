from disnake.ext import commands
from commands.online_users import OnlineCog
from events.events_voice import EventCog


class YourBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_cog(OnlineCog(self))
        self.add_cog(EventCog(self))
