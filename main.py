import os

import config
from utils.classes.bot import EsBot

bot = EsBot()

for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

bot.run(config.discord)
