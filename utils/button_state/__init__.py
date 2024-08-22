import datetime

import nextcord

from utils.neccessary import get_class_from_file


class ButtonState:
    def __init__(self, client, global_db, mongodb):
        self.client = client
        self.global_db = global_db
        self.db_roles = mongodb['Roles']
        self.db_punishments = mongodb['Punishments']
        self.db_online = mongodb['Online']

    async def add_button(self, datebase, *, message_id, channel_id, user_request=None, moderator_id=None, guild_id=None,
                         class_method=None,
                         params=None):
        if datebase == "Roles":
            db = self.db_roles
        elif datebase == "Punishments":
            db = self.db_punishments
        elif datebase == "Online":
            db = self.db_online
        button_id = await db.insert_one({
            'message_id': message_id,
            'channel_id': channel_id,
            'user_request': user_request,
            'moderator_id': moderator_id,
            'guild_id': guild_id,
            'class_method': class_method,
            'params': params,
            'type_button': datebase,
            'check': False,
            'date': f'{datetime.datetime.now().strftime("%d.%m.%Y")}'
        })
        return button_id.inserted_id

    async def remove_button(self, datebase, *, channel_id, message_id, guild_id, id_button=None):
        if datebase == "Roles":
            db = self.db_roles
        elif datebase == "Punishments":
            db = self.db_punishments
        else:
            db = self.db_online
        filter = {
            'message_id': message_id,
            'channel_id': channel_id,
            'guild_id': guild_id
        } if id_button is None else {'id_button': id_button}

        existing_document = await db.find_one(filter)
        if not existing_document:
            print("Document not found with the given filter")
            return None

        result = await db.delete_one({'_id': existing_document['_id']})

        return result

    async def remove_old_buttons(self, db, days=3):
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        cutoff_date_str = cutoff_date.strftime("%d.%m.%Y")
        result = await db.delete_many({'date': {'$lt': cutoff_date_str}})
        print(f"Deleted {result.deleted_count} old buttons.")

    async def remove_all_buttons_server(self, guild_id):
        databases = {
            "Roles": self.db_roles,
            "Punishments": self.db_punishments,
            "Online": self.db_online
        }
        for db_name, db in databases.items():
            await db.delete_many({'guild_id': guild_id})

    async def get_button(self, datebase=None, user_request=None, moderator_id=None, guild_id=None, id_button=None):
        databases = {
            "Roles": self.db_roles,
            "Punishments": self.db_punishments,
            "Online": self.db_online
        }

        if id_button is not None:
            for db_name, db in databases.items():
                existing_document = await db.find_one({'message_id': id_button, 'guild_id': guild_id})
                if existing_document:
                    return existing_document
            print("Document not found with the given id_button across all databases")
            return None

        db = databases.get(datebase)
        if not db:
            print("Invalid database specified")
            return None

        filter = {
            'user_request': user_request,
            'moderator_id': moderator_id,
            'guild_id': guild_id
        }

        existing_document = await db.find_one(filter)
        if not existing_document:
            print("Document not found with the given filter")
            return None
        return existing_document

    async def update_button(self, module, message_id: int, channel_id: int, class_name, params):
        module_name = f'utils.button_state.views.{module}'
        selected_class = await get_class_from_file(module_name, class_name)

        if not selected_class:
            return

        view = selected_class(**params)

        channel = self.client.get_channel(channel_id)
        if channel:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(view=view)
                print("Кнопка успешно обновлена.")
            except nextcord.NotFound:
                print("Сообщение не найдено.")
            except nextcord.Forbidden:
                print("Нет прав на редактирование этого сообщения.")
            except Exception as e:
                print(f"Произошла ошибка: {e}")
        else:
            print("Канал не найден.")

    async def load_all_buttons(self):
        await self.remove_old_buttons(self.db_roles)
        await self.remove_old_buttons(self.db_punishments)
        await self.remove_old_buttons(self.db_online)

        all_buttons = {
            'Roles': await self.db_roles.find().to_list(length=None),
            'Punishments': await self.db_punishments.find().to_list(length=None),
            'Online': await self.db_online.find().to_list(length=None)
        }

        return all_buttons
