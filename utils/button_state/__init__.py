class ButtonState:
    def __init__(self, client, global_db, mongodb):
        self.client = client
        self.global_db = global_db
        self.db_roles = mongodb['Roles']
        self.db_punishments = mongodb['Punishments']
        self.db_online = mongodb['Online']

    async def add_button(self, datebase, *, message_id, channel_id, user_request=None, moderator_id=None, guild_id=None, class_method=None,
                         params=None):
        if datebase == "Roles":
            db = self.db_roles
        elif datebase == "Punishments":
            db = self.db_punishments
        else:
            db = self.db_online
        button_id = await db.insert_one({
            'message_id': message_id,
            'channel_id': channel_id,
            'user_request': user_request,
            'moderator_id': moderator_id,
            'guild_id': guild_id,
            'class_method': class_method,
            'params': params,
            'check': False
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

    async def get_button(self, datebase, *, user_request, moderator_id, guild_id, id_button=None):
        if datebase == "Roles":
            db = self.db_roles
        elif datebase == "Punishments":
            db = self.db_punishments
        else:
            db = self.db_online
        filter = {
            'user_request': user_request,
            'moderator_id': moderator_id,
            'guild_id': guild_id
        } if id_button is None else {'id_button': id_button}

        existing_document = await db.find_one(filter)
        if not existing_document:
            print("Document not found with the given filter")
            return None
        return existing_document

    async def load_all_buttons(self):
        all_buttons = {
            'Roles': [],
            'Punishments': [],
            'Online': []
        }

        roles_buttons = await self.db_roles.find().to_list(length=None)
        punishments_buttons = await self.db_punishments.find().to_list(length=None)
        online_buttons = await self.db_online.find().to_list(length=None)

        all_buttons['Roles'].extend(roles_buttons)
        all_buttons['Punishments'].extend(punishments_buttons)
        all_buttons['Online'].extend(online_buttons)

        return all_buttons
