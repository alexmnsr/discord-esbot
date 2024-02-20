import os
import disnake
from bot import YourBot

intents = disnake.Intents.default().all()
bot = YourBot(command_prefix='/', help_command=None, intents=intents)

bot.run(os.getenv("TOKEN_BOT"))
