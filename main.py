import os

import config
from utils.classes.bot import EsBot
from dotenv import load_dotenv

load_dotenv()

bot = EsBot()

for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

start = os.getenv('LOCAL_TOKEN') if os.getenv('DEBUG') == 'True' else os.getenv('TOKEN_BOT')

bot.run(start)
