import asyncio
import datetime
from datetime import timedelta

import nextcord

from utils.classes.actions import ActionType
from utils.neccessary import remove_role, send_embed, add_role, user_visual, user_text, mute_name, beautify_seconds
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

    async def user_muted(self, user_id, guild_id):
        return await self.database.get_mutes(user_id, guild_id)

    async def give_mute(self, role_name, *, user, guild, moderator, reason, duration, jump_url):
        get, give, remove = self.mute_info(role_name)
        user_id = user.id
        action_id = await give(user_id=user_id, guild_id=guild.id, moderator_id=moderator.id, reason=reason,
                               duration=duration, jump_url=jump_url)
        if not action_id:
            return
        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']
        guild, member = await add_role(self.client, user_id, guild.id, action_id, role_name)
        if not guild:
            return

        embed = nextcord.Embed(
            title=f'Вам выдан {mute_name(role_name)} мут.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>\nВыдал модератор: <@{moderator.id}>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_footer(text=f'Action ID: {action_id}')

        await send_embed(member, embed)

        log_embed = nextcord.Embed(title=f'Выдача {mute_name(role_name)} мута',
                                   color=0xFF0000)
        log_embed.set_author(name=moderator.display_name, icon_url=moderator.display_avatar.url)
        log_embed.add_field(name='Пользователь', value=user_visual(member))
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>')
        log_embed.add_field(name='Длительность мута', value=str(int(duration / 60)) + "м")
        log_embed.add_field(name='Ссылка на сообщение', value=jump_url)
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
            title=f'Ваш {mute_name(role_name)} мут истек.',
            description=f'Вы снова можете продолжать общение в текстовых чатах на сервере {guild.name}.',
            color=0x00FF00
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member, embed)

    async def remove_mute(self, user_id, guild_id, role_name, moderator):
        get, give, remove = self.mute_info(role_name)

        if not (mute := await get(user_id=user_id, guild_id=guild_id)) or not await remove(user_id, guild_id,
                                                                                           moderator_id=moderator.id):
            return False
        if role_name == 'Mute » Full':
            role_name = ['Mute » Text', 'Mute » Voice']

        guild, member = await remove_role(self.client, user_id, guild_id, mute['action_id'], role_name)

        if guild:
            embed = nextcord.Embed(
                title=f'Вам был снят мут!',
                description=f'Модератор {user_text(moderator)} снял у вас мут на сервере {guild.name}.',
                color=0x00FF00
            )
            await send_embed(member, embed)

        log_embed = nextcord.Embed(title=f'Снятие {mute_name(role_name)} мута', color=0x00FF00)
        log_embed.add_field(name='Пользователь', value=user_visual(member))
        log_embed.set_author(name=moderator.display_name, icon_url=moderator.display_avatar.url)
        log_embed.set_footer(text=f'ID: {mute["action_id"]}')
        await self.client.db.actions.send_log(mute['action_id'], guild, log_embed)
        return True


class WarnHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    async def give_warn(self, type_warn, *, user, guild, moderator, reason, approve_moderator=None, jump_url):
        action_id = await self.database.give_warn(user_id=user.id,
                                                  guild_id=guild.id,
                                                  moderator_id=moderator,
                                                  reason=reason,
                                                  warn_type=type_warn,
                                                  approve_moderator=approve_moderator,
                                                  jump_url=jump_url)
        if not action_id:
            return

        embed = nextcord.Embed(
            title=f'Вам выдано предупреждение на сервере {guild.name}.',
            description=f'Причина: {reason}\nВыдал модератор: <@{moderator}>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        embed.set_footer(text=f'Action ID: {action_id}')

        await send_embed(user.id, embed)

        log_embed = nextcord.Embed(
            title=f'Выдача предупреждения на сервере {guild.name}',
            color=0xFF0000)
        log_embed.add_field(name='Модератор', value=f'<@{moderator}>')
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Ссылка на сообщение', value=jump_url)
        log_embed.set_footer(text=f'ID: {user.id}')

        return action_id


class BanHandler:
    def __init__(self, handler) -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    async def give_ban(self, type_ban, *, user, guild, moderator, reason, duration, approve_moderator=None, jump_url):
        action_id = await self.database.give_ban(user_id=user.id,
                                                 guild_id=guild.id,
                                                 moderator_id=moderator,
                                                 reason=reason,
                                                 duration=duration,
                                                 ban_type=type_ban,
                                                 approve_moderator=approve_moderator,
                                                 jump_url=jump_url)
        if not action_id:
            return

        embed = nextcord.Embed(
            title=f'Вам выдана блокировка на сервере {guild.name}.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + timedelta(seconds=int(duration))).timestamp())}:R>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(user.id, embed)
        await guild.ban(user, reason=f'Action ID: {action_id}')

        log_embed = nextcord.Embed(
            title=f'Выдача {f"блокировки на сервере {guild.name}" if type_ban != ActionType.BAN_GLOBAL else "глобальной блокировки."}',
            color=0xFF0000)
        log_embed.add_field(name='Модератор', value=f'<@{moderator}>')
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'{"Никогда" if duration == "-1" else f"<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=int(duration))).timestamp())}:R>"}')
        log_embed.add_field(name='Длительность блокировки',
                            value=beautify_seconds(duration) if duration != '-1' else 'Никогда')
        log_embed.add_field(name='Ссылка на сообщение', value=jump_url)
        log_embed.set_footer(text=f'ID: {user.id}')
        await self.client.db.actions.send_log(action_id, guild, embed=log_embed)

        if duration != '-1':
            self.client.loop.create_task(self.wait_ban(action_id, duration))

    async def wait_ban(self, action_id, seconds):
        seconds = int(seconds)
        await asyncio.sleep(seconds)
        ban = await self.database.get_ban(action_id=action_id)
        if not ban:
            return

        await self.database.remove_ban(action_id=action_id)
        if ban['type'] == 'global':
            for g in self.client.guilds:
                try:
                    await g.unban(nextcord.Object(ban['user_id']), reason=f'Action ID: {action_id}')
                except:
                    pass
        else:
            guild = self.client.get_guild(ban['guild_id'])
            if not guild:
                return
            try:
                await guild.unban(nextcord.Object(ban['user_id']), reason=f'Action ID: {action_id}')
            except nextcord.NotFound:
                pass

        embed = nextcord.Embed(
            title=f'Срок Вашей блокировки {"всех серверах" if ban["type"] == "global" else "на сервере " + guild.name} истек.',
            description=f'Вы снова можете продолжать общение.',
            color=0x00FF00
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(await self.client.fetch_user(ban['user_id']), embed)

    async def unban(self, user, guild):
        if (not (ban := await self.database.get_ban(user_id=user.id, guild_id=guild.id)) or
                not await self.database.remove_ban(user.id, guild.id)):
            return False

        try:
            await guild.unban(user)
        except nextcord.NotFound:
            pass
        if guild:
            embed = nextcord.Embed(
                title='Снятие бана',
                description=f'У пользователя {user.mention} снята блокировка на сервере {guild.name}.',
                color=0x00FF00
            )
            await send_embed(user, embed)

        log_embed = nextcord.Embed(title='Снятие блокировки', color=0x00FF00)
        log_embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        log_embed.set_footer(text=f'ID: {ban["action_id"]}')
        await self.client.db.actions.send_log(ban['action_id'], guild, log_embed)
        return True


class ApproveHandler:
    def __init__(self, handler: "PunishmentsHandler") -> None:
        self.handler = handler
        self.client = handler.client
        self.database = handler.database

    async def add(self, info: dict) -> int:
        return await self.database.add_approve(info)

    async def pop(self, approve_id: int) -> dict:
        data = await self.database.get_approve(approve_id)
        await self.database.remove_approve(approve_id)
        return data


class PunishmentsHandler:
    def __init__(self, client, global_db, mongodb) -> None:
        self.database = PunishmentsDatabase(client, global_db, mongodb)
        self.client = client
        self.mutes = MuteHandler(self)
        self.bans = BanHandler(self)
        self.warns = WarnHandler(self)
        self.approves = ApproveHandler(self)

    async def reload(self):
        current_mutes = await self.database.get_mutes()
        current_bans = await self.database.get_bans()
        for mute in current_mutes:
            role_name = 'Mute » Text' if mute['type'] == 'text' else 'Mute » Voice' if mute[
                                                                                           'type'] == 'voice' else 'Mute » Full'
            self.client.loop.create_task(self.mutes.wait_mute(mute['action_id'],
                                                              ((mute['given_at'] + datetime.timedelta(seconds=mute[
                                                                  'duration'])) - datetime.datetime.now()).total_seconds(),
                                                              role_name))
        for ban in current_bans:
            if ban['duration'] == '-1':
                continue
            self.client.loop.create_task(self.bans.wait_ban(ban['action_id'],
                                                            ((ban['given_at'] + datetime.timedelta(seconds=ban[
                                                                'duration'])) - datetime.datetime.now()).total_seconds()))
