import os
from dotenv import load_dotenv
from nextcord.ext import commands
from utils.classes.bot import EsBot
import vk_api

load_dotenv()
vk_bot = vk_api.VkApi(token=os.getenv('VK_TOKEN'))
session_api = vk_bot.get_api()


class Vkontakte(commands.Cog):  # VK API
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot

    async def send_message(self, message, chat_id: 413):  # 413 test conferenciya
        if chat_id == 413:
            return vk_bot.method('messages.send',
                                 {'user_id': 239759093,
                                  'message': 'Ошибка конференции:\n\n' + message,
                                  'random_id': 0,
                                  'peer_id': 239759093})
        vk_bot.method('messages.send', {'chat_id': chat_id,
                                        'message': message,
                                        'random_id': 0})


def setup(bot: EsBot) -> None:
    bot.add_cog(Vkontakte(bot))
