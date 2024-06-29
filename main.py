import os

from dotenv import load_dotenv

from utils.classes.bot import EsBo1t

load_dotenv()

bot = EsBot()

directory = '/bots/discord-esbot/cogs' if os.getenv('DEBUG') == 'False' else 'cogs'

for filename in os.listdir(directory):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

start = os.getenv('LOCAL_TOKEN') if os.getenv('DEBUG') == 'True' else os.getenv('TOKEN_BOT')

bot.run(start)
