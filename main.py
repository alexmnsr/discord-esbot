import os
from loguru import logger
from dotenv import load_dotenv
from utils.classes.bot import EsBot
from utils.crons.cron_stats import CRON_Stats

load_dotenv()
logger.disable("vkbottle")

bot = EsBot()

# Загружаем cogs
for root, _, files in os.walk('cogs'):
    for filename in files:
        if filename.endswith('.py'):
            relative_path = os.path.relpath(os.path.join(root, filename), 'cogs')
            module = relative_path.replace(os.path.sep, '.').replace('.py', '')
            bot.load_extension(f'cogs.{module}')

cron_stats = CRON_Stats(bot)

start = os.getenv('LOCAL_TOKEN') if os.getenv('DEBUG') == 'True' else os.getenv('TOKEN_BOT')
bot.run(start)
