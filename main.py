import os
import disnake
from bot import YourBot

intents = disnake.Intents.default().all()
debug = os.getenv('DEBUG')
if debug:
    bot = YourBot(command_prefix='/', help_command=None, intents=intents)
    bot.run(os.getenv("LOCAL_TOKEN"))
else:
    bot = YourBot(command_prefix='/', help_command=None, intents=intents)
    bot.run(os.getenv("TOKEN_BOT"))
