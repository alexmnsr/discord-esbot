import datetime
import asyncio
import nextcord
import logging
from utils.neccessary import get_class_from_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ButtonState:
    def __init__(self, client, global_db, mongodb):
        self.client = client
        self.global_db = global_db
        self.db_map = {
            "Roles": mongodb['Roles'],
            "Punishments": mongodb['Punishments'],
            "Online": mongodb['Online']
        }

    async def add_button(self, datebase, **kwargs):
        db = self.db_map.get(datebase)
        if db is None:  # Исправленная проверка
            raise ValueError(f"Invalid database specified: {datebase}")

        button_id = await db.insert_one({
            'message_id': kwargs.get('message_id'),
            'channel_id': kwargs.get('channel_id'),
            'user_request': kwargs.get('user_request'),
            'moderator_id': kwargs.get('moderator_id'),
            'guild_id': kwargs.get('guild_id'),
            'class_method': kwargs.get('class_method'),
            'params': kwargs.get('params'),
            'type_button': datebase,
            'check': False,
            'date': datetime.datetime.now().strftime("%d.%m.%Y")
        })
        return button_id.inserted_id

    async def remove_button(self, datebase, *, channel_id, message_id, guild_id, id_button=None):
        db = self.db_map.get(datebase)
        if not db:
            raise ValueError(f"Invalid database specified: {datebase}")

        filter = {'message_id': message_id, 'channel_id': channel_id, 'guild_id': guild_id}
        if id_button is not None:
            filter['id_button'] = id_button

        existing_document = await db.find_one(filter)
        if not existing_document:
            logger.warning("Document not found with the given filter")
            return None

        result = await db.delete_one({'_id': existing_document['_id']})
        return result

    async def remove_old_buttons(self, db, days=3):
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        cutoff_date_str = cutoff_date.strftime("%d.%m.%Y")
        result = await db.delete_many({'date': {'$lt': cutoff_date_str}})
        logger.info(f"Deleted {result.deleted_count} old buttons.")

    async def remove_all_buttons_server(self, guild_id):
        tasks = [
            db.delete_many({'guild_id': guild_id}) for db in self.db_map.values()
        ]
        await asyncio.gather(*tasks)

    async def get_button(self, datebase=None, user_request=None, moderator_id=None, guild_id=None, id_button=None):
        if id_button is not None:
            for db_name, db in self.db_map.items():
                existing_document = await db.find_one({'message_id': id_button, 'guild_id': guild_id})
                if existing_document:
                    return existing_document
            logger.warning("Document not found with the given id_button across all databases")
            return None

        db = self.db_map.get(datebase)
        if not db:
            logger.warning("Invalid database specified")
            return None

        filter = {'user_request': user_request, 'moderator_id': moderator_id, 'guild_id': guild_id}
        existing_document = await db.find_one(filter)
        if not existing_document:
            logger.warning("Document not found with the given filter")
            return None
        return existing_document

    async def update_button(self, module, message_id: int, channel_id: int, class_name, params):
        module_name = f'utils.button_state.views.{module}'
        selected_class = await get_class_from_file(module_name, class_name)

        if not selected_class:
            logger.error(f"Class {class_name} not found in module {module_name}")
            return

        view = selected_class(**params)

        channel = self.client.get_channel(channel_id)
        if channel:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(view=view)
                logger.info("Button successfully updated.")
            except nextcord.NotFound:
                logger.warning("Message not found.")
            except nextcord.Forbidden:
                logger.warning("No permission to edit this message.")
            except Exception as e:
                logger.error(f"An error occurred: {e}")
        else:
            logger.warning("Channel not found.")

    async def load_all_buttons(self):
        tasks = [
            self.remove_old_buttons(self.db_map['Roles']),
            self.remove_old_buttons(self.db_map['Punishments']),
            self.remove_old_buttons(self.db_map['Online'])
        ]
        await asyncio.gather(*tasks)

        all_buttons = {
            'Roles': await self.db_map['Roles'].find().to_list(length=None),
            'Punishments': await self.db_map['Punishments'].find().to_list(length=None),
            'Online': await self.db_map['Online'].find().to_list(length=None)
        }

        return all_buttons
