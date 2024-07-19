import os
from dotenv import load_dotenv
from nextcord.ext import commands
from utils.classes.bot import EsBot
import vk_api

load_dotenv()
vk_bot = vk_api.VkApi(token=os.getenv('VK_TOKEN'))
session_api = vk_bot.get_api()

# Список серверов (413 = test конференция)
chat_ids = {
    611264224391331911: 413,
    2: 413,
    3: 413,
    4: 413,
    506143782509740052: 411,
    595710119967195150: 413,
    607244699731886110: 413,
    612650423387553814: 413,
    650711938648506370: 408,
    679781601202536458: 413,
    694982589664067685: 413,
    697481284905205800: 413,
    773905724056928276: 413,
    14: 413,
    898582894338002994: 404,
    992142629213061220: 413,
    992143605105967165: 413,
    18: 413,
    19: 413,
    992144732434210937: 413,
    1170024698487246909: 413,
}


class Vkontakte(commands.Cog):  # VK API
    def __init__(self, bot: EsBot) -> None:
        self.bot = bot

    async def send_message(self, server_id, message):  # 413 test conferenciya
        chat_id = chat_ids.get(server_id, 413)
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
