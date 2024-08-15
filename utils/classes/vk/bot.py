import logging
import os

from vkbottle.bot import Bot

logging.basicConfig(level=logging.INFO)
logging.getLogger('vkbottle').setLevel(logging.INFO)

chat_ids = {
    611264224391331911: 421,
    2: 413,
    3: 413,
    4: 413,
    506143782509740052: 411,
    595710119967195150: 417,
    607244699731886110: 413,
    612650423387553814: 413,
    650711938648506370: 408,
    679781601202536458: 418,
    694982589664067685: 413,
    697481284905205800: 413,
    773905724056928276: 413,
    14: 413,
    898582894338002994: 404,
    992142629213061220: 420,
    992143605105967165: 422,
    18: 413,
    19: 413,
    992144732434210937: 413,
    1170024698487246909: 419,
}


class VKBot:
    def __init__(self) -> None:
        self.bot = Bot(os.getenv('VK_TOKEN'))
        self.api = self.bot.api

    async def send_message(self, server_id: int, message: str):
        chat_id = chat_ids.get(server_id, 413)

        if chat_id == 413:
            return await self.api.messages.send(user_id=239759093,
                                                peer_id=239759093,
                                                message=message,
                                                random_id=0)

        await self.api.messages.send(chat_id=chat_id,
                                     message=message,
                                     random_id=0)

    async def private_send_message(self, id_user: int, message: str):
        return await self.api.messages.send(user_id=id_user,
                                            peer_id=id_user,
                                            message=message,
                                            random_id=0)
