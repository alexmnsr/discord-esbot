import datetime
import enum

from motor import motor_asyncio


class ActionType(enum.Enum):
    APPROVE_BAN = 'approve_ban'
    APPROVE_WARN = 'approve_warn'
    UNMUTE_LOCAL = 'unmute_local'
    BAN_LOCAL = 'ban_local'
    BAN_GLOBAL = 'ban_global'
    UNBAN_LOCAL = 'unban_local'
    WARN_LOCAL = 'warn_local'
    UNWARN_LOCAL = 'unwarn_local'
    TIME_WARN = 'warn_time'
    MUTE_TEXT = 'mute_text'
    MUTE_VOICE = 'mute_voice'
    MUTE_FULL = 'mute_full'
    ROLE_APPROVE = 'role_approve'
    ROLE_REJECT = 'role_reject'
    ROLE_REMOVE = 'role_remove'
    ROLE_CANCEL = 'role_cancel'


human_actions = {
    ActionType.BAN_LOCAL.value: "Блокировка",
    ActionType.BAN_GLOBAL.value: "Глобальная блокировка",
    ActionType.UNBAN_LOCAL.value: "Снятие блокировки",
    ActionType.WARN_LOCAL.value: "Предупреждение",
    ActionType.UNWARN_LOCAL.value: "Снятие предупреждения",
    ActionType.TIME_WARN.value: "Временное предупреждение",
    ActionType.MUTE_TEXT.value: "Блокировка текстовых каналов",
    ActionType.MUTE_VOICE.value: "Блокировка голосовых каналов",
    ActionType.UNMUTE_LOCAL.value: "Снятие мута",
    ActionType.MUTE_FULL.value: "Полная блокировка каналов",
    ActionType.ROLE_APPROVE.value: "Одобрение роли",
    ActionType.ROLE_REJECT.value: "Отклонение роли",
    ActionType.ROLE_REMOVE.value: "Снятие роли",
    ActionType.ROLE_CANCEL.value: "Перепроверка роли"
}

moder_actions = {
    ActionType.BAN_LOCAL.value: "Блокировки",
    ActionType.APPROVE_BAN.value: "Подтверждение блокировки",
    ActionType.BAN_GLOBAL.value: "G-блокировки",
    ActionType.UNBAN_LOCAL.value: "Снятие блокировки",
    ActionType.WARN_LOCAL.value: "Варны",
    ActionType.APPROVE_WARN.value: "Подтвержденые варны",
    ActionType.UNWARN_LOCAL.value: "Снятие варна",
    ActionType.TIME_WARN.value: "Врем.преды",
    ActionType.MUTE_TEXT.value: "Текст-муты",
    ActionType.MUTE_VOICE.value: "Войс-муты",
    ActionType.MUTE_FULL.value: "Фулл-муты",
    ActionType.UNMUTE_LOCAL.value: "Снятие мута",
    ActionType.ROLE_APPROVE.value: "Одобренных ролей",
    ActionType.ROLE_REJECT.value: "Отказанных ролей",
    ActionType.ROLE_REMOVE.value: "Снятия ролей",
    ActionType.ROLE_CANCEL.value: "Перепроверка роли"
}

payload_types = {
    'duration': "Длительность",
    'reason': "Причина",
    'jump_url': "Ссылка на сообщение",
    'nick': "Никнейм",
    'rang': "Ранг",
    'role': "Роль"
}


def from_humanise(action_type):
    for k, v in human_actions.items():
        if v == action_type:
            return k


class Actions:
    def __init__(self, db: motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.actions = self.db['list']

    async def add_action(self, *, user_id, guild_id, moderator_id, action_type: ActionType, payload):
        result = await self.actions.insert_one({
            'user_id': user_id,
            'guild_id': guild_id,
            'moderator_id': moderator_id,
            'action_type': action_type.value,
            'payload': payload,
            'time': datetime.datetime.now()
        })
        return result.inserted_id  # Возвращаем автоматически сгенерированный _id

    async def update_action(self, *, user_id, guild_id, moderator_id, action_type: ActionType, payload):
        filter = {
            'user_id': user_id,
            'guild_id': guild_id,
            'payload': payload
        }

        update = {
            '$set': {
                'moderator_id': int(moderator_id),
                'action_type': action_type.value
            }
        }

        # Проверка текущего состояния документа
        existing_document = await self.actions.find_one(filter)
        if not existing_document:
            print("Document not found with the given filter")
            return None
        filter_by_id = {'_id': existing_document['_id']}
        result = await self.actions.update_one(filter_by_id, update)

        return result

    async def get_punishments(self, type_punishment, *, user_id=None, guild_id=None):
        query = {'user_id': user_id}
        if guild_id:
            query['guild_id'] = guild_id
        if type_punishment != 'FULL':
            query['action_type'] = from_humanise(type_punishment)

        punishments = await self.actions.find(query).to_list(length=None)
        return punishments

    async def get_action(self, action_id):
        return await self.actions.find_one({'_id': action_id})

    @staticmethod
    async def send_log(action_id, guild, embed):
        embed.set_footer(text=f'ID: {action_id}')
        log_channel = [channel for channel in guild.channels if "логи-наказаний" in channel.name][0]
        await log_channel.send(embed=embed)

    @property
    async def max_id(self):
        return await self.actions.count_documents({}) + 1000 - 1

    async def moderator_actions(self, date, moderator_id, guild):
        return await self.actions.find(
            {'moderator_id': moderator_id, 'guild_id': guild, 'time': {'$gte': date, '$lt': date + datetime.timedelta(days=1)}}).to_list(
            length=None)
