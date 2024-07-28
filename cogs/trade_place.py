from nextcord.ext import commands

from utils.classes.bot import EsBot


class TradePlace(commands.Cog):
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot


def setup(bot: EsBot) -> None:
    bot.add_cog(TradePlace(bot))
