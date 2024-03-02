import datetime
from typing import Any

import nextcord
from nextcord.ext import commands

from utils.neccessary import is_date_valid, date_autocomplete
from utils.online import OnlineHandler


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Stats(bot))
