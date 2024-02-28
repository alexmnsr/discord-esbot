import os
import disnake
from bot import YourBot

intents = disnake.Intents.default().all()
debug = os.getenv('DEBUG')
bot = YourBot(command_prefix='/', help_command=None, intents=intents)

if debug == 'True':
    start = os.getenv("LOCAL_TOKEN")
else:
    start = os.getenv("TOKEN_BOT")

bot.run(start)
