from nextcord.ext import commands


class Stats(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Stats(bot))
