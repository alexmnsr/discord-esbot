import os
import disnake
from bot import YourBot

bot = YourBot(command_prefix='/', help_command=None, intents=disnake.Intents.all())

bot.run(os.getenv("TOKEN_BOT"))
