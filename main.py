import os

from dotenv import load_dotenv

from utils.classes.bot import EsBot

load_dotenv()

bot = EsBot()

for root, _, files in os.walk('cogs'):
    for filename in files:
        if filename.endswith('.py'):
            # Получаем относительный путь и преобразуем его в формат cogs.subdir.module
            relative_path = os.path.relpath(os.path.join(root, filename), 'cogs')
            module = relative_path.replace(os.path.sep, '.').replace('.py', '')
            bot.load_extension(f'cogs.{module}')

start = os.getenv('LOCAL_TOKEN') if os.getenv('DEBUG') == 'True' else os.getenv('TOKEN_BOT')

bot.run(start)
