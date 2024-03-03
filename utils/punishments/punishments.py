import asyncio
import datetime

import nextcord

from utils.neccessary import remove_role, send_embed, add_role
from utils.punishments.punishments_database import PunishmentsDatabase


class PunishmentsHandler:
    def __init__(self, client, global_db, mongodb) -> None:
        self.database = PunishmentsDatabase(client, global_db, mongodb)
        self.client = client

    async def give_text_mute(self, *, user, guild, moderator, reason, duration):
        user_id = user.id
        action_id = await self.database.give_text_mute(user_id, guild.id, moderator.id, reason, duration)
        if not action_id:
            return

        guild, member = await add_role(self.client, user_id, guild.id, action_id, 'Mute » Text')
        if not guild:
            return

        embed = nextcord.Embed(
            title='Вам выдан текстовый мут.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member, embed)

        log_embed = nextcord.Embed(title='Выдача текстового мута', color=0xFF0000)
        log_embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        log_embed.add_field(name='Модератор', value=moderator.mention)
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>')
        log_embed.add_field(name='Длительность мута', value=str(int(duration / 60)) + "м")
        log_embed.set_footer(text=f'ID: {member.id}')
        await self.client.db.actions.send_log(action_id, guild, embed=log_embed)

        self.client.loop.create_task(self.wait_text_mute(action_id, duration))

    async def give_voice_mute(self, *, user, guild, moderator, reason, duration):
        user_id = user.id
        action_id = await self.database.give_voice_mute(user_id, guild.id, moderator.id, reason, duration)
        if not action_id:
            return

        guild, member = await add_role(self.client, user_id, guild.id, action_id, 'Mute » Voice')
        if not guild:
            return

        embed = nextcord.Embed(
            title='Вам выдан голосовой мут.',
            description=f'Причина: {reason}\nВремя истечения: <t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>',
            color=0xFF0000
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member, embed)

        log_embed = nextcord.Embed(title='Выдача голосового мута', color=0xFF0000)
        log_embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        log_embed.add_field(name='Модератор', value=moderator.mention)
        log_embed.add_field(name='Причина', value=reason)
        log_embed.add_field(name='Время истечения',
                            value=f'<t:{int((datetime.datetime.now() + datetime.timedelta(seconds=duration)).timestamp())}:R>')
        log_embed.add_field(name='Длительность мута', value=str(int(duration / 60)) + "м")
        log_embed.set_footer(text=f'ID: {member.id}')
        await self.client.db.actions.send_log(action_id, guild, embed=log_embed)

        self.client.loop.create_task(self.wait_voice_mute(action_id, duration))

    async def wait_text_mute(self, action_id, seconds):
        await asyncio.sleep(seconds)
        mute = await self.database.get_text_mute(action_id=action_id)
        if not mute:
            return

        await self.database.remove_text_mute(mute['user_id'], mute['guild_id'])

        guild, member = await remove_role(self.client, mute['user_id'], mute['guild_id'], action_id, 'Mute » Text')
        if not guild:
            return

        embed = nextcord.Embed(
            title='Ваш текстовый мут истек.',
            description=f'Вы снова можете продолжать общение в текстовых чатах на сервере {guild.name}.',
            color=0x00FF00
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member, embed)

    async def wait_voice_mute(self, action_id, seconds):
        await asyncio.sleep(seconds)
        mute = await self.database.get_voice_mute(action_id=action_id)
        if not mute:
            return

        await self.database.remove_voice_mute(mute['user_id'], mute['guild_id'])

        guild, member = await remove_role(self.client, mute['user_id'], mute['guild_id'], action_id, 'Mute » Voice')
        if not guild:
            return

        embed = nextcord.Embed(
            title='Ваш голосовой мут истек.',
            description=f'Вы снова можете продолжать общение в голосовых каналах на сервере {guild.name}.',
            color=0x00FF00
        )
        embed.set_author(name=guild.name, icon_url=guild.icon.url)

        await send_embed(member, embed)

    async def remove_mute(self, user_id, guild_id, role_name):
        if role_name == 'Mute » Text' and (mute := await self.database.get_text_mute(user_id=user_id, guild_id=guild_id)) and not await self.database.remove_text_mute(user_id, guild_id):
            return False
        elif role_name == 'Mute » Voice' and (mute := await self.database.get_voice_mute(user_id=user_id,guild_id=guild_id)) and not await self.database.remove_voice_mute(user_id, guild_id):
            return False
        elif not await self.database.remove_full_mute(user_id, guild_id):
            return False

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

    async def reload(self):
        current_mutes = await self.database.get_mutes()
        for mute in current_mutes:
            if mute['type'] == 'text':
                action_id = mute['action_id']
                expires_in = (mute['given_at'] + datetime.timedelta(seconds=mute['duration']))
                seconds = (expires_in - datetime.datetime.now()).total_seconds()
                self.client.loop.create_task(self.wait_text_mute(action_id, seconds))
