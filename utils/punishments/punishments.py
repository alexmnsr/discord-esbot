import asyncio
import datetime
import nextcord

from datetime import timedelta

from utils.classes.actions import ActionType
from utils.neccessary import remove_role, send_embed, add_role, add_ban
from utils.punishments.punishments_database import PunishmentsDatabase


class MuteHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    def mute_info(self, role_name):
        get, give, remove = (self.database.get_text_mute, self.database.give_text_mute, self.database.remove_text_mute) \
            if role_name == 'Mute » Text' else (
            self.database.get_voice_mute, self.database.give_voice_mute, self.database.remove_voice_mute
        ) \
            if role_name == 'Mute » Voice' else (
            self.database.get_full_mute, self.database.give_full_mute, self.database.remove_full_mute
        )
        return get, give, remove

    async def give_mute(self, role_name, *, user, guild, moderator, reason, duration):
        get, give, remove = self.mute_info(role_name)
        user_id = user.id
        action_id = await give(user_id=user_id, guild_id=guild.id, moderator_id=moderator.id, reason=reason,
                               duration=duration)
        if not action_id:
            return
        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        guild, member = await add_role(self.client, user_id, guild.id, action_id, role_name)
        if not guild:
            return

        embed = nextcord.Embed(
            title=f'Вам выдан {role_name}.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member, embed)

        log_embed = nextcord.Embed(title=f'Выдача {role_name if isinstance(role_name, str) else "Full » Mute"}',
                                   color=0xFF0000)
        log_embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        log_embed.add_field(name='Модератор', value=moderator.mention)
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>')
        log_embed.add_field(name='Длительность мута', value=str(int(duration / 60)) + "м")
        log_embed.set_footer(text=f'ID: {member.id}')
        await self.client.db.actions.send_log(action_id, guild, embed=log_embed)

        self.client.loop.create_task(self.wait_mute(action_id, duration, role_name))

    async def wait_mute(self, action_id, seconds, role_name):
        await asyncio.sleep(seconds)
        get, give, remove = self.mute_info(role_name)
        mute = await get(action_id=action_id)
        if not mute:
            return

        await remove(mute['user_id'], mute['guild_id'])
        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        guild, member = await remove_role(self.client, mute['user_id'], mute['guild_id'], action_id, role_name)
        if not guild:
            return

        embed = nextcord.Embed(
            title='Ваш текстовый мут истек.',
            description=f'Вы снова можете продолжать общение в текстовых чатах на сервере {guild.name}.',
            color=0x00FF00
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member, embed)

    async def remove_mute(self, user_id, guild_id, role_name):
        get, give, remove = self.mute_info(role_name)

        if not (mute := await get(user_id=user_id, guild_id=guild_id)) or not await remove(user_id, guild_id):
            return False
        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']

        guild, member = await remove_role(self.client, user_id, guild_id, mute['action_id'], role_name)

        if guild:
            embed = nextcord.Embed(
                title='Снятие мута',
                description=f'У пользователя {member.mention} снят мут.',
                color=0x00FF00
            )
            await send_embed(member, embed)

        log_embed = nextcord.Embed(title='Снятие мута', color=0x00FF00)
        log_embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        log_embed.set_footer(text=f'ID: {mute["action_id"]}')
        await self.client.db.actions.send_log(mute['action_id'], guild, log_embed)
        return True


class BanHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    async def give_ban(self, type_ban, *, user_id, guild, moderator, reason, duration):
        action_id = await self.database.give_ban(user_id=user_id, guild_id=guild.id, moderator_id=moderator.id,
                                                 reason=reason,
                                                 duration=duration, ban_type=type_ban)
        guild, member = await add_ban(self.client, user_id, guild.id)
        if not action_id:
            return

        embed = nextcord.Embed(
            title=f'Вам выдана блокировка на сервере {guild.name}.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + timedelta(days=int(duration))).timestamp())}:R>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member.id, embed)

        log_embed = nextcord.Embed(
            title=f'Выдача {f"блокировки на сервере {guild.name}" if type_ban != "TYPE_GLOBALBAN" else "глобальной блокировки."}',
            color=0xFF0000)
        log_embed.add_field(name='Модератор', value=moderator.mention)
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'{"Никогда" if str(duration) == "-1" else f"<t:{int((datetime.datetime.now() + datetime.timedelta(days=int(duration))).timestamp())}:R>"}')
        log_embed.add_field(name='Длительность блокировки',
                            value=f'{"Вечно" if str(duration) == "-1" else str(duration) + " дней"}')
        log_embed.set_footer(text=f'ID: {member.id}')
        await self.client.db.actions.send_log(action_id, guild, embed=log_embed)

        self.client.loop.create_task(self.wait_ban(action_id, timedelta(days=int(duration)).days * 24 * 60 * 60) if duration != '-1' else '-1')

    async def wait_ban(self, action_id, seconds):
        if seconds == '-1':
            return
        seconds = int(seconds)
        await asyncio.sleep(seconds)
        ban = await self.database.get_ban(action_id=action_id)
        if not ban:
            return

        await self.database.remove_ban(ban['user_id'], ban['guild_id'], action_id=action_id)
        guild, member = await self.database.remove_ban(self.client, ban['user_id'], ban['guild_id'], action_id)
        if not guild:
            return

        embed = nextcord.Embed(
            title=f'Срок Вашей блокировки на сервере {guild.name} истек.',
            description=f'Вы снова можете продолжать общение.',
            color=0x00FF00
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member, embed)

    async def unban(self, user_id, guild_id, ):
        if not (ban := await self.database.get_ban(user_id=user_id, guild_id=guild_id)) or not await self.database.remove_ban(user_id,
                                                                                                                guild_id):
            return False

        guild, member = await self.database.remove_ban(self.client, user_id, guild_id)
        if guild:
            embed = nextcord.Embed(
                title='Снятие мута',
                description=f'У пользователя {member.mention} снята блокировка на сервере {guild.name}.',
                color=0x00FF00
            )
            await send_embed(member, embed)

        log_embed = nextcord.Embed(title='Снятие блокировки', color=0x00FF00)
        log_embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        log_embed.set_footer(text=f'ID: {ban["action_id"]}')
        await self.client.db.actions.send_log(ban['action_id'], guild, log_embed)
        return True


class PunishmentsHandler:
    def __init__(self, client, global_db, mongodb) -> None:
        self.database = PunishmentsDatabase(client, global_db, mongodb)
        self.client = client
        self.mutes = MuteHandler(self)
        self.bans = BanHandler(self)

    async def reload(self):
        current_mutes = await self.database.get_mutes()
        for mute in current_mutes:
            role_name = 'Mute » Text' if mute['type'] == 'text' else 'Mute » Voice' if mute[
                                                                                           'type'] == 'voice' else 'Mute » Full'
